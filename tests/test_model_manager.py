from __future__ import annotations

import json

from core.model_manager import (
    CALL_TYPE_DOCUMENT_CLASSIFICATION,
    ModelManager,
    ModelManagerError,
    StubModelProvider,
)


class FailingProvider:
    def generate_json(self, **kwargs):
        raise RuntimeError("provider down")


def test_model_manager_primary_success(tmp_path):
    mm = ModelManager(
        primary_provider=StubModelProvider(),
        fallback_provider=StubModelProvider(),
        log_root=tmp_path,
    )
    out = mm.call_json(
        call_type=CALL_TYPE_DOCUMENT_CLASSIFICATION,
        system_prompt="Return JSON only",
        user_prompt="Classify document. policy and procedure text",
    )
    assert out["category"] == "policy_document"

    log_files = list(tmp_path.glob("mc_*.json"))
    assert len(log_files) == 1
    payload = json.loads(log_files[0].read_text())
    assert payload["success"] is True
    assert payload["fallback_used"] is False
    assert payload["non_authoritative"] is True


def test_model_manager_fallback_success(tmp_path):
    mm = ModelManager(
        primary_provider=FailingProvider(),
        fallback_provider=StubModelProvider(),
        log_root=tmp_path,
    )
    out = mm.call_json(
        call_type=CALL_TYPE_DOCUMENT_CLASSIFICATION,
        system_prompt="Return JSON only",
        user_prompt="Classify document. policy and procedure text",
    )
    assert out["category"] == "policy_document"

    payload = json.loads(next(tmp_path.glob("mc_*.json")).read_text())
    assert payload["success"] is True
    assert payload["fallback_used"] is True
    assert "primary_failed" in (payload["error"] or "")


def test_model_manager_double_failure(tmp_path):
    mm = ModelManager(
        primary_provider=FailingProvider(),
        fallback_provider=FailingProvider(),
        log_root=tmp_path,
    )
    try:
        mm.call_json(
            call_type=CALL_TYPE_DOCUMENT_CLASSIFICATION,
            system_prompt="Return JSON only",
            user_prompt="Classify document. text",
        )
    except ModelManagerError as exc:
        assert "primary_failed" in str(exc)
        assert "fallback_failed" in str(exc)
    else:
        raise AssertionError("expected ModelManagerError")

    payload = json.loads(next(tmp_path.glob("mc_*.json")).read_text())
    assert payload["success"] is False
    assert payload["fallback_used"] is True
