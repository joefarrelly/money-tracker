import os
import tempfile

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename

from database import get_db
from models import Account, Transaction
from parsers import barclays, chase
from schemas import DetectBankResult, UploadResult

router = APIRouter()

ALLOWED_EXTENSIONS = {"pdf"}
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "uploads")


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_or_create_account(bank: str, account_number: str, db: Session) -> Account:
    acc = db.query(Account).filter_by(account_number=account_number).first()
    if not acc:
        acc = Account(bank=bank, account_number=account_number)
        db.add(acc)
        db.flush()
    return acc


def _persist_transactions(df, account_id: int, source_file: str, db: Session) -> dict:
    added = skipped = 0
    for _, row in df.iterrows():
        exists = db.query(Transaction).filter_by(
            account_id=account_id,
            date=row["date"].date(),
            description=row["description"],
            amount=round(float(row["amount"]), 2),
        ).first()

        if exists:
            skipped += 1
            continue

        db.add(Transaction(
            account_id=account_id,
            date=row["date"].date(),
            description=str(row["description"]),
            amount=round(float(row["amount"]), 2),
            balance=round(float(row["balance"]), 2) if row["balance"] else None,
            source_file=source_file,
        ))
        added += 1

    db.commit()
    return {"added": added, "skipped": skipped}


@router.post("/", response_model=UploadResult)
async def upload_statement(
    file: UploadFile,
    bank: str = Form(...),
    account_number: str = Form(...),
    year: int | None = Form(None),
    db: Session = Depends(get_db),
):
    if not file.filename or not _allowed(file.filename):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    bank = bank.strip().lower()
    account_number = account_number.strip()

    if not bank or not account_number:
        raise HTTPException(status_code=400, detail="bank and account_number are required")

    filename = secure_filename(file.filename)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    try:
        if bank == "barclays":
            detected_year = year or barclays.detect_year(filepath, filename)
            df = barclays.parse(filepath, detected_year)
        elif bank == "chase":
            df = chase.parse(filepath)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported bank: {bank}")

        account = _get_or_create_account(bank, account_number, db)
        result = _persist_transactions(df, account.id, filename, db)
        db.refresh(account)
        return UploadResult(added=result["added"], skipped=result["skipped"], account=account)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@router.get("/detect-bank", response_model=DetectBankResult)
def detect_bank(filename: str = ""):
    lower = filename.lower()
    if "barclays" in lower or lower.startswith("statement"):
        return DetectBankResult(bank="barclays")
    if "chase" in lower:
        return DetectBankResult(bank="chase")
    return DetectBankResult(bank=None)
