from tests.test_records import make


def test_vaccine_library_search_and_lookup(client, auth):
    body = client.get("/vaccines", headers=auth, params={"q": "measles"}).json()
    assert {v["id"] for v in body["vaccines"]} >= {"mr", "mmr"}
    assert all(v["sources"] and v["diseases"] for v in body["vaccines"])
    assert client.get("/vaccines/hep b", headers=auth).json()["id"] == "hepb"
    assert client.get("/vaccines/unknown-vaccine", headers=auth).status_code == 404
    only = client.get("/vaccines", headers=auth, params={"category": "Adolescent & adult"}).json()["vaccines"]
    assert only and all(v["category"] == "Adolescent & adult" for v in only)


def test_rule_based_explanation_matches_the_example(client, auth):
    out = client.post("/assistant/explain", headers=auth,
                      json={"text": "The MMR vaccine provides protection against measles, mumps, and rubella."}).json()
    assert out["method"] == "rules"
    assert out["text"] == "The MMR vaccine helps protect you against three infections: measles, mumps, and rubella."
    assert client.post("/assistant/explain", headers=auth, json={"text": "short"}).status_code == 422


def test_curated_explanation_for_library_vaccine(client, auth):
    out = client.post("/assistant/explain", headers=auth, json={"vaccine_id": "mmr"}).json()
    assert out["method"] == "curated" and "three infections" in out["text"] and out["source"]


def test_llm_failure_falls_back_to_rules(client, auth, monkeypatch):
    from config import settings
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "LLM_API_KEY", "bad-key")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "http://127.0.0.1:9")  # nothing listens here
    out = client.post("/assistant/explain", headers=auth, json={"text": "Rotavirus vaccine prevents gastroenteritis in infants."}).json()
    assert out["method"] == "rules" and "wasn't available" in out["notice"]


def test_dashboard_reflects_database_contents(client, auth):
    empty = client.get("/dashboard/summary", headers=auth).json()
    assert empty["cards"]["total_doses"] == 0 and empty["recent"] == []
    make(client, auth, vaccine_name="BCG", dose_number=1, vaccination_date="2025-03-05")
    client.post("/vaccinations/bulk", headers=auth, json={"records": [
        {"vaccine_name": "OPV", "dose_number": 1, "vaccination_date": "2025-04-12", "verification_status": "unverified", "source_type": "ocr"}]})
    s = client.get("/dashboard/summary", headers=auth).json()
    assert s["cards"]["total_doses"] == 2 and s["cards"]["confirmed_doses"] == 1
    assert s["cards"]["completed_items"] >= 1 and s["cards"]["needs_verification"] == 1
    assert s["attention"][0]["vaccine_name"].startswith("Oral polio")
    assert s["ledger"] and s["schedule"]["version"]


def test_timeline_separates_history_undated_and_estimates(client, auth):
    make(client, auth, vaccine_name="BCG", dose_number=1, vaccination_date="2025-03-05")
    make(client, auth, vaccine_name="Hepatitis B", dose_number=1, vaccination_date=None, verification_status="unverified")
    t = client.get("/vaccinations/timeline", headers=auth).json()
    assert [r["vaccine_name"] for r in t["history"]] == ["BCG"]
    assert [r["vaccine_name"] for r in t["undated"]] == ["Hepatitis B"]
    assert t["upcoming"] and all(u["estimated_date"] for u in t["upcoming"])


def test_validation_errors_are_friendly(client, auth):
    r = client.post("/vaccinations", headers=auth, json={"vaccine_name": "", "dose_number": 99})
    assert r.status_code == 422 and r.json()["detail"] and r.json()["errors"]
    assert "Traceback" not in r.text
