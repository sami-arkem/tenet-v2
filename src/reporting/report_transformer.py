from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.llm.model_adapter import ModelAdapter, ModelAdapterError, ModelRequest
from src.reporting.build_report_pack import build_report_pack
from src.reporting.report_prompt_builder import build_report_messages
from src.reporting.report_validator import validate_report_outputs


class ReportTransformerError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReportTransformerResult:
    model_name: str
    provider: str
    reports: Dict[str, str]


class ReportTransformer:
    def __init__(self, model_adapter: Optional[ModelAdapter] = None) -> None:
        self.model_adapter = model_adapter or ModelAdapter.from_env()

    def is_configured(self) -> bool:
        return self.model_adapter.is_configured()

    def _generate_reports(self, messages: list[dict[str, str]], model_name: str) -> ReportTransformerResult:
        try:
            response = self.model_adapter.generate_json(
                ModelRequest(
                    task_type="reasoning",
                    messages=messages,
                    model_name=model_name,
                    temperature=None,
                    max_output_tokens=2200,
                    reasoning_effort=None,
                )
            )
        except ModelAdapterError as exc:
            raise ReportTransformerError(f"Report transform failed: {exc}") from exc

        content = response.content
        required = {
            "board_memo_markdown",
            "regulator_memo_markdown",
            "client_report_markdown",
        }
        missing = required - set(content.keys())
        if missing:
            raise ReportTransformerError(f"Missing report sections: {sorted(missing)}")

        return ReportTransformerResult(
            model_name=response.model_name,
            provider=response.provider,
            reports={
                "board_memo_markdown": str(content["board_memo_markdown"]),
                "regulator_memo_markdown": str(content["regulator_memo_markdown"]),
                "client_report_markdown": str(content["client_report_markdown"]),
            },
        )

    def transform(self, audit_output: Dict[str, Any], model_name: str = "gpt-4.1-mini") -> ReportTransformerResult:
        report_pack = build_report_pack(audit_output)
        first_result = self._generate_reports(build_report_messages(audit_output, report_pack), model_name)
        failures = validate_report_outputs(audit_output, first_result.reports)
        if not failures:
            return first_result

        repair_messages = build_report_messages(
            audit_output,
            report_pack,
            validation_failures=failures,
            prior_reports=first_result.reports,
        )
        repaired_result = self._generate_reports(repair_messages, model_name)
        repair_failures = validate_report_outputs(audit_output, repaired_result.reports)
        if repair_failures:
            raise ReportTransformerError(
                "Report validation failed after repair pass: " + " | ".join(repair_failures)
            )
        return repaired_result
