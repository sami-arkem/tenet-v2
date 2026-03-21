from src.llm.model_adapter import ModelRegistry


def test_model_registry_loads_defaults():
    registry = ModelRegistry()
    assert registry.resolve_default_model("reasoning") == "gpt-5"
    assert registry.resolve_default_model("intake") == "gpt-5-mini"
    cfg = registry.get_model_config("gpt-5")
    assert cfg["provider"] == "openai_compatible"
