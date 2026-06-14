from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import extract
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Account, Category, Transaction
from schemas import (
    BulkCategoriseRequest,
    BulkCategoriseResponse,
    TransactionOut,
    TransactionPage,
    TransactionUpdate,
)

router = APIRouter()


def _user_txn_query(db: Session, user_email: str):
    """Base query: transactions belonging to the current user's accounts."""
    return (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(Account.user_email == user_email)
    )


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
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _user_txn_query(db, current_user).order_by(Transaction.date.desc())

    if account_id is not None:
        q = q.filter(Transaction.account_id == account_id)
    if category_id is not None:
        if category_id == -1:
            q = q.filter(Transaction.category_id.is_(None))
        else:
            q = q.filter(Transaction.category_id == category_id)
    if year is not None:
        q = q.filter(extract("year", Transaction.date) == year)
    if month is not None:
        q = q.filter(extract("month", Transaction.date) == month)
    if search:
        q = q.filter(Transaction.description.ilike(f"%{search}%"))
    if amount_type == "in":
        q = q.filter(Transaction.amount > 0)
    elif amount_type == "out":
        q = q.filter(Transaction.amount < 0)
    if hide_transfers:
        q = q.filter(Transaction.is_transfer == False)  # noqa: E712

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return TransactionPage(
        transactions=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/{txn_id}", response_model=TransactionOut)
def get_transaction(
    txn_id: int,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = _user_txn_query(db, current_user).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.patch("/{txn_id}", response_model=TransactionOut)
def update_transaction(
    txn_id: int,
    body: TransactionUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = _user_txn_query(db, current_user).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(txn, field, value)
    db.commit()
    db.refresh(txn)
    return txn


@router.patch("/bulk-categorise", response_model=BulkCategoriseResponse)
def bulk_categorise(
    body: BulkCategoriseRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = db.get(Category, body.category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    txns = (
        _user_txn_query(db, current_user)
        .filter(Transaction.description.ilike(f"%{body.pattern}%"))
        .all()
    )
    for t in txns:
        t.category_id = body.category_id
    db.commit()
    return BulkCategoriseResponse(updated=len(txns))
