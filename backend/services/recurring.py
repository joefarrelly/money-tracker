"""
Auto-detect recurring expenses from transaction history.

Algorithm:
  1. Group transactions by normalised merchant name.
  2. For each merchant with 3+ occurrences, check if they appear at roughly monthly
     intervals (within ±10 days) with similar amounts (within 20%).
  3. Return candidates sorted by confidence (occurrence count × amount stability).
"""

from collections import defaultdict
from datetime import date
import re

from database import db
from models import RecurringExpense, Transaction


def _normalise_merchant(description: str) -> str:
    """Strip noise to get a stable merchant key."""
    s = description.upper()
    # Remove common reference number patterns
    s = re.sub(r"\b\d{6,}\b", "", s)
    s = re.sub(r"[*#/\\]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Take first ~4 words as the key
    words = s.split()
    return " ".join(words[:4])


def detect_recurring(min_occurrences: int = 3) -> list[dict]:
    """
    Analyse all stored transactions and return a list of recurring expense candidates.
    Only considers outgoing transactions (amount < 0).
    """
    txns = (
        Transaction.query.filter(Transaction.amount < 0)
        .order_by(Transaction.date)
        .all()
    )

    # Group by merchant key
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for t in txns:
        key = _normalise_merchant(t.description)
        groups[key].append(t)

    candidates = []
    for merchant, group in groups.items():
        if len(group) < min_occurrences:
            continue

        amounts = [abs(t.amount) for t in group]
        dates = [t.date for t in group]

        # Check amount stability: std/mean < 0.2
        mean_amount = sum(amounts) / len(amounts)
        if mean_amount < 1:
            continue
        variance = sum((a - mean_amount) ** 2 for a in amounts) / len(amounts)
        std = variance ** 0.5
        if std / mean_amount > 0.20:
            continue

        # Check monthly cadence: gaps between consecutive dates ~25-35 days
        gaps = [
            (dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)
        ]
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

        # Day of month (most common)
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


def sync_recurring_to_db() -> dict:
    """
    Run detection and upsert confirmed recurring expenses into the DB.
    Returns counts of created/updated/skipped.
    """
    candidates = detect_recurring()
    created = updated = skipped = 0

    for c in candidates:
        existing = RecurringExpense.query.filter_by(
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
            db.session.add(
                RecurringExpense(
                    merchant_pattern=c["merchant_pattern"],
                    typical_amount=c["typical_amount"],
                    frequency=c["frequency"],
                    day_of_month=c["day_of_month"],
                    is_confirmed=False,
                )
            )
            created += 1

    db.session.commit()
    return {"created": created, "updated": updated, "skipped": skipped}
