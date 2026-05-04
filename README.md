# Money Tracker

Personal finance tracker. Upload Barclays and Chase PDF statements, track salaries, and see your monthly disposable income after recurring expenses.

## Why I Built This

I was managing my personal finances across three separate tools — a Google Sheet for salary records, a Python script (ScrapeBanks) for parsing bank statement PDFs, and manual calculations for figuring out disposable income. Every month I'd repeat the same process across all three. This app consolidates them into one place: upload a statement, see your transactions, and get an up-to-date disposable income figure automatically.

## Features

- Upload bank statement PDFs (Barclays, Chase) — transactions parsed and deduplicated automatically
- Manual salary records with net/gross amounts
- Auto-detection of recurring expenses from transaction history
- Dashboard showing disposable income = net salary − recurring costs

## Stack

- **Backend:** Python / FastAPI / SQLAlchemy / SQLite
- **Frontend:** React / TypeScript / Vite / Tailwind CSS

## Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python app.py
```

Runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`.
