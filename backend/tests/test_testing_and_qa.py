import io
import pytest


@pytest.fixture
def qa_headers(db_session):
    from app.models.employee import Employee, RoleEnum
    from app.core.security import get_password_hash, create_access_token

    qa = Employee(
        emp_code="EMP-QA-99",
        first_name="Inspector",
        last_name="Gadget",
        email="qa@test.com",
        password_hash=get_password_hash("Password123!"),
        role=RoleEnum.QA_INSPECTOR,
        is_active=True
    )
    db_session.add(qa)
    db_session.commit()
    token = create_access_token(subject=qa.id, role=qa.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_setup_batch(client, admin_headers):
    # 1. Client
    c_res = client.post("/api/v1/clients/", headers=admin_headers, json={"name": "NetGearX", "code": "NGX"})
    client_id = c_res.json()["id"]

    # 2. Product
    p_res = client.post(
        "/api/v1/products/",
        headers=admin_headers,
        json={"client_id": client_id, "category": "ROUTER", "model_number": "NGX-RTR", "model_name": "Pro Router"}
    )
    product_id = p_res.json()["id"]

    # 3. Test Template
    t_res = client.post(
        "/api/v1/test-templates/",
        headers=admin_headers,
        json={
            "product_model_id": product_id,
            "name": "RF and Power Baseline",
            "parameters": [
                {
                    "parameter_name": "Power Consumption",
                    "data_type": "NUMERIC_RANGE",
                    "min_limit": 5.0,
                    "max_limit": 15.0,
                    "unit_of_measure": "W",
                    "is_mandatory": True,
                    "display_order": 1
                },
                {
                    "parameter_name": "Power LED On",
                    "data_type": "BOOLEAN",
                    "is_mandatory": True,
                    "display_order": 2
                }
            ]
        }
    )
    template_data = t_res.json()
    template_id = template_data["id"]
    params = template_data["parameters"]

    # 4. Inward Batch with 3 units
    b_res = client.post(
        "/api/v1/batches/",
        headers=admin_headers,
        json={
            "client_id": client_id,
            "product_model_id": product_id,
            "batch_number": "BAT-NGX-01",
            "expected_qty": 3,
            "received_qty": 3
        }
    )
    batch_id = b_res.json()["id"]

    # Ingest 3 serials
    client.post(
        f"/api/v1/batches/{batch_id}/serials/bulk-import",
        headers=admin_headers,
        json={"serial_numbers": ["NGX-001", "NGX-002", "NGX-003"]}
    )

    items_res = client.get(f"/api/v1/batches/{batch_id}/items", headers=admin_headers)
    items = items_res.json()

    return {
        "template_id": template_id,
        "parameters": params,
        "items": items
    }


def test_manual_testing_pass_and_fail(client, tech_headers, test_setup_batch):
    setup = test_setup_batch
    template_id = setup["template_id"]
    param_power = setup["parameters"][0]["id"]
    param_led = setup["parameters"][1]["id"]
    item_pass = setup["items"][0]["id"]
    item_fail = setup["items"][1]["id"]

    # 1. Manual test PASS (Power = 10.0, LED = true)
    res_pass = client.post(
        "/api/v1/testing/manual",
        headers=tech_headers,
        json={
            "batch_item_id": item_pass,
            "template_id": template_id,
            "results": [
                {"parameter_id": param_power, "measured_value": "10.0"},
                {"parameter_id": param_led, "measured_value": "true"}
            ],
            "remarks": "Clean pass"
        }
    )
    assert res_pass.status_code == 201
    assert res_pass.json()["overall_result"] == "PASS"

    # 2. Manual test FAIL (Power = 20.0 > max 15.0)
    res_fail = client.post(
        "/api/v1/testing/manual",
        headers=tech_headers,
        json={
            "batch_item_id": item_fail,
            "template_id": template_id,
            "results": [
                {"parameter_id": param_power, "measured_value": "20.0"},
                {"parameter_id": param_led, "measured_value": "true"}
            ],
            "remarks": "Overpower fault"
        }
    )
    assert res_fail.status_code == 201
    assert res_fail.json()["overall_result"] == "FAIL"


def test_bench_csv_import(client, tech_headers, test_setup_batch):
    setup = test_setup_batch
    template_id = setup["template_id"]

    # Create CSV content for unit NGX-003
    csv_content = "serial_number,Power Consumption,Power LED On\nNGX-003,8.5,true\n"
    file_stream = io.BytesIO(csv_content.encode("utf-8"))

    res = client.post(
        f"/api/v1/testing/upload-bench-csv?template_id={template_id}",
        headers=tech_headers,
        files={"file": ("bench_test_run.csv", file_stream, "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["processed_units"] == 1
    assert data["passed_units"] == 1
    assert data["failed_units"] == 0


def test_defect_logging_and_qa_disposition_enforcement(client, tech_headers, qa_headers, test_setup_batch):
    setup = test_setup_batch
    template_id = setup["template_id"]
    param_power = setup["parameters"][0]["id"]
    param_led = setup["parameters"][1]["id"]
    item_pass = setup["items"][0]["id"]
    item_fail = setup["items"][1]["id"]

    # Test unit 1 to PASS, unit 2 to FAIL
    client.post(
        "/api/v1/testing/manual",
        headers=tech_headers,
        json={
            "batch_item_id": item_pass,
            "template_id": template_id,
            "results": [
                {"parameter_id": param_power, "measured_value": "9.0"},
                {"parameter_id": param_led, "measured_value": "true"}
            ]
        }
    )
    client.post(
        "/api/v1/testing/manual",
        headers=tech_headers,
        json={
            "batch_item_id": item_fail,
            "template_id": template_id,
            "results": [
                {"parameter_id": param_power, "measured_value": "2.0"},
                {"parameter_id": param_led, "measured_value": "false"}
            ]
        }
    )

    # 1. Log defect on failed unit
    def_res = client.post(
        "/api/v1/quality/defects",
        headers=tech_headers,
        json={
            "batch_item_id": item_fail,
            "defect_code": "DEF-PWR-LOW",
            "severity": "CRITICAL",
            "description": "Under-voltage below 5W threshold"
        }
    )
    assert def_res.status_code == 201
    assert def_res.json()["defect_code"] == "DEF-PWR-LOW"

    # 2. QA Inspector attempts to APPROVE the failed unit -> MUST BE REJECTED WITH 400!
    disp_reject = client.post(
        "/api/v1/quality/disposition",
        headers=qa_headers,
        json={"batch_item_id": item_fail, "decision": "APPROVED"}
    )
    assert disp_reject.status_code == 400
    assert "latest test result was FAIL" in disp_reject.json()["detail"]

    # 3. QA Inspector requests RETEST for the failed unit -> Accepted
    disp_rework = client.post(
        "/api/v1/quality/disposition",
        headers=qa_headers,
        json={"batch_item_id": item_fail, "decision": "RETEST_REQUESTED", "remarks": "Fix power rail capacitor"}
    )
    assert disp_rework.status_code == 201

    # 4. QA Inspector APPROVES the passed unit -> Accepted
    disp_approve = client.post(
        "/api/v1/quality/disposition",
        headers=qa_headers,
        json={"batch_item_id": item_pass, "decision": "APPROVED", "remarks": "Quality sign-off complete"}
    )
    assert disp_approve.status_code == 201
    assert disp_approve.json()["decision"] == "APPROVED"
