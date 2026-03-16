from fastapi import APIRouter
from backend.app.schemas.gap_detection import GapDetectionOutput
from backend.app.services.gap_detection_service import run_gap_detection

router = APIRouter(prefix="/gap-detection", tags=["gap-detection"])


@router.get("/mock", response_model=GapDetectionOutput)
def gap_detection_mock():
    return run_gap_detection("Credit Scoring Engine")
