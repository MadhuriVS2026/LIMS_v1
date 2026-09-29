"""Audit Log & SAP Integration Log repository interfaces (Ports)."""
from abc import ABC, abstractmethod

from src.domain.entities.audit_log import AuditLog, SAPIntegrationLog, SAPReceivedLot


class IAuditLogRepository(ABC):
    @abstractmethod
    async def write(self, entry: AuditLog) -> AuditLog: ...

    @abstractmethod
    async def list_recent(self, skip: int = 0, limit: int = 100) -> list[AuditLog]: ...


class ISAPIntegrationLogRepository(ABC):
    @abstractmethod
    async def write(self, entry: SAPIntegrationLog) -> SAPIntegrationLog: ...

    @abstractmethod
    async def list_recent(self, limit: int = 100) -> list[SAPIntegrationLog]: ...


class ISAPReceivedLotRepository(ABC):
    @abstractmethod
    async def upsert(self, lot: SAPReceivedLot) -> SAPReceivedLot: ...

    @abstractmethod
    async def list_recent(self, limit: int = 100) -> list[SAPReceivedLot]: ...

    @abstractmethod
    async def get_by_inspection_lot(self, inspection_lot: str) -> SAPReceivedLot | None: ...

    @abstractmethod
    async def mark_consumed(self, inspection_lot: str, sample_id: int) -> None: ...
