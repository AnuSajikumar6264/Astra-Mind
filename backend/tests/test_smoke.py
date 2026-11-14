import os
import tempfile

# Keep test state isolated from a developer's local demo database.
os.environ.setdefault("ASTRA_DB_PATH", os.path.join(tempfile.gettempdir(), "astramind-pytest.db"))

from fastapi.testclient import TestClient
from app.main import app


def test_dashboard_has_five_domains():
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["domains"]) == 5
        assert payload["astronaut"]["id"] == "crew-01"


def test_simulation_adds_observations():
    with TestClient(app) as client:
        before = client.get("/api/v1/dashboard").json()["observation_count"]
        response = client.post("/api/v1/simulation/run", json={"scenario": "nominal", "samples": 1})
        assert response.status_code == 200
        assert response.json()["created_count"] > 0
        after = client.get("/api/v1/dashboard").json()["observation_count"]
        assert after > before


def test_forecast_returns_contract():
    with TestClient(app) as client:
        response = client.get("/api/v1/forecast/crew-01")
        assert response.status_code == 200
        assert "method" in response.json()
        assert isinstance(response.json()["points"], list)
