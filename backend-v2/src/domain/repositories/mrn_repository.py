"""MRN — Material Requisition & Consumption repository interfaces (Ports)."""
from abc import ABC, abstractmethod

from src.domain.entities.mrn import (
    ConsumptionPosting,
    MaterialRequisition,
    MRNLineItem,
    MRNMaterialLot,
)


class IMRNMaterialLotRepository(ABC):
    @abstractmethod
    async def get_by_id(self, lot_id: int) -> MRNMaterialLot | None: ...

    @abstractmethod
    async def get_by_natural_key(self, grn_document_no: str, grn_item_no: str) -> MRNMaterialLot | None: ...

    @abstractmethod
    async def upsert(self, lot: MRNMaterialLot) -> MRNMaterialLot: ...

    @abstractmethod
    async def update(self, lot: MRNMaterialLot) -> MRNMaterialLot: ...

    @abstractmethod
    async def list_available(self) -> list[MRNMaterialLot]: ...

    @abstractmethod
    async def list_all(self) -> list[MRNMaterialLot]: ...


class IMaterialRequisitionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, mrn_id: int) -> MaterialRequisition | None: ...

    @abstractmethod
    async def list_all(self) -> list[MaterialRequisition]: ...

    @abstractmethod
    async def create(self, mrn: MaterialRequisition) -> MaterialRequisition: ...

    @abstractmethod
    async def update(self, mrn: MaterialRequisition) -> MaterialRequisition: ...

    @abstractmethod
    async def add_line_item(self, mrn_id: int, item: MRNLineItem) -> MRNLineItem: ...

    @abstractmethod
    async def remove_line_item(self, mrn_id: int, line_item_id: int) -> None: ...

    @abstractmethod
    async def update_line_item(self, item: MRNLineItem) -> MRNLineItem: ...

    @abstractmethod
    async def get_line_item_by_id(self, line_item_id: int) -> MRNLineItem | None: ...

    @abstractmethod
    async def count_by_number_prefix(self, prefix: str) -> int: ...


class IConsumptionPostingRepository(ABC):
    @abstractmethod
    async def create(self, posting: ConsumptionPosting) -> ConsumptionPosting: ...

    @abstractmethod
    async def update(self, posting: ConsumptionPosting) -> ConsumptionPosting: ...

    @abstractmethod
    async def get_by_id(self, posting_id: int) -> ConsumptionPosting | None: ...

    @abstractmethod
    async def get_by_idempotency_key(self, idempotency_key: str) -> ConsumptionPosting | None: ...

    @abstractmethod
    async def list_by_mrn(self, mrn_id: int) -> list[ConsumptionPosting]: ...
