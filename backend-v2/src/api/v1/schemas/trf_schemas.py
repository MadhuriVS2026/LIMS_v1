"""Pydantic schemas for TRF — Test Request Form endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateTRFRequest(BaseModel):
    product_id: int
    batch_number: str
    label_claim: str | None = None
    stage_of_sample: str | None = None
    group_name: str | None = None
    quantity: str | None = None
    storage_condition: str | None = None
    storage_period: str | None = None
    pack_details: str | None = None
    manufactured_by: str | None = None
    mfg_date: datetime | None = None
    expiry_or_retest_date: datetime | None = None
    remark: str | None = None


class CreateTestLineRequest(BaseModel):
    test_id: int
    specification: str | None = None
    raw_data_reference: str | None = None
    remark: str | None = None


class TRFTestLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trf_id: int
    line_no: int
    test_id: int
    test_code: str | None = None
    test_name: str | None = None
    specification: str | None = None
    raw_data_reference: str | None = None
    result: str | None = None
    remark: str | None = None
    status: str


class TRFResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trf_number: str
    ar_number: str | None = None
    product_id: int
    batch_number: str
    label_claim: str | None = None
    stage_of_sample: str | None = None
    group_name: str | None = None
    quantity: str | None = None
    storage_condition: str | None = None
    storage_period: str | None = None
    pack_details: str | None = None
    manufactured_by: str | None = None
    mfg_date: datetime | None = None
    expiry_or_retest_date: datetime | None = None
    remark: str | None = None
    source: str
    status: str
    created_by: str
    created_date: datetime
    initiated_by: str | None = None
    initiated_at: datetime | None = None
    fdgl_approved_by: str | None = None
    fdgl_approved_at: datetime | None = None
    adgl_accepted_by: str | None = None
    adgl_accepted_at: datetime | None = None
    analyst_accepted_by: str | None = None
    analyst_accepted_at: datetime | None = None
    results_submitted_by: str | None = None
    results_submitted_at: datetime | None = None
    released_by: str | None = None
    released_at: datetime | None = None
    referred_back_by: str | None = None
    referred_back_at: datetime | None = None
    referred_back_comments: str | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    rejected_comments: str | None = None
    test_lines: list[TRFTestLineResponse] = []


class SubmitTestResultRequest(BaseModel):
    result: str | None = None
    remark: str | None = None


class EsignActionRequest(BaseModel):
    """Shared shape for e-signed gate actions (FDGL Approve, ADGL Accept, Submit Results, Release)."""

    password: str


class ReferBackRejectRequest(BaseModel):
    comments: str


class ATRResponse(BaseModel):
    """Passthrough wrapper for the immutable ATR snapshot dict captured at release."""

    model_config = ConfigDict(extra="allow")

    trf_number: str
    ar_number: str | None = None
