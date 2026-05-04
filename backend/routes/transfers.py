from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Transaction
from services.transfers import detect_transfers

router = APIRouter()


class TransferConfirmRequest(BaseModel):
    txn_out_id: int
    txn_in_id: int


class TransferIgnoreRequest(BaseModel):
    txn_id: int


# ── Candidates ────────────────────────────────────────────────────────────────

@router.get("/candidates")
def get_candidates(db: Session = Depends(get_db)):
    return detect_transfers(db)


# ── Confirm a pair ────────────────────────────────────────────────────────────

@router.post("/confirm")
def confirm_transfer(body: TransferConfirmRequest, db: Session = Depends(get_db)):
    txn_out = db.get(Transaction, body.txn_out_id)
    txn_in = db.get(Transaction, body.txn_in_id)

    if not txn_out or not txn_in:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn_out.account_id == txn_in.account_id:
        raise HTTPException(status_code=400, detail="Both transactions are on the same account")

    txn_out.is_transfer = True
    txn_out.transfer_counterpart_id = txn_in.id
    txn_out.transfer_ignored = False

    txn_in.is_transfer = True
    txn_in.transfer_counterpart_id = txn_out.id
    txn_in.transfer_ignored = False

    db.commit()
    return {"ok": True}


# ── Ignore (deny candidate) ───────────────────────────────────────────────────

@router.post("/ignore")
def ignore_transfer(body: TransferIgnoreRequest, db: Session = Depends(get_db)):
    txn = db.get(Transaction, body.txn_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.transfer_ignored = True
    db.commit()
    return {"ok": True}


# ── Unlink a confirmed transfer ───────────────────────────────────────────────

@router.post("/unlink/{txn_id}")
def unlink_transfer(txn_id: int, db: Session = Depends(get_db)):
    txn = db.get(Transaction, txn_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Clear the counterpart too
    if txn.transfer_counterpart_id:
        counterpart = db.get(Transaction, txn.transfer_counterpart_id)
        if counterpart:
            counterpart.is_transfer = False
            counterpart.transfer_counterpart_id = None

    txn.is_transfer = False
    txn.transfer_counterpart_id = None
    db.commit()
    return {"ok": True}


# ── List confirmed transfers ──────────────────────────────────────────────────

@router.get("/confirmed")
def get_confirmed(db: Session = Depends(get_db)):
    """
    Returns confirmed transfers as pairs (or singletons for one-sided transfers).
    Deduplicates pairs so each shows once.
    """
    confirmed = (
        db.query(Transaction)
        .filter(Transaction.is_transfer == True)  # noqa: E712
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

        # Normalise so txn_out is always the negative side
        txn_out = t if t.amount <= 0 else counterpart
        txn_in = counterpart if t.amount <= 0 else t

        results.append({
            "txn_out": _ser(txn_out) if txn_out else None,
            "txn_in": _ser(txn_in) if txn_in else None,
            "primary_id": t.id,
        })

    return results


def _ser(t: Transaction) -> dict:
    account = t.account
    return {
        "id": t.id,
        "date": t.date.isoformat(),
        "description": t.description,
        "amount": t.amount,
        "account_id": t.account_id,
        "account_name": (account.nickname or account.account_number) if account else str(t.account_id),
    }
