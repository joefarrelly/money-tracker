# Money Tracker

Personal finance tracker. Upload Barclays and Chase PDF statements, track salaries, and see your monthly disposable income after recurring expenses.

## Features

- Upload bank statement PDFs (Barclays, Chase) — transactions parsed and deduplicated automatically
- Manual salary records with net/gross amounts
- Auto-detection of recurring expenses from transaction history
- Dashboard showing disposable income = net salary − recurring costs

## Stack

- **Backend:** Python / Flask / SQLAlchemy / SQLite
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

Runs at `http://localhost:5000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`.
