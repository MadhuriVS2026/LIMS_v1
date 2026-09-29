"""Specification Master Data API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user, get_session, require_role
from src.api.v1.schemas.auth_schemas import ESignRequest
from src.api.v1.schemas.specification_schemas import (
    CreateSpecificationRequest,
    SpecificationResponse,
)
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/specifications", tags=["Specifications"])


@router.get("", response_model=list[SpecificationResponse])
async def list_specifications(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_specification_service(session)
    return await service.list_specifications()


@router.post("", response_model=SpecificationResponse)
async def create_specification(
    request: CreateSpecificationRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_specification_service(session)
    return await service.create_specification(
        request.product_id, request.spec_type, request.document_no,
        [t.model_dump() for t in request.tests], current_user,
    )


@router.post("/{spec_id}/approve", response_model=SpecificationResponse)
async def approve_specification(
    spec_id: int,
    esign: ESignRequest,
    current_user: User = Depends(require_role("Supervisor", "QA")),
    session: AsyncSession = Depends(get_session),
):
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, esign.password)

    service = Container.get_specification_service(session)
    return await service.approve_specification(spec_id, current_user, esign.comments)
