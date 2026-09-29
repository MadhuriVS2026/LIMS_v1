"""Sample Manager API endpoints — the core LIMS workflow."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user, get_session, require_role
from src.api.v1.schemas.auth_schemas import ESignRequest
from src.api.v1.schemas.sample_schemas import (
    CreateSampleRequest,
    SampleResponse,
    SampleResultResponse,
    SubmitResultRequest,
    UpdateSampleRequest,
)
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/samples", tags=["Samples"])


@router.get("", response_model=list[SampleResponse])
async def list_samples(
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_sample_service(session)
    return await service.list_samples(status)


@router.post("", response_model=SampleResponse)
async def log_sample(
    request: CreateSampleRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Sample Login Registration — auto-generates A.R. Number, seeds results from Active Specification."""
    service = Container.get_sample_service(session)
    return await service.log_sample(
        request.product_id, request.batch_number, request.quantity_received, request.unit,
        request.sample_type, request.priority or "Normal", request.sap_inspection_lot,
        request.sap_material, request.sap_plant, request.sap_vendor, request.sap_vendor_batch,
        request.manufacturing_date, request.expiry_date, current_user,
    )


@router.post("/{sample_id}/receive", response_model=SampleResponse)
async def receive_sample(
    sample_id: int,
    current_user: User = Depends(require_role("Analyst", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_sample_service(session)
    return await service.receive_sample(sample_id, current_user)


@router.put("/{sample_id}", response_model=SampleResponse)
async def update_sample(
    sample_id: int,
    request: UpdateSampleRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Edit sample registration details. Only permitted while the sample is
    Logged or Received."""
    service = Container.get_sample_service(session)
    return await service.update_sample(
        sample_id, current_user,
        batch_number=request.batch_number, quantity_received=request.quantity_received,
        unit=request.unit, sample_type=request.sample_type, priority=request.priority,
        sap_inspection_lot=request.sap_inspection_lot, sap_material=request.sap_material,
        sap_plant=request.sap_plant, sap_vendor=request.sap_vendor,
        sap_vendor_batch=request.sap_vendor_batch,
        manufacturing_date=request.manufacturing_date, expiry_date=request.expiry_date,
    )


@router.delete("/{sample_id}", response_model=SampleResponse)
async def delete_sample(
    sample_id: int,
    esign: ESignRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete (deactivate) a sample. E-signed; blocked once released.
    Writes an audit entry flagged for GL/TL/Supervisor/Admin review."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, esign.password)

    service = Container.get_sample_service(session)
    return await service.soft_delete_sample(sample_id, current_user, esign.comments)


@router.post("/{sample_id}/release", response_model=SampleResponse)
async def release_batch(
    sample_id: int,
    verdict: str = Query(...),
    esign: ESignRequest | None = None,
    current_user: User = Depends(require_role("QA")),
    session: AsyncSession = Depends(get_session),
):
    """QA releases the batch with an E-Signed verdict; generates immutable COA snapshot."""
    if esign and esign.password:
        auth_service = Container.get_auth_service(session)
        await auth_service.verify_esignature(current_user, esign.password)

    service = Container.get_sample_service(session)
    return await service.release_sample(sample_id, verdict, current_user, esign.comments if esign else None)


@router.get("/{sample_id}/coa")
async def get_coa(
    sample_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_sample_service(session)
    sample = await service.get_sample(sample_id)
    if sample.status not in ("Approved", "Rejected"):
        from src.application.exceptions.application_exceptions import ValidationException
        raise ValidationException("Sample not yet released")
    if not sample.coa_data:
        from src.application.exceptions.application_exceptions import ValidationException
        raise ValidationException("COA data not available")
    return sample.coa_data
