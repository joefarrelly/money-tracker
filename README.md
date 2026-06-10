# Money Tracker

Personal finance tracker. Upload bank statement PDFs, track payslips, and see your monthly disposable income after recurring expenses.

## Why I Built This

I was managing my personal finances across three separate tools — a Google Sheet for salary records, a Python script (ScrapeBanks) for parsing bank statement PDFs, and manual calculations for figuring out disposable income. Every month I'd repeat the same process across all three. This app consolidates them into one place.

## Features

- Upload bank statement PDFs (Barclays, Chase) — transactions parsed and deduplicated automatically
- Upload payslip PDFs (NordHealth / Provet Cloud) with full line-item breakdown
- Gmail IMAP polling — automatically imports statements and payslips sent to your inbox
- Auto-detection of recurring expenses from transaction history with category assignment
- Transfer detection — internal account movements excluded from totals
- Dashboard showing disposable income = net salary − recurring costs, with YoY comparisons and 12-month trend

## Stack

- **Backend:** Python / FastAPI / SQLAlchemy / SQLite
- **Frontend:** React / TypeScript / Vite / Tailwind CSS

## Setup

### With Docker (recommended)

```bash
docker compose up --build
```

Runs at `http://localhost:5004`.

### Without Docker

Backend:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python app.py
```
Runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

Frontend:
```bash
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:5173`.

### Email Import (optional)

Add to `backend/.env`:
```
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your-app-password
```

The app polls your inbox every 5 minutes and imports any PDF attachments it recognises as statements or payslips.
