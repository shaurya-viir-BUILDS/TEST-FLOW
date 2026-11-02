from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, get_current_user
from app.core.security import get_password_hash
from app.models.department import Department
from app.models.employee import Employee, RoleEnum
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse

router = APIRouter()


@router.get("/", response_model=List[EmployeeResponse])
def list_employees(
    department_id: Optional[int] = None,
    role: Optional[RoleEnum] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    query = db.query(Employee)
    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)
    if role is not None:
        query = query.filter(Employee.role == role)
    if is_active is not None:
        query = query.filter(Employee.is_active == is_active)

    employees = query.order_by(Employee.id).offset(skip).limit(limit).all()

    # Enrich with department name
    result = []
    for emp in employees:
        resp = EmployeeResponse.model_validate(emp)
        resp.department_name = emp.department.name if emp.department else None
        result.append(resp)
    return result


@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    emp_in: EmployeeCreate,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.HR_OFFICER]))
):
    # Only Super Admin can create accounts with Super Admin role
    if emp_in.role == RoleEnum.SUPER_ADMIN and _current_user.role != RoleEnum.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can assign the Super Admin role."
        )

    # Check duplicate email
    if db.query(Employee).filter(Employee.email == emp_in.email.lower().strip()).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee with this email already exists."
        )

    # Check duplicate emp_code
    if db.query(Employee).filter(Employee.emp_code == emp_in.emp_code.strip().upper()).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee with this employee code already exists."
        )

    # Check department if provided
    dept_name = None
    if emp_in.department_id:
        dept = db.query(Department).filter(Department.id == emp_in.department_id).first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department with id {emp_in.department_id} not found."
            )
        dept_name = dept.name

    employee = Employee(
        emp_code=emp_in.emp_code.strip().upper(),
        first_name=emp_in.first_name.strip(),
        last_name=emp_in.last_name.strip(),
        email=emp_in.email.lower().strip(),
        password_hash=get_password_hash(emp_in.password),
        role=emp_in.role,
        department_id=emp_in.department_id,
        is_active=emp_in.is_active
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)

    resp = EmployeeResponse.model_validate(employee)
    resp.department_name = dept_name
    return resp


@router.get("/{id}", response_model=EmployeeResponse)
def get_employee(
    id: int,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    employee = db.query(Employee).filter(Employee.id == id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id {id} not found."
        )
    resp = EmployeeResponse.model_validate(employee)
    resp.department_name = employee.department.name if employee.department else None
    return resp


@router.put("/{id}", response_model=EmployeeResponse)
def update_employee(
    id: int,
    emp_in: EmployeeUpdate,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.HR_OFFICER]))
):
    employee = db.query(Employee).filter(Employee.id == id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id {id} not found."
        )

    # Non-super-admins cannot edit a Super Admin account
    if employee.role == RoleEnum.SUPER_ADMIN and _current_user.role != RoleEnum.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can modify a Super Admin account."
        )

    # Cannot modify own role (e.g., HR self-promotion to Super Admin)
    if emp_in.role is not None:
        if emp_in.role == RoleEnum.SUPER_ADMIN and _current_user.role != RoleEnum.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admin can grant the Super Admin role."
            )
        if employee.id == _current_user.id and emp_in.role != _current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees are not permitted to modify their own role."
            )

    if emp_in.email is not None:
        email_clean = emp_in.email.lower().strip()
        existing = db.query(Employee).filter(Employee.email == email_clean, Employee.id != id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already used by another employee.")
        employee.email = email_clean

    if emp_in.first_name is not None:
        employee.first_name = emp_in.first_name.strip()
    if emp_in.last_name is not None:
        employee.last_name = emp_in.last_name.strip()
    if emp_in.role is not None:
        employee.role = emp_in.role
    if emp_in.is_active is not None:
        employee.is_active = emp_in.is_active
    if emp_in.department_id is not None:
        dept = db.query(Department).filter(Department.id == emp_in.department_id).first()
        if not dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
        employee.department_id = emp_in.department_id
    if emp_in.password:
        employee.password_hash = get_password_hash(emp_in.password)

    db.commit()
    db.refresh(employee)

    resp = EmployeeResponse.model_validate(employee)
    resp.department_name = employee.department.name if employee.department else None
    return resp

