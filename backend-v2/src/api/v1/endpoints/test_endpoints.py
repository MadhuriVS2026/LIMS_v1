"""Test Parameter Master Data API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user, get_session, require_role
from src.api.v1.schemas.test_schemas import CreateTestRequest, TestResponse
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/tests", tags=["Test Parameters"])


@router.get("", response_model=list[TestResponse])
async def list_tests(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_test_service(session)
    return await service.list_tests()


@router.post("", response_model=TestResponse)
async def create_test(
    request: CreateTestRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_test_service(session)
    return await service.create_test(
        request.code, request.name, request.type, request.unit,
        request.method_no, request.category, request.technique, current_user,
    )
