"""SQLAlchemy ORM models for Resource Manager: Column, ReferenceStandard, Chemical, Volumetric."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
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
