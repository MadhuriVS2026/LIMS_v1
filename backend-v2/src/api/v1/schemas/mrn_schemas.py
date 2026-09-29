"""Pydantic schemas for MRN — Material Requisition & Consumption endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MRNMaterialLotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grn_document_no: str
    grn_item_no: str
    material_code: str
    material_description: str | None = None
    batch_number: str | None = None
    plant: str
    unit: str
    original_quantity: float
    consumed_quantity: float
    available_quantity: float
    status: str
    grn_date: datetime | None = None
    pulled_at: datetime | None = None


class MaterialQueuePullResponse(BaseModel):
    pulled: int
    lots: list[MRNMaterialLotResponse]


class CreateLineItemRequest(BaseModel):
    lot_id: int
    requested_quantity: float
    project_code: str


class MRNLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mrn_id: int
    line_no: int
    lot_id: int
    requested_quantity: float
    project_code: str
    status: str
    lot_material_code: str | None = None
    lot_batch_number: str | None = None
    consumption_posting_id: int | None = None


class MaterialRequisitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mrn_number: str
    status: str
    created_by: str
    created_date: datetime
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    posted_by: str | None = None
    posted_at: datetime | None = None
    line_items: list[MRNLineItemResponse] = []


class ApproveAndPostRequest(BaseModel):
    password: str
    comments: str | None = None


class ConsumptionPostingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_item_id: int
    idempotency_key: str
    status: str
    sap_doc_no: str | None = None
    error_message: str | None = None
    posted_at: datetime | None = None
