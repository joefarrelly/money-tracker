from datetime import date

from flask import Blueprint, jsonify, request

from database import db
from models import Salary

bp = Blueprint("salaries", __name__)


@bp.get("/")
def list_salaries():
    salaries = Salary.query.order_by(Salary.date.desc()).all()
    return jsonify([s.to_dict() for s in salaries])


@bp.post("/")
def create_salary():
    data = request.get_json()
    try:
        salary_date = date.fromisoformat(data["date"])
    except (KeyError, ValueError):
        return jsonify({"error": "valid date (YYYY-MM-DD) required"}), 400

    net = data.get("net_amount")
    if net is None:
        return jsonify({"error": "net_amount required"}), 400

    s = Salary(
        date=salary_date,
        net_amount=float(net),
        gross_amount=float(data["gross_amount"]) if data.get("gross_amount") else None,
        employer=data.get("employer", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(s)
    db.session.commit()
    return jsonify(s.to_dict()), 201


@bp.patch("/<int:salary_id>")
def update_salary(salary_id):
    s = Salary.query.get_or_404(salary_id)
    data = request.get_json()
    if "date" in data:
        s.date = date.fromisoformat(data["date"])
    if "net_amount" in data:
        s.net_amount = float(data["net_amount"])
    if "gross_amount" in data:
        s.gross_amount = float(data["gross_amount"]) if data["gross_amount"] else None
    if "employer" in data:
        s.employer = data["employer"]
    if "notes" in data:
        s.notes = data["notes"]
    db.session.commit()
    return jsonify(s.to_dict())


@bp.delete("/<int:salary_id>")
def delete_salary(salary_id):
    s = Salary.query.get_or_404(salary_id)
    db.session.delete(s)
    db.session.commit()
    return "", 204
