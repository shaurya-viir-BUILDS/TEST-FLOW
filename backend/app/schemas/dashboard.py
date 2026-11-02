from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class DashboardOverviewResponse(BaseModel):
    total_batches: int
    total_units: int
    units_passed: int
    units_failed: int
    units_pending: int
    units_qa_approved: int
    units_dispatched: int
    overall_yield_percentage: float
    first_pass_yield_percentage: float
    open_defects_count: int
    active_technicians_on_shift: int
    today_attendance_percentage: float

    # Frontend dual-compatibility fields
    passed_units: int = 0
    failed_units: int = 0
    total_registered_units: int = 0
    tested_units: int = 0
    attendance_rate_today: float = 0.0


class TestingDashboardResponse(BaseModel):
    total_assignments: int
    completed_assignments: int
    pending_assignments: int
    retest_assignments: int
    units_by_status: Dict[str, int]
    batch_progress_items: List[Dict[str, Any]] = []


class QualityDashboardResponse(BaseModel):
    total_quality_reviews: int
    approved_batches: int
    pending_batches: int
    rejected_batches: int
    total_defects: int
    open_defects: int
    resolved_defects: int
    defect_resolution_rate: float
    by_severity: Dict[str, int]
    top_defect_codes: List[Dict[str, Any]] = []


class AttendanceReportResponse(BaseModel):
    period: str
    total_records: int
    status_distribution: Dict[str, int]
    employee_rates: List[Dict[str, Any]] = []


class OperationalReportResponse(BaseModel):
    generated_at: str
    total_clients: int
    total_product_models: int
    total_batches: int
    total_units: int
    batch_summary: List[Dict[str, Any]] = []
    dispatch_summary: List[Dict[str, Any]] = []

