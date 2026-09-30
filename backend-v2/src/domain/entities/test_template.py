"""
Test Template and Test Worksheet domain entities.

A `TestTemplate` is a versioned, approvable definition of one analytical
calculation sheet — replacing one of the lab's standalone Excel workbooks. A
`TestWorksheet` is the filled-in instance of a template bound to a single TRF
test line, holding the analyst's entered values, the chromatographic areas, and
the computed result snapshot.

Business rules (see design.md for rationale):
- A template's definition is only editable while `Draft` (Requirement 1.4);
  editing an `Active` template produces a NEW version via `new_version()` rather
  than mutating the approved one.
- Approval is e-signed and moves `PendingApproval -> Active` (Requirement 1.3).
- A worksheet is bound to a template *version* at creation and never re-pointed,
  so an executed worksheet stays reproducible after the template moves on
  (Requirement 2.7).
- Who may edit a worksheet's values is a function of the parent TRF's status:
  entry while the TRF is `InProgress`, correction while `PendingADGLRelease`
  (Requirements 5.3, 5.6). The status→mode mapping lives here; the role check
  belongs to the application service, which is the layer holding the `User`.
- A worksheet cannot be confirmed while any blocking acceptance criterion fails
  (Requirement 5.5); the criteria themselves are evaluated by the calculation
  engine, so this entity only guards on status.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.domain.entities.base_entity import BaseEntity


class TemplateStatus(str, Enum):
    DRAFT = "Draft"
    PENDING_APPROVAL = "PendingApproval"
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class WorksheetStatus(str, Enum):
    IN_PROGRESS = "InProgress"
    #  Analyst has submitted the worksheet for supervisory review; editing is
    #  locked until a reviewer approves or refers it back.
    PENDING_REVIEW = "PendingReview"
    #  A reviewer sent it back to the analyst with comments; editable again.
    REFERRED_BACK = "ReferredBack"
    CONFIRMED = "Confirmed"


#  Worksheet statuses in which the analyst may still edit values. A worksheet
#  under review (PendingReview) or already approved (Confirmed) is locked.
_EDITABLE_WORKSHEET_STATUSES = (
    WorksheetStatus.IN_PROGRESS.value,
    WorksheetStatus.REFERRED_BACK.value,
)

#  Roles that may review a submitted worksheet. GL/TL already inherit Supervisor
#  via ROLE_INHERITANCE, but they are listed explicitly so has_role — which
#  checks the raw role — accepts them here too.
WORKSHEET_REVIEWER_ROLES = ("Supervisor", "GL", "TL", "QA", "Admin")


class WorksheetEditMode(str, Enum):
    """Why a worksheet is being edited — drives which role is allowed."""

    ENTRY = "Entry"  # Analyst/Admin, parent TRF InProgress
    CORRECTION = "Correction"  # QA/Admin, parent TRF PendingADGLRelease


#  Parent-TRF statuses that permit worksheet mutation, and in which mode.
_EDIT_MODE_BY_TRF_STATUS: dict[str, WorksheetEditMode] = {
    "InProgress": WorksheetEditMode.ENTRY,
    "PendingADGLRelease": WorksheetEditMode.CORRECTION,
}


@dataclass
class TestTemplate(BaseEntity):
    """
    A versioned analytical calculation template.

    `definition` is the raw JSON body; it is parsed and validated by
    `TemplateDefinition.parse()` in the calculation domain service. This entity
    deliberately does not depend on that parser — it owns identity, versioning,
    and lifecycle, not schema semantics.
    """

    code: str = field(default="")
    name: str = field(default="")
    archetype: str = field(default="")
    test_id: int = field(default=0)
    version: int = field(default=1)
    status: str = field(default=TemplateStatus.DRAFT.value)
    result_unit: str | None = field(default=None)
    definition: dict = field(default_factory=dict)

    approved_by: str | None = field(default=None)
    approved_at: datetime | None = field(default=None)
    #  Set on the older version when a newer one is approved, so history is walkable.
    superseded_by_id: int | None = field(default=None)

    # ── Denormalized for API projection (avoids extra queries) ──
    test_code: str | None = field(default=None)
    test_name: str | None = field(default=None)

    # ── Guards ──

    def can_edit_definition(self) -> bool:
        """Requirement 1.4: the definition is only mutable while Draft."""
        return self.status == TemplateStatus.DRAFT.value

    def can_submit(self) -> bool:
        return self.status == TemplateStatus.DRAFT.value and bool(self.definition)

    def can_approve(self) -> bool:
        return self.status == TemplateStatus.PENDING_APPROVAL.value

    def can_reject(self) -> bool:
        return self.status == TemplateStatus.PENDING_APPROVAL.value

    def can_deactivate(self) -> bool:
        return self.status == TemplateStatus.ACTIVE.value

    def can_version(self) -> bool:
        """A new draft may be branched from any approved template."""
        return self.status in (TemplateStatus.ACTIVE.value, TemplateStatus.INACTIVE.value)

    @property
    def is_selectable(self) -> bool:
        """Only Active templates may be attached to a TRF test line."""
        return self.status == TemplateStatus.ACTIVE.value

    # ── Transitions ──

    def update_definition(self, definition: dict, actor: str) -> None:
        if not self.can_edit_definition():
            raise ValueError(
                f"A template's definition can only be edited while Draft "
                f"(current status: {self.status})"
            )
        self.definition = definition
        self.mark_modified(actor)

    def submit_for_approval(self, actor: str) -> None:
        if not self.can_submit():
            raise ValueError(
                f"Template must be Draft with a definition to submit "
                f"(current status: {self.status})"
            )
        self.status = TemplateStatus.PENDING_APPROVAL.value
        self.mark_modified(actor)

    def approve(self, actor: str, when: datetime) -> None:
        if not self.can_approve():
            raise ValueError(
                f"Approval requires PendingApproval status (current status: {self.status})"
            )
        self.status = TemplateStatus.ACTIVE.value
        self.approved_by = actor
        self.approved_at = when
        self.mark_modified(actor)

    def reject(self, actor: str) -> None:
        """Send an unapproved template back to its author."""
        if not self.can_reject():
            raise ValueError(
                f"Rejection requires PendingApproval status (current status: {self.status})"
            )
        self.status = TemplateStatus.DRAFT.value
        self.mark_modified(actor)

    def deactivate(self, actor: str) -> None:
        if not self.can_deactivate():
            raise ValueError(
                f"Only an Active template can be deactivated (current status: {self.status})"
            )
        self.status = TemplateStatus.INACTIVE.value
        self.mark_modified(actor)

    def new_version(self, actor: str) -> "TestTemplate":
        """
        Branch a new `Draft` from this template.

        Requirement 1.4 / Property 10: this returns a *new* entity and leaves
        `self` untouched, so worksheets already executed against this version
        keep resolving against exactly what they ran on. The caller persists the
        result and sets `superseded_by_id` on approval.
        """
        if not self.can_version():
            raise ValueError(
                f"A new version can only be branched from an approved template "
                f"(current status: {self.status})"
            )
        return TestTemplate(
            code=self.code,
            name=self.name,
            archetype=self.archetype,
            test_id=self.test_id,
            version=self.version + 1,
            status=TemplateStatus.DRAFT.value,
            result_unit=self.result_unit,
            #  Deep-ish copy: the definition must not alias the approved version's.
            definition=_deep_copy_json(self.definition),
            created_by=actor,
            modified_by=actor,
        )

    def mark_superseded_by(self, template_id: int, actor: str) -> None:
        self.superseded_by_id = template_id
        self.mark_modified(actor)


@dataclass
class TestWorksheet(BaseEntity):
    """
    The filled-in instance of a template on one TRF test line.

    `context_values` holds context-field values by key. `group_values` holds the
    analyst's input/area values per group as a list of row dicts. Computed values
    are NOT stored while in progress — they are derived on demand so a template
    fix is picked up immediately — but are snapshotted at confirmation so a
    reported result stays reproducible (Requirement 2.7).
    """

    trf_test_line_id: int = field(default=0)
    template_id: int = field(default=0)
    template_version: int = field(default=1)
    status: str = field(default=WorksheetStatus.IN_PROGRESS.value)

    context_values: dict[str, Any] = field(default_factory=dict)
    group_values: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    computed_snapshot: dict | None = field(default=None)
    reportable_result: str | None = field(default=None)

    confirmed_by: str | None = field(default=None)
    confirmed_at: datetime | None = field(default=None)

    # ── Review cycle (analyst submit -> supervisor approve / refer back) ──
    submitted_for_review_by: str | None = field(default=None)
    submitted_for_review_at: datetime | None = field(default=None)
    #  The analyst's note accompanying the submission.
    submission_comments: str | None = field(default=None)
    reviewed_by: str | None = field(default=None)
    reviewed_at: datetime | None = field(default=None)
    #  The reviewer's note on approve or refer-back.
    review_comments: str | None = field(default=None)

    # ── Denormalized for API projection ──
    template_code: str | None = field(default=None)
    template_name: str | None = field(default=None)

    # ── Guards ──

    @staticmethod
    def edit_mode_for(trf_status: str) -> WorksheetEditMode | None:
        """
        Which kind of edit the parent TRF's status permits, or `None`.

        Requirements 5.3 / 5.6: entry while `InProgress`, correction while
        `PendingADGLRelease`, nothing otherwise. The caller pairs the returned
        mode with a role check.
        """
        return _EDIT_MODE_BY_TRF_STATUS.get(trf_status)

    def can_edit_values(self, trf_status: str) -> bool:
        return self.edit_mode_for(trf_status) is not None and self.is_worksheet_editable

    @property
    def is_worksheet_editable(self) -> bool:
        """Worksheet-level gate: values are frozen while under review."""
        return self.status in _EDITABLE_WORKSHEET_STATUSES

    @property
    def is_pending_review(self) -> bool:
        return self.status == WorksheetStatus.PENDING_REVIEW.value

    def can_confirm(self, trf_status: str) -> bool:
        """
        Confirmation is only meaningful during result entry. Whether blocking
        acceptance criteria pass is decided by the calculation engine and
        enforced by the application service — this guard covers status only.
        """
        return self.edit_mode_for(trf_status) is WorksheetEditMode.ENTRY

    @property
    def is_confirmed(self) -> bool:
        return self.status == WorksheetStatus.CONFIRMED.value

    # ── Transitions ──

    def set_values(
        self,
        context_values: dict[str, Any] | None,
        group_values: dict[str, list[dict[str, Any]]] | None,
        actor: str,
    ) -> None:
        """Replace the stored input values. Callers validate status/role first."""
        if context_values is not None:
            self.context_values = dict(context_values)
        if group_values is not None:
            self.group_values = {k: [dict(r) for r in v] for k, v in group_values.items()}
        self.mark_modified(actor)

    def confirm(
        self, actor: str, when: datetime, computed_snapshot: dict, reportable_result: str | None
    ) -> None:
        """
        Freeze the computed state and publish the reportable result.

        Requirement 2.7 / Property 16: the snapshot captured here is never
        rewritten, so the reported number stays reproducible even if the
        template is later versioned or master data changes.
        """
        self.status = WorksheetStatus.CONFIRMED.value
        self.computed_snapshot = computed_snapshot
        self.reportable_result = reportable_result
        self.confirmed_by = actor
        self.confirmed_at = when
        self.mark_modified(actor)

    def reopen(self, actor: str) -> None:
        """
        Return a confirmed worksheet to entry so a correction can be made.

        The prior snapshot is intentionally retained until the next confirmation
        overwrites it, so there is never a window where a released TRF has a
        result with no supporting snapshot.
        """
        self.status = WorksheetStatus.IN_PROGRESS.value
        self.confirmed_by = None
        self.confirmed_at = None
        self.mark_modified(actor)

    # ── Review cycle transitions ──

    def submit_for_review(self, actor: str, when: datetime, comments: str | None) -> None:
        """
        Analyst sends the worksheet to a supervisor. Only from an editable state
        (InProgress or ReferredBack); locks editing until the reviewer acts.
        """
        if not self.is_worksheet_editable:
            raise ValueError(
                f"Only a worksheet in progress can be submitted for review "
                f"(current status: {self.status})"
            )
        self.status = WorksheetStatus.PENDING_REVIEW.value
        self.submitted_for_review_by = actor
        self.submitted_for_review_at = when
        self.submission_comments = comments
        #  Clear any prior review outcome now a fresh cycle has started.
        self.reviewed_by = None
        self.reviewed_at = None
        self.review_comments = None
        self.mark_modified(actor)

    def refer_back(self, actor: str, when: datetime, comments: str | None) -> None:
        """Reviewer returns the worksheet to the analyst for changes."""
        if not self.is_pending_review:
            raise ValueError(
                f"Only a worksheet pending review can be referred back "
                f"(current status: {self.status})"
            )
        self.status = WorksheetStatus.REFERRED_BACK.value
        self.reviewed_by = actor
        self.reviewed_at = when
        self.review_comments = comments
        self.mark_modified(actor)

    def approve_review(self, actor: str, when: datetime, comments: str | None) -> None:
        """
        Reviewer accepts the submitted worksheet. Records the review outcome; the
        service performs the result confirmation (snapshot + publish) separately,
        since that requires the calculation engine.
        """
        if not self.is_pending_review:
            raise ValueError(
                f"Only a worksheet pending review can be approved "
                f"(current status: {self.status})"
            )
        self.reviewed_by = actor
        self.reviewed_at = when
        self.review_comments = comments
        self.mark_modified(actor)


def _deep_copy_json(value: Any) -> Any:
    """
    Copy a JSON-shaped structure so a branched version cannot alias its parent's
    definition. Avoids `copy.deepcopy` because the payload is known to be plain
    JSON, and aliasing an approved template's definition would be a correctness
    bug rather than a performance one.
    """
    if isinstance(value, dict):
        return {k: _deep_copy_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deep_copy_json(v) for v in value]
    return value
