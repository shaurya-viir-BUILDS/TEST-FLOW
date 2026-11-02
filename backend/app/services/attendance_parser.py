import io
from datetime import datetime, date, time
from typing import Optional, Dict, Any, List, Tuple
import openpyxl
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.attendance import AttendanceRecord, AttendanceStatusEnum, AttendanceSourceEnum
from app.schemas.attendance import ExcelImportResult, ExcelRowError

# Flexible column header aliases (case-insensitive, spaces and underscores stripped)
HEADER_ALIASES = {
    "emp_code": {"empcode", "empid", "employeecode", "badgeid", "staffid", "userid", "code"},
    "date": {"date", "attendancedate", "attdate", "punchdate", "logdate"},
    "punch_in": {"punchin", "intime", "timein", "checkin", "in", "firstin"},
    "punch_out": {"punchout", "outtime", "timeout", "checkout", "out", "lastout"},
    "status": {"status", "attendancestatus", "remark", "attendance"},
}


def _clean_header(name: Any) -> str:
    if name is None:
        return ""
    return str(name).lower().replace(" ", "").replace("_", "").replace("-", "")


def _identify_columns(headers: List[Any]) -> Dict[str, int]:
    """Map canonical field names to column indices."""
    col_map: Dict[str, int] = {}
    for idx, header in enumerate(headers):
        cleaned = _clean_header(header)
        for canonical, aliases in HEADER_ALIASES.items():
            if cleaned == canonical.replace("_", "") or cleaned in aliases:
                col_map[canonical] = idx
                break
    return col_map


def _parse_date(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(val: Any) -> Optional[time]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.time()
    if isinstance(val, time):
        return val
    val_str = str(val).strip()
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(val_str, fmt).time()
        except ValueError:
            continue
    return None


def _parse_status(val: Any, has_punch_in: bool) -> AttendanceStatusEnum:
    if val is not None:
        s = str(val).strip().upper()
        if "ABS" in s:
            return AttendanceStatusEnum.ABSENT
        if "LEAVE" in s:
            return AttendanceStatusEnum.ON_LEAVE
        if "HALF" in s:
            return AttendanceStatusEnum.HALF_DAY
        if "PRES" in s or "P" == s:
            return AttendanceStatusEnum.PRESENT
    return AttendanceStatusEnum.PRESENT if has_punch_in else AttendanceStatusEnum.ABSENT


def parse_attendance_excel(file_bytes: bytes, db: Session) -> ExcelImportResult:
    """
    Parses a biometric attendance Excel workbook (.xlsx) and bulk creates/updates attendance records.
    """
    wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True)
    sheet = wb.active
    
    rows = list(sheet.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        return ExcelImportResult(
            total_rows=0,
            imported_count=0,
            skipped_rows=0,
            errors=[ExcelRowError(row=0, reason="Worksheet contains no data or missing header row.")]
        )

    headers = rows[0]
    col_map = _identify_columns(headers)

    if "emp_code" not in col_map:
        return ExcelImportResult(
            total_rows=len(rows) - 1,
            imported_count=0,
            skipped_rows=len(rows) - 1,
            errors=[ExcelRowError(row=1, reason="Could not locate 'Employee Code' or 'EmpID' column in header.")]
        )

    if "date" not in col_map:
        return ExcelImportResult(
            total_rows=len(rows) - 1,
            imported_count=0,
            skipped_rows=len(rows) - 1,
            errors=[ExcelRowError(row=1, reason="Could not locate 'Date' column in header.")]
        )

    # Cache all active employees by normalized emp_code
    all_employees = db.query(Employee).all()
    emp_lookup: Dict[str, Employee] = {
        emp.emp_code.strip().upper(): emp for emp in all_employees
    }

    imported_count = 0
    skipped_count = 0
    errors: List[ExcelRowError] = []

    for row_idx, row_data in enumerate(rows[1:], start=2):
        if not any(row_data):  # Blank row
            continue

        raw_code = row_data[col_map["emp_code"]]
        if not raw_code:
            errors.append(ExcelRowError(row=row_idx, reason="Empty Employee Code"))
            skipped_count += 1
            continue

        code_key = str(raw_code).strip().upper()
        employee = emp_lookup.get(code_key)
        if not employee:
            errors.append(ExcelRowError(row=row_idx, emp_code=str(raw_code), reason=f"Employee '{raw_code}' not found in database"))
            skipped_count += 1
            continue

        raw_date = row_data[col_map["date"]]
        att_date = _parse_date(raw_date)
        if not att_date:
            errors.append(ExcelRowError(row=row_idx, emp_code=str(raw_code), reason=f"Invalid date format: '{raw_date}'"))
            skipped_count += 1
            continue

        punch_in = None
        if "punch_in" in col_map and col_map["punch_in"] < len(row_data):
            raw_punch_in = row_data[col_map["punch_in"]]
            if raw_punch_in is not None and str(raw_punch_in).strip():
                punch_in = _parse_time(raw_punch_in)
                if punch_in is None:
                    errors.append(ExcelRowError(row=row_idx, emp_code=str(raw_code), reason=f"Invalid punch_in time format: '{raw_punch_in}'"))
                    skipped_count += 1
                    continue

        punch_out = None
        if "punch_out" in col_map and col_map["punch_out"] < len(row_data):
            raw_punch_out = row_data[col_map["punch_out"]]
            if raw_punch_out is not None and str(raw_punch_out).strip():
                punch_out = _parse_time(raw_punch_out)
                if punch_out is None:
                    errors.append(ExcelRowError(row=row_idx, emp_code=str(raw_code), reason=f"Invalid punch_out time format: '{raw_punch_out}'"))
                    skipped_count += 1
                    continue

        raw_status = None
        if "status" in col_map and col_map["status"] < len(row_data):
            raw_status = row_data[col_map["status"]]

        status = _parse_status(raw_status, has_punch_in=(punch_in is not None))

        # Check existing record for (employee_id, att_date)
        record = db.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == employee.id,
            AttendanceRecord.attendance_date == att_date
        ).first()

        if record:
            record.punch_in = punch_in or record.punch_in
            record.punch_out = punch_out or record.punch_out
            record.status = status
            record.source = AttendanceSourceEnum.EXCEL_IMPORT
        else:
            record = AttendanceRecord(
                employee_id=employee.id,
                attendance_date=att_date,
                punch_in=punch_in,
                punch_out=punch_out,
                status=status,
                source=AttendanceSourceEnum.EXCEL_IMPORT
            )
            db.add(record)

        imported_count += 1

    db.commit()

    return ExcelImportResult(
        total_rows=len(rows) - 1,
        imported_count=imported_count,
        skipped_rows=skipped_count,
        errors=errors
    )

