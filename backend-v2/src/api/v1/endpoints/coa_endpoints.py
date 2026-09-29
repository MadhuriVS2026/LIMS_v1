"""
Certificate of Analysis API endpoints.

Generation is e-signed and restricted to QA/Admin. Reading is open to any
authenticated role — an analyst needs to see the certificate their results went
into.

There is no update or delete route, matching the repository: a certificate is
issued once, and a correction is a new certificate that supersedes it.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_role
from src.api.v1.schemas.coa_schemas import (
    COAPreviewResponse,
    COAResponse,
    COASummaryResponse,
    GenerateCOARequest,
    PreviewCOARequest,
)
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/coa", tags=["Certificate of Analysis"])

_ANY_ROLE = ("Admin", "Analyst", "Supervisor", "QA")
_ISSUER_ROLES = ("Admin", "QA")


@router.get("", response_model=list[COASummaryResponse])
async def list_coas(
    product_id: int | None = Query(default=None),
    batch_number: str | None = Query(default=None),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 8.1: issued certificates, newest first."""
    service = Container.get_coa_service(session)
    return await service.list_coas(product_id=product_id, batch_number=batch_number)


@router.get("/{coa_id}", response_model=COAResponse)
async def get_coa(
    coa_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 8.3, 8.4: the frozen snapshot the print page renders."""
    service = Container.get_coa_service(session)
    return await service.get(coa_id)


@router.post("/preview", response_model=COAPreviewResponse)
async def preview_coa(
    request: PreviewCOARequest,
    current_user: User = Depends(require_role(*_ISSUER_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    """
    Compile what a certificate would contain, without issuing one.

    A POST despite being read-only: the compilation is a computation over a
    product/batch pair rather than a resource with its own URL, and this keeps the
    request shape identical to `generate` minus the signature.

    Restricted to the issuer roles because it is a pre-signature review step, not
    a document anyone needs to read.
    """
    service = Container.get_coa_service(session)
    snapshot = await service.preview(request.product_id, request.batch_number)
    return COAPreviewResponse(snapshot=snapshot)


@router.post("", response_model=COAResponse)
async def generate_coa(
    request: GenerateCOARequest,
    current_user: User = Depends(require_role(*_ISSUER_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    """
    Requirement 8.1, 8.3, 8.5, 9.5: e-signed generation.

    Rejected with a 400 when the batch has no released results — a certificate
    compiled from nothing would assert that testing happened when it did not.
    """
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_coa_service(session)
    return await service.generate(
        product_id=request.product_id,
        batch_number=request.batch_number,
        actor=current_user,
        remarks=request.remarks,
    )
