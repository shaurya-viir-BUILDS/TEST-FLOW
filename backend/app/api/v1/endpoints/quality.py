from typing import List, Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, require_role, get_current_user
from app.models.employee import RoleEnum, Employee
from app.models.batch import BatchItem, BatchItemStatusEnum
from app.models.testing import TestSession, TestResultEnum
from app.models.quality import DefectLog, QADisposition, QADecisionEnum, DefectSeverityEnum
from app.schemas.quality import (
    DefectLogCreate,
    DefectLogResponse,
    QADispositionCreate,
    QADispositionResponse,
    RetestSubmissionRequest,
    QualityHistoryItemResponse,
    DefectSummaryResponse,
)
from app.schemas.testing import ManualTestExecutionRequest
from app.services.testing_engine import execute_manual_test
from app.api.v1.endpoints.testing import _format_session_response

router = APIRouter()


def _format_defect_response(d: DefectLog) -> DefectLogResponse:
    resp = DefectLogResponse.model_validate(d)
    if d.batch_item:
        resp.serial_number = d.batch_item.serial_number
    if d.author:
        resp.logged_by_name = f"{d.author.first_name} {d.author.last_name}"
    if d.resolver:
        resp.resolved_by_name = f"{d.resolver.first_name} {d.resolver.last_name}"
    return resp


@router.post("/defects", response_model=DefectLogResponse, status_code=status.HTTP_201_CREATED)
def log_defect(
    defect_in: DefectLogCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.TEST_TECHNICIAN, RoleEnum.QA_INSPECTOR]))
):
    item = db.query(BatchItem).filter(BatchItem.id == defect_in.batch_item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch item {defect_in.batch_item_id} not found.")

    defect = DefectLog(
        batch_item_id=defect_in.batch_item_id,
        test_session_id=defect_in.test_session_id,
        defect_code=defect_in.defect_code.strip().upper(),
        severity=defect_in.severity,
        description=defect_in.description.strip(),
        logged_by=current_user.id
    )
    db.add(defect)
    item.is_defective = True
    db.commit()
    db.refresh(defect)

    return _format_defect_response(defect)


@router.get("/defects", response_model=List[DefectLogResponse])
def list_defects(
    batch_item_id: Optional[int] = None,
    severity: Optional[DefectSeverityEnum] = None,
    is_resolved: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    query = db.query(DefectLog)
    if batch_item_id is not None:
        query = query.filter(DefectLog.batch_item_id == batch_item_id)
    if severity is not None:
        query = query.filter(DefectLog.severity == severity)
    if is_resolved is not None:
        query = query.filter(DefectLog.is_resolved == is_resolved)

    defects = query.order_by(DefectLog.created_at.desc()).offset(skip).limit(limit).all()
    return [_format_defect_response(d) for d in defects]


@router.post("/disposition", response_model=QADispositionResponse, status_code=status.HTTP_201_CREATED)
def submit_qa_disposition(
    disp_in: QADispositionCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.QA_INSPECTOR]))
):
    item = db.query(BatchItem).filter(BatchItem.id == disp_in.batch_item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch item {disp_in.batch_item_id} not found.")

    # Business rule: Cannot approve if unit is in FAILED status
    if disp_in.decision == QADecisionEnum.APPROVED:
        latest_session = db.query(TestSession).filter(
            TestSession.batch_item_id == item.id
        ).order_by(TestSession.execution_date.desc()).first()

        if not latest_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unit {item.serial_number} has not been tested yet. Cannot approve."
            )
        if latest_session.overall_result != TestResultEnum.PASS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unit {item.serial_number} latest test result was FAIL. Retest required before QA approval."
            )

        item.current_status = BatchItemStatusEnum.QA_APPROVED
        item.is_defective = False
    elif disp_in.decision == QADecisionEnum.RETEST_REQUESTED:
        item.current_status = BatchItemStatusEnum.QA_REWORK
    elif disp_in.decision == QADecisionEnum.SCRAPPED:
        item.current_status = BatchItemStatusEnum.QA_SCRAPPED
        item.is_defective = True

    disp = QADisposition(
        batch_item_id=item.id,
        inspector_id=current_user.id,
        decision=disp_in.decision,
        remarks=disp_in.remarks.strip() if disp_in.remarks else None
    )
    db.add(disp)
    db.commit()
    db.refresh(disp)

    resp = QADispositionResponse.model_validate(disp)
    resp.serial_number = item.serial_number
    resp.inspector_name = f"{current_user.first_name} {current_user.last_name}"
    return resp


# --------------------------------------------------------------------------
# Module 5: Retesting Workflow & Quality History
# --------------------------------------------------------------------------

@router.post("/retest", response_model=dict, status_code=status.HTTP_201_CREATED)
def submit_unit_retest(
    retest_in: RetestSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.TEST_TECHNICIAN, RoleEnum.TEST_SUPERVISOR]))
):
    """
    Submits a retest session for a unit marked for rework (QA_REWORK or FAILED).
    If retest passes, resolves the associated defect record and transitions unit to PASSED.
    """
    item = db.query(BatchItem).filter(BatchItem.id == retest_in.batch_item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch item {retest_in.batch_item_id} not found.")

    if item.current_status not in (BatchItemStatusEnum.QA_REWORK, BatchItemStatusEnum.FAILED, BatchItemStatusEnum.ALLOCATED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unit status is '{item.current_status.value}'. Retest is only applicable for QA_REWORK, FAILED, or ALLOCATED units."
        )

    # Execute manual test
    exec_req = ManualTestExecutionRequest(
        batch_item_id=retest_in.batch_item_id,
        template_id=retest_in.template_id,
        results=retest_in.results,
        remarks=f"Retest: {retest_in.resolution_notes or 'Post-rework verification'}"
    )
    session = execute_manual_test(db, exec_req, technician_id=current_user.id)

    # If pass, resolve defect log
    defect_resolved = False
    if session.overall_result == TestResultEnum.PASS:
        # Find open defect
        query = db.query(DefectLog).filter(DefectLog.batch_item_id == item.id, DefectLog.is_resolved == False)
        if retest_in.defect_id:
            query = query.filter(DefectLog.id == retest_in.defect_id)
        open_defect = query.first()

        if open_defect:
            open_defect.is_resolved = True
            open_defect.resolved_by = current_user.id
            open_defect.resolved_at = datetime.utcnow()
            open_defect.resolution_notes = retest_in.resolution_notes or "Passed retest verification"
            open_defect.retest_session_id = session.id
            defect_resolved = True
            item.is_defective = False

        db.commit()

    return {
        "retest_session_id": session.id,
        "overall_result": session.overall_result,
        "new_status": item.current_status,
        "defect_resolved": defect_resolved
    }


@router.get("/history/{batch_item_id}", response_model=QualityHistoryItemResponse)
def get_unit_quality_history(
    batch_item_id: int,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    """
    Returns complete chronological quality lifecycle for a serial unit:
    all test sessions, logged defects, and inspector decisions.
    """
    item = db.query(BatchItem).filter(BatchItem.id == batch_item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch item {batch_item_id} not found.")

    sessions = db.query(TestSession).filter(TestSession.batch_item_id == batch_item_id).order_by(TestSession.execution_date.asc()).all()
    defects = db.query(DefectLog).filter(DefectLog.batch_item_id == batch_item_id).order_by(DefectLog.created_at.asc()).all()
    dispositions = db.query(QADisposition).filter(QADisposition.batch_item_id == batch_item_id).order_by(QADisposition.disposition_at.asc()).all()

    formatted_sessions = [_format_session_response(s) for s in sessions]
    formatted_defects = [_format_defect_response(d) for d in defects]
    formatted_disps = []
    for disp in dispositions:
        d_resp = QADispositionResponse.model_validate(disp)
        d_resp.serial_number = item.serial_number
        d_resp.inspector_name = f"{disp.inspector.first_name} {disp.inspector.last_name}" if disp.inspector else None
        formatted_disps.append(d_resp)

    batch_num = item.batch.batch_number if item.batch else None
    prod_model = item.batch.product_model.model_number if item.batch and item.batch.product_model else None

    return QualityHistoryItemResponse(
        serial_number=item.serial_number,
        batch_number=batch_num,
        product_model=prod_model,
        current_status=item.current_status.value,
        is_defective=item.is_defective,
        test_sessions=formatted_sessions,
        defect_logs=formatted_defects,
        dispositions=formatted_disps
    )


@router.get("/defect-summary", response_model=DefectSummaryResponse)
def get_defect_summary(
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    """
    Returns Pareto defect analytics grouped by severity and top defect codes.
    """
    total = db.query(DefectLog).count()
    resolved = db.query(DefectLog).filter(DefectLog.is_resolved == True).count()
    open_count = total - resolved

    # Severity counts
    sev_counts = db.query(DefectLog.severity, func.count(DefectLog.id)).group_by(DefectLog.severity).all()
    by_severity = {s.value: cnt for s, cnt in sev_counts}

    # Top defect codes
    code_counts = db.query(
        DefectLog.defect_code,
        func.count(DefectLog.id).label("count")
    ).group_by(DefectLog.defect_code).order_by(func.count(DefectLog.id).desc()).limit(10).all()

    top_codes = [{"code": c, "count": cnt} for c, cnt in code_counts]

    return DefectSummaryResponse(
        total_defects=total,
        open_defects=open_count,
        resolved_defects=resolved,
        by_severity=by_severity,
        top_defect_codes=top_codes
    )
