import importlib.util
import sys
from pathlib import Path


def _load_module():
    path = Path("scripts/proof_density_lane.py")
    spec = importlib.util.spec_from_file_location("proof_density_lane", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_classify_item_uses_audit_context_domains_and_jurisdictions(tmp_path: Path):
    module = _load_module()
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "audit_context.json").write_text(
        """
        {
          "audit_id": "case-001",
          "entity_name": "Proof Density Entity",
          "audit_type": "kyc_kyb_policy_and_control_review",
          "jurisdictions": ["CANADA"],
          "domains": ["kyc_kyb", "governance"]
        }
        """,
        encoding="utf-8",
    )

    item = module.classify_item(
        kind="gold_case",
        base_dir=case_dir,
        manifest_path=None,
        allowed_domains={"kyc", "kyb", "governance"},
        allowed_jurisdictions={"canada"},
    )

    assert item.item_id == "case-001"
    assert item.domains == ["kyc", "kyb", "governance"]
    assert item.jurisdictions == ["canada"]
    assert "kyc::canada" in item.classification_keys
    assert "kyb::canada" in item.classification_keys
    assert item.metadata_complete is True


def test_load_observed_gate_artifacts_parses_real_repo_shapes(tmp_path: Path, monkeypatch):
    module = _load_module()
    root = tmp_path
    (root / "logs" / "evals").mkdir(parents=True)
    (root / "logs" / "customer_pack_stability").mkdir(parents=True)
    (root / "logs").mkdir(exist_ok=True)

    (root / "logs" / "final_execution_summary.json").write_text(
        """
        {
          "all_steps_passed": true,
          "readiness": {"overall_readiness": true}
        }
        """,
        encoding="utf-8",
    )
    (root / "logs" / "evals" / "live_model_eval_summary.json").write_text(
        """
        [
          {"case_id": "a", "passed": true, "weighted_score": 1.0, "failures": []},
          {"case_id": "b", "passed": false, "weighted_score": 0.5, "failures": ["x"]}
        ]
        """,
        encoding="utf-8",
    )
    (root / "logs" / "customer_pack_stability" / "summary.json").write_text(
        """
        {
          "pack_count": 4,
          "successful_workflow_runs": 3,
          "failed_workflow_runs": 1
        }
        """,
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "ROOT", root)
    observed = module.load_observed_gate_artifacts()

    assert observed["all_steps_passed"] is True
    assert observed["eval_case_count"] == 2
    assert observed["eval_failed_count"] == 1
    assert observed["eval_min_weighted_score"] == 0.5
    assert observed["customer_pack_successful_runs"] == 3
    assert observed["overall_readiness"] is True


def test_load_observed_gate_artifacts_keeps_zero_successful_runs(tmp_path: Path, monkeypatch):
    module = _load_module()
    root = tmp_path
    (root / "logs" / "customer_pack_stability").mkdir(parents=True)
    (root / "logs").mkdir(exist_ok=True)

    (root / "logs" / "customer_pack_stability" / "summary.json").write_text(
        """
        {
          "pack_count": 2,
          "successful_workflow_runs": 0,
          "failed_workflow_runs": 2
        }
        """,
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "ROOT", root)
    observed = module.load_observed_gate_artifacts()

    assert observed["customer_pack_successful_runs"] == 0


def test_classify_item_marks_unrecognized_domain_as_metadata_debt(tmp_path: Path):
    module = _load_module()
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "audit_context.json").write_text(
        """
        {
          "audit_id": "case-002",
          "entity_name": "Proof Density Entity",
          "audit_type": "aml_readiness_review",
          "jurisdictions": ["US"],
          "domains": ["made_up_domain"]
        }
        """,
        encoding="utf-8",
    )

    item = module.classify_item(
        kind="gold_case",
        base_dir=case_dir,
        manifest_path=None,
        allowed_domains={"aml", "governance"},
        allowed_jurisdictions={"us"},
    )

    assert item.metadata_complete is False
    assert "unrecognized_domain" in item.metadata_issues


def test_compute_overall_gate_health_prefers_current_final_execution_run():
    module = _load_module()
    health = module.compute_overall_gate_health(
        gate_results=[
            {
                "name": "final_execution_discipline",
                "passed": True,
                "timed_out": False,
                "returncode": 0,
            }
        ],
        observed_artifacts={
            "all_steps_passed": False,
            "eval_failed_count": 0,
            "eval_min_weighted_score": 1.0,
        },
    )

    assert health["green"] is True
    assert health["failures"] == []


def test_discover_items_prefers_pack_root_and_skips_runtime_descendants(tmp_path: Path):
    module = _load_module()
    root = tmp_path / "data" / "customer_evidence_packs"
    pack_dir = root / "real_pack"
    pack_dir.mkdir(parents=True)
    (pack_dir / "audit_context.json").write_text(
        """
        {
          "audit_id": "pack-001",
          "entity_name": "Pack Entity",
          "audit_type": "aml_readiness_review",
          "jurisdictions": ["US"]
        }
        """,
        encoding="utf-8",
    )
    export_dir = pack_dir / "tenet_run" / "exports" / "pack-001"
    export_dir.mkdir(parents=True)
    (export_dir / "artifact.pdf").write_text("x", encoding="utf-8")
    template_dir = root / "_template"
    template_dir.mkdir()
    (template_dir / "audit_context.json").write_text("{}", encoding="utf-8")

    module.ROOT = tmp_path
    items = module.discover_items(
        kind="customer_pack",
        search_roots=["data/customer_evidence_packs"],
        manifest_names=["manifest.json"],
        allowed_domains={"aml", "governance"},
        allowed_jurisdictions={"us"},
    )

    assert len(items) == 1
    assert items[0].item_id == "pack-001"
    assert items[0].path.endswith("real_pack")
