import io

from PIL import Image


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (200, 120), "white").save(buf, "PNG")
    return buf.getvalue()


def test_unsupported_extension(client, auth):
    r = client.post("/documents/upload", headers=auth, files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_content_must_match_extension(client, auth):
    r = client.post("/documents/upload", headers=auth, files={"file": ("fake.png", b"%PDF-1.4 not an image", "image/png")})
    assert r.status_code == 415


def test_empty_and_oversized_files(client, auth, monkeypatch):
    assert client.post("/documents/upload", headers=auth, files={"file": ("a.png", b"", "image/png")}).status_code == 422
    from config import settings
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 0)
    assert client.post("/documents/upload", headers=auth, files={"file": ("a.png", png_bytes(), "image/png")}).status_code == 413


def test_damaged_image(client, auth):
    r = client.post("/documents/upload", headers=auth, files={"file": ("a.png", b"\x89PNG\r\n\x1a\n" + b"garbage", "image/png")})
    assert r.status_code == 422


def test_stored_name_is_server_generated(client, auth, db):
    from models import Document
    r = client.post("/documents/upload", headers=auth, files={"file": ("../../etc/passwd.png", png_bytes(), "image/png")})
    assert r.status_code == 201
    doc = db.query(Document).one()
    assert ".." not in doc.stored_filename and "/" not in doc.stored_filename and doc.stored_filename.endswith(".png")
    assert "/" not in doc.original_filename


def test_delete_document_removes_file_but_keeps_records(client, auth, db):
    from models import Document
    from services import file_service
    doc_id = client.post("/documents/upload", headers=auth, files={"file": ("c.png", png_bytes(), "image/png")}).json()["id"]
    saved = client.post("/vaccinations/bulk", headers=auth, json={"document_id": doc_id, "records": [
        {"vaccine_name": "BCG", "vaccination_date": "2025-03-05", "source_type": "ocr"}]})
    assert saved.status_code == 201
    path = file_service.file_path(db.query(Document).one())
    assert path.exists()
    assert client.delete(f"/documents/{doc_id}", headers=auth).status_code == 204
    assert not path.exists()
    records = client.get("/vaccinations", headers=auth).json()
    assert len(records) == 1 and records[0]["source_document"] == "c.png"


def test_retention_policy_deletes_old_files(client, auth, db, monkeypatch):
    from datetime import timedelta
    from config import settings
    from models import Document, utcnow
    from services import file_service
    monkeypatch.setattr(settings, "DOCUMENT_RETENTION_DAYS", 30)
    client.post("/documents/upload", headers=auth, files={"file": ("c.png", png_bytes(), "image/png")})
    doc = db.query(Document).one()
    doc.uploaded_at = utcnow() - timedelta(days=45)
    db.commit()
    path = file_service.file_path(doc)
    assert file_service.purge_expired(db) == 1
    assert not path.exists() and doc.processing_status == "expired"
