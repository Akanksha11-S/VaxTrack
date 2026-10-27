"""In-app reminders derived from the schedule status.

Reminders are *estimates*, not appointments. One reminder exists per (user, vaccine, dose),
enforced by a unique constraint, so recalculating never creates duplicates.
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from models import Reminder, User, VaccinationRecord
from services import schedule_service, vaccine_service

HORIZON_DAYS = 365  # only create reminders for doses estimated within the next year


def sync_reminders(db: Session, user: User, today: date | None = None) -> list[Reminder]:
    today = today or date.today()
    items = schedule_service.evaluate_for_user(db, user, today)
    by_key = {(i["vaccine_id"], i["dose"]): i for i in items}
    wanted: dict[tuple[str, int], dict] = {}
    # A date read from and confirmed on a user's card takes precedence over generic schedule estimates.
    for rec in db.query(VaccinationRecord).filter_by(user_id=user.id).all():
        if not rec.next_due_date or rec.verification_status != "confirmed":
            continue
        vaccine, _score = vaccine_service.canonicalize(rec.vaccine_name)
        if not vaccine:
            continue
        dose = rec.dose_number or 1
        wanted[(vaccine["id"], dose)] = {
            "vaccine_id": vaccine["id"], "vaccine_name": rec.vaccine_name, "dose": dose,
            "estimated_date": rec.next_due_date, "status": "card_due",
            "dose_label": f"Dose {dose}", "age_label": "date printed on your reviewed vaccination card",
            "date_source": "estimate" if rec.next_due_date_estimated else "card",
        }
    for key, item in by_key.items():
        est = item["estimated_date"]
        if key in wanted:  # a reviewed card date wins over the generic schedule
            continue
        if item["status"] == "potentially_due" and est:
            item["date_source"] = "schedule"
            wanted[key] = item
        elif item["status"] == "upcoming" and est and est <= today + timedelta(days=HORIZON_DAYS):
            item["date_source"] = "schedule"
            wanted[key] = item

    lead = timedelta(days=user.reminder_lead_days or 14)
    existing = {(r.vaccine_id, r.dose_number): r for r in db.query(Reminder).filter_by(user_id=user.id).all()}

    for key, item in wanted.items():
        reason = _reason(item)
        row = existing.get(key)
        if row is None:
            db.add(Reminder(
                user_id=user.id, vaccine_id=key[0], vaccine_name=item["vaccine_name"], dose_number=key[1],
                estimated_date=item["estimated_date"], remind_from=item["estimated_date"] - lead, reason=reason, date_source=item.get("date_source", "schedule"),
            ))
            continue
        row.vaccine_name, row.reason = item["vaccine_name"], reason
        row.date_source = item.get("date_source", "schedule")
        if row.estimated_date != item["estimated_date"]:
            row.estimated_date = item["estimated_date"]
            if row.status == "acknowledged":
                row.status = "pending"  # the date moved, so it deserves a fresh look
        row.remind_from = item["estimated_date"] - lead

    for key, row in existing.items():
        if key in wanted or row.status in ("completed", "dismissed"):
            continue
        item = by_key.get(key)
        if item and item["status"] == "recorded":
            row.status = "completed"  # a confirmed record now exists
        else:
            db.delete(row)  # the dose is no longer expected (record changed or schedule changed)
    db.commit()
    return list_reminders(db, user)


def _reason(item: dict) -> str:
    if item.get("date_source") == "card":
        return "Next due date read from your reviewed vaccination card. Confirm with your healthcare provider if unsure."
    if item.get("date_source") == "estimate":
        return "Tentative date estimated from the selected schedule because the card did not provide a next due date. Please confirm it with a healthcare provider."
    if item["status"] == "potentially_due":
        return (f"{item['dose_label']} may be due now, based on the {item['age_label']} age range in your schedule. "
                "Check whether it has already been given.")
    return f"{item['dose_label']} is expected around this date, based on the {item['age_label']} age range in your schedule."


def list_reminders(db: Session, user: User) -> list[Reminder]:
    return (db.query(Reminder).filter_by(user_id=user.id)
            .order_by(Reminder.estimated_date, Reminder.vaccine_name, Reminder.dose_number).all())


def serialize(r: Reminder, today: date | None = None) -> dict:
    today = today or date.today()
    days_until = (r.estimated_date - today).days
    return {
        "id": r.id,
        "vaccine_id": r.vaccine_id,
        "vaccine_name": r.vaccine_name,
        "dose_number": r.dose_number,
        "estimated_date": r.estimated_date.isoformat(),
        "remind_from": r.remind_from.isoformat(),
        "days_until": days_until,
        "reason": r.reason,
        "date_source": getattr(r, "date_source", "schedule"),
        "needs_confirmation": getattr(r, "date_source", "schedule") != "card",
        "status": r.status,
        "is_due_soon": r.status == "pending" and today >= r.remind_from,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
