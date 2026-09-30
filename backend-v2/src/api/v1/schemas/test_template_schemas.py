"""
Pydantic schemas for test-template and worksheet endpoints.

The template `definition` and the worksheet's `context_values`/`group_values`
are intentionally passed through as loose JSON rather than modelled field by
field. They are validated by `TemplateDefinition.parse` and the worksheet
service, which are the only places that understand template semantics; a
second Pydantic model of the same structure would be a duplicate schema to keep
in sync, and it would reject a template the engine could actually run.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Templates ────────────────────────────────────────────────────────


class TestTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    archetype: str
    test_id: int
    test_code: str | None = None
    test_name: str | None = None
    version: int
    status: str
    result_unit: str | None = None
    definition: dict = {}
    approved_by: str | None = None
    approved_at: datetime | None = None
    superseded_by_id: int | None = None
    created_by: str | None = None
    created_date: datetime | None = None
    modified_by: str | None = None
    modified_date: datetime | None = None


class TestTemplateSummaryResponse(BaseModel):
    """List projection — omits `definition`, which can run to tens of kilobytes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    archetype: str
    test_id: int
    test_code: str | None = None
    test_name: str | None = None
    version: int
    status: str
    result_unit: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    superseded_by_id: int | None = None
    created_by: str | None = None
    created_date: datetime | None = None


class CreateTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    archetype: str = Field(min_length=1, max_length=50)
    test_id: int
    result_unit: str | None = Field(default=None, max_length=50)
    definition: dict


class UpdateDefinitionRequest(BaseModel):
    definition: dict


class UpdateTemplateHeaderRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    result_unit: str | None = Field(default=None, max_length=50)


class EsignActionRequest(BaseModel):
    """Shared shape for e-signed actions, matching the MRN/TRF convention."""

    password: str
    comments: str | None = None


class RejectTemplateRequest(BaseModel):
    reason: str = Field(min_length=1)


class DeactivateTemplateRequest(BaseModel):
    reason: str | None = None


# ── Worksheets ───────────────────────────────────────────────────────


class CriterionResultResponse(BaseModel):
    key: str
    label: str
    observed: Any = None
    operator: str
    limit: list[float]
    limit_text: str
    severity: str
    #  `None` when the observed value is still blank, i.e. not yet assessable —
    #  which is distinct from failing, and the UI must not show it as a failure.
    passed: bool | None = None


class WorksheetComputedResponse(BaseModel):
    """
    The evaluated state of a worksheet.

    `values` holds context scalars and singleton-group fields as `group.field`;
    `rows` holds every group's rows including calculated columns. Both are
    returned so the UI can render any template generically without knowing which
    archetype it is looking at.
    """

    values: dict[str, Any] = {}
    rows: dict[str, list[dict[str, Any]]] = {}
    criteria: list[CriterionResultResponse] = []
    reportable_result: Any = None
    has_blocking_failure: bool = False


class WorksheetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trf_test_line_id: int
    template_id: int
    template_version: int
    template_code: str | None = None
    template_name: str | None = None
    status: str
    context_values: dict[str, Any] = {}
    group_values: dict[str, list[dict[str, Any]]] = {}
    computed_snapshot: dict | None = None
    reportable_result: str | None = None
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    submitted_for_review_by: str | None = None
    submitted_for_review_at: datetime | None = None
    submission_comments: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_comments: str | None = None
    created_by: str | None = None
    created_date: datetime | None = None
    modified_by: str | None = None
    modified_date: datetime | None = None


class ReviewActionRequest(BaseModel):
    """Comments accompanying a worksheet submit / approve / refer-back."""

    comments: str | None = None


class WorksheetDetailResponse(BaseModel):
    """
    A worksheet together with the definition it is bound to and its current
    computed state — one round trip for everything the entry form needs.
    """

    worksheet: WorksheetResponse
    template: TestTemplateResponse
    computed: WorksheetComputedResponse


class CreateWorksheetRequest(BaseModel):
    template_id: int


class WorksheetValuesRequest(BaseModel):
    """
    Candidate values for preview or save.

    `None` means "leave what is stored alone"; an empty dict means "clear it".
    That distinction is why these are nullable rather than defaulting to `{}`.
    """

    context_values: dict[str, Any] | None = None
    group_values: dict[str, list[dict[str, Any]]] | None = None


class SaveWorksheetRequest(WorksheetValuesRequest):
    #  Required by the service when the parent TRF is PendingADGLRelease, i.e.
    #  when this is a correction to an already-submitted result.
    reason: str | None = None


class ConfirmWorksheetResponse(BaseModel):
    worksheet: WorksheetResponse
    computed: WorksheetComputedResponse
    test_line_id: int
    test_line_result: str | None = None
