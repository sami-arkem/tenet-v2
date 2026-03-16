from fastapi import APIRouter
from backend.app.schemas.risk_classification import RiskClassificationOutput
from backend.app.services.risk_classification_service import run_risk_classification

router = APIRouter(prefix="/risk-classification", tags=["risk-classification"])


@router.get("/mock", response_model=RiskClassificationOutput)
def risk_classification_mock():
    return run_risk_classification("Autonomous Credit Decisioning")
