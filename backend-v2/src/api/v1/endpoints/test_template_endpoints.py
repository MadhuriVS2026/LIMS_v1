"""
Test template API endpoints.

Authoring is Admin-only; approval is e-signed by Admin/Supervisor/QA, verified
here via `AuthService.verify_esignature` before the service runs, matching the
established MRN/TRF gate pattern. Reading the catalogue is open to any
authenticated role — an analyst needs to see which template a result came from.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_role
from src.api.v1.schemas.test_template_schemas import (
    CreateTemplateRequest,
    DeactivateTemplateRequest,
    EsignActionRequest,
    RejectTemplateRequest,
    TestTemplateResponse,
    TestTemplateSummaryResponse,
    UpdateDefinitionRequest,
    UpdateTemplateHeaderRequest,
)
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/test-templates", tags=["Test Templates"])

_ANY_ROLE = ("Admin", "Analyst", "Supervisor", "QA")
_REVIEWER = ("Admin", "Supervisor", "QA")


@router.get("", response_model=list[TestTemplateSummaryResponse])
async def list_templates(
    test_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.1: the template catalogue, without the definition bodies."""
    service = Container.get_test_template_service(session)
    return await service.list_templates(test_id=test_id, status=status)


@router.get("/for-test/{test_id}", response_model=list[TestTemplateSummaryResponse])
async def templates_for_test(
    test_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.5: only Active templates, i.e. what a test line may attach."""
    service = Container.get_test_template_service(session)
    return await service.templates_for_test(test_id)


@router.get("/{template_id}", response_model=TestTemplateResponse)
async def get_template(
    template_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.1: full template including its definition."""
    service = Container.get_test_template_service(session)
    return await service.get_template(template_id)


@router.get("/{template_id}/versions", response_model=list[TestTemplateSummaryResponse])
async def list_versions(
    template_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.4: every version sharing this template's code, newest first."""
    service = Container.get_test_template_service(session)
    template = await service.get_template(template_id)
    return await service.list_versions(template.code)


@router.post("", response_model=TestTemplateResponse)
async def create_template(
    request: CreateTemplateRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.1, 1.2, 9.1: create a Draft template with a validated definition."""
    service = Container.get_test_template_service(session)
    return await service.create_template(
        name=request.name,
        archetype=request.archetype,
        test_id=request.test_id,
        definition=request.definition,
        result_unit=request.result_unit,
        actor=current_user,
    )


@router.put("/{template_id}/definition", response_model=TestTemplateResponse)
async def update_definition(
    template_id: int,
    request: UpdateDefinitionRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.2, 1.4: replace a Draft template's definition."""
    service = Container.get_test_template_service(session)
    return await service.update_definition(template_id, request.definition, current_user)


@router.put("/{template_id}", response_model=TestTemplateResponse)
async def update_header(
    template_id: int,
    request: UpdateTemplateHeaderRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    """Rename or re-unit a Draft template without touching its definition."""
    service = Container.get_test_template_service(session)
    return await service.update_header(
        template_id, current_user, name=request.name, result_unit=request.result_unit
    )


@router.post("/{template_id}/submit", response_model=TestTemplateResponse)
async def submit_for_approval(
    template_id: int,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.3: Draft -> PendingApproval."""
    service = Container.get_test_template_service(session)
    return await service.submit_for_approval(template_id, current_user)


@router.post("/{template_id}/approve", response_model=TestTemplateResponse)
async def approve_template(
    template_id: int,
    request: EsignActionRequest,
    current_user: User = Depends(require_role(*_REVIEWER)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.3, 9.2: e-signed approval -> Active, superseding any older version."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_test_template_service(session)
    return await service.approve(template_id, current_user, comments=request.comments)


@router.post("/{template_id}/reject", response_model=TestTemplateResponse)
async def reject_template(
    template_id: int,
    request: RejectTemplateRequest,
    current_user: User = Depends(require_role(*_REVIEWER)),
    session: AsyncSession = Depends(get_session),
):
    """Send an unapproved template back to its author with a reason."""
    service = Container.get_test_template_service(session)
    return await service.reject(template_id, current_user, request.reason)


@router.post("/{template_id}/new-version", response_model=TestTemplateResponse)
async def new_version(
    template_id: int,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.4: branch an approved template into a new Draft, leaving it untouched."""
    service = Container.get_test_template_service(session)
    return await service.new_version(template_id, current_user)


@router.post("/{template_id}/deactivate", response_model=TestTemplateResponse)
async def deactivate_template(
    template_id: int,
    request: DeactivateTemplateRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.5: stop offering this template on new test lines."""
    service = Container.get_test_template_service(session)
    return await service.deactivate(template_id, current_user, reason=request.reason)
