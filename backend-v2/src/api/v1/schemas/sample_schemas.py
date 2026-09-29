"""Pydantic schemas for Sample & SampleResult endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.api.v1.schemas.product_schemas import ProductResponse
from src.api.v1.schemas.test_schemas import TestResponse


class CreateSampleRequest(BaseModel):
    product_id: int
    batch_number: str
    quantity_received: float
    unit: str
    sample_type: str | None = None
    priority: str | None = "Normal"
    sap_inspection_lot: str | None = None
    sap_material: str | None = None
    sap_plant: str | None = None
    sap_vendor: str | None = None
    sap_vendor_batch: str | None = None
    manufacturing_date: datetime | None = None
    expiry_date: datetime | None = None


class SubmitResultRequest(BaseModel):
    result_value: float | None = None
    result_text: str | None = None
    password: str
    comments: str | None = None


class SampleResultResponse(BaseModel):
    id: int
    sample_id: int
    test_id: int
    min_limit: float | None = None
    max_limit: float | None = None
    expected_result: str | None = None
    result_value: float | None = None
    result_text: str | None = None
    status: str
    is_oos: bool
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    test: TestResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class SampleResponse(BaseModel):
    id: int
    sample_code: str
    product_id: int
    batch_number: str
    quantity_received: float
    unit: str
    sample_type: str | None = None
    priority: str | None = None
    status: str
    sap_inspection_lot: str | None = None
    sap_ud_posted: bool | None = False
    manufacturing_date: datetime | None = None
    expiry_date: datetime | None = None
    logged_by: str | None = None
    logged_at: datetime | None = None
    received_by: str | None = None
    received_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    coa_released_by: str | None = None
    coa_released_at: datetime | None = None
    coa_data: dict | None = None
    product: ProductResponse | None = None
    results: list[SampleResultResponse] = []

    model_config = ConfigDict(from_attributes=True)
