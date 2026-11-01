from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, require_role, get_current_user
from app.models.employee import RoleEnum, Employee
from app.models.batch import Batch, BatchItem, BatchStatusEnum, BatchItemStatusEnum
from app.models.testing import TestSession, TestResultDetail, TestTaskAllocation, TaskAllocationStatusEnum
from app.schemas.testing import (
    ManualTestExecutionRequest,
    TestSessionResponse,
    TestResultDetailResponse,
    BenchCsvImportResult,
    TaskAllocationCreate,
    TaskAllocationResponse,
    BatchTestingProgressResponse,
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


# --------------------------------------------------------------------------
# Module 4: Task Allocation & Batch Progress Tracking
# --------------------------------------------------------------------------

@router.post("/allocate-tasks", response_model=TaskAllocationResponse, status_code=status.HTTP_201_CREATED)
def allocate_test_tasks(
    alloc_in: TaskAllocationCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.TEST_SUPERVISOR]))
):
    """
    Supervisor allocates an inward batch (or subset of serial numbers) to an active technician.
    Transitions units to ALLOCATED status.
    """
    batch = db.query(Batch).filter(Batch.id == alloc_in.batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch {alloc_in.batch_id} not found.")

    technician = db.query(Employee).filter(Employee.id == alloc_in.technician_id).first()
    if not technician or not technician.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned technician not found or inactive.")

    # Target items query
    items_query = db.query(BatchItem).filter(BatchItem.batch_id == batch.id)
    if alloc_in.serial_numbers:
        items_query = items_query.filter(BatchItem.serial_number.in_([s.strip().upper() for s in alloc_in.serial_numbers]))

    items = items_query.all()
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No matching batch items found for allocation.")

    # Transition items from RECEIVED / QA_REWORK to ALLOCATED
    for item in items:
        if item.current_status in (BatchItemStatusEnum.RECEIVED, BatchItemStatusEnum.QA_REWORK):
            item.current_status = BatchItemStatusEnum.ALLOCATED

    # Transition parent batch status if still RECEIVED
    if batch.current_status == BatchStatusEnum.RECEIVED:
        batch.current_status = BatchStatusEnum.ALLOCATED

    allocation = TestTaskAllocation(
        batch_id=batch.id,
        technician_id=technician.id,
        assigned_by_id=current_user.id,
        status=TaskAllocationStatusEnum.IN_PROGRESS,
        notes=alloc_in.notes
    )
    db.add(allocation)
    db.commit()
    db.refresh(allocation)

    return TaskAllocationResponse(
        id=allocation.id,
        batch_id=batch.id,
        batch_number=batch.batch_number,
        technician_id=technician.id,
        technician_name=f"{technician.first_name} {technician.last_name}",
        status=allocation.status,
        assigned_at=allocation.assigned_at,
        notes=allocation.notes
    )


@router.get("/my-queue", response_model=List[dict])
def get_technician_queue(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.TEST_TECHNICIAN, RoleEnum.TEST_SUPERVISOR]))
):
    """
    Returns active testing tasks and assigned units for the logged-in technician.
    """
    allocations = db.query(TestTaskAllocation).filter(
        TestTaskAllocation.technician_id == current_user.id,
        TestTaskAllocation.status.in_([TaskAllocationStatusEnum.PENDING, TaskAllocationStatusEnum.IN_PROGRESS])
    ).order_by(TestTaskAllocation.assigned_at.desc()).all()

    queue = []
    for a in allocations:
        batch = a.batch
        allocated_items = db.query(BatchItem).filter(
            BatchItem.batch_id == a.batch_id,
            BatchItem.current_status.in_([BatchItemStatusEnum.ALLOCATED, BatchItemStatusEnum.IN_TESTING])
        ).all()

        queue.append({
            "allocation_id": a.id,
            "batch_id": a.batch_id,
            "batch_number": batch.batch_number if batch else None,
            "product_model": batch.product_model.model_number if batch and batch.product_model else None,
            "assigned_at": a.assigned_at,
            "pending_units_count": len(allocated_items),
            "units": [
                {
                    "id": u.id,
                    "serial_number": u.serial_number,
                    "status": u.current_status,
                    "qr_code_hash": u.qr_code_hash
                }
                for u in allocated_items
            ]
        })
    return queue


@router.get("/batch-progress/{batch_id}", response_model=BatchTestingProgressResponse)
def get_batch_testing_progress(
    batch_id: int,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    """
    Calculates detailed testing completion percentages, yield rates, and active technicians for a batch.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch {batch_id} not found.")

    counts = db.query(
        BatchItem.current_status,
        func.count(BatchItem.id)
    ).filter(BatchItem.batch_id == batch_id).group_by(BatchItem.current_status).all()

    count_map = {status: cnt for status, cnt in counts}
    total = sum(count_map.values()) or batch.received_qty

    units_received = count_map.get(BatchItemStatusEnum.RECEIVED, 0)
    units_allocated = count_map.get(BatchItemStatusEnum.ALLOCATED, 0)
    units_in_testing = count_map.get(BatchItemStatusEnum.IN_TESTING, 0)
    units_passed = count_map.get(BatchItemStatusEnum.PASSED, 0)
    units_failed = count_map.get(BatchItemStatusEnum.FAILED, 0)
    units_qa_approved = count_map.get(BatchItemStatusEnum.QA_APPROVED, 0)
    units_qa_rework = count_map.get(BatchItemStatusEnum.QA_REWORK, 0)
    units_qa_scrapped = count_map.get(BatchItemStatusEnum.QA_SCRAPPED, 0)

    # Tested units includes PASSED, FAILED, QA_APPROVED, QA_REWORK, QA_SCRAPPED
    completed_units = units_passed + units_failed + units_qa_approved + units_qa_rework + units_qa_scrapped
    completion_pct = round((completed_units / max(total, 1)) * 100, 1)

    successful_units = units_passed + units_qa_approved
    first_pass_yield = round((successful_units / max(completed_units, 1)) * 100, 1) if completed_units > 0 else 0.0

    # Assigned technicians
    tech_allocs = db.query(TestTaskAllocation).filter(TestTaskAllocation.batch_id == batch_id).all()
    technicians = list({f"{a.technician.first_name} {a.technician.last_name}" for a in tech_allocs if a.technician})

    prod_name = batch.product_model.model_name if batch.product_model else "Unknown"

    return BatchTestingProgressResponse(
        batch_id=batch.id,
        batch_number=batch.batch_number,
        product_model_name=prod_name,
        total_units=total,
        units_received=units_received,
        units_allocated=units_allocated,
        units_in_testing=units_in_testing,
        units_passed=units_passed,
        units_failed=units_failed,
        units_qa_approved=units_qa_approved,
        units_qa_rework=units_qa_rework,
        units_qa_scrapped=units_qa_scrapped,
        completion_percentage=completion_pct,
        first_pass_yield=first_pass_yield,
        active_technicians=technicians
    )
