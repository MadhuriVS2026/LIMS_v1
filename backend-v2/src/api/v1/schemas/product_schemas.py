"""Pydantic schemas for Product/Material endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateProductRequest(BaseModel):
    code: str
    name: str
    description: str | None = None
    material_type: str | None = None
    retest_period_days: int | None = None
    storage_condition: str | None = None


class ProductResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    material_type: str | None = None
    retest_period_days: int | None = None
    storage_condition: str | None = None
    status: str
    created_by: str | None = None
    created_date: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
