from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.testing import ParameterDataTypeEnum, TestExecutionTypeEnum, TestResultEnum, TaskAllocationStatusEnum


class TestParameterBase(BaseModel):
    parameter_name: str
    data_type: ParameterDataTypeEnum
    min_limit: Optional[float] = None
    max_limit: Optional[float] = None
    unit_of_measure: Optional[str] = None
    expected_text: Optional[str] = None
    is_mandatory: bool = True
    display_order: int = 0


class TestParameterCreate(TestParameterBase):
    pass


class TestParameterResponse(TestParameterBase):
    id: int
    template_id: int

    model_config = ConfigDict(from_attributes=True)


class TestTemplateBase(BaseModel):
    product_model_id: int
    name: str
    version: int = 1
    is_active: bool = True


class TestTemplateCreate(TestTemplateBase):
    parameters: List[TestParameterCreate] = Field(..., min_length=1)


class TestTemplateResponse(TestTemplateBase):
    id: int
    created_at: datetime
    product_model_number: Optional[str] = None
    product_model_name: Optional[str] = None
    parameter_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TestTemplateDetailResponse(TestTemplateResponse):
    parameters: List[TestParameterResponse] = []


class ManualTestValueSubmission(BaseModel):
    parameter_id: int
    measured_value: str


class ManualTestExecutionRequest(BaseModel):
    batch_item_id: int
    template_id: int
    results: List[ManualTestValueSubmission]
    remarks: Optional[str] = None


class TestResultDetailResponse(BaseModel):
    id: Optional[int] = None
    parameter_id: int
    parameter_name: Optional[str] = None
    measured_value: str
    result: TestResultEnum

    model_config = ConfigDict(from_attributes=True)


class TestSessionResponse(BaseModel):
    id: int
    batch_item_id: int
    serial_number: Optional[str] = None
    template_name: Optional[str] = None
    technician_name: Optional[str] = None
    execution_type: TestExecutionTypeEnum
    overall_result: TestResultEnum
    execution_date: datetime
    remarks: Optional[str] = None
    details: List[TestResultDetailResponse] = []

    model_config = ConfigDict(from_attributes=True)


class BenchCsvImportResult(BaseModel):
    processed_units: int
    passed_units: int
    failed_units: int
    failed_serials: List[Dict[str, Any]] = []


# Task Allocation & Batch Progress Schemas
class TaskAllocationCreate(BaseModel):
    batch_id: int
    technician_id: int
    serial_numbers: Optional[List[str]] = None
    notes: Optional[str] = None


class TaskAllocationResponse(BaseModel):
    id: int
    batch_id: int
    batch_number: Optional[str] = None
    technician_id: int
    technician_name: Optional[str] = None
    status: TaskAllocationStatusEnum
    assigned_at: datetime
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BatchTestingProgressResponse(BaseModel):
    batch_id: int
    batch_number: str
    product_model_name: Optional[str] = None
    total_units: int
    units_received: int
    units_allocated: int
    units_in_testing: int
    units_passed: int
    units_failed: int
    units_qa_approved: int
    units_qa_rework: int
    units_qa_scrapped: int
    completion_percentage: float
    first_pass_yield: float
    active_technicians: List[str] = []
