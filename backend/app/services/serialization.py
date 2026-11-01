import hashlib
from typing import List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.batch import Batch, BatchItem, BatchItemStatusEnum


def generate_qr_hash(serial_number: str, batch_id: int) -> str:
    """Generates a secure, deterministic hash token representing the physical QR payload."""
    raw = f"TESTFLOW:BID={batch_id}:SN={serial_number}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def register_vendor_serials(
    db: Session,
    batch: Batch,
    serial_numbers: List[str]
) -> Tuple[int, List[BatchItem]]:
    """
    Registers a list of pre-printed vendor serial numbers against an inward batch.
    Rejects any duplicates already registered in the system.
    """
    clean_serials = [s.strip().upper() for s in serial_numbers if s.strip()]
    if not clean_serials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid serial numbers provided."
        )

    # Check for duplicates in the provided payload
    if len(clean_serials) != len(set(clean_serials)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload contains duplicate serial numbers."
        )

    # Check against database for existing collisions
    existing_items = db.query(BatchItem.serial_number).filter(
        BatchItem.serial_number.in_(clean_serials)
    ).all()
    if existing_items:
        conflicts = [item[0] for item in existing_items]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The following serial numbers already exist in the system: {conflicts[:5]}"
        )

    # Create batch items
    new_items = []
    for sn in clean_serials:
        qr_hash = generate_qr_hash(sn, batch.id)
        item = BatchItem(
            batch_id=batch.id,
            serial_number=sn,
            qr_code_hash=qr_hash,
            current_status=BatchItemStatusEnum.RECEIVED,
            is_defective=False
        )
        new_items.append(item)

    db.add_all(new_items)
    db.commit()

    return len(new_items), new_items


def auto_generate_batch_serials(
    db: Session,
    batch: Batch,
    prefix: str = None,
    count: int = None
) -> Tuple[int, List[BatchItem]]:
    """
    Auto-generates sequential serial numbers and QR hashes for internal sticker printing.
    Example output format: TF-AX3000-0001 through TF-AX3000-0100
    """
    qty_to_generate = count or batch.received_qty
    if qty_to_generate <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity to generate must be greater than zero."
        )

    # Determine prefix
    if not prefix:
        model_tag = batch.product_model.model_number.replace(" ", "").replace("-", "")[:8].upper()
        prefix = f"TF-{model_tag}"

    # Find the maximum existing sequence number for this prefix
    # Pattern: PREFIX-0001
    existing = db.query(BatchItem.serial_number).filter(
        BatchItem.serial_number.like(f"{prefix}-%")
    ).all()
    
    max_seq = 0
    for (sn,) in existing:
        try:
            parts = sn.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                max_seq = max(max_seq, int(parts[1]))
        except (ValueError, IndexError):
            continue

    new_items = []
    for i in range(1, qty_to_generate + 1):
        seq = max_seq + i
        sn = f"{prefix}-{seq:04d}"
        qr_hash = generate_qr_hash(sn, batch.id)
        item = BatchItem(
            batch_id=batch.id,
            serial_number=sn,
            qr_code_hash=qr_hash,
            current_status=BatchItemStatusEnum.RECEIVED,
            is_defective=False
        )
        new_items.append(item)

    db.add_all(new_items)
    db.commit()

    return len(new_items), new_items
