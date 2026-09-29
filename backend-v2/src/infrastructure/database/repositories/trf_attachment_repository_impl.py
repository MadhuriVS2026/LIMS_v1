"""TRF attachment repository implementation (Adapter)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.trf_attachment import TRFAttachment
from src.domain.repositories.trf_attachment_repository import ITRFAttachmentRepository
from src.infrastructure.database.models.trf_attachment_model import TRFAttachmentModel


class TRFAttachmentRepositoryImpl(ITRFAttachmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, attachment_id: int) -> TRFAttachment | None:
        stmt = (
            select(TRFAttachmentModel)
            .options(selectinload(TRFAttachmentModel.test_line))
            .where(TRFAttachmentModel.id == attachment_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_trf(self, trf_id: int) -> list[TRFAttachment]:
        stmt = (
            select(TRFAttachmentModel)
            .options(selectinload(TRFAttachmentModel.test_line))
            .where(TRFAttachmentModel.trf_id == trf_id)
            .order_by(TRFAttachmentModel.id.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_test_line(self, trf_test_line_id: int) -> list[TRFAttachment]:
        stmt = (
            select(TRFAttachmentModel)
            .options(selectinload(TRFAttachmentModel.test_line))
            .where(TRFAttachmentModel.trf_test_line_id == trf_test_line_id)
            .order_by(TRFAttachmentModel.id.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, attachment: TRFAttachment) -> TRFAttachment:
        model = TRFAttachmentModel(
            trf_id=attachment.trf_id,
            trf_test_line_id=attachment.trf_test_line_id,
            original_filename=attachment.original_filename,
            storage_name=attachment.storage_name,
            content_type=attachment.content_type,
            size_bytes=attachment.size_bytes,
            checksum_sha256=attachment.checksum_sha256,
            description=attachment.description,
            uploaded_by=attachment.uploaded_by,
            uploaded_at=attachment.uploaded_at,
            created_by=attachment.created_by,
            modified_by=attachment.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return await self.get_by_id(model.id)  # type: ignore[return-value]

    async def delete(self, attachment_id: int) -> None:
        model = await self._session.get(TRFAttachmentModel, attachment_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    @staticmethod
    def _to_entity(model: TRFAttachmentModel) -> TRFAttachment:
        return TRFAttachment(
            id=model.id,
            trf_id=model.trf_id,
            trf_test_line_id=model.trf_test_line_id,
            original_filename=model.original_filename,
            storage_name=model.storage_name,
            content_type=model.content_type,
            size_bytes=model.size_bytes,
            checksum_sha256=model.checksum_sha256,
            description=model.description,
            uploaded_by=model.uploaded_by,
            uploaded_at=model.uploaded_at,
            test_line_no=model.test_line.line_no if model.test_line else None,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
