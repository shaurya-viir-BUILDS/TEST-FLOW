from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, get_current_user
from app.models.client import Client
from app.models.employee import RoleEnum, Employee
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse

router = APIRouter()


@router.get("/", response_model=List[ClientResponse])
def list_clients(
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    clients = db.query(Client).order_by(Client.name).all()
    results = []
    for c in clients:
        resp = ClientResponse.model_validate(c)
        resp.total_models = len(c.product_models)
        resp.total_batches = len(c.batches)
        results.append(resp)
    return results


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.OPERATIONS_MGR]))
):
    existing = db.query(Client).filter(
        (Client.name == client_in.name.strip()) | (Client.code == client_in.code.strip().upper())
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client with this name or code already exists."
        )

    client = Client(
        name=client_in.name.strip(),
        code=client_in.code.strip().upper(),
        contact_name=client_in.contact_name.strip() if client_in.contact_name else None,
        email=client_in.email.lower().strip() if client_in.email else None,
        phone=client_in.phone.strip() if client_in.phone else None
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    resp = ClientResponse.model_validate(client)
    resp.total_models = 0
    resp.total_batches = 0
    return resp


@router.get("/{id}", response_model=ClientResponse)
def get_client(
    id: int,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    client = db.query(Client).filter(Client.id == id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Client with id {id} not found.")

    resp = ClientResponse.model_validate(client)
    resp.total_models = len(client.product_models)
    resp.total_batches = len(client.batches)
    return resp


@router.put("/{id}", response_model=ClientResponse)
def update_client(
    id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.OPERATIONS_MGR]))
):
    client = db.query(Client).filter(Client.id == id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Client with id {id} not found.")

    if client_in.name is not None:
        client.name = client_in.name.strip()
    if client_in.code is not None:
        client.code = client_in.code.strip().upper()
    if client_in.contact_name is not None:
        client.contact_name = client_in.contact_name.strip()
    if client_in.email is not None:
        client.email = client_in.email.lower().strip()
    if client_in.phone is not None:
        client.phone = client_in.phone.strip()

    db.commit()
    db.refresh(client)

    resp = ClientResponse.model_validate(client)
    resp.total_models = len(client.product_models)
    resp.total_batches = len(client.batches)
    return resp

