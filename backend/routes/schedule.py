from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User, VaccinationRecord, VaccinationSchedule
from services import record_service, schedule_service

router = APIRouter(tags=["Dashboard and schedule"])

DISCLAIMER = ("Vaccination schedules depend on country, age, medical circumstances and official recommendations. "
              "VaxTrack uses a simplified reference schedule to organise your records. It is educational and does not replace "
              "advice from a healthcare provider.")


def schedule_out(s: VaccinationSchedule) -> dict:
    return {"key": s.key, "name": s.name, "country": s.country, "version": s.version, "source": s.source,
            "source_url": s.source_url, "description": s.description, "date_order": s.date_order,
            "rule_count": len(s.rules)}


def group_by_vaccine(items: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for it in items:
        g = groups.setdefault(it["vaccine_id"], {"vaccine_id": it["vaccine_id"], "vaccine_name": it["vaccine_name"],
                                                 "category": it["category"], "doses": []})
        g["doses"].append(schedule_service.serialize_item(it))
    return list(groups.values())


@router.get("/schedule/options")
def schedule_options(db: Session = Depends(get_db)):
    """Public reference data (no personal information), so the registration form can offer the choices."""
    return [schedule_out(s) for s in db.query(VaccinationSchedule).order_by(VaccinationSchedule.id).all()]


@router.get("/schedule/status")
def schedule_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    schedule = schedule_service.get_schedule(db, user.schedule_key)
    if schedule is None:
        raise HTTPException(404, "The selected schedule is no longer available. Choose another in your profile.")
    items = schedule_service.evaluate_for_user(db, user)
    return {
        "schedule": schedule_out(schedule),
        "as_of": date.today().isoformat(),
        "age": schedule_service.age_parts(user.date_of_birth),
        "counts": schedule_service.summarize(items),
        "vaccines": group_by_vaccine(items),
        "disclaimer": DISCLAIMER,
    }


@router.get("/dashboard/summary")
def dashboard_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    schedule = schedule_service.get_schedule(db, user.schedule_key)
    records = db.query(VaccinationRecord).filter_by(user_id=user.id).all()
    annotated = record_service.annotate(db, user, records)
    items = schedule_service.evaluate_for_user(db, user)
    counts = schedule_service.summarize(items)

    upcoming = sorted((i for i in items if i["status"] in ("upcoming", "potentially_due") and i["estimated_date"]),
                      key=lambda i: i["estimated_date"])
    flagged = sorted((r for r in annotated if r["needs_attention"]),
                     key=lambda r: (not r["has_error"], r["vaccination_date"] is None, r["id"]))
    recent = sorted(annotated, key=lambda r: (r["created_at"] or "", r["id"]), reverse=True)[:5]

    per_year: dict[int, int] = {}
    for r in annotated:
        if r["vaccination_date"]:
            y = int(r["vaccination_date"][:4])
            per_year[y] = per_year.get(y, 0) + 1

    return {
        "cards": {
            "total_doses": len(annotated),
            "confirmed_doses": sum(1 for r in annotated if r["verification_status"] == "confirmed"),
            "completed_items": counts["recorded"],
            "schedule_items": counts["total"],
            "upcoming_doses": counts["upcoming"] + counts["potentially_due"],
            "needs_verification": len(flagged),
        },
        "counts": counts,
        "schedule": schedule_out(schedule) if schedule else None,
        "recent": recent,
        "upcoming": [schedule_service.serialize_item(i) for i in upcoming[:5]],
        "attention": flagged[:6],
        "attention_total": len(flagged),
        "ledger": group_by_vaccine(items),
        "per_year": [{"year": y, "count": c} for y, c in sorted(per_year.items())],
        "age": schedule_service.age_parts(user.date_of_birth),
    }
