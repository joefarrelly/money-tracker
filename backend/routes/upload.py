import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename

from database import get_db
from models import Account, StatementFormat, Transaction
from parsers import universal
from schemas import (
    ColumnMapping,
    ConfirmUploadRequest,
    DetectBankResult,
    PreviewResponse,
    StatementFormatOut,
    UploadResult,
)

router = APIRouter()

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_DIR = os.path.join(_BASE, "uploads")
TMP_DIR = os.path.join(UPLOAD_DIR, "tmp")


def _ensure_dirs():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_account(bank: str, account_number: str, db: Session) -> Account:
    acc = db.query(Account).filter_by(account_number=account_number).first()
    if not acc:
        acc = Account(bank=bank, account_number=account_number)
        db.add(acc)
        db.flush()
    return acc


def _persist_transactions(df, account_id: int, source_file: str, db: Session) -> dict:
    added = skipped = 0
    new_txns = []
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
        bal = row.get("balance")
        txn = Transaction(
            account_id=account_id,
            date=row["date"].date(),
            description=str(row["description"]),
            amount=round(float(row["amount"]), 2),
            balance=round(float(bal), 2) if bal and bal == bal else None,
            source_file=source_file,
        )
        db.add(txn)
        new_txns.append(txn)
        added += 1
    db.commit()
    for txn in new_txns:
        db.refresh(txn)
    return {"added": added, "skipped": skipped, "transactions": new_txns}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/formats", response_model=list[StatementFormatOut])
def list_formats(db: Session = Depends(get_db)):
    return db.query(StatementFormat).order_by(
        StatementFormat.is_builtin.desc(),
        StatementFormat.use_count.desc(),
    ).all()


@router.post("/preview", response_model=PreviewResponse)
async def preview_upload(file: UploadFile, db: Session = Depends(get_db)):
    """
    Upload a PDF statement and get back a preview of the detected column mapping.
    The file is saved temporarily under a preview_token UUID.
    Call /confirm with the token (and any adjustments) to complete the import.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    _ensure_dirs()
    token = str(uuid.uuid4())
    tmp_path = os.path.join(TMP_DIR, f"{token}.pdf")

    contents = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(contents)

    try:
        saved_formats = db.query(StatementFormat).all()
        result = universal.extract_preview(tmp_path, filename=file.filename, saved_formats=saved_formats)
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=422, detail=str(e))

    matched_fmt = result.pop("matched_format")

    return PreviewResponse(
        preview_token=token,
        matched_format=matched_fmt,
        confidence=result["confidence"],
        column_headers=result["column_headers"],
        proposed_mapping=ColumnMapping(**result["proposed_mapping"]),
        detected_account_number=result["detected_account_number"],
        detected_year=result["detected_year"],
        needs_year=result["needs_year"],
        sample_rows=result["sample_rows"],
        total_rows=result["total_rows"],
    )


@router.post("/confirm", response_model=UploadResult)
def confirm_upload(body: ConfirmUploadRequest, db: Session = Depends(get_db)):
    """
    Confirm a previewed upload and import the transactions.
    Optionally saves the column mapping as a named format for future uploads.
    """
    tmp_path = os.path.join(TMP_DIR, f"{body.preview_token}.pdf")
    if not os.path.exists(tmp_path):
        raise HTTPException(status_code=404, detail="Preview not found or already used")

    mapping_dict = body.mapping.model_dump()
    year = body.year

    try:
        df = universal.parse_with_mapping(tmp_path, mapping_dict, year=year, skip_patterns=body.skip_patterns)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    if df.empty:
        raise HTTPException(status_code=422, detail="No transactions could be parsed from this file")

    # Infer a bank name from the format or account number
    bank_name = "unknown"
    if body.format_id:
        fmt = db.get(StatementFormat, body.format_id)
        if fmt:
            bank_name = fmt.name.lower()

    account = _get_or_create_account(bank_name, body.account_number, db)
    counts = _persist_transactions(df, account.id, body.preview_token, db)
    db.refresh(account)

    # Save format if requested
    if body.save_format and body.format_name:
        existing = db.query(StatementFormat).filter_by(name=body.format_name).first()
        if not existing:
            db.add(StatementFormat(
                name=body.format_name,
                column_headers=body.column_headers,
                **mapping_dict,
                is_builtin=False,
            ))
            db.commit()

    # Bump use_count on the matched format
    if body.format_id:
        fmt = db.get(StatementFormat, body.format_id)
        if fmt:
            fmt.use_count += 1
            fmt.last_used_at = datetime.utcnow()
            db.commit()

    return UploadResult(
        added=counts["added"],
        skipped=counts["skipped"],
        account=account,
        transactions=counts["transactions"],
    )


@router.get("/detect-bank", response_model=DetectBankResult)
def detect_bank(filename: str = ""):
    lower = filename.lower()
    if "barclays" in lower or lower.startswith("statement"):
        return DetectBankResult(bank="barclays")
    if "chase" in lower:
        return DetectBankResult(bank="chase")
    return DetectBankResult(bank=None)
