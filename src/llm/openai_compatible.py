from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List


class OpenAICompatibleClient:
    def __init__(self, base_url: str = "", api_key: str = "", model: str = "", timeout_seconds: int = 90):
        self.base_url = (base_url or os.getenv("TENET_LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("TENET_LLM_API_KEY", "")
        self.model = model or os.getenv("TENET_LLM_MODEL", "")
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def _extract_message_text(self, parsed: Dict[str, Any]) -> str:
        try:
            message = parsed["choices"][0]["message"]
        except Exception as exc:
            raise RuntimeError(f"Unexpected response shape: {json.dumps(parsed)[:2000]}") from exc

        content = message.get("content")

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text" and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                    elif "text" in item and isinstance(item["text"], str):
                        parts.append(item["text"])
            text = "\n".join(p.strip() for p in parts if p and p.strip())
            if text:
                return text

        refusal = message.get("refusal")
        if refusal:
            raise RuntimeError(f"Model refusal: {refusal}")

        raise RuntimeError(f"Could not extract text content from response: {json.dumps(parsed)[:2000]}")

    def _post_chat_completions(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None,
        max_output_tokens: int,
        reasoning_effort: str | None,
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "max_completion_tokens": max_output_tokens,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {error_body}") from e

        return json.loads(body)

    def chat_json(self, messages: List[Dict[str, str]], temperature=None, max_output_tokens: int = 700, reasoning_effort: str | None = "low") -> Dict[str, Any]:
        attempts = [max_output_tokens, max(max_output_tokens * 2, max_output_tokens + 800)]
        last_error: RuntimeError | None = None

        for attempt_idx, token_budget in enumerate(attempts, start=1):
            parsed = self._post_chat_completions(
                messages=messages,
                temperature=temperature,
                max_output_tokens=token_budget,
                reasoning_effort=reasoning_effort,
            )
            choice = parsed["choices"][0]
            finish_reason = choice.get("finish_reason", "")
            reasoning_tokens = parsed.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens", 0)
            total_completion = parsed.get("usage", {}).get("completion_tokens", 0)

            content_text = self._extract_message_text(parsed)

            if finish_reason == "length" and not content_text.strip():
                last_error = RuntimeError(
                    f"Model exhausted token budget on reasoning with no output. "
                    f"reasoning_tokens={reasoning_tokens}, completion_tokens={total_completion}. "
                    f"Reduce prompt size or adjust model_reasoner budget/effort."
                )
                if attempt_idx < len(attempts):
                    continue
                raise last_error

            try:
                return json.loads(content_text)
            except json.JSONDecodeError as exc:
                last_error = RuntimeError(
                    f"Model returned non-JSON content: {content_text[:2000]} | raw_response={json.dumps(parsed)[:2000]}"
                )
                if finish_reason == "length" and attempt_idx < len(attempts):
                    continue
                raise last_error from exc

        if last_error is not None:
            raise last_error
        raise RuntimeError("Model call failed without a recoverable response")
