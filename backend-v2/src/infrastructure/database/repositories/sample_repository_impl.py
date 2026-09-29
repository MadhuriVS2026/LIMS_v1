"""Sample & SampleResult repository implementation (Adapter)."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.sample import Sample, SampleResult
from src.domain.repositories.sample_repository import ISampleRepository
from src.infrastructure.database.models.sample_model import SampleModel, SampleResultModel
from src.infrastructure.database.models.test_model import TestModel


class SampleRepositoryImpl(ISampleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, sample_id: int) -> Sample | None:
        stmt = (
            select(SampleModel)
            .options(selectinload(SampleModel.results).selectinload(SampleResultModel.test))
            .where(SampleModel.id == sample_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self, status: str | None = None) -> list[Sample]:
        stmt = select(SampleModel).options(
            selectinload(SampleModel.results).selectinload(SampleResultModel.test)
        )
        if status:
            stmt = stmt.where(SampleModel.status == status)
        stmt = stmt.order_by(SampleModel.logged_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, sample: Sample) -> Sample:
        model = SampleModel(
            sample_code=sample.sample_code,
            product_id=sample.product_id,
            batch_number=sample.batch_number,
            quantity_received=sample.quantity_received,
            unit=sample.unit,
            sample_type=sample.sample_type,
            priority=sample.priority,
            status=sample.status,
            sap_inspection_lot=sample.sap_inspection_lot,
            sap_material=sample.sap_material,
            sap_plant=sample.sap_plant,
            sap_vendor=sample.sap_vendor,
            sap_vendor_batch=sample.sap_vendor_batch,
            manufacturing_date=sample.manufacturing_date,
            expiry_date=sample.expiry_date,
            logged_by=sample.logged_by,
            logged_at=sample.logged_at,
            created_by=sample.created_by,
            modified_by=sample.modified_by,
        )
        self._session.add(model)
        await self._session.flush()

        for r in sample.results:
            result_model = SampleResultModel(
                sample_id=model.id,
                test_id=r.test_id,
                min_limit=r.min_limit,
                max_limit=r.max_limit,
                expected_result=r.expected_result,
                status=r.status,
                is_oos=r.is_oos,
            )
            self._session.add(result_model)
        await self._session.flush()

        return await self.get_by_id(model.id)  # type: ignore[return-value]

    async def update(self, sample: Sample) -> Sample:
        model = await self._session.get(SampleModel, sample.id)
        if model is None:
            raise ValueError(f"Sample {sample.id} not found")
        model.status = sample.status
        model.received_by = sample.received_by
        model.received_at = sample.received_at
        model.approved_by = sample.approved_by
        model.approved_at = sample.approved_at
        model.coa_released_by = sample.coa_released_by
        model.coa_released_at = sample.coa_released_at
        model.coa_data = sample.coa_data
        model.sap_ud_posted = sample.sap_ud_posted
        model.sap_ud_code = sample.sap_ud_code
        model.sap_ud_posted_at = sample.sap_ud_posted_at
        model.modified_by = sample.modified_by
        model.modified_date = sample.modified_date
        await self._session.flush()
        return await self.get_by_id(sample.id)  # type: ignore[return-value]

    async def count_by_code_prefix(self, prefix: str) -> int:
        stmt = select(func.count()).select_from(SampleModel).where(
            SampleModel.sample_code.like(f"{prefix}%")
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_result_by_id(self, result_id: int) -> SampleResult | None:
        stmt = (
            select(SampleResultModel)
            .options(selectinload(SampleResultModel.test))
            .where(SampleResultModel.id == result_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._result_to_entity(model) if model else None

    async def update_result(self, result: SampleResult) -> SampleResult:
        model = await self._session.get(SampleResultModel, result.id)
        if model is None:
            raise ValueError(f"SampleResult {result.id} not found")
        model.result_value = result.result_value
        model.result_text = result.result_text
        model.status = result.status
        model.analyst_id = result.analyst_id
        model.submitted_at = result.submitted_at
        model.supervisor_id = result.supervisor_id
        model.reviewed_at = result.reviewed_at
        model.is_oos = result.is_oos
        model.oos_investigation_id = result.oos_investigation_id
        await self._session.flush()
        return await self.get_result_by_id(result.id)  # type: ignore[return-value]

    @staticmethod
    def _result_to_entity(model: SampleResultModel) -> SampleResult:
        return SampleResult(
            id=model.id,
            sample_id=model.sample_id,
            test_id=model.test_id,
            min_limit=model.min_limit,
            max_limit=model.max_limit,
            expected_result=model.expected_result,
            result_value=model.result_value,
            result_text=model.result_text,
            status=model.status,
            analyst_id=model.analyst_id,
            submitted_at=model.submitted_at,
            supervisor_id=model.supervisor_id,
            reviewed_at=model.reviewed_at,
            is_oos=model.is_oos,
            oos_investigation_id=model.oos_investigation_id,
            test_type=model.test.type if model.test else "Quantitative",
            test_code=model.test.code if model.test else None,
            test_name=model.test.name if model.test else None,
            test_unit=model.test.unit if model.test else None,
            test_method_no=model.test.method_no if model.test else None,
            test_category=model.test.category if model.test else None,
            test_technique=model.test.technique if model.test else None,
            test_status=model.test.status if model.test else None,
        )

    @classmethod
    def _to_entity(cls, model: SampleModel) -> Sample:
        results = [cls._result_to_entity(r) for r in (model.results or [])]
        return Sample(
            id=model.id,
            sample_code=model.sample_code,
            product_id=model.product_id,
            batch_number=model.batch_number,
            quantity_received=model.quantity_received,
            unit=model.unit,
            sample_type=model.sample_type,
            priority=model.priority,
            status=model.status,
            sap_inspection_lot=model.sap_inspection_lot,
            sap_material=model.sap_material,
            sap_plant=model.sap_plant,
            sap_vendor=model.sap_vendor,
            sap_vendor_batch=model.sap_vendor_batch,
            manufacturing_date=model.manufacturing_date,
            expiry_date=model.expiry_date,
            sap_ud_posted=model.sap_ud_posted,
            sap_ud_code=model.sap_ud_code,
            sap_ud_posted_at=model.sap_ud_posted_at,
            logged_by=model.logged_by,
            logged_at=model.logged_at,
            received_by=model.received_by,
            received_at=model.received_at,
            approved_by=model.approved_by,
            approved_at=model.approved_at,
            coa_released_by=model.coa_released_by,
            coa_released_at=model.coa_released_at,
            coa_data=model.coa_data,
            results=results,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
