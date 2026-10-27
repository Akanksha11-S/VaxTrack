from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Document, User, VaccinationRecord
from schemas import BulkRecordsIn, RecordIn, RecordUpdate
from services import record_service, reminder_service, schedule_service

router = APIRouter(prefix="/vaccinations", tags=["Vaccination records"])


def _all(db: Session, user: User) -> list[VaccinationRecord]:
    return db.query(VaccinationRecord).filter_by(user_id=user.id).all()


def _owned(db: Session, user: User, record_id: int) -> VaccinationRecord:
    rec = db.query(VaccinationRecord).filter_by(id=record_id, user_id=user.id).first()
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.")
    return rec


def _check_date(user: User, vdate: date | None) -> None:
    if vdate and vdate < user.date_of_birth:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "A vaccination date can't be before the date of birth on your profile.")


def _duplicate_conflict(rows: list[dict]) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, {
        "code": "possible_duplicate",
        "message": "This looks like a record you already have.",
        "duplicates": rows,
    })


@router.get("")
def list_records(q: str = Query("", max_length=100), verification: str = Query("", pattern="^(|confirmed|unverified)$"),
                 year: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    records = _all(db, user)
    annotated = {r["id"]: r for r in record_service.annotate(db, user, records)}
    out = []
    for r in sorted(records, key=lambda r: (r.vaccination_date is None, r.vaccination_date or date.min), reverse=False):
        if q and q.lower() not in r.vaccine_name.lower():
            continue
        if verification and r.verification_status != verification:
            continue
        if year and (r.vaccination_date is None or r.vaccination_date.year != year):
            continue
        out.append(annotated[r.id])
    out.sort(key=lambda r: (r["vaccination_date"] is None, r["vaccination_date"] or ""), reverse=False)
    return out


@router.get("/timeline")
def timeline(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    records = record_service.annotate(db, user, _all(db, user))
    history = sorted((r for r in records if r["vaccination_date"]), key=lambda r: r["vaccination_date"], reverse=True)
    undated = [r for r in records if not r["vaccination_date"]]
    items = schedule_service.evaluate_for_user(db, user)
    upcoming = sorted((i for i in items if i["status"] in ("upcoming", "potentially_due") and i["estimated_date"]),
                      key=lambda i: i["estimated_date"])
    return {
        "history": history,
        "undated": undated,
        "upcoming": [schedule_service.serialize_item(i) for i in upcoming],
        "date_of_birth": user.date_of_birth.isoformat(),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_record(body: RecordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_date(user, body.vaccination_date)
    if body.next_due_date and body.vaccination_date and body.next_due_date <= body.vaccination_date:
        raise HTTPException(422, "The next due date must be after the vaccination date.")
    name, _ = record_service.canonical_name(body.vaccine_name)
    if not body.allow_duplicate:
        dupes = record_service.find_duplicates(_all(db, user), name, body.dose_number, body.vaccination_date)
        if dupes:
            raise _duplicate_conflict([{"index": 0, "matches": [record_service.brief(d) for d in dupes]}])
    rec = VaccinationRecord(
        user_id=user.id, vaccine_name=name, dose_number=body.dose_number, vaccination_date=body.vaccination_date,
        next_due_date=body.next_due_date, next_due_date_estimated=body.next_due_date_estimated,
        notes=body.notes, verification_status=body.verification_status, source_type="manual",
    )
    db.add(rec)
    db.commit()
    reminder_service.sync_reminders(db, user)
    return record_service.annotate(db, user, [rec] + [r for r in _all(db, user) if r.id != rec.id])[0]


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def create_bulk(body: BulkRecordsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Save the rows a user reviewed on the OCR page."""
    doc = None
    if body.document_id is not None:
        doc = db.query(Document).filter_by(id=body.document_id, user_id=user.id).first()
        if doc is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")

    existing = _all(db, user)
    pending: list[VaccinationRecord] = []
    conflicts = []
    for index, row in enumerate(body.records):
        _check_date(user, row.vaccination_date)
        if row.next_due_date and row.vaccination_date and row.next_due_date <= row.vaccination_date:
            raise HTTPException(422, f"The next due date must be after the vaccination date in row {index + 1}.")
        name, _ = record_service.canonical_name(row.vaccine_name)
        if not body.allow_duplicates:
            matches = record_service.find_duplicates(existing + pending, name, row.dose_number, row.vaccination_date)
            if matches:
                conflicts.append({"index": index, "matches": [record_service.brief(m) for m in matches]})
        pending.append(VaccinationRecord(
            user_id=user.id, vaccine_name=name, dose_number=row.dose_number, vaccination_date=row.vaccination_date,
            next_due_date=row.next_due_date, next_due_date_estimated=row.next_due_date_estimated,
            notes=row.notes, verification_status=row.verification_status,
            source_type="ocr" if doc else row.source_type, ocr_confidence=row.ocr_confidence,
            document_id=doc.id if doc else None, source_document=doc.original_filename if doc else None,
        ))
    if conflicts:
        raise _duplicate_conflict(conflicts)
    db.add_all(pending)
    db.commit()
    reminder_service.sync_reminders(db, user)
    saved_ids = {r.id for r in pending}
    annotated = record_service.annotate(db, user, _all(db, user))
    return {"saved": len(pending), "records": [r for r in annotated if r["id"] in saved_ids]}


@router.put("/{record_id}")
def update_record(record_id: int, body: RecordUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rec = _owned(db, user, record_id)
    data = body.model_dump(exclude_unset=True)
    allow_duplicate = data.pop("allow_duplicate", False)
    if data.get("vaccine_name") is None:
        data.pop("vaccine_name", None)
    if data.get("verification_status") is None:
        data.pop("verification_status", None)

    next_due = data.get("next_due_date", rec.next_due_date)
    vaccination_date = data.get("vaccination_date", rec.vaccination_date)
    if next_due and vaccination_date and next_due <= vaccination_date:
        raise HTTPException(422, "The next due date must be after the vaccination date.")
    name = record_service.canonical_name(data["vaccine_name"])[0] if "vaccine_name" in data else rec.vaccine_name
    dose = data["dose_number"] if "dose_number" in data else rec.dose_number
    vdate = data["vaccination_date"] if "vaccination_date" in data else rec.vaccination_date
    _check_date(user, vdate)
    if not allow_duplicate:
        dupes = record_service.find_duplicates(_all(db, user), name, dose, vdate, exclude_id=rec.id)
        if dupes:
            raise _duplicate_conflict([{"index": 0, "matches": [record_service.brief(d) for d in dupes]}])

    rec.vaccine_name, rec.dose_number, rec.vaccination_date = name, dose, vdate
    if "next_due_date" in data:
        rec.next_due_date = data["next_due_date"]
    if "next_due_date_estimated" in data and data["next_due_date_estimated"] is not None:
        rec.next_due_date_estimated = data["next_due_date_estimated"]
    if "notes" in data:
        rec.notes = (data["notes"] or "").strip() or None
    if "verification_status" in data:
        rec.verification_status = data["verification_status"]
    db.commit()
    reminder_service.sync_reminders(db, user)
    everything = _all(db, user)
    return next(r for r in record_service.annotate(db, user, everything) if r["id"] == rec.id)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rec = _owned(db, user, record_id)
    db.delete(rec)
    db.commit()
    reminder_service.sync_reminders(db, user)
