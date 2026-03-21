from src.llm.model_adapter import ModelAdapter, ModelRegistry, ModelRequest
from src.llm.openai_compatible import OpenAICompatibleClient


class FakeOpenAICompatibleClient(OpenAICompatibleClient):
    def __init__(self):
        super().__init__(base_url="https://example.com/v1", api_key="test-key", model="gpt-5")
        self.calls = []

    def is_configured(self) -> bool:
        return True

    def chat_json(self, messages, temperature=0.2, max_output_tokens=700):
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "model": self.model,
            }
        )
        return {"status": "ok", "kind": "structured_json"}


def test_model_adapter_generate_json_uses_registry_model():
    registry = ModelRegistry()
    client = FakeOpenAICompatibleClient()
    adapter = ModelAdapter(registry=registry, openai_client=client)

    response = adapter.generate_json(
        ModelRequest(
            task_type="reasoning",
            messages=[
                {"role": "system", "content": "You are Tenet."},
                {"role": "user", "content": "{\"hello\": \"world\"}"},
            ],
        )
    )

    assert response.model_name == registry.data["default_reasoning_model"]
    assert response.content["status"] == "ok"
    assert len(client.calls) == 1
