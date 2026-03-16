from backend.app.services.raw_case_loader import load_jsonl


def test_train_v1_loads():
    data = load_jsonl("data/processed/train_v1.jsonl")
    assert len(data) == 7


def test_train_v1_covers_all_core_tasks():
    data = load_jsonl("data/processed/train_v1.jsonl")
    tasks = {item["input"]["task"] for item in data}
    assert "kyc_screening" in tasks
    assert "kyb_screening" in tasks
    assert "risk_classification" in tasks
    assert "gap_detection" in tasks
    assert "document_compliance_analysis" in tasks

def test_train_v1_has_required_output_keys():
    data = load_jsonl("data/processed/train_v1.jsonl")
    for item in data:
        assert "task" in item["output"]
        assert "confidence" in item["output"]
