# Money Tracker — Claude Instructions

## Project Overview
Personal finance tracker that consolidates:
- Bank statement PDF uploads (Barclays, Chase)
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
  routes/           # APIRouters: accounts, transactions, upload, salaries, categories, dashboard
  parsers/
    universal.py    # Universal PDF parser: table extraction, column-role heuristics,
                    #   format matching, preview + confirm flow (replaces barclays.py/chase.py)
  services/         # recurring.py (auto-detection), summary.py (disposable income)
```

### Frontend structure
```
frontend/src/
  pages/            # Dashboard, Transactions, Upload, Recurring, Salaries
  api/client.ts     # Axios wrapper for all API calls
  types/index.ts    # Shared TypeScript types
```

## Key Decisions
- Transactions use a unified `amount` field: positive = money in, negative = money out.
- Duplicate detection on upload: `(account_id, date, description, amount)` tuple.
- Recurring detection: merchant normalisation + monthly cadence (20–40 day gaps, <20% amount variance, 3+ occurrences).
- Disposable income = net salary − sum of active recurring expense monthly costs.

## PDF Parsing
The upload flow is a two-step preview → confirm pattern:
1. `POST /api/upload/preview` — saves temp file, extracts tables via camelot, scores column roles, tries to match a saved `StatementFormat`, returns a `PreviewResponse` with `preview_token`.
2. `POST /api/upload/confirm` — loads temp file by token, calls `parse_with_mapping` with the confirmed mapping, persists transactions, optionally saves the format for reuse.

The universal parser (`parsers/universal.py`) handles all banks. It scores tables by header quality × column efficiency to find the transaction table, then infers column roles (date, description, amount, money_in/out, balance). `total_rows` in the preview reflects the count across all matching pages, not just the first.

The original bank-specific parsing logic is in `C:/Users/Joe/Desktop/App/personal/ScrapeBanks/bank_app.py` (`process_barclays_pdf`, `process_chase_pdf`) — kept as reference but no longer used directly.

## StatementFormats
Built-in formats for Barclays and Chase are seeded on startup. User-defined formats are saved when "Save this format" is checked on confirm. `use_count` is bumped on each successful import. Schema migrations for new columns use `_migrate()` in `database.py` (PRAGMA table_info + ALTER TABLE — no Alembic).
