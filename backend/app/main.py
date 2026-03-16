from fastapi import FastAPI
from backend.app.api.routes.document_compliance import router as document_compliance_router
from backend.app.api.routes.gap_detection import router as gap_detection_router
from backend.app.api.routes.global_scope import router as global_scope_router
from backend.app.api.routes.kyb import router as kyb_router
from backend.app.api.routes.kyc import router as kyc_router
from backend.app.api.routes.model_contract import router as model_contract_router
from backend.app.api.routes.report_contract import router as report_contract_router
from backend.app.api.routes.risk_classification import router as risk_classification_router
from backend.app.api.routes.sanctions import router as sanctions_router
from backend.app.api.routes.screening import router as screening_router
from backend.app.schemas.health import HealthResponse

app = FastAPI(title="Tenet API", version="0.1.0")

app.include_router(screening_router)
app.include_router(sanctions_router)
app.include_router(model_contract_router)
app.include_router(report_contract_router)
app.include_router(global_scope_router)
app.include_router(kyc_router)
app.include_router(kyb_router)
app.include_router(risk_classification_router)
app.include_router(gap_detection_router)
app.include_router(document_compliance_router)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", service="tenet-api")
