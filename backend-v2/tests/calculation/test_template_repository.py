"""
Repository smoke tests for test templates and worksheets.

Exercises code/version uniqueness, version branching (asserting the prior
version survives untouched in the database, not just in memory), the
one-worksheet-per-test-line constraint, and worksheet round-tripping including
JSON payloads.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from src.domain.entities.test_template import TemplateStatus, WorksheetStatus
from src.domain.entities.test_template import TestTemplate as TemplateEntity
from src.domain.entities.test_template import TestWorksheet as WorksheetEntity
from src.infrastructure.database.models.product_model import ProductModel
from src.infrastructure.database.models.test_model import TestModel
from src.infrastructure.database.models.trf_model import TestRequestFormModel, TRFTestLineModel
from src.infrastructure.database.repositories.test_template_repository_impl import (
    TestTemplateRepositoryImpl,
    TestWorksheetRepositoryImpl,
)

DEFINITION = {
    "resultRef": "g.out",
    "groups": [
        {
            "key": "g",
            "kind": "singleton",
            "fields": [
                {"key": "a", "kind": "input"},
                {"key": "out", "kind": "calculated", "expression": "a * 2"},
            ],
        }
    ],
}


async def _seed_test(session) -> TestModel:
    test = TestModel(code="TST-01", name="Assay", type="Quantitative", status="Active")
    session.add(test)
    await session.flush()
    return test


async def _seed_test_line(session) -> TRFTestLineModel:
    """A TRF test line, plus the product and TRF rows its FKs require."""
    product = ProductModel(code="PRD-1", name="Product One", status="Active")
    session.add(product)
    await session.flush()

    trf = TestRequestFormModel(
        trf_number="TRF-20260805-0001",
        product_id=product.id,
        batch_number="B-1",
        status="InProgress",
    )
    session.add(trf)
    await session.flush()

    test = await _seed_test(session)
    line = TRFTestLineModel(trf_id=trf.id, line_no=1, test_id=test.id)
    session.add(line)
    await session.flush()
    return line


def _template(test_id: int, **overrides) -> TemplateEntity:
    base = dict(
        code="TPL-A1-0001",
        name="Assay by HPLC",
        archetype="A1",
        test_id=test_id,
        definition=DEFINITION,
        created_by="admin",
        modified_by="admin",
    )
    base.update(overrides)
    return TemplateEntity(**base)


@pytest.mark.asyncio
async def test_create_and_fetch_template(db_session):
    repo = TestTemplateRepositoryImpl(db_session)
    test = await _seed_test(db_session)

    created = await repo.create(_template(test.id))
    assert created.id > 0
    assert created.status == TemplateStatus.DRAFT.value
    assert created.version == 1
    # Denormalized test projection is populated for API responses.
    assert created.test_code == "TST-01"
    assert created.test_name == "Assay"

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.definition == DEFINITION


@pytest.mark.asyncio
async def test_code_and_version_pair_is_unique(db_session):
    repo = TestTemplateRepositoryImpl(db_session)
    test = await _seed_test(db_session)
    await repo.create(_template(test.id))

    with pytest.raises(IntegrityError):
        await repo.create(_template(test.id))


@pytest.mark.asyncio
async def test_same_code_different_version_is_allowed(db_session):
    repo = TestTemplateRepositoryImpl(db_session)
    test = await _seed_test(db_session)
    await repo.create(_template(test.id, version=1))
    v2 = await repo.create(_template(test.id, version=2))
    assert v2.version == 2

    versions = await repo.list_versions_of("TPL-A1-0001")
    # Newest first.
    assert [v.version for v in versions] == [2, 1]


@pytest.mark.asyncio
async def test_versioning_persists_without_disturbing_the_prior_version(db_session):
    """
    Property 10 at the persistence layer: branching and approving a new version
    must leave the earlier row's definition and approval intact on disk.
    """
    repo = TestTemplateRepositoryImpl(db_session)
    test = await _seed_test(db_session)

    v1 = await repo.create(_template(test.id))
    v1.submit_for_approval("admin")
    v1.approve("qa", v1.created_date)
    v1 = await repo.update(v1)

    draft = v1.new_version("admin")
    draft.definition["groups"][0]["fields"][1]["expression"] = "a * 999"
    v2 = await repo.create(draft)

    reloaded_v1 = await repo.get_by_id(v1.id)
    assert reloaded_v1 is not None
    assert reloaded_v1.status == TemplateStatus.ACTIVE.value
    assert reloaded_v1.approved_by == "qa"
    assert reloaded_v1.definition["groups"][0]["fields"][1]["expression"] == "a * 2"

    reloaded_v2 = await repo.get_by_id(v2.id)
    assert reloaded_v2 is not None
    assert reloaded_v2.status == TemplateStatus.DRAFT.value
    assert reloaded_v2.definition["groups"][0]["fields"][1]["expression"] == "a * 999"


@pytest.mark.asyncio
async def test_superseded_pointer_round_trips(db_session):
    repo = TestTemplateRepositoryImpl(db_session)
    test = await _seed_test(db_session)
    v1 = await repo.create(_template(test.id))
    v2 = await repo.create(_template(test.id, version=2))

    v1.mark_superseded_by(v2.id, "qa")
    await repo.update(v1)

    reloaded = await repo.get_by_id(v1.id)
    assert reloaded is not None
    assert reloaded.superseded_by_id == v2.id


@pytest.mark.asyncio
async def test_list_active_for_test_excludes_unapproved(db_session):
    repo = TestTemplateRepositoryImpl(db_session)
    test = await _seed_test(db_session)

    draft = await repo.create(_template(test.id, version=1))
    active = await repo.create(_template(test.id, version=2))
    active.submit_for_approval("admin")
    active.approve("qa", active.created_date)
    await repo.update(active)

    selectable = await repo.list_active_for_test(test.id)
    ids = {t.id for t in selectable}
    assert active.id in ids
    assert draft.id not in ids


@pytest.mark.asyncio
async def test_count_by_code_prefix_counts_distinct_codes_not_rows(db_session):
    """
    Versions share a code, so counting rows would skip sequence numbers as
    templates get versioned — the generator needs distinct codes.
    """
    repo = TestTemplateRepositoryImpl(db_session)
    test = await _seed_test(db_session)

    await repo.create(_template(test.id, code="TPL-A1-0001", version=1))
    await repo.create(_template(test.id, code="TPL-A1-0001", version=2))
    await repo.create(_template(test.id, code="TPL-A1-0002", version=1))
    # A different archetype must not be counted.
    await repo.create(_template(test.id, code="TPL-A4-0001", version=1))

    assert await repo.count_by_code_prefix("TPL-A1-") == 2
    assert await repo.count_by_code_prefix("TPL-A4-") == 1
    assert await repo.count_by_code_prefix("TPL-A6-") == 0


@pytest.mark.asyncio
async def test_get_by_code_and_version(db_session):
    repo = TestTemplateRepositoryImpl(db_session)
    test = await _seed_test(db_session)
    await repo.create(_template(test.id, version=1))
    await repo.create(_template(test.id, version=2))

    found = await repo.get_by_code_and_version("TPL-A1-0001", 2)
    assert found is not None
    assert found.version == 2
    assert await repo.get_by_code_and_version("TPL-A1-0001", 99) is None


@pytest.mark.asyncio
async def test_worksheet_create_and_fetch_by_test_line(db_session):
    template_repo = TestTemplateRepositoryImpl(db_session)
    ws_repo = TestWorksheetRepositoryImpl(db_session)

    line = await _seed_test_line(db_session)
    template = await template_repo.create(_template(line.test_id))

    created = await ws_repo.create(
        WorksheetEntity(
            trf_test_line_id=line.id,
            template_id=template.id,
            template_version=template.version,
            context_values={"label_claim": 50.0},
            group_values={"g": [{"a": 21.0}]},
            created_by="analyst",
            modified_by="analyst",
        )
    )
    assert created.id > 0
    assert created.status == WorksheetStatus.IN_PROGRESS.value
    assert created.template_code == "TPL-A1-0001"

    by_line = await ws_repo.get_by_test_line(line.id)
    assert by_line is not None
    assert by_line.id == created.id
    # JSON payloads survive the round trip.
    assert by_line.context_values == {"label_claim": 50.0}
    assert by_line.group_values["g"][0]["a"] == 21.0


@pytest.mark.asyncio
async def test_one_worksheet_per_test_line(db_session):
    template_repo = TestTemplateRepositoryImpl(db_session)
    ws_repo = TestWorksheetRepositoryImpl(db_session)

    line = await _seed_test_line(db_session)
    template = await template_repo.create(_template(line.test_id))

    await ws_repo.create(
        WorksheetEntity(trf_test_line_id=line.id, template_id=template.id)
    )
    with pytest.raises(IntegrityError):
        await ws_repo.create(
            WorksheetEntity(trf_test_line_id=line.id, template_id=template.id)
        )


@pytest.mark.asyncio
async def test_worksheet_confirmation_round_trips(db_session):
    template_repo = TestTemplateRepositoryImpl(db_session)
    ws_repo = TestWorksheetRepositoryImpl(db_session)

    line = await _seed_test_line(db_session)
    template = await template_repo.create(_template(line.test_id))
    ws = await ws_repo.create(
        WorksheetEntity(trf_test_line_id=line.id, template_id=template.id)
    )

    snapshot = {"values": {"g.out": 42.0}, "criteria": [{"key": "sst", "passed": True}]}
    ws.confirm("analyst", ws.created_date, snapshot, "42.0")
    await ws_repo.update(ws)

    reloaded = await ws_repo.get_by_id(ws.id)
    assert reloaded is not None
    assert reloaded.is_confirmed is True
    assert reloaded.reportable_result == "42.0"
    assert reloaded.computed_snapshot == snapshot
    assert reloaded.confirmed_by == "analyst"


@pytest.mark.asyncio
async def test_list_by_trf_returns_worksheets_in_line_order(db_session):
    template_repo = TestTemplateRepositoryImpl(db_session)
    ws_repo = TestWorksheetRepositoryImpl(db_session)

    line_1 = await _seed_test_line(db_session)
    template = await template_repo.create(_template(line_1.test_id))

    #  A second line on the same TRF.
    line_2 = TRFTestLineModel(trf_id=line_1.trf_id, line_no=2, test_id=line_1.test_id)
    db_session.add(line_2)
    await db_session.flush()

    await ws_repo.create(
        WorksheetEntity(trf_test_line_id=line_2.id, template_id=template.id)
    )
    await ws_repo.create(
        WorksheetEntity(trf_test_line_id=line_1.id, template_id=template.id)
    )

    worksheets = await ws_repo.list_by_trf(line_1.trf_id)
    assert len(worksheets) == 2
    assert [w.trf_test_line_id for w in worksheets] == [line_1.id, line_2.id]


@pytest.mark.asyncio
async def test_missing_records_return_none(db_session):
    template_repo = TestTemplateRepositoryImpl(db_session)
    ws_repo = TestWorksheetRepositoryImpl(db_session)
    assert await template_repo.get_by_id(9999) is None
    assert await ws_repo.get_by_id(9999) is None
    assert await ws_repo.get_by_test_line(9999) is None
