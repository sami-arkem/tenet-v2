from backend.app.services.gold_test_loader import load_gold_tests


def test_gold_catalog_has_required_tasks():
    data = load_gold_tests()
    tasks = {item["task"] for item in data}
    assert "kyc_screening" in tasks
    assert "kyb_screening" in tasks
    assert "risk_classification" in tasks
    assert "gap_detection" in tasks


def test_gold_catalog_ids_unique():
    data = load_gold_tests()
    ids = [item["id"] for item in data]
    assert len(ids) == len(set(ids))
