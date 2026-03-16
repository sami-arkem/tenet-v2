from pathlib import Path


def test_dataset_manifest_exists():
    path = Path("docs/DATASET_MANIFEST.md")
    assert path.exists()


def test_dataset_manifest_has_core_sections():
    text = Path("docs/DATASET_MANIFEST.md").read_text()
    assert "2000+ high-quality examples minimum" in text
    assert "kyc_screening" in text
    assert "kyb_screening" in text
    assert "risk_classification" in text
    assert "gap_detection" in text
    assert "document_compliance_analysis" in text
