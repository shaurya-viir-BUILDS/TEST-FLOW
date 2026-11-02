from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.models.employee import Employee
from app.schemas.auth import LoginRequest, TokenResponse, UserMeResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.email == login_data.email.lower().strip()).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is currently inactive"
        )

    access_token = create_access_token(subject=user.id, role=user.role.value)
    
    # Also set HTTP-only cookie for secure browser clients
    response.set_cookie(
        key="testflow_access_token",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24,  # 24 hours
        samesite="lax",
        secure=settings.cookie_secure
    )

    dept_name = user.department.name if user.department else None

    user_response = UserMeResponse(
        id=user.id,
        emp_code=user.emp_code,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user.role,
        department_id=user.department_id,
        department_name=dept_name,
        is_active=user.is_active
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("testflow_access_token")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserMeResponse)
def get_current_user_profile(current_user: Employee = Depends(get_current_user)):
    dept_name = current_user.department.name if current_user.department else None
    return UserMeResponse(
        id=current_user.id,
        emp_code=current_user.emp_code,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email,
        role=current_user.role,
        department_id=current_user.department_id,
        department_name=dept_name,
        is_active=current_user.is_active
    )
