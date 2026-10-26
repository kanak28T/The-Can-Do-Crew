import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from api.main import app, ENGINE

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_engine():
    """Reset SQLite DB before each test to ensure isolation."""
    import os
    db_path = os.getenv("DATABASE_URL", "db/events.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    # Trigger FastAPI startup (loads baseline)
    with TestClient(app) as c:
        yield c
    if os.path.exists(db_path):
        os.remove(db_path)

def make_event(overrides: dict | None = None) -> dict:
    base = {
        "domain": "power",
        "event_type": "outage",
        "entity_id": "substation-1",
        "h3_cell": "89609610143ffff",
        "severity": 0.9,
        "source_type": "official",
        "source_reliability": 0.9,
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario_tag": None,
    }
    if overrides:
        base.update(overrides)
    return base

def test_ingest_valid_event():
    payload = make_event()
    response = client.post("/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "event_id" in data
    assert data["risk"] >= 0.0

def test_ingest_missing_field():
    payload = make_event()
    payload.pop("domain")
    response = client.post("/ingest", json=payload)
    assert response.status_code == 422
    resp = response.json()
    assert resp["status"] == "rejected"
    assert "Schema validation failed" in resp["reason"]

def test_ingest_pii_rejection():
    payload = make_event({"entity_id": "123-456-7890"})
    response = client.post("/ingest", json=payload)
    assert response.status_code == 422
    resp = response.json()
    assert resp["status"] == "rejected"
    assert "PII detected" in resp["reason"]

def test_zone_returned_for_high_risk():
    payload = make_event({"severity": 1.0})
    ingest_resp = client.post("/ingest", json=payload)
    assert ingest_resp.status_code == 200
    import os
    os.environ["PRIVACY_K"] = "1"
    zones_resp = client.get("/zones?risk_min=0.0")
    assert zones_resp.status_code == 200
    zones = zones_resp.json()["zones"]
    cell_ids = [z["cell_id"] for z in zones]
    assert payload["h3_cell"] in cell_ids
