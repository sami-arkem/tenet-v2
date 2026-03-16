from typing import List
from pydantic import BaseModel


class TaskContract(BaseModel):
    name: str
    required_input: List[str]
    required_output: List[str]


class ModelContractResponse(BaseModel):
    tasks: List[TaskContract]
