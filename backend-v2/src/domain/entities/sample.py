"""Sample domain entity — the core Sample Manager workflow aggregate."""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base_entity import BaseEntity


@dataclass
class _TestProjection:
    """Read-only projection of Test details, embedded in SampleResult for API responses."""

    id: int
    code: str
    name: str
    type: str
    unit: str | None
    status: str
    method_no: str | None = None
    category: str | None = None
    technique: str | None = None


@dataclass
class SampleResult:
    """Value object: a single test result on a Sample."""

    id: int = 0
    sample_id: int = 0
    test_id: int = 0
    min_limit: float | None = None
    max_limit: float | None = None
    expected_result: str | None = None
    result_value: float | None = None
    result_text: str | None = None
    status: str = "Pending"  # Pending, Submitted, Approved
    analyst_id: int | None = None
    submitted_at: datetime | None = None
    supervisor_id: int | None = None
    reviewed_at: datetime | None = None
    is_oos: bool = False
    oos_investigation_id: int | None = None
    test_type: str = "Quantitative"
    # Denormalized test details for API projection (avoids extra queries)
    test_code: str | None = None
    test_name: str | None = None
    test_unit: str | None = None
    test_status: str | None = None
    test_method_no: str | None = None
    test_category: str | None = None
    test_technique: str | None = None

    @property
    def test(self) -> "_TestProjection | None":
        """Lightweight projection for API serialization (avoids extra queries)."""
        if self.test_code is None:
            return None
        return _TestProjection(
            id=self.test_id, code=self.test_code, name=self.test_name or "",
            type=self.test_type, unit=self.test_unit, status=self.test_status or "Active",
            method_no=self.test_method_no, category=self.test_category, technique=self.test_technique,
        )

    def evaluate_oos(self) -> bool:
        """
        Core domain rule: determine if this result is Out-of-Specification.
        Quantitative: value must fall within [min_limit, max_limit].
        Qualitative: text must match expected_result (case-insensitive).
        """
        if self.test_type == "Quantitative":
            if self.result_value is None:
                return False
            if self.min_limit is not None and self.result_value < self.min_limit:
                return True
            if self.max_limit is not None and self.result_value > self.max_limit:
                return True
            return False
        # Qualitative
        if self.expected_result and self.result_text:
            return self.result_text.strip().lower() != self.expected_result.strip().lower()
        return False


@dataclass
class Sample(BaseEntity):
    """
    Sample aggregate root — drives the entire QC lifecycle:
    Logged -> Received -> (Testing) -> Under Review -> OOS Investigation? -> Approved/Rejected

    Business Rules:
    - sample_code is auto-generated: SMP-YYYYMMDD-XXXX (unique, sequential per day).
    - Cannot be logged without an Active Specification for the Product.
    - Cannot transition to Under Review until all results are Submitted/Approved.
    - Any OOS result forces status to 'OOS Investigation'.
    - Release requires QA role + E-Signature; produces an immutable COA snapshot.
    """

    sample_code: str = field(default="")
    product_id: int = field(default=0)
    batch_number: str = field(default="")
    quantity_received: float = field(default=0.0)
    unit: str = field(default="")
    sample_type: str | None = field(default=None)
    priority: str = field(default="Normal")
    status: str = field(default="Logged")

    sap_inspection_lot: str | None = field(default=None)
    sap_material: str | None = field(default=None)
    sap_plant: str | None = field(default=None)
    sap_vendor: str | None = field(default=None)
    sap_vendor_batch: str | None = field(default=None)
    manufacturing_date: datetime | None = field(default=None)
    expiry_date: datetime | None = field(default=None)
    sap_ud_posted: bool = field(default=False)
    sap_ud_code: str | None = field(default=None)
    sap_ud_posted_at: datetime | None = field(default=None)

    logged_by: str | None = field(default=None)
    logged_at: datetime | None = field(default=None)
    received_by: str | None = field(default=None)
    received_at: datetime | None = field(default=None)
    approved_by: str | None = field(default=None)
    approved_at: datetime | None = field(default=None)
    coa_released_by: str | None = field(default=None)
    coa_released_at: datetime | None = field(default=None)
    coa_data: dict | None = field(default=None)

    results: list[SampleResult] = field(default_factory=list)

    def receive(self, receiver: str, when: datetime) -> None:
        self.status = "Received"
        self.received_by = receiver
        self.received_at = when
        self.mark_modified(receiver)

    def all_results_finalized(self) -> bool:
        return all(r.status in ("Submitted", "Approved") for r in self.results)

    def has_oos(self) -> bool:
        return any(r.is_oos for r in self.results)

    def refresh_status_after_result_submission(self) -> None:
        """Domain rule: recompute Sample status based on current result set."""
        if self.has_oos():
            self.status = "OOS Investigation"
        elif self.all_results_finalized():
            self.status = "Under Review"

    def release(self, verdict: str, qa_user: str, when: datetime, comments: str | None, snapshot: dict) -> None:
        if verdict not in ("Approved", "Rejected"):
            raise ValueError("Verdict must be Approved or Rejected")
        self.status = verdict
        self.approved_by = qa_user
        self.approved_at = when
        self.coa_released_by = qa_user
        self.coa_released_at = when
        self.coa_data = snapshot
        self.mark_modified(qa_user)
