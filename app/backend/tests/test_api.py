import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Тест для проверки /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_endpoint():
    """Тест для проверки /predict endpoint с тестовыми данными."""
    test_data = [
        {
            "accountId": 1,
            "roomsCount": 3,
            "residentsCount": 2,
            "buildingType": "Частный",
            "consumption": {"1": 1000, "2": 1200, "3": 900}
        }
    ]
    
    response = client.post("/predict", json=test_data)
    assert response.status_code == 200
    
    results = response.json()
    assert len(results) == 1
    assert "accountId" in results[0]
    assert "isCommercial" in results[0]
    assert "probability" in results[0]
    assert results[0]["accountId"] == 1


def test_predict_empty_list():
    """Тест для проверки /predict endpoint с пустым списком."""
    response = client.post("/predict", json=[])
    assert response.status_code == 200
    assert response.json() == []


def test_root_endpoint():
    """Тест для проверки корневого endpoint."""
    response = client.get("/")
    assert response.status_code == 200 