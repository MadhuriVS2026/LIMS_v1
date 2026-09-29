"""Test Parameter repository interface (Port)."""
from abc import ABC, abstractmethod

from src.domain.entities.test_parameter import TestParameter


class ITestRepository(ABC):
    @abstractmethod
    async def get_by_id(self, test_id: int) -> TestParameter | None: ...

    @abstractmethod
    async def list_all(self) -> list[TestParameter]: ...

    @abstractmethod
    async def create(self, test: TestParameter) -> TestParameter: ...
