"""
User Application Service.
Orchestrates user CRUD, activation, and password changes.
"""
from src.application.exceptions.application_exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.user_repository import IUserRepository
from src.infrastructure.security.password_encoder import hash_password, verify_password


class UserService:
    """Application service for user management."""

    def __init__(self, user_repo: IUserRepository, audit_repo: IAuditLogRepository) -> None:
        self._user_repo = user_repo
        self._audit_repo = audit_repo

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return await self._user_repo.list_all(skip, limit)

    async def create_user(
        self,
        username: str,
        password: str,
        full_name: str,
        role: str,
        email: str | None,
        department: str | None,
        actor: User,
    ) -> User:
        if await self._user_repo.exists_by_username(username):
            raise ConflictException(f"Username '{username}' already exists")

        user = User(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            email=email,
            department=department,
            is_active=True,
            created_by=actor.username,
            modified_by=actor.username,
        )
        created = await self._user_repo.create(user)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="CREATE",
                table_name="users",
                record_id=created.id,
                new_values={"username": created.username, "role": created.role},
            )
        )
        return created

    async def update_user(
        self,
        user_id: int,
        full_name: str | None,
        role: str | None,
        email: str | None,
        department: str | None,
        is_active: bool | None,
        actor: User,
    ) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundException("User not found")

        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if email is not None:
            user.email = email
        if department is not None:
            user.department = department
        if is_active is not None:
            user.is_active = is_active

        user.mark_modified(actor.username)
        updated = await self._user_repo.update(user)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="UPDATE",
                table_name="users",
                record_id=updated.id,
            )
        )
        return updated

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedException("Current password is incorrect")

        user.password_hash = hash_password(new_password)
        user.mark_modified(user.username)
        await self._user_repo.update(user)
