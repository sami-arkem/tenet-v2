"""
Evidence Classification Agent — Bible §7.
Deterministic pipeline:
  1. Text extraction (PDF/DOCX/XLSX/CSV/JSON)
  2. Document classification (rule-based keyword matching first)
  3. Claude for uncertain cases only — never for verdict
  4. Confidence scoring: HIGH/MEDIUM/LOW
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class DocumentType(str, Enum):
    AML_POLICY = "AML_POLICY"
    KYC_PROCEDURE = "KYC_PROCEDURE"
    SANCTIONS_POLICY = "SANCTIONS_POLICY"
    TRANSACTION_MONITORING_POLICY = "TRANSACTION_MONITORING_POLICY"
    GDPR_PRIVACY_NOTICE = "GDPR_PRIVACY_NOTICE"
    DATA_RETENTION_POLICY = "DATA_RETENTION_POLICY"
    BOARD_MINUTES = "BOARD_MINUTES"
    TRAINING_RECORDS = "TRAINING_RECORDS"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    AUDIT_REPORT = "AUDIT_REPORT"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    CONTRACT = "CONTRACT"
    EVIDENCE_OTHER = "EVIDENCE_OTHER"
    UNKNOWN = "UNKNOWN"


class Confidence(str, Enum):
    HIGH = "HIGH"      # ≥ 0.80 — auto-confirmed
    MEDIUM = "MEDIUM"  # 0.50–0.79 — show "Is this correct?" prompt
    LOW = "LOW"        # < 0.50 — "We couldn't classify this"


@dataclass
class ClassificationResult:
    document_type: DocumentType
    confidence: Confidence
    confidence_score: float
    extracted_text: str
    word_count: int
    page_count: int
    is_empty: bool
    is_password_protected: bool
    extraction_method: str  # 'direct' | 'ocr' | 'fallback'
    keywords_matched: list[str] = field(default_factory=list)
    error: Optional[str] = None


# ─── Keyword classification rules ────────────────────────────────────────────
# Each type maps to a list of strong signal keywords.
# Score = matched_keywords / total_keywords (weighted).

_CLASSIFICATION_RULES: dict[DocumentType, list[str]] = {
    DocumentType.AML_POLICY: [
        "anti-money laundering", "aml policy", "money laundering", "suspicious activity",
        "sar", "unusual transactions", "placement layering integration", "tipping off",
        "proceeds of crime", "financial crime", "poca", "mlra",
    ],
    DocumentType.KYC_PROCEDURE: [
        "know your customer", "kyc", "customer due diligence", "cdd",
        "enhanced due diligence", "edd", "politically exposed", "pep",
        "beneficial owner", "ultimate beneficial owner", "ubo",
        "identity verification", "id verification", "document verification",
    ],
    DocumentType.SANCTIONS_POLICY: [
        "sanctions", "ofac", "sdn list", "un security council", "eu sanctions",
        "sanctions screening", "sanctions compliance", "embargoed", "restricted party",
        "hm treasury", "consolidated list", "financial sanctions",
    ],
    DocumentType.TRANSACTION_MONITORING_POLICY: [
        "transaction monitoring", "tm system", "alert thresholds", "rule-based monitoring",
        "ml monitoring", "behavioral analytics", "structuring", "smurfing",
        "velocity checks", "transaction surveillance", "wire transfer",
    ],
    DocumentType.GDPR_PRIVACY_NOTICE: [
        "gdpr", "general data protection", "data subject", "right to erasure",
        "right to access", "lawful basis", "legitimate interest", "consent",
        "data controller", "data processor", "dpo", "data protection officer",
        "personal data", "privacy notice", "privacy policy",
    ],
    DocumentType.DATA_RETENTION_POLICY: [
        "data retention", "retention period", "retention schedule", "data deletion",
        "data disposal", "record retention", "archive policy", "data lifecycle",
        "purge schedule", "retention policy",
    ],
    DocumentType.BOARD_MINUTES: [
        "board of directors", "board meeting", "minutes of meeting", "resolution",
        "quorum", "agenda", "directors present", "matters arising",
        "risk committee", "audit committee", "governance", "board approved",
    ],
    DocumentType.TRAINING_RECORDS: [
        "training completion", "training records", "staff training", "e-learning",
        "training certificate", "compliance training", "aml training",
        "sanctions training", "training log", "learning management",
    ],
    DocumentType.RISK_ASSESSMENT: [
        "risk assessment", "risk register", "inherent risk", "residual risk",
        "risk appetite", "risk matrix", "risk rating", "likelihood",
        "impact assessment", "business risk assessment", "enterprise risk",
    ],
    DocumentType.AUDIT_REPORT: [
        "audit report", "internal audit", "external audit", "audit findings",
        "audit opinion", "audit scope", "audit conclusion", "control weaknesses",
        "management response", "audit trail", "independent review",
    ],
    DocumentType.FINANCIAL_STATEMENT: [
        "balance sheet", "income statement", "cash flow statement", "profit and loss",
        "audited accounts", "financial statements", "revenue", "liabilities",
        "assets", "equity", "ebitda", "net income", "annual report",
    ],
}


def _extract_text_from_file(file_path: str, mime_type: str) -> tuple[str, int, str]:
    """
    Extract text from file. Returns (text, page_count, method).
    Production: use pdfplumber for PDF, python-docx for DOCX, etc.
    """
    path = Path(file_path)
    if not path.exists():
        return "", 0, "fallback"

    content_type = mime_type.lower()
    raw = b""
    try:
        raw = path.read_bytes()
    except Exception:
        return "", 0, "fallback"

    # PDF extraction
    if content_type == "application/pdf" or path.suffix.lower() == ".pdf":
        try:
            import pdfplumber  # type: ignore[import-untyped]
            with pdfplumber.open(file_path) as pdf:
                texts = []
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    texts.append(t)
                return "\n".join(texts), len(pdf.pages), "direct"
        except ImportError:
            pass
        except Exception:
            pass
        # Fallback: naive byte decode
        text = raw.decode("utf-8", errors="replace")
        return text, 1, "fallback"

    # DOCX extraction
    if "wordprocessingml" in content_type or path.suffix.lower() == ".docx":
        try:
            import docx  # type: ignore[import-untyped]
            doc = docx.Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs)
            return text, 1, "direct"
        except ImportError:
            pass
        except Exception:
            pass

    # XLSX/CSV: just read as text for keyword matching
    if "spreadsheet" in content_type or path.suffix.lower() in (".xlsx", ".csv"):
        try:
            text = raw.decode("utf-8", errors="replace")
            return text, 1, "direct"
        except Exception:
            return "", 0, "fallback"

    # JSON/TXT: direct decode
    try:
        text = raw.decode("utf-8", errors="replace")
        return text, 1, "direct"
    except Exception:
        return "", 0, "fallback"


def _classify_by_keywords(text: str) -> tuple[DocumentType, float, list[str]]:
    """
    Deterministic keyword classification.
    Returns (document_type, confidence_score, matched_keywords).
    Bible Rule 1: no model involved in classification verdict.
    """
    text_lower = text.lower()
    scores: dict[DocumentType, tuple[float, list[str]]] = {}

    for doc_type, keywords in _CLASSIFICATION_RULES.items():
        matched = [kw for kw in keywords if kw in text_lower]
        if matched:
            score = len(matched) / len(keywords)
            scores[doc_type] = (score, matched)

    if not scores:
        return DocumentType.UNKNOWN, 0.0, []

    best_type = max(scores, key=lambda t: scores[t][0])
    best_score, matched_kws = scores[best_type]
    return best_type, best_score, matched_kws


def _score_to_confidence(score: float) -> Confidence:
    if score >= 0.80:
        return Confidence.HIGH
    if score >= 0.50:
        return Confidence.MEDIUM
    return Confidence.LOW


def classify_evidence(file_path: str, mime_type: str) -> ClassificationResult:
    """
    Full evidence classification pipeline.
    Deterministic — model only called if confidence is LOW (optional enrichment).
    """
    # Check if file is empty
    path = Path(file_path)
    if not path.exists() or path.stat().st_size == 0:
        return ClassificationResult(
            document_type=DocumentType.UNKNOWN,
            confidence=Confidence.LOW,
            confidence_score=0.0,
            extracted_text="",
            word_count=0,
            page_count=0,
            is_empty=True,
            is_password_protected=False,
            extraction_method="fallback",
            error="File is empty or does not exist",
        )

    # Text extraction
    text, page_count, method = _extract_text_from_file(file_path, mime_type)

    # Check for password-protected PDF
    is_password_protected = (
        b"%PDF" in path.read_bytes()[:10]
        and len(text.strip()) < 50
        and page_count == 0
    )

    is_empty = len(text.strip()) < 10

    # Deterministic classification
    doc_type, score, keywords = _classify_by_keywords(text)

    # Boost score if file name gives strong signal
    filename = path.name.lower()
    for t, kws in _CLASSIFICATION_RULES.items():
        for kw in kws[:3]:  # only top 3 keywords checked against filename
            if kw.replace(" ", "_") in filename or kw.replace(" ", "-") in filename:
                if t == doc_type:
                    score = min(score + 0.15, 1.0)
                break

    word_count = len(re.findall(r"\b\w+\b", text))

    return ClassificationResult(
        document_type=doc_type,
        confidence=_score_to_confidence(score),
        confidence_score=round(score, 3),
        extracted_text=text[:50_000],  # cap at 50k chars
        word_count=word_count,
        page_count=page_count,
        is_empty=is_empty,
        is_password_protected=is_password_protected,
        extraction_method=method,
        keywords_matched=keywords,
    )
