"""Certificate of Analysis repository implementation (Adapter)."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.certificate_of_analysis import CertificateOfAnalysis
from src.domain.repositories.coa_repository import ICOARepository
from src.infrastructure.database.models.coa_model import CertificateOfAnalysisModel


class COARepositoryImpl(ICOARepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, coa_id: int) -> CertificateOfAnalysis | None:
        stmt = (
            select(CertificateOfAnalysisModel)
            .options(selectinload(CertificateOfAnalysisModel.product))
            .where(CertificateOfAnalysisModel.id == coa_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_number(self, coa_number: str) -> CertificateOfAnalysis | None:
        stmt = (
            select(CertificateOfAnalysisModel)
            .options(selectinload(CertificateOfAnalysisModel.product))
            .where(CertificateOfAnalysisModel.coa_number == coa_number)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(
        self, product_id: int | None = None, batch_number: str | None = None
    ) -> list[CertificateOfAnalysis]:
        stmt = select(CertificateOfAnalysisModel).options(
            selectinload(CertificateOfAnalysisModel.product)
        )
        if product_id is not None:
            stmt = stmt.where(CertificateOfAnalysisModel.product_id == product_id)
        if batch_number is not None:
            stmt = stmt.where(CertificateOfAnalysisModel.batch_number == batch_number)
        #  Newest first: when a batch has been re-certified, the current
        #  certificate is the one a user wants at the top.
        stmt = stmt.order_by(CertificateOfAnalysisModel.id.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_number_prefix(self, prefix: str) -> int:
        stmt = (
            select(func.count())
            .select_from(CertificateOfAnalysisModel)
            .where(CertificateOfAnalysisModel.coa_number.like(f"{prefix}%"))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, coa: CertificateOfAnalysis) -> CertificateOfAnalysis:
        model = CertificateOfAnalysisModel(
            coa_number=coa.coa_number,
            product_id=coa.product_id,
            batch_number=coa.batch_number,
            status=coa.status,
            snapshot=coa.snapshot,
            released_by=coa.released_by,
            released_at=coa.released_at,
            created_by=coa.created_by,
            modified_by=coa.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return await self.get_by_id(model.id)  # type: ignore[return-value]

    @staticmethod
    def _to_entity(model: CertificateOfAnalysisModel) -> CertificateOfAnalysis:
        product = model.product
        return CertificateOfAnalysis(
            id=model.id,
            coa_number=model.coa_number,
            product_id=model.product_id,
            batch_number=model.batch_number,
            status=model.status,
            snapshot=model.snapshot or {},
            released_by=model.released_by,
            released_at=model.released_at,
            product_code=product.code if product else None,
            product_name=product.name if product else None,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
