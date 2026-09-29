"""MRN — Material Requisition & Consumption repository implementations (Adapters)."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.mrn import (
    ConsumptionPosting,
    MaterialRequisition,
    MRNLineItem,
    MRNMaterialLot,
)
from src.domain.repositories.mrn_repository import (
    IConsumptionPostingRepository,
    IMaterialRequisitionRepository,
    IMRNMaterialLotRepository,
)
from src.infrastructure.database.models.mrn_model import (
    ConsumptionPostingModel,
    MaterialRequisitionModel,
    MRNLineItemModel,
    MRNMaterialLotModel,
)


class MRNMaterialLotRepositoryImpl(IMRNMaterialLotRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, lot_id: int) -> MRNMaterialLot | None:
        model = await self._session.get(MRNMaterialLotModel, lot_id)
        return self._to_entity(model) if model else None

    async def get_by_natural_key(self, grn_document_no: str, grn_item_no: str) -> MRNMaterialLot | None:
        stmt = select(MRNMaterialLotModel).where(
            MRNMaterialLotModel.grn_document_no == grn_document_no,
            MRNMaterialLotModel.grn_item_no == grn_item_no,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def upsert(self, lot: MRNMaterialLot) -> MRNMaterialLot:
        stmt = select(MRNMaterialLotModel).where(
            MRNMaterialLotModel.grn_document_no == lot.grn_document_no,
            MRNMaterialLotModel.grn_item_no == lot.grn_item_no,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = MRNMaterialLotModel(
                grn_document_no=lot.grn_document_no,
                grn_item_no=lot.grn_item_no,
            )
            self._session.add(model)

        model.material_code = lot.material_code
        model.material_description = lot.material_description
        model.batch_number = lot.batch_number
        model.plant = lot.plant
        model.unit = lot.unit
        model.original_quantity = lot.original_quantity
        model.grn_date = lot.grn_date
        model.pulled_at = lot.pulled_at
        # consumed_quantity is intentionally NOT overwritten by an upsert from
        # SAP — it is only ever advanced by this system's own consumption
        # postings (Requirement 1.3: update fields, not consumption progress).

        await self._session.flush()
        return self._to_entity(model)

    async def update(self, lot: MRNMaterialLot) -> MRNMaterialLot:
        model = await self._session.get(MRNMaterialLotModel, lot.id)
        if model is None:
            raise ValueError(f"MRNMaterialLot {lot.id} not found")
        model.consumed_quantity = lot.consumed_quantity
        model.modified_by = lot.modified_by
        model.modified_date = lot.modified_date
        await self._session.flush()
        return self._to_entity(model)

    async def list_available(self) -> list[MRNMaterialLot]:
        stmt = (
            select(MRNMaterialLotModel)
            .where(MRNMaterialLotModel.consumed_quantity < MRNMaterialLotModel.original_quantity)
            .order_by(MRNMaterialLotModel.pulled_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(self) -> list[MRNMaterialLot]:
        stmt = select(MRNMaterialLotModel).order_by(MRNMaterialLotModel.pulled_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: MRNMaterialLotModel) -> MRNMaterialLot:
        return MRNMaterialLot(
            id=model.id,
            grn_document_no=model.grn_document_no,
            grn_item_no=model.grn_item_no,
            material_code=model.material_code,
            material_description=model.material_description,
            batch_number=model.batch_number,
            plant=model.plant,
            unit=model.unit,
            original_quantity=model.original_quantity,
            consumed_quantity=model.consumed_quantity,
            grn_date=model.grn_date,
            pulled_at=model.pulled_at,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )


class MaterialRequisitionRepositoryImpl(IMaterialRequisitionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, mrn_id: int) -> MaterialRequisition | None:
        stmt = (
            select(MaterialRequisitionModel)
            .options(selectinload(MaterialRequisitionModel.line_items).selectinload(MRNLineItemModel.lot))
            .where(MaterialRequisitionModel.id == mrn_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[MaterialRequisition]:
        stmt = (
            select(MaterialRequisitionModel)
            .options(selectinload(MaterialRequisitionModel.line_items).selectinload(MRNLineItemModel.lot))
            .order_by(MaterialRequisitionModel.created_date.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, mrn: MaterialRequisition) -> MaterialRequisition:
        model = MaterialRequisitionModel(
            mrn_number=mrn.mrn_number,
            status=mrn.status,
            created_by=mrn.created_by,
            modified_by=mrn.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return await self.get_by_id(model.id)  # type: ignore[return-value]

    async def update(self, mrn: MaterialRequisition) -> MaterialRequisition:
        model = await self._session.get(MaterialRequisitionModel, mrn.id)
        if model is None:
            raise ValueError(f"MaterialRequisition {mrn.id} not found")
        model.status = mrn.status
        model.submitted_by = mrn.submitted_by
        model.submitted_at = mrn.submitted_at
        model.posted_by = mrn.posted_by
        model.posted_at = mrn.posted_at
        model.modified_by = mrn.modified_by
        model.modified_date = mrn.modified_date
        await self._session.flush()
        return await self.get_by_id(mrn.id)  # type: ignore[return-value]

    async def add_line_item(self, mrn_id: int, item: MRNLineItem) -> MRNLineItem:
        model = MRNLineItemModel(
            mrn_id=mrn_id,
            line_no=item.line_no,
            lot_id=item.lot_id,
            requested_quantity=item.requested_quantity,
            project_code=item.project_code,
            status=item.status,
            created_by=item.created_by,
            modified_by=item.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return await self.get_line_item_by_id(model.id)  # type: ignore[return-value]

    async def remove_line_item(self, mrn_id: int, line_item_id: int) -> None:
        model = await self._session.get(MRNLineItemModel, line_item_id)
        if model is not None and model.mrn_id == mrn_id:
            await self._session.delete(model)
            await self._session.flush()

    async def update_line_item(self, item: MRNLineItem) -> MRNLineItem:
        model = await self._session.get(MRNLineItemModel, item.id)
        if model is None:
            raise ValueError(f"MRNLineItem {item.id} not found")
        model.status = item.status
        model.consumption_posting_id = item.consumption_posting_id
        model.modified_by = item.modified_by
        model.modified_date = item.modified_date
        await self._session.flush()
        return await self.get_line_item_by_id(item.id)  # type: ignore[return-value]

    async def get_line_item_by_id(self, line_item_id: int) -> MRNLineItem | None:
        stmt = (
            select(MRNLineItemModel)
            .options(selectinload(MRNLineItemModel.lot))
            .where(MRNLineItemModel.id == line_item_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._line_item_to_entity(model) if model else None

    async def count_by_number_prefix(self, prefix: str) -> int:
        stmt = select(func.count()).select_from(MaterialRequisitionModel).where(
            MaterialRequisitionModel.mrn_number.like(f"{prefix}%")
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    def _line_item_to_entity(model: MRNLineItemModel) -> MRNLineItem:
        return MRNLineItem(
            id=model.id,
            mrn_id=model.mrn_id,
            line_no=model.line_no,
            lot_id=model.lot_id,
            requested_quantity=model.requested_quantity,
            project_code=model.project_code,
            status=model.status,
            consumption_posting_id=model.consumption_posting_id,
            lot_material_code=model.lot.material_code if model.lot else None,
            lot_batch_number=model.lot.batch_number if model.lot else None,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )

    @classmethod
    def _to_entity(cls, model: MaterialRequisitionModel) -> MaterialRequisition:
        return MaterialRequisition(
            id=model.id,
            mrn_number=model.mrn_number,
            status=model.status,
            submitted_by=model.submitted_by,
            submitted_at=model.submitted_at,
            posted_by=model.posted_by,
            posted_at=model.posted_at,
            line_items=[cls._line_item_to_entity(li) for li in (model.line_items or [])],
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )


class ConsumptionPostingRepositoryImpl(IConsumptionPostingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, posting: ConsumptionPosting) -> ConsumptionPosting:
        model = ConsumptionPostingModel(
            line_item_id=posting.line_item_id,
            idempotency_key=posting.idempotency_key,
            status=posting.status,
            sap_doc_no=posting.sap_doc_no,
            error_message=posting.error_message,
            posted_at=posting.posted_at,
            created_by=posting.created_by,
            modified_by=posting.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, posting: ConsumptionPosting) -> ConsumptionPosting:
        model = await self._session.get(ConsumptionPostingModel, posting.id)
        if model is None:
            raise ValueError(f"ConsumptionPosting {posting.id} not found")
        model.status = posting.status
        model.sap_doc_no = posting.sap_doc_no
        model.error_message = posting.error_message
        model.posted_at = posting.posted_at
        model.modified_by = posting.modified_by
        model.modified_date = posting.modified_date
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_id(self, posting_id: int) -> ConsumptionPosting | None:
        model = await self._session.get(ConsumptionPostingModel, posting_id)
        return self._to_entity(model) if model else None

    async def get_by_idempotency_key(self, idempotency_key: str) -> ConsumptionPosting | None:
        stmt = select(ConsumptionPostingModel).where(
            ConsumptionPostingModel.idempotency_key == idempotency_key
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_mrn(self, mrn_id: int) -> list[ConsumptionPosting]:
        stmt = (
            select(ConsumptionPostingModel)
            .join(MRNLineItemModel, ConsumptionPostingModel.line_item_id == MRNLineItemModel.id)
            .where(MRNLineItemModel.mrn_id == mrn_id)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: ConsumptionPostingModel) -> ConsumptionPosting:
        return ConsumptionPosting(
            id=model.id,
            line_item_id=model.line_item_id,
            idempotency_key=model.idempotency_key,
            status=model.status,
            sap_doc_no=model.sap_doc_no,
            error_message=model.error_message,
            posted_at=model.posted_at,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
