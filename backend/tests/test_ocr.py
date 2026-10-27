from pathlib import Path

import pytest

from services import extraction_service, ocr_service

SAMPLE = Path(__file__).parent / "samples" / "sample_card.png"
pytestmark = pytest.mark.skipif(not ocr_service.is_available(), reason="Tesseract OCR is not installed")


def test_ocr_reads_the_sample_card():
    result = ocr_service.read_document(SAMPLE, "png")
    assert result.engine == "tesseract" and result.lines
    rows = extraction_service.extract_candidates(result.lines, "DMY", "sample_card.png")
    found = {(r["vaccine_name"], r["dose_number"], r["vaccination_date"]) for r in rows}
    assert ("Hepatitis B", 1, "2020-03-14") in found
    assert ("Oral polio vaccine (OPV)", 2, "2020-06-06") in found
    assert ("Pentavalent (DPT-HepB-Hib)", 1, "2020-04-25") in found
    assert ("Measles-Rubella (MR)", 1, "2020-12-20") in found
    assert ("BCG", None, "2020-03-14") in found


def test_upload_then_extract_endpoint(client, auth):
    with open(SAMPLE, "rb") as fh:
        up = client.post("/documents/upload", headers=auth, files={"file": ("my card.png", fh, "image/png")})
    assert up.status_code == 201
    doc = up.json()
    out = client.post(f"/documents/{doc['id']}/extract", headers=auth)
    assert out.status_code == 200
    body = out.json()
    assert body["document"]["processing_status"] == "processed" and len(body["records"]) >= 5
    assert all(r["verification_status"] == "unverified" for r in body["records"])


def test_blank_image_gets_a_clear_error(client, auth, tmp_path):
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), "white").save(buf, "PNG")
    up = client.post("/documents/upload", headers=auth, files={"file": ("blank.png", buf.getvalue(), "image/png")}).json()
    resp = client.post(f"/documents/{up['id']}/extract", headers=auth)
    assert resp.status_code == 422 and "blank" in resp.json()["detail"]["message"]
