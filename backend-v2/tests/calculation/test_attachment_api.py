"""
Integration tests for the attachment endpoints.

Drives the real ASGI app, overriding only `get_session`, `get_current_user`, and
the configured storage path (pointed at a temp directory so tests never write
into the repository).

Covers the upload/list/download round trip, the rejection paths through HTTP
status codes, and delete refused on a released TRF.
"""
import io

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.v1.dependencies import get_current_user, get_session
from src.config import dependency_injection
from src.config.settings import settings
from src.domain.entities.user import User
from src.main import app
from tests.calculation.conftest import seed_trf_with_line, set_trf_status, user

PDF = b"%PDF-1.7\n" + b"x" * 400

_CURRENT: dict[str, User] = {}


def as_user(u: User) -> None:
    _CURRENT["user"] = u


@pytest_asyncio.fixture
async def client(db_session, tmp_path, monkeypatch):
    async def _session_override():
        yield db_session

    async def _user_override() -> User:
        return _CURRENT["user"]

    #  Point storage at a temp directory. Patched on the settings object the
    #  container reads at call time, so the service picks it up per request.
    monkeypatch.setattr(
        dependency_injection.settings,
        "ATTACHMENT_STORAGE_PATH",
        str(tmp_path / "attachments"),
        raising=False,
    )

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user] = _user_override
    as_user(user("analyst", "Analyst"))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test/api/v1"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    _CURRENT.clear()


@pytest.mark.asyncio
async def test_limits_are_exposed_to_the_client(client):
    response = await client.get("/attachments/limits")
    assert response.status_code == 200
    body = response.json()
    assert body["max_bytes"] == settings.ATTACHMENT_MAX_BYTES
    assert "application/pdf" in body["allowed_content_types"]


@pytest.mark.asyncio
async def test_upload_list_download_round_trip(client, db_session):
    trf, line = await seed_trf_with_line(db_session)

    response = await client.post(
        f"/trf/{trf.id}/attachments",
        files={"file": ("chromatogram.pdf", io.BytesIO(PDF), "application/pdf")},
        data={"test_line_id": str(line.id), "description": "Injection 1"},
    )
    assert response.status_code == 200
    saved = response.json()
    assert saved["original_filename"] == "chromatogram.pdf"
    assert saved["size_bytes"] == len(PDF)
    assert saved["size_display"].endswith("KB")
    assert saved["trf_test_line_id"] == line.id
    assert saved["uploaded_by"] == "analyst"
    #  The generated storage name is not exposed to clients — they have no use
    #  for it and it is the only thing that maps to a path.
    assert "storage_name" not in saved

    listed = await client.get(f"/trf/{trf.id}/attachments")
    assert listed.status_code == 200
    assert [a["id"] for a in listed.json()] == [saved["id"]]

    download = await client.get(f"/attachments/{saved['id']}/download")
    assert download.status_code == 200
    assert download.content == PDF
    assert "chromatogram.pdf" in download.headers["content-disposition"]


@pytest.mark.asyncio
async def test_a_trf_level_attachment_needs_no_test_line(client, db_session):
    trf, _line = await seed_trf_with_line(db_session)
    response = await client.post(
        f"/trf/{trf.id}/attachments",
        files={"file": ("batch_record.pdf", io.BytesIO(PDF), "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["trf_test_line_id"] is None


@pytest.mark.asyncio
async def test_disallowed_type_is_a_400(client, db_session):
    trf, _line = await seed_trf_with_line(db_session)
    response = await client.post(
        f"/trf/{trf.id}/attachments",
        files={"file": ("payload.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-msdownload")},
    )
    assert response.status_code == 400
    assert "not accepted" in response.json()["detail"]
    assert (await client.get(f"/trf/{trf.id}/attachments")).json() == []


@pytest.mark.asyncio
async def test_a_renamed_file_is_a_400(client, db_session):
    trf, _line = await seed_trf_with_line(db_session)
    response = await client.post(
        f"/trf/{trf.id}/attachments",
        files={"file": ("chromatogram.pdf", io.BytesIO(b"MZ\x90\x00" + b"x" * 400), "application/pdf")},
    )
    assert response.status_code == 400
    assert "do not match the declared type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_is_role_gated(client, db_session):
    trf, _line = await seed_trf_with_line(db_session)
    as_user(user("sup", "Supervisor", user_id=4))

    response = await client.post(
        f"/trf/{trf.id}/attachments",
        files={"file": ("x.pdf", io.BytesIO(PDF), "application/pdf")},
    )
    assert response.status_code == 403

    #  But a Supervisor can still read and download — they review the raw data.
    assert (await client.get(f"/trf/{trf.id}/attachments")).status_code == 200


@pytest.mark.asyncio
async def test_delete_refused_on_a_released_trf(client, db_session):
    trf, _line = await seed_trf_with_line(db_session)
    saved = (
        await client.post(
            f"/trf/{trf.id}/attachments",
            files={"file": ("raw.pdf", io.BytesIO(PDF), "application/pdf")},
        )
    ).json()

    await set_trf_status(db_session, trf, "Released")

    response = await client.delete(f"/attachments/{saved['id']}")
    assert response.status_code == 400
    assert "released record" in response.json()["detail"]

    #  Still listed, still downloadable.
    assert [a["id"] for a in (await client.get(f"/trf/{trf.id}/attachments")).json()] == [
        saved["id"]
    ]
    assert (await client.get(f"/attachments/{saved['id']}/download")).status_code == 200


@pytest.mark.asyncio
async def test_upload_refused_on_a_released_trf(client, db_session):
    trf, _line = await seed_trf_with_line(db_session)
    await set_trf_status(db_session, trf, "Released")

    response = await client.post(
        f"/trf/{trf.id}/attachments",
        files={"file": ("late.pdf", io.BytesIO(PDF), "application/pdf")},
    )
    assert response.status_code == 400
    assert "Released" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_removes_it(client, db_session):
    trf, _line = await seed_trf_with_line(db_session)
    saved = (
        await client.post(
            f"/trf/{trf.id}/attachments",
            files={"file": ("raw.pdf", io.BytesIO(PDF), "application/pdf")},
        )
    ).json()

    response = await client.delete(f"/attachments/{saved['id']}", params={"reason": "Wrong file"})
    assert response.status_code == 200
    assert (await client.get(f"/trf/{trf.id}/attachments")).json() == []
    assert (await client.get(f"/attachments/{saved['id']}/download")).status_code == 404


@pytest.mark.asyncio
async def test_unknown_attachment_is_a_404(client, db_session):
    await seed_trf_with_line(db_session)
    assert (await client.get("/attachments/9999/download")).status_code == 404
    assert (await client.delete("/attachments/9999")).status_code == 404
