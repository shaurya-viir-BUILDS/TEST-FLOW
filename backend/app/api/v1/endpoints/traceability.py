from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.employee import Employee
from app.models.batch import BatchItem
from app.models.testing import TestSession
from app.models.quality import DefectLog, QADisposition
from app.models.dispatch import DispatchItem, DispatchOrder
from app.schemas.dispatch import TraceabilityTimelineResponse

router = APIRouter()


@router.get("/{serial_number}", response_model=TraceabilityTimelineResponse)
def get_serial_traceability(
    serial_number: str,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    """
    Universal Serial Number Traceability Query:
    Reconstructs the unbroken cradle-to-grave operational lifecycle of any unit:
    Inward Batch -> Test Executions -> Defect Logs -> QA Dispositions -> Dispatch Order.
    """
    sn_clean = serial_number.strip().upper()
    item = db.query(BatchItem).filter(BatchItem.serial_number == sn_clean).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Serial number '{sn_clean}' not found in system records."
        )

    batch = item.batch
    product = batch.product_model if batch else None
    client = batch.client if batch else None

    # 1. Product details
    product_info = {
        "model_number": product.model_number if product else "Unknown",
        "model_name": product.model_name if product else "Unknown",
        "category": product.category.value if product and hasattr(product.category, "value") else str(product.category if product else "Unknown"),
        "client_name": client.name if client else "Unknown",
        "client_code": client.code if client else "Unknown",
    }

    # 2. Inward lot details
    inward_info = {
        "batch_id": batch.id if batch else None,
        "batch_number": batch.batch_number if batch else "Unknown",
        "inward_date": str(batch.inward_date) if batch else None,
        "challan_number": batch.challan_number if batch else None,
        "storage_location": batch.storage_location if batch else None,
        "batch_lifecycle_status": batch.current_status.value if batch and hasattr(batch.current_status, "value") else str(batch.current_status if batch else "Unknown"),
    }

    # 3. Test Sessions & Measurements
    sessions = db.query(TestSession).filter(TestSession.batch_item_id == item.id).order_by(TestSession.execution_date.asc()).all()
    test_history = []
    for s in sessions:
        details = [
            {
                "parameter": d.parameter.parameter_name if d.parameter else f"Param #{d.parameter_id}",
                "measured_value": d.measured_value,
                "unit": d.parameter.unit_of_measure if d.parameter else None,
                "result": d.result.value if hasattr(d.result, "value") else str(d.result)
            }
            for d in s.details
        ]
        test_history.append({
            "session_id": s.id,
            "template_name": s.template.name if s.template else None,
            "technician": f"{s.technician.first_name} {s.technician.last_name}" if s.technician else "Unknown",
            "execution_type": s.execution_type.value if hasattr(s.execution_type, "value") else str(s.execution_type),
            "overall_result": s.overall_result.value if hasattr(s.overall_result, "value") else str(s.overall_result),
            "execution_date": s.execution_date.isoformat(),
            "remarks": s.remarks,
            "measurements": details
        })

    # 4. Defect Records
    defects = db.query(DefectLog).filter(DefectLog.batch_item_id == item.id).order_by(DefectLog.created_at.asc()).all()
    defect_history = []
    for d in defects:
        defect_history.append({
            "defect_id": d.id,
            "defect_code": d.defect_code,
            "severity": d.severity.value if hasattr(d.severity, "value") else str(d.severity),
            "description": d.description,
            "logged_by": f"{d.author.first_name} {d.author.last_name}" if d.author else "Unknown",
            "created_at": d.created_at.isoformat(),
            "is_resolved": d.is_resolved,
            "resolution_notes": d.resolution_notes,
            "resolved_by": f"{d.resolver.first_name} {d.resolver.last_name}" if d.resolver else None,
            "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None
        })

    # 5. Quality Disposition
    latest_disp = db.query(QADisposition).filter(QADisposition.batch_item_id == item.id).order_by(QADisposition.disposition_at.desc()).first()
    qa_info = None
    if latest_disp:
        qa_info = {
            "decision": latest_disp.decision.value if hasattr(latest_disp.decision, "value") else str(latest_disp.decision),
            "inspector": f"{latest_disp.inspector.first_name} {latest_disp.inspector.last_name}" if latest_disp.inspector else "Unknown",
            "remarks": latest_disp.remarks,
            "disposition_at": latest_disp.disposition_at.isoformat()
        }

    # 6. Dispatch info
    dispatch_item = db.query(DispatchItem).filter(DispatchItem.batch_item_id == item.id).first()
    dispatch_info = None
    if dispatch_item and dispatch_item.dispatch_order:
        do = dispatch_item.dispatch_order
        dispatch_info = {
            "dispatch_id": do.id,
            "dispatch_code": do.dispatch_code,
            "dispatch_date": str(do.dispatch_date),
            "status": do.status.value if hasattr(do.status, "value") else str(do.status),
            "carrier_name": do.carrier_name,
            "vehicle_number": do.vehicle_number,
            "notes": do.notes
        }

    return TraceabilityTimelineResponse(
        serial_number=item.serial_number,
        qr_code_hash=item.qr_code_hash,
        current_status=item.current_status.value if hasattr(item.current_status, "value") else str(item.current_status),
        is_defective=item.is_defective,
        product=product_info,
        inward_batch=inward_info,
        test_history=test_history,
        defects=defect_history,
        quality_review=qa_info,
        dispatch=dispatch_info
    )

