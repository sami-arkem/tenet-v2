from backend.app.services.training_seed_loader import load_training_seed


def test_training_seed_has_required_tasks():
    data = load_training_seed()
    tasks = {item["input"]["task"] for item in data}
    assert "kyc_screening" in tasks
    assert "kyb_screening" in tasks


def test_training_seed_entries_have_outputs():
    data = load_training_seed()
    for item in data:
        assert "task" in item["output"]
        assert "confidence" in item["output"]
