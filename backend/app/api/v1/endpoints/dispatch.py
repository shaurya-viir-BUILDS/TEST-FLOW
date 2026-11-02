from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, get_current_user
from app.models.employee import RoleEnum, Employee
from app.models.batch import Batch, BatchItem, BatchItemStatusEnum, BatchStatusEnum
from app.models.dispatch import DispatchOrder, DispatchItem, DispatchStatusEnum
from app.schemas.dispatch import DispatchCreate, DispatchResponse

router = APIRouter()


def _format_dispatch_response(d: DispatchOrder) -> DispatchResponse:
    resp = DispatchResponse.model_validate(d)
    if d.batch:
        resp.batch_number = d.batch.batch_number
        if d.batch.client:
            resp.client_name = d.batch.client.name
    serials = [item.batch_item.serial_number for item in d.items if item.batch_item]
    resp.dispatched_serials = serials
    resp.total_units = len(serials)
    return resp


@router.get("/", response_model=List[DispatchResponse])
def list_dispatches(
    batch_id: Optional[int] = None,
    status_filter: Optional[DispatchStatusEnum] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    query = db.query(DispatchOrder)
    if batch_id is not None:
        query = query.filter(DispatchOrder.batch_id == batch_id)
    if status_filter is not None:
        query = query.filter(DispatchOrder.status == status_filter)

    dispatches = query.order_by(DispatchOrder.dispatch_date.desc(), DispatchOrder.id.desc()).offset(skip).limit(limit).all()
    return [_format_dispatch_response(d) for d in dispatches]


@router.post("/", response_model=DispatchResponse, status_code=status.HTTP_201_CREATED)
def create_dispatch_order(
    disp_in: DispatchCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.STORE_KEEPER, RoleEnum.OPERATIONS_MGR]))
):
    """
    Creates an outbound dispatch order.
    Enforces strict quality gate rules:
    - READY/DISPATCHED orders may include only per-unit QA_APPROVED serials.
    - One unit's QA approval does not approve the rest of the batch.
    - HELD or BLOCKED dispatches cannot contain units.
    """
    batch = db.query(Batch).filter(Batch.id == disp_in.batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch {disp_in.batch_id} not found.")

    # Check for duplicate dispatch_code
    existing = db.query(DispatchOrder).filter(DispatchOrder.dispatch_code == disp_in.dispatch_code.strip().upper()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Dispatch code '{disp_in.dispatch_code}' already exists.")

    # Invariant: HELD or BLOCKED dispatches must not include products
    if disp_in.status in (DispatchStatusEnum.HELD, DispatchStatusEnum.BLOCKED) and disp_in.serial_numbers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dispatch with status '{disp_in.status.value}' cannot contain products (must be empty list)."
        )

    # Validate serial units FIRST before touching database session
    items_to_dispatch = []
    if disp_in.serial_numbers:
        clean_serials = [s.strip().upper() for s in disp_in.serial_numbers if s.strip()]
        items = db.query(BatchItem).filter(
            BatchItem.batch_id == batch.id,
            BatchItem.serial_number.in_(clean_serials)
        ).all()

        found_serials = {i.serial_number for i in items}
        missing = set(clean_serials) - found_serials
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The following serials do not belong to batch {batch.batch_number}: {list(missing)[:5]}"
            )

        for item in items:
            if item.current_status == BatchItemStatusEnum.DISPATCHED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unit {item.serial_number} has already been dispatched."
                )
            if item.current_status != BatchItemStatusEnum.QA_APPROVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unit {item.serial_number} is in '{item.current_status.value}' state. "
                           f"Only QA_APPROVED units can be dispatched. "
                           f"Each unit must be individually approved by a QA inspector before dispatch."
                )
            existing_d_item = db.query(DispatchItem).filter(DispatchItem.batch_item_id == item.id).first()
            if existing_d_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unit {item.serial_number} is already attached to dispatch order #{existing_d_item.dispatch_order_id}."
                )
            items_to_dispatch.append(item)

    if disp_in.status in (DispatchStatusEnum.READY, DispatchStatusEnum.DISPATCHED):
        qa_approval_label = "approved"
    elif disp_in.status == DispatchStatusEnum.BLOCKED:
        qa_approval_label = "rejected"
    else:
        qa_approval_label = "pending"

    client_id = disp_in.client_id or batch.client_id

    dispatch = DispatchOrder(
        dispatch_code=disp_in.dispatch_code.strip().upper(),
        batch_id=batch.id,
        client_id=client_id,
        dispatch_date=disp_in.dispatch_date,
        status=disp_in.status,
        quality_approval=qa_approval_label,
        carrier_name=disp_in.carrier_name,
        vehicle_number=disp_in.vehicle_number,
        total_units=len(items_to_dispatch),
        notes=disp_in.notes,
        created_by_id=current_user.id
    )
    db.add(dispatch)
    db.flush()

    for item in items_to_dispatch:
        d_item = DispatchItem(
            dispatch_order_id=dispatch.id,
            batch_item_id=item.id
        )
        db.add(d_item)
        if disp_in.status == DispatchStatusEnum.DISPATCHED:
            item.current_status = BatchItemStatusEnum.DISPATCHED

    if disp_in.status == DispatchStatusEnum.DISPATCHED and items_to_dispatch:
        batch.current_status = BatchStatusEnum.DISPATCHED

    db.commit()
    db.refresh(dispatch)
    return _format_dispatch_response(dispatch)


@router.get("/{id}", response_model=DispatchResponse)
def get_dispatch(
    id: int,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    dispatch = db.query(DispatchOrder).filter(DispatchOrder.id == id).first()
    if not dispatch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispatch order with id {id} not found.")
    return _format_dispatch_response(dispatch)


@router.put("/{id}/status", response_model=DispatchResponse)
def update_dispatch_status(
    id: int,
    new_status: DispatchStatusEnum,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.STORE_KEEPER, RoleEnum.OPERATIONS_MGR]))
):
    dispatch = db.query(DispatchOrder).filter(DispatchOrder.id == id).first()
    if not dispatch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispatch order with id {id} not found.")

    if new_status == DispatchStatusEnum.DISPATCHED:
        for item in dispatch.items:
            if item.batch_item:
                if item.batch_item.current_status != BatchItemStatusEnum.QA_APPROVED and item.batch_item.current_status != BatchItemStatusEnum.DISPATCHED:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unit '{item.batch_item.serial_number}' is in '{item.batch_item.current_status.value}' state. Only QA_APPROVED units can be dispatched."
                    )
                item.batch_item.current_status = BatchItemStatusEnum.DISPATCHED
        if dispatch.batch:
            dispatch.batch.current_status = BatchStatusEnum.DISPATCHED

    dispatch.status = new_status

    db.commit()
    db.refresh(dispatch)
    return _format_dispatch_response(dispatch)
