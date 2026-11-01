from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class ParameterDataTypeEnum(str, enum.Enum):
    NUMERIC_RANGE = "NUMERIC_RANGE"
    BOOLEAN = "BOOLEAN"
    TEXT = "TEXT"


class TestExecutionTypeEnum(str, enum.Enum):
    MANUAL = "MANUAL"
    CSV_IMPORT = "CSV_IMPORT"


class TestResultEnum(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class TaskAllocationStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TestTemplate(Base):
    __tablename__ = "test_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_model_id = Column(Integer, ForeignKey("product_models.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    product_model = relationship("ProductModel")
    creator = relationship("Employee")
    parameters = relationship("TestParameter", back_populates="template", cascade="all, delete-orphan", order_by="TestParameter.display_order")


class TestParameter(Base):
    __tablename__ = "test_parameters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("test_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    parameter_name = Column(String(150), nullable=False)
    data_type = Column(SQLEnum(ParameterDataTypeEnum), nullable=False)
    min_limit = Column(Float, nullable=True)
    max_limit = Column(Float, nullable=True)
    unit_of_measure = Column(String(30), nullable=True)
    expected_text = Column(String(255), nullable=True)
    is_mandatory = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)

    template = relationship("TestTemplate", back_populates="parameters")


class TestSession(Base):
    __tablename__ = "test_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_item_id = Column(Integer, ForeignKey("batch_items.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("test_templates.id", ondelete="RESTRICT"), nullable=False, index=True)
    technician_id = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)
    execution_type = Column(SQLEnum(TestExecutionTypeEnum), nullable=False, default=TestExecutionTypeEnum.MANUAL)
    overall_result = Column(SQLEnum(TestResultEnum), nullable=False, index=True)
    execution_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    remarks = Column(Text, nullable=True)

    batch_item = relationship("BatchItem")
    template = relationship("TestTemplate")
    technician = relationship("Employee")
    details = relationship("TestResultDetail", back_populates="session", cascade="all, delete-orphan")
    defects = relationship("DefectLog", primaryjoin="TestSession.id == DefectLog.test_session_id", back_populates="test_session")


class TestResultDetail(Base):
    __tablename__ = "test_result_details"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    test_session_id = Column(Integer, ForeignKey("test_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    parameter_id = Column(Integer, ForeignKey("test_parameters.id", ondelete="RESTRICT"), nullable=False, index=True)
    measured_value = Column(String(100), nullable=False)
    result = Column(SQLEnum(TestResultEnum), nullable=False)

    session = relationship("TestSession", back_populates="details")
    parameter = relationship("TestParameter")


class TestTaskAllocation(Base):
    __tablename__ = "test_task_allocations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_item_id = Column(Integer, ForeignKey("batch_items.id", ondelete="SET NULL"), nullable=True, index=True)
    technician_id = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_by_id = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    status = Column(SQLEnum(TaskAllocationStatusEnum), nullable=False, default=TaskAllocationStatusEnum.PENDING, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(String(255), nullable=True)

    batch = relationship("Batch")
    batch_item = relationship("BatchItem")
    technician = relationship("Employee", foreign_keys=[technician_id])
    assigned_by = relationship("Employee", foreign_keys=[assigned_by_id])
