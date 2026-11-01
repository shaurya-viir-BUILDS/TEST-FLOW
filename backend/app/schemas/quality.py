from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.models.quality import DefectSeverityEnum, QADecisionEnum
from app.schemas.testing import ManualTestValueSubmission, TestSessionResponse


class DefectLogCreate(BaseModel):
    batch_item_id: int
    test_session_id: Optional[int] = None
    defect_code: str
    severity: DefectSeverityEnum = DefectSeverityEnum.MAJOR
    description: str


class DefectLogResponse(BaseModel):
    id: int
    batch_item_id: int
    test_session_id: Optional[int] = None
    serial_number: Optional[str] = None
    defect_code: str
    severity: DefectSeverityEnum
    description: str
    logged_by_name: Optional[str] = None
    created_at: datetime
    is_resolved: bool = False
    resolved_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    retest_session_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class QADispositionCreate(BaseModel):
    batch_item_id: int
    decision: QADecisionEnum
    remarks: Optional[str] = None


class QADispositionResponse(BaseModel):
    id: int
    batch_item_id: int
    serial_number: Optional[str] = None
    inspector_id: int
    inspector_name: Optional[str] = None
    decision: QADecisionEnum
    remarks: Optional[str] = None
    disposition_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RetestSubmissionRequest(BaseModel):
    batch_item_id: int
    template_id: int
    defect_id: Optional[int] = None
    results: List[ManualTestValueSubmission]
    resolution_notes: Optional[str] = None


class QualityHistoryItemResponse(BaseModel):
    serial_number: str
    batch_number: Optional[str] = None
    product_model: Optional[str] = None
    current_status: str
    is_defective: bool
    test_sessions: List[TestSessionResponse] = []
    defect_logs: List[DefectLogResponse] = []
    dispositions: List[QADispositionResponse] = []


class DefectSummaryResponse(BaseModel):
    total_defects: int
    open_defects: int
    resolved_defects: int
    by_severity: Dict[str, int] = {}
    top_defect_codes: List[Dict[str, Any]] = []
