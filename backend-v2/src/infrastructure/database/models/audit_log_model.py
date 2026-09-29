"""SQLAlchemy ORM models for AuditLog & SAPIntegrationLog."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base_model import Base


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    comments: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class SAPIntegrationLogModel(Base):
    __tablename__ = "sap_integration_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    sample_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("samples.id"), nullable=True)
    sap_inspection_lot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    request_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SAPReceivedLotModel(Base):
    """Stores inspection lots pushed inbound from SAP CPI, for reference during sample logging."""

    __tablename__ = "sap_received_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    inspection_lot: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    plant: Mapped[str | None] = mapped_column(String(20), nullable=True)
    material_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    material_desc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    storage_location: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vendor_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor_batch: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lot_quantity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lot_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    manufacturing_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    characteristics: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    consumed_by_sample_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("samples.id"), nullable=True
    )
