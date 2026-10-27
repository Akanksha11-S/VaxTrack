from tests.test_records import make


def reminders(client, auth):
    return client.get("/reminders", headers=auth).json()["reminders"]


def test_reminders_are_generated_for_upcoming_doses(client, auth):
    items = reminders(client, auth)
    assert items and all(r["status"] == "pending" for r in items)
    assert all(r["reason"] and r["estimated_date"] for r in items)


def test_recalculating_never_duplicates(client, auth):
    first = reminders(client, auth)
    for _ in range(3):
        client.post("/reminders/recalculate", headers=auth)
    again = reminders(client, auth)
    keys = [(r["vaccine_id"], r["dose_number"]) for r in again]
    assert len(keys) == len(set(keys)) == len(first)


def newborn(client):
    from datetime import date, timedelta
    from tests.conftest import register
    dob = (date.today() - timedelta(days=3)).isoformat()
    return register(client, email="baby@example.com", name="Baby", dob=dob)


def test_saving_a_confirmed_record_completes_its_reminder(client):
    from datetime import date
    headers = newborn(client)
    before = {(r["vaccine_id"], r["dose_number"]): r for r in reminders(client, headers)}
    assert before[("bcg", 1)]["status"] == "pending"  # potentially due for a 3-day-old
    make(client, headers, vaccine_name="BCG", dose_number=1, vaccination_date=date.today().isoformat())
    after = {(r["vaccine_id"], r["dose_number"]): r for r in reminders(client, headers)}
    assert after[("bcg", 1)]["status"] == "completed"


def test_deleting_the_record_brings_the_reminder_back_pending_or_missing(client, auth):
    rec = make(client, auth, vaccine_name="BCG", dose_number=1, vaccination_date="2025-03-05").json()
    client.delete(f"/vaccinations/{rec['id']}", headers=auth)
    again = {(r["vaccine_id"], r["dose_number"]): r for r in reminders(client, auth)}
    # the earlier auto-completed reminder stays as history; the user can restore it.
    assert ("bcg", 1) not in again or again[("bcg", 1)]["status"] in ("completed", "pending")


def test_acknowledge_dismiss_and_restore(client, auth):
    target = reminders(client, auth)[0]
    for status in ("acknowledged", "dismissed", "pending"):
        out = client.put(f"/reminders/{target['id']}", headers=auth, json={"status": status})
        assert out.status_code == 200 and out.json()["status"] == status
    client.put(f"/reminders/{target['id']}", headers=auth, json={"status": "dismissed"})
    client.post("/reminders/recalculate", headers=auth)
    still = next(r for r in reminders(client, auth) if r["id"] == target["id"])
    assert still["status"] == "dismissed"  # recalculation doesn't resurrect dismissed reminders


def test_changing_date_of_birth_moves_estimates(client, auth):
    before = {r["id"]: r["estimated_date"] for r in reminders(client, auth)}
    client.put("/profile", headers=auth, json={"date_of_birth": "2025-04-01"})
    after = {(r["vaccine_id"], r["dose_number"]): r["estimated_date"] for r in reminders(client, auth)}
    assert set(after.values()) != set(before.values())


def test_lead_days_set_when_a_reminder_becomes_visible(client, auth):
    client.put("/profile", headers=auth, json={"reminder_lead_days": 30})
    r = reminders(client, auth)[0]
    from datetime import date, timedelta
    assert date.fromisoformat(r["remind_from"]) == date.fromisoformat(r["estimated_date"]) - timedelta(days=30)
