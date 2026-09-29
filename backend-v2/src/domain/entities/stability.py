"""
Stability Management domain entities.

Models the full Stability workflow per the real "Stability Protocol Format" and
"Stability Report Format" documents: a `StabilityProtocol` header with a Loading
Matrix (`StabilityMatrixCell` rows: condition x time-point-in-days), scheduled
time-point pulls (`StabilitySample`, whose status is DERIVED from a linked Sample
Manager `Sample`'s status rather than independently settable), and an assembled,
signed-off `StabilityReport`.

Business Rules (see design.md / requirements.md for full rationale):
- `StabilityMatrixCell` rows can only be added/edited while the protocol is `Draft`
  (Requirement 1.4), and are upserted by the natural key
  `(protocol_id, condition, time_point_days, is_reserve)` (Requirement 1.3).
- The two-step approval (`Draft -> FormulationChecked -> Active`) both use the
  existing Supervisor role, each independently e-signed (Requirement 3).
- `StabilitySample.status` is always derived from the linked Sample's status once
  `sample_id` is populated, never independently set (Requirement 5.4).
- A `StabilityReport` is immutable once `Prepared` or `Approved`; regenerating
  creates a new `Draft` record instead of mutating a signed one (Requirement 6.3).
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.domain.entities.base_entity import BaseEntity

# Standard day-based time points from the real Stability Protocol Format document.
STANDARD_TIME_POINT_DAYS: list[int] = [15, 30, 60, 90, 180, 270, 365, 545, 730, 1095]

# Suggested (not enforced) condition values from the real document.
SUGGESTED_CONDITIONS: list[str] = [
    "40°C±2°C/75%±5%RH",
    "30°C±2°C/65%±5%RH",
    "30°C±2°C/75%±5%RH",
    "25°C±2°C/60%±5%RH",
    "5°C±3°C",
    "Other",
]

# Sample Manager statuses that map onto each derived StabilitySample status.
_PULLED_SAMPLE_STATUSES = {"Logged", "Received"}
_COMPLETED_SAMPLE_STATUSES = {"Approved", "Rejected"}


def time_point_month_label(time_point_days: int | None) -> str | None:
    """
    Requirement 1.5: derive a human-readable month label for a day-based time
    point (e.g. day 90 -> "3M"), for display/reporting alongside the exact day
    value. Uses a 30-day month approximation, rounding to the nearest month;
    day 15 has no clean month label and returns None.
    """
    if time_point_days is None:
        return None
    months = round(time_point_days / 30)
    if months <= 0:
        return None
    return f"{months}M"


@dataclass
class StabilityMatrixCell(BaseEntity):
    """
    One cell of a StabilityProtocol's Loading Matrix: a specific condition +
    time point (in days), optionally scheduled, with an optional per-cell note.
    `is_reserve` marks the "Reserve" column, which has no time_point_days and is
    never included in generated schedules (Requirement 4.4).

    Natural key (for upsert): (protocol_id, condition, time_point_days, is_reserve).
    """

    protocol_id: int = field(default=0)
    condition: str = field(default="")
    is_reserve: bool = field(default=False)
    time_point_days: int | None = field(default=None)
    time_point_month_label: str | None = field(default=None)
    is_scheduled: bool = field(default=False)
    notes: str | None = field(default=None)


@dataclass
class StabilityProtocol(BaseEntity):
    """Stability study protocol master (Long Term / Accelerated / Intermediate)."""

    protocol_code: str = field(default="")
    product_id: int = field(default=0)
    condition: str = field(default="")  # e.g. 25°C/60%RH — coarse summary field
    duration_months: int = field(default=0)  # coarse summary field, not scheduling source of truth
    study_type: str | None = field(default=None)
    testing_frequency: str | None = field(default=None)  # coarse summary field (csv of months)
    status: str = field(default="Draft")  # Draft, FormulationChecked, Active, Completed, Cancelled

    # Header fields from the real Stability Protocol Format document (Requirement 2.1)
    label_claim: str | None = field(default=None)
    mfg_date: datetime | None = field(default=None)
    batch_number: str | None = field(default=None)
    placebo_batch_number: str | None = field(default=None)
    batch_size: str | None = field(default=None)
    stability_initiation_date: datetime | None = field(default=None)
    no_of_samples_time_points: str | None = field(default=None)
    fill_volume: str | None = field(default=None)
    api_name: str | None = field(default=None)
    api_batch_no: str | None = field(default=None)
    api_source: str | None = field(default=None)
    primary_pack: str | None = field(default=None)
    secondary_pack: str | None = field(default=None)
    headspace: str | None = field(default=None)
    orientation: str | None = field(default=None)  # Upright | Inverted
    remarks: str | None = field(default=None)

    # Two-step approval workflow (Requirement 3)
    formulation_checked_by: str | None = field(default=None)
    formulation_checked_at: datetime | None = field(default=None)
    approved_by: str | None = field(default=None)  # Analytical check (2nd sign)
    approved_at: datetime | None = field(default=None)

    def can_edit_matrix(self) -> bool:
        """Requirement 1.4: Loading Matrix can only be mutated while Draft."""
        return self.status == "Draft"

    def can_check_formulation(self) -> bool:
        """Requirement 3.3: Formulation Check requires Draft status."""
        return self.status == "Draft"

    def check_formulation(self, actor: str, when: datetime) -> None:
        self.formulation_checked_by = actor
        self.formulation_checked_at = when
        self.status = "FormulationChecked"
        self.mark_modified(actor)

    def can_check_analytical(self) -> bool:
        """Requirement 3.5: Analytical Check requires FormulationChecked status."""
        return self.status == "FormulationChecked"

    def check_analytical(self, actor: str, when: datetime) -> None:
        self.approved_by = actor
        self.approved_at = when
        self.status = "Active"
        self.mark_modified(actor)

    def can_generate_schedule(self) -> bool:
        """Requirement 4.2: schedule generation requires an Active protocol."""
        return self.status == "Active"

    def can_edit_header(self) -> bool:
        """Header fields (product, condition, batch, pack details, etc.) can
        only be edited while the protocol is still Draft — once Formulation
        Check has happened the header is considered locked."""
        return self.status == "Draft"

    def can_complete(self) -> bool:
        """A study can be marked Completed once it is Active (i.e. past both
        approval checks) — this is a manual close-out action, not tied to any
        specific time point, since a study may be closed early or after its
        full duration."""
        return self.status == "Active"

    def complete(self, actor: str, when: datetime) -> None:
        self.status = "Completed"
        self.mark_modified(actor)

    def can_cancel(self) -> bool:
        """A study can be cancelled from any state except a terminal one."""
        return self.status not in ("Completed", "Cancelled")

    def cancel(self, actor: str, when: datetime) -> None:
        self.status = "Cancelled"
        self.mark_modified(actor)


@dataclass
class StabilitySample(BaseEntity):
    """
    A scheduled time-point pull for a StabilityProtocol, sourced from one
    `StabilityMatrixCell`. `status` is always DERIVED from the linked Sample
    Manager Sample's status once `sample_id` is populated (Requirement 5.4) —
    it is intentionally not a field that callers set directly; use
    `compute_status()` to determine the current status from the linked Sample.
    """

    protocol_id: int = field(default=0)
    matrix_cell_id: int = field(default=0)
    condition: str = field(default="")  # denormalized from the matrix cell
    time_point_days: int | None = field(default=None)  # denormalized from the matrix cell
    time_point_months: int = field(default=0)  # legacy field, kept for backward compatibility
    batch_number: str = field(default="")
    scheduled_date: datetime | None = field(default=None)
    pull_date: datetime | None = field(default=None)
    sample_id: int | None = field(default=None)
    comments: str | None = field(default=None)

    # Denormalized projection of the linked Sample's status, refreshed on every
    # read by the repository/service layer — never set independently by callers.
    linked_sample_status: str | None = field(default=None)

    @staticmethod
    def compute_status(sample_id: int | None, linked_sample_status: str | None) -> str:
        """
        Requirement 5.4: pure derivation rule.
        No linked sample -> Scheduled.
        Linked Sample status Logged/Received -> Pulled.
        Linked Sample status Approved/Rejected -> Completed.
        Any other linked Sample status (results in progress) -> Testing.
        """
        if not sample_id:
            return "Scheduled"
        if linked_sample_status in _COMPLETED_SAMPLE_STATUSES:
            return "Completed"
        if linked_sample_status in _PULLED_SAMPLE_STATUSES:
            return "Pulled"
        return "Testing"

    @property
    def status(self) -> str:
        """Derived, read-only status — see compute_status()."""
        return self.compute_status(self.sample_id, self.linked_sample_status)

    def can_pull(self) -> bool:
        """Requirement 5.2: pull requires the derived status to be Scheduled."""
        return self.status == "Scheduled"

    @staticmethod
    def compute_scheduled_date(
        stability_initiation_date: datetime | None, time_point_days: int | None
    ) -> datetime | None:
        """Requirement 4.3: scheduled_date = initiation_date + time_point_days."""
        if stability_initiation_date is None or time_point_days is None:
            return None
        return stability_initiation_date + timedelta(days=time_point_days)


@dataclass
class StabilityReport(BaseEntity):
    """
    Assembled results document for a StabilityProtocol, per the real
    "Stability Report Format" document. Immutable once Prepared or Approved —
    regenerating creates a new Draft record instead (Requirement 6.3).
    """

    protocol_id: int = field(default=0)
    report_number: str = field(default="")
    status: str = field(default="Draft")  # Draft, Prepared, Approved

    # Header snapshot, captured at generation time from the source protocol.
    product_name: str | None = field(default=None)
    composition_label: str | None = field(default=None)
    manufactured_at: str | None = field(default=None)
    stability_study_type: str | None = field(default=None)
    batch_no: str | None = field(default=None)
    stability_condition: str | None = field(default=None)
    batch_size: str | None = field(default=None)
    date_of_commencement: datetime | None = field(default=None)
    manufacturing_date: datetime | None = field(default=None)
    stability_protocol_no: str | None = field(default=None)
    expiry_date: datetime | None = field(default=None)
    api_source: str | None = field(default=None)
    api_batch_number: str | None = field(default=None)
    packing: str | None = field(default=None)

    # Assembled results table: one row per test, one column per Completed time point.
    # Shape: [{ "test_id": ..., "test_name": ..., "specification": ..., "results": { "Initial": ..., "30 Days": ... } }]
    results_data: list[dict] = field(default_factory=list)
    remarks: str | None = field(default=None)

    # Signature footer
    prepared_by: str | None = field(default=None)  # Analyst e-sign (system-enforced gate)
    prepared_at: datetime | None = field(default=None)
    checked_by_name: str | None = field(default=None)  # free-text, print-only
    reviewed_by_name: str | None = field(default=None)  # free-text, print-only
    approved_by: str | None = field(default=None)  # QA e-sign (system-enforced gate)
    approved_at: datetime | None = field(default=None)

    generated_by: str | None = field(default=None)
    generated_at: datetime | None = field(default=None)

    def is_signed(self) -> bool:
        """Requirement 6.3: Prepared or Approved reports are immutable snapshots."""
        return self.status in ("Prepared", "Approved")

    def can_prepare(self) -> bool:
        """Requirement 7.2: Prepare requires Draft status."""
        return self.status == "Draft"

    def prepare(self, actor: str, when: datetime) -> None:
        self.prepared_by = actor
        self.prepared_at = when
        self.status = "Prepared"
        self.mark_modified(actor)

    def can_approve(self) -> bool:
        """Requirement 7.4: Approve requires Prepared status."""
        return self.status == "Prepared"

    def approve(self, actor: str, when: datetime) -> None:
        self.approved_by = actor
        self.approved_at = when
        self.status = "Approved"
        self.mark_modified(actor)
