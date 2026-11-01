from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, require_role, get_current_user
from app.models.client import Client
from app.models.product import ProductModel
from app.models.batch import Batch, BatchItem, BatchStatusEnum, BatchItemStatusEnum
from app.models.employee import RoleEnum, Employee
from app.schemas.batch import (
    BatchCreate,
    BatchUpdate,
    BatchResponse,
    BatchDetailResponse,
    BatchItemResponse,
    BatchItemBulkImportRequest,
    BatchItemAutoGenerateRequest,
)
from app.services.serialization import register_vendor_serials, auto_generate_batch_serials

router = APIRouter()


def _enrich_batch_response(batch: Batch, db: Session) -> BatchResponse:
    resp = BatchResponse.model_validate(batch)
    resp.client_name = batch.client.name if batch.client else None
    if batch.product_model:
        resp.product_model_number = batch.product_model.model_number
        resp.product_model_name = batch.product_model.model_name

    # Calculate status counts
    counts = db.query(
        BatchItem.current_status,
        func.count(BatchItem.id)
    ).filter(BatchItem.batch_id == batch.id).group_by(BatchItem.current_status).all()

    count_map = {status: cnt for status, cnt in counts}
    resp.total_serials_registered = sum(count_map.values())
    resp.passed_count = count_map.get(BatchItemStatusEnum.PASSED, 0)
    resp.failed_count = count_map.get(BatchItemStatusEnum.FAILED, 0)
    resp.qa_approved_count = count_map.get(BatchItemStatusEnum.QA_APPROVED, 0)
    return resp


@router.get("/", response_model=List[BatchResponse])
def list_batches(
    client_id: Optional[int] = None,
    product_model_id: Optional[int] = None,
    status_filter: Optional[BatchStatusEnum] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    query = db.query(Batch)
    if client_id is not None:
        query = query.filter(Batch.client_id == client_id)
    if product_model_id is not None:
        query = query.filter(Batch.product_model_id == product_model_id)
    if status_filter is not None:
        query = query.filter(Batch.current_status == status_filter)

    batches = query.order_by(Batch.inward_date.desc(), Batch.id.desc()).offset(skip).limit(limit).all()
    return [_enrich_batch_response(b, db) for b in batches]


@router.post("/", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_inward_batch(
    batch_in: BatchCreate,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.STORE_KEEPER, RoleEnum.OPERATIONS_MGR]))
):
    # Verify client and product exist
    client = db.query(Client).filter(Client.id == batch_in.client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Client id {batch_in.client_id} not found.")

    product = db.query(ProductModel).filter(ProductModel.id == batch_in.product_model_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product model id {batch_in.product_model_id} not found.")

    # Check batch_number uniqueness
    existing = db.query(Batch).filter(Batch.batch_number == batch_in.batch_number.strip().upper()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Batch number '{batch_in.batch_number}' already exists.")

    batch = Batch(
        batch_number=batch_in.batch_number.strip().upper(),
        client_id=batch_in.client_id,
        product_model_id=batch_in.product_model_id,
        inward_date=batch_in.inward_date,
        challan_number=batch_in.challan_number.strip() if batch_in.challan_number else None,
        expected_qty=batch_in.expected_qty,
        received_qty=batch_in.received_qty,
        current_status=BatchStatusEnum.RECEIVED,
        storage_location=batch_in.storage_location.strip() if batch_in.storage_location else None
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    return _enrich_batch_response(batch, db)


@router.get("/{id}", response_model=BatchResponse)
def get_batch(
    id: int,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    batch = db.query(Batch).filter(Batch.id == id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch with id {id} not found.")
    return _enrich_batch_response(batch, db)


@router.get("/{id}/items", response_model=List[BatchItemResponse])
def get_batch_items(
    id: int,
    status_filter: Optional[BatchItemStatusEnum] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    batch = db.query(Batch).filter(Batch.id == id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch with id {id} not found.")

    query = db.query(BatchItem).filter(BatchItem.batch_id == id)
    if status_filter:
        query = query.filter(BatchItem.current_status == status_filter)

    items = query.order_by(BatchItem.id).offset(skip).limit(limit).all()
    return items


@router.post("/{id}/serials/bulk-import", response_model=BatchResponse)
def bulk_import_vendor_serials(
    id: int,
    import_in: BatchItemBulkImportRequest,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.STORE_KEEPER]))
):
    batch = db.query(Batch).filter(Batch.id == id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch with id {id} not found.")

    register_vendor_serials(db, batch, import_in.serial_numbers)
    return _enrich_batch_response(batch, db)


@router.post("/{id}/serials/auto-generate", response_model=BatchResponse)
def auto_generate_serials(
    id: int,
    gen_in: BatchItemAutoGenerateRequest,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.STORE_KEEPER]))
):
    batch = db.query(Batch).filter(Batch.id == id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch with id {id} not found.")

    auto_generate_batch_serials(db, batch, prefix=gen_in.prefix, count=gen_in.count)
    return _enrich_batch_response(batch, db)


@router.put("/{id}/status", response_model=BatchResponse)
def update_batch_status(
    id: int,
    new_status: BatchStatusEnum,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.OPERATIONS_MGR, RoleEnum.TEST_SUPERVISOR]))
):
    batch = db.query(Batch).filter(Batch.id == id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch with id {id} not found.")

    batch.current_status = new_status
    db.commit()
    db.refresh(batch)
    return _enrich_batch_response(batch, db)

