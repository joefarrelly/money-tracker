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
Runs on `http://localhost:5000`. Interactive API docs at `http://localhost:5000/docs`.

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
  parsers/          # PDF parsers: barclays.py, chase.py
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
The canonical parsing logic lives in `C:/Users/Joe/Desktop/App/personal/ScrapeBanks/bank_app.py` (`process_barclays_pdf`, `process_chase_pdf`). Check there before rewriting any parser logic.
