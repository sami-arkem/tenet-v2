from fastapi import APIRouter
from backend.app.schemas.model_contract import SupportedTasksResponse
from backend.app.schemas.model_contract_definition import ModelContractResponse
from backend.app.services.model_contract_definition_service import get_model_contract
from backend.app.services.model_contract_service import get_supported_tasks

router = APIRouter(prefix="/model-contract", tags=["model-contract"])


@router.get("/tasks", response_model=SupportedTasksResponse)
def supported_tasks():
    data = get_supported_tasks()
    return SupportedTasksResponse(**data)


@router.get("", response_model=ModelContractResponse)
def model_contract():
    data = get_model_contract()
    return ModelContractResponse(**data)
