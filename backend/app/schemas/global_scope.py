from typing import List
from pydantic import BaseModel


class GlobalScopeResponse(BaseModel):
    vision: str
    coverage: List[str]
    jurisdictions: List[str]
