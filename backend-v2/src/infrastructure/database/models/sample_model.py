"""SQLAlchemy ORM models for Sample & SampleResult."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class SampleModel(BaseModel):
    __tablename__ = "samples"

    sample_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_received: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    sample_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="Normal")
    status: Mapped[str] = mapped_column(String(50), default="Logged")

    sap_inspection_lot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sap_material: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sap_plant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sap_vendor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sap_vendor_batch: Mapped[str | None] = mapped_column(String(50), nullable=True)
    manufacturing_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sap_ud_posted: Mapped[bool] = mapped_column(Boolean, default=False)
    sap_ud_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sap_ud_posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    logged_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    received_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    coa_released_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    coa_released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    coa_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    product = relationship("ProductModel")
    results = relationship("SampleResultModel", back_populates="sample")


class SampleResultModel(BaseModel):
    __tablename__ = "sample_results"

    sample_id: Mapped[int] = mapped_column(Integer, ForeignKey("samples.id"), nullable=False)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("tests.id"), nullable=False)
    min_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_result: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Pending")
    analyst_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    supervisor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_oos: Mapped[bool] = mapped_column(Boolean, default=False)
    oos_investigation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("oos_investigations.id"), nullable=True
    )

    sample = relationship("SampleModel", back_populates="results")
    test = relationship("TestModel")
