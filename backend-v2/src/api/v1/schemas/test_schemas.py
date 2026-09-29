"""Pydantic schemas for Test Parameter endpoints."""
from pydantic import BaseModel, ConfigDict


class CreateTestRequest(BaseModel):
    code: str
    name: str
    type: str
    unit: str | None = None
    method_no: str | None = None
    category: str | None = None
    technique: str | None = None


class TestResponse(BaseModel):
    id: int
    code: str
    name: str
    type: str
    unit: str | None = None
    method_no: str | None = None
    category: str | None = None
    technique: str | None = None
    status: str

    model_config = ConfigDict(from_attributes=True)
