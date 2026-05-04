# Money Tracker — Claude Instructions

## Project Overview
Personal finance tracker that consolidates:
- Bank statement PDF uploads (Barclays, Chase)
- Payslip PDF uploads (NordHealth / Provet Cloud format) with full line-item breakdown
- Auto-detected recurring expenses with category assignment
- Disposable income calculation (salary net − recurring costs)
- Transfer detection to exclude internal movements from totals

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
  routes/           # APIRouters: accounts, transactions, upload, salaries, categories, dashboard, settings, transfers
  parsers/
    universal.py    # Universal PDF parser: table extraction, column-role heuristics,
                    #   format matching, preview + confirm flow (replaces barclays.py/chase.py)
    payslip.py      # Payslip PDF parser: handles 3 table layouts, extracts line items + NI number
  services/         # recurring.py (auto-detection), summary.py (monthly summary + disposable income),
                    #   transfers.py (transfer candidate detection)
```

### Frontend structure
```
frontend/src/
  pages/            # Dashboard, Transactions, Upload, Recurring, Salaries, Settings, Transfers
  components/       # Shared components: Spinner
  api/client.ts     # fetch wrapper with 60s GET cache + auto-invalidate on mutations
  types/index.ts    # Shared TypeScript types
```

## Design System
- **Palette:** Tailwind `slate-*` throughout (blue-tinted dark, not pure gray)
- **Background:** `slate-950`, cards `slate-900`, inputs `slate-800`
- **Borders:** `slate-800` / `slate-700`
- **Accent:** indigo/violet — nav active state, buttons, spinner, gradient on logo
- **Stat cards:** coloured left border per meaning — emerald (salary), red (spent), sky (net flow), violet (savings rate)
- **Nav:** sticky, `slate-900/95` with backdrop blur; active item is indigo pill

## Key Decisions
- Transactions use a unified `amount` field: positive = money in, negative = money out.
- Duplicate detection on upload: `(account_id, date, description, amount)` tuple.
- Recurring detection: merchant normalisation + monthly cadence (20–40 day gaps, <20% amount variance, 3+ occurrences).
- Disposable income = net salary − sum of active recurring expense monthly costs.
- Payslip entry is upload-only (no manual form). Single: `POST /api/salaries/upload-payslip`. Bulk: `POST /api/salaries/bulk-upload-payslips`.
- Payslip duplicate detection: `(date, ni_number)` at app level + partial unique DB index `WHERE ni_number IS NOT NULL`.
- NI number is the per-person identity key for payslips (supports multiple people, e.g. partners). Mapped to display names via `PersonIdentity` in Settings.
- Transfer detection: transactions flagged `is_transfer=True` are excluded from monthly totals and category breakdowns so they don't inflate income/spending.

## API Response Cache (`api/client.ts`)
GET responses are cached in memory for 60 seconds keyed by URL. Any non-GET request via `request()` clears the whole cache. Raw fetch upload functions (`uploadPayslip`, `bulkUploadPayslips`, `bulkUpload`) also call `cache.clear()` on success. Export `invalidateCache()` for manual clearing if needed.

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

## Settings
`GET/PUT /api/settings/ni-numbers` — lists all NI numbers seen in payslips, create/update display name.
Accounts already have nickname support via `PATCH /api/accounts/{id}`.

## Dashboard Summary API
`GET /api/dashboard/summary?year=Y&month=M` returns an enriched `MonthlySummary`:
- `recurring_actuals` — for each active recurring expense, matches transactions in the month by merchant pattern substring, computes `actual_amount`, `found_this_month`, `is_over` (>15% above monthly cost), and `category_name`/`category_color`/`category_id`
- `salary_entries[].line_items` — full payslip line items (earnings + deductions) included inline

`GET /api/dashboard/trend?months=N` returns N months of `MonthlySummary` (default 12, without `recurring_actuals`/`line_items` for performance).

Dashboard fetches: current month summary, previous month summary, same-month-last-year summary (for YoY deltas), 12-month trend, and recent transactions — all in parallel.

Currency values are formatted to 2 decimal places throughout the frontend (`toLocaleString` with `minimumFractionDigits: 2`).

## Transactions API Filters
`GET /api/transactions/` supports: `search`, `category_id` (-1 = uncategorised/NULL), `account_id`, `year`, `month`, `amount_type` ("in"/"out"), `hide_transfers` (bool), `page`, `per_page`.

## Recurring Expenses
`RecurringExpense` has `category_id` — assign categories in the Recurring page. Dashboard recurring widget has two tabs:
- **This month** — found/pending/over status per item
- **By category** — monthly cost grouped by category with % of salary bars

## Transfer Detection
`services/transfers.py` scans all unreviewed transactions for candidate account-to-account transfers: negative on one account paired with a positive of the same amount (±£0.02) on a different account within ±2 days. Confidence score: 1.0 for same-day exact match, reduced by 0.15/day and proportional amount delta.

`routes/transfers.py` exposes:
- `GET /api/transfers/candidates` — unreviewed candidate pairs, sorted by confidence
- `POST /api/transfers/confirm` — marks both sides `is_transfer=True`, links them via `transfer_counterpart_id`
- `POST /api/transfers/ignore` — sets `transfer_ignored=True` on a transaction (hides it from candidates)
- `POST /api/transfers/unlink/{txn_id}` — clears transfer flags on both sides of a confirmed pair
- `GET /api/transfers/confirmed` — confirmed pairs, deduplicated, normalised so `txn_out` is always the negative side

Transaction model has three new fields: `is_transfer`, `transfer_counterpart_id`, `transfer_ignored`. Added via `_migrate()` in `database.py`.
