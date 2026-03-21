import json
from pathlib import Path

from src.reasoning.reason import reason
from src.reporting.build_report_pack import build_report_pack
from src.reporting.report_transformer import ReportTransformer
from src.reporting.report_validator import assert_valid_report_outputs

audit_output = reason(
    audit_context={
        "audit_id": "report-live-001",
        "entity_name": "Report Live Entity",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "source_families": ["regulations", "aml"],
        "query_terms": ["aml policy", "transaction monitoring"],
        "top_k": 2
    },
    reasoner=None,
    runtime_config={
        "enable_model_reasoning": False,
        "model_overlay_sections": [],
        "fallback_to_deterministic_on_model_error": True,
        "require_retrieved_chunks_for_model_reasoning": True
    }
)

Path("logs").mkdir(exist_ok=True)
Path("logs/report_audit_output.json").write_text(json.dumps(audit_output, indent=2), encoding="utf-8")

report_pack = build_report_pack(audit_output)
Path("logs/report_pack.json").write_text(json.dumps(report_pack, indent=2), encoding="utf-8")

result = ReportTransformer().transform(audit_output, model_name="gpt-4.1-mini")

reports = {
    "board_memo_markdown": result.reports["board_memo_markdown"],
    "regulator_memo_markdown": result.reports["regulator_memo_markdown"],
    "client_report_markdown": result.reports["client_report_markdown"],
}

assert_valid_report_outputs(audit_output, reports)

Path("logs/board_memo.md").write_text(reports["board_memo_markdown"], encoding="utf-8")
Path("logs/regulator_memo.md").write_text(reports["regulator_memo_markdown"], encoding="utf-8")
Path("logs/client_report.md").write_text(reports["client_report_markdown"], encoding="utf-8")

print("wrote logs/report_audit_output.json")
print("wrote logs/report_pack.json")
print("wrote logs/board_memo.md")
print("wrote logs/regulator_memo.md")
print("wrote logs/client_report.md")
print("report validation passed")
