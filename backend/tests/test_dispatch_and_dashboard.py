import pytest
from datetime import date
from app.models.employee import Employee, RoleEnum
from app.core.security import create_access_token, get_password_hash


@pytest.fixture
def store_headers(db_session):
    store = Employee(
        emp_code="EMP-STORE-99",
        first_name="Store",
        last_name="Keeper",
        email="store@test.com",
        password_hash=get_password_hash("Password123!"),
        role=RoleEnum.STORE_KEEPER,
        is_active=True
    )
    db_session.add(store)
    db_session.commit()
    token = create_access_token(subject=store.id, role=store.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def setup_dispatch_batch(client, admin_headers):
    # 1. Client & Model
    c_res = client.post("/api/v1/clients/", headers=admin_headers, json={"name": "Dispatch OEM", "code": "DSP-OEM"})
    cid = c_res.json()["id"]

    p_res = client.post(
        "/api/v1/products/",
        headers=admin_headers,
        json={"client_id": cid, "category": "ROUTER", "model_number": "RTR-DISP", "model_name": "Dispatch Router"}
    )
    pid = p_res.json()["id"]

    # 2. Inward Batch with 2 units
    b_res = client.post(
        "/api/v1/batches/",
        headers=admin_headers,
        json={"client_id": cid, "product_model_id": pid, "batch_number": "BAT-DSP-001", "expected_qty": 2, "received_qty": 2}
    )
    bid = b_res.json()["id"]

    # 3. Serials
    client.post(
        f"/api/v1/batches/{bid}/serials/bulk-import",
        headers=admin_headers,
        json={"serial_numbers": ["DSP-SN-001", "DSP-SN-002"]}
    )
    items = client.get(f"/api/v1/batches/{bid}/items", headers=admin_headers).json()

    # Template
    t_res = client.post(
        "/api/v1/test-templates/",
        headers=admin_headers,
        json={
            "product_model_id": pid,
            "name": "Dispatch Verification Template",
            "parameters": [
                {"parameter_name": "Voltage Check", "data_type": "NUMERIC_RANGE", "min_limit": 11.0, "max_limit": 13.0, "is_mandatory": True}
            ]
        }
    )
    tid = t_res.json()["id"]
    param_id = t_res.json()["parameters"][0]["id"]

    return {
        "batch_id": bid,
        "template_id": tid,
        "param_id": param_id,
        "items": items
    }


def test_dispatch_order_creation_and_eligibility(client, store_headers, admin_headers, setup_dispatch_batch):
    setup = setup_dispatch_batch
    bid = setup["batch_id"]
    tid = setup["template_id"]
    param_id = setup["param_id"]
    item_pass = setup["items"][0]["id"]
    item_fail = setup["items"][1]["id"]

    # 1. Test unit 1 to PASS
    client.post(
        "/api/v1/testing/manual",
        headers=admin_headers,
        json={"batch_item_id": item_pass, "template_id": tid, "results": [{"parameter_id": param_id, "measured_value": "12.0"}]}
    )
    # Unit 2 remains un-tested / NOT approved

    # 2. Attempt dispatch with un-tested unit -> MUST FAIL with 400
    res_fail = client.post(
        "/api/v1/dispatch/",
        headers=store_headers,
        json={
            "dispatch_code": "DSP-ORDER-001",
            "batch_id": bid,
            "status": "DISPATCHED",
            "serial_numbers": ["DSP-SN-002"]
        }
    )
    assert res_fail.status_code == 400
    assert "Only QA_APPROVED units can be dispatched" in res_fail.json()["detail"]

    # 2b. Attempt dispatch with merely PASSED unit (no QA) -> MUST ALSO FAIL
    res_passed_no_qa = client.post(
        "/api/v1/dispatch/",
        headers=store_headers,
        json={
            "dispatch_code": "DSP-ORDER-001",
            "batch_id": bid,
            "status": "DISPATCHED",
            "serial_numbers": ["DSP-SN-001"]
        }
    )
    assert res_passed_no_qa.status_code == 400
    assert "Only QA_APPROVED units can be dispatched" in res_passed_no_qa.json()["detail"]

    # 3. QA-approve unit 1, then dispatch -> SUCCEEDS
    client.post(
        "/api/v1/quality/disposition",
        headers=admin_headers,
        json={"batch_item_id": item_pass, "decision": "APPROVED", "remarks": "QA sign-off"}
    )

    res_pass = client.post(
        "/api/v1/dispatch/",
        headers=store_headers,
        json={
            "dispatch_code": "DSP-ORDER-001",
            "batch_id": bid,
            "status": "DISPATCHED",
            "serial_numbers": ["DSP-SN-001"],
            "carrier_name": "FedEx Ground"
        }
    )
    assert res_pass.status_code == 201
    disp_data = res_pass.json()
    assert disp_data["dispatch_code"] == "DSP-ORDER-001"
    assert disp_data["total_units"] == 1
    assert "DSP-SN-001" in disp_data["dispatched_serials"]


def test_held_dispatch_cannot_contain_units(client, store_headers, setup_dispatch_batch):
    setup = setup_dispatch_batch
    bid = setup["batch_id"]

    res = client.post(
        "/api/v1/dispatch/",
        headers=store_headers,
        json={
            "dispatch_code": "DSP-HELD-001",
            "batch_id": bid,
            "status": "HELD",
            "serial_numbers": ["DSP-SN-001"]
        }
    )
    assert res.status_code == 400
    assert "cannot contain products" in res.json()["detail"]


def test_universal_traceability_query(client, admin_headers, store_headers, setup_dispatch_batch):
    setup = setup_dispatch_batch
    bid = setup["batch_id"]
    tid = setup["template_id"]
    param_id = setup["param_id"]
    item_id = setup["items"][0]["id"]

    # Test unit
    client.post(
        "/api/v1/testing/manual",
        headers=admin_headers,
        json={"batch_item_id": item_id, "template_id": tid, "results": [{"parameter_id": param_id, "measured_value": "12.2"}]}
    )

    # QA approve
    client.post(
        "/api/v1/quality/disposition",
        headers=admin_headers,
        json={"batch_item_id": item_id, "decision": "APPROVED", "remarks": "Pass verified"}
    )

    # Dispatch
    client.post(
        "/api/v1/dispatch/",
        headers=store_headers,
        json={"dispatch_code": "DSP-TRACE-001", "batch_id": bid, "status": "DISPATCHED", "serial_numbers": ["DSP-SN-001"]}
    )

    # Execute Universal Traceability lookup
    trace_res = client.get("/api/v1/traceability/DSP-SN-001", headers=admin_headers)
    assert trace_res.status_code == 200
    trace = trace_res.json()

    assert trace["serial_number"] == "DSP-SN-001"
    assert trace["product"]["model_number"] == "RTR-DISP"
    assert trace["inward_batch"]["batch_number"] == "BAT-DSP-001"
    assert len(trace["test_history"]) >= 1
    assert trace["test_history"][0]["measurements"][0]["measured_value"] == "12.2"
    assert trace["quality_review"]["decision"] == "APPROVED"
    assert trace["dispatch"]["dispatch_code"] == "DSP-TRACE-001"
    assert trace["dispatch"]["status"] == "DISPATCHED"


def test_dashboard_endpoints(client, admin_headers):
    # Overview
    ov_res = client.get("/api/v1/dashboard/overview", headers=admin_headers)
    assert ov_res.status_code == 200
    ov = ov_res.json()
    assert "overall_yield_percentage" in ov
    assert "total_batches" in ov

    # Testing Dashboard
    t_res = client.get("/api/v1/dashboard/testing", headers=admin_headers)
    assert t_res.status_code == 200
    t = t_res.json()
    assert "units_by_status" in t

    # Quality Dashboard
    q_res = client.get("/api/v1/dashboard/quality", headers=admin_headers)
    assert q_res.status_code == 200
    q = q_res.json()
    assert "total_defects" in q
    assert "defect_resolution_rate" in q

    # Operational Report
    op_res = client.get("/api/v1/dashboard/reports/operations", headers=admin_headers)
    assert op_res.status_code == 200
    op = op_res.json()
    assert "total_batches" in op

    # Attendance Report
    att_res = client.get("/api/v1/dashboard/reports/attendance", headers=admin_headers)
    assert att_res.status_code == 200
    att = att_res.json()
    assert "employee_rates" in att

