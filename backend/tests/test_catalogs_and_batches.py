import pytest


def test_client_crud(client, admin_headers):
    # 1. Create client
    res = client.post(
        "/api/v1/clients/",
        headers=admin_headers,
        json={
            "name": "Telco Alpha Corp",
            "code": "TELCO-A",
            "contact_name": "Dave Miller",
            "email": "dave@telcoa.com",
            "phone": "+1-555-0199"
        }
    )
    assert res.status_code == 201
    client_id = res.json()["id"]
    assert res.json()["code"] == "TELCO-A"

    # 2. Duplicate client rejection
    res_dup = client.post(
        "/api/v1/clients/",
        headers=admin_headers,
        json={"name": "Telco Alpha Corp", "code": "TELCO-A-2"}
    )
    assert res_dup.status_code == 400

    # 3. List clients
    res_list = client.get("/api/v1/clients/", headers=admin_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_product_model_creation(client, admin_headers):
    # Setup client
    c_res = client.post(
        "/api/v1/clients/",
        headers=admin_headers,
        json={"name": "Broadband Beta", "code": "BB-BETA"}
    )
    client_id = c_res.json()["id"]

    # Create Product Model
    p_res = client.post(
        "/api/v1/products/",
        headers=admin_headers,
        json={
            "client_id": client_id,
            "category": "ROUTER",
            "model_number": "RT-AX58U",
            "model_name": "Dual-Band Wi-Fi 6 Router",
            "specifications": {
                "bands": ["2.4GHz", "5GHz"],
                "max_power_w": 12.0
            }
        }
    )
    assert p_res.status_code == 201
    prod_data = p_res.json()
    assert prod_data["model_number"] == "RT-AX58U"
    assert prod_data["client_name"] == "Broadband Beta"


def test_batch_creation_and_vendor_serial_import(client, admin_headers):
    # 1. Setup client & product
    c_res = client.post("/api/v1/clients/", headers=admin_headers, json={"name": "SatCorp", "code": "SAT"})
    client_id = c_res.json()["id"]
    p_res = client.post(
        "/api/v1/products/",
        headers=admin_headers,
        json={"client_id": client_id, "category": "SET_TOP_BOX", "model_number": "STB-4K", "model_name": "4K Receiver"}
    )
    product_id = p_res.json()["id"]

    # 2. Inward receive batch
    b_res = client.post(
        "/api/v1/batches/",
        headers=admin_headers,
        json={
            "client_id": client_id,
            "product_model_id": product_id,
            "batch_number": "BAT-SAT-001",
            "expected_qty": 3,
            "received_qty": 3,
            "storage_location": "Dock-A3"
        }
    )
    assert b_res.status_code == 201
    batch_id = b_res.json()["id"]
    assert b_res.json()["current_status"] == "RECEIVED"

    # 3. Import vendor serials
    v_serials = ["SAT-SN-101", "SAT-SN-102", "SAT-SN-103"]
    imp_res = client.post(
        f"/api/v1/batches/{batch_id}/serials/bulk-import",
        headers=admin_headers,
        json={"serial_numbers": v_serials}
    )
    assert imp_res.status_code == 200
    assert imp_res.json()["total_serials_registered"] == 3

    # 4. Verify batch items and QR hash
    items_res = client.get(f"/api/v1/batches/{batch_id}/items", headers=admin_headers)
    assert items_res.status_code == 200
    items = items_res.json()
    assert len(items) == 3
    assert items[0]["serial_number"] == "SAT-SN-101"
    assert items[0]["qr_code_hash"] is not None

    # 5. Duplicate serial rejection
    dup_res = client.post(
        f"/api/v1/batches/{batch_id}/serials/bulk-import",
        headers=admin_headers,
        json={"serial_numbers": ["SAT-SN-101"]}
    )
    assert dup_res.status_code == 400
    assert "already exist" in dup_res.json()["detail"]


def test_batch_auto_serial_generation(client, admin_headers):
    # Setup client & product
    c_res = client.post("/api/v1/clients/", headers=admin_headers, json={"name": "RemoteCorp", "code": "REMOTE-OEM"})
    client_id = c_res.json()["id"]
    p_res = client.post(
        "/api/v1/products/",
        headers=admin_headers,
        json={"client_id": client_id, "category": "REMOTE_CONTROL", "model_number": "RC-VOICE", "model_name": "Smart Voice Remote"}
    )
    product_id = p_res.json()["id"]

    # Inward receive batch
    b_res = client.post(
        "/api/v1/batches/",
        headers=admin_headers,
        json={
            "client_id": client_id,
            "product_model_id": product_id,
            "batch_number": "BAT-REM-001",
            "expected_qty": 5,
            "received_qty": 5
        }
    )
    batch_id = b_res.json()["id"]

    # Auto generate serials
    gen_res = client.post(
        f"/api/v1/batches/{batch_id}/serials/auto-generate",
        headers=admin_headers,
        json={"prefix": "TF-RCVOICE", "count": 5}
    )
    assert gen_res.status_code == 200
    assert gen_res.json()["total_serials_registered"] == 5

    # Check generated format
    items_res = client.get(f"/api/v1/batches/{batch_id}/items", headers=admin_headers)
    items = items_res.json()
    assert len(items) == 5
    assert items[0]["serial_number"] == "TF-RCVOICE-0001"
    assert items[4]["serial_number"] == "TF-RCVOICE-0005"
