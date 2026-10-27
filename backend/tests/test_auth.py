from tests.conftest import register


def test_register_login_and_me(client):
    headers = register(client)
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["email"] == "asha@example.com"
    ok = client.post("/auth/login", json={"email": "ASHA@example.com", "password": "Sunrise2026"})
    assert ok.status_code == 200 and ok.json()["access_token"]


def test_wrong_password_and_unknown_email_look_the_same(client):
    register(client)
    bad = client.post("/auth/login", json={"email": "asha@example.com", "password": "wrong-one1"})
    unknown = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong-one1"})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json()["detail"] == unknown.json()["detail"]


def test_duplicate_email_is_rejected(client):
    register(client)
    again = client.post("/auth/register", json={"name": "B", "email": "asha@example.com", "password": "Another123", "date_of_birth": "2000-01-01"})
    assert again.status_code == 409


def test_password_is_hashed(client, db):
    from models import User
    register(client)
    user = db.query(User).one()
    assert user.password_hash != "Sunrise2026" and user.password_hash.startswith("$2")


def test_weak_password_and_future_dob_are_rejected(client):
    weak = client.post("/auth/register", json={"name": "A", "email": "a@b.co", "password": "short", "date_of_birth": "2000-01-01"})
    future = client.post("/auth/register", json={"name": "A", "email": "a@b.co", "password": "Strong1234", "date_of_birth": "2999-01-01"})
    assert weak.status_code == 422 and future.status_code == 422


def test_protected_routes_need_a_token(client):
    for path in ("/auth/me", "/profile", "/vaccinations", "/dashboard/summary", "/reminders", "/reports/vaccination-pdf"):
        assert client.get(path).status_code == 401, path


def test_profile_update_changes_schedule(client, auth):
    resp = client.put("/profile", headers=auth, json={"schedule_key": "who-routine", "reminder_lead_days": 7})
    assert resp.status_code == 200 and resp.json()["schedule_key"] == "who-routine"
    bad = client.put("/profile", headers=auth, json={"schedule_key": "nope"})
    assert bad.status_code == 422
