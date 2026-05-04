from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import extract
from sqlalchemy.orm import Session

from database import get_db
from models import Category, Transaction
from schemas import (
    BulkCategoriseRequest,
    BulkCategoriseResponse,
    TransactionOut,
    TransactionPage,
    TransactionUpdate,
)

router = APIRouter()


@router.get("/", response_model=TransactionPage)
def list_transactions(
    page: int = 1,
    per_page: int = 50,
    account_id: int | None = None,
    category_id: int | None = None,
    month: int | None = None,
    year: int | None = None,
    search: str = "",
    amount_type: str = "",
    hide_transfers: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).order_by(Transaction.date.desc())

    if account_id is not None:
        q = q.filter(Transaction.account_id == account_id)
    if category_id is not None:
        if category_id == -1:
            q = q.filter(Transaction.category_id == None)
        else:
            q = q.filter(Transaction.category_id == category_id)
    if year is not None:
        q = q.filter(extract("year", Transaction.date) == year)
    if month is not None:
        q = q.filter(extract("month", Transaction.date) == month)
    if search.strip():
        q = q.filter(Transaction.description.ilike(f"%{search.strip()}%"))
    if amount_type == "in":
        q = q.filter(Transaction.amount > 0)
    elif amount_type == "out":
        q = q.filter(Transaction.amount < 0)
    if hide_transfers:
        q = q.filter(Transaction.is_transfer == False)

    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return TransactionPage(
        transactions=items,
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
    )


@router.get("/{txn_id}", response_model=TransactionOut)
def get_transaction(txn_id: int, db: Session = Depends(get_db)):
    t = db.get(Transaction, txn_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return t


@router.patch("/{txn_id}", response_model=TransactionOut)
def update_transaction(txn_id: int, body: TransactionUpdate, db: Session = Depends(get_db)):
    t = db.get(Transaction, txn_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if body.category_id is not None:
        if not db.get(Category, body.category_id):
            raise HTTPException(status_code=404, detail="Category not found")
        t.category_id = body.category_id
    elif body.category_id == 0:
        t.category_id = None

    if body.is_recurring is not None:
        t.is_recurring = body.is_recurring

    db.commit()
    db.refresh(t)
    return t


@router.patch("/bulk-categorise", response_model=BulkCategoriseResponse)
def bulk_categorise(body: BulkCategoriseRequest, db: Session = Depends(get_db)):
    if not db.get(Category, body.category_id):
        raise HTTPException(status_code=404, detail="Category not found")

    updated = (
        db.query(Transaction)
        .filter(Transaction.description.ilike(f"%{body.pattern}%"))
        .update({"category_id": body.category_id}, synchronize_session=False)
    )
    db.commit()
    return BulkCategoriseResponse(updated=updated)
