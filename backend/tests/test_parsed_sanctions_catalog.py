from backend.app.services.raw_case_loader import load_jsonl


def test_ofac_parsed_loads():
    data = load_jsonl("data/processed/sanctions/parsed/ofac_sdn.jsonl")
    assert len(data) > 1000


def test_uk_parsed_loads():
    data = load_jsonl("data/processed/sanctions/parsed/uk_sanctions.jsonl")
    assert len(data) > 1000


def test_parsed_sanctions_have_core_fields():
    files = [
        "data/processed/sanctions/parsed/ofac_sdn.jsonl",
        "data/processed/sanctions/parsed/uk_sanctions.jsonl",
    ]
    for path in files:
        first = load_jsonl(path)[0]
        assert "source" in first
        assert "record_type" in first
        assert "name" in first
