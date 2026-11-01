def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Password123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@test.com"
    assert data["user"]["role"] == "SUPER_ADMIN"


def test_login_invalid_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "WrongPassword!"}
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_get_me_endpoint(client, tech_headers):
    response = client.get("/api/v1/auth/me", headers=tech_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "tech@test.com"
    assert data["role"] == "TEST_TECHNICIAN"


def test_unauthenticated_me_rejected(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

