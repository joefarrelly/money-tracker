from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
from models import Salary
from schemas import SalaryCreate, SalaryOut, SalaryUpdate

router = APIRouter()


@router.get("/", response_model=list[SalaryOut])
def list_salaries(db: Session = Depends(get_db)):
    return db.query(Salary).order_by(Salary.date.desc()).all()


@router.post("/", response_model=SalaryOut, status_code=201)
def create_salary(body: SalaryCreate, db: Session = Depends(get_db)):
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
