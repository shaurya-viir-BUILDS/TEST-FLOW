"""
Loader for the official TestFlow Synthetic Demo Seed dataset.
Loads data/synthetic_demo/seed_data.json into the database with full relational fidelity.
"""
import json
from pathlib import Path
from datetime import datetime, date, time
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.department import Department
from app.models.employee import Employee, RoleEnum
from app.models.client import Client
from app.models.product import ProductModel, ProductCategoryEnum
from app.models.batch import Batch, BatchItem, BatchStatusEnum, BatchItemStatusEnum
from app.models.testing import (
    TestTemplate,
    TestParameter,
    TestSession,
    TestResultDetail,
    TestTaskAllocation,
    ParameterDataTypeEnum,
    TestExecutionTypeEnum,
    TestResultEnum,
    TaskAllocationStatusEnum,
)
from app.models.quality import DefectLog, QADisposition, DefectSeverityEnum, QADecisionEnum
from app.models.dispatch import DispatchOrder, DispatchItem, DispatchStatusEnum
from app.models.attendance import AttendanceRecord, AttendanceStatusEnum, AttendanceSourceEnum

SEED_FILE = Path(__file__).resolve().parents[3] / "data" / "synthetic_demo" / "seed_data.json"


def load_synthetic_demo_seed(db: Session = None):
    owns_session = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        owns_session = True

    try:
        if not SEED_FILE.exists():
            raise FileNotFoundError(f"Seed file not found at: {SEED_FILE}")

        payload = json.loads(SEED_FILE.read_text(encoding="utf-8"))

        print(f"Loading TestFlow Synthetic Demo Seed: {payload['dataset_metadata']['dataset_id']}...")

        # 1. Departments
        depts = {
            "management": ("Operations Management", "DEP-OPS"),
            "hr": ("Human Resources", "DEP-HR"),
            "test_lead": ("Testing Floor Lead", "DEP-LEAD"),
            "tester": ("Testing & Diagnostics", "DEP-TEST"),
            "qa": ("Quality Assurance", "DEP-QA"),
            "store_keeper": ("Warehouse & Inventory", "DEP-STORE"),
        }
        dept_lookup = {}
        for key, (name, code) in depts.items():
            d = db.query(Department).filter(Department.code == code).first()
            if not d:
                d = Department(name=name, code=code)
                db.add(d)
                db.flush()
            dept_lookup[key] = d

        # 2. Employees
        role_map = {
            "management": RoleEnum.OPERATIONS_MGR,
            "hr": RoleEnum.HR_OFFICER,
            "test_lead": RoleEnum.TEST_SUPERVISOR,
            "tester": RoleEnum.TEST_TECHNICIAN,
            "qa": RoleEnum.QA_INSPECTOR,
            "store_keeper": RoleEnum.STORE_KEEPER,
        }
        emp_lookup = {}
        default_pwd_hash = get_password_hash("DemoPass123!")

        for emp_raw in payload["employees"]:
            code = emp_raw["employee_id"]
            existing = db.query(Employee).filter(Employee.emp_code == code).first()
            role = role_map.get(emp_raw["role"], RoleEnum.TEST_TECHNICIAN)
            dept = dept_lookup.get(emp_raw["role"], dept_lookup["tester"])

            # Split display name
            parts = emp_raw["display_name"].split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else "Demo"

            if not existing:
                emp = Employee(
                    emp_code=code,
                    first_name=first_name,
                    last_name=last_name,
                    email=f"{code.lower()}@testflow-demo.local",
                    password_hash=default_pwd_hash,
                    role=role,
                    department_id=dept.id,
                    is_active=emp_raw.get("active", True)
                )
                db.add(emp)
                db.flush()
                emp_lookup[code] = emp
            else:
                emp_lookup[code] = existing

        # 3. Clients
        client_lookup = {}
        for c_raw in payload["clients"]:
            cid = c_raw["client_id"]
            existing = db.query(Client).filter(Client.code == cid).first()
            if not existing:
                client = Client(
                    name=c_raw["name"],
                    code=cid,
                    contact_name=f"Contact for {c_raw['name']}",
                    email=f"contact@{cid.lower()}.demo.local",
                    phone="+1-800-SYNTHETIC"
                )
                db.add(client)
                db.flush()
                client_lookup[cid] = client
            else:
                client_lookup[cid] = existing

        # 4. Test Templates & Parameters
        template_lookup = {}
        for t_raw in payload["test_templates"]:
            tid = t_raw["template_id"]
            existing = db.query(TestTemplate).filter(TestTemplate.name == t_raw["name"]).first()
            
            # Temporary product_model_id = 1 placeholder, will update after models are created
            if not existing:
                t = TestTemplate(
                    product_model_id=1,
                    name=t_raw["name"],
                    version=t_raw.get("version", 1),
                    is_active=True,
                    created_by=emp_lookup["EMP-SYN-005"].id
                )
                db.add(t)
                db.flush()

                for s in t_raw["steps"]:
                    param = TestParameter(
                        template_id=t.id,
                        parameter_name=s["name"],
                        data_type=ParameterDataTypeEnum.NUMERIC_RANGE,
                        min_limit=s["valid_range"]["min"],
                        max_limit=s["valid_range"]["max"],
                        unit_of_measure=s["measurement_unit"],
                        is_mandatory=True,
                        display_order=s["sequence"]
                    )
                    db.add(param)
                db.flush()
                template_lookup[tid] = t
            else:
                template_lookup[tid] = existing

        # 5. Product Models
        cat_map = {
            "wifi_router": ProductCategoryEnum.ROUTER,
            "remote": ProductCategoryEnum.REMOTE_CONTROL,
            "set_top_box": ProductCategoryEnum.SET_TOP_BOX,
        }
        model_lookup = {}
        for m_raw in payload["product_models"]:
            mid = m_raw["model_id"]
            client = client_lookup[m_raw["client_id"]]
            template = template_lookup[m_raw["test_template_id"]]

            existing = db.query(ProductModel).filter(
                ProductModel.client_id == client.id,
                ProductModel.model_number == m_raw["model_code"]
            ).first()

            if not existing:
                pm = ProductModel(
                    client_id=client.id,
                    category=cat_map.get(m_raw["category"], ProductCategoryEnum.OTHER),
                    model_number=m_raw["model_code"],
                    model_name=m_raw["name"],
                    specifications={"synthetic": True, "template_id": m_raw["test_template_id"]}
                )
                db.add(pm)
                db.flush()
                # Link template to this model
                template.product_model_id = pm.id
                model_lookup[mid] = pm
            else:
                model_lookup[mid] = existing

        # 6. Batches
        batch_status_map = {
            "awaiting_registration": BatchStatusEnum.RECEIVED,
            "in_testing": BatchStatusEnum.IN_TESTING,
            "partially_tested": BatchStatusEnum.IN_TESTING,
            "completed": BatchStatusEnum.TESTED,
            "quality_review": BatchStatusEnum.TESTED,
            "rejected": BatchStatusEnum.CANCELLED,
        }
        batch_lookup = {}
        for b_raw in payload["batches"]:
            bid = b_raw["batch_id"]
            existing = db.query(Batch).filter(Batch.batch_number == bid).first()
            model = model_lookup[b_raw["model_id"]]
            status = batch_status_map.get(b_raw["lifecycle_status"], BatchStatusEnum.RECEIVED)

            if not existing:
                batch = Batch(
                    batch_number=bid,
                    client_id=model.client_id,
                    product_model_id=model.id,
                    inward_date=date.fromisoformat(b_raw["received_date"]),
                    challan_number=f"CHAL-{bid}",
                    expected_qty=b_raw["quantity"],
                    received_qty=b_raw["quantity"],
                    current_status=status,
                    storage_location=f"Bay-{bid[-3:]}"
                )
                db.add(batch)
                db.flush()
                batch_lookup[bid] = batch
            else:
                batch_lookup[bid] = existing

        # 7. Products / Batch Items
        product_status_map = {
            "pending": BatchItemStatusEnum.ALLOCATED,
            "passed": BatchItemStatusEnum.PASSED,
            "failed_awaiting_retest": BatchItemStatusEnum.QA_REWORK,
            "quality_review": BatchItemStatusEnum.PASSED,
            "rejected": BatchItemStatusEnum.QA_SCRAPPED,
        }
        product_lookup = {}
        for p_raw in payload["products"]:
            sn = p_raw["serial_number"]
            existing = db.query(BatchItem).filter(BatchItem.serial_number == sn).first()
            batch = batch_lookup[p_raw["batch_id"]]
            item_status = product_status_map.get(p_raw["status"], BatchItemStatusEnum.RECEIVED)

            if not existing:
                item = BatchItem(
                    batch_id=batch.id,
                    serial_number=sn,
                    qr_code_hash=f"QR:{sn}:{batch.id}",
                    current_status=item_status,
                    is_defective=(p_raw["status"] in ("failed_awaiting_retest", "rejected"))
                )
                db.add(item)
                db.flush()
                product_lookup[p_raw["product_id"]] = item
            else:
                product_lookup[p_raw["product_id"]] = existing

        # 8. Test Assignments -> TestTaskAllocation
        assignment_lookup = {}
        for a_raw in payload["test_assignments"]:
            item = product_lookup[a_raw["product_id"]]
            tech = emp_lookup[a_raw["assigned_to_employee_id"]]
            alloc = TestTaskAllocation(
                batch_id=item.batch_id,
                batch_item_id=item.id,
                technician_id=tech.id,
                assigned_by_id=emp_lookup["EMP-SYN-005"].id,
                status=TaskAllocationStatusEnum.COMPLETED if a_raw["status"] == "completed" else TaskAllocationStatusEnum.IN_PROGRESS,
                notes=f"Synthetic assignment {a_raw['assignment_id']}"
            )
            db.add(alloc)
            db.flush()
            assignment_lookup[a_raw["assignment_id"]] = (item, tech, alloc, a_raw["template_id"])

        # 9. Test Results -> TestSession & TestResultDetail
        # Group results by assignment
        results_by_assignment = {}
        for r_raw in payload["test_results"]:
            aid = r_raw["assignment_id"]
            results_by_assignment.setdefault(aid, []).append(r_raw)

        result_lookup = {}
        for aid, r_list in results_by_assignment.items():
            item, tech, alloc, tid = assignment_lookup[aid]
            template = template_lookup.get(tid) or db.query(TestTemplate).first()

            overall_pass = all(r["status"] == "pass" for r in r_list)
            session = TestSession(
                batch_item_id=item.id,
                template_id=template.id,
                technician_id=tech.id,
                execution_type=TestExecutionTypeEnum.MANUAL,
                overall_result=TestResultEnum.PASS if overall_pass else TestResultEnum.FAIL,
                execution_date=datetime.combine(date.fromisoformat(r_list[0].get("tested_at", "2026-10-29")), time(10, 0)),
                remarks="Synthetic test execution"
            )
            db.add(session)
            db.flush()

            # Add details
            param_objs = template.parameters
            for idx, r_raw in enumerate(r_list):
                param = param_objs[idx % len(param_objs)]
                meas_val = str(r_raw["measurement_value"]) if r_raw["measurement_value"] is not None else "0.0"
                det = TestResultDetail(
                    test_session_id=session.id,
                    parameter_id=param.id,
                    measured_value=meas_val,
                    result=TestResultEnum.PASS if r_raw["status"] == "pass" else TestResultEnum.FAIL
                )
                db.add(det)
                result_lookup[r_raw["result_id"]] = (session, det)

        # 10. Defects
        sev_map = {
            "minor": DefectSeverityEnum.MINOR,
            "major": DefectSeverityEnum.MAJOR,
            "critical": DefectSeverityEnum.CRITICAL,
        }
        # Use QA Inspector for defect logging and resolution (fallback to tester if missing)
        qa_inspector = emp_lookup.get("EMP-SYN-013", emp_lookup["EMP-SYN-007"])
        for d_raw in payload["defects"]:
            item = product_lookup[d_raw["product_id"]]
            is_res = (d_raw["status"] == "resolved")
            defect = DefectLog(
                batch_item_id=item.id,
                defect_code=f"DEF-{d_raw['category'].upper()[:4]}",
                severity=sev_map.get(d_raw["severity"], DefectSeverityEnum.MAJOR),
                description=d_raw["description"],
                logged_by=emp_lookup["EMP-SYN-007"].id,
                is_resolved=is_res,
                resolved_by=qa_inspector.id if is_res else None,
                resolution_notes=d_raw.get("resolution") if is_res else None,
                resolved_at=datetime.utcnow() if is_res else None
            )
            db.add(defect)

        # 11. Quality Reviews -> QADisposition
        for q_raw in payload["quality_reviews"]:
            batch = batch_lookup[q_raw["batch_id"]]
            reviewer = emp_lookup[q_raw["reviewed_by_employee_id"]]
            decision = QADecisionEnum.APPROVED if q_raw["status"] == "approved" else (QADecisionEnum.SCRAPPED if q_raw["status"] == "rejected" else QADecisionEnum.RETEST_REQUESTED)

            for item in batch.items:
                disp = QADisposition(
                    batch_item_id=item.id,
                    inspector_id=reviewer.id,
                    decision=decision,
                    remarks=q_raw.get("notes"),
                    disposition_at=datetime.combine(date.fromisoformat(q_raw["review_date"]), time(14, 0))
                )
                db.add(disp)

        # 12. Attendance Records (August - October 2026)
        att_status_map = {
            "present": AttendanceStatusEnum.PRESENT,
            "absent": AttendanceStatusEnum.ABSENT,
            "late": AttendanceStatusEnum.PRESENT,  # late counts as present with punch note
            "half_day": AttendanceStatusEnum.HALF_DAY,
            "leave": AttendanceStatusEnum.ON_LEAVE,
        }
        for att_raw in payload["attendance_records"]:
            emp = emp_lookup[att_raw["employee_id"]]
            att_date = date.fromisoformat(att_raw["attendance_date"])
            status = att_status_map.get(att_raw["status"], AttendanceStatusEnum.PRESENT)

            # Avoid duplicates on (employee_id, date)
            existing = db.query(AttendanceRecord).filter(
                AttendanceRecord.employee_id == emp.id,
                AttendanceRecord.attendance_date == att_date
            ).first()

            if not existing:
                ar = AttendanceRecord(
                    employee_id=emp.id,
                    attendance_date=att_date,
                    punch_in=time(9, 0) if status in (AttendanceStatusEnum.PRESENT, AttendanceStatusEnum.HALF_DAY) else None,
                    punch_out=time(18, 0) if status == AttendanceStatusEnum.PRESENT else (time(13, 0) if status == AttendanceStatusEnum.HALF_DAY else None),
                    status=status,
                    source=AttendanceSourceEnum.MANUAL
                )
                db.add(ar)

        # 13. Dispatches (use Store Keeper role for dispatch creation)
        disp_status_map = {
            "dispatched": DispatchStatusEnum.DISPATCHED,
            "ready": DispatchStatusEnum.READY,
            "held": DispatchStatusEnum.HELD,
            "blocked": DispatchStatusEnum.BLOCKED,
        }
        store_keeper = emp_lookup.get("EMP-SYN-014", emp_lookup["EMP-SYN-001"])
        for d_raw in payload["dispatches"]:
            batch = batch_lookup[d_raw["batch_id"]]
            d_status = disp_status_map.get(d_raw["status"], DispatchStatusEnum.READY)

            existing = db.query(DispatchOrder).filter(DispatchOrder.dispatch_code == d_raw["dispatch_id"]).first()
            if not existing:
                order = DispatchOrder(
                    dispatch_code=d_raw["dispatch_id"],
                    batch_id=batch.id,
                    client_id=batch.client_id,
                    dispatch_date=date.fromisoformat(d_raw["dispatch_date"]),
                    status=d_status,
                    quality_approval=d_raw.get("quality_approval", "approved"),
                    carrier_name="SafeExpress Logistics",
                    vehicle_number="DL-01-SY-2026",
                    total_units=len(d_raw["product_ids"]),
                    notes=f"Synthetic demo dispatch for batch {batch.batch_number}",
                    created_by_id=store_keeper.id
                )
                db.add(order)
                db.flush()

                for pid in d_raw["product_ids"]:
                    item = product_lookup[pid]
                    d_item = DispatchItem(
                        dispatch_order_id=order.id,
                        batch_item_id=item.id
                    )
                    db.add(d_item)
                    if d_status == DispatchStatusEnum.DISPATCHED:
                        item.current_status = BatchItemStatusEnum.DISPATCHED

        db.commit()
        print("✓ TestFlow Synthetic Demo Seed successfully loaded into database!")

    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    load_synthetic_demo_seed()
