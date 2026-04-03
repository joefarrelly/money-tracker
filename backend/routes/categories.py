from flask import Blueprint, jsonify, request

from database import db
from models import Category

bp = Blueprint("categories", __name__)


@bp.get("/")
def list_categories():
    cats = Category.query.order_by(Category.name).all()
    return jsonify([c.to_dict() for c in cats])


@bp.post("/")
def create_category():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400

    if Category.query.filter_by(name=name).first():
        return jsonify({"error": "Category already exists"}), 409

    cat = Category(name=name, color=data.get("color", "#6b7280"), icon=data.get("icon"))
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201


@bp.patch("/<int:cat_id>")
def update_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    data = request.get_json()
    if "name" in data:
        cat.name = data["name"]
    if "color" in data:
        cat.color = data["color"]
    if "icon" in data:
        cat.icon = data["icon"]
    db.session.commit()
    return jsonify(cat.to_dict())


@bp.delete("/<int:cat_id>")
def delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    return "", 204
