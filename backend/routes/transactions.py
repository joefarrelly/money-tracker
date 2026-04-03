from flask import Blueprint, jsonify, request

from database import db
from models import Category, Transaction

bp = Blueprint("transactions", __name__)


@bp.get("/")
def list_transactions():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    account_id = request.args.get("account_id", type=int)
    category_id = request.args.get("category_id", type=int)
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    search = request.args.get("search", "").strip()

    q = Transaction.query.order_by(Transaction.date.desc())

    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category_id:
        q = q.filter(Transaction.category_id == category_id)
    if year:
        q = q.filter(db.extract("year", Transaction.date) == year)
    if month:
        q = q.filter(db.extract("month", Transaction.date) == month)
    if search:
        q = q.filter(Transaction.description.ilike(f"%{search}%"))

    paginated = q.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "transactions": [t.to_dict() for t in paginated.items],
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages,
            "per_page": per_page,
        }
    )


@bp.get("/<int:txn_id>")
def get_transaction(txn_id):
    t = Transaction.query.get_or_404(txn_id)
    return jsonify(t.to_dict())


@bp.patch("/<int:txn_id>")
def update_transaction(txn_id):
    t = Transaction.query.get_or_404(txn_id)
    data = request.get_json()

    if "category_id" in data:
        if data["category_id"] is not None:
            Category.query.get_or_404(data["category_id"])
        t.category_id = data["category_id"]

    if "is_recurring" in data:
        t.is_recurring = bool(data["is_recurring"])

    db.session.commit()
    return jsonify(t.to_dict())


@bp.patch("/bulk-categorise")
def bulk_categorise():
    """Apply a category to all transactions matching a description fragment."""
    data = request.get_json()
    pattern = data.get("pattern", "").strip()
    category_id = data.get("category_id")

    if not pattern or category_id is None:
        return jsonify({"error": "pattern and category_id required"}), 400

    Category.query.get_or_404(category_id)

    updated = (
        Transaction.query.filter(Transaction.description.ilike(f"%{pattern}%"))
        .update({"category_id": category_id}, synchronize_session=False)
    )
    db.session.commit()
    return jsonify({"updated": updated})
