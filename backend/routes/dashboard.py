from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import RecurringExpense
from schemas import RecurringExpenseOut, RecurringExpenseUpdate
from services.recurring import detect_recurring, sync_recurring_to_db
from services.summary import monthly_summary, trend_summary

router = APIRouter()


@router.get("/summary")
def summary(
    year: int | None = None,
    month: int | None = None,
    current_user: Annotated[str, Depends(get_current_user)] = "",
    db: Session = Depends(get_db),
):
    today = date.today()
    return monthly_summary(db, year or today.year, month or today.month, current_user)


@router.get("/trend")
def trend(
    months: int = 6,
    current_user: Annotated[str, Depends(get_current_user)] = "",
    db: Session = Depends(get_db),
):
    return trend_summary(db, months, current_user)


@router.get("/recurring/candidates")
def recurring_candidates(
    current_user: Annotated[str, Depends(get_current_user)] = "",
    db: Session = Depends(get_db),
):
    return detect_recurring(db, current_user)


@router.post("/recurring/sync")
def recurring_sync(
    current_user: Annotated[str, Depends(get_current_user)] = "",
    db: Session = Depends(get_db),
):
    return sync_recurring_to_db(db, current_user)


@router.get("/recurring", response_model=list[RecurringExpenseOut])
def list_recurring(
    current_user: Annotated[str, Depends(get_current_user)] = "",
    db: Session = Depends(get_db),
):
    return (
        db.query(RecurringExpense)
        .filter_by(user_email=current_user, is_active=True)
        .order_by(RecurringExpense.typical_amount.desc())
        .all()
    )


@router.patch("/recurring/{rec_id}", response_model=RecurringExpenseOut)
def update_recurring(
    rec_id: int,
    body: RecurringExpenseUpdate,
    current_user: Annotated[str, Depends(get_current_user)] = "",
    db: Session = Depends(get_db),
):
    r = db.query(RecurringExpense).filter_by(id=rec_id, user_email=current_user).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return r
