from fastapi import APIRouter
from backend.app.schemas.kyc import KYCOutput
from backend.app.services.kyc_service import run_kyc_screening

router = APIRouter(prefix="/kyc", tags=["kyc"])


@router.get("/mock", response_model=KYCOutput)
def kyc_mock():
    return run_kyc_screening("Sarah Johnson")
