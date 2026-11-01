from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, get_current_user
from app.models.employee import RoleEnum, Employee
from app.models.batch import BatchItem, BatchItemStatusEnum
from app.models.testing import TestSession, TestResultEnum
from app.models.quality import DefectLog, QADisposition, QADecisionEnum
from app.schemas.quality import (
    DefectLogCreate,
    DefectLogResponse,
    QADispositionCreate,
    QADispositionResponse
)

router = APIRouter()


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

    resp = DefectLogResponse.model_validate(defect)
    resp.serial_number = item.serial_number
    resp.logged_by_name = f"{current_user.first_name} {current_user.last_name}"
    return resp


@router.get("/defects", response_model=List[DefectLogResponse])
def list_defects(
    batch_item_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    query = db.query(DefectLog)
    if batch_item_id is not None:
        query = query.filter(DefectLog.batch_item_id == batch_item_id)

    defects = query.order_by(DefectLog.created_at.desc()).offset(skip).limit(limit).all()
    results = []
    for d in defects:
        resp = DefectLogResponse.model_validate(d)
        if d.batch_item:
            resp.serial_number = d.batch_item.serial_number
        if d.author:
            resp.logged_by_name = f"{d.author.first_name} {d.author.last_name}"
        results.append(resp)
    return results


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
        # Check latest test session
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
