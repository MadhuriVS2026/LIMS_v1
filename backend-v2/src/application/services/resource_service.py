"""
Resource Manager Application Service.
Handles Instruments, Columns, Reference Standards, Chemicals, and Volumetric
Solutions — all with unified audit logging. Stability Management was
extracted into its own StabilityService (see stability_service.py).
"""
from datetime import datetime, timezone

from src.domain.entities.audit_log import AuditLog
from src.domain.entities.instrument import Instrument
from src.domain.entities.resource_items import (
    ChemicalReagent,
    ColumnMaster,
    ReferenceStandard,
    VolumetricSolution,
)
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.resource_repositories import (
    IChemicalRepository,
    IColumnRepository,
    IInstrumentRepository,
    IReferenceStandardRepository,
    IVolumetricSolutionRepository,
)


class ResourceService:
    """Application service consolidating all Resource Manager sub-modules."""

    def __init__(
        self,
        instrument_repo: IInstrumentRepository,
        column_repo: IColumnRepository,
        standard_repo: IReferenceStandardRepository,
        chemical_repo: IChemicalRepository,
        volumetric_repo: IVolumetricSolutionRepository,
        audit_repo: IAuditLogRepository,
    ) -> None:
        self._instrument_repo = instrument_repo
        self._column_repo = column_repo
        self._standard_repo = standard_repo
        self._chemical_repo = chemical_repo
        self._volumetric_repo = volumetric_repo
        self._audit_repo = audit_repo

    # ─── Instruments ───
    async def list_instruments(self) -> list[Instrument]:
        return await self._instrument_repo.list_all()

    async def create_instrument(
        self, code: str, name: str, category: str | None, manufacturer: str | None,
        model_number: str | None, serial_number: str | None, location: str | None,
        calibration_frequency_days: int | None, actor: User,
    ) -> Instrument:
        instrument = Instrument(
            code=code, name=name, category=category, manufacturer=manufacturer,
            model_number=model_number, serial_number=serial_number, location=location,
            calibration_frequency_days=calibration_frequency_days, status="Active",
            created_by=actor.username, modified_by=actor.username,
        )
        created = await self._instrument_repo.create(instrument)
        await self._audit_repo.write(
            AuditLog(user_id=actor.id, username=actor.username, action="CREATE",
                      table_name="instruments", record_id=created.id)
        )
        return created

    async def record_calibration(
        self, instrument_id: int, calibration_date: datetime, next_due_date: datetime | None,
        result: str, certificate_no: str | None, comments: str | None, actor: User,
    ) -> Instrument:
        instrument = await self._instrument_repo.get_by_id(instrument_id)
        if instrument is None:
            from src.application.exceptions.application_exceptions import NotFoundException
            raise NotFoundException("Instrument not found")
        instrument.record_calibration(calibration_date, actor.username, next_due_date, result)
        updated = await self._instrument_repo.update(instrument)
        await self._audit_repo.write(
            AuditLog(user_id=actor.id, username=actor.username, action="CALIBRATE",
                      table_name="instruments", record_id=updated.id, comments=f"Result: {result}")
        )
        return updated

    async def count_calibration_due(self, days: int = 7) -> int:
        return await self._instrument_repo.count_due_for_calibration(days)

    # ─── Columns ───
    async def list_columns(self) -> list[ColumnMaster]:
        return await self._column_repo.list_all()

    async def create_column(
        self, code: str, name: str, type_: str | None, manufacturer: str | None,
        dimensions: str | None, serial_number: str | None, instrument_id: int | None,
        max_injections: int | None, actor: User,
    ) -> ColumnMaster:
        column = ColumnMaster(
            code=code, name=name, type=type_, manufacturer=manufacturer, dimensions=dimensions,
            serial_number=serial_number, instrument_id=instrument_id, max_injections=max_injections,
            status="Active", created_by=actor.username, modified_by=actor.username,
        )
        created = await self._column_repo.create(column)
        await self._audit_repo.write(
            AuditLog(user_id=actor.id, username=actor.username, action="CREATE",
                      table_name="columns", record_id=created.id)
        )
        return created

    # ─── Reference Standards ───
    async def list_reference_standards(self) -> list[ReferenceStandard]:
        return await self._standard_repo.list_all()

    async def create_reference_standard(
        self, code: str, name: str, lot_number: str | None, potency: float | None,
        manufacturer: str | None, category: str | None, storage_condition: str | None,
        quantity_received: float | None, unit: str | None, received_date: datetime | None,
        expiry_date: datetime | None, actor: User,
    ) -> ReferenceStandard:
        standard = ReferenceStandard(
            code=code, name=name, lot_number=lot_number, potency=potency,
            manufacturer=manufacturer, category=category, storage_condition=storage_condition,
            quantity_received=quantity_received, unit=unit, received_date=received_date,
            expiry_date=expiry_date, status="Active",
            created_by=actor.username, modified_by=actor.username,
        )
        created = await self._standard_repo.create(standard)
        await self._audit_repo.write(
            AuditLog(user_id=actor.id, username=actor.username, action="CREATE",
                      table_name="reference_standards", record_id=created.id)
        )
        return created

    # ─── Chemicals/Reagents ───
    async def list_chemicals(self) -> list[ChemicalReagent]:
        return await self._chemical_repo.list_all()

    async def create_chemical(
        self, code: str, name: str, grade: str | None, manufacturer: str | None,
        lot_number: str | None, cas_number: str | None, quantity_received: float | None,
        unit: str | None, storage_condition: str | None, received_date: datetime | None,
        expiry_date: datetime | None, actor: User,
    ) -> ChemicalReagent:
        chemical = ChemicalReagent(
            code=code, name=name, grade=grade, manufacturer=manufacturer, lot_number=lot_number,
            cas_number=cas_number, quantity_received=quantity_received, unit=unit,
            storage_condition=storage_condition, received_date=received_date, expiry_date=expiry_date,
            status="Active", created_by=actor.username, modified_by=actor.username,
        )
        created = await self._chemical_repo.create(chemical)
        await self._audit_repo.write(
            AuditLog(user_id=actor.id, username=actor.username, action="CREATE",
                      table_name="chemicals_reagents", record_id=created.id)
        )
        return created

    # ─── Volumetric Solutions ───
    async def list_volumetric_solutions(self) -> list[VolumetricSolution]:
        return await self._volumetric_repo.list_all()

    async def create_volumetric_solution(
        self, code: str, name: str, concentration: str | None, prepared_date: datetime | None,
        expiry_date: datetime | None, standardization_factor: float | None, actor: User,
    ) -> VolumetricSolution:
        solution = VolumetricSolution(
            code=code, name=name, concentration=concentration, prepared_by=actor.username,
            prepared_date=prepared_date, expiry_date=expiry_date,
            standardization_factor=standardization_factor, standardized_by=actor.username,
            standardized_date=prepared_date, status="Active",
            created_by=actor.username, modified_by=actor.username,
        )
        created = await self._volumetric_repo.create(solution)
        await self._audit_repo.write(
            AuditLog(user_id=actor.id, username=actor.username, action="CREATE",
                      table_name="volumetric_solutions", record_id=created.id)
        )
        return created
