from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_all_phase_0_1_core_endpoints():
    endpoints = [
        "/health",
        "/model-contract",
        "/model-contract/tasks",
        "/report-contract",
        "/global-scope",
        "/kyc/mock",
        "/kyb/mock",
        "/risk-classification/mock",
        "/gap-detection/mock",
        "/document-compliance/mock",
        "/sanctions/status",
        "/screening/status",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200


def test_model_contract_has_five_tasks():
    response = client.get("/model-contract")
    data = response.json()
    assert len(data["tasks"]) == 5
