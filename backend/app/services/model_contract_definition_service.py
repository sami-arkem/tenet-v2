def get_model_contract():
    return {
        "tasks": [
            {
                "name": "kyc_screening",
                "required_input": ["full_name", "entity_type"],
                "required_output": ["task", "entity_name", "risk_score", "risk_band", "decision", "findings", "confidence"],
            },
            {
                "name": "kyb_screening",
                "required_input": ["company_name", "jurisdiction", "industry"],
                "required_output": ["task", "company_name", "risk_score", "risk_band", "decision", "risk_factors", "findings", "confidence"],
            },
            {
                "name": "risk_classification",
                "required_input": ["system_name", "system_description", "jurisdiction", "use_case", "sector"],
                "required_output": ["task", "system_name", "overall_risk_score", "risk_tier", "triggered_categories", "required_controls", "findings", "confidence"],
            },
            {
                "name": "gap_detection",
                "required_input": ["system_name", "jurisdiction", "system_type", "controls_present"],
                "required_output": ["task", "system_name", "overall_gap_score", "missing_controls", "control_gaps", "findings", "confidence"],
            },
            {
                "name": "document_compliance_analysis",
                "required_input": ["document_name", "document_type", "document_text", "jurisdiction"],
                "required_output": ["task", "document_name", "risk_score", "triggered_obligations", "identified_gaps", "findings", "confidence"],
            },
        ]
    }
