"""Resource Manager API endpoints: Instruments, Columns, Reference Standards,
Chemicals/Reagents, and Volumetric Solutions. Stability Management has its own
endpoints — see stability_endpoints.py."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user, get_session, require_role
from src.api.v1.schemas.resource_schemas import (
    ChemicalResponse,
    ColumnResponse,
    CreateChemicalRequest,
    CreateColumnRequest,
    CreateInstrumentRequest,
    CreateReferenceStandardRequest,
    CreateVolumetricSolutionRequest,
    InstrumentResponse,
    RecordCalibrationRequest,
    ReferenceStandardResponse,
    VolumetricSolutionResponse,
)
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(tags=["Resource Manager"])


# ─── Instruments ───
@router.get("/instruments", response_model=list[InstrumentResponse])
async def list_instruments(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await Container.get_resource_service(session).list_instruments()


@router.post("/instruments", response_model=InstrumentResponse)
async def create_instrument(
    request: CreateInstrumentRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_resource_service(session)
    return await service.create_instrument(
        request.code, request.name, request.category, request.manufacturer,
        request.model_number, request.serial_number, request.location,
        request.calibration_frequency_days, current_user,
    )


@router.post("/instruments/{instrument_id}/calibrate", response_model=InstrumentResponse)
async def calibrate_instrument(
    instrument_id: int,
    request: RecordCalibrationRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_resource_service(session)
    return await service.record_calibration(
        instrument_id, request.calibration_date, request.next_due_date,
        request.result, request.certificate_no, request.comments, current_user,
    )


# ─── Columns ───
@router.get("/columns", response_model=list[ColumnResponse])
async def list_columns(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await Container.get_resource_service(session).list_columns()


@router.post("/columns", response_model=ColumnResponse)
async def create_column(
    request: CreateColumnRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_resource_service(session)
    return await service.create_column(
        request.code, request.name, request.type, request.manufacturer, request.dimensions,
        request.serial_number, request.instrument_id, request.max_injections, current_user,
    )


# ─── Reference Standards ───
@router.get("/reference-standards", response_model=list[ReferenceStandardResponse])
async def list_reference_standards(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await Container.get_resource_service(session).list_reference_standards()


@router.post("/reference-standards", response_model=ReferenceStandardResponse)
async def create_reference_standard(
    request: CreateReferenceStandardRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_resource_service(session)
    return await service.create_reference_standard(
        request.code, request.name, request.lot_number, request.potency, request.manufacturer,
        request.category, request.storage_condition, request.quantity_received, request.unit,
        request.received_date, request.expiry_date, current_user,
    )


# ─── Chemicals / Reagents ───
@router.get("/chemicals", response_model=list[ChemicalResponse])
async def list_chemicals(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await Container.get_resource_service(session).list_chemicals()


@router.post("/chemicals", response_model=ChemicalResponse)
async def create_chemical(
    request: CreateChemicalRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_resource_service(session)
    return await service.create_chemical(
        request.code, request.name, request.grade, request.manufacturer, request.lot_number,
        request.cas_number, request.quantity_received, request.unit, request.storage_condition,
        request.received_date, request.expiry_date, current_user,
    )


# ─── Volumetric Solutions ───
@router.get("/volumetric-solutions", response_model=list[VolumetricSolutionResponse])
async def list_volumetric_solutions(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await Container.get_resource_service(session).list_volumetric_solutions()


@router.post("/volumetric-solutions", response_model=VolumetricSolutionResponse)
async def create_volumetric_solution(
    request: CreateVolumetricSolutionRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_resource_service(session)
    return await service.create_volumetric_solution(
        request.code, request.name, request.concentration, request.prepared_date,
        request.expiry_date, request.standardization_factor, current_user,
    )
