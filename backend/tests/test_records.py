from datetime import date, timedelta


def make(client, auth, **over):
    body = {"vaccine_name": "BCG", "dose_number": 1, "vaccination_date": "2025-03-05", "verification_status": "confirmed"}
    body.update(over)
    return client.post("/vaccinations", headers=auth, json=body)


def test_create_edit_delete_record(client, auth):
    created = make(client, auth, vaccine_name="bcg")
    assert created.status_code == 201
    rec = created.json()
    assert rec["vaccine_name"] == "BCG" and rec["verification_status"] == "confirmed"

    edited = client.put(f"/vaccinations/{rec['id']}", headers=auth, json={"vaccination_date": "2025-03-06", "notes": "Left arm"})
    assert edited.status_code == 200
    assert edited.json()["vaccination_date"] == "2025-03-06" and edited.json()["notes"] == "Left arm"

    assert client.delete(f"/vaccinations/{rec['id']}", headers=auth).status_code == 204
    assert client.get("/vaccinations", headers=auth).json() == []


def test_future_dates_are_rejected(client, auth):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    resp = make(client, auth, vaccination_date=tomorrow)
    assert resp.status_code == 422


def test_date_before_birth_is_rejected(client, auth):
    assert make(client, auth, vaccination_date="2024-01-01").status_code == 422


def test_unrecognised_vaccine_is_saved_but_flagged(client, auth):
    rec = make(client, auth, vaccine_name="Mystery shot", dose_number=None).json()
    assert rec["vaccine_name"] == "Mystery shot"
    assert "unrecognized_vaccine" in [f["code"] for f in rec["flags"]]


def test_clearing_a_date_with_null(client, auth):
    rec = make(client, auth).json()
    out = client.put(f"/vaccinations/{rec['id']}", headers=auth, json={"vaccination_date": None}).json()
    assert out["vaccination_date"] is None
    assert "missing_date" in [f["code"] for f in out["flags"]]


def test_bulk_save_from_ocr_review(client, auth):
    rows = [
        {"vaccine_name": "OPV", "dose_number": 1, "vaccination_date": "2025-04-12", "verification_status": "confirmed", "source_type": "ocr", "ocr_confidence": 91},
        {"vaccine_name": "Pentavalent", "dose_number": 1, "vaccination_date": None, "verification_status": "unverified", "source_type": "ocr", "ocr_confidence": 40},
    ]
    resp = client.post("/vaccinations/bulk", headers=auth, json={"records": rows})
    assert resp.status_code == 201 and resp.json()["saved"] == 2
    stored = {r["vaccine_name"]: r for r in client.get("/vaccinations", headers=auth).json()}
    assert stored["Pentavalent (DPT-HepB-Hib)"]["verification_status"] == "unverified"
    assert stored["Oral polio vaccine (OPV)"]["verification_status"] == "confirmed"
