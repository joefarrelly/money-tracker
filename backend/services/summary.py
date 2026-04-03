"""Monthly summary and disposable income calculations."""

from datetime import date
from calendar import monthrange

from sqlalchemy import func, extract

from database import db
from models import RecurringExpense, Salary, Transaction


def monthly_summary(year: int, month: int) -> dict:
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

    txns = Transaction.query.filter(
        Transaction.date >= start,
        Transaction.date <= end,
    ).all()

    total_in = sum(t.amount for t in txns if t.amount > 0)
    total_out = abs(sum(t.amount for t in txns if t.amount < 0))

    # Salary that month
    salary_rows = Salary.query.filter(
        Salary.date >= start,
        Salary.date <= end,
    ).all()
    salary_total = sum(s.net_amount for s in salary_rows)

    # Active recurring expenses
    recurring = RecurringExpense.query.filter_by(is_active=True).all()
    recurring_monthly_total = sum(r.monthly_cost for r in recurring)

    # Category breakdown (spending only)
    cat_breakdown = {}
    for t in txns:
        if t.amount >= 0:
            continue
        cat_name = t.category.name if t.category else "Uncategorised"
        cat_color = t.category.color if t.category else "#6b7280"
        if cat_name not in cat_breakdown:
            cat_breakdown[cat_name] = {"amount": 0.0, "color": cat_color, "count": 0}
        cat_breakdown[cat_name]["amount"] += abs(t.amount)
        cat_breakdown[cat_name]["count"] += 1

    # Disposable = salary - recurring costs (ignores one-off spending)
    disposable = salary_total - recurring_monthly_total

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
        "salary_entries": [s.to_dict() for s in salary_rows],
    }


def trend_summary(months: int = 6) -> list[dict]:
    """Return monthly summaries for the last N months."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    today = date.today()
    results = []
    for i in range(months - 1, -1, -1):
        d = today - relativedelta(months=i)
        results.append(monthly_summary(d.year, d.month))
    return results
