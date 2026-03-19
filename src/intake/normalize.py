from __future__ import annotations

import re
from typing import Dict, Iterable, List

from src.intake.contracts import IntakeTurn, NormalizedAuditContext
from src.intake.state import IntakeState


AUDIT_TYPE_PATTERNS = {
    "aml_readiness_review": [
        "aml readiness", "anti money laundering", "aml review", "aml audit"
    ],
    "kyc_kyb_policy_and_control_review": [
        "kyc", "kyb", "customer identification", "beneficial ownership", "onboarding controls"
    ],
    "sanctions_readiness_review": [
        "sanctions", "ofac", "ofsi", "watchlist", "screening"
    ],
    "policy_governance_gap_analysis": [
        "governance gap", "policy gap", "governance review", "policy review"
    ],
    "vendor_internal_compliance_readiness_review": [
        "vendor review", "third party", "outsourcing", "internal compliance readiness"
    ],
    "audit_report_generation_from_uploaded_evidence": [
        "report from evidence", "generate report", "uploaded evidence"
    ],
}

INDUSTRY_PATTERNS = {
    "fintech": ["fintech", "financial technology", "embedded finance"],
    "payments": ["payments", "payment processor", "payment platform", "card issuing", "merchant acquiring"],
    "crypto": ["crypto", "virtual asset", "exchange", "custody", "stablecoin", "wallet"],
}

JURISDICTION_PATTERNS = {
    "US": ["united states", "us", "usa"],
    "UK": ["united kingdom", "uk", "britain", "england"],
    "EU": ["european union", "eu", "europe"],
}

ENTITY_TYPE_PATTERNS = {
    "payments_platform": ["payments platform", "payment platform", "processor", "orchestration platform"],
    "crypto_exchange": ["exchange", "crypto exchange"],
    "wallet_provider": ["wallet", "wallet provider"],
    "merchant_acquirer": ["acquirer", "acquiring"],
    "issuer": ["issuer", "card issuing", "issuing"],
    "vendor": ["vendor", "third party", "provider"],
}

CUSTOMER_TYPE_PATTERNS = {
    "consumer": ["consumer", "individual", "retail user"],
    "smb": ["smb", "small business", "merchant"],
    "enterprise": ["enterprise", "large business", "institutional"],
}

PRODUCT_PATTERNS = {
    "wallet": ["wallet"],
    "card_issuing": ["card issuing", "issuing"],
    "merchant_acquiring": ["merchant acquiring", "acquiring"],
    "cross_border_payments": ["cross border", "international payments"],
    "fiat_on_off_ramp": ["on ramp", "off ramp"],
    "kyc_vendor_workflow": ["sumsub", "persona", "trulioo", "onfido"],
    "blockchain_screening": ["chainalysis", "elliptic", "blockchain screening"],
}

CHANNEL_PATTERNS = {
    "api": ["api"],
    "dashboard": ["dashboard", "portal", "backoffice"],
    "mobile_app": ["mobile app", "ios", "android"],
    "web_app": ["web app", "web portal", "browser"],
}

PAYMENT_FLOW_PATTERNS = {
    "wallet_funding": ["wallet funding", "top up"],
    "merchant_settlement": ["merchant settlement", "settlement"],
    "payouts": ["payout", "disbursement"],
    "card_spend": ["card spend", "card transaction"],
}

DATA_PATTERNS = {
    "identity_data": ["identity data", "kyc data", "passport", "id document"],
    "transaction_data": ["transaction data", "payments data", "ledger"],
    "beneficial_ownership_data": ["beneficial owner", "ubo"],
    "sanctions_screening_data": ["screening data", "watchlist match"],
}

HIGH_RISK_PATTERNS = {
    "cross_border_payments": ["cross border", "international payments"],
    "high_risk_geographies": ["high risk geography", "sanctioned geography"],
    "crypto_exposure": ["crypto", "virtual asset"],
    "third_party_dependence": ["vendor", "outsourced", "third party"],
}

SOURCE_FAMILY_HINTS = {
    "aml_readiness_review": ["regulations", "aml", "enforcement"],
    "kyc_kyb_policy_and_control_review": ["regulations", "aml", "kyc"],
    "sanctions_readiness_review": ["regulations", "sanctions", "enforcement"],
    "policy_governance_gap_analysis": ["regulations", "governance"],
    "vendor_internal_compliance_readiness_review": ["regulations", "vendor_risk", "governance"],
    "audit_report_generation_from_uploaded_evidence": ["uploaded_evidence"],
}


def _lower(text: str) -> str:
    return (text or "").strip().lower()


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    return any(p in text for p in phrases)


def _extract_first_match(text: str, pattern_map: Dict[str, List[str]]) -> str | None:
    for canonical, phrases in pattern_map.items():
        if _contains_any(text, phrases):
            return canonical
    return None


def _extract_multi_match(text: str, pattern_map: Dict[str, List[str]]) -> List[str]:
    matches: List[str] = []
    for canonical, phrases in pattern_map.items():
        if _contains_any(text, phrases):
            matches.append(canonical)
    return sorted(set(matches))


def _extract_entity_name(message: str) -> str | None:
    patterns = [
        r"(?:we are|company is|entity is|business is|platform is)\s+([A-Z][A-Za-z0-9&\-\s]{1,60})",
        r"(?:our company|our platform|our entity)\s+([A-Z][A-Za-z0-9&\-\s]{1,60})",
    ]
    for pattern in patterns:
        m = re.search(pattern, message)
        if m:
            return m.group(1).strip()
    return None


def _merge_unique(existing: List[str], incoming: List[str]) -> List[str]:
    return sorted(set(existing + incoming))


def normalize_turn(state: IntakeState, turn: IntakeTurn) -> IntakeState:
    text = _lower(turn.user_message)
    ctx = state.context

    audit_type = _extract_first_match(text, AUDIT_TYPE_PATTERNS)
    if audit_type and not ctx.audit_type:
        ctx.audit_type = audit_type
        ctx.field_confidence["audit_type"] = 0.8

    industry = _extract_first_match(text, INDUSTRY_PATTERNS)
    if industry and not ctx.industry:
        ctx.industry = industry
        ctx.field_confidence["industry"] = 0.8

    jurisdictions = _extract_multi_match(text, JURISDICTION_PATTERNS)
    if jurisdictions:
        ctx.jurisdictions = _merge_unique(ctx.jurisdictions, jurisdictions)
        ctx.field_confidence["jurisdictions"] = 0.8

    entity_type = _extract_first_match(text, ENTITY_TYPE_PATTERNS)
    if entity_type and not ctx.entity_type:
        ctx.entity_type = entity_type
        ctx.field_confidence["entity_type"] = 0.7

    customer_types = _extract_multi_match(text, CUSTOMER_TYPE_PATTERNS)
    if customer_types:
        ctx.customer_types = _merge_unique(ctx.customer_types, customer_types)
        ctx.field_confidence["customer_types"] = 0.7

    products = _extract_multi_match(text, PRODUCT_PATTERNS)
    if products:
        ctx.products = _merge_unique(ctx.products, products)
        ctx.field_confidence["products"] = 0.75

    channels = _extract_multi_match(text, CHANNEL_PATTERNS)
    if channels:
        ctx.distribution_channels = _merge_unique(ctx.distribution_channels, channels)

    payment_flows = _extract_multi_match(text, PAYMENT_FLOW_PATTERNS)
    if payment_flows:
        ctx.payment_flows = _merge_unique(ctx.payment_flows, payment_flows)

    data_categories = _extract_multi_match(text, DATA_PATTERNS)
    if data_categories:
        ctx.data_categories_processed = _merge_unique(ctx.data_categories_processed, data_categories)

    high_risk = _extract_multi_match(text, HIGH_RISK_PATTERNS)
    if high_risk:
        ctx.high_risk_activities = _merge_unique(ctx.high_risk_activities, high_risk)

    entity_name = _extract_entity_name(turn.user_message)
    if entity_name and not ctx.entity_name:
        ctx.entity_name = entity_name
        ctx.field_confidence["entity_name"] = 0.6

    if turn.uploaded_filenames:
        ctx.evidence_paths = _merge_unique(ctx.evidence_paths, turn.uploaded_filenames)
    if turn.uploaded_urls:
        ctx.evidence_paths = _merge_unique(ctx.evidence_paths, turn.uploaded_urls)

    if ctx.audit_type:
        ctx.source_families = _merge_unique(ctx.source_families, SOURCE_FAMILY_HINTS.get(ctx.audit_type, []))

    query_terms: List[str] = []
    if ctx.audit_type:
        query_terms.append(ctx.audit_type.replace("_", " "))
    if ctx.industry:
        query_terms.append(ctx.industry)
    query_terms.extend(ctx.products)
    query_terms.extend(ctx.customer_types)
    query_terms.extend(ctx.high_risk_activities)
    ctx.query_terms = _merge_unique(ctx.query_terms, query_terms)

    if turn.user_message.strip():
        state.conversation_history.append({"role": "user", "content": turn.user_message.strip()})

    state.update_ready_flag()
    return state


def normalize_state_to_audit_context(state: IntakeState) -> Dict[str, object]:
    ctx = state.context
    note_bits: List[str] = []
    if state.inferred_facts:
        note_bits.append("Inferred: " + "; ".join(state.inferred_facts))
    if state.contradictions:
        note_bits.append("Contradictions: " + "; ".join(state.contradictions))
    if ctx.notes:
        note_bits.append(ctx.notes)

    return {
        "audit_type": ctx.audit_type,
        "industry": ctx.industry,
        "jurisdictions": ctx.jurisdictions,
        "entity_name": ctx.entity_name,
        "entity_type": ctx.entity_type,
        "trade_name": ctx.trade_name,
        "business_model": ctx.business_model,
        "products": ctx.products,
        "customer_types": ctx.customer_types,
        "customer_geographies": ctx.customer_geographies,
        "distribution_channels": ctx.distribution_channels,
        "payment_flows": ctx.payment_flows,
        "data_categories_processed": ctx.data_categories_processed,
        "high_risk_activities": ctx.high_risk_activities,
        "source_families": ctx.source_families,
        "query_terms": ctx.query_terms,
        "evidence_paths": ctx.evidence_paths,
        "excluded_domains": ctx.excluded_domains,
        "notes": " | ".join(note_bits).strip() if note_bits else None,
    }
