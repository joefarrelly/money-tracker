from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    db.init_app(app)
    with app.app_context():
        import models  # noqa: F401 — ensures all models are registered before create_all
        db.create_all()
        _seed_default_categories()


def _seed_default_categories():
    from models import Category

    defaults = [
        {"name": "Housing", "color": "#ef4444", "icon": "home"},
        {"name": "Groceries", "color": "#22c55e", "icon": "shopping-cart"},
        {"name": "Transport", "color": "#3b82f6", "icon": "car"},
        {"name": "Utilities", "color": "#f59e0b", "icon": "zap"},
        {"name": "Subscriptions", "color": "#8b5cf6", "icon": "repeat"},
        {"name": "Eating Out", "color": "#f97316", "icon": "utensils"},
        {"name": "Entertainment", "color": "#ec4899", "icon": "tv"},
        {"name": "Health", "color": "#14b8a6", "icon": "heart"},
        {"name": "Income", "color": "#10b981", "icon": "trending-up"},
        {"name": "Savings", "color": "#6366f1", "icon": "piggy-bank"},
        {"name": "Other", "color": "#6b7280", "icon": "tag"},
    ]

    for cat_data in defaults:
        if not Category.query.filter_by(name=cat_data["name"]).first():
            db.session.add(Category(**cat_data))

    db.session.commit()
