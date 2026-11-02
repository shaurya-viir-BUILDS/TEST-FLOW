import csv
import io
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.batch import BatchItem, BatchItemStatusEnum
from app.models.employee import Employee, RoleEnum
from app.models.testing import (
    TestTemplate,
    TestParameter,
    TestSession,
    TestResultDetail,
    TestTaskAllocation,
    TaskAllocationStatusEnum,
    ParameterDataTypeEnum,
    TestExecutionTypeEnum,
    TestResultEnum
)
from app.schemas.testing import ManualTestExecutionRequest, BenchCsvImportResult


def evaluate_parameter(param: TestParameter, measured_val: str) -> Tuple[TestResultEnum, str]:
    """
    Evaluates a measured string against parameter bounds/expectations.
    Returns (PASS/FAIL, normalized_value_str).
    """
    val_clean = str(measured_val).strip()
    
    if param.data_type == ParameterDataTypeEnum.NUMERIC_RANGE:
        try:
            num = float(val_clean)
        except ValueError:
            return TestResultEnum.FAIL, val_clean

        if param.min_limit is not None and num < param.min_limit:
            return TestResultEnum.FAIL, val_clean
        if param.max_limit is not None and num > param.max_limit:
            return TestResultEnum.FAIL, val_clean
        return TestResultEnum.PASS, val_clean

    elif param.data_type == ParameterDataTypeEnum.BOOLEAN:
        truthy = {"true", "1", "yes", "pass", "y", "t", "ok"}
        if val_clean.lower() in truthy:
            return TestResultEnum.PASS, "true"
        return TestResultEnum.FAIL, "false"

    elif param.data_type == ParameterDataTypeEnum.TEXT:
        if param.expected_text:
            if val_clean.lower() == param.expected_text.strip().lower():
                return TestResultEnum.PASS, val_clean
            return TestResultEnum.FAIL, val_clean
        return TestResultEnum.PASS, val_clean

    return TestResultEnum.FAIL, val_clean


def execute_manual_test(
    db: Session,
    request: ManualTestExecutionRequest,
    technician_id: int
) -> TestSession:
    batch_item = db.query(BatchItem).filter(BatchItem.id == request.batch_item_id).first()
    if not batch_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch item with id {request.batch_item_id} not found."
        )

    template = db.query(TestTemplate).filter(TestTemplate.id == request.template_id).first()
    if not template or not template.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active test template with id {request.template_id} not found."
        )

    # 1. Reject testing on terminal / already approved or dispatched states
    disallowed_states = {
        BatchItemStatusEnum.QA_APPROVED,
        BatchItemStatusEnum.QA_SCRAPPED,
        BatchItemStatusEnum.DISPATCHED
    }
    if batch_item.current_status in disallowed_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unit '{batch_item.serial_number}' is in '{batch_item.current_status.value}' state and cannot be tested."
        )

    # 2. Enforce template belongs to product model of unit
    if batch_item.batch and template.product_model_id != batch_item.batch.product_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test template '{template.name}' belongs to a different product model than unit '{batch_item.serial_number}'."
        )

    # 3. Technician assignment check (if allocated to a specific technician, prevent others from testing)
    active_alloc = db.query(TestTaskAllocation).filter(
        TestTaskAllocation.batch_item_id == batch_item.id,
        TestTaskAllocation.status.in_([TaskAllocationStatusEnum.PENDING, TaskAllocationStatusEnum.IN_PROGRESS])
    ).first()
    if not active_alloc:
        active_alloc = db.query(TestTaskAllocation).filter(
            TestTaskAllocation.batch_id == batch_item.batch_id,
            TestTaskAllocation.batch_item_id == None,
            TestTaskAllocation.status.in_([TaskAllocationStatusEnum.PENDING, TaskAllocationStatusEnum.IN_PROGRESS])
        ).first()

    if active_alloc and active_alloc.technician_id != technician_id:
        tech_user = db.query(Employee).filter(Employee.id == technician_id).first()
        if tech_user and tech_user.role == RoleEnum.TEST_TECHNICIAN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unit '{batch_item.serial_number}' is allocated to another technician (ID {active_alloc.technician_id})."
            )

    # Build parameter lookup
    param_map: Dict[int, TestParameter] = {p.id: p for p in template.parameters}

    overall_pass = True
    details_to_create = []

    for sub in request.results:
        param = param_map.get(sub.parameter_id)
        if not param:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown parameter ID {sub.parameter_id} for template '{template.name}'."
            )
        eval_result, norm_val = evaluate_parameter(param, sub.measured_value)
        if eval_result == TestResultEnum.FAIL and param.is_mandatory:
            overall_pass = False

        detail = TestResultDetail(
            parameter_id=param.id,
            measured_value=norm_val,
            result=eval_result
        )
        details_to_create.append(detail)

    submitted_ids = {sub.parameter_id for sub in request.results}
    missing_mandatory = [
        p.parameter_name for p in template.parameters
        if p.is_mandatory and p.id not in submitted_ids
    ]
    if missing_mandatory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing mandatory test parameters: {missing_mandatory}. "
                   f"All mandatory checks must be submitted."
        )

    overall_result = TestResultEnum.PASS if overall_pass else TestResultEnum.FAIL

    session = TestSession(
        batch_item_id=batch_item.id,
        template_id=template.id,
        technician_id=technician_id,
        execution_type=TestExecutionTypeEnum.MANUAL,
        overall_result=overall_result,
        remarks=request.remarks
    )
    db.add(session)
    db.flush()

    for d in details_to_create:
        d.test_session_id = session.id
        db.add(d)

    # Transition unit status
    batch_item.current_status = BatchItemStatusEnum.PASSED if overall_pass else BatchItemStatusEnum.FAILED
    if not overall_pass:
        batch_item.is_defective = True

    db.commit()
    db.refresh(session)
    return session


def parse_bench_csv(
    file_bytes: bytes,
    template_id: int,
    technician_id: int,
    db: Session
) -> BenchCsvImportResult:
    """
    Parses automated test bench CSV export and creates TestSession records.
    Assumes CSV contains 'serial_number' and parameter columns matching template parameter names.
    """
    template = db.query(TestTemplate).filter(TestTemplate.id == template_id).first()
    if not template or not template.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active test template id {template_id} not found."
        )

    # Map normalized parameter name to TestParameter object
    param_name_map = {
        p.parameter_name.lower().replace(" ", "").replace("_", ""): p
        for p in template.parameters
    }

    content_str = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content_str))

    # Identify serial column
    fieldnames = reader.fieldnames or []
    serial_col = None
    for f in fieldnames:
        clean = f.lower().replace(" ", "").replace("_", "")
        if clean in {"serialnumber", "serial", "sn", "deviceid", "unitid"}:
            serial_col = f
            break

    if not serial_col:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV header missing 'serial_number' or 'sn' column."
        )

    processed = 0
    passed = 0
    failed = 0
    failed_items = []

    for row_idx, row in enumerate(reader, start=2):
        raw_sn = row.get(serial_col)
        if not raw_sn:
            continue
        sn = raw_sn.strip().upper()

        item = db.query(BatchItem).filter(BatchItem.serial_number == sn).first()
        if not item:
            failed_items.append({"serial_number": sn, "row": row_idx, "reason": "Serial not registered in system"})
            failed += 1
            processed += 1
            continue

        disallowed_states = {
            BatchItemStatusEnum.QA_APPROVED,
            BatchItemStatusEnum.QA_SCRAPPED,
            BatchItemStatusEnum.DISPATCHED
        }
        if item.current_status in disallowed_states:
            failed_items.append({"serial_number": sn, "row": row_idx, "reason": f"Unit in '{item.current_status.value}' state cannot be tested."})
            failed += 1
            processed += 1
            continue

        if item.batch and template.product_model_id != item.batch.product_model_id:
            failed_items.append({"serial_number": sn, "row": row_idx, "reason": "Test template does not match product model of unit"})
            failed += 1
            processed += 1
            continue

        active_alloc = db.query(TestTaskAllocation).filter(
            TestTaskAllocation.batch_item_id == item.id,
            TestTaskAllocation.status.in_([TaskAllocationStatusEnum.PENDING, TaskAllocationStatusEnum.IN_PROGRESS])
        ).first()
        if not active_alloc:
            active_alloc = db.query(TestTaskAllocation).filter(
                TestTaskAllocation.batch_id == item.batch_id,
                TestTaskAllocation.batch_item_id == None,
                TestTaskAllocation.status.in_([TaskAllocationStatusEnum.PENDING, TaskAllocationStatusEnum.IN_PROGRESS])
            ).first()

        if active_alloc and active_alloc.technician_id != technician_id:
            caller = db.query(Employee).filter(Employee.id == technician_id).first()
            if caller and caller.role == RoleEnum.TEST_TECHNICIAN:
                failed_items.append({"serial_number": sn, "row": row_idx, "reason": f"Unit assigned to technician ID {active_alloc.technician_id}"})
                failed += 1
                processed += 1
                continue

        overall_pass = True
        details = []

        for col_name, raw_val in row.items():
            if col_name == serial_col or raw_val is None:
                continue
            clean_col = col_name.lower().replace(" ", "").replace("_", "")
            param = param_name_map.get(clean_col)
            if not param:
                continue

            eval_res, norm_val = evaluate_parameter(param, str(raw_val))
            if eval_res == TestResultEnum.FAIL and param.is_mandatory:
                overall_pass = False

            details.append(TestResultDetail(
                parameter_id=param.id,
                measured_value=norm_val,
                result=eval_res
            ))

        evaluated_ids = {d.parameter_id for d in details}
        missing_mandatory = [
            p.parameter_name for p in template.parameters
            if p.is_mandatory and p.id not in evaluated_ids
        ]
        if missing_mandatory:
            overall_pass = False

        overall_result = TestResultEnum.PASS if overall_pass else TestResultEnum.FAIL
        session = TestSession(
            batch_item_id=item.id,
            template_id=template.id,
            technician_id=technician_id,
            execution_type=TestExecutionTypeEnum.CSV_IMPORT,
            overall_result=overall_result,
            remarks=f"Imported from bench CSV log (Row {row_idx})"
        )
        db.add(session)
        db.flush()

        for d in details:
            d.test_session_id = session.id
            db.add(d)

        item.current_status = BatchItemStatusEnum.PASSED if overall_pass else BatchItemStatusEnum.FAILED
        if not overall_pass:
            item.is_defective = True
            if missing_mandatory:
                reason = f"Missing mandatory parameters: {missing_mandatory}"
            else:
                reason = "Parameter tolerance failed"
            failed_items.append({"serial_number": sn, "row": row_idx, "reason": reason})
            failed += 1
        else:
            passed += 1

        processed += 1

    db.commit()

    return BenchCsvImportResult(
        processed_units=processed,
        passed_units=passed,
        failed_units=failed,
        failed_serials=failed_items
    )

