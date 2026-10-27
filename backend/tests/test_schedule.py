from datetime import date

from dateutil.relativedelta import relativedelta

from services import schedule_service as ss
from services.schedule_service import RecordView

import json
from pathlib import Path

RULES = {s["key"]: s["rules"] for s in json.loads((Path(__file__).parent.parent / "data" / "schedules.json").read_text())["schedules"]}
UIP = RULES["in-uip"]
TODAY = date(2026, 6, 1)


def status_of(items, vaccine, dose):
    return next(i for i in items if i["vaccine_id"] == vaccine and i["dose"] == dose)


def rec(i, vaccine, dose, when, verified=True, conf=None):
    return RecordView(i, vaccine, dose, when, verified, conf)


def test_newborn_with_no_records_has_upcoming_and_due_doses_but_nothing_missed():
    dob = TODAY - relativedelta(days=3)
    items = ss.evaluate(dob, UIP, [], TODAY)
    assert status_of(items, "bcg", 1)["status"] == "potentially_due"
    assert status_of(items, "penta", 1)["status"] == "upcoming"
    assert status_of(items, "penta", 1)["estimated_date"] == dob + relativedelta(weeks=6)
    assert not [i for i in items if i["status"] == "possibly_missed"]


def test_confirmed_record_is_recorded():
    dob = TODAY - relativedelta(months=3)
    items = ss.evaluate(dob, UIP, [rec(1, "bcg", 1, dob + relativedelta(days=2))], TODAY)
    assert status_of(items, "bcg", 1)["status"] == "recorded"


def test_unconfirmed_ocr_record_never_counts_as_recorded():
    dob = TODAY - relativedelta(months=3)
    items = ss.evaluate(dob, UIP, [rec(1, "bcg", 1, dob + relativedelta(days=2), verified=False, conf=45)], TODAY)
    it = status_of(items, "bcg", 1)
    assert it["status"] == "needs_verification" and "hard to read" in it["explanation"]


def test_missing_date_needs_verification():
    dob = TODAY - relativedelta(months=3)
    assert status_of(ss.evaluate(dob, UIP, [rec(1, "bcg", 1, None)], TODAY), "bcg", 1)["status"] == "needs_verification"


def test_no_record_after_the_window_is_possibly_missed_not_missed():
    dob = TODAY - relativedelta(years=3)
    it = status_of(ss.evaluate(dob, UIP, [], TODAY), "penta", 1)
    assert it["status"] == "possibly_missed" and "does not mean" in it["explanation"]


def test_estimate_follows_previous_dose_plus_minimum_interval():
    dob = date(2026, 1, 1)
    late_first = dob + relativedelta(weeks=12)  # dose 1 given late
    items = ss.evaluate(dob, UIP, [rec(1, "opv", 1, late_first)], date(2026, 3, 20))
    second = status_of(items, "opv", 2)
    assert second["estimated_date"] == late_first + relativedelta(weeks=4)
    assert second["status"] in ("upcoming", "potentially_due")  # a late first dose shifts the window instead of marking dose 2 missed


def test_interval_conflict_is_flagged():
    dob = date(2026, 1, 1)
    r1, r2 = rec(1, "opv", 1, date(2026, 2, 20)), rec(2, "opv", 2, date(2026, 2, 25))
    items = ss.evaluate(dob, UIP, [r1, r2], date(2026, 6, 1))
    it = status_of(items, "opv", 2)
    assert it["status"] == "needs_verification" and it["issue"] == "interval"


def test_conflicting_duplicate_dates_and_impossible_dates():
    dob = date(2026, 1, 1)
    conflict = ss.evaluate(dob, UIP, [rec(1, "bcg", 1, date(2026, 1, 3)), rec(2, "bcg", 1, date(2026, 1, 9))], TODAY)
    assert status_of(conflict, "bcg", 1)["issue"] == "conflict"
    before = ss.evaluate(dob, UIP, [rec(1, "bcg", 1, date(2025, 12, 1))], TODAY)
    assert status_of(before, "bcg", 1)["issue"] == "before_birth"
    future = ss.evaluate(dob, UIP, [rec(1, "bcg", 1, date(2026, 12, 1))], TODAY)
    assert status_of(future, "bcg", 1)["issue"] == "future"


def test_record_without_dose_number_gives_not_enough_information():
    dob = TODAY - relativedelta(months=6)
    items = ss.evaluate(dob, UIP, [rec(1, "penta", None, date(2026, 1, 20))], TODAY)
    assert status_of(items, "penta", 1)["status"] == "not_enough_information"


def test_regional_vaccines_are_never_called_missed():
    dob = TODAY - relativedelta(years=5)
    je = status_of(ss.evaluate(dob, UIP, [], TODAY), "je", 1)
    assert je["status"] == "not_enough_information"


def test_mmr_counts_towards_mr_rules():
    dob = TODAY - relativedelta(months=11)
    items = ss.evaluate(dob, UIP, [rec(1, "mmr", 1, dob + relativedelta(months=9, days=3))], TODAY)
    assert status_of(items, "mr", 1)["status"] == "recorded"


def test_different_schedules_give_different_rules():
    assert {r["vaccine"] for r in RULES["who-routine"]} != {r["vaccine"] for r in UIP}
    assert all("age" in r and "dose" in r for rs in RULES.values() for r in rs)


def test_schedule_status_endpoint(client, auth):
    body = client.get("/schedule/status", headers=auth).json()
    assert body["schedule"]["key"] == "in-uip" and body["schedule"]["version"]
    assert body["counts"]["total"] == sum(body["counts"][k] for k in ss.STATUS_ORDER)
    assert all(d["explanation"] for v in body["vaccines"] for d in v["doses"])
    assert [o["key"] for o in client.get("/schedule/options", headers=auth).json()] == ["in-uip", "who-routine"]
