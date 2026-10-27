"""Helpers for vaccination records: name normalisation, duplicate detection and attention flags."""
from datetime import date

from sqlalchemy.orm import Session

from models import User, VaccinationRecord
from services import schedule_service, vaccine_service


def canonical_name(name: str) -> tuple[str, bool]:
    """Return (name to store, recognised). Recognised names are stored with the library's display name."""
    vaccine, _score = vaccine_service.canonicalize(name)
    if vaccine:
        return vaccine["name"], True
    return " ".join(name.split()), False


def _identity(name: str) -> str:
    vaccine, _ = vaccine_service.canonicalize(name)
    return vaccine["id"] if vaccine else vaccine_service.norm(name)


def is_duplicate(a_name: str, a_dose: int | None, a_date: date | None, b: VaccinationRecord) -> bool:
    if _identity(a_name) != _identity(b.vaccine_name):
        return False
    if a_dose is not None and b.dose_number is not None and a_dose == b.dose_number:
        return True
    same_date = a_date is not None and a_date == b.vaccination_date
    doses_compatible = a_dose is None or b.dose_number is None or a_dose == b.dose_number
    return same_date and doses_compatible


def find_duplicates(records: list[VaccinationRecord], name: str, dose: int | None, vdate: date | None,
                    exclude_id: int | None = None) -> list[VaccinationRecord]:
    return [r for r in records if (exclude_id is None or r.id != exclude_id) and is_duplicate(name, dose, vdate, r)]


def brief(r: VaccinationRecord) -> dict:
    return {
        "id": r.id, "vaccine_name": r.vaccine_name, "dose_number": r.dose_number,
        "vaccination_date": r.vaccination_date.isoformat() if r.vaccination_date else None,
    }


def annotate(db: Session, user: User, records: list[VaccinationRecord], today: date | None = None) -> list[dict]:
    """Serialise records with `flags` describing anything the user should double-check."""
    today = today or date.today()
    schedule_flags: dict[int, list[dict]] = {}
    messages = {
        "conflict": "Another record for the same dose shows a different date.",
        "before_birth": "The date is before your date of birth.",
        "future": "The date is in the future.",
        "interval": "The date doesn't fit with the neighbouring doses in the schedule.",
    }
    for item in schedule_service.evaluate_for_user(db, user, today):
        if item["issue"] in messages:
            for rid in item["record_ids"]:
                schedule_flags.setdefault(rid, []).append(
                    {"code": item["issue"], "severity": "error", "message": messages[item["issue"]]}
                )

    out = []
    for r in records:
        vaccine, _ = vaccine_service.canonicalize(r.vaccine_name)
        flags: list[dict] = []
        if r.verification_status == "unverified":
            flags.append({"code": "unverified", "severity": "warning",
                          "message": "Not confirmed yet. Check the details, then mark it as confirmed."})
        if r.vaccination_date is None:
            flags.append({"code": "missing_date", "severity": "warning", "message": "Date not recorded."})
        if vaccine is None:
            flags.append({"code": "unrecognized_vaccine", "severity": "warning",
                          "message": "This name isn't in the vaccine library, so it can't be matched to your schedule."})
        elif r.dose_number is None and not vaccine.get("single_dose"):
            flags.append({"code": "missing_dose", "severity": "warning", "message": "No dose number."})
        if r.source_type == "ocr" and r.verification_status == "unverified" and (r.ocr_confidence or 100) < 60:
            flags.append({"code": "low_confidence", "severity": "warning",
                          "message": "The scan was hard to read. Check every field."})
        if find_duplicates(records, r.vaccine_name, r.dose_number, r.vaccination_date, exclude_id=r.id):
            flags.append({"code": "duplicate", "severity": "warning", "message": "Possible duplicate of another record."})
        flags.extend(schedule_flags.get(r.id, []))
        out.append(serialize(r, flags))
    return out


def serialize(r: VaccinationRecord, flags: list[dict] | None = None) -> dict:
    flags = flags or []
    return {
        "id": r.id,
        "vaccine_name": r.vaccine_name,
        "dose_number": r.dose_number,
        "vaccination_date": r.vaccination_date.isoformat() if r.vaccination_date else None,
        "next_due_date": r.next_due_date.isoformat() if r.next_due_date else None,
        "next_due_date_estimated": r.next_due_date_estimated,
        "document_id": r.document_id,
        "source_document": r.source_document,
        "source_type": r.source_type,
        "ocr_confidence": r.ocr_confidence,
        "verification_status": r.verification_status,
        "notes": r.notes,
        "flags": flags,
        "needs_attention": bool(flags),
        "has_error": any(f["severity"] == "error" for f in flags),
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
