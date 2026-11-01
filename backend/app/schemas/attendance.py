from datetime import date, time, datetime
from typing import Optional, List, Dict, Any
import enum
from pydantic import BaseModel, ConfigDict
from app.models.attendance import AttendanceStatusEnum, AttendanceSourceEnum


class PunchTypeEnum(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"


class PunchRequest(BaseModel):
    punch_type: PunchTypeEnum = PunchTypeEnum.IN


class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    emp_code: Optional[str] = None
    employee_name: Optional[str] = None
    attendance_date: date
    punch_in: Optional[time] = None
    punch_out: Optional[time] = None
    status: AttendanceStatusEnum
    source: AttendanceSourceEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceSummary(BaseModel):
    date: date
    total_employees: int
    present: int
    absent: int
    on_leave: int
    half_day: int
    present_percentage: float


class ExcelRowError(BaseModel):
    row: int
    emp_code: Optional[str] = None
    reason: str


class ExcelImportResult(BaseModel):
    total_rows: int
    imported_count: int
    skipped_rows: int
    errors: List[ExcelRowError] = []

