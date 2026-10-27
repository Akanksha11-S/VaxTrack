from tests.test_records import make


def test_same_dose_is_a_duplicate_until_allowed(client, auth):
    assert make(client, auth).status_code == 201
    again = make(client, auth, vaccination_date="2025-03-09")
    assert again.status_code == 409
    detail = again.json()["detail"]
    assert detail["code"] == "possible_duplicate" and detail["duplicates"][0]["matches"]
    forced = make(client, auth, vaccination_date="2025-03-09", allow_duplicate=True)
    assert forced.status_code == 201
    flags = [f["code"] for f in forced.json()["flags"]]
    assert "duplicate" in flags


def test_aliases_count_as_the_same_vaccine(client, auth):
    make(client, auth, vaccine_name="Hep B", dose_number=2, vaccination_date="2025-04-20")
    assert make(client, auth, vaccine_name="Hepatitis B", dose_number=2, vaccination_date="2025-04-21").status_code == 409


def test_different_doses_are_not_duplicates(client, auth):
    make(client, auth, vaccine_name="OPV", dose_number=1, vaccination_date="2025-04-12")
    assert make(client, auth, vaccine_name="OPV", dose_number=2, vaccination_date="2025-05-14").status_code == 201


def test_bulk_detects_duplicates_inside_the_batch(client, auth):
    row = {"vaccine_name": "OPV", "dose_number": 1, "vaccination_date": "2025-04-12"}
    resp = client.post("/vaccinations/bulk", headers=auth, json={"records": [row, dict(row)]})
    assert resp.status_code == 409 and resp.json()["detail"]["duplicates"][0]["index"] == 1
    ok = client.post("/vaccinations/bulk", headers=auth, json={"records": [row, dict(row)], "allow_duplicates": True})
    assert ok.status_code == 201
