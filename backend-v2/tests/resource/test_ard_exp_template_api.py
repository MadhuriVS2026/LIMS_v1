"""
Integration tests for the ARD-EXP-TEMPLATES Master endpoints.

Drives the real ASGI app, overriding only `get_session` and `get_current_user`
(mirroring tests/resource/test_project_api.py). Asserts routing, role gating,
validation, and the full CRUD lifecycle for /ard-exp-templates.
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
    "template_name": "ARD-EXP-Dissolution",
    "comments": "Standard dissolution experiment template",
    "primary_department": "Analytical R&D",
    "plant": "Ahmedabad",
    "location": "Block A",
    "is_active": True,
    "secondary_department": "Formulation R&D",
    "module": "ARD",
}


@pytest.mark.asyncio
async def test_list_empty_then_populated(client):
    assert (await client.get("/ard-exp-templates")).json() == []

    created = await client.post("/ard-exp-templates", json=_VALID)
    assert created.status_code == 200
    body = created.json()
    assert body["template_name"] == "ARD-EXP-Dissolution"
    assert body["is_active"] is True
    assert body["primary_department"] == "Analytical R&D"
    assert body["id"] is not None

    listed = await client.get("/ard-exp-templates")
    assert listed.status_code == 200
    assert [t["template_name"] for t in listed.json()] == ["ARD-EXP-Dissolution"]


@pytest.mark.asyncio
async def test_update_template(client):
    created = (await client.post("/ard-exp-templates", json=_VALID)).json()
    tid = created["id"]

    payload = {**_VALID, "template_name": "ARD-EXP-Assay", "is_active": False, "module": "QC"}
    updated = await client.put(f"/ard-exp-templates/{tid}", json=payload)
    assert updated.status_code == 200
    body = updated.json()
    assert body["template_name"] == "ARD-EXP-Assay"
    assert body["is_active"] is False
    assert body["module"] == "QC"


@pytest.mark.asyncio
async def test_delete_template(client):
    created = (await client.post("/ard-exp-templates", json=_VALID)).json()
    tid = created["id"]

    deleted = await client.delete(f"/ard-exp-templates/{tid}")
    assert deleted.status_code == 204

    assert (await client.get("/ard-exp-templates")).json() == []


@pytest.mark.asyncio
async def test_update_missing_is_404(client):
    assert (await client.put("/ard-exp-templates/9999", json=_VALID)).status_code == 404


@pytest.mark.asyncio
async def test_delete_missing_is_404(client):
    assert (await client.delete("/ard-exp-templates/9999")).status_code == 404


@pytest.mark.asyncio
async def test_create_requires_admin(client):
    as_user(make_analyst_user())
    assert (await client.post("/ard-exp-templates", json=_VALID)).status_code == 403

    as_user(make_admin_user())
    assert (await client.post("/ard-exp-templates", json=_VALID)).status_code == 200


@pytest.mark.asyncio
async def test_mutations_require_admin(client):
    created = (await client.post("/ard-exp-templates", json=_VALID)).json()
    tid = created["id"]

    as_user(make_analyst_user())
    assert (await client.put(f"/ard-exp-templates/{tid}", json=_VALID)).status_code == 403
    assert (await client.delete(f"/ard-exp-templates/{tid}")).status_code == 403


@pytest.mark.asyncio
async def test_create_missing_required_field_is_422(client):
    payload = {k: v for k, v in _VALID.items() if k != "template_name"}
    assert (await client.post("/ard-exp-templates", json=payload)).status_code == 422
