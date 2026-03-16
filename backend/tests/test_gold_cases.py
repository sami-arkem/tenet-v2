from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_kyc_mock_matches_gold_case():
    response = client.get("/kyc/mock")
    assert response.status_code == 200
    data = response.json()
    assert data["task"] == "kyc_screening"
    assert data["decision"] == "PASS"
    assert data["risk_band"] == "LOW"


def test_kyb_mock_matches_gold_case():
    response = client.get("/kyb/mock")
    assert response.status_code == 200
    data = response.json()
    assert data["task"] == "kyb_screening"
    assert data["risk_band"] in ["HIGH", "CRITICAL"]
