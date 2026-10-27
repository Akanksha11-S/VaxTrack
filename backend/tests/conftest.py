import os
import sys
import tempfile
from pathlib import Path

# Point the app at a throwaway database and upload folder BEFORE it is imported.
_tmp = tempfile.mkdtemp(prefix="vaxtrack-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp, 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(Path(_tmp, "uploads"))
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production-use-0123456789"
os.environ["LLM_PROVIDER"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from database import Base, SessionLocal, engine
from main import app
from services import schedule_service

SAMPLE_CARD = Path(__file__).parent / "samples" / "sample_card.png"


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        schedule_service.seed_schedules(db)
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def register(client, email="asha@example.com", name="Asha Rao", dob="2025-03-01", password="Sunrise2026"):
    resp = client.post("/auth/register", json={"name": name, "email": email, "password": password, "date_of_birth": dob})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    return register(client)


@pytest.fixture()
def db():
    with SessionLocal() as session:
        yield session
