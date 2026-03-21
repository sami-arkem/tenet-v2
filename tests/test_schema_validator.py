from src.reasoning.schema import OUTPUT_SCHEMA_TEMPLATE
from src.reasoning.schema_validator import repair_to_template, validate_exact_shape


def test_repair_to_template_adds_missing_keys_and_removes_extras():
    broken = {
        "audit_meta": {"audit_id": "a1"},
        "unexpected_root": {"x": 1},
    }

    result = repair_to_template(broken, OUTPUT_SCHEMA_TEMPLATE)

    assert "audit_meta" in result.repaired_output
    assert "unexpected_root" not in result.repaired_output
    assert len(result.errors) > 0


def test_validate_exact_shape_accepts_template_shape():
    errors = validate_exact_shape(OUTPUT_SCHEMA_TEMPLATE, OUTPUT_SCHEMA_TEMPLATE)
    assert errors == []
