"""OOS Investigation API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user, get_session, require_role
from src.api.v1.schemas.oos_schemas import CloseOOSRequest, OOSResponse
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/oos", tags=["OOS Investigations"])


@router.get("", response_model=list[OOSResponse])
async def list_oos(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_oos_service(session)
    return await service.list_oos()


@router.post("/{oos_id}/close", response_model=OOSResponse)
async def close_oos(
    oos_id: int,
    request: CloseOOSRequest,
    current_user: User = Depends(require_role("Supervisor", "QA")),
    session: AsyncSession = Depends(get_session),
):
    """Close an OOS investigation with root cause + CAPA (E-Signed)."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_oos_service(session)
    return await service.close_oos(oos_id, request.root_cause, request.corrective_action, current_user)
