def test_punch_in_and_out(client, tech_headers):
    # 1. Punch In
    res_in = client.post(
        "/api/v1/attendance/punch",
        headers=tech_headers,
        json={"punch_type": "IN"}
    )
    assert res_in.status_code == 200
    data_in = res_in.json()
    assert data_in["status"] == "PRESENT"
    assert data_in["punch_in"] is not None

    # 2. Duplicate punch in rejected
    res_dup = client.post(
        "/api/v1/attendance/punch",
        headers=tech_headers,
        json={"punch_type": "IN"}
    )
    assert res_dup.status_code == 400
    assert "Already punched in" in res_dup.json()["detail"]

    # 3. Punch Out
    res_out = client.post(
        "/api/v1/attendance/punch",
        headers=tech_headers,
        json={"punch_type": "OUT"}
    )
    assert res_out.status_code == 200
    data_out = res_out.json()
    assert data_out["punch_out"] is not None


def test_today_summary(client, tech_headers, admin_headers):
    # Punch in for technician
    client.post(
        "/api/v1/attendance/punch",
        headers=tech_headers,
        json={"punch_type": "IN"}
    )

    # Check summary
    res_summary = client.get("/api/v1/attendance/today-summary", headers=admin_headers)
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["total_employees"] == 3
    assert summary["present"] == 1
    assert summary["present_percentage"] > 0

