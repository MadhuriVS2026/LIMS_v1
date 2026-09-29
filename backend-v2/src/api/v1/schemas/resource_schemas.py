"""Pydantic schemas for Resource Manager endpoints (Instruments, Columns, Standards, etc.)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateInstrumentRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    code: str
    name: str
    category: str | None = None
    manufacturer: str | None = None
    model_number: str | None = None
    serial_number: str | None = None
    location: str | None = None
    calibration_frequency_days: int | None = None


class InstrumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: int
    code: str
    name: str
    category: str | None = None
    manufacturer: str | None = None
    model_number: str | None = None
    serial_number: str | None = None
    location: str | None = None
    status: str
    calibration_due_date: datetime | None = None
    calibration_frequency_days: int | None = None
    last_calibrated_at: datetime | None = None
    last_calibrated_by: str | None = None
    qualification_status: str | None = None


class RecordCalibrationRequest(BaseModel):
    calibration_date: datetime
    next_due_date: datetime | None = None
    result: str
    certificate_no: str | None = None
    comments: str | None = None


class CreateColumnRequest(BaseModel):
    code: str
    name: str
    type: str | None = None
    manufacturer: str | None = None
    dimensions: str | None = None
    serial_number: str | None = None
    instrument_id: int | None = None
    max_injections: int | None = None


class ColumnResponse(BaseModel):
    id: int
    code: str
    name: str
    type: str | None = None
    manufacturer: str | None = None
    dimensions: str | None = None
    serial_number: str | None = None
    instrument_id: int | None = None
    max_injections: int | None = None
    current_injections: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class CreateReferenceStandardRequest(BaseModel):
    code: str
    name: str
    lot_number: str | None = None
    potency: float | None = None
    manufacturer: str | None = None
    category: str | None = None
    storage_condition: str | None = None
    quantity_received: float | None = None
    unit: str | None = None
    received_date: datetime | None = None
    expiry_date: datetime | None = None


class ReferenceStandardResponse(BaseModel):
    id: int
    code: str
    name: str
    lot_number: str | None = None
    potency: float | None = None
    manufacturer: str | None = None
    category: str | None = None
    quantity_received: float | None = None
    quantity_remaining: float | None = None
    unit: str | None = None
    expiry_date: datetime | None = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class CreateChemicalRequest(BaseModel):
    code: str
    name: str
    grade: str | None = None
    manufacturer: str | None = None
    lot_number: str | None = None
    cas_number: str | None = None
    quantity_received: float | None = None
    unit: str | None = None
    storage_condition: str | None = None
    received_date: datetime | None = None
    expiry_date: datetime | None = None


class ChemicalResponse(BaseModel):
    id: int
    code: str
    name: str
    grade: str | None = None
    manufacturer: str | None = None
    lot_number: str | None = None
    cas_number: str | None = None
    quantity_received: float | None = None
    quantity_remaining: float | None = None
    unit: str | None = None
    expiry_date: datetime | None = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class CreateVolumetricSolutionRequest(BaseModel):
    code: str
    name: str
    concentration: str | None = None
    prepared_date: datetime | None = None
    expiry_date: datetime | None = None
    standardization_factor: float | None = None


class VolumetricSolutionResponse(BaseModel):
    id: int
    code: str
    name: str
    concentration: str | None = None
    prepared_by: str | None = None
    prepared_date: datetime | None = None
    expiry_date: datetime | None = None
    standardization_factor: float | None = None
    status: str

    model_config = ConfigDict(from_attributes=True)



