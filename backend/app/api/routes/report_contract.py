from fastapi import APIRouter
from backend.app.schemas.report_contract import ReportContractResponse
from backend.app.services.report_contract_service import get_report_contract

router = APIRouter(prefix="/report-contract", tags=["report-contract"])


@router.get("", response_model=ReportContractResponse)
def report_contract():
    return ReportContractResponse(**get_report_contract())
