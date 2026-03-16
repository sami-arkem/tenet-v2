from fastapi import APIRouter
from backend.app.schemas.sanctions import SanctionsStatusResponse
from backend.app.services.sanctions_service import get_sanctions_status

router = APIRouter(prefix="/sanctions", tags=["sanctions"])


@router.get("/status", response_model=SanctionsStatusResponse)
def sanctions_status():
    data = get_sanctions_status()
    return SanctionsStatusResponse(**data)
