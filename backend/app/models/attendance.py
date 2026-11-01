from datetime import datetime, date, time
import enum
from sqlalchemy import Column, Integer, String, Date, Time, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class AttendanceStatusEnum(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    HALF_DAY = "HALF_DAY"
    ON_LEAVE = "ON_LEAVE"


class AttendanceSourceEnum(str, enum.Enum):
    MANUAL = "MANUAL"
    EXCEL_IMPORT = "EXCEL_IMPORT"
    BIOMETRIC_DEVICE = "BIOMETRIC_DEVICE"


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    punch_in = Column(Time, nullable=True)
    punch_out = Column(Time, nullable=True)
    status = Column(SQLEnum(AttendanceStatusEnum), nullable=False, default=AttendanceStatusEnum.PRESENT)
    source = Column(SQLEnum(AttendanceSourceEnum), nullable=False, default=AttendanceSourceEnum.MANUAL)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    employee = relationship("Employee", back_populates="attendance_records")

    __table_args__ = (
        UniqueConstraint("employee_id", "attendance_date", name="uix_employee_date"),
    )

