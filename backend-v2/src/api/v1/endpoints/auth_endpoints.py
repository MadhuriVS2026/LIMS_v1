"""Authentication API endpoints."""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user, get_session
from src.api.v1.schemas.auth_schemas import (
    PasswordChangeRequest,
    TokenResponse,
    UserResponse,
)
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate and receive a JWT access token. 8-hour expiry for lab shifts."""
    auth_service = Container.get_auth_service(session)
    token, _ = await auth_service.login(form_data.username, form_data.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get the currently authenticated user's profile."""
    return current_user


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Change the current user's password."""
    user_service = Container.get_user_service(session)
    await user_service.change_password(current_user, request.current_password, request.new_password)
    return {"message": "Password changed successfully"}
