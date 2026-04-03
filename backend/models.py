from datetime import datetime
from database import db


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    bank = db.Column(db.String(50), nullable=False)  # 'barclays', 'chase'
    account_number = db.Column(db.String(50), nullable=False, unique=True)
    nickname = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship("Transaction", back_populates="account", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "bank": self.bank,
            "account_number": self.account_number,
            "nickname": self.nickname or self.account_number,
            "created_at": self.created_at.isoformat(),
        }


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    color = db.Column(db.String(7), default="#6b7280")  # hex color
    icon = db.Column(db.String(50))

    transactions = db.relationship("Transaction", back_populates="category", lazy="dynamic")
    recurring_expenses = db.relationship("RecurringExpense", back_populates="category", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "icon": self.icon,
        }


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=False)
    # Positive = money in, negative = money out (unified amount field)
    amount = db.Column(db.Float, nullable=False)
    balance = db.Column(db.Float)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    is_recurring = db.Column(db.Boolean, default=False)
    source_file = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship("Account", back_populates="transactions")
    category = db.relationship("Category", back_populates="transactions")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "account": self.account.to_dict() if self.account else None,
            "date": self.date.isoformat(),
            "description": self.description,
            "amount": self.amount,
            "balance": self.balance,
            "category_id": self.category_id,
            "category": self.category.to_dict() if self.category else None,
            "is_recurring": self.is_recurring,
            "source_file": self.source_file,
            "created_at": self.created_at.isoformat(),
        }


class RecurringExpense(db.Model):
    __tablename__ = "recurring_expenses"

    id = db.Column(db.Integer, primary_key=True)
    merchant_pattern = db.Column(db.String(255), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    # Typical monthly amount (negative for expense)
    typical_amount = db.Column(db.Float, nullable=False)
    # 'monthly' or 'annual'
    frequency = db.Column(db.String(20), nullable=False, default="monthly")
    # Day of month it usually hits (1-31), null if irregular
    day_of_month = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    # Auto-detected or manually confirmed
    is_confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship("Category", back_populates="recurring_expenses")

    @property
    def monthly_cost(self):
        if self.frequency == "annual":
            return self.typical_amount / 12
        return self.typical_amount

    def to_dict(self):
        return {
            "id": self.id,
            "merchant_pattern": self.merchant_pattern,
            "category_id": self.category_id,
            "category": self.category.to_dict() if self.category else None,
            "typical_amount": self.typical_amount,
            "frequency": self.frequency,
            "day_of_month": self.day_of_month,
            "is_active": self.is_active,
            "is_confirmed": self.is_confirmed,
            "monthly_cost": self.monthly_cost,
            "created_at": self.created_at.isoformat(),
        }


class Salary(db.Model):
    __tablename__ = "salaries"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    gross_amount = db.Column(db.Float, nullable=True)
    net_amount = db.Column(db.Float, nullable=False)
    employer = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "gross_amount": self.gross_amount,
            "net_amount": self.net_amount,
            "employer": self.employer,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }
