from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_model_contract():
    response = client.get("/model-contract")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert len(data["tasks"]) == 5

def test_global_scope():
    response = client.get("/global-scope")
    assert response.status_code == 200
    data = response.json()
    assert data["vision"] == "end_to_end_global_compliance_intelligence"


def test_report_contract():
    response = client.get("/report-contract")
    assert response.status_code == 200
    data = response.json()
    assert data["report_pipeline"]["reasoning_layer"] == "tenet_structured_model"
