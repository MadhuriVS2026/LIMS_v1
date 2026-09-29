"""Pydantic schemas for Specification endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.api.v1.schemas.product_schemas import ProductResponse
from src.api.v1.schemas.test_schemas import TestResponse


class SpecTestItem(BaseModel):
    test_id: int
    min_limit: float | None = None
    max_limit: float | None = None
    expected_result: str | None = None
    display_in_coa: bool = True


class CreateSpecificationRequest(BaseModel):
    product_id: int
    spec_type: str | None = None
    document_no: str | None = None
    tests: list[SpecTestItem]


class UpdateSpecificationRequest(BaseModel):
    """All fields optional. Providing `tests` replaces the full limit set.
    Editing an approved spec returns it to Pending Approval (re-approval)."""
    spec_type: str | None = None
    document_no: str | None = None
    tests: list[SpecTestItem] | None = None


class SpecTestResponse(BaseModel):
    id: int
    test_id: int
    min_limit: float | None = None
    max_limit: float | None = None
    expected_result: str | None = None
    display_in_coa: bool = True
    test: TestResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class SpecificationResponse(BaseModel):
    id: int
    product_id: int
    version: int
    spec_type: str | None = None
    document_no: str | None = None
    status: str
    created_by: str | None = None
    created_date: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    tests: list[SpecTestResponse] = []
    product: ProductResponse | None = None

    model_config = ConfigDict(from_attributes=True)
