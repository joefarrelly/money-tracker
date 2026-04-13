from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ── Account ──────────────────────────────────────────────────────────────────

class AccountOut(BaseModel):
    id: int
    bank: str
    account_number: str
    nickname: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _nickname_fallback(self):
        if not self.nickname:
            self.nickname = self.account_number
        return self


class AccountUpdate(BaseModel):
    nickname: str


# ── Category ─────────────────────────────────────────────────────────────────

class CategoryOut(BaseModel):
    id: int
    name: str
    color: str
    icon: Optional[str] = None

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str
    color: str = "#6b7280"
    icon: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


# ── Transaction ───────────────────────────────────────────────────────────────

class TransactionOut(BaseModel):
    id: int
    account_id: int
    account: Optional[AccountOut] = None
    date: date
    description: str
    amount: float
    balance: Optional[float] = None
    category_id: Optional[int] = None
    category: Optional[CategoryOut] = None
    is_recurring: bool
    source_file: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionUpdate(BaseModel):
    category_id: Optional[int] = None
    is_recurring: Optional[bool] = None


class BulkCategoriseRequest(BaseModel):
    pattern: str
    category_id: int


class BulkCategoriseResponse(BaseModel):
    updated: int


class TransactionPage(BaseModel):
    transactions: list[TransactionOut]
    total: int
    page: int
    pages: int
    per_page: int


# ── Salary ────────────────────────────────────────────────────────────────────

class SalaryOut(BaseModel):
    id: int
    date: date
    gross_amount: Optional[float] = None
    net_amount: float
    employer: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SalaryCreate(BaseModel):
    date: date
    net_amount: float
    gross_amount: Optional[float] = None
    employer: Optional[str] = ""
    notes: Optional[str] = ""


class SalaryUpdate(BaseModel):
    date: Optional[date] = None
    net_amount: Optional[float] = None
    gross_amount: Optional[float] = None
    employer: Optional[str] = None
    notes: Optional[str] = None


# ── Recurring expense ─────────────────────────────────────────────────────────

class RecurringExpenseOut(BaseModel):
    id: int
    merchant_pattern: str
    category_id: Optional[int] = None
    category: Optional[CategoryOut] = None
    typical_amount: float
    frequency: str
    day_of_month: Optional[int] = None
    is_active: bool
    is_confirmed: bool
    monthly_cost: float
    created_at: datetime

    model_config = {"from_attributes": True}


class RecurringExpenseUpdate(BaseModel):
    is_confirmed: Optional[bool] = None
    is_active: Optional[bool] = None
    category_id: Optional[int] = None
    typical_amount: Optional[float] = None


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadResult(BaseModel):
    added: int
    skipped: int
    account: AccountOut


class DetectBankResult(BaseModel):
    bank: Optional[str] = None
