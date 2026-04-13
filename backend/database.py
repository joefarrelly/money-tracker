import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'money_tracker.db')}"
)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models  # noqa: F401 — registers all models before create_all
    Base.metadata.create_all(bind=engine)
    _seed_default_categories()


def _seed_default_categories():
    from models import Category

    db = SessionLocal()
    try:
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
            if not db.query(Category).filter_by(name=cat_data["name"]).first():
                db.add(Category(**cat_data))
        db.commit()
    finally:
        db.close()
