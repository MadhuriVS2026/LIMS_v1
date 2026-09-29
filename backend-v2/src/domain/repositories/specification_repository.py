"""Specification repository interface (Port)."""
from abc import ABC, abstractmethod

from src.domain.entities.specification import Specification


class ISpecificationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, spec_id: int) -> Specification | None: ...

    @abstractmethod
    async def list_all(self) -> list[Specification]: ...

    @abstractmethod
    async def list_by_product(self, product_id: int) -> list[Specification]: ...

    @abstractmethod
    async def get_active_for_product(self, product_id: int) -> Specification | None: ...

    @abstractmethod
    async def create(self, spec: Specification) -> Specification: ...

    @abstractmethod
    async def update(self, spec: Specification, *, replace_tests: bool = False) -> Specification: ...

    @abstractmethod
    async def deactivate_active_for_product(self, product_id: int) -> None: ...
