from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from database import get_db
from models import Account, Transaction
from services.transfers import detect_transfers

router = APIRouter()


class TransferConfirmRequest(BaseModel):
    txn_out_id: int
    txn_in_id: int


class TransferIgnoreRequest(BaseModel):
    txn_id: int


def _owned_txn(txn_id: int, user_email: str, db: Session) -> Transaction:
    """Fetch a transaction that belongs to the current user, or 404."""
    txn = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(Transaction.id == txn_id, Account.user_email == user_email)
        .first()
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.get("/candidates")
def get_candidates(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return detect_transfers(db, current_user)


@router.post("/confirm")
def confirm_transfer(
    body: TransferConfirmRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn_out = _owned_txn(body.txn_out_id, current_user, db)
    txn_in = _owned_txn(body.txn_in_id, current_user, db)

    if txn_out.account_id == txn_in.account_id:
        raise HTTPException(
            status_code=400, detail="Both transactions are on the same account"
        )

    txn_out.is_transfer = True
    txn_out.transfer_counterpart_id = txn_in.id
    txn_out.transfer_ignored = False

    txn_in.is_transfer = True
    txn_in.transfer_counterpart_id = txn_out.id
    txn_in.transfer_ignored = False

    db.commit()
    return {"ok": True}


@router.post("/ignore")
def ignore_transfer(
    body: TransferIgnoreRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = _owned_txn(body.txn_id, current_user, db)
    txn.transfer_ignored = True
    db.commit()
    return {"ok": True}


@router.post("/unlink/{txn_id}")
def unlink_transfer(
    txn_id: int,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = _owned_txn(txn_id, current_user, db)

    if txn.transfer_counterpart_id:
        counterpart = _owned_txn(txn.transfer_counterpart_id, current_user, db)
        counterpart.is_transfer = False
        counterpart.transfer_counterpart_id = None

    txn.is_transfer = False
    txn.transfer_counterpart_id = None
    db.commit()
    return {"ok": True}


@router.get("/confirmed")
def get_confirmed(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_account_ids = {
        row.id for row in db.query(Account.id).filter_by(user_email=current_user).all()
    }
    confirmed = (
        db.query(Transaction)
        .filter(
            Transaction.is_transfer == True,  # noqa: E712
            Transaction.account_id.in_(user_account_ids),
        )
        .options(joinedload(Transaction.account))
        .order_by(Transaction.date.desc())
        .all()
    )

    seen_ids: set[int] = set()
    results = []

    for t in confirmed:
        if t.id in seen_ids:
            continue
        seen_ids.add(t.id)

        counterpart = None
        if t.transfer_counterpart_id:
            seen_ids.add(t.transfer_counterpart_id)
            counterpart = db.get(Transaction, t.transfer_counterpart_id)

        txn_out = t if t.amount <= 0 else counterpart
        txn_in = counterpart if t.amount <= 0 else t

        results.append(
            {
                "txn_out": _ser(txn_out) if txn_out else None,
                "txn_in": _ser(txn_in) if txn_in else None,
                "primary_id": t.id,
            }
        )

    return results


def _ser(t: Transaction) -> dict:
    account = t.account
    return {
        "id": t.id,
        "date": t.date.isoformat(),
        "description": t.description,
        "amount": t.amount,
        "account_id": t.account_id,
        "account_name": (account.nickname or account.account_number)
        if account
        else str(t.account_id),
    }
