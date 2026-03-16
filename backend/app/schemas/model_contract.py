from pydantic import BaseModel
from typing import List


class SupportedTasksResponse(BaseModel):
    tasks: List[str]
