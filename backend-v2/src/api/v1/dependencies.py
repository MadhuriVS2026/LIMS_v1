"""
FastAPI dependency providers: DB session, current user, role guards.
"""
from collections.abc import AsyncGenerator, Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.dependency_injection import Container
from src.domain.entities.user import User
from src.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
from src.infrastructure.database.session import get_db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

#  Role hierarchy: new organizational roles inherit the rights of a base role.
#  GL (Group Leader) and TL (Team Leader) carry the same authority as a
#  Supervisor; Scientist is an initiator/user equivalent to an Analyst. A role
#  always satisfies itself; the entries below add the inherited base role.
#  Enforcement everywhere calls require_role(<base roles>), so expanding a
#  user's role to its effective set here means every existing guard keeps
#  working without being edited. The user's real role name is preserved for
#  display and the audit trail.
ROLE_INHERITANCE: dict[str, tuple[str, ...]] = {
    "GL": ("Supervisor",),
    "TL": ("Supervisor",),
    "Scientist": ("Analyst",),
}


def effective_roles(role: str) -> set[str]:
    """Return the set of roles a user effectively holds (self + inherited)."""
    return {role, *ROLE_INHERITANCE.get(role, ())}


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Decode the JWT and load the current User entity."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        jwt_provider = Container.get_jwt_provider()
        payload = jwt_provider.verify_token(token)
    except jwt.PyJWTError:
        raise credentials_exception

    user_repo = UserRepositoryImpl(session)
    user = await user_repo.get_by_id(payload.user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


def require_role(*roles: str) -> Callable:
    """Dependency factory: restrict endpoint access to specific roles."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if effective_roles(current_user.role).isdisjoint(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires one of the following roles: {', '.join(roles)}",
            )
        return current_user

    return role_checker
