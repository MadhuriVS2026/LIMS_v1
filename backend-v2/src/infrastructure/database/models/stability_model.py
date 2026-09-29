"""SQLAlchemy ORM models for Stability Management."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class StabilityProtocolModel(BaseModel):
    __tablename__ = "stability_protocols"

    protocol_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    condition: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)
    study_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    testing_frequency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Draft")

    # Header fields from the real Stability Protocol Format document
    label_claim: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfg_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    placebo_batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stability_initiation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    no_of_samples_time_points: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fill_volume: Mapped[str | None] = mapped_column(String(100), nullable=True)
    api_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_batch_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    api_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_pack: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secondary_pack: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headspace: Mapped[str | None] = mapped_column(String(100), nullable=True)
    orientation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    remarks: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Two-step approval workflow
    formulation_checked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    formulation_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    product = relationship("ProductModel")


class StabilityMatrixCellModel(BaseModel):
    __tablename__ = "stability_matrix_cells"
    __table_args__ = (
        UniqueConstraint(
            "protocol_id", "condition", "time_point_days", "is_reserve",
            name="uq_stability_matrix_cell_natural_key",
        ),
    )

    protocol_id: Mapped[int] = mapped_column(Integer, ForeignKey("stability_protocols.id"), nullable=False)
    condition: Mapped[str] = mapped_column(String(100), nullable=False)
    is_reserve: Mapped[bool] = mapped_column(Boolean, default=False)
    time_point_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_point_month_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class StabilitySampleModel(BaseModel):
    __tablename__ = "stability_samples"

    protocol_id: Mapped[int] = mapped_column(Integer, ForeignKey("stability_protocols.id"), nullable=False)
    matrix_cell_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stability_matrix_cells.id"), nullable=False
    )
    condition: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    time_point_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_point_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pull_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sample_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("samples.id"), nullable=True)
    comments: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class StabilityReportModel(BaseModel):
    __tablename__ = "stability_reports"

    protocol_id: Mapped[int] = mapped_column(Integer, ForeignKey("stability_protocols.id"), nullable=False)
    report_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="Draft")

    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    composition_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufactured_at: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stability_study_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stability_condition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_of_commencement: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    manufacturing_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stability_protocol_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    api_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    packing: Mapped[str | None] = mapped_column(String(255), nullable=True)

    results_data: Mapped[list | None] = mapped_column(JSON, nullable=True)
    remarks: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    prepared_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    checked_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    generated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
