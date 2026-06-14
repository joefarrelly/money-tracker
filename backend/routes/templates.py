import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import UserParserTemplate
from schemas import (
    ExtractTablesResponse,
    UserParserTemplateCreate,
    UserParserTemplateOut,
)

router = APIRouter()

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TMP_DIR = os.path.join(_BASE, "uploads", "tmp")


@router.get("/", response_model=list[UserParserTemplateOut])
def list_templates(
    template_type: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(UserParserTemplate).filter_by(user_email=current_user)
    if template_type:
        q = q.filter(UserParserTemplate.template_type == template_type)
    return q.order_by(UserParserTemplate.name).all()


@router.post("/", response_model=UserParserTemplateOut, status_code=201)
def create_template(
    body: UserParserTemplateCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tmpl = UserParserTemplate(user_email=current_user, **body.model_dump())
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.put("/{template_id}", response_model=UserParserTemplateOut)
def update_template(
    template_id: int,
    body: UserParserTemplateCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tmpl = (
        db.query(UserParserTemplate)
        .filter_by(id=template_id, user_email=current_user)
        .first()
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    for k, v in body.model_dump().items():
        setattr(tmpl, k, v)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: int,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tmpl = (
        db.query(UserParserTemplate)
        .filter_by(id=template_id, user_email=current_user)
        .first()
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tmpl)
    db.commit()


@router.post("/extract-tables", response_model=ExtractTablesResponse)
async def extract_tables(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
):
    """
    Upload a sample file (PDF or CSV) and get back all extracted tables with
    their headers and sample rows. Used during template creation.
    """
    filename = file.filename or ""
    is_csv = filename.lower().endswith(".csv")
    is_pdf = filename.lower().endswith(".pdf")

    if not is_csv and not is_pdf:
        raise HTTPException(
            status_code=400, detail="Only PDF and CSV files are supported"
        )

    os.makedirs(TMP_DIR, exist_ok=True)
    suffix = ".csv" if is_csv else ".pdf"
    tmp_path = os.path.join(TMP_DIR, f"{uuid.uuid4()}{suffix}")

    try:
        contents = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(contents)

        from parsers import universal

        file_type = "csv" if is_csv else "pdf"
        raw_tables = universal.extract_all_tables(tmp_path, file_type=file_type)

        detected_account = None
        if not is_csv:
            text = universal._extract_text(tmp_path)
            detected_account = universal.detect_account_number(text)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return ExtractTablesResponse(
        tables=raw_tables,
        detected_account_number=detected_account,
    )
