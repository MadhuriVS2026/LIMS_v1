"""TRF attachment repository interface (Port)."""
from abc import ABC, abstractmethod

from src.domain.entities.trf_attachment import TRFAttachment


class ITRFAttachmentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, attachment_id: int) -> TRFAttachment | None: ...

    @abstractmethod
    async def list_by_trf(self, trf_id: int) -> list[TRFAttachment]:
        """Every attachment on a TRF, newest first."""

    @abstractmethod
    async def list_by_test_line(self, trf_test_line_id: int) -> list[TRFAttachment]:
        """Attachments scoped to one test line — used by COA compilation."""

    @abstractmethod
    async def create(self, attachment: TRFAttachment) -> TRFAttachment: ...

    @abstractmethod
    async def delete(self, attachment_id: int) -> None:
        """Remove the metadata row. The caller removes the stored bytes."""
