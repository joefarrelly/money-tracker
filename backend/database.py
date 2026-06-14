import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_raw_url = os.environ.get("DATABASE_URL")
if not _raw_url:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Run via Docker ('docker compose up') or set DATABASE_URL in backend/.env."
    )

DATABASE_URL = _raw_url
engine = create_engine(DATABASE_URL)
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
    _migrate()
    _seed_default_categories()


def _migrate():
    """Add columns/indexes that exist in the model but are missing from the live DB."""
    from sqlalchemy import inspect as sa_inspect, text

    migrations = [
        ("salaries", "source_file", "VARCHAR(255)"),
        ("salaries", "ni_number", "VARCHAR(20)"),
        ("transactions", "is_transfer", "BOOLEAN DEFAULT FALSE"),
        ("transactions", "transfer_counterpart_id", "INTEGER"),
        ("transactions", "transfer_ignored", "BOOLEAN DEFAULT FALSE"),
        ("email_imports", "imported_at", "TIMESTAMP"),
        ("user_parser_templates", "deduction_boundary_keyword", "VARCHAR(100)"),
        # Multi-tenancy
        ("accounts", "user_email", "VARCHAR(255)"),
        ("recurring_expenses", "user_email", "VARCHAR(255)"),
        ("salaries", "user_email", "VARCHAR(255)"),
        ("person_identities", "user_email", "VARCHAR(255)"),
        ("email_imports", "user_email", "VARCHAR(255)"),
    ]
    inspector = sa_inspect(engine)
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            existing = {col["name"] for col in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                )
                conn.commit()

        # Drop the old globally-unique constraint on account_number now that it's per-user
        conn.execute(
            text(
                "ALTER TABLE accounts "
                "DROP CONSTRAINT IF EXISTS accounts_account_number_key"
            )
        )
        conn.commit()

        # Partial unique index: prevent duplicate (date, ni_number) when ni_number is set
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_salary_date_ni "
                "ON salaries(date, ni_number) WHERE ni_number IS NOT NULL"
            )
        )
        conn.commit()


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
