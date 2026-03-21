from __future__ import annotations

import inspect
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.llm.openai_compatible import OpenAICompatibleClient


MODEL_REGISTRY_PATH = Path("data/config/model_registry_v1.json")


class ModelAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelRequest:
    task_type: str
    messages: List[Dict[str, str]]
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    reasoning_effort: Optional[str] = "low"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    model_name: str
    provider: str
    content: Dict[str, Any]
    raw_usage: Dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    def __init__(self, path: Path = MODEL_REGISTRY_PATH) -> None:
        self.path = path
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            raise ModelAdapterError(f"Model registry not found: {self.path}")
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if "models" not in data or not isinstance(data["models"], dict):
            raise ModelAdapterError("Invalid model registry: missing models map")
        return data

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    def resolve_default_model(self, task_type: str) -> str:
        if task_type == "intake":
            model_name = self._data.get("default_intake_model")
        else:
            model_name = self._data.get("default_reasoning_model")

        if not model_name:
            raise ModelAdapterError(f"No default model configured for task_type={task_type}")
        return model_name

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        models = self._data["models"]
        if model_name not in models:
            raise ModelAdapterError(f"Unknown model: {model_name}")
        config = models[model_name]
        required = {"provider", "max_input_tokens", "max_output_tokens", "supports_json_mode"}
        missing = required - set(config.keys())
        if missing:
            raise ModelAdapterError(f"Model config missing keys for {model_name}: {sorted(missing)}")
        return config


class ModelAdapter:
    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        openai_client: Optional[OpenAICompatibleClient] = None,
    ) -> None:
        self.registry = registry or ModelRegistry()
        self.openai_client = openai_client or OpenAICompatibleClient()

    def is_configured(self) -> bool:
        return self.openai_client.is_configured()

    def _resolve_model(self, request: ModelRequest) -> tuple[str, Dict[str, Any]]:
        model_name = request.model_name or self.registry.resolve_default_model(request.task_type)
        config = self.registry.get_model_config(model_name)
        return model_name, config

    def _validate_messages(self, messages: List[Dict[str, str]]) -> None:
        if not isinstance(messages, list) or not messages:
            raise ModelAdapterError("messages must be a non-empty list")
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ModelAdapterError(f"message at index {idx} must be a dict")
            if msg.get("role") not in {"system", "developer", "user", "assistant"}:
                raise ModelAdapterError(f"invalid message role at index {idx}: {msg.get('role')}")
            content = msg.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ModelAdapterError(f"message content must be non-empty string at index {idx}")

    def _estimate_chars(self, messages: List[Dict[str, str]]) -> int:
        return sum(len(m.get("content", "")) for m in messages)

    def _validate_request(self, request: ModelRequest, config: Dict[str, Any]) -> None:
        self._validate_messages(request.messages)

        if request.temperature is not None:
            if request.temperature < 0 or request.temperature > 1:
                raise ModelAdapterError("temperature must be between 0 and 1")

        if request.reasoning_effort is not None:
            if request.reasoning_effort not in {"none", "low", "medium", "high", "minimal"}:
                raise ModelAdapterError("reasoning_effort must be one of none, low, medium, high, minimal")

        max_output_tokens = request.max_output_tokens or int(config["max_output_tokens"])
        if max_output_tokens <= 0:
            raise ModelAdapterError("max_output_tokens must be positive")

        estimated_chars = self._estimate_chars(request.messages)
        estimated_tokens = max(1, estimated_chars // 4)
        if estimated_tokens > int(config["max_input_tokens"]):
            raise ModelAdapterError(
                f"estimated input too large: {estimated_tokens} tokens > {config['max_input_tokens']}"
            )

    def generate_json(self, request: ModelRequest) -> ModelResponse:
        model_name, config = self._resolve_model(request)
        self._validate_request(request, config)

        provider = config["provider"]
        max_output_tokens = request.max_output_tokens or int(config["max_output_tokens"])

        if provider != "openai_compatible":
            raise ModelAdapterError(f"Unsupported provider: {provider}")

        if not config.get("supports_json_mode", False):
            raise ModelAdapterError(f"Model does not support json mode: {model_name}")

        if not self.openai_client.is_configured():
            raise ModelAdapterError("OpenAI-compatible client is not configured")

        original_model = self.openai_client.model
        try:
            self.openai_client.model = model_name
            chat_json_signature = inspect.signature(self.openai_client.chat_json)
            kwargs = {
                "messages": request.messages,
                "temperature": request.temperature,
                "max_output_tokens": max_output_tokens,
            }
            if "reasoning_effort" in chat_json_signature.parameters:
                kwargs["reasoning_effort"] = request.reasoning_effort
            content = self.openai_client.chat_json(**kwargs)
        except Exception as exc:
            raise ModelAdapterError(f"Model call failed for {model_name}: {exc}") from exc
        finally:
            self.openai_client.model = original_model

        if not isinstance(content, dict):
            raise ModelAdapterError("Model response content must be a JSON object")

        return ModelResponse(
            model_name=model_name,
            provider=provider,
            content=content,
            raw_usage={},
        )

    @classmethod
    def from_env(cls) -> "ModelAdapter":
        registry_path = Path(os.getenv("TENET_MODEL_REGISTRY_PATH", str(MODEL_REGISTRY_PATH)))
        registry = ModelRegistry(registry_path)
        client = OpenAICompatibleClient(
            base_url=os.getenv("TENET_LLM_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("TENET_LLM_API_KEY", ""),
            model=os.getenv("TENET_LLM_MODEL", ""),
        )
        return cls(registry=registry, openai_client=client)
