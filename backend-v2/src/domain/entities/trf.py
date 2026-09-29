"""
TRF — Test Request Form domain entities.

Models the request/approval container in which one or more analytical tests
are raised against a product/batch (`TestRequestForm` aggregate root with
`TRFTestLine` children), routed through a two-gate departmental approval
chain (FDGL -> ADGL), tested by an Analyst, and released with an immutable
ATR snapshot.

Business Rules (see design.md / requirements.md for full rationale):
- Test lines can only be added/removed while status is Draft, ReferredBack,
  or (FDGL only) PendingFDGLApproval (Requirement 1.4).
- Submission requires at least one test line (Requirement 2.2).
- Every gate transition requires its exact documented source status
  (Requirement 3.5, 4.4, State Model).
- Refer-Back and Reject require a non-blank comment (Requirement 3.4).
- ar_number is assigned exactly once, at ADGL Accept (Requirement 4.6).
- submit_results() requires every test line to have a non-blank result
  (Requirement 5.5).
- Result correction is ADGL-and-PendingADGLRelease-only (Requirement 6.2).
- Resubmission after Refer-Back always re-enters at PendingFDGLApproval,
  regardless of which gate referred it back (Requirement 7.2, 7.3).
- The ATR snapshot is captured once, at release, and never mutated again
  (Requirement 8.4).
"""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base_entity import BaseEntity


@dataclass
class TRFTestLine(BaseEntity):
    """
    One test line on a TestRequestForm, referencing the Test Master.
    `specification`/`raw_data_reference`/`result`/`remark` are free text this
    iteration (no structured calculation engine, no file attachments).
    """

    trf_id: int = field(default=0)
    line_no: int = field(default=0)
    test_id: int = field(default=0)
    specification: str | None = field(default=None)
    raw_data_reference: str | None = field(default=None)
    result: str | None = field(default=None)
    remark: str | None = field(default=None)

    # Denormalized test fields for API projection (avoids extra queries)
    test_code: str | None = field(default=None)
    test_name: str | None = field(default=None)

    @property
    def status(self) -> str:
        """Derived display-only status — never independently set."""
        return "Resulted" if self.result and self.result.strip() else "Pending"

    def set_result(self, result: str | None, remark: str | None) -> None:
        self.result = result
        self.remark = remark

    def has_result(self) -> bool:
        return bool(self.result and self.result.strip())


@dataclass
class TestRequestForm(BaseEntity):
    """
    TRF aggregate root — drives the full request/approval/testing/release
    lifecycle:

    Draft -> PendingFDGLApproval -> PendingADGLAcceptance ->
    PendingAnalystAcceptance -> InProgress -> PendingADGLRelease -> Released

    With ReferredBack (from any gate, always resubmits back to
    PendingFDGLApproval) and Rejected (terminal) branches.
    """

    trf_number: str = field(default="")
    ar_number: str | None = field(default=None)

    product_id: int = field(default=0)
    batch_number: str = field(default="")
    label_claim: str | None = field(default=None)
    stage_of_sample: str | None = field(default=None)
    group_name: str | None = field(default=None)
    quantity: str | None = field(default=None)
    storage_condition: str | None = field(default=None)
    storage_period: str | None = field(default=None)
    pack_details: str | None = field(default=None)
    manufactured_by: str | None = field(default=None)
    mfg_date: datetime | None = field(default=None)
    expiry_or_retest_date: datetime | None = field(default=None)
    remark: str | None = field(default=None)

    # Reserved hook for a future Stability -> TRF auto-generation integration.
    # Unwired this iteration (see design.md Decision 7).
    source: str = field(default="Manual")  # "Manual" | "Stability"
    stability_pull_ref: int | None = field(default=None)

    status: str = field(default="Draft")
    # Draft, PendingFDGLApproval, PendingADGLAcceptance, PendingAnalystAcceptance,
    # InProgress, PendingADGLRelease, Released, ReferredBack, Rejected

    initiated_by: str | None = field(default=None)
    initiated_at: datetime | None = field(default=None)
    fdgl_approved_by: str | None = field(default=None)
    fdgl_approved_at: datetime | None = field(default=None)
    adgl_accepted_by: str | None = field(default=None)
    adgl_accepted_at: datetime | None = field(default=None)
    analyst_accepted_by: str | None = field(default=None)
    analyst_accepted_at: datetime | None = field(default=None)
    results_submitted_by: str | None = field(default=None)
    results_submitted_at: datetime | None = field(default=None)
    released_by: str | None = field(default=None)
    released_at: datetime | None = field(default=None)
    referred_back_by: str | None = field(default=None)
    referred_back_at: datetime | None = field(default=None)
    referred_back_comments: str | None = field(default=None)
    rejected_by: str | None = field(default=None)
    rejected_at: datetime | None = field(default=None)
    rejected_comments: str | None = field(default=None)

    test_lines: list[TRFTestLine] = field(default_factory=list)
    atr_snapshot: dict | None = field(default=None)

    # ── Test line mutation ──────────────────────────────────────────

    def can_mutate_lines(self, actor_is_fdgl: bool = False) -> bool:
        """Requirement 1.4: Draft/ReferredBack (Initiator), or PendingFDGLApproval (FDGL only)."""
        if self.status in ("Draft", "ReferredBack"):
            return True
        if self.status == "PendingFDGLApproval" and actor_is_fdgl:
            return True
        return False

    # ── Submission ────────────────────────────────────────────────

    def can_submit(self) -> bool:
        """Requirement 2.2, 2.3: Draft/ReferredBack with >=1 test line."""
        return self.status in ("Draft", "ReferredBack") and len(self.test_lines) > 0

    def submit(self, actor: str, when: datetime) -> None:
        if not self.can_submit():
            raise ValueError(
                "TRF must be in Draft or ReferredBack status with at least one test line to submit"
            )
        self.status = "PendingFDGLApproval"
        self.initiated_by = self.initiated_by or actor
        self.initiated_at = self.initiated_at or when
        self.mark_modified(actor)

    # ── FDGL gate ─────────────────────────────────────────────────

    def can_fdgl_act(self) -> bool:
        return self.status == "PendingFDGLApproval"

    def fdgl_approve(self, actor: str, when: datetime) -> None:
        if not self.can_fdgl_act():
            raise ValueError(f"FDGL approval requires PendingFDGLApproval status (current: {self.status})")
        self.status = "PendingADGLAcceptance"
        self.fdgl_approved_by = actor
        self.fdgl_approved_at = when
        self.mark_modified(actor)

    def fdgl_refer_back(self, actor: str, comments: str, when: datetime) -> None:
        self._refer_back("FDGL approval", actor, comments, when)

    def fdgl_reject(self, actor: str, comments: str, when: datetime) -> None:
        self._reject("FDGL approval", actor, comments, when)

    # ── ADGL acceptance gate ──────────────────────────────────────

    def can_adgl_accept_act(self) -> bool:
        return self.status == "PendingADGLAcceptance"

    def adgl_accept(self, actor: str, ar_number: str, when: datetime) -> None:
        if not self.can_adgl_accept_act():
            raise ValueError(f"ADGL acceptance requires PendingADGLAcceptance status (current: {self.status})")
        self.status = "PendingAnalystAcceptance"
        self.ar_number = ar_number
        self.adgl_accepted_by = actor
        self.adgl_accepted_at = when
        self.mark_modified(actor)

    def adgl_refer_back(self, actor: str, comments: str, when: datetime) -> None:
        self._refer_back("ADGL acceptance", actor, comments, when)

    def adgl_reject(self, actor: str, comments: str, when: datetime) -> None:
        self._reject("ADGL acceptance", actor, comments, when)

    # ── Analyst gate ──────────────────────────────────────────────

    def can_analyst_act(self) -> bool:
        return self.status == "PendingAnalystAcceptance"

    def analyst_accept(self, actor: str, when: datetime) -> None:
        if not self.can_analyst_act():
            raise ValueError(f"Analyst acceptance requires PendingAnalystAcceptance status (current: {self.status})")
        self.status = "InProgress"
        self.analyst_accepted_by = actor
        self.analyst_accepted_at = when
        self.mark_modified(actor)

    def analyst_refer_back(self, actor: str, comments: str, when: datetime) -> None:
        self._refer_back("Analyst acceptance", actor, comments, when)

    def analyst_reject(self, actor: str, comments: str, when: datetime) -> None:
        self._reject("Analyst acceptance", actor, comments, when)

    # ── Result submission ────────────────────────────────────────

    def can_enter_results(self) -> bool:
        return self.status == "InProgress"

    def all_lines_resulted(self) -> bool:
        """Requirement 5.5: every test line must have a non-blank result."""
        return len(self.test_lines) > 0 and all(line.has_result() for line in self.test_lines)

    def submit_results(self, actor: str, when: datetime) -> None:
        if not self.can_enter_results():
            raise ValueError(f"Submit Results requires InProgress status (current: {self.status})")
        if not self.all_lines_resulted():
            unresulted = [line.line_no for line in self.test_lines if not line.has_result()]
            raise ValueError(f"Every test line must have a result before submitting (missing: {unresulted})")
        self.status = "PendingADGLRelease"
        self.results_submitted_by = actor
        self.results_submitted_at = when
        self.mark_modified(actor)

    # ── ADGL review, correction, release ─────────────────────────

    def can_correct_result(self) -> bool:
        """Requirement 6.2: correction is only possible while PendingADGLRelease."""
        return self.status == "PendingADGLRelease"

    def can_release(self) -> bool:
        return self.status == "PendingADGLRelease"

    def release(self, actor: str, when: datetime, atr_snapshot: dict) -> None:
        if not self.can_release():
            raise ValueError(f"Release requires PendingADGLRelease status (current: {self.status})")
        self.status = "Released"
        self.released_by = actor
        self.released_at = when
        self.atr_snapshot = atr_snapshot
        self.mark_modified(actor)

    # ── Refer-Back resubmission ───────────────────────────────────

    def can_resubmit(self) -> bool:
        return self.status == "ReferredBack"

    def resubmit(self, actor: str, when: datetime) -> None:
        """Requirement 7.2, 7.3: always re-enters at PendingFDGLApproval."""
        if not self.can_resubmit():
            raise ValueError(f"Resubmit requires ReferredBack status (current: {self.status})")
        self.status = "PendingFDGLApproval"
        self.mark_modified(actor)

    # ── ATR ────────────────────────────────────────────────────────

    def can_view_atr(self) -> bool:
        return self.status == "Released"

    # ── Shared private helpers ────────────────────────────────────

    def _refer_back(self, gate_name: str, actor: str, comments: str, when: datetime) -> None:
        if not comments or not comments.strip():
            raise ValueError("A non-blank comment is required to refer back a TRF")
        expected = {
            "FDGL approval": self.can_fdgl_act,
            "ADGL acceptance": self.can_adgl_accept_act,
            "Analyst acceptance": self.can_analyst_act,
        }[gate_name]
        if not expected():
            raise ValueError(f"{gate_name} refer-back requires the matching source status (current: {self.status})")
        self.status = "ReferredBack"
        self.referred_back_by = actor
        self.referred_back_at = when
        self.referred_back_comments = comments.strip()
        self.mark_modified(actor)

    def _reject(self, gate_name: str, actor: str, comments: str, when: datetime) -> None:
        if not comments or not comments.strip():
            raise ValueError("A non-blank comment is required to reject a TRF")
        expected = {
            "FDGL approval": self.can_fdgl_act,
            "ADGL acceptance": self.can_adgl_accept_act,
            "Analyst acceptance": self.can_analyst_act,
        }[gate_name]
        if not expected():
            raise ValueError(f"{gate_name} rejection requires the matching source status (current: {self.status})")
        self.status = "Rejected"
        self.rejected_by = actor
        self.rejected_at = when
        self.rejected_comments = comments.strip()
        self.mark_modified(actor)
