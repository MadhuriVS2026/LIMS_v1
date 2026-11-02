"""
Integration tests for the Project Master endpoints.

Drives the real ASGI app, overriding only `get_session` and `get_current_user`
(mirroring tests/calculation/test_coa_api.py). Asserts routing, role gating,
and validation for GET /projects and POST /projects.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.v1.dependencies import get_current_user, get_session
from src.domain.entities.user import User
from src.main import app
from tests.conftest import make_admin_user, make_analyst_user

_CURRENT: dict[str, User] = {}


def as_user(u: User) -> None:
    _CURRENT["user"] = u


@pytest_asyncio.fixture
async def client(db_session):
    async def _session_override():
        yield db_session

    async def _user_override() -> User:
        return _CURRENT["user"]

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user] = _user_override
    as_user(make_admin_user())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as ac:
        yield ac

    app.dependency_overrides.clear()
    _CURRENT.clear()


_VALID = {
    "project_id": "PID-2026-001",
    "product_name": "Doxorubicin Liposome",
    "product_code": "PRD-DOXO-01",
    "project_code": "PRJ-ONCO-01",
    "project_code_academic": "AR-ONCO-01",
    "bd_code_sap": "BD-100231",
    "group_lead": "Suresh Iyer",
    "location": "Ahmedabad",
    "market": "US",
    "license": "ANDA",
    "status": "Active",
}


@pytest.mark.asyncio
async def test_list_projects_empty_then_populated(client):
    assert (await client.get("/projects")).json() == []

    created = await client.post("/projects", json=_VALID)
    assert created.status_code == 200
    body = created.json()
    assert body["project_id"] == "PID-2026-001"
    assert body["status"] == "Active"
    assert body["id"] is not None

    listed = await client.get("/projects")
    assert listed.status_code == 200
    assert [p["project_id"] for p in listed.json()] == ["PID-2026-001"]


@pytest.mark.asyncio
async def test_create_requires_admin(client):
    as_user(make_analyst_user())
    assert (await client.post("/projects", json=_VALID)).status_code == 403

    as_user(make_admin_user())
    assert (await client.post("/projects", json=_VALID)).status_code == 200


@pytest.mark.asyncio
async def test_create_missing_required_field_is_422(client):
    payload = {k: v for k, v in _VALID.items() if k != "product_name"}
    assert (await client.post("/projects", json=payload)).status_code == 422
