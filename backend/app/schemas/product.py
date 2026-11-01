from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.models.product import ProductCategoryEnum


class ProductModelBase(BaseModel):
    client_id: int
    category: ProductCategoryEnum
    model_number: str
    model_name: str
    specifications: Optional[Dict[str, Any]] = None


class ProductModelCreate(ProductModelBase):
    pass


class ProductModelUpdate(BaseModel):
    category: Optional[ProductCategoryEnum] = None
    model_number: Optional[str] = None
    model_name: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None


class ProductModelResponse(ProductModelBase):
    id: int
    client_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
