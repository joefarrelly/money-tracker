from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
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

    transactions = relationship(
        "Transaction", back_populates="category", lazy="dynamic"
    )
    recurring_expenses = relationship(
        "RecurringExpense", back_populates="category", lazy="dynamic"
    )


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
    transfer_counterpart_id = Column(
        Integer, ForeignKey("transactions.id"), nullable=True
    )
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
    salary_id = Column(
        Integer, ForeignKey("salaries.id", ondelete="CASCADE"), nullable=False
    )
    description = Column(String(255), nullable=False)
    rate = Column(Float, nullable=True)
    units = Column(String(100), nullable=True)
    amount = Column(Float, nullable=False)
    this_year_amount = Column(Float, nullable=True)
    line_type = Column(String(20), nullable=False)  # "earning" | "deduction"

    salary = relationship("Salary", back_populates="line_items")


class EmailImport(Base):
    __tablename__ = "email_imports"

    id = Column(Integer, primary_key=True)
    message_id = Column(String(500), unique=True, nullable=False)
    subject = Column(String(500))
    sender = Column(String(255))
    received_at = Column(DateTime)
    filename = Column(String(255))
    import_type = Column(String(20))  # "payslip" | "bank_statement"
    status = Column(
        String(20), default="pending"
    )  # "pending" | "imported" | "skipped" | "failed"
    error_message = Column(Text)
    file_path = Column(String(500))
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    imported_at = Column(DateTime)


class UserEmailConfig(Base):
    __tablename__ = "user_email_configs"

    user_email = Column(String(255), primary_key=True)
    app_password = Column(String(255), nullable=False)
    label = Column(String(100), default="INBOX")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class UserParserTemplate(Base):
    """User-defined column mapping for parsing bank statements or payslips."""

    __tablename__ = "user_parser_templates"

    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    template_type = Column(String(20), nullable=False)  # "statement" | "payslip"
    file_type = Column(String(10), nullable=False, default="pdf")  # "pdf" | "csv"

    # Which extracted table to use (0-based; None = auto-select best)
    table_index = Column(Integer, nullable=True)

    # Column headers from the sample file, stored for display in the editor
    column_headers = Column(JSON, nullable=True)

    # Column role assignments (0-based indices)
    date_col = Column(Integer, nullable=True)
    description_col = Column(Integer, nullable=True)
    date_description_col = Column(Integer, nullable=True)
    balance_col = Column(Integer, nullable=True)
    # "split" = separate money_in / money_out columns; "signed" = single signed column
    amount_style = Column(String(10), nullable=False, default="signed")
    amount_col = Column(Integer, nullable=True)
    money_in_col = Column(Integer, nullable=True)
    money_out_col = Column(Integer, nullable=True)
    date_format = Column(String(30), nullable=True, default="%d %b %Y")
    year_source = Column(String(20), nullable=True, default="inline")

    # Description substrings that cause a row to be skipped (e.g. "Opening balance")
    skip_patterns = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
