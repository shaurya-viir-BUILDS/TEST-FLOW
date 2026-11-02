from typing import Optional
from pydantic import BaseModel
from app.models.employee import RoleEnum


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserMeResponse"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None


class UserMeResponse(BaseModel):
    id: int
    emp_code: str
    first_name: str
    last_name: str
    email: str
    role: RoleEnum
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    is_active: bool


# Resolve forward ref
TokenResponse.model_rebuild()

