from datetime import datetime, date as date_type
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
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
    is_transfer = Column(Boolean, default=False)
    transfer_counterpart_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    transfer_ignored = Column(Boolean, default=False)
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


class PersonIdentity(Base):
    __tablename__ = "person_identities"

    id = Column(Integer, primary_key=True)
    ni_number = Column(String(20), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Salary(Base):
    __tablename__ = "salaries"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    gross_amount = Column(Float, nullable=True)
    net_amount = Column(Float, nullable=False)
    employer = Column(String(255))
    notes = Column(Text)
    ni_number = Column(String(20), nullable=True)
    source_file = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    line_items = relationship(
        "PayslipLineItem", back_populates="salary", cascade="all, delete-orphan"
    )


class PayslipLineItem(Base):
    __tablename__ = "payslip_line_items"

    id = Column(Integer, primary_key=True)
    salary_id = Column(Integer, ForeignKey("salaries.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(255), nullable=False)
    rate = Column(Float, nullable=True)
    units = Column(String(100), nullable=True)
    amount = Column(Float, nullable=False)
    this_year_amount = Column(Float, nullable=True)
    line_type = Column(String(20), nullable=False)  # "earning" | "deduction"

    salary = relationship("Salary", back_populates="line_items")


class StatementFormat(Base):
    """
    Saved column mapping for a bank statement format.
    Built-in entries seed Barclays and Chase; users can save their own.
    """
    __tablename__ = "statement_formats"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

    # Raw column header strings as they appear in the PDF (used for auto-matching)
    column_headers = Column(JSON, nullable=False)

    # Column indices (0-based) for each role
    date_col = Column(Integer, nullable=False)
    description_col = Column(Integer, nullable=False)
    balance_col = Column(Integer, nullable=True)

    # "split" = separate money_in / money_out columns (e.g. Barclays)
    # "signed" = single amount column with +/- prefix (e.g. Chase)
    amount_style = Column(String(10), nullable=False)
    amount_col = Column(Integer, nullable=True)           # for "signed"
    money_in_col = Column(Integer, nullable=True)         # for "split"
    money_out_col = Column(Integer, nullable=True)        # for "split"
    date_description_col = Column(Integer, nullable=True) # merged date+description column

    # Date parsing
    date_format = Column(String(30), nullable=False)          # e.g. "%d %b" or "%d %b %Y"
    year_source = Column(String(20), nullable=False, default="inline")  # "inline"|"detect"|"manual"

    is_builtin = Column(Boolean, default=False)
    use_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
