"""
Initial database seed script to populate default departments and initial user accounts.
"""
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.department import Department
from app.models.employee import Employee, RoleEnum


"""
Initial database seed script to populate default departments and initial user accounts.
"""
import os
from app.core.config import settings
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.department import Department
from app.models.employee import Employee, RoleEnum


def seed_data():
    if settings.is_production and os.getenv("ALLOW_SEED_IN_PRODUCTION", "false").lower() not in ("true", "1"):
        print("⚠ Refusing to seed default demo credentials in PRODUCTION environment.")
        return

    # Only create tables via Base.metadata during SQLite development without migrations
    if not settings.is_production and settings.sqlalchemy_database_uri.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Seed Departments
        dept_data = [
            ("Testing & Diagnostics", "DEP-TEST"),
            ("Quality Assurance", "DEP-QA"),
            ("Warehouse & Inventory", "DEP-STORE"),
            ("Human Resources", "DEP-HR"),
            ("Operations Management", "DEP-OPS"),
        ]
        dept_map = {}
        for name, code in dept_data:
            dept = db.query(Department).filter(Department.code == code).first()
            if not dept:
                dept = Department(name=name, code=code)
                db.add(dept)
                db.flush()
            dept_map[code] = dept

        # 2. Seed Staff Accounts (including featured demo credentials)
        users_data = [
            ("EMP-SHAURYA", "Shaurya", "Viir Singh", "shaurya.singh@testflow.local", "67890", RoleEnum.SUPER_ADMIN, "DEP-OPS"),
            ("EMP-SAMBHAV", "Sambhav", "Yadav", "sambhav.yadav@testflow.local", "12345", RoleEnum.OPERATIONS_MGR, "DEP-OPS"),
            ("EMP-001", "Alex", "Admin", "admin@testflow.local", "Admin123!", RoleEnum.SUPER_ADMIN, "DEP-OPS"),
            ("EMP-002", "Hannah", "Reed", "hr@testflow.local", "HrPass123!", RoleEnum.HR_OFFICER, "DEP-HR"),
            ("EMP-003", "Sam", "Vance", "supervisor@testflow.local", "Super123!", RoleEnum.TEST_SUPERVISOR, "DEP-TEST"),
            ("EMP-101", "Tom", "Miller", "technician1@testflow.local", "Tech123!", RoleEnum.TEST_TECHNICIAN, "DEP-TEST"),
            ("EMP-201", "Quinn", "Adams", "qa1@testflow.local", "QaPass123!", RoleEnum.QA_INSPECTOR, "DEP-QA"),
            ("EMP-301", "Steve", "Karp", "store@testflow.local", "Store123!", RoleEnum.STORE_KEEPER, "DEP-STORE"),
        ]

        for emp_code, first, last, email, password, role, dept_code in users_data:
            existing = db.query(Employee).filter(
                (Employee.email == email) | (Employee.emp_code == emp_code)
            ).first()
            dept = dept_map.get(dept_code)
            if not existing:
                emp = Employee(
                    emp_code=emp_code,
                    first_name=first,
                    last_name=last,
                    email=email,
                    password_hash=get_password_hash(password),
                    role=role,
                    department_id=dept.id if dept else None,
                    is_active=True
                )
                db.add(emp)
            else:
                existing.first_name = first
                existing.last_name = last
                existing.email = email
                existing.password_hash = get_password_hash(password)
                existing.role = role
                existing.is_active = True

        db.commit()
        print("✓ Database seeded successfully with initial departments and users.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()

