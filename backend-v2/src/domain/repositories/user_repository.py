"""User repository interface (Port)."""
from abc import ABC, abstractmethod

from src.domain.entities.user import User


class IUserRepository(ABC):
    """Abstract repository for User aggregate persistence."""

    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None: ...

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]: ...

    @abstractmethod
    async def exists_by_username(self, username: str) -> bool: ...
