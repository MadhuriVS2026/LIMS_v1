"""Test Parameter repository implementation (Adapter)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.test_parameter import TestParameter
from src.domain.repositories.test_repository import ITestRepository
from src.infrastructure.database.models.test_model import TestModel


class TestRepositoryImpl(ITestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, test_id: int) -> TestParameter | None:
        model = await self._session.get(TestModel, test_id)
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[TestParameter]:
        result = await self._session.execute(select(TestModel))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, test: TestParameter) -> TestParameter:
        model = TestModel(
            code=test.code,
            name=test.name,
            type=test.type,
            unit=test.unit,
            method_no=test.method_no,
            category=test.category,
            technique=test.technique,
            status=test.status,
            created_by=test.created_by,
            modified_by=test.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: TestModel) -> TestParameter:
        return TestParameter(
            id=model.id,
            code=model.code,
            name=model.name,
            type=model.type,
            unit=model.unit,
            method_no=model.method_no,
            category=model.category,
            technique=model.technique,
            status=model.status,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
