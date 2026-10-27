import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Document, User, utcnow
from services import extraction_service, file_service, ocr_service, schedule_service
from services.file_service import UploadError
from services.ocr_service import OCRError

log = logging.getLogger("vaxtrack")
router = APIRouter(prefix="/documents", tags=["Documents and OCR"])


def doc_out(d: Document) -> dict:
    return {
        "id": d.id, "original_filename": d.original_filename, "file_type": d.file_type, "size_bytes": d.size_bytes,
        "processing_status": d.processing_status,
        "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
        "processed_at": d.processed_at.isoformat() if d.processed_at else None,
        "file_available": d.processing_status != "expired",
    }


def _owned(db: Session, user: User, document_id: int) -> Document:
    doc = db.query(Document).filter_by(id=document_id, user_id=user.id).first()
    if doc is None:  # same answer whether it doesn't exist or belongs to someone else
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return doc


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Read one byte past the limit so oversized files are rejected without loading them in full.
    from config import settings
    content = await file.read(settings.max_upload_bytes + 1)
    try:
        file_type = file_service.validate_upload(file.filename or "", content)
    except UploadError as exc:
        raise HTTPException(exc.status, exc.message)
    stored = file_service.store_file(user.id, file_type, content)
    doc = Document(user_id=user.id, original_filename=file_service.sanitize_filename(file.filename or ""),
                   stored_filename=stored, file_type=file_type, size_bytes=len(content))
    db.add(doc)
    db.commit()
    file_service.purge_expired(db)
    return doc_out(doc)


@router.post("/{document_id}/extract")
def extract(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = _owned(db, user, document_id)
    if doc.processing_status == "expired":
        raise HTTPException(status.HTTP_410_GONE, "This file was deleted under the retention policy. Upload it again.")
    schedule = schedule_service.get_schedule(db, user.schedule_key)
    date_order = schedule.date_order if schedule else "DMY"

    doc.processing_status = "processing"
    db.commit()
    try:
        result = ocr_service.read_document(file_service.file_path(doc), doc.file_type)
    except OCRError as exc:
        doc.processing_status = "failed"
        db.commit()
        code = 503 if exc.code == "tesseract_missing" else 422
        raise HTTPException(code, {"code": exc.code, "message": exc.message})
    except Exception as exc:  # never expose a stack trace, and never log the document's text
        log.error("OCR failed for document %s: %s", doc.id, type(exc).__name__)
        doc.processing_status = "failed"
        db.commit()
        raise HTTPException(500, {"code": "ocr_failed", "message": "We couldn't read this document. Try a clearer photo or scan."})

    candidates = extraction_service.extract_candidates(result.lines, date_order, doc.original_filename)
    has_text = any(len(l.text.strip()) > 2 for l in result.lines)
    doc.processing_status = "processed" if has_text else "no_text"
    doc.processed_at = utcnow()
    db.commit()

    warnings = []
    if not has_text:
        warnings.append("No readable text was found. Try a sharper, well-lit photo or a higher-resolution scan.")
    elif not candidates:
        warnings.append("Text was found, but no vaccinations could be identified. You can add them manually below.")
    if result.page_count > len({l.page for l in result.lines}) and result.page_count > 6:
        warnings.append("Only the first pages of this PDF were read.")
    return {
        "document": doc_out(doc),
        "records": candidates,
        "page_count": result.page_count,
        "engine": result.engine,
        "average_confidence": result.average_confidence,
        "date_order": date_order,
        "warnings": warnings,
    }


@router.get("")
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.query(Document).filter_by(user_id=user.id).order_by(Document.uploaded_at.desc()).all()
    return [doc_out(d) for d in docs]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = _owned(db, user, document_id)
    file_service.delete_file(doc)
    db.delete(doc)  # records created from it keep their data (document_id becomes NULL)
    db.commit()
