"""Rule-based schedule matcher.

Compares a person's records with the rules in a reference schedule and gives every
rule one of six cautious statuses plus a plain-language explanation. The evaluation
function is pure (no database access) so it is easy to test.

Design principles
- A missing record never means "definitely missed" - the worst status is "Possibly missed".
- Records that came from OCR and have not been confirmed never count as Recorded.
- Missing dates, conflicting records and impossible intervals lead to "Needs verification".
"""
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from models import User, VaccinationRecord, VaccinationSchedule
from services import vaccine_service

SCHEDULE_FILE = Path(__file__).resolve().parent.parent / "data" / "schedules.json"

STATUS_LABELS = {
    "recorded": "Recorded",
    "upcoming": "Upcoming",
    "potentially_due": "Potentially due",
    "possibly_missed": "Possibly missed",
    "needs_verification": "Needs verification",
    "not_enough_information": "Not enough information",
}
STATUS_ORDER = list(STATUS_LABELS)
GRACE_DAYS = 4  # Common practice: doses given up to 4 days early are still counted.


@dataclass
class RecordView:
    id: int
    vaccine_id: str | None
    dose: int | None
    date: date | None
    verified: bool
    ocr_confidence: float | None = None


# ---------------------------------------------------------------- schedule data
def seed_schedules(db: Session) -> None:
    """Load data/schedules.json into the vaccination_schedules table (insert or update)."""
    with open(SCHEDULE_FILE, encoding="utf-8") as fh:
        payload = json.load(fh)
    for s in payload["schedules"]:
        row = db.query(VaccinationSchedule).filter_by(key=s["key"]).one_or_none()
        if row is None:
            row = VaccinationSchedule(key=s["key"])
            db.add(row)
        row.name, row.country, row.version = s["name"], s["country"], s["version"]
        row.source, row.source_url = s["source"], s.get("source_url")
        row.date_order = s.get("date_order", "DMY")
        row.description = s.get("description")
        row.rules = s["rules"]
    db.commit()


def add_span(start: date, value: int, unit: str) -> date:
    return start + relativedelta(**{unit: value})


def age_bounds(age: dict) -> tuple[tuple[int, str], tuple[int, str]]:
    """Return ((min, unit), (max, unit)); a rule may use one shared unit or separate min_unit/max_unit."""
    shared = age.get("unit")
    return (age["min"], age.get("min_unit", shared)), (age["max"], age.get("max_unit", shared))


def age_label(age: dict) -> str:
    (lo, lo_u), (hi, hi_u) = age_bounds(age)
    if (lo, lo_u) == (hi, hi_u):
        return _span_text(lo, lo_u)
    if lo_u == hi_u:
        return f"{lo} to {hi} {hi_u}"
    return f"{_span_text(lo, lo_u)} to {_span_text(hi, hi_u)}"


def _span_text(value: int, unit: str) -> str:
    return f"{value} {unit[:-1] if value == 1 else unit}"


def _fmt(d: date | None) -> str:
    return d.strftime("%d %b %Y").lstrip("0") if d else "an unknown date"


# ---------------------------------------------------------------- evaluation
def evaluate(dob: date, rules: list[dict], records: list[RecordView], today: date | None = None) -> list[dict]:
    today = today or date.today()
    rules_by_vaccine: dict[str, list[dict]] = defaultdict(list)
    for rule in rules:
        rules_by_vaccine[rule["vaccine"]].append(rule)

    items: list[dict] = []
    for vaccine_id, vrules in rules_by_vaccine.items():
        accepted = vaccine_service.satisfied_by(vaccine_id)
        recs = [r for r in records if r.vaccine_id in accepted]
        numbered: dict[int, list[RecordView]] = defaultdict(list)
        unnumbered = [r for r in recs if r.dose is None]
        for r in recs:
            if r.dose is not None:
                numbered[r.dose].append(r)
        unnumbered_left = len(unnumbered)
        dose_dates: dict[int, date] = {}

        for rule in sorted(vrules, key=lambda x: x["dose"]):
            age = rule["age"]
            (lo, lo_u), (hi, hi_u) = age_bounds(age)
            start = add_span(dob, lo, lo_u)
            end = add_span(dob, hi, hi_u)
            interval = rule.get("min_interval")
            interval_date = None
            if interval:
                prev_date = dose_dates.get(interval["after_dose"])
                if prev_date:
                    interval_date = add_span(prev_date, interval["value"], interval["unit"])

            item = {
                "vaccine_id": vaccine_id,
                "vaccine_name": vaccine_service.display_name(vaccine_id),
                "category": (vaccine_service.get_by_id(vaccine_id) or {}).get("category"),
                "dose": rule["dose"],
                "dose_label": rule.get("label") or f"Dose {rule['dose']}",
                "age_label": age_label(age),
                "notes": rule.get("notes"),
                "conditional": bool(rule.get("conditional")),
                "min_interval": interval,
                "record_ids": [],
                "record_date": None,
                "estimated_date": None,
                "window_start": None,
                "window_end": None,
                "issue": None,
            }

            matches = numbered.get(rule["dose"], [])
            if matches:
                status, why, issue, rec_date = _judge_matches(matches, dob, today, interval, dose_dates, rule)
                item["record_ids"] = [m.id for m in matches]
                item["record_date"] = rec_date
                item["issue"] = issue
                if rec_date:
                    dose_dates[rule["dose"]] = rec_date
            else:
                est = start
                depends_on_missing = False
                if interval:
                    if interval_date and interval_date > est:
                        est = interval_date
                    elif not interval_date:
                        depends_on_missing = True
                shift = est - start
                end = end + shift if shift.days > 0 else end
                item["estimated_date"] = est
                item["window_start"], item["window_end"] = start, end

                if unnumbered_left > 0 and today >= start:
                    unnumbered_left -= 1
                    status = "not_enough_information"
                    why = ("A record for this vaccine has no dose number, so we can't tell whether it covers this dose. "
                           "Add the dose number to the record to resolve this.")
                    item["issue"] = "unnumbered"
                elif rule.get("conditional"):
                    status = "not_enough_information"
                    why = (rule.get("notes") or "This dose only applies in some regions.") + \
                          " VaxTrack can't tell whether it applies to you, so it is not counted as missed."
                elif today < est:
                    status = "upcoming"
                    why = f"Estimated from the schedule: recommended from {_span_text(lo, lo_u)} of age."
                    if interval_date and interval_date > start:
                        why = (f"Estimated as {_span_text(interval['value'], interval['unit'])} after dose "
                               f"{interval['after_dose']} ({_fmt(dose_dates.get(interval['after_dose']))}).")
                    elif depends_on_missing:
                        why += f" It also depends on dose {interval['after_dose']}, which has no record yet."
                elif today <= end:
                    status = "potentially_due"
                    why = ("Your age falls inside the recommended window for this dose and no record was found. "
                           "It may already have been given - add the record if you have it.")
                    if depends_on_missing:
                        why += f" Dose {interval['after_dose']} also has no record yet."
                else:
                    status = "possibly_missed"
                    why = ("No record was found and the usual window has passed. This does not mean the dose was missed - "
                           "the record may simply not have been added. A healthcare provider can advise on catch-up.")
            item["window_start"] = item["window_start"] or start
            item["window_end"] = item["window_end"] or end
            item["status"] = status
            item["status_label"] = STATUS_LABELS[status]
            item["explanation"] = why
            items.append(item)
    return items


def _judge_matches(matches, dob, today, interval, dose_dates, rule):
    dated = [m for m in matches if m.date]
    if not dated:
        return ("needs_verification",
                "A record exists for this dose but it has no date, so it can't be counted yet.", "no_date", None)
    distinct = sorted({m.date for m in dated})
    if len(distinct) > 1:
        return ("needs_verification",
                f"Records for this dose show different dates ({', '.join(_fmt(d) for d in distinct)}). Keep the correct one.",
                "conflict", None)
    rec_date = distinct[0]
    if rec_date < dob:
        return ("needs_verification", f"The recorded date ({_fmt(rec_date)}) is before the date of birth.", "before_birth", rec_date)
    if rec_date > today:
        return ("needs_verification", f"The recorded date ({_fmt(rec_date)}) is in the future.", "future", rec_date)
    if interval:
        prev = dose_dates.get(interval["after_dose"])
        if prev:
            earliest = add_span(prev, interval["value"], interval["unit"]) - timedelta(days=GRACE_DAYS)
            if rec_date < prev:
                return ("needs_verification",
                        f"This dose is dated before dose {interval['after_dose']} ({_fmt(prev)}). Check both dates.",
                        "interval", rec_date)
            if rec_date < earliest:
                return ("needs_verification",
                        f"This dose is closer than the minimum {_span_text(interval['value'], interval['unit'])} "
                        f"after dose {interval['after_dose']} ({_fmt(prev)}). Check both dates.",
                        "interval", rec_date)
    if not any(m.verified for m in dated):
        low = any((m.ocr_confidence or 100) < 60 for m in dated)
        why = "This dose was read from an uploaded card but you haven't confirmed it yet."
        if low:
            why += " The text was hard to read, so check the details carefully."
        return ("needs_verification", why, "unverified", rec_date)
    return ("recorded", f"Recorded on {_fmt(rec_date)}.", None, rec_date)


def summarize(items: list[dict]) -> dict[str, int]:
    counts = {k: 0 for k in STATUS_ORDER}
    for it in items:
        counts[it["status"]] += 1
    counts["total"] = len(items)
    return counts


# ---------------------------------------------------------------- database helpers
def get_schedule(db: Session, key: str) -> VaccinationSchedule | None:
    return db.query(VaccinationSchedule).filter_by(key=key).one_or_none()


def record_views(user_records: list[VaccinationRecord]) -> list[RecordView]:
    views = []
    for r in user_records:
        v, _ = vaccine_service.canonicalize(r.vaccine_name)
        dose = r.dose_number
        if dose is None and v and v.get("single_dose"):
            dose = 1  # one-dose vaccines (e.g. BCG) don't need a dose number to be matched
        views.append(RecordView(
            id=r.id, vaccine_id=v["id"] if v else None, dose=dose, date=r.vaccination_date,
            verified=r.verification_status == "confirmed", ocr_confidence=r.ocr_confidence,
        ))
    return views


def evaluate_for_user(db: Session, user: User, today: date | None = None) -> list[dict]:
    schedule = get_schedule(db, user.schedule_key)
    if schedule is None:
        return []
    records = db.query(VaccinationRecord).filter_by(user_id=user.id).all()
    return evaluate(user.date_of_birth, schedule.rules, record_views(records), today)


def serialize_item(item: dict) -> dict:
    out = dict(item)
    for key in ("record_date", "estimated_date", "window_start", "window_end"):
        out[key] = item[key].isoformat() if item.get(key) else None
    return out


def age_parts(dob: date, today: date | None = None) -> dict:
    today = today or date.today()
    rd = relativedelta(today, dob)
    return {"years": rd.years, "months": rd.months, "days": rd.days}
