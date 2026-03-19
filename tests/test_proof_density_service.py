from __future__ import annotations

from pathlib import Path

from core.proof_density_service import (
    build_proof_density_summary,
    load_customer_pack_registry,
    load_gold_case_registry,
    seed_example_customer_pack,
    seed_example_gold_case,
)


def test_seed_and_load_gold_registry(tmp_path: Path):
    gold_root = tmp_path / "gold"
    seed_example_gold_case(gold_root)

    registry = load_gold_case_registry(gold_root)
    assert registry["count"] == 1
    assert len(registry["errors"]) == 0
    assert registry["items"][0]["case_id"] == "gold_case_example_001"
    assert registry["items"][0]["domain"] == "aml"


def test_seed_and_load_customer_pack_registry(tmp_path: Path):
    pack_root = tmp_path / "packs"
    seed_example_customer_pack(pack_root)

    registry = load_customer_pack_registry(pack_root)
    assert registry["count"] == 1
    assert len(registry["errors"]) == 0
    assert registry["items"][0]["pack_id"] == "customer_pack_example_001"
    assert registry["items"][0]["expected_executable"] is True


def test_build_proof_density_summary(tmp_path: Path):
    gold_root = tmp_path / "gold"
    pack_root = tmp_path / "packs"

    seed_example_gold_case(gold_root)
    seed_example_customer_pack(pack_root)

    summary = build_proof_density_summary(
        gold_root=gold_root,
        customer_pack_root=pack_root,
        target_gold_cases=100,
        target_customer_packs=20,
    )
    assert summary["deterministic_authoritative"] is True
    assert summary["current"]["gold_cases"] == 1
    assert summary["current"]["customer_packs"] == 1
    assert summary["remaining"]["gold_cases"] == 99
    assert summary["remaining"]["customer_packs"] == 19
    assert summary["validation"]["all_registries_valid"] is True
    assert summary["coverage"]["gold_cases_by_domain"]["aml"] == 1
    assert summary["coverage"]["customer_packs_by_domain"]["aml"] == 1
