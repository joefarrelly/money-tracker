from datetime import date, datetime
from typing import Literal, Optional

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
    is_transfer: bool = False
    transfer_counterpart_id: Optional[int] = None
    transfer_ignored: bool = False
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

class PayslipLineItemOut(BaseModel):
    id: int
    description: str
    rate: Optional[float] = None
    units: Optional[str] = None
    amount: float
    this_year_amount: Optional[float] = None
    line_type: str  # "earning" | "deduction"

    model_config = {"from_attributes": True}


class SalaryOut(BaseModel):
    id: int
    date: date
    gross_amount: Optional[float] = None
    net_amount: float
    employer: Optional[str] = None
    notes: Optional[str] = None
    ni_number: Optional[str] = None
    source_file: Optional[str] = None
    created_at: datetime
    line_items: list[PayslipLineItemOut] = []

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
    transactions: list[TransactionOut] = []


class DetectBankResult(BaseModel):
    bank: Optional[str] = None


# ── Statement formats ─────────────────────────────────────────────────────────

class StatementFormatOut(BaseModel):
    id: int
    name: str
    column_headers: list[str]
    date_col: Optional[int] = None
    description_col: Optional[int] = None
    date_description_col: Optional[int] = None
    balance_col: Optional[int] = None
    amount_style: str
    amount_col: Optional[int] = None
    money_in_col: Optional[int] = None
    money_out_col: Optional[int] = None
    date_format: str
    year_source: str
    is_builtin: bool
    use_count: int

    model_config = {"from_attributes": True}


class ColumnMapping(BaseModel):
    date_col: Optional[int] = None
    description_col: Optional[int] = None
    date_description_col: Optional[int] = None  # merged date+description column
    balance_col: Optional[int] = None
    amount_style: Literal["signed", "split"] = "signed"
    amount_col: Optional[int] = None
    money_in_col: Optional[int] = None
    money_out_col: Optional[int] = None
    date_format: str = "%d %b %Y"
    year_source: Literal["inline", "detect", "manual"] = "inline"


class PreviewResponse(BaseModel):
    preview_token: str
    matched_format: Optional[StatementFormatOut] = None
    confidence: float
    column_headers: list[str]
    proposed_mapping: ColumnMapping
    detected_account_number: Optional[str] = None
    detected_year: Optional[int] = None
    needs_year: bool
    sample_rows: list[list[str]]
    total_rows: int


class ConfirmUploadRequest(BaseModel):
    preview_token: str
    account_number: str
    mapping: ColumnMapping
    column_headers: list[str] = []  # raw headers from preview, needed if saving format
    year: Optional[int] = None
    skip_patterns: list[str] = []   # description substrings to exclude (e.g. "Opening balance")
    save_format: bool = False
    format_name: Optional[str] = None
    format_id: Optional[int] = None  # reference existing format to bump use_count


class BulkFileResult(BaseModel):
    filename: str
    added: int = 0
    skipped: int = 0
    error: Optional[str] = None
    note: Optional[str] = None  # e.g. "Used auto-detected mapping"


class BulkUploadResult(BaseModel):
    results: list[BulkFileResult]
    total_added: int
    total_skipped: int
    total_errors: int


# ── Person identities (NI number → display name) ─────────────────────────────

class PersonIdentityOut(BaseModel):
    id: int
    ni_number: str
    display_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PersonIdentityCreate(BaseModel):
    ni_number: str
    display_name: str


class PersonIdentityUpdate(BaseModel):
    display_name: str
