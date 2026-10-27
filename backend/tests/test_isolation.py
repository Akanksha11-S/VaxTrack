import io

from PIL import Image

from tests.conftest import register
from tests.test_records import make


def png():
    buf = io.BytesIO()
    Image.new("RGB", (200, 120), "white").save(buf, "PNG")
    return buf.getvalue()


def test_users_cannot_see_or_change_each_others_data(client):
    alice = register(client, email="alice@example.com", name="Alice")
    bob = register(client, email="bob@example.com", name="Bob")

    rec = make(client, alice).json()
    doc = client.post("/documents/upload", headers=alice, files={"file": ("a.png", png(), "image/png")}).json()
    reminder_id = client.get("/reminders", headers=alice).json()["reminders"][0]["id"]

    # Bob's lists are empty
    assert client.get("/vaccinations", headers=bob).json() == []
    assert client.get("/documents", headers=bob).json() == []

    # Bob gets 404 (not 403) for Alice's resources, so their existence isn't revealed
    assert client.put(f"/vaccinations/{rec['id']}", headers=bob, json={"notes": "x"}).status_code == 404
    assert client.delete(f"/vaccinations/{rec['id']}", headers=bob).status_code == 404
    assert client.post(f"/documents/{doc['id']}/extract", headers=bob).status_code == 404
    assert client.delete(f"/documents/{doc['id']}", headers=bob).status_code == 404
    assert client.put(f"/reminders/{reminder_id}", headers=bob, json={"status": "dismissed"}).status_code == 404
    assert client.post("/vaccinations/bulk", headers=bob, json={"document_id": doc["id"], "records": [{"vaccine_name": "BCG"}]}).status_code == 404

    # Alice's data is untouched, and Bob's dashboard and report ignore it
    assert client.get("/vaccinations", headers=alice).json()[0]["notes"] is None
    assert client.get("/dashboard/summary", headers=bob).json()["cards"]["total_doses"] == 0

    import fitz
    text = "".join(p.get_text() for p in fitz.open(stream=client.get("/reports/vaccination-pdf", headers=bob).content, filetype="pdf"))
    assert "Bob" in text and "Alice" not in text and "BCG" not in text.split("Recorded vaccinations")[1].split("Upcoming")[0]


def test_same_vaccine_can_exist_for_two_users(client):
    a = register(client, email="a@example.com")
    b = register(client, email="b@example.com")
    assert make(client, a).status_code == 201 and make(client, b).status_code == 201
