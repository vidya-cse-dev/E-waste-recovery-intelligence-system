"""End-to-end tests of the web API using synthetic images (no trained weights needed)."""
import io

import cv2
import numpy as np
import pytest

import config


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "ANNOTATED_DIR", tmp_path / "annotated")
    config.UPLOAD_DIR.mkdir()
    config.ANNOTATED_DIR.mkdir()
    import app as app_module
    import database
    database.init()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def jpeg(kind="clean"):
    rng = np.random.default_rng(3)
    img = np.full((360, 480, 3), (120, 130, 125), np.uint8)
    img = np.clip(img + rng.integers(-40, 40, img.shape), 0, 255).astype(np.uint8)   # sharp texture
    if kind == "burnt":
        cv2.rectangle(img, (80, 60), (400, 300), (20, 40, 80), -1)                   # dark brown scorch
        img = np.clip(img.astype(int) + rng.integers(-12, 12, img.shape), 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return io.BytesIO(buf.tobytes())


def post_image(client, name, kind="clean", component=""):
    return client.post("/api/analyze", data={"image": (jpeg(kind), name), "component": component},
                       content_type="multipart/form-data")


def test_clean_battery_asks_questions_then_decides(client):
    r = post_image(client, "battery_1.jpg")
    assert r.status_code == 200
    data = r.get_json()
    assert data["detected"] and data["component"] == "battery"
    assert data["questions"] and data["ask_reasons"] and "decision" not in data

    r2 = client.post("/api/decide", json={"id": data["id"], "answers": {
        "bat_swelling": "no", "bat_charge": "works", "bat_age": "lt1"}})
    dec = r2.get_json()
    assert dec["code"] == "reusable" and dec["value"]["low"] <= dec["value"]["high"]
    assert client.get("/api/stats").get_json()["total"] == 1


def test_battery_swelling_answer_leads_to_recycle(client):
    data = post_image(client, "battery_2.jpg").get_json()
    dec = client.post("/api/decide", json={"id": data["id"], "answers": {"bat_swelling": "yes"}}).get_json()
    assert dec["code"] == "recycle"


def test_burnt_part_is_flagged_and_decided_without_questions(client):
    data = post_image(client, "motor_burnt.jpg", kind="burnt").get_json()
    assert data["condition"]["findings"].get("burn", 0) > 0.5
    assert data["decision"]["code"] == "recycle"


def test_manual_component_choice(client):
    data = post_image(client, "photo.jpg", component="sensor").get_json()
    assert data["component"] == "sensor" and data["detector_mode"] == "manual"


def test_rejects_bad_uploads(client):
    assert client.post("/api/analyze", data={}, content_type="multipart/form-data").status_code == 400
    bad = client.post("/api/analyze", data={"image": (io.BytesIO(b"hello"), "notes.txt")},
                      content_type="multipart/form-data")
    assert bad.status_code == 400
    fake = client.post("/api/analyze", data={"image": (io.BytesIO(b"not an image"), "x.jpg")},
                       content_type="multipart/form-data")
    assert fake.status_code == 400
    assert client.post("/api/decide", json={"id": 999, "answers": {}}).status_code == 404


def test_dashboard_pages_and_export(client):
    data = post_image(client, "arduino_1.jpg").get_json()
    client.post("/api/decide", json={"id": data["id"], "answers": {}})
    assert client.get("/").status_code == 200
    assert client.get("/dashboard").status_code == 200
    csv_text = client.get("/export/records.csv").data.decode()
    assert csv_text.startswith("id,date,component") and "Arduino board" in csv_text
    assert client.get("/api/records").get_json()[0]["component_display"] == "Arduino board"
    assert client.get(data["annotated_url"]).status_code == 200
