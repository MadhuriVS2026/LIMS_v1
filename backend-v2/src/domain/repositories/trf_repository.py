"""TRF — Test Request Form repository interface (Port)."""
from abc import ABC, abstractmethod

from src.domain.entities.trf import TestRequestForm, TRFTestLine


class ITRFRepository(ABC):
    @abstractmethod
    async def get_by_id(self, trf_id: int) -> TestRequestForm | None: ...

    @abstractmethod
    async def list_all(self) -> list[TestRequestForm]: ...

    @abstractmethod
    async def list_released_for_batch(
        self, product_id: int, batch_number: str
    ) -> list[TestRequestForm]:
        """
        Released TRFs for one product/batch, oldest first — the input to COA
        compilation. A dedicated query rather than filtering `list_all()`, since
        this runs on every COA generation and would otherwise load every TRF in
        the system to find a handful.
        """

    @abstractmethod
    async def create(self, trf: TestRequestForm) -> TestRequestForm: ...

    @abstractmethod
    async def update(self, trf: TestRequestForm) -> TestRequestForm: ...

    @abstractmethod
    async def count_by_number_prefix(self, prefix: str) -> int: ...

    @abstractmethod
    async def count_ar_by_number_prefix(self, prefix: str) -> int: ...

    @abstractmethod
    async def add_test_line(self, trf_id: int, line: TRFTestLine) -> TRFTestLine: ...

    @abstractmethod
    async def remove_test_line(self, trf_id: int, line_id: int) -> None: ...

    @abstractmethod
    async def update_test_line(self, line: TRFTestLine) -> TRFTestLine: ...

    @abstractmethod
    async def get_test_line_by_id(self, line_id: int) -> TRFTestLine | None: ...
