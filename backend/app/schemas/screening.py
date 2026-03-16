from pydantic import BaseModel


class ScreeningStatusResponse(BaseModel):
    status: str
    module: str
