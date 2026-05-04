import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import Account, EmailImport, PayslipLineItem, Salary, Transaction

router = APIRouter()


class EmailImportOut(BaseModel):
    id: int
    message_id: str
    subject: str | None
    sender: str | None
    received_at: datetime | None
    filename: str | None
    import_type: str | None
    status: str
    error_message: str | None
    raw_data: dict | None
    created_at: datetime
    imported_at: datetime | None

    class Config:
        from_attributes = True


class PollResult(BaseModel):
    new_imports: int
    message: str


@router.get("/", response_model=list[EmailImportOut])
def list_imports(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(EmailImport).order_by(EmailImport.received_at.desc())
    if status:
        q = q.filter(EmailImport.status == status)
    else:
        q = q.filter(EmailImport.status != "dismissed")
    return q.all()


@router.post("/poll", response_model=PollResult)
def trigger_poll(db: Session = Depends(get_db)):
    from services.email_poller import poll_emails
    try:
        count = poll_emails(db)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return PollResult(
        new_imports=count,
        message=f"Found {count} new import{'s' if count != 1 else ''}",
    )


@router.post("/{import_id}/confirm", response_model=EmailImportOut)
def confirm_import(import_id: int, db: Session = Depends(get_db)):
    record = db.get(EmailImport, import_id)
    if not record:
        raise HTTPException(status_code=404, detail="Import not found")
    if record.status != "pending":
        raise HTTPException(status_code=409, detail=f"Import is already {record.status}")
    if not record.raw_data:
        raise HTTPException(status_code=422, detail="No parsed data available")

    try:
        if record.import_type == "payslip":
            _confirm_payslip(record, db)
        elif record.import_type == "bank_statement":
            _confirm_bank_statement(record, db)
        else:
            raise HTTPException(status_code=422, detail="Unknown import type")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    record.status = "imported"
    record.imported_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    _cleanup_file(record.file_path)
    return record


@router.post("/{import_id}/skip", response_model=EmailImportOut)
def skip_import(import_id: int, db: Session = Depends(get_db)):
    record = db.get(EmailImport, import_id)
    if not record:
        raise HTTPException(status_code=404, detail="Import not found")
    record.status = "skipped"
    db.commit()
    db.refresh(record)
    _cleanup_file(record.file_path)
    return record


@router.delete("/{import_id}", response_model=EmailImportOut)
def dismiss_import(import_id: int, db: Session = Depends(get_db)):
    """Soft-delete: marks as dismissed so it's hidden and won't be re-imported on next poll."""
    record = db.get(EmailImport, import_id)
    if not record:
        raise HTTPException(status_code=404, detail="Import not found")
    _cleanup_file(record.file_path)
    record.status = "dismissed"
    db.commit()
    db.refresh(record)
    return record


# ── Internal helpers ──────────────────────────────────────────────────────────

def _confirm_payslip(record: EmailImport, db: Session):
    d = record.raw_data
    ni = d.get("ni_number") or None

    dup_q = db.query(Salary).filter(Salary.date == d["date"])
    if ni:
        dup_q = dup_q.filter(Salary.ni_number == ni)
    else:
        dup_q = dup_q.filter(Salary.employer == d.get("employer", ""))
    if dup_q.first():
        raise HTTPException(
            status_code=409,
            detail=f"Payslip for {d['date']} already exists",
        )

    salary = Salary(
        date=d["date"],
        employer=d.get("employer"),
        ni_number=ni,
        net_amount=d["net_pay"],
        gross_amount=d.get("gross_pay"),
        source_file=record.filename,
    )
    db.add(salary)
    db.flush()

    for item in d.get("line_items", []):
        db.add(PayslipLineItem(
            salary_id=salary.id,
            description=item["description"],
            rate=item.get("rate"),
            units=item.get("units"),
            amount=item["amount"],
            this_year_amount=item.get("this_year_amount"),
            line_type=item["line_type"],
        ))


def _confirm_bank_statement(record: EmailImport, db: Session):
    d = record.raw_data
    account_number = d.get("account_number") or "unknown"
    bank_name = d.get("bank_name") or "unknown"

    acc = db.query(Account).filter_by(account_number=account_number).first()
    if not acc:
        acc = Account(bank=bank_name, account_number=account_number)
        db.add(acc)
        db.flush()

    added = 0
    for txn in d.get("transactions", []):
        exists = db.query(Transaction).filter_by(
            account_id=acc.id,
            date=txn["date"],
            description=txn["description"],
            amount=txn["amount"],
        ).first()
        if not exists:
            db.add(Transaction(
                account_id=acc.id,
                date=txn["date"],
                description=txn["description"],
                amount=txn["amount"],
                balance=txn.get("balance"),
                source_file=record.filename,
            ))
            added += 1


def _cleanup_file(path: str | None):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
