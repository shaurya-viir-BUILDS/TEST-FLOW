from datetime import date, datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_user
from app.models.employee import Employee, RoleEnum
from app.models.client import Client
from app.models.product import ProductModel
from app.models.batch import Batch, BatchItem, BatchItemStatusEnum, BatchStatusEnum
from app.models.testing import TestSession, TestTaskAllocation, TestResultEnum, TaskAllocationStatusEnum
from app.models.quality import DefectLog, QADisposition, QADecisionEnum
from app.models.dispatch import DispatchOrder, DispatchStatusEnum
from app.models.attendance import AttendanceRecord, AttendanceStatusEnum
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    TestingDashboardResponse,
    QualityDashboardResponse,
    AttendanceReportResponse,
    OperationalReportResponse,
)

router = APIRouter()


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    """
    High-level operational overview for executive management.
    """
    total_batches = db.query(Batch).count()
    total_units = db.query(BatchItem).count()

    # Unit counts by status
    counts = db.query(
        BatchItem.current_status,
        func.count(BatchItem.id)
    ).group_by(BatchItem.current_status).all()
    count_map = {status: cnt for status, cnt in counts}

    units_passed = count_map.get(BatchItemStatusEnum.PASSED, 0)
    units_failed = count_map.get(BatchItemStatusEnum.FAILED, 0)
    units_qa_approved = count_map.get(BatchItemStatusEnum.QA_APPROVED, 0)
    units_dispatched = count_map.get(BatchItemStatusEnum.DISPATCHED, 0)
    units_rework = count_map.get(BatchItemStatusEnum.QA_REWORK, 0)
    units_scrapped = count_map.get(BatchItemStatusEnum.QA_SCRAPPED, 0)
    units_pending = count_map.get(BatchItemStatusEnum.RECEIVED, 0) + count_map.get(BatchItemStatusEnum.ALLOCATED, 0) + count_map.get(BatchItemStatusEnum.IN_TESTING, 0)

    tested_total = units_passed + units_failed + units_qa_approved + units_dispatched + units_rework + units_scrapped
    successful_total = units_passed + units_qa_approved + units_dispatched

    overall_yield = round((successful_total / max(tested_total, 1)) * 100, 1) if tested_total > 0 else 0.0

    # First pass yield calculation (first test session per unit)
    first_sessions_sub = (
        db.query(
            TestSession.batch_item_id,
            func.min(TestSession.id).label("min_session_id")
        )
        .group_by(TestSession.batch_item_id)
        .subquery()
    )
    first_sessions = (
        db.query(TestSession.overall_result)
        .join(first_sessions_sub, TestSession.id == first_sessions_sub.c.min_session_id)
        .all()
    )
    total_first_pass_units = len(first_sessions)
    first_pass_success = sum(1 for (res,) in first_sessions if res == TestResultEnum.PASS)
    first_pass_yield = round((first_pass_success / max(total_first_pass_units, 1)) * 100, 1) if total_first_pass_units > 0 else 0.0

    open_defects = db.query(DefectLog).filter(DefectLog.is_resolved == False).count()

    # Shift attendance
    today = date.today()
    total_active_staff = db.query(Employee).filter(Employee.is_active == True).count()
    today_records = db.query(AttendanceRecord).filter(AttendanceRecord.attendance_date == today).all()
    present_today = sum(1 for r in today_records if r.status in (AttendanceStatusEnum.PRESENT, AttendanceStatusEnum.HALF_DAY))
    att_pct = round((present_today / max(total_active_staff, 1)) * 100, 1)

    technicians_on_shift = db.query(Employee).filter(
        Employee.role.in_([RoleEnum.TEST_TECHNICIAN, RoleEnum.TEST_SUPERVISOR]),
        Employee.is_active == True
    ).count()

    return DashboardOverviewResponse(
        total_batches=total_batches,
        total_units=total_units,
        units_passed=units_passed,
        units_failed=units_failed,
        units_pending=units_pending,
        units_qa_approved=units_qa_approved,
        units_dispatched=units_dispatched,
        overall_yield_percentage=overall_yield,
        first_pass_yield_percentage=first_pass_yield,
        open_defects_count=open_defects,
        active_technicians_on_shift=technicians_on_shift,
        today_attendance_percentage=att_pct,
        passed_units=units_passed,
        failed_units=units_failed,
        total_registered_units=total_units,
        tested_units=tested_total,
        attendance_rate_today=att_pct
    )


@router.get("/testing", response_model=TestingDashboardResponse)
def get_testing_dashboard(
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    """
    Detailed testing floor operational dashboard.
    """
    total_alloc = db.query(TestTaskAllocation).count()
    completed_alloc = db.query(TestTaskAllocation).filter(TestTaskAllocation.status == TaskAllocationStatusEnum.COMPLETED).count()
    pending_alloc = db.query(TestTaskAllocation).filter(TestTaskAllocation.status == TaskAllocationStatusEnum.PENDING).count()

    # Counts by unit status
    counts = db.query(BatchItem.current_status, func.count(BatchItem.id)).group_by(BatchItem.current_status).all()
    status_map = {s.value if hasattr(s, "value") else str(s): cnt for s, cnt in counts}

    # Batch progress items
    batches = db.query(Batch).order_by(Batch.inward_date.desc()).limit(15).all()
    batch_items = []
    for b in batches:
        b_counts = db.query(BatchItem.current_status, func.count(BatchItem.id)).filter(BatchItem.batch_id == b.id).group_by(BatchItem.current_status).all()
        m = {s: cnt for s, cnt in b_counts}
        total = sum(m.values()) or b.received_qty
        passed = m.get(BatchItemStatusEnum.PASSED, 0) + m.get(BatchItemStatusEnum.QA_APPROVED, 0) + m.get(BatchItemStatusEnum.DISPATCHED, 0)
        batch_items.append({
            "batch_id": b.id,
            "batch_number": b.batch_number,
            "product_model": b.product_model.model_number if b.product_model else "Unknown",
            "total_units": total,
            "passed_units": passed,
            "status": b.current_status.value if hasattr(b.current_status, "value") else str(b.current_status),
            "completion_pct": round((passed / max(total, 1)) * 100, 1)
        })

    return TestingDashboardResponse(
        total_assignments=total_alloc,
        completed_assignments=completed_alloc,
        pending_assignments=pending_alloc,
        retest_assignments=status_map.get("QA_REWORK", 0),
        units_by_status=status_map,
        batch_progress_items=batch_items
    )


@router.get("/quality", response_model=QualityDashboardResponse)
def get_quality_dashboard(
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    """
    Quality Assurance KPI dashboard: reviews, defect resolution, and Pareto distribution.
    """
    total_reviews = db.query(QADisposition).count()
    approved = db.query(QADisposition).filter(QADisposition.decision == QADecisionEnum.APPROVED).count()
    rejected = db.query(QADisposition).filter(QADisposition.decision == QADecisionEnum.SCRAPPED).count()
    retest = db.query(QADisposition).filter(QADisposition.decision == QADecisionEnum.RETEST_REQUESTED).count()

    total_defects = db.query(DefectLog).count()
    resolved = db.query(DefectLog).filter(DefectLog.is_resolved == True).count()
    open_count = total_defects - resolved
    res_rate = round((resolved / max(total_defects, 1)) * 100, 1) if total_defects > 0 else 100.0

    # Severity
    sev_counts = db.query(DefectLog.severity, func.count(DefectLog.id)).group_by(DefectLog.severity).all()
    by_severity = {s.value if hasattr(s, "value") else str(s): cnt for s, cnt in sev_counts}

    # Top defect codes
    top_defects = db.query(
        DefectLog.defect_code,
        func.count(DefectLog.id).label("count")
    ).group_by(DefectLog.defect_code).order_by(func.count(DefectLog.id).desc()).limit(8).all()
    top_codes = [{"code": c, "count": cnt} for c, cnt in top_defects]

    return QualityDashboardResponse(
        total_quality_reviews=total_reviews,
        approved_batches=approved,
        pending_batches=retest,
        rejected_batches=rejected,
        total_defects=total_defects,
        open_defects=open_count,
        resolved_defects=resolved,
        defect_resolution_rate=res_rate,
        by_severity=by_severity,
        top_defect_codes=top_codes
    )


@router.get("/reports/operations", response_model=OperationalReportResponse)
def get_operational_report(
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    """
    Executive performance summary report across clients, models, batches, and dispatches.
    """
    clients_count = db.query(Client).count()
    models_count = db.query(ProductModel).count()
    batches = db.query(Batch).all()
    dispatches = db.query(DispatchOrder).all()

    b_summary = [
        {
            "batch_number": b.batch_number,
            "client": b.client.name if b.client else "Unknown",
            "model": b.product_model.model_number if b.product_model else "Unknown",
            "received_date": str(b.inward_date),
            "quantity": b.received_qty,
            "status": b.current_status.value if hasattr(b.current_status, "value") else str(b.current_status)
        }
        for b in batches
    ]

    d_summary = [
        {
            "dispatch_code": d.dispatch_code,
            "dispatch_date": str(d.dispatch_date),
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "total_units": d.total_units,
            "carrier": d.carrier_name
        }
        for d in dispatches
    ]

    return OperationalReportResponse(
        generated_at=datetime.utcnow().isoformat(),
        total_clients=clients_count,
        total_product_models=models_count,
        total_batches=len(batches),
        total_units=db.query(BatchItem).count(),
        batch_summary=b_summary,
        dispatch_summary=d_summary
    )


@router.get("/reports/attendance", response_model=AttendanceReportResponse)
def get_attendance_report(
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    """
    Detailed attendance report across all recorded months with individual employee rates.
    """
    records = db.query(AttendanceRecord).all()
    dist = {}
    for r in records:
        key = r.status.value if hasattr(r.status, "value") else str(r.status)
        dist[key] = dist.get(key, 0) + 1

    # Group by employee
    employees = db.query(Employee).all()
    emp_rates = []
    for emp in employees:
        emp_records = [r for r in records if r.employee_id == emp.id]
        total = len(emp_records)
        present = sum(1 for r in emp_records if r.status in (AttendanceStatusEnum.PRESENT, AttendanceStatusEnum.HALF_DAY))
        rate = round((present / max(total, 1)) * 100, 1) if total > 0 else 0.0
        emp_rates.append({
            "emp_code": emp.emp_code,
            "name": f"{emp.first_name} {emp.last_name}",
            "role": emp.role.value if hasattr(emp.role, "value") else str(emp.role),
            "total_logged_days": total,
            "present_days": present,
            "attendance_rate": rate
        })

    # Determine period dynamically from actual records
    if records:
        valid_dates = [r.attendance_date for r in records if r.attendance_date]
        if valid_dates:
            min_date = min(valid_dates)
            max_date = max(valid_dates)
            if min_date == max_date:
                period_str = min_date.strftime("%B %Y")
            else:
                period_str = f"{min_date.strftime('%B %Y')} - {max_date.strftime('%B %Y')}"
        else:
            period_str = "All Time"
    else:
        period_str = "No Records"

    return AttendanceReportResponse(
        period=period_str,
        total_records=len(records),
        status_distribution=dist,
        employee_rates=emp_rates
    )

