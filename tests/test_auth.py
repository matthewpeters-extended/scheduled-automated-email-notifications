from conftest import login


def test_register_and_login(client):
    response = client.post(
        "/register", json={"name": "Nina", "email": "nina@test-suite.dev", "password": "nina12345"}
    )
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "nina@test-suite.dev"

    response = client.post("/login", json={"email": "nina@test-suite.dev", "password": "nina12345"})
    assert response.status_code == 200
    assert response.json()["email"] == "nina@test-suite.dev"


def test_register_rejects_duplicate_email(client, user):
    response = client.post(
        "/register", json={"name": "Someone Else", "email": "nina@test-suite.dev", "password": "whatever123"}
    )
    assert response.status_code == 400


def test_login_rejects_wrong_password(client, user):
    response = client.post("/login", json={"email": "nina@test-suite.dev", "password": "wrong-password"})
    assert response.status_code == 401


def test_me_requires_login(client):
    response = client.get("/me")
    assert response.status_code == 401


def test_me_returns_logged_in_user(client, user):
    login(client, "nina@test-suite.dev", "nina12345")

    response = client.get("/me")
    assert response.status_code == 200
    assert response.json()["email"] == "nina@test-suite.dev"


def test_logout_clears_session(client, user):
    login(client, "nina@test-suite.dev", "nina12345")
    assert client.get("/me").status_code == 200

    response = client.post("/logout")
    assert response.status_code == 204

    assert client.get("/me").status_code == 401
