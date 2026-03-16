from backend.app.services.raw_case_loader import load_jsonl


def test_raw_case_files_cover_all_core_tasks():
    files = [
        "data/raw/kyc_cases.jsonl",
        "data/raw/kyb_cases.jsonl",
        "data/raw/risk_cases.jsonl",
        "data/raw/gap_cases.jsonl",
        "data/raw/document_cases.jsonl",
    ]
    tasks = set()
    for path in files:
        for item in load_jsonl(path):
            tasks.add(item["input"]["task"])

    assert "kyc_screening" in tasks
    assert "kyb_screening" in tasks
    assert "risk_classification" in tasks
    assert "gap_detection" in tasks
    assert "document_compliance_analysis" in tasks


def test_raw_case_entries_have_input_and_output():
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
