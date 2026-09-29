"""
Worksheet API endpoints.

Two prefixes on one router, because the resources genuinely live in two places:
a worksheet is *created and found* through its TRF test line, but once it exists
it is addressed by its own id. Nesting the mutation routes under the test line
too would mean every save carried a redundant line id the service would have to
re-verify.

Role and status gating is enforced in `WorksheetService` rather than in
`require_role` here: who may write depends on the *parent TRF's status*, which a
static role dependency cannot express. The `require_role` guards below are the
outer bound — the union of roles that could ever be permitted.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_role
from src.api.v1.schemas.test_template_schemas import (
    ConfirmWorksheetResponse,
    CreateWorksheetRequest,
    CriterionResultResponse,
    SaveWorksheetRequest,
    TestTemplateResponse,
    WorksheetComputedResponse,
    WorksheetDetailResponse,
    WorksheetResponse,
    WorksheetValuesRequest,
)
from src.config.dependency_injection import Container
from src.domain.entities.test_template import TestTemplate, TestWorksheet
from src.domain.entities.user import User
from src.domain.services.calculation.evaluator import WorksheetResult
from src.domain.services.calculation.expression import EMPTY

router = APIRouter(tags=["Test Worksheets"])

_ANY_ROLE = ("Admin", "Analyst", "Supervisor", "QA")
_WRITERS = ("Admin", "Analyst", "QA")


def _plain(value):
    """`EMPTY` is an engine sentinel with no JSON representation."""
    return None if value is EMPTY else value


def _computed(result: WorksheetResult) -> WorksheetComputedResponse:
    return WorksheetComputedResponse(
        values={k: _plain(v) for k, v in result.values.items()},
        rows={
            group_key: [{k: _plain(v) for k, v in row.items()} for row in rows]
            for group_key, rows in result.rows.items()
        },
        criteria=[
            CriterionResultResponse(
                key=c.key,
                label=c.label,
                observed=_plain(c.observed),
                operator=c.operator.value,
                limit=list(c.limit),
                limit_text=c.limit_text,
                severity=c.severity.value,
                passed=c.passed,
            )
            for c in result.criteria
        ],
        reportable_result=_plain(result.reportable_result),
        has_blocking_failure=result.has_blocking_failure,
    )


def _detail(
    worksheet: TestWorksheet, template: TestTemplate, result: WorksheetResult
) -> WorksheetDetailResponse:
    return WorksheetDetailResponse(
        worksheet=WorksheetResponse.model_validate(worksheet),
        template=TestTemplateResponse.model_validate(template),
        computed=_computed(result),
    )


# ── Addressed through the TRF test line ──────────────────────────────


@router.post("/trf/test-lines/{line_id}/worksheet", response_model=WorksheetDetailResponse)
async def create_worksheet(
    line_id: int,
    request: CreateWorksheetRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 5.1, 5.2: attach an Active template to a test line and seed its context."""
    service = Container.get_worksheet_service(session)
    worksheet = await service.create_worksheet(line_id, request.template_id, current_user)
    _, template, result = await service.preview(worksheet.id)
    return _detail(worksheet, template, result)


@router.get("/trf/test-lines/{line_id}/worksheet", response_model=WorksheetDetailResponse)
async def get_worksheet_for_line(
    line_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """
    Requirement 5.2: the worksheet on a test line, with its definition and current
    computed state — one round trip for everything the entry form needs.

    404 when the line has no worksheet, which is a normal state rather than an
    error: not every test is templated.
    """
    service = Container.get_worksheet_service(session)
    worksheet = await service.get_worksheet_for_line(line_id)
    if worksheet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This test line has no worksheet",
        )
    _, template, result = await service.preview(worksheet.id)
    return _detail(worksheet, template, result)


@router.get("/trf/{trf_id}/worksheets", response_model=list[WorksheetResponse])
async def list_worksheets_for_trf(
    trf_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Every worksheet across a TRF's test lines — the basis for COA compilation."""
    service = Container.get_worksheet_service(session)
    return await service.list_for_trf(trf_id)


# ── Addressed by worksheet id ────────────────────────────────────────


@router.get("/worksheets/{worksheet_id}", response_model=WorksheetDetailResponse)
async def get_worksheet(
    worksheet_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_worksheet_service(session)
    worksheet, template, result = await service.preview(worksheet_id)
    return _detail(worksheet, template, result)


@router.post("/worksheets/{worksheet_id}/preview", response_model=WorksheetComputedResponse)
async def preview_worksheet(
    worksheet_id: int,
    request: WorksheetValuesRequest,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """
    Requirement 2.1, 2.5: recalculate against candidate values without persisting.

    This is what the entry form calls on every change, so it deliberately writes
    nothing — no row, no audit entry.
    """
    service = Container.get_worksheet_service(session)
    _, _, result = await service.preview(
        worksheet_id,
        context_values=request.context_values,
        group_values=request.group_values,
    )
    return _computed(result)


@router.put("/worksheets/{worksheet_id}/values", response_model=WorksheetDetailResponse)
async def save_worksheet_values(
    worksheet_id: int,
    request: SaveWorksheetRequest,
    current_user: User = Depends(require_role(*_WRITERS)),
    session: AsyncSession = Depends(get_session),
):
    """
    Requirement 4.2, 5.3, 5.6, 9.3, 9.4: persist entered values.

    Entry by Analyst/Admin while the TRF is `InProgress`; correction by QA/Admin
    while `PendingADGLRelease`, which additionally requires a `reason`. The
    service decides which applies from the parent TRF's status.
    """
    service = Container.get_worksheet_service(session)
    worksheet, template, result = await service.save_values(
        worksheet_id,
        current_user,
        context_values=request.context_values,
        group_values=request.group_values,
        reason=request.reason,
    )
    return _detail(worksheet, template, result)


@router.post("/worksheets/{worksheet_id}/confirm", response_model=ConfirmWorksheetResponse)
async def confirm_worksheet(
    worksheet_id: int,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """
    Requirement 5.4, 5.5, 2.7: snapshot the computed state and publish the
    reportable result to the test line. Refused while any blocking acceptance
    criterion fails.
    """
    service = Container.get_worksheet_service(session)
    worksheet, test_line, result = await service.confirm_result(worksheet_id, current_user)
    return ConfirmWorksheetResponse(
        worksheet=WorksheetResponse.model_validate(worksheet),
        computed=_computed(result),
        test_line_id=test_line.id,
        test_line_result=test_line.result,
    )
