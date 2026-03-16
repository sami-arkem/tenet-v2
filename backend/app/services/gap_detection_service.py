from backend.app.schemas.gap_detection import ControlGap, GapDetectionOutput


def run_gap_detection(system_name: str) -> GapDetectionOutput:
    return GapDetectionOutput(
        task="gap_detection",
        system_name=system_name,
        overall_gap_score=88,
        missing_controls=["human_oversight", "bias_testing", "explainability"],
        control_gaps=[
            ControlGap(
                control="human_oversight",
                severity="HIGH",
                reason="Missing human review checkpoint",
            ),
            ControlGap(
                control="bias_testing",
                severity="HIGH",
                reason="No bias testing evidence found",
            ),
            ControlGap(
                control="explainability",
                severity="MEDIUM",
                reason="No explainability documentation found",
            ),
        ],
        findings=["Critical compliance controls are missing"],
        confidence=0.95,
    )
