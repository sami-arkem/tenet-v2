from backend.app.services.raw_case_loader import load_jsonl


def test_load_kyc_cases():
    data = load_jsonl("data/raw/kyc_cases.jsonl")
    assert len(data) >= 2


def test_load_kyb_cases():
    data = load_jsonl("data/raw/kyb_cases.jsonl")
    assert len(data) >= 2


def test_load_risk_cases():
    data = load_jsonl("data/raw/risk_cases.jsonl")
    assert len(data) >= 1

def test_load_gap_cases():
    data = load_jsonl("data/raw/gap_cases.jsonl")
    assert len(data) >= 1


def test_load_document_cases():
    data = load_jsonl("data/raw/document_cases.jsonl")
    assert len(data) >= 1
