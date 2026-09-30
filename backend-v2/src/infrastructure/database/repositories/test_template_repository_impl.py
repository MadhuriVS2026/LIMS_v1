"""Test template / worksheet repository implementations (Adapters)."""
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.test_template import TestTemplate, TestWorksheet
from src.domain.repositories.test_template_repository import (
    ITestTemplateRepository,
    ITestWorksheetRepository,
)
from src.infrastructure.database.models.test_model import TestModel
from src.infrastructure.database.models.test_template_model import (
    TestTemplateModel,
    TestWorksheetModel,
)
from src.infrastructure.database.models.trf_model import TRFTestLineModel


class TestTemplateRepositoryImpl(ITestTemplateRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, template_id: int) -> TestTemplate | None:
        stmt = (
            select(TestTemplateModel)
            .options(selectinload(TestTemplateModel.test))
            .where(TestTemplateModel.id == template_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(
        self, test_id: int | None = None, status: str | None = None
    ) -> list[TestTemplate]:
        stmt = select(TestTemplateModel).options(selectinload(TestTemplateModel.test))
        if test_id is not None:
            stmt = stmt.where(TestTemplateModel.test_id == test_id)
        if status is not None:
            stmt = stmt.where(TestTemplateModel.status == status)
        stmt = stmt.order_by(
            TestTemplateModel.code.asc(), TestTemplateModel.version.desc()
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_active_for_test(self, test_id: int) -> list[TestTemplate]:
        return await self.list_all(test_id=test_id, status="Active")

    async def get_by_code_and_version(self, code: str, version: int) -> TestTemplate | None:
        stmt = (
            select(TestTemplateModel)
            .options(selectinload(TestTemplateModel.test))
            .where(TestTemplateModel.code == code, TestTemplateModel.version == version)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_versions_of(self, code: str) -> list[TestTemplate]:
        stmt = (
            select(TestTemplateModel)
            .options(selectinload(TestTemplateModel.test))
            .where(TestTemplateModel.code == code)
            .order_by(TestTemplateModel.version.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_code_prefix(self, prefix: str) -> int:
        """
        Counts DISTINCT codes, not rows — versions of one template share a code,
        so counting rows would skip sequence numbers as templates get versioned.
        """
        stmt = (
            select(func.count(distinct(TestTemplateModel.code)))
            .select_from(TestTemplateModel)
            .where(TestTemplateModel.code.like(f"{prefix}%"))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, template: TestTemplate) -> TestTemplate:
        model = TestTemplateModel(
            code=template.code,
            name=template.name,
            archetype=template.archetype,
            test_id=template.test_id,
            version=template.version,
            status=template.status,
            result_unit=template.result_unit,
            definition=template.definition,
            approved_by=template.approved_by,
            approved_at=template.approved_at,
            superseded_by_id=template.superseded_by_id,
            created_by=template.created_by,
            modified_by=template.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return await self.get_by_id(model.id)  # type: ignore[return-value]

    async def update(self, template: TestTemplate) -> TestTemplate:
        model = await self._session.get(TestTemplateModel, template.id)
        if model is None:
            raise ValueError(f"TestTemplate {template.id} not found")
        model.name = template.name
        model.result_unit = template.result_unit
        model.status = template.status
        model.definition = template.definition
        model.approved_by = template.approved_by
        model.approved_at = template.approved_at
        model.superseded_by_id = template.superseded_by_id
        model.modified_by = template.modified_by
        model.modified_date = template.modified_date
        await self._session.flush()
        return await self.get_by_id(template.id)  # type: ignore[return-value]

    @staticmethod
    def _to_entity(model: TestTemplateModel) -> TestTemplate:
        test: TestModel | None = model.test
        return TestTemplate(
            id=model.id,
            code=model.code,
            name=model.name,
            archetype=model.archetype,
            test_id=model.test_id,
            version=model.version,
            status=model.status,
            result_unit=model.result_unit,
            definition=model.definition or {},
            approved_by=model.approved_by,
            approved_at=model.approved_at,
            superseded_by_id=model.superseded_by_id,
            test_code=test.code if test else None,
            test_name=test.name if test else None,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )


class TestWorksheetRepositoryImpl(ITestWorksheetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, worksheet_id: int) -> TestWorksheet | None:
        stmt = (
            select(TestWorksheetModel)
            .options(selectinload(TestWorksheetModel.template))
            .where(TestWorksheetModel.id == worksheet_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_test_line(self, trf_test_line_id: int) -> TestWorksheet | None:
        stmt = (
            select(TestWorksheetModel)
            .options(selectinload(TestWorksheetModel.template))
            .where(TestWorksheetModel.trf_test_line_id == trf_test_line_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_trf(self, trf_id: int) -> list[TestWorksheet]:
        stmt = (
            select(TestWorksheetModel)
            .options(selectinload(TestWorksheetModel.template))
            .join(TRFTestLineModel, TestWorksheetModel.trf_test_line_id == TRFTestLineModel.id)
            .where(TRFTestLineModel.trf_id == trf_id)
            .order_by(TRFTestLineModel.line_no.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, worksheet: TestWorksheet) -> TestWorksheet:
        model = TestWorksheetModel(
            trf_test_line_id=worksheet.trf_test_line_id,
            template_id=worksheet.template_id,
            template_version=worksheet.template_version,
            status=worksheet.status,
            context_values=worksheet.context_values,
            group_values=worksheet.group_values,
            computed_snapshot=worksheet.computed_snapshot,
            reportable_result=worksheet.reportable_result,
            created_by=worksheet.created_by,
            modified_by=worksheet.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return await self.get_by_id(model.id)  # type: ignore[return-value]

    async def update(self, worksheet: TestWorksheet) -> TestWorksheet:
        model = await self._session.get(TestWorksheetModel, worksheet.id)
        if model is None:
            raise ValueError(f"TestWorksheet {worksheet.id} not found")
        model.status = worksheet.status
        model.context_values = worksheet.context_values
        model.group_values = worksheet.group_values
        model.computed_snapshot = worksheet.computed_snapshot
        model.reportable_result = worksheet.reportable_result
        model.confirmed_by = worksheet.confirmed_by
        model.confirmed_at = worksheet.confirmed_at
        model.submitted_for_review_by = worksheet.submitted_for_review_by
        model.submitted_for_review_at = worksheet.submitted_for_review_at
        model.submission_comments = worksheet.submission_comments
        model.reviewed_by = worksheet.reviewed_by
        model.reviewed_at = worksheet.reviewed_at
        model.review_comments = worksheet.review_comments
        model.modified_by = worksheet.modified_by
        model.modified_date = worksheet.modified_date
        await self._session.flush()
        return await self.get_by_id(worksheet.id)  # type: ignore[return-value]

    @staticmethod
    def _to_entity(model: TestWorksheetModel) -> TestWorksheet:
        template: TestTemplateModel | None = model.template
        return TestWorksheet(
            id=model.id,
            trf_test_line_id=model.trf_test_line_id,
            template_id=model.template_id,
            template_version=model.template_version,
            status=model.status,
            context_values=model.context_values or {},
            group_values=model.group_values or {},
            computed_snapshot=model.computed_snapshot,
            reportable_result=model.reportable_result,
            confirmed_by=model.confirmed_by,
            confirmed_at=model.confirmed_at,
            submitted_for_review_by=model.submitted_for_review_by,
            submitted_for_review_at=model.submitted_for_review_at,
            submission_comments=model.submission_comments,
            reviewed_by=model.reviewed_by,
            reviewed_at=model.reviewed_at,
            review_comments=model.review_comments,
            template_code=template.code if template else None,
            template_name=template.name if template else None,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
