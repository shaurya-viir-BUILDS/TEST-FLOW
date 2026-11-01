import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.main import app
from app.models.department import Department
from app.models.employee import Employee, RoleEnum

# In-memory SQLite for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        # Seed test department
        dept = Department(name="Testing Lab", code="DEP-TEST")
        session.add(dept)
        session.flush()

        # Seed test users
        admin = Employee(
            emp_code="EMP-TEST-01",
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            password_hash=get_password_hash("Password123!"),
            role=RoleEnum.SUPER_ADMIN,
            department_id=dept.id,
            is_active=True
        )
        tech = Employee(
            emp_code="EMP-TEST-02",
            first_name="Tech",
            last_name="Tester",
            email="tech@test.com",
            password_hash=get_password_hash("Password123!"),
            role=RoleEnum.TEST_TECHNICIAN,
            department_id=dept.id,
            is_active=True
        )
        hr = Employee(
            emp_code="EMP-TEST-03",
            first_name="Helen",
            last_name="Resource",
            email="hr@test.com",
            password_hash=get_password_hash("Password123!"),
            role=RoleEnum.HR_OFFICER,
            department_id=dept.id,
            is_active=True
        )
        session.add_all([admin, tech, hr])
        session.commit()

        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(db_session) -> dict:
    admin = db_session.query(Employee).filter(Employee.email == "admin@test.com").first()
    token = create_access_token(subject=admin.id, role=admin.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tech_headers(db_session) -> dict:
    tech = db_session.query(Employee).filter(Employee.email == "tech@test.com").first()
    token = create_access_token(subject=tech.id, role=tech.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def hr_headers(db_session) -> dict:
    hr = db_session.query(Employee).filter(Employee.email == "hr@test.com").first()
    token = create_access_token(subject=hr.id, role=hr.role.value)
    return {"Authorization": f"Bearer {token}"}

