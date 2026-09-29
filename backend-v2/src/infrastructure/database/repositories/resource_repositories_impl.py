"""Repository implementations for Resource Manager entities."""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.instrument import Instrument
from src.domain.entities.resource_items import (
    ChemicalReagent,
    ColumnMaster,
    ReferenceStandard,
    VolumetricSolution,
)
from src.domain.repositories.resource_repositories import (
    IChemicalRepository,
    IColumnRepository,
    IInstrumentRepository,
    IReferenceStandardRepository,
    IVolumetricSolutionRepository,
)
from src.infrastructure.database.models.instrument_model import InstrumentModel
from src.infrastructure.database.models.resource_models import (
    ChemicalReagentModel,
    ColumnMasterModel,
    ReferenceStandardModel,
    VolumetricSolutionModel,
)


class InstrumentRepositoryImpl(IInstrumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, instrument_id: int) -> Instrument | None:
        model = await self._session.get(InstrumentModel, instrument_id)
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[Instrument]:
        result = await self._session.execute(select(InstrumentModel))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, instrument: Instrument) -> Instrument:
        model = InstrumentModel(
            code=instrument.code, name=instrument.name, category=instrument.category,
            manufacturer=instrument.manufacturer, model_number=instrument.model_number,
            serial_number=instrument.serial_number, location=instrument.location,
            calibration_frequency_days=instrument.calibration_frequency_days,
            status=instrument.status, created_by=instrument.created_by, modified_by=instrument.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, instrument: Instrument) -> Instrument:
        model = await self._session.get(InstrumentModel, instrument.id)
        if model is None:
            raise ValueError(f"Instrument {instrument.id} not found")
        model.status = instrument.status
        model.calibration_due_date = instrument.calibration_due_date
        model.last_calibrated_at = instrument.last_calibrated_at
        model.last_calibrated_by = instrument.last_calibrated_by
        model.qualification_status = instrument.qualification_status
        model.modified_by = instrument.modified_by
        await self._session.flush()
        return self._to_entity(model)

    async def count_due_for_calibration(self, days: int) -> int:
        from datetime import timedelta
        threshold = datetime.now(timezone.utc) + timedelta(days=days)
        stmt = select(func.count()).select_from(InstrumentModel).where(
            InstrumentModel.calibration_due_date <= threshold
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    def _to_entity(model: InstrumentModel) -> Instrument:
        return Instrument(
            id=model.id, code=model.code, name=model.name, category=model.category,
            manufacturer=model.manufacturer, model_number=model.model_number,
            serial_number=model.serial_number, location=model.location, status=model.status,
            calibration_due_date=model.calibration_due_date,
            calibration_frequency_days=model.calibration_frequency_days,
            last_calibrated_at=model.last_calibrated_at, last_calibrated_by=model.last_calibrated_by,
            qualification_status=model.qualification_status,
            created_by=model.created_by, created_date=model.created_date,
            modified_by=model.modified_by, modified_date=model.modified_date,
        )


class ColumnRepositoryImpl(IColumnRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[ColumnMaster]:
        result = await self._session.execute(select(ColumnMasterModel))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, column: ColumnMaster) -> ColumnMaster:
        model = ColumnMasterModel(
            code=column.code, name=column.name, type=column.type,
            manufacturer=column.manufacturer, dimensions=column.dimensions,
            serial_number=column.serial_number, instrument_id=column.instrument_id,
            max_injections=column.max_injections, status=column.status,
            created_by=column.created_by, modified_by=column.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: ColumnMasterModel) -> ColumnMaster:
        return ColumnMaster(
            id=model.id, code=model.code, name=model.name, type=model.type,
            manufacturer=model.manufacturer, dimensions=model.dimensions,
            serial_number=model.serial_number, instrument_id=model.instrument_id,
            max_injections=model.max_injections, current_injections=model.current_injections,
            status=model.status, received_date=model.received_date, retirement_date=model.retirement_date,
            created_by=model.created_by, created_date=model.created_date,
            modified_by=model.modified_by, modified_date=model.modified_date,
        )


class ReferenceStandardRepositoryImpl(IReferenceStandardRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[ReferenceStandard]:
        result = await self._session.execute(select(ReferenceStandardModel))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, standard: ReferenceStandard) -> ReferenceStandard:
        model = ReferenceStandardModel(
            code=standard.code, name=standard.name, lot_number=standard.lot_number,
            potency=standard.potency, manufacturer=standard.manufacturer, category=standard.category,
            storage_condition=standard.storage_condition, quantity_received=standard.quantity_received,
            quantity_remaining=standard.quantity_received, unit=standard.unit,
            received_date=standard.received_date, expiry_date=standard.expiry_date,
            status=standard.status, created_by=standard.created_by, modified_by=standard.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: ReferenceStandardModel) -> ReferenceStandard:
        return ReferenceStandard(
            id=model.id, code=model.code, name=model.name, lot_number=model.lot_number,
            potency=model.potency, manufacturer=model.manufacturer, category=model.category,
            storage_condition=model.storage_condition, quantity_received=model.quantity_received,
            quantity_remaining=model.quantity_remaining, unit=model.unit,
            received_date=model.received_date, expiry_date=model.expiry_date, status=model.status,
            created_by=model.created_by, created_date=model.created_date,
            modified_by=model.modified_by, modified_date=model.modified_date,
        )


class ChemicalRepositoryImpl(IChemicalRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[ChemicalReagent]:
        result = await self._session.execute(select(ChemicalReagentModel))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, chemical: ChemicalReagent) -> ChemicalReagent:
        model = ChemicalReagentModel(
            code=chemical.code, name=chemical.name, grade=chemical.grade,
            manufacturer=chemical.manufacturer, lot_number=chemical.lot_number,
            cas_number=chemical.cas_number, quantity_received=chemical.quantity_received,
            quantity_remaining=chemical.quantity_received, unit=chemical.unit,
            storage_condition=chemical.storage_condition, received_date=chemical.received_date,
            expiry_date=chemical.expiry_date, status=chemical.status,
            created_by=chemical.created_by, modified_by=chemical.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: ChemicalReagentModel) -> ChemicalReagent:
        return ChemicalReagent(
            id=model.id, code=model.code, name=model.name, grade=model.grade,
            manufacturer=model.manufacturer, lot_number=model.lot_number, cas_number=model.cas_number,
            quantity_received=model.quantity_received, quantity_remaining=model.quantity_remaining,
            unit=model.unit, storage_condition=model.storage_condition,
            received_date=model.received_date, expiry_date=model.expiry_date,
            opened_date=model.opened_date, status=model.status,
            created_by=model.created_by, created_date=model.created_date,
            modified_by=model.modified_by, modified_date=model.modified_date,
        )


class VolumetricSolutionRepositoryImpl(IVolumetricSolutionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[VolumetricSolution]:
        result = await self._session.execute(select(VolumetricSolutionModel))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, solution: VolumetricSolution) -> VolumetricSolution:
        model = VolumetricSolutionModel(
            code=solution.code, name=solution.name, concentration=solution.concentration,
            prepared_by=solution.prepared_by, prepared_date=solution.prepared_date,
            expiry_date=solution.expiry_date, standardization_factor=solution.standardization_factor,
            standardized_by=solution.standardized_by, standardized_date=solution.standardized_date,
            status=solution.status, created_by=solution.created_by, modified_by=solution.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: VolumetricSolutionModel) -> VolumetricSolution:
        return VolumetricSolution(
            id=model.id, code=model.code, name=model.name, concentration=model.concentration,
            prepared_by=model.prepared_by, prepared_date=model.prepared_date,
            expiry_date=model.expiry_date, standardization_factor=model.standardization_factor,
            standardized_by=model.standardized_by, standardized_date=model.standardized_date,
            status=model.status, created_by=model.created_by, created_date=model.created_date,
            modified_by=model.modified_by, modified_date=model.modified_date,
        )



