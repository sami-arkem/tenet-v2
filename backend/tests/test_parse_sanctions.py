from pathlib import Path
from backend.app.services.raw_case_loader import load_jsonl


def test_ofac_parsed_file_exists():
    path = Path("data/processed/sanctions/parsed/ofac_sdn.jsonl")
    assert path.exists()


def test_ofac_parsed_file_has_rows():
    data = load_jsonl("data/processed/sanctions/parsed/ofac_sdn.jsonl")
    assert len(data) > 1000


def test_ofac_parsed_rows_have_core_fields():
    data = load_jsonl("data/processed/sanctions/parsed/ofac_sdn.jsonl")
    first = data[0]
    assert "source" in first
    assert "record_type" in first
    assert "entity_id" in first
    assert "name" in first
