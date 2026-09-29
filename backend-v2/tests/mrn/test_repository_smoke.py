"""
Smoke tests for MRN repository implementations (Task 4.2/4.5/4.6).
Exercises upsert-by-natural-key, availability filtering, MRN header + line
item CRUD, and consumption posting CRUD against the shared in-memory db_session
fixture.
"""
import pytest

from src.domain.entities.mrn import ConsumptionPosting, MaterialRequisition, MRNLineItem, MRNMaterialLot
from src.infrastructure.database.repositories.mrn_repository_impl import (
    ConsumptionPostingRepositoryImpl,
    MaterialRequisitionRepositoryImpl,
    MRNMaterialLotRepositoryImpl,
)


@pytest.mark.asyncio
async def test_lot_upsert_and_natural_key_lookup(db_session):
    repo = MRNMaterialLotRepositoryImpl(db_session)
    lot = MRNMaterialLot(
        grn_document_no="GRN001", grn_item_no="0001", material_code="MAT-1",
        plant="EP22", unit="KG", original_quantity=100.0,
    )
    created = await repo.upsert(lot)
    assert created.id > 0
    assert created.status == "Available"

    # Upsert again with the same natural key should update, not duplicate.
    lot.material_description = "Updated description"
    lot.original_quantity = 150.0
    updated = await repo.upsert(lot)
    assert updated.id == created.id
    assert updated.original_quantity == 150.0

    fetched = await repo.get_by_natural_key("GRN001", "0001")
    assert fetched is not None
    assert fetched.material_description == "Updated description"

    all_lots = await repo.list_all()
    assert len(all_lots) == 1


@pytest.mark.asyncio
async def test_list_available_excludes_exhausted_lots(db_session):
    repo = MRNMaterialLotRepositoryImpl(db_session)
    available = await repo.upsert(
        MRNMaterialLot(grn_document_no="G1", grn_item_no="1", material_code="M1", plant="EP22", unit="KG", original_quantity=10.0)
    )
    exhausted = await repo.upsert(
        MRNMaterialLot(grn_document_no="G2", grn_item_no="1", material_code="M2", plant="EP22", unit="KG", original_quantity=5.0)
    )
    exhausted.consumed_quantity = 5.0
    await repo.update(exhausted)

    result = await repo.list_available()
    ids = {lot.id for lot in result}
    assert available.id in ids
    assert exhausted.id not in ids


@pytest.mark.asyncio
async def test_mrn_header_and_line_item_crud(db_session):
    lot_repo = MRNMaterialLotRepositoryImpl(db_session)
    mrn_repo = MaterialRequisitionRepositoryImpl(db_session)

    lot = await lot_repo.upsert(
        MRNMaterialLot(grn_document_no="G3", grn_item_no="1", material_code="M3", plant="EP22", unit="KG", original_quantity=50.0)
    )

    mrn = await mrn_repo.create(MaterialRequisition(mrn_number="MRN-20260101-0001", created_by="analyst"))
    assert mrn.id > 0
    assert mrn.status == "Draft"

    line = await mrn_repo.add_line_item(
        mrn.id, MRNLineItem(line_no=1, lot_id=lot.id, requested_quantity=10.0, project_code="PRJ-1", created_by="analyst")
    )
    assert line.id > 0
    assert line.lot_material_code == "M3"

    fetched_mrn = await mrn_repo.get_by_id(mrn.id)
    assert fetched_mrn is not None
    assert len(fetched_mrn.line_items) == 1

    count = await mrn_repo.count_by_number_prefix("MRN-20260101-")
    assert count == 1

    await mrn_repo.remove_line_item(mrn.id, line.id)
    fetched_after_remove = await mrn_repo.get_by_id(mrn.id)
    assert len(fetched_after_remove.line_items) == 0


@pytest.mark.asyncio
async def test_consumption_posting_crud(db_session):
    lot_repo = MRNMaterialLotRepositoryImpl(db_session)
    mrn_repo = MaterialRequisitionRepositoryImpl(db_session)
    posting_repo = ConsumptionPostingRepositoryImpl(db_session)

    lot = await lot_repo.upsert(
        MRNMaterialLot(grn_document_no="G4", grn_item_no="1", material_code="M4", plant="EP22", unit="KG", original_quantity=50.0)
    )
    mrn = await mrn_repo.create(MaterialRequisition(mrn_number="MRN-20260101-0002", created_by="analyst"))
    line = await mrn_repo.add_line_item(
        mrn.id, MRNLineItem(line_no=1, lot_id=lot.id, requested_quantity=10.0, project_code="PRJ-1", created_by="analyst")
    )

    posting = await posting_repo.create(
        ConsumptionPosting(line_item_id=line.id, idempotency_key="MRN-20260101-0002-1", status="Pending")
    )
    assert posting.id > 0

    fetched = await posting_repo.get_by_idempotency_key("MRN-20260101-0002-1")
    assert fetched is not None
    assert fetched.id == posting.id

    posting.status = "Success"
    posting.sap_doc_no = "5000123456"
    updated = await posting_repo.update(posting)
    assert updated.status == "Success"
    assert updated.sap_doc_no == "5000123456"

    by_mrn = await posting_repo.list_by_mrn(mrn.id)
    assert len(by_mrn) == 1
