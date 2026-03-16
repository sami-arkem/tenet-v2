from pydantic import BaseModel


class SanctionsStatusResponse(BaseModel):
    status: str
    provider: str
