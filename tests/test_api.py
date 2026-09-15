import os

os.environ["PROMPTCRAFT_DB_PATH"] = "data/test-promptcraft.db"

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_demo_comparison_and_history():
    payload = {
        "prompt": "Return a JSON summary about prompt testing.",
        "providers": [{"provider": "demo", "model": "promptcraft-demo"}],
        "expected_keywords": ["prompt", "recommendation"],
    }
    with TestClient(app) as client:
        response = client.post("/api/compare", json=payload)
        history = client.get("/api/experiments")
    assert response.status_code == 200
    body = response.json()
    assert body["winner"] == "demo"
    assert body["results"][0]["scores"]["overall"] > 0
    assert history.status_code == 200
    assert len(history.json()["experiments"]) >= 1


def test_validation_rejects_empty_prompt():
    with TestClient(app) as client:
        response = client.post("/api/compare", json={"prompt": ""})
    assert response.status_code == 422

