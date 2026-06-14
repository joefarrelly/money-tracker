from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Account
from schemas import AccountOut, AccountUpdate

router = APIRouter()


@router.get("/", response_model=list[AccountOut])
def list_accounts(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Account)
        .filter_by(user_email=current_user)
        .order_by(Account.bank, Account.nickname)
        .all()
    )


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: int,
    body: AccountUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(Account).filter_by(id=account_id, user_email=current_user).first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.nickname = body.nickname.strip()
    db.commit()
    db.refresh(account)
    return account
