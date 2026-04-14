"""
Transfer detection: find pairs of transactions that are likely internal
account-to-account transfers (same amount, different accounts, within ±2 days).
"""

from sqlalchemy.orm import Session, joinedload

from models import Transaction


def detect_transfers(db: Session) -> list[dict]:
    """
    Find candidate transfer pairs among unreviewed transactions.
    A candidate is a negative transaction on one account paired with a positive
    transaction of the same amount on a different account within ±2 days.
    """
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.is_transfer == False,  # noqa: E712
            Transaction.transfer_ignored == False,  # noqa: E712
        )
        .options(joinedload(Transaction.account))
        .order_by(Transaction.date)
        .all()
    )

    negatives = [t for t in txns if t.amount < 0]
    positives = [t for t in txns if t.amount > 0]

    candidates = []
    seen_pairs: set[tuple[int, int]] = set()

    for neg in negatives:
        for pos in positives:
            if neg.account_id == pos.account_id:
                continue
            # Amount match within £0.02 (rounding differences between banks)
            if abs(abs(neg.amount) - abs(pos.amount)) > 0.02:
                continue
            day_diff = abs((neg.date - pos.date).days)
            if day_diff > 2:
                continue

            pair_key = (min(neg.id, pos.id), max(neg.id, pos.id))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Confidence: 1.0 for same-day exact match, lower for day gaps or rounding
            amount_delta = abs(abs(neg.amount) - abs(pos.amount))
            confidence = round(1.0 - (day_diff * 0.15) - (amount_delta / max(abs(neg.amount), 0.01) * 0.1), 3)

            candidates.append({
                "txn_out": _serialise(neg),
                "txn_in": _serialise(pos),
                "day_diff": day_diff,
                "confidence": confidence,
            })

    candidates.sort(key=lambda c: -c["confidence"])
    return candidates


def _serialise(t: Transaction) -> dict:
    account = t.account
    return {
        "id": t.id,
        "date": t.date.isoformat(),
        "description": t.description,
        "amount": t.amount,
        "account_id": t.account_id,
        "account_name": (account.nickname or account.account_number) if account else str(t.account_id),
    }
