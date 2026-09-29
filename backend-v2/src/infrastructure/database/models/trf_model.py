"""SQLAlchemy ORM models for the TRF — Test Request Form module."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class TestRequestFormModel(BaseModel):
    __tablename__ = "test_request_forms"

    trf_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    ar_number: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)

    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    label_claim: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stage_of_sample: Mapped[str | None] = mapped_column(String(100), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    storage_condition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_period: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pack_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufactured_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfg_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_or_retest_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Reserved hook for a future Stability -> TRF auto-generation integration.
    source: Mapped[str] = mapped_column(String(20), default="Manual")
    stability_pull_ref: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="Draft")

    initiated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    initiated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fdgl_approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fdgl_approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    adgl_accepted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    adgl_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    analyst_accepted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    analyst_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    results_submitted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    results_submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    released_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    referred_back_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referred_back_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    referred_back_comments: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_comments: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    atr_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    test_lines = relationship(
        "TRFTestLineModel", back_populates="trf", cascade="all, delete-orphan"
    )
    product = relationship("ProductModel")


class TRFTestLineModel(BaseModel):
    __tablename__ = "trf_test_lines"

    trf_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_request_forms.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("tests.id"), nullable=False)
    specification: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_data_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    trf = relationship("TestRequestFormModel", back_populates="test_lines")
    test = relationship("TestModel")
