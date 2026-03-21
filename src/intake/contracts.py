from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class IntakeTurn:
    user_message: str
    uploaded_filenames: List[str] = field(default_factory=list)
    uploaded_urls: List[str] = field(default_factory=list)


@dataclass
class NormalizedAuditContext:
    audit_type: Optional[str] = None
    industry: Optional[str] = None
    jurisdictions: List[str] = field(default_factory=list)

    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    trade_name: Optional[str] = None
    business_model: Optional[str] = None

    products: List[str] = field(default_factory=list)
    customer_types: List[str] = field(default_factory=list)
    customer_geographies: List[str] = field(default_factory=list)
    distribution_channels: List[str] = field(default_factory=list)
    payment_flows: List[str] = field(default_factory=list)
    data_categories_processed: List[str] = field(default_factory=list)
    high_risk_activities: List[str] = field(default_factory=list)

    source_families: List[str] = field(default_factory=list)
    query_terms: List[str] = field(default_factory=list)
    evidence_paths: List[str] = field(default_factory=list)
    excluded_domains: List[str] = field(default_factory=list)

    notes: Optional[str] = None

    field_confidence: Dict[str, float] = field(default_factory=dict)
    open_questions: List[str] = field(default_factory=list)
    evidence_gaps: List[str] = field(default_factory=list)
