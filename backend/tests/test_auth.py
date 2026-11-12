from tests.conftest import register


def test_register_and_me(client):
    data = register(client)
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"
    assert "hashed_password" not in r.json()


def test_password_is_hashed(client):
    from app.database.session import SessionLocal
    from app.models.user import User
    register(client)
    with SessionLocal() as db:
        u = db.query(User).one()
        assert u.hashed_password.startswith("$argon2")


def test_duplicate_email_rejected(client):
    register(client)
    r = client.post("/api/auth/register", json={"email": "A@example.com", "full_name": "X", "password": "longenough1", "hospital_name": "H"})
    assert r.status_code == 409


def test_weak_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "b@example.com", "full_name": "X", "password": "short"})
    assert r.status_code == 422


def test_login_success_and_failure(client):
    register(client)
    ok = client.post("/api/auth/login", json={"email": "a@example.com", "password": "correct-horse-1"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
    assert bad.status_code == 401
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    assert unknown.status_code == 401
    assert bad.json()["detail"] == unknown.json()["detail"]  # no user enumeration


def test_protected_route_requires_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"
