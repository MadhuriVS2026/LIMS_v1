"""SQLAlchemy ORM models for Instrument & InstrumentCalibration."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class InstrumentModel(BaseModel):
    __tablename__ = "instruments"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active")
    calibration_due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    calibration_frequency_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_calibrated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_calibrated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qualification_status: Mapped[str | None] = mapped_column(String(50), nullable=True)


class InstrumentCalibrationModel(BaseModel):
    __tablename__ = "instrument_calibrations"

    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instruments.id"), nullable=False)
    calibration_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    next_due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    performed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[str | None] = mapped_column(String(20), nullable=True)
    certificate_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comments: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    instrument = relationship("InstrumentModel")
