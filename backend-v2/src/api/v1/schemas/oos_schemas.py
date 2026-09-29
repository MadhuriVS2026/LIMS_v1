"""Pydantic schemas for OOS Investigation endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.api.v1.schemas.test_schemas import TestResponse


class CloseOOSRequest(BaseModel):
    root_cause: str
    corrective_action: str
    password: str


class OOSResponse(BaseModel):
    id: int
    sample_id: int
    test_id: int
    investigation_type: str | None = "OOS"
    phase1_comments: str
    root_cause: str | None = None
    corrective_action: str | None = None
    status: str
    created_by: str
    created_date: datetime
    closed_by: str | None = None
    closed_at: datetime | None = None
    test: TestResponse | None = None

    model_config = ConfigDict(from_attributes=True)
