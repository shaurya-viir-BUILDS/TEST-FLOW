from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, get_current_user
from app.models.employee import RoleEnum, Employee
from app.models.batch import BatchItem
from app.models.testing import TestSession, TestResultDetail
from app.schemas.testing import (
    ManualTestExecutionRequest,
    TestSessionResponse,
    TestResultDetailResponse,
    BenchCsvImportResult
)
from app.services.testing_engine import execute_manual_test, parse_bench_csv

router = APIRouter()


def _format_session_response(s: TestSession) -> TestSessionResponse:
    details = []
    for d in s.details:
        param_name = d.parameter.parameter_name if d.parameter else f"Param #{d.parameter_id}"
        d_resp = TestResultDetailResponse(
            id=d.id,
            parameter_id=d.parameter_id,
            parameter_name=param_name,
            measured_value=d.measured_value,
            result=d.result
        )
        details.append(d_resp)

    serial = s.batch_item.serial_number if s.batch_item else None
    template_name = s.template.name if s.template else None
    tech_name = f"{s.technician.first_name} {s.technician.last_name}" if s.technician else None

    return TestSessionResponse(
        id=s.id,
        batch_item_id=s.batch_item_id,
        serial_number=serial,
        template_name=template_name,
        technician_name=tech_name,
        execution_type=s.execution_type,
        overall_result=s.overall_result,
        execution_date=s.execution_date,
        remarks=s.remarks,
        details=details
    )


@router.post("/manual", response_model=TestSessionResponse, status_code=status.HTTP_201_CREATED)
def submit_manual_test(
    request: ManualTestExecutionRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.TEST_TECHNICIAN, RoleEnum.TEST_SUPERVISOR]))
):
    session = execute_manual_test(db, request, technician_id=current_user.id)
    return _format_session_response(session)


@router.post("/upload-bench-csv", response_model=BenchCsvImportResult)
async def upload_bench_csv(
    template_id: int = Query(..., description="ID of active TestTemplate defining criteria"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.TEST_TECHNICIAN, RoleEnum.TEST_SUPERVISOR]))
):
    if not (file.filename.endswith(".csv") or file.filename.endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV (.csv) file exported from test bench."
        )

    file_bytes = await file.read()
    result = parse_bench_csv(file_bytes, template_id, technician_id=current_user.id, db=db)
    return result


@router.get("/history/{batch_item_id}", response_model=List[TestSessionResponse])
def get_test_history(
    batch_item_id: int,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    item = db.query(BatchItem).filter(BatchItem.id == batch_item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch item {batch_item_id} not found.")

    sessions = db.query(TestSession).filter(TestSession.batch_item_id == batch_item_id).order_by(TestSession.execution_date.desc()).all()
    return [_format_session_response(s) for s in sessions]
