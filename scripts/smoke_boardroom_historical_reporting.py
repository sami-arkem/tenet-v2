import json
from pathlib import Path

from src.reporting.build_report_pack import build_report_pack
from src.reporting.deterministic_report_builder import build_deterministic_report_markdown_bundle
from src.workflow.workflow_runner import run_customer_evidence_pack

pack_dir = "data/customer_evidence_packs/demo_enterprise_pack"
result = run_customer_evidence_pack(pack_dir)

audit_output = json.loads(Path(result["audit_output_path"]).read_text(encoding="utf-8"))
report_pack = build_report_pack(audit_output)
reports = build_deterministic_report_markdown_bundle(audit_output)

Path("logs").mkdir(exist_ok=True)
Path("logs/boardroom_historical_report_pack.json").write_text(json.dumps(report_pack, indent=2), encoding="utf-8")
Path("logs/boardroom_historical_board.md").write_text(reports["board_memo_markdown"], encoding="utf-8")
Path("logs/boardroom_historical_regulator.md").write_text(reports["regulator_memo_markdown"], encoding="utf-8")
Path("logs/boardroom_historical_client.md").write_text(reports["client_report_markdown"], encoding="utf-8")

print("wrote logs/boardroom_historical_report_pack.json")
print("wrote logs/boardroom_historical_board.md")
print("wrote logs/boardroom_historical_regulator.md")
print("wrote logs/boardroom_historical_client.md")
