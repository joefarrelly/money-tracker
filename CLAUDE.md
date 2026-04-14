# Money Tracker — Claude Instructions

## Project Overview
Personal finance tracker that consolidates:
- Bank statement PDF uploads (Barclays, Chase)
- Payslip PDF uploads (NordHealth / Provet Cloud format) with full line-item breakdown
- Salary records (manual entry)
- Auto-detected recurring expenses
- Disposable income calculation (salary net − recurring costs)

## Stack
- **Backend:** FastAPI + SQLAlchemy + SQLite (`backend/money_tracker.db`)
- **Frontend:** React + TypeScript + Vite + Tailwind CSS

## Running Locally

**Backend** (from `backend/`):
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Runs on `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

**Frontend** (from `frontend/`):
```bash
npm install
npm run dev
```
Runs on `http://localhost:5173`, proxies `/api` to the backend.

## Architecture

### Backend structure
```
backend/
  app.py            # FastAPI app, registers routers, startup hook
  models.py         # SQLAlchemy models (DeclarativeBase)
  schemas.py        # Pydantic request/response models
  database.py       # Engine, SessionLocal, get_db dependency, DB init + seeding
  routes/           # APIRouters: accounts, transactions, upload, salaries, categories, dashboard, settings
  parsers/
    universal.py    # Universal PDF parser: table extraction, column-role heuristics,
                    #   format matching, preview + confirm flow (replaces barclays.py/chase.py)
    payslip.py      # Payslip PDF parser: handles 3 table layouts, extracts line items + NI number
  services/         # recurring.py (auto-detection), summary.py (monthly summary + disposable income)
```

### Frontend structure
```
frontend/src/
  pages/            # Dashboard, Transactions, Upload, Recurring, Salaries, Settings
  api/client.ts     # Axios wrapper for all API calls
  types/index.ts    # Shared TypeScript types
```

## Key Decisions
- Transactions use a unified `amount` field: positive = money in, negative = money out.
- Duplicate detection on upload: `(account_id, date, description, amount)` tuple.
- Recurring detection: merchant normalisation + monthly cadence (20–40 day gaps, <20% amount variance, 3+ occurrences).
- Disposable income = net salary − sum of active recurring expense monthly costs.
- Payslip duplicate detection: `(date, ni_number)` at app level + partial unique DB index `WHERE ni_number IS NOT NULL`. Manual entries fall back to `(date, employer)`.
- NI number is the per-person identity key for payslips (supports multiple people, e.g. partners). Mapped to display names via `PersonIdentity` in Settings.

## PDF Parsing
The upload flow is a two-step preview → confirm pattern:
1. `POST /api/upload/preview` — saves temp file, extracts tables via camelot, scores column roles, tries to match a saved `StatementFormat`, returns a `PreviewResponse` with `preview_token`.
2. `POST /api/upload/confirm` — loads temp file by token, calls `parse_with_mapping` with the confirmed mapping, persists transactions, optionally saves the format for reuse.

The universal parser (`parsers/universal.py`) handles all banks. It scores tables by header quality × column efficiency to find the transaction table, then infers column roles (date, description, amount, money_in/out, balance). `total_rows` in the preview reflects the count across all matching pages, not just the first.

The original bank-specific parsing logic is in `C:/Users/Joe/Desktop/App/personal/ScrapeBanks/bank_app.py` (`process_barclays_pdf`, `process_chase_pdf`) — kept as reference but no longer used directly.

## StatementFormats
Built-in formats for Barclays and Chase are seeded on startup. User-defined formats are saved when "Save this format" is checked on confirm. `use_count` is bumped on each successful import. Schema migrations for new columns use `_migrate()` in `database.py` (PRAGMA table_info + ALTER TABLE — no Alembic).

## Payslip Parsing
`parsers/payslip.py` handles NordHealth / Provet Cloud payslips using camelot stream flavor (no Ghostscript needed). Handles 3 PDF layouts that this payroll system produces:
- 5-column: Description | Rate | Units Due | Amount | This Year
- 4-column: Description | Rate/Units (merged) | Amount | This Year
- 4-column merged: Description | Rate | Units | Amount+ThisYear (merged cell, split on `\n`)

NI number extracted from "NI Letter & No: A PB175845B" — strips the leading category letter, stores just the NI number (`PB175845B`). Earnings appear before the TOTAL row; deductions after.

Single upload: `POST /api/salaries/upload-payslip`. Bulk (one-time): `POST /api/salaries/bulk-upload-payslips`.

## Settings
`GET/PUT /api/settings/ni-numbers` — lists all NI numbers seen in payslips, create/update display name.
Accounts already have nickname support via `PATCH /api/accounts/{id}`.

## Dashboard Summary API
`GET /api/dashboard/summary?year=Y&month=M` returns an enriched `MonthlySummary`:
- `recurring_actuals` — for each active recurring expense, matches transactions in the month by merchant pattern substring, computes `actual_amount`, `found_this_month`, and `is_over` (>15% above monthly cost)
- `salary_entries[].line_items` — full payslip line items (earnings + deductions) included inline; empty for manual salary entries

`GET /api/dashboard/trend?months=N` returns N months of `MonthlySummary` (without `recurring_actuals`/`line_items` for performance).

Currency values are formatted to 2 decimal places throughout the frontend (`toLocaleString` with `minimumFractionDigits: 2`).
