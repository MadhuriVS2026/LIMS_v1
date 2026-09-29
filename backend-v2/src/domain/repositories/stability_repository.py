"""Stability Management repository interface (Port)."""
from abc import ABC, abstractmethod

from src.domain.entities.stability import (
    StabilityMatrixCell,
    StabilityProtocol,
    StabilityReport,
    StabilitySample,
)


class IStabilityRepository(ABC):
    # ── Protocol ──
    @abstractmethod
    async def get_protocol_by_id(self, protocol_id: int) -> StabilityProtocol | None: ...

    @abstractmethod
    async def list_protocols(self) -> list[StabilityProtocol]: ...

    @abstractmethod
    async def create_protocol(self, protocol: StabilityProtocol) -> StabilityProtocol: ...

    @abstractmethod
    async def update_protocol(self, protocol: StabilityProtocol) -> StabilityProtocol: ...

    @abstractmethod
    async def count_protocols(self) -> int: ...

    # ── Loading Matrix ──
    @abstractmethod
    async def list_matrix_cells(self, protocol_id: int) -> list[StabilityMatrixCell]: ...

    @abstractmethod
    async def upsert_matrix_cell(self, cell: StabilityMatrixCell) -> StabilityMatrixCell: ...

    @abstractmethod
    async def get_matrix_cell_by_natural_key(
        self, protocol_id: int, condition: str, time_point_days: int | None, is_reserve: bool
    ) -> StabilityMatrixCell | None: ...

    @abstractmethod
    async def get_matrix_cell_by_id(self, cell_id: int) -> StabilityMatrixCell | None: ...

    # ── Time-point samples ──
    @abstractmethod
    async def list_samples(self, protocol_id: int) -> list[StabilitySample]: ...

    @abstractmethod
    async def get_sample_by_id(self, sample_id: int) -> StabilitySample | None: ...

    @abstractmethod
    async def create_sample(self, sample: StabilitySample) -> StabilitySample: ...

    @abstractmethod
    async def update_sample(self, sample: StabilitySample) -> StabilitySample: ...

    @abstractmethod
    async def exists_sample_for_cell(
        self, protocol_id: int, batch_number: str, matrix_cell_id: int
    ) -> bool: ...

    # ── Reports ──
    @abstractmethod
    async def list_reports(self, protocol_id: int) -> list[StabilityReport]: ...

    @abstractmethod
    async def get_report_by_id(self, report_id: int) -> StabilityReport | None: ...

    @abstractmethod
    async def get_latest_signed_report(self, protocol_id: int) -> StabilityReport | None: ...

    @abstractmethod
    async def get_latest_draft_report(self, protocol_id: int) -> StabilityReport | None: ...

    @abstractmethod
    async def create_report(self, report: StabilityReport) -> StabilityReport: ...

    @abstractmethod
    async def update_report(self, report: StabilityReport) -> StabilityReport: ...

    @abstractmethod
    async def count_reports(self) -> int: ...
