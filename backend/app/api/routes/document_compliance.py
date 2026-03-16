from fastapi import APIRouter
from backend.app.schemas.document_compliance import DocumentComplianceOutput
from backend.app.services.document_compliance_service import run_document_compliance

router = APIRouter(prefix="/document-compliance", tags=["document-compliance"])


@router.get("/mock", response_model=DocumentComplianceOutput)
def document_compliance_mock():
    return run_document_compliance("Vendor Policy")
