from flask import Blueprint, jsonify, request

from database import db
from models import Account

bp = Blueprint("accounts", __name__)


@bp.get("/")
def list_accounts():
    accounts = Account.query.order_by(Account.bank, Account.nickname).all()
    return jsonify([a.to_dict() for a in accounts])


@bp.patch("/<int:account_id>")
def update_account(account_id):
    a = Account.query.get_or_404(account_id)
    data = request.get_json()
    if "nickname" in data:
        a.nickname = data["nickname"].strip()
    db.session.commit()
    return jsonify(a.to_dict())
