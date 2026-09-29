"""Stability Management repository implementation (Adapter)."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.stability import (
    StabilityMatrixCell,
    StabilityProtocol,
    StabilityReport,
    StabilitySample,
)
from src.domain.repositories.stability_repository import IStabilityRepository
from src.infrastructure.database.models.sample_model import SampleModel
from src.infrastructure.database.models.stability_model import (
    StabilityMatrixCellModel,
    StabilityProtocolModel,
    StabilityReportModel,
    StabilitySampleModel,
)


class StabilityRepositoryImpl(IStabilityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Protocol ──
    async def get_protocol_by_id(self, protocol_id: int) -> StabilityProtocol | None:
        model = await self._session.get(StabilityProtocolModel, protocol_id)
        return self._protocol_to_entity(model) if model else None

    async def list_protocols(self) -> list[StabilityProtocol]:
        stmt = select(StabilityProtocolModel).order_by(StabilityProtocolModel.created_date.desc())
        result = await self._session.execute(stmt)
        return [self._protocol_to_entity(m) for m in result.scalars().all()]

    async def create_protocol(self, protocol: StabilityProtocol) -> StabilityProtocol:
        model = StabilityProtocolModel(
            protocol_code=protocol.protocol_code, product_id=protocol.product_id,
            condition=protocol.condition, duration_months=protocol.duration_months,
            study_type=protocol.study_type, testing_frequency=protocol.testing_frequency,
            status=protocol.status,
            label_claim=protocol.label_claim, mfg_date=protocol.mfg_date,
            batch_number=protocol.batch_number, placebo_batch_number=protocol.placebo_batch_number,
            batch_size=protocol.batch_size, stability_initiation_date=protocol.stability_initiation_date,
            no_of_samples_time_points=protocol.no_of_samples_time_points, fill_volume=protocol.fill_volume,
            api_name=protocol.api_name, api_batch_no=protocol.api_batch_no, api_source=protocol.api_source,
            primary_pack=protocol.primary_pack, secondary_pack=protocol.secondary_pack,
            headspace=protocol.headspace, orientation=protocol.orientation, remarks=protocol.remarks,
            created_by=protocol.created_by, modified_by=protocol.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._protocol_to_entity(model)

    async def update_protocol(self, protocol: StabilityProtocol) -> StabilityProtocol:
        model = await self._session.get(StabilityProtocolModel, protocol.id)
        if model is None:
            raise ValueError(f"StabilityProtocol {protocol.id} not found")
        model.condition = protocol.condition
        model.duration_months = protocol.duration_months
        model.study_type = protocol.study_type
        model.testing_frequency = protocol.testing_frequency
        model.status = protocol.status
        model.label_claim = protocol.label_claim
        model.mfg_date = protocol.mfg_date
        model.batch_number = protocol.batch_number
        model.placebo_batch_number = protocol.placebo_batch_number
        model.batch_size = protocol.batch_size
        model.stability_initiation_date = protocol.stability_initiation_date
        model.no_of_samples_time_points = protocol.no_of_samples_time_points
        model.fill_volume = protocol.fill_volume
        model.api_name = protocol.api_name
        model.api_batch_no = protocol.api_batch_no
        model.api_source = protocol.api_source
        model.primary_pack = protocol.primary_pack
        model.secondary_pack = protocol.secondary_pack
        model.headspace = protocol.headspace
        model.orientation = protocol.orientation
        model.remarks = protocol.remarks
        model.formulation_checked_by = protocol.formulation_checked_by
        model.formulation_checked_at = protocol.formulation_checked_at
        model.approved_by = protocol.approved_by
        model.approved_at = protocol.approved_at
        model.modified_by = protocol.modified_by
        model.modified_date = protocol.modified_date
        await self._session.flush()
        return self._protocol_to_entity(model)

    async def count_protocols(self) -> int:
        stmt = select(func.count()).select_from(StabilityProtocolModel)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ── Loading Matrix ──
    async def list_matrix_cells(self, protocol_id: int) -> list[StabilityMatrixCell]:
        stmt = select(StabilityMatrixCellModel).where(
            StabilityMatrixCellModel.protocol_id == protocol_id
        )
        result = await self._session.execute(stmt)
        return [self._cell_to_entity(m) for m in result.scalars().all()]

    async def upsert_matrix_cell(self, cell: StabilityMatrixCell) -> StabilityMatrixCell:
        model = None
        if cell.id:
            model = await self._session.get(StabilityMatrixCellModel, cell.id)
        if model is None:
            stmt = select(StabilityMatrixCellModel).where(
                StabilityMatrixCellModel.protocol_id == cell.protocol_id,
                StabilityMatrixCellModel.condition == cell.condition,
                StabilityMatrixCellModel.time_point_days == cell.time_point_days,
                StabilityMatrixCellModel.is_reserve == cell.is_reserve,
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

        if model is None:
            model = StabilityMatrixCellModel(
                protocol_id=cell.protocol_id, condition=cell.condition,
                is_reserve=cell.is_reserve, time_point_days=cell.time_point_days,
                created_by=cell.created_by, modified_by=cell.modified_by,
            )
            self._session.add(model)

        model.time_point_month_label = cell.time_point_month_label
        model.is_scheduled = cell.is_scheduled
        model.notes = cell.notes
        model.modified_by = cell.modified_by
        await self._session.flush()
        return self._cell_to_entity(model)

    async def get_matrix_cell_by_natural_key(
        self, protocol_id: int, condition: str, time_point_days: int | None, is_reserve: bool
    ) -> StabilityMatrixCell | None:
        stmt = select(StabilityMatrixCellModel).where(
            StabilityMatrixCellModel.protocol_id == protocol_id,
            StabilityMatrixCellModel.condition == condition,
            StabilityMatrixCellModel.time_point_days == time_point_days,
            StabilityMatrixCellModel.is_reserve == is_reserve,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._cell_to_entity(model) if model else None

    async def get_matrix_cell_by_id(self, cell_id: int) -> StabilityMatrixCell | None:
        model = await self._session.get(StabilityMatrixCellModel, cell_id)
        return self._cell_to_entity(model) if model else None

    # ── Time-point samples ──
    async def list_samples(self, protocol_id: int) -> list[StabilitySample]:
        stmt = select(StabilitySampleModel, SampleModel.status).outerjoin(
            SampleModel, StabilitySampleModel.sample_id == SampleModel.id
        ).where(StabilitySampleModel.protocol_id == protocol_id)
        result = await self._session.execute(stmt)
        return [self._sample_to_entity(m, s) for m, s in result.all()]

    async def get_sample_by_id(self, sample_id: int) -> StabilitySample | None:
        stmt = select(StabilitySampleModel, SampleModel.status).outerjoin(
            SampleModel, StabilitySampleModel.sample_id == SampleModel.id
        ).where(StabilitySampleModel.id == sample_id)
        result = await self._session.execute(stmt)
        row = result.first()
        return self._sample_to_entity(row[0], row[1]) if row else None

    async def create_sample(self, sample: StabilitySample) -> StabilitySample:
        model = StabilitySampleModel(
            protocol_id=sample.protocol_id, matrix_cell_id=sample.matrix_cell_id,
            condition=sample.condition, time_point_days=sample.time_point_days,
            time_point_months=sample.time_point_months, batch_number=sample.batch_number,
            scheduled_date=sample.scheduled_date, pull_date=sample.pull_date,
            sample_id=sample.sample_id, comments=sample.comments,
            created_by=sample.created_by, modified_by=sample.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._sample_to_entity(model, None)

    async def update_sample(self, sample: StabilitySample) -> StabilitySample:
        model = await self._session.get(StabilitySampleModel, sample.id)
        if model is None:
            raise ValueError(f"StabilitySample {sample.id} not found")
        model.pull_date = sample.pull_date
        model.sample_id = sample.sample_id
        model.comments = sample.comments
        model.modified_by = sample.modified_by
        model.modified_date = sample.modified_date
        await self._session.flush()
        linked_status = None
        if model.sample_id:
            linked = await self._session.get(SampleModel, model.sample_id)
            linked_status = linked.status if linked else None
        return self._sample_to_entity(model, linked_status)

    async def exists_sample_for_cell(
        self, protocol_id: int, batch_number: str, matrix_cell_id: int
    ) -> bool:
        stmt = select(func.count()).select_from(StabilitySampleModel).where(
            StabilitySampleModel.protocol_id == protocol_id,
            StabilitySampleModel.batch_number == batch_number,
            StabilitySampleModel.matrix_cell_id == matrix_cell_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    # ── Reports ──
    async def list_reports(self, protocol_id: int) -> list[StabilityReport]:
        stmt = (
            select(StabilityReportModel)
            .where(StabilityReportModel.protocol_id == protocol_id)
            .order_by(StabilityReportModel.created_date.desc())
        )
        result = await self._session.execute(stmt)
        return [self._report_to_entity(m) for m in result.scalars().all()]

    async def get_report_by_id(self, report_id: int) -> StabilityReport | None:
        model = await self._session.get(StabilityReportModel, report_id)
        return self._report_to_entity(model) if model else None

    async def get_latest_signed_report(self, protocol_id: int) -> StabilityReport | None:
        stmt = (
            select(StabilityReportModel)
            .where(
                StabilityReportModel.protocol_id == protocol_id,
                StabilityReportModel.status.in_(["Prepared", "Approved"]),
            )
            .order_by(StabilityReportModel.created_date.desc())
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return self._report_to_entity(model) if model else None

    async def get_latest_draft_report(self, protocol_id: int) -> StabilityReport | None:
        stmt = (
            select(StabilityReportModel)
            .where(
                StabilityReportModel.protocol_id == protocol_id,
                StabilityReportModel.status == "Draft",
            )
            .order_by(StabilityReportModel.created_date.desc())
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return self._report_to_entity(model) if model else None

    async def create_report(self, report: StabilityReport) -> StabilityReport:
        model = StabilityReportModel(
            protocol_id=report.protocol_id, report_number=report.report_number,
            status=report.status,
            product_name=report.product_name, composition_label=report.composition_label,
            manufactured_at=report.manufactured_at, stability_study_type=report.stability_study_type,
            batch_no=report.batch_no, stability_condition=report.stability_condition,
            batch_size=report.batch_size, date_of_commencement=report.date_of_commencement,
            manufacturing_date=report.manufacturing_date, stability_protocol_no=report.stability_protocol_no,
            expiry_date=report.expiry_date, api_source=report.api_source,
            api_batch_number=report.api_batch_number, packing=report.packing,
            results_data=report.results_data, remarks=report.remarks,
            generated_by=report.generated_by, generated_at=report.generated_at,
            created_by=report.created_by, modified_by=report.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._report_to_entity(model)

    async def update_report(self, report: StabilityReport) -> StabilityReport:
        model = await self._session.get(StabilityReportModel, report.id)
        if model is None:
            raise ValueError(f"StabilityReport {report.id} not found")
        model.status = report.status
        model.results_data = report.results_data
        model.remarks = report.remarks
        model.prepared_by = report.prepared_by
        model.prepared_at = report.prepared_at
        model.checked_by_name = report.checked_by_name
        model.reviewed_by_name = report.reviewed_by_name
        model.approved_by = report.approved_by
        model.approved_at = report.approved_at
        model.modified_by = report.modified_by
        model.modified_date = report.modified_date
        await self._session.flush()
        return self._report_to_entity(model)

    async def count_reports(self) -> int:
        stmt = select(func.count()).select_from(StabilityReportModel)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ── Mapping helpers ──
    @staticmethod
    def _protocol_to_entity(model: StabilityProtocolModel) -> StabilityProtocol:
        return StabilityProtocol(
            id=model.id, protocol_code=model.protocol_code, product_id=model.product_id,
            condition=model.condition, duration_months=model.duration_months,
            study_type=model.study_type, testing_frequency=model.testing_frequency,
            status=model.status,
            label_claim=model.label_claim, mfg_date=model.mfg_date,
            batch_number=model.batch_number, placebo_batch_number=model.placebo_batch_number,
            batch_size=model.batch_size, stability_initiation_date=model.stability_initiation_date,
            no_of_samples_time_points=model.no_of_samples_time_points, fill_volume=model.fill_volume,
            api_name=model.api_name, api_batch_no=model.api_batch_no, api_source=model.api_source,
            primary_pack=model.primary_pack, secondary_pack=model.secondary_pack,
            headspace=model.headspace, orientation=model.orientation, remarks=model.remarks,
            formulation_checked_by=model.formulation_checked_by,
            formulation_checked_at=model.formulation_checked_at,
            approved_by=model.approved_by, approved_at=model.approved_at,
            created_by=model.created_by, created_date=model.created_date,
            modified_by=model.modified_by, modified_date=model.modified_date,
        )

    @staticmethod
    def _cell_to_entity(model: StabilityMatrixCellModel) -> StabilityMatrixCell:
        return StabilityMatrixCell(
            id=model.id, protocol_id=model.protocol_id, condition=model.condition,
            is_reserve=model.is_reserve, time_point_days=model.time_point_days,
            time_point_month_label=model.time_point_month_label, is_scheduled=model.is_scheduled,
            notes=model.notes, created_by=model.created_by, created_date=model.created_date,
            modified_by=model.modified_by, modified_date=model.modified_date,
        )

    @staticmethod
    def _sample_to_entity(
        model: StabilitySampleModel, linked_sample_status: str | None
    ) -> StabilitySample:
        return StabilitySample(
            id=model.id, protocol_id=model.protocol_id, matrix_cell_id=model.matrix_cell_id,
            condition=model.condition, time_point_days=model.time_point_days,
            time_point_months=model.time_point_months, batch_number=model.batch_number,
            scheduled_date=model.scheduled_date, pull_date=model.pull_date,
            sample_id=model.sample_id, comments=model.comments,
            linked_sample_status=linked_sample_status,
            created_by=model.created_by, created_date=model.created_date,
            modified_by=model.modified_by, modified_date=model.modified_date,
        )

    @staticmethod
    def _report_to_entity(model: StabilityReportModel) -> StabilityReport:
        return StabilityReport(
            id=model.id, protocol_id=model.protocol_id, report_number=model.report_number,
            status=model.status,
            product_name=model.product_name, composition_label=model.composition_label,
            manufactured_at=model.manufactured_at, stability_study_type=model.stability_study_type,
            batch_no=model.batch_no, stability_condition=model.stability_condition,
            batch_size=model.batch_size, date_of_commencement=model.date_of_commencement,
            manufacturing_date=model.manufacturing_date, stability_protocol_no=model.stability_protocol_no,
            expiry_date=model.expiry_date, api_source=model.api_source,
            api_batch_number=model.api_batch_number, packing=model.packing,
            results_data=model.results_data or [], remarks=model.remarks,
            prepared_by=model.prepared_by, prepared_at=model.prepared_at,
            checked_by_name=model.checked_by_name, reviewed_by_name=model.reviewed_by_name,
            approved_by=model.approved_by, approved_at=model.approved_at,
            generated_by=model.generated_by, generated_at=model.generated_at,
            created_by=model.created_by, created_date=model.created_date,
            modified_by=model.modified_by, modified_date=model.modified_date,
        )
