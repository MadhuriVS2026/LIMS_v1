"""OOS Investigation repository implementation (Adapter)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.oos_investigation import OOSInvestigation
from src.domain.repositories.oos_repository import IOOSRepository
from src.infrastructure.database.models.oos_model import OOSInvestigationModel


class OOSRepositoryImpl(IOOSRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, oos_id: int) -> OOSInvestigation | None:
        model = await self._session.get(OOSInvestigationModel, oos_id)
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[OOSInvestigation]:
        stmt = (
            select(OOSInvestigationModel)
            .options(selectinload(OOSInvestigationModel.test))
            .order_by(OOSInvestigationModel.created_date.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_open_for_sample(self, sample_id: int) -> list[OOSInvestigation]:
        stmt = select(OOSInvestigationModel).where(
            OOSInvestigationModel.sample_id == sample_id,
            OOSInvestigationModel.status == "Open",
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def find_existing(self, sample_id: int, test_id: int) -> OOSInvestigation | None:
        stmt = select(OOSInvestigationModel).where(
            OOSInvestigationModel.sample_id == sample_id,
            OOSInvestigationModel.test_id == test_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create(self, oos: OOSInvestigation) -> OOSInvestigation:
        model = OOSInvestigationModel(
            sample_id=oos.sample_id,
            test_id=oos.test_id,
            investigation_type=oos.investigation_type,
            phase1_comments=oos.phase1_comments,
            status=oos.status,
            created_by=oos.created_by,
            modified_by=oos.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, oos: OOSInvestigation) -> OOSInvestigation:
        model = await self._session.get(OOSInvestigationModel, oos.id)
        if model is None:
            raise ValueError(f"OOSInvestigation {oos.id} not found")
        model.root_cause = oos.root_cause
        model.corrective_action = oos.corrective_action
        model.status = oos.status
        model.closed_by = oos.closed_by
        model.closed_at = oos.closed_at
        model.modified_by = oos.modified_by
        model.modified_date = oos.modified_date
        await self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: OOSInvestigationModel) -> OOSInvestigation:
        return OOSInvestigation(
            id=model.id,
            sample_id=model.sample_id,
            test_id=model.test_id,
            investigation_type=model.investigation_type,
            phase1_comments=model.phase1_comments,
            root_cause=model.root_cause,
            corrective_action=model.corrective_action,
            status=model.status,
            closed_by=model.closed_by,
            closed_at=model.closed_at,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
