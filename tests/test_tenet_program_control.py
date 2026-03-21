from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/tenet_program_control.py")
    spec = importlib.util.spec_from_file_location("tenet_program_control", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pct():
    module = load_module()
    assert module.pct(52, 100) == 52.0
    assert module.pct(0, 0) == 0.0


def test_compute_score_happy_path():
    module = load_module()
    metrics = {
        "proof_density": {
            "gold_actual": 100,
            "gold_target": 100,
            "packs_actual": 20,
            "packs_target": 20,
            "gate_green": True,
            "present": True,
        },
        "bible_alignment": {
            "present": True,
            "status": "green",
            "issue_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "taxonomy_issue_count": 0,
        },
        "final_execution": {"present": True, "all_steps_passed": True},
        "live_eval": {"present": True, "case_count": 100, "failed_count": 0, "min_weighted_score": 1.0},
        "customer_pack_summary": {"present": True, "successful_runs": 20},
        "taxonomy": {"dossiers_present": True, "dossier_count": 0, "adjudications_applied": 0, "unresolved_dossiers": 0},
        "real_002": {"readiness_present": True, "ready_items": 10, "blocked_items": 0, "blocker_type_counts": {}, "imported_shards": 2, "failed_shards": 0},
    }
    score = module.compute_score(metrics)
    assert score["total_score"] == 100.0


def test_build_blockers():
    module = load_module()
    metrics = {
        "proof_density": {"gold_actual": 52, "gold_target": 100, "packs_actual": 6, "packs_target": 20, "gate_green": True, "present": True},
        "bible_alignment": {"present": True, "status": "red", "issue_count": 7, "error_count": 3, "warning_count": 0, "taxonomy_issue_count": 2},
        "final_execution": {"present": True, "all_steps_passed": True},
        "live_eval": {"present": True, "case_count": 52, "failed_count": 0, "min_weighted_score": 1.0},
        "customer_pack_summary": {"present": True, "successful_runs": 6},
        "taxonomy": {"dossiers_present": True, "dossier_count": 7, "adjudications_applied": 0, "unresolved_dossiers": 7},
        "real_002": {"readiness_present": True, "ready_items": 0, "blocked_items": 11, "blocker_type_counts": {}, "imported_shards": 0, "failed_shards": 0},
    }
    blockers = module.build_blockers(metrics)
    codes = {blocker.code for blocker in blockers}
    assert "proof.gold_cases_below_target" in codes
    assert "proof.customer_packs_below_target" in codes
    assert "bible.alignment_errors_present" in codes
    assert "corpus.taxonomy_adjudications_unresolved" in codes
    assert "intake.real_002_blocked_items_present" in codes


def test_build_worklist():
    module = load_module()
    metrics = {
        "proof_density": {"gold_actual": 52, "gold_target": 100, "packs_actual": 6, "packs_target": 20, "gate_green": True, "present": True},
        "taxonomy": {"dossiers_present": True, "dossier_count": 7, "adjudications_applied": 0, "unresolved_dossiers": 7},
        "real_002": {"readiness_present": True, "ready_items": 0, "blocked_items": 11, "blocker_type_counts": {}, "imported_shards": 0, "failed_shards": 0},
    }
    worklist = module.build_worklist(metrics, [])
    assert worklist[0]["task"].lower().startswith("resolve remaining gold-case taxonomy adjudications")
    assert worklist[1]["task"].lower().startswith("convert blocked real_002 intake items")
