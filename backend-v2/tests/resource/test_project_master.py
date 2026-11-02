"""
Unit tests for the Project Master slice of ResourceService.

Builds a ResourceService from the real repository implementations against the
in-memory `db_session` fixture (mirroring the Instruments/Standards convention).
Only the Project Master repos matter here; the other resource repos are wired
with their real impls so the service constructs exactly as it does in the DI
container.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.application.services.resource_service import ResourceService
from src.infrastructure.database.models.audit_log_model import AuditLogModel
from src.infrastructure.database.repositories.audit_repository_impl import (
    AuditLogRepositoryImpl,
)
from src.infrastructure.database.repositories.resource_repositories_impl import (
    ARDExpTemplateRepositoryImpl,
    ChemicalRepositoryImpl,
    ColumnRepositoryImpl,
    InstrumentRepositoryImpl,
    ProjectRepositoryImpl,
    ReferenceStandardRepositoryImpl,
    VolumetricSolutionRepositoryImpl,
)
from tests.conftest import make_admin_user


def _service(session) -> ResourceService:
    return ResourceService(
        InstrumentRepositoryImpl(session),
        ColumnRepositoryImpl(session),
        ReferenceStandardRepositoryImpl(session),
        ChemicalRepositoryImpl(session),
        VolumetricSolutionRepositoryImpl(session),
        ProjectRepositoryImpl(session),
        ARDExpTemplateRepositoryImpl(session),
        AuditLogRepositoryImpl(session),
    )


async def _create_full(session, actor, **overrides):
    payload = dict(
        project_id="PID-2026-001", product_name="Doxorubicin Liposome",
        product_code="PRD-DOXO-01", project_code="PRJ-ONCO-01",
        project_code_academic="AR-ONCO-01", bd_code_sap="BD-100231",
        group_lead="Suresh Iyer", location="Ahmedabad", market="US",
        start_date=None, end_date=None, license="ANDA",
        comments="dev program", status="Active",
        requested_person="BD Team", remarks="priority",
    )
    payload.update(overrides)
    return await _service(session).create_project(actor=actor, **payload)


@pytest.mark.asyncio
async def test_create_project_persists_all_fields(db_session):
    actor = make_admin_user()
    created = await _create_full(db_session, actor)

    assert created.id is not None
    assert created.project_id == "PID-2026-001"
    assert created.product_name == "Doxorubicin Liposome"
    assert created.product_code == "PRD-DOXO-01"
    assert created.project_code == "PRJ-ONCO-01"
    assert created.project_code_academic == "AR-ONCO-01"
    assert created.bd_code_sap == "BD-100231"
    assert created.group_lead == "Suresh Iyer"
    assert created.location == "Ahmedabad"
    assert created.market == "US"
    assert created.license == "ANDA"
    assert created.comments == "dev program"
    assert created.status == "Active"
    assert created.requested_person == "BD Team"
    assert created.remarks == "priority"
    assert created.created_by == actor.username


@pytest.mark.asyncio
async def test_create_project_writes_audit_row(db_session):
    actor = make_admin_user()
    created = await _create_full(db_session, actor)

    rows = (
        await db_session.execute(
            select(AuditLogModel).where(AuditLogModel.table_name == "project_master")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "CREATE"
    assert rows[0].record_id == created.id
    assert rows[0].username == actor.username


@pytest.mark.asyncio
async def test_list_projects_returns_created_rows(db_session):
    actor = make_admin_user()
    await _create_full(db_session, actor, project_id="PID-2026-001")
    await _create_full(db_session, actor, project_id="PID-2026-002")

    projects = await _service(db_session).list_projects()
    assert {p.project_id for p in projects} == {"PID-2026-001", "PID-2026-002"}


@pytest.mark.asyncio
async def test_duplicate_project_id_raises_integrity_error(db_session):
    actor = make_admin_user()
    await _create_full(db_session, actor, project_id="PID-DUP")
    with pytest.raises(IntegrityError):
        await _create_full(db_session, actor, project_id="PID-DUP")


@pytest.mark.asyncio
async def test_status_defaults_to_active_when_none(db_session):
    actor = make_admin_user()
    created = await _create_full(db_session, actor, status=None)
    assert created.status == "Active"
