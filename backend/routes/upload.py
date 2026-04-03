import os

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from database import db
from models import Account, Transaction
from parsers import barclays, chase

bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"pdf"}


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_or_create_account(bank: str, account_number: str) -> Account:
    acc = Account.query.filter_by(account_number=account_number).first()
    if not acc:
        acc = Account(bank=bank, account_number=account_number)
        db.session.add(acc)
        db.session.flush()
    return acc


def _persist_transactions(df, account_id: int, source_file: str) -> dict:
    """Insert parsed DataFrame rows, skipping duplicates."""
    added = skipped = 0
    for _, row in df.iterrows():
        exists = Transaction.query.filter_by(
            account_id=account_id,
            date=row["date"].date(),
            description=row["description"],
            amount=round(float(row["amount"]), 2),
        ).first()

        if exists:
            skipped += 1
            continue

        db.session.add(
            Transaction(
                account_id=account_id,
                date=row["date"].date(),
                description=str(row["description"]),
                amount=round(float(row["amount"]), 2),
                balance=round(float(row["balance"]), 2) if row["balance"] else None,
                source_file=source_file,
            )
        )
        added += 1

    db.session.commit()
    return {"added": added, "skipped": skipped}


@bp.post("/")
def upload_statement():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    bank = request.form.get("bank", "").strip().lower()
    account_number = request.form.get("account_number", "").strip()

    if not file.filename or not _allowed(file.filename):
        return jsonify({"error": "Only PDF files are supported"}), 400

    if not bank or not account_number:
        return jsonify({"error": "bank and account_number are required"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        if bank == "barclays":
            year_param = request.form.get("year", type=int)
            year = year_param or barclays.detect_year(filepath, filename)
            df = barclays.parse(filepath, year)
        elif bank == "chase":
            df = chase.parse(filepath)
        else:
            return jsonify({"error": f"Unsupported bank: {bank}"}), 400

        account = _get_or_create_account(bank, account_number)
        result = _persist_transactions(df, account.id, filename)
        result["account"] = account.to_dict()
        return jsonify(result), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@bp.get("/detect-bank")
def detect_bank_endpoint():
    """Accept a filename and return the detected bank (for UI pre-fill)."""
    filename = request.args.get("filename", "")
    filename_lower = filename.lower()

    if "barclays" in filename_lower or filename_lower.startswith("statement"):
        return jsonify({"bank": "barclays"})
    if "chase" in filename_lower:
        return jsonify({"bank": "chase"})

    return jsonify({"bank": None})
