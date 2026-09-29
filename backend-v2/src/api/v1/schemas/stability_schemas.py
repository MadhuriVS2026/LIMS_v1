"""Pydantic schemas for Stability Management endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateProtocolRequest(BaseModel):
    product_id: int
    condition: str
    duration_months: int
    study_type: str | None = None
    testing_frequency: str | None = None
    label_claim: str | None = None
    mfg_date: datetime | None = None
    batch_number: str | None = None
    placebo_batch_number: str | None = None
    batch_size: str | None = None
    stability_initiation_date: datetime | None = None
    no_of_samples_time_points: str | None = None
    fill_volume: str | None = None
    api_name: str | None = None
    api_batch_no: str | None = None
    api_source: str | None = None
    primary_pack: str | None = None
    secondary_pack: str | None = None
    headspace: str | None = None
    orientation: str | None = None
    remarks: str | None = None


class StabilityProtocolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    protocol_code: str
    product_id: int
    condition: str
    duration_months: int
    study_type: str | None = None
    testing_frequency: str | None = None
    status: str
    label_claim: str | None = None
    mfg_date: datetime | None = None
    batch_number: str | None = None
    placebo_batch_number: str | None = None
    batch_size: str | None = None
    stability_initiation_date: datetime | None = None
    no_of_samples_time_points: str | None = None
    fill_volume: str | None = None
    api_name: str | None = None
    api_batch_no: str | None = None
    api_source: str | None = None
    primary_pack: str | None = None
    secondary_pack: str | None = None
    headspace: str | None = None
    orientation: str | None = None
    remarks: str | None = None
    formulation_checked_by: str | None = None
    formulation_checked_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_by: str
    created_date: datetime


class UpdateProtocolHeaderRequest(BaseModel):
    """All fields optional — only the ones provided are updated. Draft-only."""
    condition: str | None = None
    duration_months: int | None = None
    study_type: str | None = None
    testing_frequency: str | None = None
    label_claim: str | None = None
    mfg_date: datetime | None = None
    batch_number: str | None = None
    placebo_batch_number: str | None = None
    batch_size: str | None = None
    stability_initiation_date: datetime | None = None
    no_of_samples_time_points: str | None = None
    fill_volume: str | None = None
    api_name: str | None = None
    api_batch_no: str | None = None
    api_source: str | None = None
    primary_pack: str | None = None
    secondary_pack: str | None = None
    headspace: str | None = None
    orientation: str | None = None
    remarks: str | None = None


class CancelProtocolRequest(BaseModel):
    reason: str | None = None


class CreateReservePullRequest(BaseModel):
    matrix_cell_id: int
    batch_number: str
    comments: str | None = None


class SetReportSignatureNamesRequest(BaseModel):
    checked_by_name: str | None = None
    reviewed_by_name: str | None = None


class MatrixCellInput(BaseModel):
    id: int | None = None
    condition: str
    is_reserve: bool = False
    time_point_days: int | None = None
    is_scheduled: bool = False
    notes: str | None = None


class SetMatrixCellsRequest(BaseModel):
    cells: list[MatrixCellInput]


class StabilityMatrixCellResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    protocol_id: int
    condition: str
    is_reserve: bool
    time_point_days: int | None = None
    time_point_month_label: str | None = None
    is_scheduled: bool
    notes: str | None = None


class EsignActionRequest(BaseModel):
    password: str
    comments: str | None = None


class GenerateScheduleRequest(BaseModel):
    batch_numbers: list[str]


class StabilitySampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    protocol_id: int
    matrix_cell_id: int
    condition: str
    time_point_days: int | None = None
    time_point_months: int
    batch_number: str
    scheduled_date: datetime | None = None
    pull_date: datetime | None = None
    sample_id: int | None = None
    comments: str | None = None
    status: str


class StabilityReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    protocol_id: int
    report_number: str
    status: str
    product_name: str | None = None
    composition_label: str | None = None
    manufactured_at: str | None = None
    stability_study_type: str | None = None
    batch_no: str | None = None
    stability_condition: str | None = None
    batch_size: str | None = None
    date_of_commencement: datetime | None = None
    manufacturing_date: datetime | None = None
    stability_protocol_no: str | None = None
    expiry_date: datetime | None = None
    api_source: str | None = None
    api_batch_number: str | None = None
    packing: str | None = None
    results_data: list[dict] = []
    remarks: str | None = None
    prepared_by: str | None = None
    prepared_at: datetime | None = None
    checked_by_name: str | None = None
    reviewed_by_name: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    generated_by: str | None = None
    generated_at: datetime | None = None
