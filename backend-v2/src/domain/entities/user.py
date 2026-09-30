"""
User domain entity.
Contains business logic and invariants for user management.
"""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base_entity import BaseEntity


@dataclass
class User(BaseEntity):
    """
    User aggregate root for the LIMS system.

    Business Rules:
    - Username must be unique (enforced at repository level).
    - Password hash is never exposed outside the domain/infrastructure boundary.
    - A blocked/inactive user cannot authenticate.
    - Account locks automatically after 5 failed login attempts for 30 minutes.
    """

    username: str = field(default="")
    password_hash: str = field(default="", repr=False)
    full_name: str = field(default="")
    role: str = field(default="Analyst")  # Admin, Analyst, Supervisor, QA, GL, TL, Scientist, FDGL, ADGL
    #  GL (Group Leader) & TL (Team Leader) inherit Supervisor rights; Scientist
    #  inherits Analyst rights. FDGL inherits Supervisor (FDGL TRF gate); ADGL
    #  inherits QA (ADGL TRF gate). See src/api/v1/dependencies.py
    #  ROLE_INHERITANCE (backend) and src/core/rbac/usePermissions.ts (frontend).
    email: str | None = field(default=None)
    department: str | None = field(default=None)
    is_active: bool = field(default=True)
    failed_login_attempts: int = field(default=0)
    locked_until: datetime | None = field(default=None)
    last_login: datetime | None = field(default=None)

    def can_authenticate(self) -> bool:
        """Check if the user is allowed to authenticate."""
        if not self.is_active:
            return False
        if self.locked_until and self.locked_until > datetime.now(self.locked_until.tzinfo):
            return False
        return True

    def register_failed_login(self) -> None:
        """Increment failed login counter; lock account after 5 attempts."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            from datetime import timedelta, timezone
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)

    def register_successful_login(self) -> None:
        """Reset failure counters and stamp last login."""
        from datetime import timezone
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.now(timezone.utc)

    def has_role(self, *roles: str) -> bool:
        """Check if user holds one of the given roles."""
        return self.role in roles

    def deactivate(self, deactivated_by: str) -> None:
        self.is_active = False
        self.mark_modified(deactivated_by)

    def activate(self, activated_by: str) -> None:
        self.is_active = True
        self.mark_modified(activated_by)
