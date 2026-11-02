from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_user, require_role
from app.models.employee import Employee, RoleEnum
from app.models.attendance import AttendanceRecord, AttendanceStatusEnum, AttendanceSourceEnum
from app.schemas.attendance import (
    PunchRequest,
    PunchTypeEnum,
    AttendanceResponse,
    AttendanceSummary,
    ExcelImportResult
)
from app.services.attendance_parser import parse_attendance_excel

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter()


@router.post("/punch", response_model=AttendanceResponse)
def punch_attendance(
    punch_in: PunchRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Self check-in or check-out for the current employee for today's date.
    """
    today = date.today()
    now_time = datetime.now().time()

    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == current_user.id,
        AttendanceRecord.attendance_date == today
    ).first()

    if punch_in.punch_type == PunchTypeEnum.IN:
        if record and record.punch_in:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Already punched in today at {record.punch_in.strftime('%H:%M:%S')}"
            )
        if not record:
            record = AttendanceRecord(
                employee_id=current_user.id,
                attendance_date=today,
                punch_in=now_time,
                status=AttendanceStatusEnum.PRESENT,
                source=AttendanceSourceEnum.MANUAL
            )
            db.add(record)
        else:
            record.punch_in = now_time
            record.status = AttendanceStatusEnum.PRESENT
            record.source = AttendanceSourceEnum.MANUAL
    else:  # OUT
        if not record:
            # Punching out without a prior punch in
            record = AttendanceRecord(
                employee_id=current_user.id,
                attendance_date=today,
                punch_out=now_time,
                status=AttendanceStatusEnum.HALF_DAY,
                source=AttendanceSourceEnum.MANUAL
            )
            db.add(record)
        else:
            record.punch_out = now_time

    db.commit()
    db.refresh(record)

    resp = AttendanceResponse.model_validate(record)
    resp.emp_code = current_user.emp_code
    resp.employee_name = f"{current_user.first_name} {current_user.last_name}"
    return resp


@router.post("/punch-in", response_model=AttendanceResponse)
def punch_in_attendance(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Self check-in alias for the current employee for today's date.
    """
    return punch_attendance(PunchRequest(punch_type=PunchTypeEnum.IN), db=db, current_user=current_user)


@router.post("/punch-out", response_model=AttendanceResponse)
def punch_out_attendance(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Self check-out alias for the current employee for today's date.
    """
    return punch_attendance(PunchRequest(punch_type=PunchTypeEnum.OUT), db=db, current_user=current_user)


@router.get("/records", response_model=List[AttendanceResponse])
def get_attendance_records(
    employee_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status_filter: Optional[AttendanceStatusEnum] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Retrieve attendance records. Regular employees can only view their own;
    HR/Admins/Supervisors/Managers can view all.
    """
    query = db.query(AttendanceRecord)

    # If technician or store keeper, restrict to own records unless manager/admin/hr/supervisor
    privileged_roles = {
        RoleEnum.SUPER_ADMIN,
        RoleEnum.OPERATIONS_MGR,
        RoleEnum.HR_OFFICER,
        RoleEnum.TEST_SUPERVISOR
    }
    if current_user.role not in privileged_roles:
        query = query.filter(AttendanceRecord.employee_id == current_user.id)
    elif employee_id is not None:
        query = query.filter(AttendanceRecord.employee_id == employee_id)

    if start_date:
        query = query.filter(AttendanceRecord.attendance_date >= start_date)
    if end_date:
        query = query.filter(AttendanceRecord.attendance_date <= end_date)
    if status_filter:
        query = query.filter(AttendanceRecord.status == status_filter)

    records = query.order_by(AttendanceRecord.attendance_date.desc()).offset(skip).limit(limit).all()

    results = []
    for r in records:
        resp = AttendanceResponse.model_validate(r)
        if r.employee:
            resp.emp_code = r.employee.emp_code
            resp.employee_name = f"{r.employee.first_name} {r.employee.last_name}"
        results.append(resp)
    return results


@router.get("/today-summary", response_model=AttendanceSummary)
def get_today_summary(
    target_date: Optional[date] = None,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    """
    Returns summary statistics for a given date (defaults to today)
    showing shift coverage and presence rates for supervisor task allocation.
    """
    query_date = target_date or date.today()
    total_active = db.query(Employee).filter(Employee.is_active == True).count()

    records = db.query(AttendanceRecord).filter(AttendanceRecord.attendance_date == query_date).all()
    
    present = sum(1 for r in records if r.status == AttendanceStatusEnum.PRESENT)
    half_day = sum(1 for r in records if r.status == AttendanceStatusEnum.HALF_DAY)
    on_leave = sum(1 for r in records if r.status == AttendanceStatusEnum.ON_LEAVE)
    
    # Those without record or marked absent
    recorded_emp_ids = {r.employee_id for r in records}
    explicit_absent = sum(1 for r in records if r.status == AttendanceStatusEnum.ABSENT)
    unrecorded_absent = max(0, total_active - len(recorded_emp_ids))
    total_absent = explicit_absent + unrecorded_absent

    present_pct = round(((present + half_day * 0.5) / max(total_active, 1)) * 100, 1)

    return AttendanceSummary(
        date=query_date,
        total_employees=total_active,
        present=present,
        absent=total_absent,
        on_leave=on_leave,
        half_day=half_day,
        present_percentage=present_pct
    )


@router.get("/today")
def get_today_attendance_bundle(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Returns today's shift summary alongside recent attendance records for the web console.
    """
    summary = get_today_summary(target_date=date.today(), db=db, _current_user=current_user)
    records = get_attendance_records(skip=0, limit=50, db=db, current_user=current_user)
    return {
        "date": summary.date,
        "total_employees": summary.total_employees,
        "present_count": summary.present,
        "absent_count": summary.absent,
        "on_leave_count": summary.on_leave,
        "half_day_count": summary.half_day,
        "attendance_rate": summary.present_percentage,
        "records": records
    }


@router.post("/upload-excel", response_model=ExcelImportResult)
async def upload_attendance_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.HR_OFFICER]))
):
    """
    Accepts biometric attendance spreadsheet (.xlsx) and parses rows into AttendanceRecord.
    """
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xlsm")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File format not supported. Please upload an Excel (.xlsx) file."
        )

    file_contents = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(file_contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Attendance file exceeds maximum allowed limit of {MAX_UPLOAD_SIZE // (1024 * 1024)}MB."
        )
    try:
        result = parse_attendance_excel(file_contents, db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process workbook: {str(e)}"
        )

