from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_data_without_trigger():
    response = client.get("/api/data")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_data_with_trigger_bug():
    response = client.get("/api/data", headers={"X-Trigger-Bug": "true"})
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
