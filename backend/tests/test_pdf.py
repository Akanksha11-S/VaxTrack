from tests.test_records import make


def test_pdf_downloads_with_latest_records(client, auth):
    make(client, auth, vaccine_name="BCG", dose_number=1, vaccination_date="2025-03-05")
    make(client, auth, vaccine_name="A very long vaccine name " * 4, dose_number=None, vaccination_date=None)
    resp = client.get("/reports/vaccination-pdf", headers=auth)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF") and len(resp.content) > 2000

    import fitz
    text = "".join(p.get_text() for p in fitz.open(stream=resp.content, filetype="pdf"))
    for needle in ("Vaccination report", "Asha Rao", "BCG", "Upcoming doses (estimated)", "Records that need review", "not medical advice"):
        assert needle in text, needle
    assert "India - Universal Immunisation Programme" in text


def test_pdf_handles_many_records_across_pages(client, auth):
    rows = [{"vaccine_name": f"Custom vaccine {i}", "dose_number": 1, "vaccination_date": "2025-04-01"} for i in range(80)]
    assert client.post("/vaccinations/bulk", headers=auth, json={"records": rows}).status_code == 201
    import fitz
    pdf = fitz.open(stream=client.get("/reports/vaccination-pdf", headers=auth).content, filetype="pdf")
    assert pdf.page_count >= 2


def test_pdf_with_non_latin_name_does_not_crash(client):
    from tests.conftest import register
    headers = register(client, email="m@example.com", name="श्रेया Patil")
    assert client.get("/reports/vaccination-pdf", headers=headers).status_code == 200
