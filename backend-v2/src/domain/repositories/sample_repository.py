"""Sample & SampleResult repository interfaces (Ports)."""
from abc import ABC, abstractmethod

from src.domain.entities.sample import Sample, SampleResult


class ISampleRepository(ABC):
    @abstractmethod
    async def get_by_id(self, sample_id: int) -> Sample | None: ...

    @abstractmethod
    async def list_all(self, status: str | None = None) -> list[Sample]: ...

    @abstractmethod
    async def create(self, sample: Sample) -> Sample: ...

    @abstractmethod
    async def update(self, sample: Sample) -> Sample: ...

    @abstractmethod
    async def count_by_code_prefix(self, prefix: str) -> int: ...

    @abstractmethod
    async def get_result_by_id(self, result_id: int) -> SampleResult | None: ...

    @abstractmethod
    async def update_result(self, result: SampleResult) -> SampleResult: ...
