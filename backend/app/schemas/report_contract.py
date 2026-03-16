from pydantic import BaseModel


class ReportPipeline(BaseModel):
    input_layer: str
    reasoning_layer: str
    report_layer: str
    output: str


class ReportContractResponse(BaseModel):
    report_pipeline: ReportPipeline
