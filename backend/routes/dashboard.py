from datetime import date

from flask import Blueprint, jsonify, request

from services.summary import monthly_summary, trend_summary
from services.recurring import detect_recurring, sync_recurring_to_db
from models import RecurringExpense
from database import db

bp = Blueprint("dashboard", __name__)


@bp.get("/summary")
def summary():
    today = date.today()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    return jsonify(monthly_summary(year, month))


@bp.get("/trend")
def trend():
    months = request.args.get("months", 6, type=int)
    return jsonify(trend_summary(months))


@bp.get("/recurring/candidates")
def recurring_candidates():
    """Return auto-detected recurring expense candidates (not yet in DB)."""
    candidates = detect_recurring()
    return jsonify(candidates)


@bp.post("/recurring/sync")
def recurring_sync():
    """Run detection and upsert results into recurring_expenses table."""
    result = sync_recurring_to_db()
    return jsonify(result)


@bp.get("/recurring")
def list_recurring():
    items = RecurringExpense.query.filter_by(is_active=True).order_by(
        RecurringExpense.typical_amount.desc()
    ).all()
    return jsonify([r.to_dict() for r in items])


@bp.patch("/recurring/<int:rec_id>")
def update_recurring(rec_id):
    r = RecurringExpense.query.get_or_404(rec_id)
    data = request.get_json()
    if "is_confirmed" in data:
        r.is_confirmed = bool(data["is_confirmed"])
    if "is_active" in data:
        r.is_active = bool(data["is_active"])
    if "category_id" in data:
        r.category_id = data["category_id"]
    if "typical_amount" in data:
        r.typical_amount = float(data["typical_amount"])
    db.session.commit()
    return jsonify(r.to_dict())
