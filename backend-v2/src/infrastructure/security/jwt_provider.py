"""
JWT token creation, validation, and decoding.
Handles access tokens with role claim for RBAC checks.
"""
from datetime import datetime, timedelta, timezone

import jwt

from src.config.settings import settings


class TokenPayload:
    """Decoded JWT token payload."""

    def __init__(self, sub: str, user_id: int, role: str, iat: datetime, exp: datetime) -> None:
        self.sub = sub
        self.user_id = user_id
        self.role = role
        self.iat = iat
        self.exp = exp


class JWTProvider:
    """Handles JWT token lifecycle: creation, verification, and decoding."""

    def __init__(self) -> None:
        self._secret_key = settings.JWT_SECRET_KEY
        self._algorithm = settings.JWT_ALGORITHM
        self._access_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def create_access_token(self, username: str, user_id: int, role: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": username,
            "user_id": user_id,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=self._access_expire_minutes),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify_token(self, token: str) -> TokenPayload:
        payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        return TokenPayload(
            sub=payload["sub"],
            user_id=payload["user_id"],
            role=payload.get("role", ""),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
