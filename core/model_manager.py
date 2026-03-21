from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Protocol


DEFAULT_MODEL_LOG_ROOT = Path("artifacts") / "model_calls"

CALL_TYPE_DOCUMENT_CLASSIFICATION = "document_classification"
CALL_TYPE_KEY_FACT_EXTRACTION = "key_fact_extraction"
CALL_TYPE_GAP_EXPLANATION = "gap_explanation"
CALL_TYPE_EXECUTIVE_NARRATIVE = "executive_narrative"

ALLOWED_CALL_TYPES = {
    CALL_TYPE_DOCUMENT_CLASSIFICATION,
    CALL_TYPE_KEY_FACT_EXTRACTION,
    CALL_TYPE_GAP_EXPLANATION,
    CALL_TYPE_EXECUTIVE_NARRATIVE,
}

DEFAULT_PRIMARY_MODEL = "claude-sonnet"
DEFAULT_FALLBACK_MODEL = "claude-haiku"

NON_AUTHORITATIVE_LABEL = (
    "MODEL-GENERATED NON-AUTHORITATIVE OUTPUT. "
    "Deterministic verdicts remain authoritative."
)


class ModelManagerError(RuntimeError):
    pass


class ModelProvider(Protocol):
    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        """
        Must return a JSON-serializable dict.
        """


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_model_call_id() -> str:
    return f"mc_{uuid.uuid4().hex[:16]}"


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


@dataclass(frozen=True)
class ModelCallRecord:
    call_id: str
    call_type: str
    model_version: str
    fallback_used: bool
    success: bool
    created_at: str
    duration_ms: int
    system_prompt: str
    user_prompt: str
    response: dict[str, Any] | None
    error: str | None
    non_authoritative: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "call_type": self.call_type,
            "model_version": self.model_version,
            "fallback_used": self.fallback_used,
            "success": self.success,
            "created_at": self.created_at,
            "duration_ms": self.duration_ms,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "response": self.response,
            "error": self.error,
            "non_authoritative": self.non_authoritative,
            "label": NON_AUTHORITATIVE_LABEL,
        }


class StubModelProvider:
    """
    Deterministic local/test provider.
    """

    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        lowered = user_prompt.lower()

        if "classify document" in lowered:
            if "sanctions" in lowered or "screening" in lowered:
                return {
                    "category": "screening_alert_log",
                    "confidence": "HIGH",
                    "reason": "matched sanctions/screening tokens",
                }
            if "policy" in lowered or "procedure" in lowered:
                return {
                    "category": "policy_document",
                    "confidence": "HIGH",
                    "reason": "matched policy/procedure tokens",
                }
            return {
                "category": "unclassified",
                "confidence": "UNCLASSIFIED",
                "reason": "no deterministic stub match",
            }

        if "extract key facts" in lowered:
            return {
                "facts": {
                    "preview": user_prompt[:300],
                    "length": len(user_prompt),
                }
            }

        if "explain compliance gap" in lowered:
            return {
                "narrative": (
                    "A compliance gap exists because required controls or evidence "
                    "do not fully satisfy the mapped requirement."
                )
            }

        if "write executive narrative" in lowered:
            return {
                "narrative": (
                    "The audit indicates a deterministically derived compliance posture "
                    "that requires operator review and remediation tracking."
                )
            }

        return {"result": "ok"}


class AnthropicJSONProvider:
    """
    Optional production provider. Only used when anthropic SDK is available and configured.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ModelManagerError("ANTHROPIC_API_KEY is required for AnthropicJSONProvider")

        try:
            from anthropic import Anthropic  # type: ignore
        except Exception as exc:
            raise ModelManagerError("anthropic package is not installed") from exc

        self._client = Anthropic(api_key=self.api_key)

    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        try:
            message = self._client.messages.create(
                model=model,
                max_tokens=max_output_tokens,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:
            raise ModelManagerError(f"anthropic call failed: {exc}") from exc

        text_parts: list[str] = []
        for block in getattr(message, "content", []):
            if getattr(block, "type", None) == "text":
                text_parts.append(getattr(block, "text", ""))

        raw = "".join(text_parts).strip()
        if not raw:
            raise ModelManagerError("anthropic returned empty response")

        try:
            payload = json.loads(raw)
        except Exception as exc:
            raise ModelManagerError(f"anthropic did not return valid json: {exc}") from exc

        if not isinstance(payload, dict):
            raise ModelManagerError("anthropic response must be a json object")
        return payload


class ModelManager:
    def __init__(
        self,
        *,
        primary_provider: ModelProvider | None = None,
        fallback_provider: ModelProvider | None = None,
        primary_model: str = DEFAULT_PRIMARY_MODEL,
        fallback_model: str = DEFAULT_FALLBACK_MODEL,
        log_root: Path = DEFAULT_MODEL_LOG_ROOT,
    ) -> None:
        self.primary_provider = primary_provider or StubModelProvider()
        self.fallback_provider = fallback_provider or StubModelProvider()
        self.primary_model = _require_non_empty_str(primary_model, "primary_model")
        self.fallback_model = _require_non_empty_str(fallback_model, "fallback_model")
        self.log_root = log_root

    def _validate_call_type(self, call_type: str) -> str:
        call_type = _require_non_empty_str(call_type, "call_type")
        if call_type not in ALLOWED_CALL_TYPES:
            raise ValueError(f"call_type must be one of {sorted(ALLOWED_CALL_TYPES)}")
        return call_type

    def _log_record(self, record: ModelCallRecord) -> None:
        path = self.log_root / f"{record.call_id}.json"
        _atomic_write_json(path, record.to_dict())

    def call_json(
        self,
        *,
        call_type: str,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int = 800,
        timeout_seconds: int = 30,
        use_fallback_on_error: bool = True,
    ) -> dict[str, Any]:
        call_type = self._validate_call_type(call_type)
        system_prompt = _require_non_empty_str(system_prompt, "system_prompt")
        user_prompt = _require_non_empty_str(user_prompt, "user_prompt")
        if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive int")
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive int")

        call_id = new_model_call_id()
        started = time.time()

        try:
            response = self.primary_provider.generate_json(
                model=self.primary_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_output_tokens=max_output_tokens,
                timeout_seconds=timeout_seconds,
            )
            if not isinstance(response, dict):
                raise ModelManagerError("primary provider returned non-object")

            record = ModelCallRecord(
                call_id=call_id,
                call_type=call_type,
                model_version=self.primary_model,
                fallback_used=False,
                success=True,
                created_at=utc_now_iso(),
                duration_ms=int((time.time() - started) * 1000),
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response=response,
                error=None,
            )
            self._log_record(record)
            return response

        except Exception as primary_exc:
            if not use_fallback_on_error:
                record = ModelCallRecord(
                    call_id=call_id,
                    call_type=call_type,
                    model_version=self.primary_model,
                    fallback_used=False,
                    success=False,
                    created_at=utc_now_iso(),
                    duration_ms=int((time.time() - started) * 1000),
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response=None,
                    error=str(primary_exc),
                )
                self._log_record(record)
                raise

            fallback_started = time.time()
            try:
                response = self.fallback_provider.generate_json(
                    model=self.fallback_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_output_tokens=max_output_tokens,
                    timeout_seconds=timeout_seconds,
                )
                if not isinstance(response, dict):
                    raise ModelManagerError("fallback provider returned non-object")

                record = ModelCallRecord(
                    call_id=call_id,
                    call_type=call_type,
                    model_version=self.fallback_model,
                    fallback_used=True,
                    success=True,
                    created_at=utc_now_iso(),
                    duration_ms=int((time.time() - fallback_started) * 1000),
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response=response,
                    error=f"primary_failed: {primary_exc}",
                )
                self._log_record(record)
                return response
            except Exception as fallback_exc:
                record = ModelCallRecord(
                    call_id=call_id,
                    call_type=call_type,
                    model_version=self.fallback_model,
                    fallback_used=True,
                    success=False,
                    created_at=utc_now_iso(),
                    duration_ms=int((time.time() - fallback_started) * 1000),
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response=None,
                    error=f"primary_failed: {primary_exc}; fallback_failed: {fallback_exc}",
                )
                self._log_record(record)
                raise ModelManagerError(str(record.error)) from fallback_exc
