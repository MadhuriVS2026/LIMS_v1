"""SQLAlchemy ORM models for the MRN — Material Requisition & Consumption module."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class MRNMaterialLotModel(BaseModel):
    __tablename__ = "mrn_material_lots"
    __table_args__ = (UniqueConstraint("grn_document_no", "grn_item_no", name="uq_mrn_lot_natural_key"),)

    grn_document_no: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    grn_item_no: Mapped[str] = mapped_column(String(20), nullable=False)
    material_code: Mapped[str] = mapped_column(String(50), nullable=False)
    material_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plant: Mapped[str] = mapped_column(String(20), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    original_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consumed_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grn_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pulled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MaterialRequisitionModel(BaseModel):
    __tablename__ = "material_requisitions"

    mrn_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="Draft")
    submitted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    posted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    line_items = relationship(
        "MRNLineItemModel", back_populates="requisition", cascade="all, delete-orphan"
    )


class MRNLineItemModel(BaseModel):
    __tablename__ = "mrn_line_items"

    mrn_id: Mapped[int] = mapped_column(Integer, ForeignKey("material_requisitions.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    lot_id: Mapped[int] = mapped_column(Integer, ForeignKey("mrn_material_lots.id"), nullable=False)
    requested_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    project_code: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="Draft")
    consumption_posting_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("consumption_postings.id", use_alter=True, name="fk_mrn_line_item_posting"),
        nullable=True,
    )

    requisition = relationship("MaterialRequisitionModel", back_populates="line_items")
    lot = relationship("MRNMaterialLotModel")


class ConsumptionPostingModel(BaseModel):
    __tablename__ = "consumption_postings"

    line_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("mrn_line_items.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    sap_doc_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
