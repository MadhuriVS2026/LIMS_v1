"""Specification repository implementation (Adapter)."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.specification import Specification, SpecificationTest
from src.domain.repositories.specification_repository import ISpecificationRepository
from src.infrastructure.database.models.specification_model import (
    SpecificationModel,
    SpecificationTestModel,
)


class SpecificationRepositoryImpl(ISpecificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, spec_id: int) -> Specification | None:
        stmt = (
            select(SpecificationModel)
            .options(selectinload(SpecificationModel.tests).selectinload(SpecificationTestModel.test))
            .where(SpecificationModel.id == spec_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[Specification]:
        stmt = select(SpecificationModel).options(
            selectinload(SpecificationModel.tests).selectinload(SpecificationTestModel.test)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_product(self, product_id: int) -> list[Specification]:
        stmt = select(SpecificationModel).where(SpecificationModel.product_id == product_id)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_active_for_product(self, product_id: int) -> Specification | None:
        stmt = (
            select(SpecificationModel)
            .options(selectinload(SpecificationModel.tests).selectinload(SpecificationTestModel.test))
            .where(SpecificationModel.product_id == product_id, SpecificationModel.status == "Active")
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create(self, spec: Specification) -> Specification:
        model = SpecificationModel(
            product_id=spec.product_id,
            version=spec.version,
            spec_type=spec.spec_type,
            document_no=spec.document_no,
            status=spec.status,
            created_by=spec.created_by,
            modified_by=spec.modified_by,
        )
        self._session.add(model)
        await self._session.flush()

        for t in spec.tests:
            test_model = SpecificationTestModel(
                specification_id=model.id,
                test_id=t.test_id,
                min_limit=t.min_limit,
                max_limit=t.max_limit,
                unit=t.unit,
                expected_result=t.expected_result,
                display_in_coa=t.display_in_coa,
            )
            self._session.add(test_model)
        await self._session.flush()

        return await self.get_by_id(model.id)  # type: ignore[return-value]

    async def update(self, spec: Specification, *, replace_tests: bool = False) -> Specification:
        model = await self._session.get(SpecificationModel, spec.id)
        if model is None:
            raise ValueError(f"Specification {spec.id} not found")
        model.spec_type = spec.spec_type
        model.document_no = spec.document_no
        model.status = spec.status
        model.approved_by = spec.approved_by
        model.approved_at = spec.approved_at
        model.modified_by = spec.modified_by
        model.modified_date = spec.modified_date

        #  Only an explicit edit replaces the child test-limit rows. Lifecycle
        #  transitions (approve/deactivate) leave them untouched.
        if replace_tests:
            existing = await self._session.execute(
                select(SpecificationTestModel).where(
                    SpecificationTestModel.specification_id == model.id
                )
            )
            for row in existing.scalars().all():
                await self._session.delete(row)
            await self._session.flush()
            for t in spec.tests:
                self._session.add(SpecificationTestModel(
                    specification_id=model.id,
                    test_id=t.test_id,
                    min_limit=t.min_limit,
                    max_limit=t.max_limit,
                    unit=t.unit,
                    expected_result=t.expected_result,
                    display_in_coa=t.display_in_coa,
                ))

        await self._session.flush()
        return await self.get_by_id(spec.id)  # type: ignore[return-value]

    async def deactivate_active_for_product(self, product_id: int) -> None:
        stmt = (
            update(SpecificationModel)
            .where(SpecificationModel.product_id == product_id, SpecificationModel.status == "Active")
            .values(status="Inactive")
        )
        await self._session.execute(stmt)

    @staticmethod
    def _to_entity(model: SpecificationModel) -> Specification:
        tests = [
            SpecificationTest(
                id=t.id,
                test_id=t.test_id,
                min_limit=t.min_limit,
                max_limit=t.max_limit,
                unit=t.unit,
                expected_result=t.expected_result,
                display_in_coa=t.display_in_coa,
            )
            for t in (model.tests or [])
        ]
        return Specification(
            id=model.id,
            product_id=model.product_id,
            version=model.version,
            spec_type=model.spec_type,
            document_no=model.document_no,
            status=model.status,
            approved_by=model.approved_by,
            approved_at=model.approved_at,
            tests=tests,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
