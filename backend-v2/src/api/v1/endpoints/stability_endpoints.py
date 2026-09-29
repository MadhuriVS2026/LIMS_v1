"""Stability Management API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user, get_session, require_role
from src.api.v1.schemas.stability_schemas import (
    CancelProtocolRequest,
    CreateProtocolRequest,
    CreateReservePullRequest,
    EsignActionRequest,
    GenerateScheduleRequest,
    SetMatrixCellsRequest,
    SetReportSignatureNamesRequest,
    StabilityMatrixCellResponse,
    StabilityProtocolResponse,
    StabilityReportResponse,
    StabilitySampleResponse,
    UpdateProtocolHeaderRequest,
)
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/stability", tags=["Stability Management"])


# ─── Protocols ───
@router.get("/protocols", response_model=list[StabilityProtocolResponse])
async def list_protocols(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    """Requirement 8.6: any authenticated role may view."""
    service = Container.get_stability_service(session)
    return await service.list_protocols()


@router.post("/protocols", response_model=StabilityProtocolResponse)
async def create_protocol(
    request: CreateProtocolRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 2.1, 8.1: raise a new Draft protocol."""
    service = Container.get_stability_service(session)
    return await service.create_protocol(request.model_dump(), current_user)


@router.get("/protocols/{protocol_id}", response_model=StabilityProtocolResponse)
async def get_protocol(
    protocol_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_stability_service(session)
    return await service.get_protocol(protocol_id)


@router.patch("/protocols/{protocol_id}", response_model=StabilityProtocolResponse)
async def update_protocol_header(
    protocol_id: int,
    request: UpdateProtocolHeaderRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Edit protocol header fields — Draft only."""
    service = Container.get_stability_service(session)
    fields = request.model_dump(exclude_unset=True)
    return await service.update_protocol_header(protocol_id, fields, current_user)


@router.post("/protocols/{protocol_id}/complete", response_model=StabilityProtocolResponse)
async def complete_protocol(
    protocol_id: int,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Manually close out an Active study."""
    service = Container.get_stability_service(session)
    return await service.complete_protocol(protocol_id, current_user)


@router.post("/protocols/{protocol_id}/cancel", response_model=StabilityProtocolResponse)
async def cancel_protocol(
    protocol_id: int,
    request: CancelProtocolRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Cancel a protocol from any non-terminal state."""
    service = Container.get_stability_service(session)
    return await service.cancel_protocol(protocol_id, current_user, request.reason)


# ─── Loading Matrix ───
@router.get("/protocols/{protocol_id}/matrix", response_model=list[StabilityMatrixCellResponse])
async def get_matrix(
    protocol_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_stability_service(session)
    return await service.list_matrix_cells(protocol_id)


@router.put("/protocols/{protocol_id}/matrix", response_model=list[StabilityMatrixCellResponse])
async def set_matrix(
    protocol_id: int,
    request: SetMatrixCellsRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.2-1.4, 8.1: upsert Loading Matrix cells (Draft-only)."""
    service = Container.get_stability_service(session)
    cells = [c.model_dump() for c in request.cells]
    return await service.set_matrix_cells(protocol_id, cells, current_user)


# ─── Two-step approval ───
@router.post("/protocols/{protocol_id}/check-formulation", response_model=StabilityProtocolResponse)
async def check_formulation(
    protocol_id: int,
    request: EsignActionRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 3.1-3.3, 8.2: Draft -> FormulationChecked (e-signed)."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_stability_service(session)
    return await service.check_formulation(protocol_id, current_user)


@router.post("/protocols/{protocol_id}/check-analytical", response_model=StabilityProtocolResponse)
async def check_analytical(
    protocol_id: int,
    request: EsignActionRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 3.4-3.6, 8.2: FormulationChecked -> Active (e-signed)."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_stability_service(session)
    return await service.check_analytical(protocol_id, current_user)


# ─── Schedule & pull ───
@router.post("/protocols/{protocol_id}/generate-schedule", response_model=list[StabilitySampleResponse])
async def generate_schedule(
    protocol_id: int,
    request: GenerateScheduleRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 4.1-4.5, 8.3: generate time-point schedule for an Active protocol."""
    service = Container.get_stability_service(session)
    return await service.generate_schedule(protocol_id, request.batch_numbers, current_user)


@router.get("/protocols/{protocol_id}/samples", response_model=list[StabilitySampleResponse])
async def list_samples(
    protocol_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 5.4, 8.6: derived status recomputed on every read."""
    service = Container.get_stability_service(session)
    return await service.list_samples(protocol_id)


@router.post("/samples/{stability_sample_id}/pull", response_model=StabilitySampleResponse)
async def pull_sample(
    stability_sample_id: int,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 5.1-5.3, 8.3: pull a Scheduled time point, auto-creating a Sample."""
    service = Container.get_stability_service(session)
    return await service.pull_sample(stability_sample_id, current_user)


@router.post("/protocols/{protocol_id}/reserve-pull", response_model=StabilitySampleResponse)
async def create_reserve_pull(
    protocol_id: int,
    request: CreateReservePullRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """
    Raises an on-demand pull from a Reserve matrix cell (e.g. for an OOS
    retest), returned already Scheduled — call the regular /pull endpoint
    on the returned sample's id to actually pull it into Sample Manager.
    """
    service = Container.get_stability_service(session)
    return await service.create_reserve_sample(
        protocol_id, request.matrix_cell_id, request.batch_number, request.comments, current_user
    )


# ─── Reports ───
@router.post("/protocols/{protocol_id}/reports", response_model=StabilityReportResponse)
async def generate_report(
    protocol_id: int,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 6.1-6.4, 8.4: assemble a Stability Report from Completed time points."""
    service = Container.get_stability_service(session)
    return await service.generate_report(protocol_id, current_user)


@router.get("/protocols/{protocol_id}/reports", response_model=list[StabilityReportResponse])
async def list_reports(
    protocol_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_stability_service(session)
    return await service.list_reports(protocol_id)


@router.get("/reports/{report_id}", response_model=StabilityReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_stability_service(session)
    return await service.get_report(report_id)


@router.patch("/reports/{report_id}/signature-names", response_model=StabilityReportResponse)
async def set_report_signature_names(
    report_id: int,
    request: SetReportSignatureNamesRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Sets the free-text 'Checked By'/'Reviewed By' print names — Draft only."""
    service = Container.get_stability_service(session)
    return await service.set_report_signature_names(
        report_id, request.checked_by_name, request.reviewed_by_name, current_user
    )


@router.post("/reports/{report_id}/prepare", response_model=StabilityReportResponse)
async def prepare_report(
    report_id: int,
    request: EsignActionRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 7.1, 7.2, 8.4: Draft -> Prepared (Analyst e-sign)."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_stability_service(session)
    return await service.prepare_report(report_id, current_user)


@router.post("/reports/{report_id}/approve", response_model=StabilityReportResponse)
async def approve_report(
    report_id: int,
    request: EsignActionRequest,
    current_user: User = Depends(require_role("Admin", "QA")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 7.3, 7.4, 8.5: Prepared -> Approved (QA e-sign)."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_stability_service(session)
    return await service.approve_report(report_id, current_user)
