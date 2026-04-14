"""Monthly summary and disposable income calculations."""

from calendar import monthrange
from datetime import date

from sqlalchemy import extract
from sqlalchemy.orm import Session

from models import RecurringExpense, Salary, Transaction


def monthly_summary(db: Session, year: int, month: int) -> dict:
    """
    Return a full monthly breakdown:
      - total_in / total_out
      - salary for that month
      - recurring expenses (active, monthly cost)
      - disposable income = salary - recurring_total
      - category breakdown of spending
    """
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    txns = db.query(Transaction).filter(
        Transaction.date >= start,
        Transaction.date <= end,
    ).all()

    total_in = sum(t.amount for t in txns if t.amount > 0 and not t.is_transfer)
    total_out = abs(sum(t.amount for t in txns if t.amount < 0 and not t.is_transfer))

    salary_rows = db.query(Salary).filter(
        Salary.date >= start,
        Salary.date <= end,
    ).all()
    salary_total = sum(s.net_amount for s in salary_rows)

    recurring = db.query(RecurringExpense).filter_by(is_active=True).all()
    recurring_monthly_total = sum(r.monthly_cost for r in recurring)

    cat_breakdown = {}
    for t in txns:
        if t.amount >= 0 or t.is_transfer:
            continue
        cat_name = t.category.name if t.category else "Uncategorised"
        cat_color = t.category.color if t.category else "#6b7280"
        if cat_name not in cat_breakdown:
            cat_breakdown[cat_name] = {"amount": 0.0, "color": cat_color, "count": 0}
        cat_breakdown[cat_name]["amount"] += abs(t.amount)
        cat_breakdown[cat_name]["count"] += 1

    disposable = salary_total - recurring_monthly_total

    # Recurring actuals — compare each active recurring expense against this month's transactions
    recurring_actuals = []
    for r in recurring:
        matching = [
            t for t in txns
            if t.amount < 0 and r.merchant_pattern.lower() in t.description.lower()
        ]
        actual = round(abs(sum(t.amount for t in matching)), 2)
        recurring_actuals.append({
            "id": r.id,
            "merchant_pattern": r.merchant_pattern,
            "typical_amount": r.typical_amount,
            "monthly_cost": round(r.monthly_cost, 2),
            "frequency": r.frequency,
            "actual_amount": actual,
            "found_this_month": actual > 0,
            "is_over": actual > 0 and actual > r.monthly_cost * 1.15,
        })

    return {
        "year": year,
        "month": month,
        "total_in": round(total_in, 2),
        "total_out": round(total_out, 2),
        "net": round(total_in - total_out, 2),
        "salary": round(salary_total, 2),
        "recurring_total": round(recurring_monthly_total, 2),
        "disposable_income": round(disposable, 2),
        "category_breakdown": [
            {"name": k, "amount": round(v["amount"], 2), "color": v["color"], "count": v["count"]}
            for k, v in sorted(cat_breakdown.items(), key=lambda x: -x[1]["amount"])
        ],
        "transaction_count": len(txns),
        "recurring_actuals": recurring_actuals,
        "salary_entries": [
            {
                "id": s.id,
                "date": s.date.isoformat(),
                "gross_amount": s.gross_amount,
                "net_amount": s.net_amount,
                "employer": s.employer,
                "notes": s.notes,
                "ni_number": s.ni_number,
                "created_at": s.created_at.isoformat(),
                "line_items": [
                    {
                        "id": li.id,
                        "description": li.description,
                        "amount": li.amount,
                        "line_type": li.line_type,
                        "rate": li.rate,
                        "units": li.units,
                        "this_year_amount": li.this_year_amount,
                    }
                    for li in s.line_items
                ],
            }
            for s in salary_rows
        ],
    }


def trend_summary(db: Session, months: int = 6) -> list[dict]:
    """Return monthly summaries for the last N months."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    today = date.today()
    results = []
    for i in range(months - 1, -1, -1):
        d = today - relativedelta(months=i)
        results.append(monthly_summary(db, d.year, d.month))
    return results
