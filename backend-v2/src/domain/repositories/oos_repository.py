"""OOS Investigation repository interface (Port)."""
from abc import ABC, abstractmethod

from src.domain.entities.oos_investigation import OOSInvestigation


class IOOSRepository(ABC):
    @abstractmethod
    async def get_by_id(self, oos_id: int) -> OOSInvestigation | None: ...

    @abstractmethod
    async def list_all(self) -> list[OOSInvestigation]: ...

    @abstractmethod
    async def list_open_for_sample(self, sample_id: int) -> list[OOSInvestigation]: ...

    @abstractmethod
    async def find_existing(self, sample_id: int, test_id: int) -> OOSInvestigation | None: ...

    @abstractmethod
    async def create(self, oos: OOSInvestigation) -> OOSInvestigation: ...

    @abstractmethod
    async def update(self, oos: OOSInvestigation) -> OOSInvestigation: ...
