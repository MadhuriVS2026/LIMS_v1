"""SQLAlchemy ORM models for Resource Manager: Column, ReferenceStandard, Chemical, Volumetric."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base_model import BaseModel


class ColumnMasterModel(BaseModel):
    __tablename__ = "columns"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dimensions: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instrument_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("instruments.id"), nullable=True)
    max_injections: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_injections: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="Active")
    received_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retirement_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReferenceStandardModel(BaseModel):
    __tablename__ = "reference_standards"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    potency: Mapped[float | None] = mapped_column(Float, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    storage_condition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity_received: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity_remaining: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    received_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active")


class ChemicalReagentModel(BaseModel):
    __tablename__ = "chemicals_reagents"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cas_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quantity_received: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity_remaining: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    storage_condition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    opened_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active")


class ProjectMasterModel(BaseModel):
    __tablename__ = "project_master"

    project_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project_code_academic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bd_code_sap: Mapped[str | None] = mapped_column(String(100), nullable=True)
    group_lead: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comments: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active")
    requested_person: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remarks: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class ARDExpTemplateModel(BaseModel):
    __tablename__ = "ard_exp_templates"

    template_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    comments: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    primary_department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    secondary_department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    module: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #  Source form identity (e.g. "ADS-01-00") and its document number
    #  (e.g. "ADS/001/00") preserved from the originating sheet.
    template_code: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    document_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    #  Complete, non-standardised sheet content as extracted from the source
    #  document: header fields + every section/table verbatim, stored as JSON text
    #  so the full form can be reproduced without flattening or summarising it.
    content: Mapped[str | None] = mapped_column(Text, nullable=True)


class VolumetricSolutionModel(BaseModel):
    __tablename__ = "volumetric_solutions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    concentration: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prepared_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prepared_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    standardization_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    standardized_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    standardized_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active")
