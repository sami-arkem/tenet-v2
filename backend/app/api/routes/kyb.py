from fastapi import APIRouter
from backend.app.schemas.kyb import KYBOutput
from backend.app.services.kyb_service import run_kyb_screening

router = APIRouter(prefix="/kyb", tags=["kyb"])


@router.get("/mock", response_model=KYBOutput)
def kyb_mock():
    return run_kyb_screening("Crypto Exchange LLC")
