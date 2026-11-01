from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProductCategoryEnum(str, enum.Enum):
    ROUTER = "ROUTER"
    SET_TOP_BOX = "SET_TOP_BOX"
    REMOTE_CONTROL = "REMOTE_CONTROL"
    IOT_GATEWAY = "IOT_GATEWAY"
    OTHER = "OTHER"


class ProductModel(Base):
    __tablename__ = "product_models"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(SQLEnum(ProductCategoryEnum), nullable=False)
    model_number = Column(String(100), nullable=False, index=True)
    model_name = Column(String(200), nullable=False)
    specifications = Column(JSON, nullable=True)  # Key-value specs: RF bands, voltage, firmware
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    client = relationship("Client", back_populates="product_models")
    batches = relationship("Batch", back_populates="product_model")

    __table_args__ = (
        UniqueConstraint("client_id", "model_number", name="uix_client_model"),
    )
