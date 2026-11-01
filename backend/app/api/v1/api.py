from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    departments,
    employees,
    attendance,
    clients,
    products,
    batches,
    test_templates,
    testing,
    quality
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(departments.router, prefix="/departments", tags=["Departments"])
api_router.include_router(employees.router, prefix="/employees", tags=["Employees"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
api_router.include_router(clients.router, prefix="/clients", tags=["Clients"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(batches.router, prefix="/batches", tags=["Batches & Inventory"])
api_router.include_router(test_templates.router, prefix="/test-templates", tags=["Testing Templates"])
api_router.include_router(testing.router, prefix="/testing", tags=["Testing Execution"])
api_router.include_router(quality.router, prefix="/quality", tags=["Quality Assurance & Defects"])

