from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import PersonIdentity, Salary, UserEmailConfig
from schemas import PersonIdentityOut, PersonIdentityUpdate

router = APIRouter()


@router.get("/ni-numbers")
def list_ni_numbers(db: Session = Depends(get_db)):
    """All distinct NI numbers seen in payslips, with their assigned name if set."""
    rows = (
        db.query(distinct(Salary.ni_number)).filter(Salary.ni_number.isnot(None)).all()
    )
    result = []
    for (ni,) in rows:
        identity = db.query(PersonIdentity).filter_by(ni_number=ni).first()
        result.append(
            {
                "ni_number": ni,
                "display_name": identity.display_name if identity else None,
                "identity_id": identity.id if identity else None,
            }
        )
    return sorted(result, key=lambda x: x["ni_number"])


@router.put("/ni-numbers/{ni_number}", response_model=PersonIdentityOut)
def set_ni_name(
    ni_number: str, body: PersonIdentityUpdate, db: Session = Depends(get_db)
):
    """Create or update the display name for a given NI number."""
    identity = db.query(PersonIdentity).filter_by(ni_number=ni_number).first()
    if identity:
        identity.display_name = body.display_name.strip()
    else:
        identity = PersonIdentity(
            ni_number=ni_number, display_name=body.display_name.strip()
        )
        db.add(identity)
    db.commit()
    db.refresh(identity)
    return identity


class EmailConfigOut(BaseModel):
    configured: bool
    user_email: str | None = None
    label: str
    enabled: bool


class EmailConfigUpdate(BaseModel):
    app_password: str
    label: str = "INBOX"
    enabled: bool = True


@router.get("/email-config", response_model=EmailConfigOut)
def get_email_config(
    current_user: str = Depends(get_current_user), db: Session = Depends(get_db)
):
    cfg = db.get(UserEmailConfig, current_user)
    if not cfg:
        return EmailConfigOut(configured=False, label="INBOX", enabled=True)
    return EmailConfigOut(
        configured=True,
        user_email=cfg.user_email,
        label=cfg.label or "INBOX",
        enabled=cfg.enabled,
    )


@router.put("/email-config", response_model=EmailConfigOut)
def set_email_config(
    body: EmailConfigUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cfg = db.get(UserEmailConfig, current_user)
    if cfg:
        cfg.app_password = body.app_password
        cfg.label = body.label
        cfg.enabled = body.enabled
    else:
        cfg = UserEmailConfig(
            user_email=current_user,
            app_password=body.app_password,
            label=body.label,
            enabled=body.enabled,
        )
        db.add(cfg)
    db.commit()
    return EmailConfigOut(
        configured=True,
        user_email=cfg.user_email,
        label=cfg.label or "INBOX",
        enabled=cfg.enabled,
    )


@router.delete("/email-config")
def delete_email_config(
    current_user: str = Depends(get_current_user), db: Session = Depends(get_db)
):
    cfg = db.get(UserEmailConfig, current_user)
    if cfg:
        db.delete(cfg)
        db.commit()
    return {"configured": False}
