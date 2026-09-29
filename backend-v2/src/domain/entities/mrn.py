"""
MRN — Material Requisition & Consumption domain entities.

Models the "last mile" of R&D plant material handling: a `MRNMaterialLot` that
has completed GRN in SAP, a `MaterialRequisition` (MRN) header raised against
one or more lots via `MRNLineItem`s, and the `ConsumptionPosting` record of
each line item's outbound SAP consumption posting attempt.

Business Rules (see design.md / requirements.md for full rationale):
- `MRNMaterialLot.status` and `available_quantity` are always derived from
  quantities, never independently settable (Requirement 4.1).
- A line item's requested quantity can never exceed its lot's available
  quantity at the time it is added (Requirement 2.2, 2.3).
- An MRN's line items can only be mutated while the MRN is in `Draft` status
  (Requirement 2.4, 2.5, 2.7).
- Submitting an MRN requires at least one line item (Requirement 2.6).
"""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base_entity import BaseEntity


@dataclass
class MRNMaterialLot(BaseEntity):
    """
    A material lot that has completed GRN (Goods Receipt Note) in SAP and is
    available (in whole or in part) for requisition at the R&D plant.

    Natural key (for SAP pull upsert): (grn_document_no, grn_item_no).
    `status` and `available_quantity` are derived properties — never set
    directly — computed from `original_quantity` and `consumed_quantity`.
    """

    grn_document_no: str = field(default="")
    grn_item_no: str = field(default="")
    material_code: str = field(default="")
    material_description: str | None = field(default=None)
    batch_number: str | None = field(default=None)
    plant: str = field(default="")
    unit: str = field(default="")
    original_quantity: float = field(default=0.0)
    consumed_quantity: float = field(default=0.0)
    grn_date: datetime | None = field(default=None)
    pulled_at: datetime | None = field(default=None)

    @property
    def available_quantity(self) -> float:
        return self.original_quantity - self.consumed_quantity

    @property
    def status(self) -> str:
        """Derived: Available / PartiallyConsumed / Exhausted. Never set directly."""
        if self.consumed_quantity <= 0:
            return "Available"
        if self.consumed_quantity >= self.original_quantity:
            return "Exhausted"
        return "PartiallyConsumed"

    def can_fulfill(self, requested_quantity: float) -> bool:
        """Requirement 2.2/2.3: a line item's requested quantity must not exceed availability."""
        return 0 < requested_quantity <= self.available_quantity

    def apply_consumption(self, quantity: float) -> None:
        """
        Increment consumed_quantity by a posted line item's quantity.
        Requirement 4.2: recompute the (derived) status immediately.
        Raises ValueError if this would over-consume the lot (Requirement 4.3, 9.8).
        """
        if quantity <= 0:
            raise ValueError("Consumption quantity must be positive")
        if quantity > self.available_quantity:
            raise ValueError(
                f"Cannot consume {quantity} from lot {self.grn_document_no}/{self.grn_item_no}: "
                f"only {self.available_quantity} available"
            )
        self.consumed_quantity += quantity


@dataclass
class ConsumptionPosting(BaseEntity):
    """
    Record of one outbound SAP consumption-posting attempt for a single
    `MRNLineItem`. Idempotency key is derived once and reused across retries
    so a successful posting is never re-submitted to SAP (Requirement 3.7).
    """

    line_item_id: int = field(default=0)
    idempotency_key: str = field(default="")
    status: str = field(default="Pending")  # Pending, Success, Failed
    sap_doc_no: str | None = field(default=None)
    error_message: str | None = field(default=None)
    posted_at: datetime | None = field(default=None)

    def mark_success(self, sap_doc_no: str, when: datetime) -> None:
        self.status = "Success"
        self.sap_doc_no = sap_doc_no
        self.error_message = None
        self.posted_at = when

    def mark_failed(self, error_message: str, when: datetime) -> None:
        self.status = "Failed"
        self.error_message = error_message
        self.posted_at = when


@dataclass
class MRNLineItem(BaseEntity):
    """
    One requested-quantity line on a `MaterialRequisition`, sourced from a
    single `MRNMaterialLot`. Status mirrors the outcome of its (at most one
    active) `ConsumptionPosting` record.
    """

    mrn_id: int = field(default=0)
    line_no: int = field(default=0)
    lot_id: int = field(default=0)
    requested_quantity: float = field(default=0.0)
    project_code: str = field(default="")
    status: str = field(default="Draft")  # Draft, Requisitioned, ConsumptionPosted, PostingFailed
    consumption_posting_id: int | None = field(default=None)

    # Denormalized lot fields for API projection (avoids extra queries)
    lot_material_code: str | None = field(default=None)
    lot_batch_number: str | None = field(default=None)

    def lock_for_submission(self) -> None:
        self.status = "Requisitioned"

    def mark_posted(self, posting_id: int) -> None:
        self.status = "ConsumptionPosted"
        self.consumption_posting_id = posting_id

    def mark_posting_failed(self, posting_id: int) -> None:
        self.status = "PostingFailed"
        self.consumption_posting_id = posting_id


@dataclass
class MaterialRequisition(BaseEntity):
    """
    MRN aggregate root — drives the requisition lifecycle:
    Draft -> Submitted -> PostingInProgress -> Posted / PartiallyPosted / PostingFailed
    (PartiallyPosted/PostingFailed can be reprocessed back toward Posted).

    Business Rules:
    - mrn_number is auto-generated (MRNNumberGenerator), unique, sequential per day.
    - Line items can only be added/removed while status == 'Draft'.
    - Submission requires at least one line item (Requirement 2.6).
    - Header status after posting is derived from the combined line outcome
      (Requirement 3.6): Posted (all succeeded), PartiallyPosted (mixed),
      PostingFailed (all failed).
    """

    mrn_number: str = field(default="")
    status: str = field(default="Draft")
    submitted_by: str | None = field(default=None)
    submitted_at: datetime | None = field(default=None)
    posted_by: str | None = field(default=None)
    posted_at: datetime | None = field(default=None)

    line_items: list[MRNLineItem] = field(default_factory=list)

    def can_mutate_line_items(self) -> bool:
        return self.status == "Draft"

    def can_submit(self) -> bool:
        return self.status == "Draft" and len(self.line_items) > 0

    def submit(self, submitted_by: str, when: datetime) -> None:
        if not self.can_submit():
            raise ValueError("MRN must be in Draft status with at least one line item to submit")
        self.status = "Submitted"
        self.submitted_by = submitted_by
        self.submitted_at = when
        for item in self.line_items:
            item.lock_for_submission()
        self.mark_modified(submitted_by)

    def can_approve_and_post(self) -> bool:
        return self.status == "Submitted"

    def can_reprocess(self) -> bool:
        return self.status in ("PartiallyPosted", "PostingFailed")

    def begin_posting(self) -> None:
        self.status = "PostingInProgress"

    def recompute_status_after_posting(self, actor: str, when: datetime) -> None:
        """Requirement 3.6: derive header status from the combined line outcome."""
        statuses = {item.status for item in self.line_items}
        if statuses == {"ConsumptionPosted"}:
            self.status = "Posted"
            self.posted_by = actor
            self.posted_at = when
        elif "ConsumptionPosted" in statuses and "PostingFailed" in statuses:
            self.status = "PartiallyPosted"
        else:
            self.status = "PostingFailed"
        self.mark_modified(actor)
