from src.llm.model_adapter import ModelAdapter, ModelResponse
from src.reporting.report_transformer import ReportTransformer, ReportTransformerError


AUDIT_OUTPUT = {
    "deployment_decision": {"status": "BLOCKED"},
    "entity_profile": {"legal_name": "Test Entity"},
    "findings": [{"title": "Transaction monitoring framework documented"}],
    "missing_controls": [{"control_id": "AML-003"}],
}


class InlineAdapter(ModelAdapter):
    def __init__(self):
        self.calls = []

    def is_configured(self):
        return True

    def generate_json(self, request):
        self.calls.append(request)
        return ModelResponse(
            model_name="gpt-4.1-mini",
            provider="openai_compatible",
            content={
                "board_memo_markdown": "# Board Memo\n\nTest Entity\n\nBLOCKED",
                "regulator_memo_markdown": "# Regulator Memo\n\nTest Entity\n\nBLOCKED\n\nAML-003",
                "client_report_markdown": "# Client Report\n\nTest Entity\n\nBLOCKED\n\nTransaction monitoring framework documented",
            },
            raw_usage={},
        )


def test_report_transformer():
    transformer = ReportTransformer(model_adapter=InlineAdapter())
    result = transformer.transform(AUDIT_OUTPUT, model_name="gpt-4.1-mini")
    assert "Board Memo" in result.reports["board_memo_markdown"]


class SequenceAdapter(ModelAdapter):
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def is_configured(self):
        return True

    def generate_json(self, request):
        self.calls.append(request)
        content = self.responses.pop(0)
        return ModelResponse(
            model_name="gpt-4.1-mini",
            provider="openai_compatible",
            content=content,
            raw_usage={},
        )


def test_report_transformer_repairs_invalid_first_draft():
    adapter = SequenceAdapter(
        [
            {
                "board_memo_markdown": "# Board Memo\n\nTest Entity\n\nBLOCKED",
                "regulator_memo_markdown": "# Regulator Memo\n\nTest Entity\n\nBLOCKED",
                "client_report_markdown": "# Client Report\n\nTest Entity\n\nBLOCKED",
            },
            {
                "board_memo_markdown": "# Board Memo\n\nTest Entity\n\nBLOCKED",
                "regulator_memo_markdown": "# Regulator Memo\n\nTest Entity\n\nBLOCKED\n\nAML-003",
                "client_report_markdown": "# Client Report\n\nTest Entity\n\nBLOCKED\n\nTransaction monitoring framework documented",
            },
        ]
    )
    transformer = ReportTransformer(model_adapter=adapter)
    result = transformer.transform(AUDIT_OUTPUT, model_name="gpt-4.1-mini")
    assert "AML-003" in result.reports["regulator_memo_markdown"]
    assert len(adapter.calls) == 2
    assert "repair_request" in adapter.calls[1].messages[1]["content"]


def test_report_transformer_fails_loudly_after_second_invalid_draft():
    adapter = SequenceAdapter(
        [
            {
                "board_memo_markdown": "# Board Memo\n\nTest Entity\n\nBLOCKED",
                "regulator_memo_markdown": "# Regulator Memo\n\nTest Entity\n\nBLOCKED",
                "client_report_markdown": "# Client Report\n\nTest Entity\n\nBLOCKED",
            },
            {
                "board_memo_markdown": "# Board Memo\n\nTest Entity\n\nBLOCKED",
                "regulator_memo_markdown": "# Regulator Memo\n\nTest Entity\n\nBLOCKED",
                "client_report_markdown": "# Client Report\n\nTest Entity\n\nBLOCKED",
            },
        ]
    )
    transformer = ReportTransformer(model_adapter=adapter)
    try:
        transformer.transform(AUDIT_OUTPUT, model_name="gpt-4.1-mini")
    except ReportTransformerError as exc:
        assert "Report validation failed after repair pass" in str(exc)
        assert "Transaction monitoring framework documented" in str(exc)
    else:
        raise AssertionError("Expected ReportTransformerError")
