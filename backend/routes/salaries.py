import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from models import PayslipLineItem, Salary
from schemas import SalaryCreate, SalaryOut, SalaryUpdate

router = APIRouter()


@router.get("/", response_model=list[SalaryOut])
def list_salaries(db: Session = Depends(get_db)):
    return db.query(Salary).order_by(Salary.date.desc()).all()


@router.post("/", response_model=SalaryOut, status_code=201)
def create_salary(body: SalaryCreate, db: Session = Depends(get_db)):
    # Duplicate check: same date + employer (manual entries have no NI number)
    existing = db.query(Salary).filter(
        Salary.date == body.date,
        Salary.employer == (body.employer or ""),
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A payslip for {body.date} from '{body.employer}' already exists (id={existing.id})",
        )
    s = Salary(
        date=body.date,
        net_amount=body.net_amount,
        gross_amount=body.gross_amount,
        employer=body.employer,
        notes=body.notes,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.post("/bulk-upload-payslips")
async def bulk_upload_payslips(
    files: list[UploadFile] = File(...), db: Session = Depends(get_db)
):
    """Parse and import multiple payslip PDFs. Skips duplicates silently."""
    from parsers.payslip import parse_payslip_pdf

    results = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            results.append({"filename": file.filename or "", "status": "error", "detail": "Not a PDF"})
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        try:
            parsed = parse_payslip_pdf(tmp_path)
        except Exception as exc:
            results.append({"filename": file.filename, "status": "error", "detail": str(exc)})
            os.unlink(tmp_path)
            continue
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if parsed["date"] is None:
            results.append({"filename": file.filename, "status": "error", "detail": "Could not extract date"})
            continue

        ni = parsed.get("ni_number") or ""
        dup_query = db.query(Salary).filter(Salary.date == parsed["date"])
        if ni:
            dup_query = dup_query.filter(Salary.ni_number == ni)
        else:
            dup_query = dup_query.filter(Salary.employer == parsed["employer"])
        if dup_query.first():
            results.append({"filename": file.filename, "status": "skipped", "detail": "Already imported"})
            continue

        salary = Salary(
            date=parsed["date"],
            employer=parsed["employer"],
            ni_number=ni or None,
            net_amount=parsed["net_pay"],
            gross_amount=parsed["gross_pay"],
            source_file=file.filename,
        )
        db.add(salary)
        db.flush()

        for item in parsed["line_items"]:
            db.add(
                PayslipLineItem(
                    salary_id=salary.id,
                    description=item["description"],
                    rate=item["rate"],
                    units=item["units"],
                    amount=item["amount"],
                    this_year_amount=item["this_year_amount"],
                    line_type=item["line_type"],
                )
            )

        db.commit()
        results.append({"filename": file.filename, "status": "imported", "date": str(parsed["date"]), "net": parsed["net_pay"]})

    imported = sum(1 for r in results if r["status"] == "imported")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")
    return {"results": results, "imported": imported, "skipped": skipped, "errors": errors}


@router.post("/upload-payslip", response_model=SalaryOut, status_code=201)
async def upload_payslip(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Parse a payslip PDF and store it with full line items."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Write to a temp file so camelot can read it
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        from parsers.payslip import parse_payslip_pdf

        try:
            parsed = parse_payslip_pdf(tmp_path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not parse payslip: {exc}")

        if parsed["date"] is None:
            raise HTTPException(status_code=422, detail="Could not extract date from payslip")

        ni = parsed.get("ni_number") or ""

        # Duplicate check: same date + NI number (or employer if NI missing)
        dup_query = db.query(Salary).filter(Salary.date == parsed["date"])
        if ni:
            dup_query = dup_query.filter(Salary.ni_number == ni)
        else:
            dup_query = dup_query.filter(Salary.employer == parsed["employer"])
        existing = dup_query.first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Payslip for {parsed['date']} already exists (id={existing.id})",
            )

        salary = Salary(
            date=parsed["date"],
            employer=parsed["employer"],
            ni_number=ni or None,
            net_amount=parsed["net_pay"],
            gross_amount=parsed["gross_pay"],
            source_file=file.filename,
        )
        db.add(salary)
        db.flush()  # get salary.id without committing

        for item in parsed["line_items"]:
            db.add(
                PayslipLineItem(
                    salary_id=salary.id,
                    description=item["description"],
                    rate=item["rate"],
                    units=item["units"],
                    amount=item["amount"],
                    this_year_amount=item["this_year_amount"],
                    line_type=item["line_type"],
                )
            )

        db.commit()
        db.refresh(salary)
        return salary

    finally:
        os.unlink(tmp_path)


@router.patch("/{salary_id}", response_model=SalaryOut)
def update_salary(salary_id: int, body: SalaryUpdate, db: Session = Depends(get_db)):
    s = db.get(Salary, salary_id)
    if not s:
        raise HTTPException(status_code=404, detail="Salary not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{salary_id}", status_code=204)
def delete_salary(salary_id: int, db: Session = Depends(get_db)):
    s = db.get(Salary, salary_id)
    if not s:
        raise HTTPException(status_code=404, detail="Salary not found")
    db.delete(s)
    db.commit()
    return Response(status_code=204)
