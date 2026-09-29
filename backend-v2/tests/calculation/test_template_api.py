"""
Integration tests for the template and worksheet endpoints.

These drive the real ASGI app through `httpx.ASGITransport`, with only two
dependencies overridden:

  * `get_session` — pointed at the in-memory test session
  * `get_current_user` — pointed at a role we control

Overriding `get_current_user` rather than `require_role` is deliberate. Each
`require_role(...)` call builds its own closure, so it cannot be overridden by
key; leaving it in place means the 403s asserted below come from the app's real
role guard, not from a test double.

E-signature verification is stubbed at `AuthService.verify_esignature`, since
these tests are about routing and authorisation, not password hashing — the
signature path itself is covered by the auth tests.

Covers task 8.6: role-gated 403s per endpoint, the full worksheet lifecycle
through HTTP (create -> save -> preview -> confirm -> result on the test line),
and confirm refused while a blocking criterion fails.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.v1.dependencies import get_current_user, get_session
from src.application.services.auth_service import AuthService
from src.domain.entities.user import User
from src.infrastructure.database.models.test_template_model import TestTemplateModel
from src.main import app
from tests.calculation.conftest import seed_test, seed_trf_with_line, set_trf_status, user
from tests.calculation.test_worksheet_service import DEFINITION, GOOD_STD, BAD_STD

ANALYST = "analyst"

#  Mutable holder so a test can switch roles mid-flight without rebuilding the
#  client — the lifecycle tests move between Analyst and QA.
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
    as_user(user(ANALYST, "Analyst"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        yield ac

    app.dependency_overrides.clear()
    _CURRENT.clear()


async def _seed_scenario(session):
    """A TRF at `InProgress` with an Active template matching its one test line."""
    test = await seed_test(session)
    trf, line = await seed_trf_with_line(session, status="InProgress", test=test)
    trf.analyst_accepted_by = ANALYST
    template = TestTemplateModel(
        code="TPL-A1-0001",
        name="Assay by HPLC",
        archetype="A1",
        test_id=test.id,
        version=1,
        status="Active",
        result_unit="%",
        definition=DEFINITION,
        created_by="admin",
        modified_by="admin",
    )
    session.add(template)
    await session.flush()
    return test, trf, line, template


# ── Template endpoints ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_template_catalogue_is_readable_by_any_role(client, db_session):
    test, _trf, _line, template = await _seed_scenario(db_session)

    for role in ("Admin", "Analyst", "Supervisor", "QA"):
        as_user(user("someone", role))
        response = await client.get("/test-templates")
        assert response.status_code == 200
        assert [t["code"] for t in response.json()] == ["TPL-A1-0001"]
        #  The list projection omits the definition body.
        assert "definition" not in response.json()[0]

    response = await client.get(f"/test-templates/{template.id}")
    assert response.status_code == 200
    assert response.json()["definition"]["resultRef"] == "sample.assay"

    response = await client.get(f"/test-templates/for-test/{test.id}")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_authoring_endpoints_are_admin_only(client, db_session):
    test, _trf, _line, template = await _seed_scenario(db_session)
    payload = {
        "name": "New template",
        "archetype": "A1",
        "test_id": test.id,
        "result_unit": "%",
        "definition": DEFINITION,
    }

    for role in ("Analyst", "Supervisor", "QA"):
        as_user(user("someone", role))
        assert (await client.post("/test-templates", json=payload)).status_code == 403
        assert (
            await client.put(
                f"/test-templates/{template.id}/definition", json={"definition": DEFINITION}
            )
        ).status_code == 403
        assert (
            await client.post(f"/test-templates/{template.id}/new-version")
        ).status_code == 403
        assert (
            await client.post(f"/test-templates/{template.id}/deactivate", json={})
        ).status_code == 403

    as_user(user("admin", "Admin"))
    response = await client.post("/test-templates", json=payload)
    assert response.status_code == 200
    assert response.json()["code"] == "TPL-A1-0002"
    assert response.json()["status"] == "Draft"


@pytest.mark.asyncio
async def test_a_malformed_definition_is_a_400_not_a_500(client, db_session):
    test, _trf, _line, _template = await _seed_scenario(db_session)
    as_user(user("admin", "Admin"))

    response = await client.post(
        "/test-templates",
        json={
            "name": "Circular",
            "archetype": "A1",
            "test_id": test.id,
            "definition": {
                "groups": [
                    {
                        "key": "g",
                        "kind": "singleton",
                        "fields": [
                            {"key": "a", "kind": "calculated", "expression": "b + 1"},
                            {"key": "b", "kind": "calculated", "expression": "a + 1"},
                        ],
                    }
                ]
            },
        },
    )
    assert response.status_code == 400
    assert "Circular reference" in response.json()["detail"]


@pytest.mark.asyncio
async def test_approval_is_e_signed_and_restricted_to_reviewers(client, db_session):
    test, _trf, _line, _template = await _seed_scenario(db_session)
    as_user(user("admin", "Admin"))
    created = (
        await client.post(
            "/test-templates",
            json={
                "name": "Second",
                "archetype": "A2",
                "test_id": test.id,
                "definition": DEFINITION,
            },
        )
    ).json()
    assert (await client.post(f"/test-templates/{created['id']}/submit")).status_code == 200

    #  An Analyst is outside the reviewer set.
    as_user(user(ANALYST, "Analyst"))
    response = await client.post(
        f"/test-templates/{created['id']}/approve", json={"password": "pw"}
    )
    assert response.status_code == 403

    #  A missing password is a schema error, not a silent approval.
    as_user(user("qa1", "QA", user_id=3))
    assert (
        await client.post(f"/test-templates/{created['id']}/approve", json={})
    ).status_code == 422

    response = await client.post(
        f"/test-templates/{created['id']}/approve",
        json={"password": "pw", "comments": "Verified against the source workbook"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Active"
    assert response.json()["approved_by"] == "qa1"


@pytest.mark.asyncio
async def test_unknown_template_is_a_404(client, db_session):
    await _seed_scenario(db_session)
    as_user(user("admin", "Admin"))
    assert (await client.get("/test-templates/9999")).status_code == 404


# ── Worksheet lifecycle through HTTP ─────────────────────────────────


@pytest.mark.asyncio
async def test_full_worksheet_lifecycle(client, db_session):
    _test, trf, line, template = await _seed_scenario(db_session)
    as_user(user(ANALYST, "Analyst"))

    #  1. Create — returns the worksheet, its template and the initial computed state.
    response = await client.post(
        f"/trf/test-lines/{line.id}/worksheet", json={"template_id": template.id}
    )
    assert response.status_code == 200
    body = response.json()
    worksheet_id = body["worksheet"]["id"]
    assert body["worksheet"]["template_version"] == 1
    assert body["worksheet"]["context_values"]["batch"] == "B-2601"
    assert body["template"]["code"] == "TPL-A1-0001"
    #  Nothing entered yet, so the assay is blank rather than zero.
    assert body["computed"]["values"]["sample.assay"] is None

    #  2. Preview — computes but must not persist.
    response = await client.post(
        f"/worksheets/{worksheet_id}/preview",
        json={"group_values": {"std": GOOD_STD, "sample": [{"area": 101_000}]}},
    )
    assert response.status_code == 200
    assert response.json()["values"]["sample.assay"] == pytest.approx(101.0)
    assert response.json()["has_blocking_failure"] is False

    fetched = (await client.get(f"/worksheets/{worksheet_id}")).json()
    assert fetched["worksheet"]["group_values"] == {}

    #  3. Save.
    response = await client.put(
        f"/worksheets/{worksheet_id}/values",
        json={"group_values": {"std": GOOD_STD, "sample": [{"area": 101_000}]}},
    )
    assert response.status_code == 200
    assert response.json()["computed"]["criteria"][0]["passed"] is True

    #  4. Reachable through the test line too.
    response = await client.get(f"/trf/test-lines/{line.id}/worksheet")
    assert response.status_code == 200
    assert response.json()["worksheet"]["id"] == worksheet_id

    #  5. Confirm — publishes to the test line.
    response = await client.post(f"/worksheets/{worksheet_id}/confirm")
    assert response.status_code == 200
    body = response.json()
    assert body["worksheet"]["status"] == "Confirmed"
    assert body["test_line_id"] == line.id
    assert body["test_line_result"] == "101 %"

    #  6. And the TRF itself now shows it.
    response = await client.get(f"/trf/{trf.id}")
    assert response.status_code == 200
    assert response.json()["test_lines"][0]["result"] == "101 %"
    assert response.json()["test_lines"][0]["status"] == "Resulted"


@pytest.mark.asyncio
async def test_confirm_is_refused_while_a_blocking_criterion_fails(client, db_session):
    _test, _trf, line, template = await _seed_scenario(db_session)
    as_user(user(ANALYST, "Analyst"))

    worksheet_id = (
        await client.post(
            f"/trf/test-lines/{line.id}/worksheet", json={"template_id": template.id}
        )
    ).json()["worksheet"]["id"]

    response = await client.put(
        f"/worksheets/{worksheet_id}/values",
        json={"group_values": {"std": BAD_STD, "sample": [{"area": 101_000}]}},
    )
    assert response.status_code == 200
    assert response.json()["computed"]["has_blocking_failure"] is True

    response = await client.post(f"/worksheets/{worksheet_id}/confirm")
    assert response.status_code == 400
    assert "blocking acceptance criterion" in response.json()["detail"]

    #  Nothing reached the test line.
    line_body = (await client.get(f"/trf/test-lines/{line.id}/worksheet")).json()
    assert line_body["worksheet"]["reportable_result"] is None


@pytest.mark.asyncio
async def test_worksheet_writes_are_role_and_status_gated(client, db_session):
    _test, trf, line, template = await _seed_scenario(db_session)
    as_user(user(ANALYST, "Analyst"))
    worksheet_id = (
        await client.post(
            f"/trf/test-lines/{line.id}/worksheet", json={"template_id": template.id}
        )
    ).json()["worksheet"]["id"]

    payload = {"group_values": {"std": GOOD_STD, "sample": [{"area": 101_000}]}}

    #  Supervisor is outside the writer set entirely — refused by require_role.
    as_user(user("sup", "Supervisor", user_id=4))
    assert (
        await client.put(f"/worksheets/{worksheet_id}/values", json=payload)
    ).status_code == 403

    #  QA is a writer, but only in Correction mode — the TRF is still InProgress.
    as_user(user("qa1", "QA", user_id=3))
    assert (
        await client.put(f"/worksheets/{worksheet_id}/values", json=payload)
    ).status_code == 403

    #  Once the TRF reaches PendingADGLRelease the roles swap over.
    as_user(user(ANALYST, "Analyst"))
    assert (
        await client.put(f"/worksheets/{worksheet_id}/values", json=payload)
    ).status_code == 200
    await set_trf_status(db_session, trf, "PendingADGLRelease")

    assert (
        await client.put(f"/worksheets/{worksheet_id}/values", json=payload)
    ).status_code == 403

    as_user(user("qa1", "QA", user_id=3))
    #  A correction without a reason is refused.
    assert (
        await client.put(f"/worksheets/{worksheet_id}/values", json=payload)
    ).status_code == 400
    response = await client.put(
        f"/worksheets/{worksheet_id}/values",
        json={**payload, "reason": "Corrected against the chromatogram"},
    )
    assert response.status_code == 200

    #  Confirmation is never QA's to make — refused by require_role at the route,
    #  so it never reaches the service's status check.
    assert (await client.post(f"/worksheets/{worksheet_id}/confirm")).status_code == 403

    #  For the Analyst it does reach the service, which refuses because at this
    #  status only QA may touch the worksheet.
    as_user(user(ANALYST, "Analyst"))
    response = await client.post(f"/worksheets/{worksheet_id}/confirm")
    assert response.status_code == 403
    assert "may correct worksheet values" in response.json()["detail"]


@pytest.mark.asyncio
async def test_preview_is_readable_by_a_reviewer(client, db_session):
    """
    A Supervisor cannot write values but must be able to see the computed sheet
    they are reviewing, so preview is not gated on the writer roles.
    """
    _test, _trf, line, template = await _seed_scenario(db_session)
    as_user(user(ANALYST, "Analyst"))
    worksheet_id = (
        await client.post(
            f"/trf/test-lines/{line.id}/worksheet", json={"template_id": template.id}
        )
    ).json()["worksheet"]["id"]

    as_user(user("sup", "Supervisor", user_id=4))
    response = await client.post(
        f"/worksheets/{worksheet_id}/preview",
        json={"group_values": {"std": GOOD_STD, "sample": [{"area": 101_000}]}},
    )
    assert response.status_code == 200
    assert response.json()["values"]["sample.assay"] == pytest.approx(101.0)


@pytest.mark.asyncio
async def test_a_test_line_without_a_worksheet_is_a_404(client, db_session):
    _test, _trf, line, _template = await _seed_scenario(db_session)
    as_user(user(ANALYST, "Analyst"))

    response = await client.get(f"/trf/test-lines/{line.id}/worksheet")
    assert response.status_code == 404
    assert "no worksheet" in response.json()["detail"]


@pytest.mark.asyncio
async def test_worksheets_can_be_listed_for_a_trf(client, db_session):
    _test, trf, line, template = await _seed_scenario(db_session)
    as_user(user(ANALYST, "Analyst"))
    await client.post(f"/trf/test-lines/{line.id}/worksheet", json={"template_id": template.id})

    response = await client.get(f"/trf/{trf.id}/worksheets")
    assert response.status_code == 200
    assert [w["trf_test_line_id"] for w in response.json()] == [line.id]
