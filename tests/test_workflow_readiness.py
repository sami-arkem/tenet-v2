from src.workflow.readiness import build_readiness_summary


def test_build_readiness_summary_shape():
    summary = build_readiness_summary()
    assert "gold_case_count" in summary
    assert "stable_live_outputs" in summary
    assert "clear_enterprise_workflow" in summary
    assert "overall_readiness" in summary
