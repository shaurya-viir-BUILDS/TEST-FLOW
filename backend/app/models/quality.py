from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class DefectSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class QADecisionEnum(str, enum.Enum):
    APPROVED = "APPROVED"
    RETEST_REQUESTED = "RETEST_REQUESTED"
    SCRAPPED = "SCRAPPED"


class DefectLog(Base):
    __tablename__ = "defect_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_item_id = Column(Integer, ForeignKey("batch_items.id", ondelete="CASCADE"), nullable=False, index=True)
    test_session_id = Column(Integer, ForeignKey("test_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    defect_code = Column(String(50), nullable=False, index=True)
    severity = Column(SQLEnum(DefectSeverityEnum), nullable=False, default=DefectSeverityEnum.MAJOR)
    description = Column(Text, nullable=False)
    logged_by = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch_item = relationship("BatchItem")
    test_session = relationship("TestSession", back_populates="defects")
    author = relationship("Employee")


class QADisposition(Base):
    __tablename__ = "qa_dispositions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_item_id = Column(Integer, ForeignKey("batch_items.id", ondelete="CASCADE"), nullable=False, index=True)
    inspector_id = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    decision = Column(SQLEnum(QADecisionEnum), nullable=False, index=True)
    remarks = Column(Text, nullable=True)
    disposition_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    batch_item = relationship("BatchItem")
    inspector = relationship("Employee")
