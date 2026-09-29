"""Sample Result recording API endpoints — submission & supervisor review."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_role
from src.api.v1.schemas.auth_schemas import ESignRequest
from src.api.v1.schemas.sample_schemas import SampleResultResponse, SubmitResultRequest
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/results", tags=["Results"])


@router.post("/{result_id}/submit", response_model=SampleResultResponse)
async def submit_result(
    result_id: int,
    request: SubmitResultRequest,
    current_user: User = Depends(require_role("Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Analyst submits a test result (E-Signed). Auto-evaluates OOS per domain rules."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_sample_service(session)
    return await service.submit_result(
        result_id, request.result_value, request.result_text, current_user, request.comments
    )


@router.post("/{result_id}/review", response_model=SampleResultResponse)
async def review_result(
    result_id: int,
    esign: ESignRequest,
    current_user: User = Depends(require_role("Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Supervisor reviews & approves a submitted result (E-Signed)."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, esign.password)

    service = Container.get_sample_service(session)
    return await service.review_result(result_id, current_user, esign.comments)
