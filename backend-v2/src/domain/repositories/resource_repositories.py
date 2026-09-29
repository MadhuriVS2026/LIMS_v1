"""Repository interfaces for Resource Manager entities (Instrument, Column, etc.)."""
from abc import ABC, abstractmethod

from src.domain.entities.instrument import Instrument
from src.domain.entities.resource_items import (
    ChemicalReagent,
    ColumnMaster,
    ReferenceStandard,
    VolumetricSolution,
)


class IInstrumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, instrument_id: int) -> Instrument | None: ...

    @abstractmethod
    async def list_all(self) -> list[Instrument]: ...

    @abstractmethod
    async def create(self, instrument: Instrument) -> Instrument: ...

    @abstractmethod
    async def update(self, instrument: Instrument) -> Instrument: ...

    @abstractmethod
    async def count_due_for_calibration(self, days: int) -> int: ...


class IColumnRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[ColumnMaster]: ...

    @abstractmethod
    async def create(self, column: ColumnMaster) -> ColumnMaster: ...


class IReferenceStandardRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[ReferenceStandard]: ...

    @abstractmethod
    async def create(self, standard: ReferenceStandard) -> ReferenceStandard: ...


class IChemicalRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[ChemicalReagent]: ...

    @abstractmethod
    async def create(self, chemical: ChemicalReagent) -> ChemicalReagent: ...


class IVolumetricSolutionRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[VolumetricSolution]: ...

    @abstractmethod
    async def create(self, solution: VolumetricSolution) -> VolumetricSolution: ...
