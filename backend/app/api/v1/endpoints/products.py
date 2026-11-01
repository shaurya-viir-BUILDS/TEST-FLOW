from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, get_current_user
from app.models.client import Client
from app.models.product import ProductModel, ProductCategoryEnum
from app.models.employee import RoleEnum, Employee
from app.schemas.product import ProductModelCreate, ProductModelUpdate, ProductModelResponse

router = APIRouter()


@router.get("/", response_model=List[ProductModelResponse])
def list_products(
    client_id: Optional[int] = None,
    category: Optional[ProductCategoryEnum] = None,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    query = db.query(ProductModel)
    if client_id is not None:
        query = query.filter(ProductModel.client_id == client_id)
    if category is not None:
        query = query.filter(ProductModel.category == category)

    models = query.order_by(ProductModel.model_name).all()
    results = []
    for m in models:
        resp = ProductModelResponse.model_validate(m)
        resp.client_name = m.client.name if m.client else None
        results.append(resp)
    return results


@router.post("/", response_model=ProductModelResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    prod_in: ProductModelCreate,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.OPERATIONS_MGR, RoleEnum.TEST_SUPERVISOR]))
):
    # Verify client exists
    client = db.query(Client).filter(Client.id == prod_in.client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Client with id {prod_in.client_id} not found.")

    # Check unique model_number per client
    existing = db.query(ProductModel).filter(
        ProductModel.client_id == prod_in.client_id,
        ProductModel.model_number == prod_in.model_number.strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model number '{prod_in.model_number}' already registered for client '{client.name}'."
        )

    product = ProductModel(
        client_id=prod_in.client_id,
        category=prod_in.category,
        model_number=prod_in.model_number.strip().upper(),
        model_name=prod_in.model_name.strip(),
        specifications=prod_in.specifications
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    resp = ProductModelResponse.model_validate(product)
    resp.client_name = client.name
    return resp


@router.get("/{id}", response_model=ProductModelResponse)
def get_product(
    id: int,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with id {id} not found.")

    resp = ProductModelResponse.model_validate(product)
    resp.client_name = product.client.name if product.client else None
    return resp


@router.put("/{id}", response_model=ProductModelResponse)
def update_product(
    id: int,
    prod_in: ProductModelUpdate,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.OPERATIONS_MGR]))
):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with id {id} not found.")

    if prod_in.category is not None:
        product.category = prod_in.category
    if prod_in.model_number is not None:
        product.model_number = prod_in.model_number.strip().upper()
    if prod_in.model_name is not None:
        product.model_name = prod_in.model_name.strip()
    if prod_in.specifications is not None:
        product.specifications = prod_in.specifications

    db.commit()
    db.refresh(product)

    resp = ProductModelResponse.model_validate(product)
    resp.client_name = product.client.name if product.client else None
    return resp

