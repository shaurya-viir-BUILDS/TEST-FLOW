from datetime import datetime, date
import enum
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base


class BatchStatusEnum(str, enum.Enum):
    RECEIVED = "RECEIVED"
    ALLOCATED = "ALLOCATED"
    IN_TESTING = "IN_TESTING"
    TESTED = "TESTED"
    QA_APPROVED = "QA_APPROVED"
    DISPATCHED = "DISPATCHED"
    CANCELLED = "CANCELLED"


class BatchItemStatusEnum(str, enum.Enum):
    RECEIVED = "RECEIVED"
    ALLOCATED = "ALLOCATED"
    IN_TESTING = "IN_TESTING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    QA_APPROVED = "QA_APPROVED"
    QA_REWORK = "QA_REWORK"
    QA_SCRAPPED = "QA_SCRAPPED"
    DISPATCHED = "DISPATCHED"


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_number = Column(String(100), unique=True, nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_model_id = Column(Integer, ForeignKey("product_models.id", ondelete="RESTRICT"), nullable=False, index=True)
    inward_date = Column(Date, default=date.today, nullable=False, index=True)
    challan_number = Column(String(100), nullable=True)
    expected_qty = Column(Integer, nullable=False)
    received_qty = Column(Integer, nullable=False)
    current_status = Column(SQLEnum(BatchStatusEnum), nullable=False, default=BatchStatusEnum.RECEIVED, index=True)
    storage_location = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    client = relationship("Client", back_populates="batches")
    product_model = relationship("ProductModel", back_populates="batches")
    items = relationship("BatchItem", back_populates="batch", cascade="all, delete-orphan")


class BatchItem(Base):
    __tablename__ = "batch_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True)
    serial_number = Column(String(150), unique=True, nullable=False, index=True)
    qr_code_hash = Column(String(255), nullable=True, index=True)
    current_status = Column(SQLEnum(BatchItemStatusEnum), nullable=False, default=BatchItemStatusEnum.RECEIVED, index=True)
    is_defective = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch = relationship("Batch", back_populates="items")

