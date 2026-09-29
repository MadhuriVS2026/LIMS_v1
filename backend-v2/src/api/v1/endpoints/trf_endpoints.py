"""TRF — Test Request Form API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_role
from src.api.v1.schemas.trf_schemas import (
    CreateTestLineRequest,
    CreateTRFRequest,
    EsignActionRequest,
    ReferBackRejectRequest,
    SubmitTestResultRequest,
    TRFResponse,
    TRFTestLineResponse,
)
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/trf", tags=["TRF — Test Request Form"])

_ANY_ROLE = ("Admin", "Analyst", "Supervisor", "QA")


@router.post("", response_model=TRFResponse)
async def create_trf(
    request: CreateTRFRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.1, 9.1: raise a new Draft TRF."""
    service = Container.get_trf_service(session)
    return await service.create_trf(request.model_dump(), current_user)


@router.get("", response_model=list[TRFResponse])
async def list_trfs(
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 12.1: Admin/QA/Supervisor see all TRFs; others see own-initiated or assigned."""
    service = Container.get_trf_service(session)
    return await service.list_trfs(current_user)


@router.get("/{trf_id}", response_model=TRFResponse)
async def get_trf(
    trf_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 9.5: any authenticated role may view a TRF's header and test lines."""
    service = Container.get_trf_service(session)
    return await service.get_trf(trf_id)


@router.get("/{trf_id}/atr")
async def get_atr(
    trf_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 8.1, 8.2, 9.5: ATR snapshot, only once Released."""
    service = Container.get_trf_service(session)
    return await service.get_atr(trf_id)


@router.post("/{trf_id}/test-lines", response_model=TRFTestLineResponse)
async def add_test_line(
    trf_id: int,
    request: CreateTestLineRequest,
    current_user: User = Depends(require_role("Admin", "Analyst", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.2, 1.4, 9.1: add a test line while Draft/ReferredBack, or PendingFDGLApproval for FDGL."""
    service = Container.get_trf_service(session)
    return await service.add_test_line(
        trf_id, request.test_id, request.specification, request.raw_data_reference, request.remark, current_user
    )


@router.delete("/{trf_id}/test-lines/{line_id}")
async def remove_test_line(
    trf_id: int,
    line_id: int,
    current_user: User = Depends(require_role("Admin", "Analyst", "Supervisor")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Requirement 1.3, 1.4, 9.1: remove a test line while Draft/ReferredBack, or PendingFDGLApproval for FDGL."""
    service = Container.get_trf_service(session)
    await service.remove_test_line(trf_id, line_id, current_user)
    return {"success": True, "message": "Test line removed"}


@router.post("/{trf_id}/submit", response_model=TRFResponse)
async def submit_trf(
    trf_id: int,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 2.1, 2.2, 2.3, 9.1: submit a Draft/ReferredBack TRF, requires >=1 test line."""
    service = Container.get_trf_service(session)
    return await service.submit_trf(trf_id, current_user)


# ── FDGL gate (Supervisor/Admin) ────────────────────────────────────────


@router.post("/{trf_id}/fdgl-approve", response_model=TRFResponse)
async def fdgl_approve(
    trf_id: int,
    request: EsignActionRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 3.1, 3.2, 9.2: e-signed FDGL approval -> PendingADGLAcceptance."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_trf_service(session)
    return await service.fdgl_approve(trf_id, current_user)


@router.post("/{trf_id}/fdgl-refer-back", response_model=TRFResponse)
async def fdgl_refer_back(
    trf_id: int,
    request: ReferBackRejectRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 3.3, 3.4, 9.2: FDGL refers the TRF back to the Initiator."""
    service = Container.get_trf_service(session)
    return await service.fdgl_refer_back(trf_id, current_user, request.comments)


@router.post("/{trf_id}/fdgl-reject", response_model=TRFResponse)
async def fdgl_reject(
    trf_id: int,
    request: ReferBackRejectRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 3.3, 3.4, 9.2: FDGL rejects the TRF."""
    service = Container.get_trf_service(session)
    return await service.fdgl_reject(trf_id, current_user, request.comments)


# ── ADGL acceptance gate (QA/Admin) ─────────────────────────────────────


@router.post("/{trf_id}/adgl-accept", response_model=TRFResponse)
async def adgl_accept(
    trf_id: int,
    request: EsignActionRequest,
    current_user: User = Depends(require_role("Admin", "QA")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 4.1, 4.2, 4.6, 9.3: e-signed ADGL acceptance, assigns ar_number."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_trf_service(session)
    return await service.adgl_accept(trf_id, current_user)


@router.post("/{trf_id}/adgl-refer-back", response_model=TRFResponse)
async def adgl_refer_back(
    trf_id: int,
    request: ReferBackRejectRequest,
    current_user: User = Depends(require_role("Admin", "QA")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 4.3, 9.3: ADGL refers the TRF back to the Initiator."""
    service = Container.get_trf_service(session)
    return await service.adgl_refer_back(trf_id, current_user, request.comments)


@router.post("/{trf_id}/adgl-reject", response_model=TRFResponse)
async def adgl_reject(
    trf_id: int,
    request: ReferBackRejectRequest,
    current_user: User = Depends(require_role("Admin", "QA")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 4.3, 9.3: ADGL rejects the TRF."""
    service = Container.get_trf_service(session)
    return await service.adgl_reject(trf_id, current_user, request.comments)


# ── Analyst gate (Analyst/Admin) ────────────────────────────────────────


@router.post("/{trf_id}/analyst-accept", response_model=TRFResponse)
async def analyst_accept(
    trf_id: int,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 5.1, 9.4: Analyst self-assigns by accepting -> InProgress. Not e-signed."""
    service = Container.get_trf_service(session)
    return await service.analyst_accept(trf_id, current_user)


@router.post("/{trf_id}/analyst-refer-back", response_model=TRFResponse)
async def analyst_refer_back(
    trf_id: int,
    request: ReferBackRejectRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 5.2, 9.4: Analyst refers the TRF back to the Initiator."""
    service = Container.get_trf_service(session)
    return await service.analyst_refer_back(trf_id, current_user, request.comments)


@router.post("/{trf_id}/analyst-reject", response_model=TRFResponse)
async def analyst_reject(
    trf_id: int,
    request: ReferBackRejectRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 5.2, 9.4: Analyst rejects the TRF."""
    service = Container.get_trf_service(session)
    return await service.analyst_reject(trf_id, current_user, request.comments)


# ── Result entry, submission, correction, release ───────────────────────


@router.put("/test-lines/{line_id}/result", response_model=TRFTestLineResponse)
async def submit_test_result(
    line_id: int,
    request: SubmitTestResultRequest,
    current_user: User = Depends(require_role("Admin", "Analyst", "QA")),
    session: AsyncSession = Depends(get_session),
):
    """
    Requirement 5.3, 6.1, 9.4: Analyst/Admin sets/updates a result while the parent TRF is
    InProgress; QA/Admin corrects a result while PendingADGLRelease (as a correction). Routed
    here by the parent TRF's current status — TRFService still enforces the exact status/role
    precondition for whichever path is taken.
    """
    service = Container.get_trf_service(session)
    line = await service.get_test_line(line_id)
    trf = await service.get_trf(line.trf_id)

    if trf.status == "PendingADGLRelease":
        return await service.correct_test_result(line_id, request.result, request.remark, current_user)
    return await service.submit_test_result(line_id, request.result, request.remark, current_user)


@router.post("/{trf_id}/submit-results", response_model=TRFResponse)
async def submit_results(
    trf_id: int,
    request: EsignActionRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 5.4, 5.5, 5.6, 9.4: e-signed results submission -> PendingADGLRelease."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_trf_service(session)
    return await service.submit_results(trf_id, current_user)


@router.post("/{trf_id}/release", response_model=TRFResponse)
async def release_results(
    trf_id: int,
    request: EsignActionRequest,
    current_user: User = Depends(require_role("Admin", "QA")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 6.3, 6.4, 9.3: e-signed release -> Released, captures the ATR snapshot."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_trf_service(session)
    return await service.release_results(trf_id, current_user)


@router.post("/{trf_id}/resubmit", response_model=TRFResponse)
async def resubmit_trf(
    trf_id: int,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 7.1, 7.2, 9.1: resubmit a ReferredBack TRF, always re-enters at FDGL."""
    service = Container.get_trf_service(session)
    return await service.resubmit_trf(trf_id, current_user)
