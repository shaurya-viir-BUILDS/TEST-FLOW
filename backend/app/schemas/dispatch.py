from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.dispatch import DispatchStatusEnum


class DispatchCreate(BaseModel):
    dispatch_code: str
    batch_id: int
    client_id: Optional[int] = None
    dispatch_date: date = Field(default_factory=date.today)
    status: DispatchStatusEnum = DispatchStatusEnum.READY
    serial_numbers: List[str] = []
    carrier_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    notes: Optional[str] = None


class DispatchResponse(BaseModel):
    id: int
    dispatch_code: str
    batch_id: int
    batch_number: Optional[str] = None
    client_name: Optional[str] = None
    dispatch_date: date
    status: DispatchStatusEnum
    quality_approval: str
    carrier_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    total_units: int
    notes: Optional[str] = None
    created_at: datetime
    dispatched_serials: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class TraceabilityTimelineResponse(BaseModel):
    serial_number: str
    qr_code_hash: Optional[str] = None
    current_status: str
    is_defective: bool
    product: Dict[str, Any]
    inward_batch: Dict[str, Any]
    test_history: List[Dict[str, Any]] = []
    defects: List[Dict[str, Any]] = []
    quality_review: Optional[Dict[str, Any]] = None
    dispatch: Optional[Dict[str, Any]] = None

