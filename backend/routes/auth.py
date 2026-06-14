import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

from auth import JWT_ALGORITHM, JWT_SECRET, create_token, get_current_user

DEMO_USER = "demo@montrack.app"

router = APIRouter()

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _redirect_uri() -> str:
    base = os.environ.get("BASE_URL", "").rstrip("/")
    return f"{base}/api/auth/callback"


def _make_state() -> str:
    payload = {
        "nonce": secrets.token_hex(16),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, JWT_SECRET or "dev-insecure", algorithm=JWT_ALGORITHM)


def _verify_state(state: str) -> bool:
    try:
        jwt.decode(state, JWT_SECRET or "dev-insecure", algorithms=[JWT_ALGORITHM])
        return True
    except JWTError:
        return False


@router.get("/google")
async def auth_google() -> RedirectResponse:
    params = {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "openid email",
        "state": _make_state(),
        "access_type": "online",
    }
    return RedirectResponse(f"{_GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/callback")
async def auth_callback(code: str, state: str) -> RedirectResponse:
    if not _verify_state(state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Token exchange failed")

        access_token = token_resp.json()["access_token"]

        user_resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")

        email: str = user_resp.json()["email"]

    token = create_token(email)
    base_url = os.environ.get("BASE_URL", "").rstrip("/")
    return RedirectResponse(f"{base_url}/auth/callback?token={token}")


@router.get("/me")
async def auth_me(email: Annotated[str, Depends(get_current_user)]) -> dict[str, str]:
    return {"email": email}


@router.get("/demo")
async def auth_demo() -> RedirectResponse:
    token = create_token(DEMO_USER)
    base_url = os.environ.get("BASE_URL", "").rstrip("/")
    return RedirectResponse(f"{base_url}/auth/callback?token={token}")
