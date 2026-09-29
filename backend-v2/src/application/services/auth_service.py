"""
Authentication Application Service.
Orchestrates login, account lockout, and E-Signature verification.
"""
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import (
    LockedException,
    UnauthorizedException,
)
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.user_repository import IUserRepository
from src.infrastructure.security.jwt_provider import JWTProvider
from src.infrastructure.security.password_encoder import verify_password


class AuthService:
    """Handles authentication, account lockout, and E-Signature checks."""

    def __init__(
        self,
        user_repo: IUserRepository,
        audit_repo: IAuditLogRepository,
        jwt_provider: JWTProvider,
    ) -> None:
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._jwt_provider = jwt_provider

    async def login(self, username: str, password: str) -> tuple[str, User]:
        """
        Authenticate a user and issue a JWT access token.
        Enforces account lockout after 5 failed attempts (30 minute lock).
        """
        user = await self._user_repo.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            if user:
                user.register_failed_login()
                await self._user_repo.update(user)
            raise UnauthorizedException("Incorrect username or password")

        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise LockedException("Account locked. Try again later.")

        user.register_successful_login()
        await self._user_repo.update(user)

        token = self._jwt_provider.create_access_token(user.username, user.id, user.role)

        await self._audit_repo.write(
            AuditLog(
                user_id=user.id,
                username=user.username,
                action="LOGIN",
                table_name="users",
                record_id=user.id,
                comments="User logged in successfully",
            )
        )
        return token, user

    async def verify_esignature(self, user: User, password: str) -> None:
        """
        Re-verify a user's password for an electronic signature action
        (21 CFR Part 11 requirement for approvals, releases, result submissions).
        """
        if not verify_password(password, user.password_hash):
            from src.domain.exceptions.domain_exceptions import ESignatureVerificationError
            raise ESignatureVerificationError(
                "Electronic signature verification failed: Invalid password."
            )
