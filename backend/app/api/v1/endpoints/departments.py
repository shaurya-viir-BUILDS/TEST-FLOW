from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role
from app.models.department import Department
from app.models.employee import Employee, RoleEnum
from app.schemas.department import DepartmentCreate, DepartmentResponse

router = APIRouter()


@router.get("/", response_model=List[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    return db.query(Department).order_by(Department.name).all()


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    dept_in: DepartmentCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.HR_OFFICER]))
):
    existing = db.query(Department).filter(
        (Department.name == dept_in.name) | (Department.code == dept_in.code.upper())
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department with this name or code already exists."
        )

    dept = Department(
        name=dept_in.name.strip(),
        code=dept_in.code.strip().upper()
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

