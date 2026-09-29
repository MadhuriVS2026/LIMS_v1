"""Certificate of Analysis repository interface (Port)."""
from abc import ABC, abstractmethod

from src.domain.entities.certificate_of_analysis import CertificateOfAnalysis


class ICOARepository(ABC):
    @abstractmethod
    async def get_by_id(self, coa_id: int) -> CertificateOfAnalysis | None: ...

    @abstractmethod
    async def get_by_number(self, coa_number: str) -> CertificateOfAnalysis | None: ...

    @abstractmethod
    async def list_all(
        self, product_id: int | None = None, batch_number: str | None = None
    ) -> list[CertificateOfAnalysis]:
        """Certificates, newest first, optionally narrowed to a product and/or batch."""

    @abstractmethod
    async def count_by_number_prefix(self, prefix: str) -> int:
        """Drives the daily-resetting sequence in the COA number."""

    @abstractmethod
    async def create(self, coa: CertificateOfAnalysis) -> CertificateOfAnalysis: ...

    #  Deliberately no `update` and no `delete`. A certificate is issued once and
    #  never revised — a correction is a new COA that supersedes it. Omitting the
    #  methods means immutability is not merely a rule someone must remember.
