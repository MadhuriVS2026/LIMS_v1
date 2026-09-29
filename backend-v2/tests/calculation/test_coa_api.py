"""
Integration tests for the COA endpoints.

Drives the real ASGI app, overriding only `get_session` and `get_current_user`,
and stubbing `AuthService.verify_esignature` — these tests are about routing,
role gating and status codes, not password hashing.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.v1.dependencies import get_current_user, get_session
from src.application.services.auth_service import AuthService
from src.domain.entities.user import User
from src.main import app
from tests.calculation.conftest import seed_test, user
from tests.calculation.test_coa_service import (
    BATCH,
    QA,
    seed_product,
    seed_released_trf,
    seed_spec,
)

_CURRENT: dict[str, User] = {}


def as_user(u: User) -> None:
    _CURRENT["user"] = u


@pytest_asyncio.fixture
async def client(db_session, monkeypatch):
    async def _session_override():
        yield db_session

    async def _user_override() -> User:
        return _CURRENT["user"]

    async def _verify_ok(self, current_user, password):  # noqa: ANN001
        return True

    monkeypatch.setattr(AuthService, "verify_esignature", _verify_ok)

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user] = _user_override
    as_user(user(QA, "QA", user_id=3))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as ac:
        yield ac

    app.dependency_overrides.clear()
    _CURRENT.clear()


async def _scenario(db_session, result="99.8 %"):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_spec(db_session, product, [(assay.id, 95.0, 105.0, None, True)])
    await seed_released_trf(db_session, product, [(assay.id, "95.0 to 105.0 %", result)])
    return product, assay


@pytest.mark.asyncio
async def test_generate_get_and_list(client, db_session):
    product, _assay = await _scenario(db_session)

    created = await client.post(
        "/coa",
        json={
            "product_id": product.id,
            "batch_number": BATCH,
            "remarks": "For release",
            "password": "pw",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["coa_number"].startswith("COA-")
    assert body["overall_verdict"] == "Pass"
    assert body["test_count"] == 1
    assert body["released_by"] == QA
    assert body["snapshot"]["tests"][0]["verdict"] == "Pass"

    fetched = await client.get(f"/coa/{body['id']}")
    assert fetched.status_code == 200
    #  The snapshot returned on GET is byte-identical to the one issued.
    assert fetched.json()["snapshot"] == body["snapshot"]

    listed = await client.get("/coa")
    assert listed.status_code == 200
    assert [c["id"] for c in listed.json()] == [body["id"]]
    #  The list projection omits the snapshot, which is the bulk of the record.
    assert "snapshot" not in listed.json()[0]


@pytest.mark.asyncio
async def test_list_filters(client, db_session):
    product, _assay = await _scenario(db_session)
    await client.post(
        "/coa", json={"product_id": product.id, "batch_number": BATCH, "password": "pw"}
    )

    assert len((await client.get("/coa", params={"product_id": product.id})).json()) == 1
    assert len((await client.get("/coa", params={"batch_number": BATCH})).json()) == 1
    assert (await client.get("/coa", params={"batch_number": "NOPE"})).json() == []


@pytest.mark.asyncio
async def test_generation_is_restricted_to_qa_and_admin(client, db_session):
    product, _assay = await _scenario(db_session)
    payload = {"product_id": product.id, "batch_number": BATCH, "password": "pw"}

    for role in ("Analyst", "Supervisor"):
        as_user(user("someone", role, user_id=8))
        assert (await client.post("/coa", json=payload)).status_code == 403

    as_user(user("admin", "Admin", user_id=2))
    assert (await client.post("/coa", json=payload)).status_code == 200


@pytest.mark.asyncio
async def test_a_certificate_is_readable_by_any_role(client, db_session):
    product, _assay = await _scenario(db_session)
    created = (
        await client.post(
            "/coa", json={"product_id": product.id, "batch_number": BATCH, "password": "pw"}
        )
    ).json()

    for role in ("Admin", "Analyst", "Supervisor", "QA"):
        as_user(user("someone", role, user_id=9))
        assert (await client.get(f"/coa/{created['id']}")).status_code == 200
        assert (await client.get("/coa")).status_code == 200


@pytest.mark.asyncio
async def test_generation_requires_a_password(client, db_session):
    product, _assay = await _scenario(db_session)
    response = await client.post(
        "/coa", json={"product_id": product.id, "batch_number": BATCH}
    )
    #  A missing e-signature is a schema error, not a silent unsigned release.
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_a_batch_with_no_released_results_is_a_400(client, db_session):
    product, _assay = await _scenario(db_session)
    response = await client.post(
        "/coa", json={"product_id": product.id, "batch_number": "NO-SUCH", "password": "pw"}
    )
    assert response.status_code == 400
    assert "No released Test Request Forms" in response.json()["detail"]
    assert (await client.get("/coa")).json() == []


@pytest.mark.asyncio
async def test_unknown_product_is_a_404(client, db_session):
    await _scenario(db_session)
    response = await client.post(
        "/coa", json={"product_id": 9999, "batch_number": BATCH, "password": "pw"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unknown_coa_is_a_404(client, db_session):
    await _scenario(db_session)
    assert (await client.get("/coa/9999")).status_code == 404


@pytest.mark.asyncio
async def test_preview_shows_a_failure_without_issuing(client, db_session):
    #  110.5 is outside 95–105.
    product, _assay = await _scenario(db_session, result="110.5 %")

    response = await client.post(
        "/coa/preview", json={"product_id": product.id, "batch_number": BATCH}
    )
    assert response.status_code == 200
    snapshot = response.json()["snapshot"]
    assert snapshot["overall_verdict"] == "Fail"
    assert snapshot["coa_number"] is None
    assert snapshot["issued_by"] is None

    #  Nothing was issued.
    assert (await client.get("/coa")).json() == []


@pytest.mark.asyncio
async def test_preview_is_restricted_to_the_issuer_roles(client, db_session):
    """Preview is a pre-signature review step, not a document anyone needs to read."""
    product, _assay = await _scenario(db_session)
    payload = {"product_id": product.id, "batch_number": BATCH}

    for role in ("Analyst", "Supervisor"):
        as_user(user("someone", role, user_id=8))
        assert (await client.post("/coa/preview", json=payload)).status_code == 403

    as_user(user(QA, "QA", user_id=3))
    assert (await client.post("/coa/preview", json=payload)).status_code == 200


@pytest.mark.asyncio
async def test_there_is_no_way_to_edit_or_delete_a_certificate(client, db_session):
    """
    Immutability is structural: no route exists, so this is a 405 rather than a
    permission decision that could be misconfigured later.
    """
    product, _assay = await _scenario(db_session)
    created = (
        await client.post(
            "/coa", json={"product_id": product.id, "batch_number": BATCH, "password": "pw"}
        )
    ).json()

    assert (await client.put(f"/coa/{created['id']}", json={})).status_code == 405
    assert (await client.delete(f"/coa/{created['id']}")).status_code == 405
