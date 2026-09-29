"""Test Template / Test Worksheet repository interfaces (Ports)."""
from abc import ABC, abstractmethod

from src.domain.entities.test_template import TestTemplate, TestWorksheet


class ITestTemplateRepository(ABC):
    @abstractmethod
    async def get_by_id(self, template_id: int) -> TestTemplate | None: ...

    @abstractmethod
    async def list_all(
        self, test_id: int | None = None, status: str | None = None
    ) -> list[TestTemplate]: ...

    @abstractmethod
    async def list_active_for_test(self, test_id: int) -> list[TestTemplate]:
        """Templates selectable on a TRF test line for the given Test."""

    @abstractmethod
    async def get_by_code_and_version(self, code: str, version: int) -> TestTemplate | None: ...

    @abstractmethod
    async def list_versions_of(self, code: str) -> list[TestTemplate]:
        """Every version sharing a template code, newest first."""

    @abstractmethod
    async def count_by_code_prefix(self, prefix: str) -> int:
        """Distinct template codes matching a prefix — drives code generation."""

    @abstractmethod
    async def create(self, template: TestTemplate) -> TestTemplate: ...

    @abstractmethod
    async def update(self, template: TestTemplate) -> TestTemplate: ...


class ITestWorksheetRepository(ABC):
    @abstractmethod
    async def get_by_id(self, worksheet_id: int) -> TestWorksheet | None: ...

    @abstractmethod
    async def get_by_test_line(self, trf_test_line_id: int) -> TestWorksheet | None:
        """At most one worksheet per TRF test line."""

    @abstractmethod
    async def list_by_trf(self, trf_id: int) -> list[TestWorksheet]:
        """Every worksheet across a TRF's test lines — used by COA compilation."""

    @abstractmethod
    async def create(self, worksheet: TestWorksheet) -> TestWorksheet: ...

    @abstractmethod
    async def update(self, worksheet: TestWorksheet) -> TestWorksheet: ...
