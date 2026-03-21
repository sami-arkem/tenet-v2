from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.dataset_ingestion_service import ingest_dataset
from core.dataset_registry_service import DEFAULT_DATASET_ROOT
from core.source_acquisition_service import DEFAULT_SOURCE_REGISTRY_ROOT, load_source_registry
from core.source_dataset_promotion_service import promote_source_to_dataset_manifest

DEFAULT_OFFICIAL_SOURCE_ROOT = DEFAULT_SOURCE_REGISTRY_ROOT / "official"


OFFICIAL_SOURCE_MANIFESTS: dict[str, dict[str, Any]] = {
    "ofac_sanctions_list_service.json": {
        "source_id": "official_ofac_sanctions_list_service",
        "title": "OFAC Sanctions List Service",
        "domain": "sanctions",
        "jurisdictions": ["us"],
        "countries": ["US"],
        "source_class": "PUBLIC_OFFICIAL",
        "acquisition_method": "PUBLIC_DOWNLOAD",
        "license_status": "PUBLIC",
        "owner": "tenet-platform",
        "source_url": "https://ofac.treasury.gov/ofac-sanctions-lists",
        "approved": True,
        "retrieval_allowed": True,
        "metadata": {
            "seeded_by": "official_corpus_bootstrap",
            "priority": "critical",
            "dataset_goal": "sanctions_screening",
        },
    },
    "fca_handbook.json": {
        "source_id": "official_fca_handbook",
        "title": "FCA Handbook of Rules and Guidance",
        "domain": "governance",
        "jurisdictions": ["uk"],
        "countries": ["GB"],
        "source_class": "PUBLIC_OFFICIAL",
        "acquisition_method": "PUBLIC_DOWNLOAD",
        "license_status": "PUBLIC",
        "owner": "tenet-platform",
        "source_url": "https://www.fca.org.uk/about/how-we-regulate/handbook",
        "approved": True,
        "retrieval_allowed": True,
        "metadata": {
            "seeded_by": "official_corpus_bootstrap",
            "priority": "high",
            "dataset_goal": "uk_regulatory_rules",
        },
    },
    "fatf_recommendations.json": {
        "source_id": "official_fatf_recommendations",
        "title": "FATF Recommendations and Standards Updates",
        "domain": "aml",
        "jurisdictions": ["global"],
        "countries": ["GLOBAL"],
        "source_class": "PUBLIC_OFFICIAL",
        "acquisition_method": "PUBLIC_DOWNLOAD",
        "license_status": "PUBLIC",
        "owner": "tenet-platform",
        "source_url": "https://www.fatf-gafi.org/en/publications/Fatfrecommendations.html",
        "approved": True,
        "retrieval_allowed": True,
        "metadata": {
            "seeded_by": "official_corpus_bootstrap",
            "priority": "critical",
            "dataset_goal": "global_aml_baseline",
        },
    },
    "eurlex_aml_package.json": {
        "source_id": "official_eurlex_aml_package",
        "title": "EUR-Lex EU AML Package and AMLA Texts",
        "domain": "aml",
        "jurisdictions": ["eu"],
        "countries": ["EU"],
        "source_class": "PUBLIC_OFFICIAL",
        "acquisition_method": "PUBLIC_DOWNLOAD",
        "license_status": "PUBLIC",
        "owner": "tenet-platform",
        "source_url": "https://eur-lex.europa.eu/EN/legal-content/summary/authority-for-anti-money-laundering-and-countering-the-financing-of-terrorism.html",
        "approved": True,
        "retrieval_allowed": True,
        "metadata": {
            "seeded_by": "official_corpus_bootstrap",
            "priority": "critical",
            "dataset_goal": "eu_aml_package",
        },
    },
    "eurlex_amld4.json": {
        "source_id": "official_eurlex_amld4",
        "title": "EUR-Lex AMLD4 / Directive (EU) 2015/849",
        "domain": "aml",
        "jurisdictions": ["eu"],
        "countries": ["EU"],
        "source_class": "PUBLIC_OFFICIAL",
        "acquisition_method": "PUBLIC_DOWNLOAD",
        "license_status": "PUBLIC",
        "owner": "tenet-platform",
        "source_url": "https://eur-lex.europa.eu/eli/dir/2015/849/oj/eng",
        "approved": True,
        "retrieval_allowed": True,
        "metadata": {
            "seeded_by": "official_corpus_bootstrap",
            "priority": "high",
            "dataset_goal": "eu_amld4",
        },
    },
}


FRAMEWORK_OVERRIDES: dict[str, list[str]] = {
    "official_ofac_sanctions_list_service": ["OFAC"],
    "official_fca_handbook": ["FCA_HANDBOOK"],
    "official_fatf_recommendations": ["FATF"],
    "official_eurlex_aml_package": ["EU_AMLA", "EU_AMLR", "EU_AMLD6"],
    "official_eurlex_amld4": ["EU_AMLD4"],
}


DOMAIN_OVERRIDES: dict[str, str] = {
    "official_ofac_sanctions_list_service": "sanctions",
    "official_fca_handbook": "governance",
    "official_fatf_recommendations": "aml",
    "official_eurlex_aml_package": "aml",
    "official_eurlex_amld4": "aml",
}


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


def seed_official_sources(root: Path = DEFAULT_OFFICIAL_SOURCE_ROOT) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    for filename, payload in OFFICIAL_SOURCE_MANIFESTS.items():
        path = root / filename
        _atomic_write_json(path, payload)
        created.append(str(path))

    return {
        "created_count": len(created),
        "created": created,
        "deterministic_authoritative": True,
    }


def bootstrap_official_corpus(
    *,
    source_root: Path = DEFAULT_SOURCE_REGISTRY_ROOT,
    dataset_root: Path = DEFAULT_DATASET_ROOT,
) -> dict[str, Any]:
    seed = seed_official_sources(DEFAULT_OFFICIAL_SOURCE_ROOT)

    promoted: list[dict[str, Any]] = []
    promotion_failures: list[dict[str, Any]] = []
    ingested: list[dict[str, Any]] = []
    ingestion_failures: list[dict[str, Any]] = []

    for source_id in sorted(OFFICIAL_SOURCE_MANIFESTS.values(), key=lambda row: row["source_id"]):
        sid = source_id["source_id"]
        try:
            promoted_row = promote_source_to_dataset_manifest(
                source_id=sid,
                source_root=source_root,
                dataset_root=dataset_root,
                override_domain=DOMAIN_OVERRIDES.get(sid),
                override_framework_ids=FRAMEWORK_OVERRIDES.get(sid),
            )
            promoted.append(promoted_row)
        except Exception as exc:
            promotion_failures.append({"source_id": sid, "error": str(exc)})

    for row in promoted:
        dataset_id = row["dataset_manifest"]["dataset_id"]
        try:
            ingested.append(ingest_dataset(dataset_id=dataset_id, root=dataset_root))
        except Exception as exc:
            ingestion_failures.append({"dataset_id": dataset_id, "error": str(exc)})

    registry = load_source_registry(source_root)
    official_source_ids = {payload["source_id"] for payload in OFFICIAL_SOURCE_MANIFESTS.values()}
    official_sources_seen = [
        item
        for item in registry["items"]
        if item.get("source_id") in official_source_ids
    ]

    return {
        "deterministic_authoritative": True,
        "seed": seed,
        "official_source_count": len(official_sources_seen),
        "promotion": {
            "promoted_count": len(promoted),
            "failure_count": len(promotion_failures),
            "promoted": promoted,
            "failures": promotion_failures,
        },
        "ingestion": {
            "processed_count": len(ingested),
            "failure_count": len(ingestion_failures),
            "processed": ingested,
            "failures": ingestion_failures,
        },
    }
