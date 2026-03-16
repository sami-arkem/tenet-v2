from backend.app.services.raw_case_loader import load_jsonl


def test_all_raw_cases_have_input_and_output():
    files = [
        "data/raw/kyc_cases.jsonl",
        "data/raw/kyb_cases.jsonl",
        "data/raw/risk_cases.jsonl",
        "data/raw/gap_cases.jsonl",
        "data/raw/document_cases.jsonl",
    ]
    for path in files:
        for item in load_jsonl(path):
            assert "input" in item
            assert "output" in item


def test_all_outputs_have_task_and_confidence():
    files = [
        "data/raw/kyc_cases.jsonl",
        "data/raw/kyb_cases.jsonl",
        "data/raw/risk_cases.jsonl",
        "data/raw/gap_cases.jsonl",
        "data/raw/document_cases.jsonl",
    ]
    for path in files:
        for item in load_jsonl(path):
            assert "task" in item["output"]
            assert "confidence" in item["output"]

def test_all_outputs_match_input_task():
    files = [
        "data/raw/kyc_cases.jsonl",
        "data/raw/kyb_cases.jsonl",
        "data/raw/risk_cases.jsonl",
        "data/raw/gap_cases.jsonl",
        "data/raw/document_cases.jsonl",
    ]
    for path in files:
        for item in load_jsonl(path):
            assert item["output"]["task"] == item["input"]["task"]
