"""Product repository interface (Port)."""
from abc import ABC, abstractmethod

from src.domain.entities.product import Product


class IProductRepository(ABC):
    @abstractmethod
    async def get_by_id(self, product_id: int) -> Product | None: ...

    @abstractmethod
    async def list_all(self) -> list[Product]: ...

    @abstractmethod
    async def create(self, product: Product) -> Product: ...

    @abstractmethod
    async def update(self, product: Product) -> Product: ...

    @abstractmethod
    async def exists_by_code(self, code: str) -> bool: ...
