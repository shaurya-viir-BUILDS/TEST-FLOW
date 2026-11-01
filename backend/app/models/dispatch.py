from datetime import datetime, date
import enum
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum as SQLEnum, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class DispatchStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    HELD = "HELD"
    BLOCKED = "BLOCKED"


class DispatchOrder(Base):
    __tablename__ = "dispatch_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dispatch_code = Column(String(100), unique=True, nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    dispatch_date = Column(Date, default=date.today, nullable=False, index=True)
    status = Column(SQLEnum(DispatchStatusEnum), nullable=False, default=DispatchStatusEnum.DRAFT, index=True)
    quality_approval = Column(String(50), nullable=False, default="pending")  # approved, pending, rejected
    carrier_name = Column(String(150), nullable=True)
    vehicle_number = Column(String(50), nullable=True)
    total_units = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch = relationship("Batch")
    client = relationship("Client")
    creator = relationship("Employee")
    items = relationship("DispatchItem", back_populates="dispatch_order", cascade="all, delete-orphan")


class DispatchItem(Base):
    __tablename__ = "dispatch_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dispatch_order_id = Column(Integer, ForeignKey("dispatch_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_item_id = Column(Integer, ForeignKey("batch_items.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)

    dispatch_order = relationship("DispatchOrder", back_populates="items")
    batch_item = relationship("BatchItem")
