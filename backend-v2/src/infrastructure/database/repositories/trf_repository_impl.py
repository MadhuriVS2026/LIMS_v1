"""TRF — Test Request Form repository implementation (Adapter)."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.trf import TestRequestForm, TRFTestLine
from src.domain.repositories.trf_repository import ITRFRepository
from src.infrastructure.database.models.test_model import TestModel
from src.infrastructure.database.models.trf_model import TestRequestFormModel, TRFTestLineModel


class TRFRepositoryImpl(ITRFRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, trf_id: int) -> TestRequestForm | None:
        stmt = (
            select(TestRequestFormModel)
            .options(selectinload(TestRequestFormModel.test_lines).selectinload(TRFTestLineModel.test))
            .where(TestRequestFormModel.id == trf_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[TestRequestForm]:
        stmt = (
            select(TestRequestFormModel)
            .options(selectinload(TestRequestFormModel.test_lines).selectinload(TRFTestLineModel.test))
            .order_by(TestRequestFormModel.created_date.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_released_for_batch(
        self, product_id: int, batch_number: str
    ) -> list[TestRequestForm]:
        stmt = (
            select(TestRequestFormModel)
            .options(selectinload(TestRequestFormModel.test_lines).selectinload(TRFTestLineModel.test))
            .where(
                TestRequestFormModel.product_id == product_id,
                TestRequestFormModel.batch_number == batch_number,
                TestRequestFormModel.status == "Released",
            )
            #  Oldest first, so a later retest of the same test naturally
            #  overwrites the earlier one during COA compilation.
            .order_by(TestRequestFormModel.released_at.asc(), TestRequestFormModel.id.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, trf: TestRequestForm) -> TestRequestForm:
        model = TestRequestFormModel(
            trf_number=trf.trf_number,
            product_id=trf.product_id,
            batch_number=trf.batch_number,
            label_claim=trf.label_claim,
            stage_of_sample=trf.stage_of_sample,
            group_name=trf.group_name,
            quantity=trf.quantity,
            storage_condition=trf.storage_condition,
            storage_period=trf.storage_period,
            pack_details=trf.pack_details,
            manufactured_by=trf.manufactured_by,
            mfg_date=trf.mfg_date,
            expiry_or_retest_date=trf.expiry_or_retest_date,
            remark=trf.remark,
            source=trf.source,
            stability_pull_ref=trf.stability_pull_ref,
            status=trf.status,
            created_by=trf.created_by,
            modified_by=trf.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return await self.get_by_id(model.id)  # type: ignore[return-value]

    async def update(self, trf: TestRequestForm) -> TestRequestForm:
        model = await self._session.get(TestRequestFormModel, trf.id)
        if model is None:
            raise ValueError(f"TestRequestForm {trf.id} not found")
        model.ar_number = trf.ar_number
        model.batch_number = trf.batch_number
        model.label_claim = trf.label_claim
        model.stage_of_sample = trf.stage_of_sample
        model.group_name = trf.group_name
        model.quantity = trf.quantity
        model.storage_condition = trf.storage_condition
        model.storage_period = trf.storage_period
        model.pack_details = trf.pack_details
        model.manufactured_by = trf.manufactured_by
        model.mfg_date = trf.mfg_date
        model.expiry_or_retest_date = trf.expiry_or_retest_date
        model.remark = trf.remark
        model.status = trf.status
        model.initiated_by = trf.initiated_by
        model.initiated_at = trf.initiated_at
        model.fdgl_approved_by = trf.fdgl_approved_by
        model.fdgl_approved_at = trf.fdgl_approved_at
        model.adgl_accepted_by = trf.adgl_accepted_by
        model.adgl_accepted_at = trf.adgl_accepted_at
        model.analyst_accepted_by = trf.analyst_accepted_by
        model.analyst_accepted_at = trf.analyst_accepted_at
        model.results_submitted_by = trf.results_submitted_by
        model.results_submitted_at = trf.results_submitted_at
        model.released_by = trf.released_by
        model.released_at = trf.released_at
        model.referred_back_by = trf.referred_back_by
        model.referred_back_at = trf.referred_back_at
        model.referred_back_comments = trf.referred_back_comments
        model.rejected_by = trf.rejected_by
        model.rejected_at = trf.rejected_at
        model.rejected_comments = trf.rejected_comments
        model.atr_snapshot = trf.atr_snapshot
        model.modified_by = trf.modified_by
        model.modified_date = trf.modified_date
        await self._session.flush()
        return await self.get_by_id(trf.id)  # type: ignore[return-value]

    async def count_by_number_prefix(self, prefix: str) -> int:
        stmt = select(func.count()).select_from(TestRequestFormModel).where(
            TestRequestFormModel.trf_number.like(f"{prefix}%")
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_ar_by_number_prefix(self, prefix: str) -> int:
        stmt = select(func.count()).select_from(TestRequestFormModel).where(
            TestRequestFormModel.ar_number.like(f"{prefix}%")
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def add_test_line(self, trf_id: int, line: TRFTestLine) -> TRFTestLine:
        model = TRFTestLineModel(
            trf_id=trf_id,
            line_no=line.line_no,
            test_id=line.test_id,
            specification=line.specification,
            raw_data_reference=line.raw_data_reference,
            result=line.result,
            remark=line.remark,
            created_by=line.created_by,
            modified_by=line.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return await self.get_test_line_by_id(model.id)  # type: ignore[return-value]

    async def remove_test_line(self, trf_id: int, line_id: int) -> None:
        model = await self._session.get(TRFTestLineModel, line_id)
        if model is not None and model.trf_id == trf_id:
            await self._session.delete(model)
            await self._session.flush()

    async def update_test_line(self, line: TRFTestLine) -> TRFTestLine:
        model = await self._session.get(TRFTestLineModel, line.id)
        if model is None:
            raise ValueError(f"TRFTestLine {line.id} not found")
        model.specification = line.specification
        model.raw_data_reference = line.raw_data_reference
        model.result = line.result
        model.remark = line.remark
        model.modified_by = line.modified_by
        model.modified_date = line.modified_date
        await self._session.flush()
        return await self.get_test_line_by_id(line.id)  # type: ignore[return-value]

    async def get_test_line_by_id(self, line_id: int) -> TRFTestLine | None:
        stmt = (
            select(TRFTestLineModel)
            .options(selectinload(TRFTestLineModel.test))
            .where(TRFTestLineModel.id == line_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._line_to_entity(model) if model else None

    @staticmethod
    def _line_to_entity(model: TRFTestLineModel) -> TRFTestLine:
        test: TestModel | None = model.test
        return TRFTestLine(
            id=model.id,
            trf_id=model.trf_id,
            line_no=model.line_no,
            test_id=model.test_id,
            specification=model.specification,
            raw_data_reference=model.raw_data_reference,
            result=model.result,
            remark=model.remark,
            test_code=test.code if test else None,
            test_name=test.name if test else None,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )

    @classmethod
    def _to_entity(cls, model: TestRequestFormModel) -> TestRequestForm:
        return TestRequestForm(
            id=model.id,
            trf_number=model.trf_number,
            ar_number=model.ar_number,
            product_id=model.product_id,
            batch_number=model.batch_number,
            label_claim=model.label_claim,
            stage_of_sample=model.stage_of_sample,
            group_name=model.group_name,
            quantity=model.quantity,
            storage_condition=model.storage_condition,
            storage_period=model.storage_period,
            pack_details=model.pack_details,
            manufactured_by=model.manufactured_by,
            mfg_date=model.mfg_date,
            expiry_or_retest_date=model.expiry_or_retest_date,
            remark=model.remark,
            source=model.source,
            stability_pull_ref=model.stability_pull_ref,
            status=model.status,
            initiated_by=model.initiated_by,
            initiated_at=model.initiated_at,
            fdgl_approved_by=model.fdgl_approved_by,
            fdgl_approved_at=model.fdgl_approved_at,
            adgl_accepted_by=model.adgl_accepted_by,
            adgl_accepted_at=model.adgl_accepted_at,
            analyst_accepted_by=model.analyst_accepted_by,
            analyst_accepted_at=model.analyst_accepted_at,
            results_submitted_by=model.results_submitted_by,
            results_submitted_at=model.results_submitted_at,
            released_by=model.released_by,
            released_at=model.released_at,
            referred_back_by=model.referred_back_by,
            referred_back_at=model.referred_back_at,
            referred_back_comments=model.referred_back_comments,
            rejected_by=model.rejected_by,
            rejected_at=model.rejected_at,
            rejected_comments=model.rejected_comments,
            atr_snapshot=model.atr_snapshot,
            test_lines=[cls._line_to_entity(li) for li in (model.test_lines or [])],
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
