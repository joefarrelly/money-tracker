from datetime import datetime, date as date_type
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    bank = Column(String(50), nullable=False)
    account_number = Column(String(50), nullable=False, unique=True)
    nickname = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="account", lazy="dynamic")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    color = Column(String(7), default="#6b7280")
    icon = Column(String(50))

    transactions = relationship("Transaction", back_populates="category", lazy="dynamic")
    recurring_expenses = relationship("RecurringExpense", back_populates="category", lazy="dynamic")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    balance = Column(Float)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    is_recurring = Column(Boolean, default=False)
    source_file = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id = Column(Integer, primary_key=True)
    merchant_pattern = Column(String(255), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    typical_amount = Column(Float, nullable=False)
    frequency = Column(String(20), nullable=False, default="monthly")
    day_of_month = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    is_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="recurring_expenses")

    @property
    def monthly_cost(self):
        if self.frequency == "annual":
            return self.typical_amount / 12
        return self.typical_amount


class Salary(Base):
    __tablename__ = "salaries"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    gross_amount = Column(Float, nullable=True)
    net_amount = Column(Float, nullable=False)
    employer = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
