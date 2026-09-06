"""API tests for the Engine Health Platform backend.

Run with: pytest -v (from backend/, with the venv's pytest on PATH).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from engine_health.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert "sensor_temp" in body["sensor_names"]


def test_list_engines_returns_demo_fleet():
    response = client.get("/engines")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] > 0
    assert len(body["engines"]) == body["count"]

    engine = body["engines"][0]
    for key in ("engine_id", "current_cycle", "latest_reading", "predicted_rul", "is_anomaly"):
        assert key in engine


def test_engine_history_for_known_engine():
    engines = client.get("/engines").json()["engines"]
    engine_id = engines[0]["engine_id"]

    response = client.get(f"/engines/{engine_id}/history")
    assert response.status_code == 200
    body = response.json()
    assert body["engine_id"] == engine_id
    assert len(body["points"]) > 0

    point = body["points"][0]
    expected_keys = (
        "cycle",
        "sensor_temp",
        "sensor_pressure",
        "sensor_vibration",
        "sensor_fuel_flow",
        "predicted_rul",
    )
    for key in expected_keys:
        assert key in point


def test_engine_history_unknown_engine_returns_404():
    response = client.get("/engines/does-not-exist/history")
    assert response.status_code == 404
    assert "does-not-exist" in response.json()["detail"]


def test_predict_healthy_reading_is_not_anomalous():
    payload = {
        "cycle": 10,
        "sensor_temp": 641.0,
        "sensor_pressure": 29.9,
        "sensor_vibration": 0.36,
        "sensor_fuel_flow": 8.1,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "predicted_rul" in body
    assert body["predicted_rul"] > 0
    assert body["is_anomaly"] is False


def test_predict_degraded_reading_is_flagged_anomalous():
    payload = {
        "cycle": 340,
        "sensor_temp": 720.0,
        "sensor_pressure": 22.0,
        "sensor_vibration": 1.5,
        "sensor_fuel_flow": 11.5,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["is_anomaly"] is True
    assert body["predicted_rul"] < 50


def test_predict_rejects_missing_fields():
    response = client.post("/predict", json={"cycle": 5})
    assert response.status_code == 422


def test_predict_rejects_negative_cycle():
    payload = {
        "cycle": -1,
        "sensor_temp": 640.0,
        "sensor_pressure": 30.0,
        "sensor_vibration": 0.35,
        "sensor_fuel_flow": 8.0,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("engine_index", [0, 1, 2])
def test_all_demo_engines_have_valid_predictions(engine_index):
    engines = client.get("/engines").json()["engines"]
    if engine_index >= len(engines):
        pytest.skip("fewer demo engines than requested index")
    engine = engines[engine_index]
    assert engine["predicted_rul"] >= 0
    assert isinstance(engine["is_anomaly"], bool)
