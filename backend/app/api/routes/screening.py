from fastapi import APIRouter
from backend.app.schemas.screening import ScreeningStatusResponse

router = APIRouter(prefix="/screening", tags=["screening"])


@router.get("/status", response_model=ScreeningStatusResponse)
def screening_status():
    return ScreeningStatusResponse(status="ok", module="screening")
