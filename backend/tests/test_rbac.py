def test_technician_cannot_create_department(client, tech_headers):
    # Technicians should get 403 Forbidden
    response = client.post(
        "/api/v1/departments/",
        headers=tech_headers,
        json={"name": "Forbidden Dept", "code": "FORBID"}
    )
    assert response.status_code == 403
    assert "Operation not permitted" in response.json()["detail"]


def test_hr_can_create_department(client, hr_headers):
    response = client.post(
        "/api/v1/departments/",
        headers=hr_headers,
        json={"name": "Logistics Lab", "code": "DEP-LOG"}
    )
    assert response.status_code == 201
    assert response.json()["code"] == "DEP-LOG"


def test_technician_cannot_create_employee(client, tech_headers):
    response = client.post(
        "/api/v1/employees/",
        headers=tech_headers,
        json={
            "emp_code": "EMP-NEW-99",
            "first_name": "Bob",
            "last_name": "Builder",
            "email": "bob@test.com",
            "role": "TEST_TECHNICIAN",
            "password": "Password123!"
        }
    )
    assert response.status_code == 403


def test_admin_can_create_employee(client, admin_headers):
    response = client.post(
        "/api/v1/employees/",
        headers=admin_headers,
        json={
            "emp_code": "EMP-NEW-99",
            "first_name": "Bob",
            "last_name": "Builder",
            "email": "bob@test.com",
            "role": "TEST_TECHNICIAN",
            "password": "Password123!"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["emp_code"] == "EMP-NEW-99"
    assert data["email"] == "bob@test.com"

