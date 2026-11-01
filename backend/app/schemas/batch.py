from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.batch import BatchStatusEnum, BatchItemStatusEnum


class BatchBase(BaseModel):
    client_id: int
    product_model_id: int
    batch_number: str
    inward_date: date = Field(default_factory=date.today)
    challan_number: Optional[str] = None
    expected_qty: int = Field(gt=0)
    received_qty: int = Field(gt=0)
    storage_location: Optional[str] = None


class BatchCreate(BatchBase):
    pass


class BatchUpdate(BaseModel):
    challan_number: Optional[str] = None
    expected_qty: Optional[int] = Field(None, gt=0)
    received_qty: Optional[int] = Field(None, gt=0)
    storage_location: Optional[str] = None
    current_status: Optional[BatchStatusEnum] = None


class BatchItemResponse(BaseModel):
    id: int
    batch_id: int
    serial_number: str
    qr_code_hash: Optional[str] = None
    current_status: BatchItemStatusEnum
    is_defective: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchResponse(BatchBase):
    id: int
    current_status: BatchStatusEnum
    created_at: datetime
    client_name: Optional[str] = None
    product_model_number: Optional[str] = None
    product_model_name: Optional[str] = None
    total_serials_registered: int = 0
    passed_count: int = 0
    failed_count: int = 0
    qa_approved_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BatchDetailResponse(BatchResponse):
    items: List[BatchItemResponse] = []


class BatchItemBulkImportRequest(BaseModel):
    serial_numbers: List[str] = Field(..., min_length=1)


class BatchItemAutoGenerateRequest(BaseModel):
    prefix: Optional[str] = None
    count: Optional[int] = Field(None, gt=0)


class BatchItemStatusUpdate(BaseModel):
    status: BatchItemStatusEnum
    is_defective: Optional[bool] = None
