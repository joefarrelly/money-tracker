from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from database import get_db
from models import PersonIdentity, Salary
from schemas import PersonIdentityOut, PersonIdentityUpdate

router = APIRouter()


@router.get("/ni-numbers")
def list_ni_numbers(db: Session = Depends(get_db)):
    """All distinct NI numbers seen in payslips, with their assigned name if set."""
    rows = (
        db.query(distinct(Salary.ni_number))
        .filter(Salary.ni_number.isnot(None))
        .all()
    )
    result = []
    for (ni,) in rows:
        identity = db.query(PersonIdentity).filter_by(ni_number=ni).first()
        result.append({
            "ni_number": ni,
            "display_name": identity.display_name if identity else None,
            "identity_id": identity.id if identity else None,
        })
    return sorted(result, key=lambda x: x["ni_number"])


@router.put("/ni-numbers/{ni_number}", response_model=PersonIdentityOut)
def set_ni_name(ni_number: str, body: PersonIdentityUpdate, db: Session = Depends(get_db)):
    """Create or update the display name for a given NI number."""
    identity = db.query(PersonIdentity).filter_by(ni_number=ni_number).first()
    if identity:
        identity.display_name = body.display_name.strip()
    else:
        identity = PersonIdentity(ni_number=ni_number, display_name=body.display_name.strip())
        db.add(identity)
    db.commit()
    db.refresh(identity)
    return identity
