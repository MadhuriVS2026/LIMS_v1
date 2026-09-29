"""Audit Log & SAP Integration Log repository implementations (Adapters)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.audit_log import AuditLog, SAPIntegrationLog, SAPReceivedLot
from src.domain.repositories.audit_repository import (
    IAuditLogRepository,
    ISAPIntegrationLogRepository,
    ISAPReceivedLotRepository,
)
from src.infrastructure.database.models.audit_log_model import (
    AuditLogModel,
    SAPIntegrationLogModel,
    SAPReceivedLotModel,
)


class AuditLogRepositoryImpl(IAuditLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def write(self, entry: AuditLog) -> AuditLog:
        model = AuditLogModel(
            user_id=entry.user_id, username=entry.username, action=entry.action,
            table_name=entry.table_name, record_id=entry.record_id,
            old_values=entry.old_values, new_values=entry.new_values, comments=entry.comments,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def list_recent(self, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        stmt = (
            select(AuditLogModel)
            .order_by(AuditLogModel.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: AuditLogModel) -> AuditLog:
        return AuditLog(
            id=model.id, timestamp=model.timestamp, user_id=model.user_id,
            username=model.username, action=model.action, table_name=model.table_name,
            record_id=model.record_id, old_values=model.old_values,
            new_values=model.new_values, comments=model.comments,
        )


class SAPIntegrationLogRepositoryImpl(ISAPIntegrationLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def write(self, entry: SAPIntegrationLog) -> SAPIntegrationLog:
        model = SAPIntegrationLogModel(
            transaction_type=entry.transaction_type, direction=entry.direction,
            sample_id=entry.sample_id, sap_inspection_lot=entry.sap_inspection_lot,
            request_payload=entry.request_payload, response_payload=entry.response_payload,
            status=entry.status, error_message=entry.error_message,
            created_by=entry.created_by, completed_at=entry.completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def list_recent(self, limit: int = 100) -> list[SAPIntegrationLog]:
        stmt = (
            select(SAPIntegrationLogModel)
            .order_by(SAPIntegrationLogModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: SAPIntegrationLogModel) -> SAPIntegrationLog:
        return SAPIntegrationLog(
            id=model.id, transaction_type=model.transaction_type, direction=model.direction,
            sample_id=model.sample_id, sap_inspection_lot=model.sap_inspection_lot,
            request_payload=model.request_payload, response_payload=model.response_payload,
            status=model.status, error_message=model.error_message,
            created_by=model.created_by, created_at=model.created_at, completed_at=model.completed_at,
        )


class SAPReceivedLotRepositoryImpl(ISAPReceivedLotRepository):
    """Stores inspection lots pushed inbound from SAP CPI (read-only reference data)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, lot: SAPReceivedLot) -> SAPReceivedLot:
        stmt = select(SAPReceivedLotModel).where(
            SAPReceivedLotModel.inspection_lot == lot.inspection_lot
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = SAPReceivedLotModel(inspection_lot=lot.inspection_lot)
            self._session.add(model)

        model.plant = lot.plant
        model.material_number = lot.material_number
        model.material_desc = lot.material_desc
        model.batch_number = lot.batch_number
        model.storage_location = lot.storage_location
        model.vendor_code = lot.vendor_code
        model.vendor_name = lot.vendor_name
        model.vendor_batch = lot.vendor_batch
        model.lot_quantity = lot.lot_quantity
        model.lot_unit = lot.lot_unit
        model.manufacturing_date = lot.manufacturing_date
        model.expiry_date = lot.expiry_date
        model.characteristics = lot.characteristics
        model.raw_payload = lot.raw_payload

        await self._session.flush()
        return self._to_entity(model)

    async def list_recent(self, limit: int = 100) -> list[SAPReceivedLot]:
        stmt = (
            select(SAPReceivedLotModel)
            .order_by(SAPReceivedLotModel.received_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_inspection_lot(self, inspection_lot: str) -> SAPReceivedLot | None:
        stmt = select(SAPReceivedLotModel).where(
            SAPReceivedLotModel.inspection_lot == inspection_lot
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def mark_consumed(self, inspection_lot: str, sample_id: int) -> None:
        stmt = select(SAPReceivedLotModel).where(
            SAPReceivedLotModel.inspection_lot == inspection_lot
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is not None:
            model.consumed_by_sample_id = sample_id
            await self._session.flush()

    @staticmethod
    def _to_entity(model: SAPReceivedLotModel) -> SAPReceivedLot:
        return SAPReceivedLot(
            id=model.id, inspection_lot=model.inspection_lot, plant=model.plant,
            material_number=model.material_number, material_desc=model.material_desc,
            batch_number=model.batch_number, storage_location=model.storage_location,
            vendor_code=model.vendor_code, vendor_name=model.vendor_name,
            vendor_batch=model.vendor_batch, lot_quantity=model.lot_quantity,
            lot_unit=model.lot_unit, manufacturing_date=model.manufacturing_date,
            expiry_date=model.expiry_date, characteristics=model.characteristics or [],
            raw_payload=model.raw_payload, received_at=model.received_at,
            consumed_by_sample_id=model.consumed_by_sample_id,
        )
