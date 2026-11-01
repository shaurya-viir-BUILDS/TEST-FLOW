from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.quality import DefectSeverityEnum, QADecisionEnum


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
