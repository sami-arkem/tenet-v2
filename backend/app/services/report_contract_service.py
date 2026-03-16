def get_report_contract():
    return {
        "report_pipeline": {
            "input_layer": "user_input_and_documents",
            "reasoning_layer": "tenet_structured_model",
            "report_layer": "claude_report_writer",
            "output": "enterprise_compliance_report",
        }
    }
