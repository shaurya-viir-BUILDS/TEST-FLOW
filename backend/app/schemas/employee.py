from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.employee import RoleEnum


class EmployeeBase(BaseModel):
    emp_code: str
    first_name: str
    last_name: str
    email: EmailStr
    role: RoleEnum
    department_id: Optional[int] = None
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    password: str


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[RoleEnum] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    id: int
    created_at: datetime
    department_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

