import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Account, Transaction, UserParserTemplate
from parsers import universal
from schemas import (
    BulkFileResult,
    BulkUploadResult,
    ColumnMapping,
    ConfirmUploadRequest,
    PreviewResponse,
    UploadResult,
)

router = APIRouter()

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_DIR = os.path.join(_BASE, "uploads")
TMP_DIR = os.path.join(UPLOAD_DIR, "tmp")


def _ensure_dirs():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)


def _get_or_create_account(
    bank: str, account_number: str, user_email: str, db: Session
) -> Account:
    acc = (
        db.query(Account)
        .filter_by(account_number=account_number, user_email=user_email)
        .first()
    )
    if not acc:
        acc = Account(bank=bank, account_number=account_number, user_email=user_email)
        db.add(acc)
        db.flush()
    return acc


def _persist_transactions(df, account_id: int, source_file: str, db: Session) -> dict:
    added = skipped = 0
    new_txns = []
    for _, row in df.iterrows():
        exists = (
            db.query(Transaction)
            .filter_by(
                account_id=account_id,
                date=row["date"].date(),
                description=row["description"],
                amount=round(float(row["amount"]), 2),
            )
            .first()
        )
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


def _file_type(filename: str) -> str:
    return "csv" if (filename or "").lower().endswith(".csv") else "pdf"


@router.post("/preview", response_model=PreviewResponse)
async def preview_upload(
    file: UploadFile = File(...),
    template_id: Optional[int] = Form(None),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a statement file and get back a preview of the detected column mapping.
    Pass template_id to apply a saved template's mapping instead of auto-detecting.
    The file is saved temporarily under a preview_token UUID; call /confirm to import.
    """
    filename = file.filename or ""
    ft = _file_type(filename)
    if ft not in ("pdf", "csv"):
        raise HTTPException(
            status_code=400, detail="Only PDF and CSV files are supported"
        )

    _ensure_dirs()
    token = str(uuid.uuid4())
    suffix = ".csv" if ft == "csv" else ".pdf"
    tmp_path = os.path.join(TMP_DIR, f"{token}{suffix}")

    contents = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(contents)

    template = None
    if template_id is not None:
        template = (
            db.query(UserParserTemplate)
            .filter_by(id=template_id, user_email=current_user)
            .first()
        )
        if not template:
            os.remove(tmp_path)
            raise HTTPException(status_code=404, detail="Template not found")

    try:
        result = universal.extract_preview(
            tmp_path, filename=filename, file_type=ft, template=template
        )
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=422, detail=str(e))

    return PreviewResponse(
        preview_token=token,
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
def confirm_upload(
    body: ConfirmUploadRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm a previewed upload and import the transactions."""
    # Find temp file (could be .pdf or .csv)
    tmp_path = None
    for suffix in (".pdf", ".csv"):
        candidate = os.path.join(TMP_DIR, f"{body.preview_token}{suffix}")
        if os.path.exists(candidate):
            tmp_path = candidate
            break
    if not tmp_path:
        raise HTTPException(status_code=404, detail="Preview not found or already used")

    ft = _file_type(tmp_path)
    mapping_dict = body.mapping.model_dump()

    template = None
    if body.template_id is not None:
        template = (
            db.query(UserParserTemplate)
            .filter_by(id=body.template_id, user_email=current_user)
            .first()
        )

    table_index = template.table_index if template else None

    try:
        df = universal.parse_with_mapping(
            tmp_path,
            mapping_dict,
            year=body.year,
            skip_patterns=body.skip_patterns,
            file_type=ft,
            table_index=table_index,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    if df.empty:
        raise HTTPException(
            status_code=422, detail="No transactions could be parsed from this file"
        )

    bank_name = template.name.lower() if template else "unknown"
    account = _get_or_create_account(bank_name, body.account_number, current_user, db)
    counts = _persist_transactions(df, account.id, body.preview_token, db)
    db.refresh(account)

    return UploadResult(
        added=counts["added"],
        skipped=counts["skipped"],
        account=account,
        transactions=counts["transactions"],
    )


@router.post("/detect-account")
async def detect_account(file: UploadFile):
    """Lightweight endpoint: extract account number from first pages of a PDF."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    _ensure_dirs()
    tmp_path = os.path.join(TMP_DIR, f"{uuid.uuid4()}.pdf")
    try:
        contents = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(contents)
        text = universal._extract_text(tmp_path)
        account_number = universal.detect_account_number(text)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {"account_number": account_number}


@router.post("/bulk", response_model=BulkUploadResult)
async def bulk_upload(
    files: list[UploadFile] = File(...),
    template_id: int = Form(...),
    account_number: str = Form(...),
    year: Optional[int] = Form(None),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import multiple statement files at once using a saved template."""
    template = (
        db.query(UserParserTemplate)
        .filter_by(id=template_id, user_email=current_user)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    mapping_dict = {
        "date_col": template.date_col,
        "description_col": template.description_col,
        "date_description_col": template.date_description_col,
        "balance_col": template.balance_col,
        "amount_style": template.amount_style,
        "amount_col": template.amount_col,
        "money_in_col": template.money_in_col,
        "money_out_col": template.money_out_col,
        "date_format": template.date_format or "%d %b %Y",
        "year_source": template.year_source or "inline",
    }
    parsed_year = year if template.year_source == "manual" else None
    skip_patterns = template.skip_patterns or []
    account = _get_or_create_account(
        template.name.lower(), account_number, current_user, db
    )

    _ensure_dirs()
    results: list[BulkFileResult] = []

    for upload in files:
        filename = upload.filename or "unknown"
        ft = _file_type(filename)
        if ft not in ("pdf", "csv"):
            results.append(BulkFileResult(filename=filename, error="Not a PDF or CSV"))
            continue

        suffix = ".csv" if ft == "csv" else ".pdf"
        tmp_path = os.path.join(TMP_DIR, f"{uuid.uuid4()}{suffix}")
        try:
            contents = await upload.read()
            with open(tmp_path, "wb") as f:
                f.write(contents)

            df = universal.parse_with_mapping(
                tmp_path,
                mapping_dict,
                year=parsed_year,
                skip_patterns=skip_patterns,
                file_type=ft,
                table_index=template.table_index,
            )

            if df.empty:
                results.append(
                    BulkFileResult(
                        filename=filename,
                        error="No transactions found — try uploading individually via Single tab",
                    )
                )
                continue

            counts = _persist_transactions(
                df, account.id, os.path.basename(tmp_path), db
            )
            results.append(
                BulkFileResult(
                    filename=filename,
                    added=counts["added"],
                    skipped=counts["skipped"],
                )
            )
        except Exception as e:
            results.append(BulkFileResult(filename=filename, error=str(e)))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return BulkUploadResult(
        results=results,
        total_added=sum(r.added for r in results),
        total_skipped=sum(r.skipped for r in results),
        total_errors=sum(1 for r in results if r.error is not None),
    )
