from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import RecurringExpense
from schemas import RecurringExpenseOut, RecurringExpenseUpdate
from services.recurring import detect_recurring, sync_recurring_to_db
from services.summary import monthly_summary, trend_summary
from fastapi import HTTPException

router = APIRouter()


@router.get("/summary")
def summary(
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
):
    today = date.today()
    return monthly_summary(db, year or today.year, month or today.month)


@router.get("/trend")
def trend(months: int = 6, db: Session = Depends(get_db)):
    return trend_summary(db, months)


@router.get("/recurring/candidates")
def recurring_candidates(db: Session = Depends(get_db)):
    return detect_recurring(db)


@router.post("/recurring/sync")
def recurring_sync(db: Session = Depends(get_db)):
    return sync_recurring_to_db(db)


@router.get("/recurring", response_model=list[RecurringExpenseOut])
def list_recurring(db: Session = Depends(get_db)):
    return (
        db.query(RecurringExpense)
        .filter_by(is_active=True)
        .order_by(RecurringExpense.typical_amount.desc())
        .all()
    )


@router.patch("/recurring/{rec_id}", response_model=RecurringExpenseOut)
def update_recurring(rec_id: int, body: RecurringExpenseUpdate, db: Session = Depends(get_db)):
    r = db.get(RecurringExpense, rec_id)
    if not r:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return r
