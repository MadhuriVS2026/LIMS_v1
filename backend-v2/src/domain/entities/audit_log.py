"""Audit Log domain entity — 21 CFR Part 11 compliance trail."""
from dataclasses import dataclass, field
from datetime import datetime, timezone

# NOTE: SAPReceivedLot is defined at the bottom of this module (keeps all
# SAP-adjacent traceability entities together with AuditLog/SAPIntegrationLog).


@dataclass
class AuditLog:
    """
    Immutable audit trail entry.
    Every CREATE/UPDATE/APPROVE/SIGN/LOGIN action in the system writes one of these.
    """

    id: int = field(default=0)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: int | None = field(default=None)
    username: str = field(default="")
    action: str = field(default="")
    table_name: str = field(default="")
    record_id: int | None = field(default=None)
    old_values: dict | None = field(default=None)
    new_values: dict | None = field(default=None)
    comments: str | None = field(default=None)


@dataclass
class SAPIntegrationLog:
    """Tracks every inbound/outbound SAP RFC transaction for traceability."""

    id: int = field(default=0)
    transaction_type: str = field(default="")  # BATCH_READ, USAGE_DECISION, etc.
    direction: str = field(default="")  # INBOUND, OUTBOUND
    sample_id: int | None = field(default=None)
    sap_inspection_lot: str | None = field(default=None)
    request_payload: dict | None = field(default=None)
    response_payload: dict | None = field(default=None)
    status: str = field(default="Pending")  # Pending, Success, Failed
    error_message: str | None = field(default=None)
    created_by: str | None = field(default=None)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = field(default=None)


@dataclass
class SAPReceivedLot:
    """
    An inspection lot pushed inbound from SAP CPI, stored as-is for the
    analyst to review and pull into a Sample when logging it (read-only
    reference data — never written back to SAP from this record).
    """

    id: int = field(default=0)
    inspection_lot: str = field(default="")
    plant: str | None = field(default=None)
    material_number: str | None = field(default=None)
    material_desc: str | None = field(default=None)
    batch_number: str | None = field(default=None)
    storage_location: str | None = field(default=None)
    vendor_code: str | None = field(default=None)
    vendor_name: str | None = field(default=None)
    vendor_batch: str | None = field(default=None)
    lot_quantity: str | None = field(default=None)
    lot_unit: str | None = field(default=None)
    manufacturing_date: str | None = field(default=None)
    expiry_date: str | None = field(default=None)
    characteristics: list[dict] = field(default_factory=list)
    raw_payload: dict | None = field(default=None)
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consumed_by_sample_id: int | None = field(default=None)
