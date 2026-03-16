from backend.app.services.training_seed_expanded_loader import load_training_seed_expanded


def test_training_seed_expanded_has_required_tasks():
    data = load_training_seed_expanded()
    tasks = {item["input"]["task"] for item in data}
    assert "risk_classification" in tasks
    assert "gap_detection" in tasks
    assert "document_compliance_analysis" in tasks


def test_training_seed_expanded_entries_have_outputs():
    data = load_training_seed_expanded()
    for item in data:
        assert "task" in item["output"]
        assert "confidence" in item["output"]
