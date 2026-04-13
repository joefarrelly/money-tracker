"""
Auto-detect recurring expenses from transaction history.

Algorithm:
  1. Group transactions by normalised merchant name.
  2. For each merchant with 3+ occurrences, check if they appear at roughly monthly
     intervals (within ±10 days) with similar amounts (within 20%).
  3. Return candidates sorted by confidence (occurrence count × amount stability).
"""

import re
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from models import RecurringExpense, Transaction


def _normalise_merchant(description: str) -> str:
    """Strip noise to get a stable merchant key."""
    s = description.upper()
    s = re.sub(r"\b\d{6,}\b", "", s)
    s = re.sub(r"[*#/\\]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    words = s.split()
    return " ".join(words[:4])


def detect_recurring(db: Session, min_occurrences: int = 3) -> list[dict]:
    """
    Analyse all stored transactions and return a list of recurring expense candidates.
    Only considers outgoing transactions (amount < 0).
    """
    txns = (
        db.query(Transaction)
        .filter(Transaction.amount < 0)
        .order_by(Transaction.date)
        .all()
    )

    groups: dict[str, list] = defaultdict(list)
    for t in txns:
        key = _normalise_merchant(t.description)
        groups[key].append(t)

    candidates = []
    for merchant, group in groups.items():
        if len(group) < min_occurrences:
            continue

        amounts = [abs(t.amount) for t in group]
        dates = [t.date for t in group]

        mean_amount = sum(amounts) / len(amounts)
        if mean_amount < 1:
            continue
        variance = sum((a - mean_amount) ** 2 for a in amounts) / len(amounts)
        std = variance ** 0.5
        if std / mean_amount > 0.20:
            continue

        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        if not gaps:
            continue
        monthly_gaps = [g for g in gaps if 20 <= g <= 40]
        annual_gaps = [g for g in gaps if 330 <= g <= 400]

        if len(monthly_gaps) / len(gaps) >= 0.6:
            frequency = "monthly"
        elif len(annual_gaps) / len(gaps) >= 0.6:
            frequency = "annual"
        else:
            continue

        days = [d.day for d in dates]
        day_of_month = max(set(days), key=days.count)

        candidates.append(
            {
                "merchant_pattern": merchant,
                "typical_amount": round(mean_amount, 2),
                "frequency": frequency,
                "day_of_month": day_of_month,
                "occurrences": len(group),
                "last_seen": max(dates).isoformat(),
            }
        )

    candidates.sort(key=lambda c: c["occurrences"], reverse=True)
    return candidates


def sync_recurring_to_db(db: Session) -> dict:
    """
    Run detection and upsert confirmed recurring expenses into the DB.
    Returns counts of created/updated/skipped.
    """
    candidates = detect_recurring(db)
    created = updated = skipped = 0

    for c in candidates:
        existing = db.query(RecurringExpense).filter_by(
            merchant_pattern=c["merchant_pattern"]
        ).first()

        if existing:
            if not existing.is_confirmed:
                existing.typical_amount = c["typical_amount"]
                existing.frequency = c["frequency"]
                existing.day_of_month = c["day_of_month"]
                updated += 1
            else:
                skipped += 1
        else:
            db.add(RecurringExpense(
                merchant_pattern=c["merchant_pattern"],
                typical_amount=c["typical_amount"],
                frequency=c["frequency"],
                day_of_month=c["day_of_month"],
                is_confirmed=False,
            ))
            created += 1

    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}
