from pathlib import Path
import sys

from fastapi.testclient import TestClient

BACKEND_PATH = Path(__file__).resolve().parents[1] / "src" / "web" / "backend"
sys.path.insert(0, str(BACKEND_PATH))

from main import app  # noqa: E402


client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "app_name" in payload
    assert "app_version" in payload


def test_environment_validation_rejects_out_of_bounds_input() -> None:
    response = client.post(
        "/api/environment",
        json={"indoor_temp": 99.0, "outdoor_temp": 20.0},
    )
    assert response.status_code == 422


def test_override_round_trip() -> None:
    response = client.post("/api/override", json={"active": True})
    assert response.status_code == 200
    assert response.json()["override_active"] is True

    response = client.get("/api/override")
    assert response.status_code == 200
    assert response.json()["override_active"] is True

    reset_response = client.post("/api/override", json={"active": False})
    assert reset_response.status_code == 200
    assert reset_response.json()["override_active"] is False
