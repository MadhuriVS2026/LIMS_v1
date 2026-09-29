"""User Management API endpoints (Admin only)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_role
from src.api.v1.schemas.auth_schemas import UserResponse
from src.api.v1.schemas.user_schemas import CreateUserRequest, UpdateUserRequest
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
) -> list[User]:
    service = Container.get_user_service(session)
    return await service.list_users()


@router.post("", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
) -> User:
    service = Container.get_user_service(session)
    return await service.create_user(
        request.username, request.password, request.full_name, request.role,
        request.email, request.department, current_user,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
) -> User:
    service = Container.get_user_service(session)
    return await service.update_user(
        user_id, request.full_name, request.role, request.email,
        request.department, request.is_active, current_user,
    )
