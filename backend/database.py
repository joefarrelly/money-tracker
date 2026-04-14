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
    _migrate()
    _seed_default_categories()
    _seed_builtin_formats()


def _migrate():
    """Add columns that exist in the model but are missing from the live DB."""
    from sqlalchemy import text

    migrations = [
        ("statement_formats", "date_description_col", "INTEGER"),
        ("salaries", "source_file", "VARCHAR(255)"),
        ("salaries", "ni_number", "VARCHAR(20)"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            existing = {r[1] for r in rows}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()

        # Partial unique index: prevent duplicate (date, ni_number) when ni_number is set
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_salary_date_ni "
            "ON salaries(date, ni_number) WHERE ni_number IS NOT NULL"
        ))
        conn.commit()


def _seed_builtin_formats():
    from models import StatementFormat

    db = SessionLocal()
    try:
        builtin = [
            {
                "name": "Barclays",
                "column_headers": ["Date", "Description", "Money out", "Money in", "Balance"],
                "date_col": 0,
                "description_col": 1,
                "money_out_col": 2,
                "money_in_col": 3,
                "balance_col": 4,
                "amount_col": None,
                "amount_style": "split",
                "date_format": "%d %b",
                "year_source": "detect",
                "is_builtin": True,
            },
            {
                "name": "Chase",
                "column_headers": ["Date", "Transaction details", "Amount", "Balance"],
                "date_col": 0,
                "description_col": 1,
                "amount_col": 2,
                "money_in_col": None,
                "money_out_col": None,
                "balance_col": 3,
                "amount_style": "signed",
                "date_format": "%d %b %Y",
                "year_source": "inline",
                "is_builtin": True,
            },
        ]
        for fmt_data in builtin:
            if not db.query(StatementFormat).filter_by(name=fmt_data["name"], is_builtin=True).first():
                db.add(StatementFormat(**fmt_data))
        db.commit()
    finally:
        db.close()


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
