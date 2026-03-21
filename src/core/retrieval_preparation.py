from __future__ import annotations

from typing import Any, Dict, List

from src.core.pack_composer import compose_pack_view


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_retrieval_preparation(audit_context: Dict[str, Any]) -> Dict[str, Any]:
    pack_view = compose_pack_view(audit_context)

    user_terms = [str(x) for x in audit_context.get("query_terms", []) if x]
    products = [str(x) for x in audit_context.get("products", []) if x]
    customer_types = [str(x) for x in audit_context.get("customer_types", []) if x]

    query_terms = _dedupe_keep_order(
        user_terms +
        products +
        customer_types +
        pack_view["query_seeds"]
    )

    return {
        "audit_type": audit_context.get("audit_type", ""),
        "jurisdictions": pack_view["jurisdictions"],
        "domains": pack_view["domains"],
        "regimes": pack_view["regimes"],
        "controls": pack_view["controls"],
        "evidence_categories": pack_view["evidence_categories"],
        "query_terms": query_terms,
    }
