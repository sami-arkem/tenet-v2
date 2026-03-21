"""
Tests for Evidence Classification Agent — Bible §7 + §T.1.
"""
import os
import tempfile
import pytest
from app.agents.evidence_agent import (
    ClassificationResult,
    Confidence,
    DocumentType,
    classify_evidence,
    _classify_by_keywords,
    _score_to_confidence,
)


class TestKeywordClassification:

    def test_aml_policy_keywords(self):
        text = "This anti-money laundering policy covers all AML requirements including suspicious activity reports and tipping off."
        doc_type, score, keywords = _classify_by_keywords(text)
        assert doc_type == DocumentType.AML_POLICY
        assert score > 0.0
        assert len(keywords) > 0

    def test_kyc_procedure_keywords(self):
        text = "Customer due diligence procedures. Know your customer (KYC) requirements. Beneficial owner identification. UBO register."
        doc_type, score, keywords = _classify_by_keywords(text)
        assert doc_type == DocumentType.KYC_PROCEDURE
        assert score > 0.0

    def test_gdpr_privacy_notice_keywords(self):
        text = "GDPR privacy notice. Data subject rights including right to erasure. Lawful basis for processing. Data Protection Officer contact."
        doc_type, score, keywords = _classify_by_keywords(text)
        assert doc_type == DocumentType.GDPR_PRIVACY_NOTICE
        assert score > 0.0

    def test_sanctions_policy_keywords(self):
        text = "Sanctions policy covering OFAC SDN list and UN Security Council sanctions screening procedures."
        doc_type, score, keywords = _classify_by_keywords(text)
        assert doc_type == DocumentType.SANCTIONS_POLICY

    def test_transaction_monitoring_keywords(self):
        text = "Transaction monitoring system with alert thresholds and velocity checks for structuring detection."
        doc_type, score, keywords = _classify_by_keywords(text)
        assert doc_type == DocumentType.TRANSACTION_MONITORING_POLICY

    def test_training_records_keywords(self):
        text = "AML training completion records. Staff training log. Annual training certificates."
        doc_type, score, keywords = _classify_by_keywords(text)
        assert doc_type == DocumentType.TRAINING_RECORDS

    def test_risk_assessment_keywords(self):
        text = "Risk assessment. Inherent risk and residual risk rating matrix. Risk appetite statement."
        doc_type, score, keywords = _classify_by_keywords(text)
        assert doc_type == DocumentType.RISK_ASSESSMENT

    def test_empty_text_returns_unknown(self):
        doc_type, score, keywords = _classify_by_keywords("")
        assert doc_type == DocumentType.UNKNOWN
        assert score == 0.0
        assert keywords == []

    def test_whitespace_only_returns_unknown(self):
        doc_type, score, keywords = _classify_by_keywords("   \n\t  ")
        assert doc_type == DocumentType.UNKNOWN

    def test_random_text_returns_unknown(self):
        doc_type, score, keywords = _classify_by_keywords("The quick brown fox jumps over the lazy dog.")
        assert doc_type == DocumentType.UNKNOWN


class TestConfidenceScoring:

    def test_high_confidence_threshold(self):
        assert _score_to_confidence(0.80) == Confidence.HIGH
        assert _score_to_confidence(0.95) == Confidence.HIGH
        assert _score_to_confidence(1.0) == Confidence.HIGH

    def test_medium_confidence_threshold(self):
        assert _score_to_confidence(0.50) == Confidence.MEDIUM
        assert _score_to_confidence(0.65) == Confidence.MEDIUM
        assert _score_to_confidence(0.79) == Confidence.MEDIUM

    def test_low_confidence_threshold(self):
        assert _score_to_confidence(0.0) == Confidence.LOW
        assert _score_to_confidence(0.25) == Confidence.LOW
        assert _score_to_confidence(0.49) == Confidence.LOW

    def test_boundary_at_0_50(self):
        assert _score_to_confidence(0.499) == Confidence.LOW
        assert _score_to_confidence(0.500) == Confidence.MEDIUM

    def test_boundary_at_0_80(self):
        assert _score_to_confidence(0.799) == Confidence.MEDIUM
        assert _score_to_confidence(0.800) == Confidence.HIGH


class TestClassifyEvidence:

    def _write_temp_file(self, content: str, suffix: str = ".txt") -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
        f.write(content)
        f.close()
        return f.name

    def teardown_method(self):
        # Cleanup handled per-test
        pass

    def test_nonexistent_file_returns_error(self):
        result = classify_evidence("/nonexistent/path/file.txt", "text/plain")
        assert result.is_empty is True
        assert result.error is not None
        assert result.document_type == DocumentType.UNKNOWN

    def test_empty_file_returns_empty_flag(self):
        path = self._write_temp_file("")
        try:
            result = classify_evidence(path, "text/plain")
            assert result.is_empty is True
            assert result.word_count == 0
        finally:
            os.unlink(path)

    def test_aml_policy_text_file(self):
        content = """
        ANTI-MONEY LAUNDERING POLICY
        This document sets out our AML policy for preventing money laundering.
        All staff must report suspicious activity reports (SARs) to the MLRO.
        Tipping off is prohibited under POCA 2002.
        Customer due diligence must be applied to all customers.
        """
        path = self._write_temp_file(content, ".txt")
        try:
            result = classify_evidence(path, "text/plain")
            assert result.document_type == DocumentType.AML_POLICY
            assert result.is_empty is False
            assert result.word_count > 0
            assert result.extraction_method in ("direct", "fallback")
        finally:
            os.unlink(path)

    def test_gdpr_privacy_notice_classification(self):
        content = """
        PRIVACY NOTICE
        We are the data controller for your personal data.
        Lawful basis: legitimate interest and consent.
        Your rights include: right to access, right to erasure, right to rectification.
        Contact our Data Protection Officer at dpo@company.com.
        We will notify the ICO of any personal data breach within 72 hours.
        """
        path = self._write_temp_file(content, ".txt")
        try:
            result = classify_evidence(path, "text/plain")
            assert result.document_type == DocumentType.GDPR_PRIVACY_NOTICE
        finally:
            os.unlink(path)

    def test_word_count_computed(self):
        content = "one two three four five six seven eight nine ten"
        path = self._write_temp_file(content, ".txt")
        try:
            result = classify_evidence(path, "text/plain")
            assert result.word_count == 10
        finally:
            os.unlink(path)

    def test_extracted_text_capped_at_50k_chars(self):
        content = "a " * 30_000  # 60k chars
        path = self._write_temp_file(content, ".txt")
        try:
            result = classify_evidence(path, "text/plain")
            assert len(result.extracted_text) <= 50_000
        finally:
            os.unlink(path)

    def test_json_file_extracted(self):
        content = '{"anti_money_laundering": true, "aml_policy": "active", "suspicious_activity": "monitored"}'
        path = self._write_temp_file(content, ".json")
        try:
            result = classify_evidence(path, "application/json")
            assert result.extracted_text != ""
        finally:
            os.unlink(path)
