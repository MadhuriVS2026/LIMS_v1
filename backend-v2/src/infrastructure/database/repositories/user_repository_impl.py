"""User repository implementation (Adapter) using SQLAlchemy async."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User
from src.domain.repositories.user_repository import IUserRepository
from src.infrastructure.database.models.user_model import UserModel


class UserRepositoryImpl(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create(self, user: User) -> User:
        model = UserModel(
            username=user.username,
            password_hash=user.password_hash,
            full_name=user.full_name,
            role=user.role,
            email=user.email,
            department=user.department,
            is_active=user.is_active,
            created_by=user.created_by,
            modified_by=user.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, user: User) -> User:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            raise ValueError(f"User with id {user.id} not found")
        model.full_name = user.full_name
        model.role = user.role
        model.email = user.email
        model.department = user.department
        model.is_active = user.is_active
        model.failed_login_attempts = user.failed_login_attempts
        model.locked_until = user.locked_until
        model.last_login = user.last_login
        model.password_hash = user.password_hash
        model.modified_by = user.modified_by
        model.modified_date = user.modified_date
        await self._session.flush()
        return self._to_entity(model)

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        stmt = select(UserModel).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def exists_by_username(self, username: str) -> bool:
        stmt = select(UserModel.id).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            username=model.username,
            password_hash=model.password_hash,
            full_name=model.full_name,
            role=model.role,
            email=model.email,
            department=model.department,
            is_active=model.is_active,
            failed_login_attempts=model.failed_login_attempts,
            locked_until=model.locked_until,
            last_login=model.last_login,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
