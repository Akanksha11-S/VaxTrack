"""Upload validation, safe storage and retention."""
import io
import os
import re
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from config import settings
from models import Document, utcnow

ALLOWED_EXTENSIONS = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "pdf": "pdf"}


class UploadError(Exception):
    def __init__(self, message: str, status: int = 422, code: str = "invalid_file"):
        super().__init__(message)
        self.message, self.status, self.code = message, status, code


def sanitize_filename(name: str) -> str:
    base = os.path.basename((name or "").replace("\\", "/"))
    base = re.sub(r"[\x00-\x1f<>:\"|?*]", "", base).strip(" .")
    return (base or "document")[:120]


def detect_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"%PDF-"):
        return "pdf"
    return None


def validate_upload(filename: str, content: bytes) -> str:
    """Check extension, size and real content type. Returns the normalised type (jpg/png/pdf)."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadError("Unsupported file type. Upload a JPG, PNG or PDF.", 415, "unsupported_type")
    if len(content) == 0:
        raise UploadError("This file is empty.", 422, "empty_file")
    if len(content) > settings.max_upload_bytes:
        raise UploadError(f"This file is larger than {settings.MAX_UPLOAD_MB} MB. Upload a smaller file.", 413, "file_too_large")
    detected = detect_type(content)
    if detected is None or detected != ALLOWED_EXTENSIONS[ext]:
        raise UploadError("The file contents don't match its type, so it can't be used.", 415, "type_mismatch")
    if detected in {"jpg", "png"}:
        from PIL import Image
        try:
            with Image.open(io.BytesIO(content)) as img:
                img.verify()
        except Exception as exc:
            raise UploadError("This image is damaged or unreadable. Try another photo or scan.", 422, "unreadable_image") from exc
    return detected


def user_dir(user_id: int) -> Path:
    path = settings.UPLOAD_DIR / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def store_file(user_id: int, file_type: str, content: bytes) -> str:
    """Write the file under a server-generated name; the user's filename is never used on disk."""
    stored = f"{uuid.uuid4().hex}.{file_type}"
    (user_dir(user_id) / stored).write_bytes(content)
    return stored


def file_path(doc: Document) -> Path:
    return settings.UPLOAD_DIR / str(doc.user_id) / doc.stored_filename


def delete_file(doc: Document) -> None:
    try:
        file_path(doc).unlink(missing_ok=True)
    except OSError:
        pass


def purge_expired(db: Session) -> int:
    """Retention policy: delete stored files older than DOCUMENT_RETENTION_DAYS.

    The database row stays (status 'expired') so the upload history remains accurate.
    Records created from the document are not affected.
    """
    if settings.DOCUMENT_RETENTION_DAYS <= 0:
        return 0
    cutoff = utcnow() - timedelta(days=settings.DOCUMENT_RETENTION_DAYS)
    old = db.query(Document).filter(Document.uploaded_at < cutoff, Document.processing_status != "expired").all()
    for doc in old:
        delete_file(doc)
        doc.processing_status = "expired"
    if old:
        db.commit()
    return len(old)
