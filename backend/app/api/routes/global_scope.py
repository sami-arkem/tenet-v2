from fastapi import APIRouter
from backend.app.schemas.global_scope import GlobalScopeResponse
from backend.app.services.global_scope_service import get_global_scope

router = APIRouter(prefix="/global-scope", tags=["global-scope"])


@router.get("", response_model=GlobalScopeResponse)
def global_scope():
    return GlobalScopeResponse(**get_global_scope())
