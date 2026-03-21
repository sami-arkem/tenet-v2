from src.reasoning.reason import load_runtime_config


def test_load_runtime_config_has_expected_keys():
    cfg = load_runtime_config()
    assert "enable_model_reasoning" in cfg
    assert "model_overlay_sections" in cfg
    assert "fallback_to_deterministic_on_model_error" in cfg
