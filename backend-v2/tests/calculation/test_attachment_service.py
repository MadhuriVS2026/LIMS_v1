"""
AttachmentService tests.

Covers **Property 15** (attachment validation cannot be bypassed) and the
released-record half of **Property 16**.

The interesting cases are the bypass attempts, because that is what the
validation exists for: a disallowed type, an executable renamed to `.pdf`, an
oversized file, a filename carrying a traversal sequence, and a delete against a
released TRF. Each asserts not only the rejection but that **nothing was left on
disk** — a rejected upload that still wrote bytes would be the actual bug.
"""
import io

import pytest

from src.application.exceptions.application_exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.application.services.attachment_service import AttachmentService
from src.infrastructure.database.repositories.audit_repository_impl import (
    AuditLogRepositoryImpl,
)
from src.infrastructure.database.repositories.trf_attachment_repository_impl import (
    TRFAttachmentRepositoryImpl,
)
from src.infrastructure.database.repositories.trf_repository_impl import TRFRepositoryImpl
from tests.calculation.conftest import seed_trf_with_line, set_trf_status, user

PDF = b"%PDF-1.7\n" + b"x" * 400
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 400
ALLOWED = ["application/pdf", "image/png", "image/jpeg", "text/csv"]


@pytest.fixture
def storage(tmp_path):
    """A real temp directory — these tests exercise actual filesystem writes."""
    return tmp_path / "attachments"


def _service(session, storage, max_bytes: int = 1024 * 1024) -> AttachmentService:
    return AttachmentService(
        TRFAttachmentRepositoryImpl(session),
        TRFRepositoryImpl(session),
        AuditLogRepositoryImpl(session),
        storage_path=str(storage),
        max_bytes=max_bytes,
        allowed_content_types=ALLOWED,
    )


def stored_files(storage) -> list[str]:
    if not storage.exists():
        return []
    return sorted(p.name for p in storage.iterdir() if p.is_file())


# ── Happy path ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_stores_bytes_and_metadata(db_session, storage):
    trf, line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)

    saved = await svc.upload(
        trf_id=trf.id,
        actor=user("analyst", "Analyst"),
        filename="chromatogram.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(PDF),
        test_line_id=line.id,
        description="Assay injection 1",
    )

    assert saved.original_filename == "chromatogram.pdf"
    assert saved.content_type == "application/pdf"
    assert saved.size_bytes == len(PDF)
    assert saved.trf_test_line_id == line.id
    assert saved.uploaded_by == "analyst"
    assert saved.uploaded_at is not None

    #  The storage name is generated, not the client's filename.
    assert saved.storage_name != "chromatogram.pdf"
    assert saved.storage_name.endswith(".pdf")
    assert stored_files(storage) == [saved.storage_name]
    assert (storage / saved.storage_name).read_bytes() == PDF


@pytest.mark.asyncio
async def test_download_path_resolves_to_the_stored_file(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)
    saved = await svc.upload(
        trf_id=trf.id,
        actor=user("analyst", "Analyst"),
        filename="raw.png",
        content_type="image/png",
        stream=io.BytesIO(PNG),
    )

    attachment, path = await svc.open_path(saved.id)
    assert attachment.original_filename == "raw.png"
    assert path.read_bytes() == PNG


@pytest.mark.asyncio
async def test_missing_stored_file_is_reported_not_served_empty(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)
    saved = await svc.upload(
        trf_id=trf.id,
        actor=user("analyst", "Analyst"),
        filename="raw.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(PDF),
    )
    (storage / saved.storage_name).unlink()

    with pytest.raises(NotFoundException) as exc:
        await svc.open_path(saved.id)
    assert "missing from attachment storage" in str(exc.value)


@pytest.mark.asyncio
async def test_attachments_list_per_trf_and_per_line(db_session, storage):
    trf, line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)
    analyst = user("analyst", "Analyst")

    trf_level = await svc.upload(
        trf_id=trf.id, actor=analyst, filename="batch_record.pdf",
        content_type="application/pdf", stream=io.BytesIO(PDF),
    )
    line_level = await svc.upload(
        trf_id=trf.id, actor=analyst, filename="chromatogram.pdf",
        content_type="application/pdf", stream=io.BytesIO(PDF), test_line_id=line.id,
    )

    assert {a.id for a in await svc.list_for_trf(trf.id)} == {trf_level.id, line_level.id}
    assert [a.id for a in await svc.list_for_test_line(line.id)] == [line_level.id]


# ── Property 15: validation cannot be bypassed ───────────────────────


@pytest.mark.asyncio
async def test_disallowed_content_type_is_rejected_and_nothing_is_written(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)

    with pytest.raises(ValidationException) as exc:
        await svc.upload(
            trf_id=trf.id,
            actor=user("analyst", "Analyst"),
            filename="payload.exe",
            content_type="application/x-msdownload",
            stream=io.BytesIO(b"MZ" + b"x" * 100),
        )
    assert "not accepted" in str(exc.value)
    assert stored_files(storage) == []
    assert await svc.list_for_trf(trf.id) == []


@pytest.mark.asyncio
async def test_a_renamed_executable_is_rejected_by_signature(db_session, storage):
    """
    The declared type is client-controlled, so the allow-list alone is not enough.
    This is the case that check exists for.
    """
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)

    with pytest.raises(ValidationException) as exc:
        await svc.upload(
            trf_id=trf.id,
            actor=user("analyst", "Analyst"),
            filename="chromatogram.pdf",
            content_type="application/pdf",
            stream=io.BytesIO(b"MZ\x90\x00" + b"x" * 400),
        )
    assert "do not match the declared type" in str(exc.value)
    assert stored_files(storage) == []


@pytest.mark.asyncio
async def test_content_type_and_signature_must_agree_with_each_other(db_session, storage):
    """A real PNG declared as a PDF is still a mismatch — both are allow-listed."""
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)

    with pytest.raises(ValidationException):
        await svc.upload(
            trf_id=trf.id,
            actor=user("analyst", "Analyst"),
            filename="mislabelled.pdf",
            content_type="application/pdf",
            stream=io.BytesIO(PNG),
        )
    assert stored_files(storage) == []


@pytest.mark.asyncio
async def test_oversized_file_is_rejected_and_the_partial_write_is_removed(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    #  Cap below one chunk so the check trips on the first read, and again above
    #  it so the multi-chunk path is covered too.
    svc = _service(db_session, storage, max_bytes=1000)

    with pytest.raises(ValidationException) as exc:
        await svc.upload(
            trf_id=trf.id,
            actor=user("analyst", "Analyst"),
            filename="huge.pdf",
            content_type="application/pdf",
            stream=io.BytesIO(b"%PDF-1.7\n" + b"x" * 5000),
        )
    assert "maximum upload size" in str(exc.value)
    #  The partial file must not survive the rejection.
    assert stored_files(storage) == []


@pytest.mark.asyncio
async def test_size_cap_trips_across_chunk_boundaries(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage, max_bytes=200 * 1024)

    with pytest.raises(ValidationException):
        await svc.upload(
            trf_id=trf.id,
            actor=user("analyst", "Analyst"),
            filename="big.pdf",
            content_type="application/pdf",
            #  Several 64 KB chunks, exceeding the cap only partway through.
            stream=io.BytesIO(b"%PDF-1.7\n" + b"x" * (300 * 1024)),
        )
    assert stored_files(storage) == []


@pytest.mark.asyncio
async def test_empty_and_too_short_files_are_rejected(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)
    analyst = user("analyst", "Analyst")

    with pytest.raises(ValidationException) as exc:
        await svc.upload(
            trf_id=trf.id, actor=analyst, filename="empty.pdf",
            content_type="application/pdf", stream=io.BytesIO(b""),
        )
    assert "empty" in str(exc.value)

    with pytest.raises(ValidationException):
        #  Shorter than the PDF magic, so the signature can never be confirmed.
        await svc.upload(
            trf_id=trf.id, actor=analyst, filename="tiny.pdf",
            content_type="application/pdf", stream=io.BytesIO(b"%PD"),
        )
    assert stored_files(storage) == []


@pytest.mark.parametrize(
    "filename",
    [
        "../../../../etc/passwd",
        "..\\..\\windows\\system32\\config\\sam",
        "/absolute/path/evil.pdf",
        "C:\\Users\\victim\\evil.pdf",
        "....//....//evil.pdf",
        "nul.pdf",
    ],
)
@pytest.mark.asyncio
async def test_a_client_filename_can_never_become_a_path(db_session, storage, filename):
    """
    Traversal is not reachable rather than merely filtered: the storage name is
    generated, so whatever the client sends only ever becomes display metadata.
    """
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)

    saved = await svc.upload(
        trf_id=trf.id,
        actor=user("analyst", "Analyst"),
        filename=filename,
        content_type="application/pdf",
        stream=io.BytesIO(PDF),
    )

    #  Exactly one file, directly in the storage root, under the generated name.
    assert stored_files(storage) == [saved.storage_name]
    assert "/" not in saved.storage_name and "\\" not in saved.storage_name
    assert ".." not in saved.storage_name
    #  And the metadata is sanitised for display.
    assert "/" not in saved.original_filename and "\\" not in saved.original_filename
    assert not saved.original_filename.startswith(".")


@pytest.mark.asyncio
async def test_two_uploads_of_the_same_filename_do_not_collide(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)
    analyst = user("analyst", "Analyst")

    first = await svc.upload(
        trf_id=trf.id, actor=analyst, filename="chromatogram.pdf",
        content_type="application/pdf", stream=io.BytesIO(PDF),
    )
    second = await svc.upload(
        trf_id=trf.id, actor=analyst, filename="chromatogram.pdf",
        content_type="application/pdf", stream=io.BytesIO(PDF + b"different"),
    )

    assert first.storage_name != second.storage_name
    assert len(stored_files(storage)) == 2
    assert (storage / second.storage_name).read_bytes().endswith(b"different")


@pytest.mark.asyncio
async def test_content_type_parameters_are_tolerated(db_session, storage):
    """Browsers send `text/csv; charset=utf-8`; the parameter must not break the match."""
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)

    saved = await svc.upload(
        trf_id=trf.id,
        actor=user("analyst", "Analyst"),
        filename="areas.csv",
        content_type="text/csv; charset=utf-8",
        stream=io.BytesIO(b"name,area\nstd,253287\n"),
    )
    assert saved.content_type == "text/csv"


# ── Authorisation & TRF status ───────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_is_refused_for_a_reviewer_only_role(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)

    with pytest.raises(ForbiddenException):
        await svc.upload(
            trf_id=trf.id,
            actor=user("sup", "Supervisor", user_id=4),
            filename="x.pdf",
            content_type="application/pdf",
            stream=io.BytesIO(PDF),
        )
    assert stored_files(storage) == []


@pytest.mark.asyncio
async def test_unknown_trf_or_mismatched_line_is_a_404(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)
    analyst = user("analyst", "Analyst")

    with pytest.raises(NotFoundException):
        await svc.upload(
            trf_id=9999, actor=analyst, filename="x.pdf",
            content_type="application/pdf", stream=io.BytesIO(PDF),
        )
    with pytest.raises(NotFoundException) as exc:
        await svc.upload(
            trf_id=trf.id, actor=analyst, filename="x.pdf",
            content_type="application/pdf", stream=io.BytesIO(PDF), test_line_id=9999,
        )
    assert "Test line not found" in str(exc.value)
    assert stored_files(storage) == []


# ── Property 16: released records are immutable ──────────────────────


@pytest.mark.asyncio
async def test_upload_is_refused_once_the_trf_is_released(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    await set_trf_status(db_session, trf, "Released")
    svc = _service(db_session, storage)

    with pytest.raises(ValidationException) as exc:
        await svc.upload(
            trf_id=trf.id,
            actor=user("analyst", "Analyst"),
            filename="late.pdf",
            content_type="application/pdf",
            stream=io.BytesIO(PDF),
        )
    assert "Released" in str(exc.value)
    assert stored_files(storage) == []


@pytest.mark.asyncio
async def test_delete_is_refused_once_the_trf_is_released(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)
    saved = await svc.upload(
        trf_id=trf.id, actor=user("analyst", "Analyst"), filename="raw.pdf",
        content_type="application/pdf", stream=io.BytesIO(PDF),
    )
    await set_trf_status(db_session, trf, "Released")

    with pytest.raises(ValidationException) as exc:
        await svc.delete(saved.id, user("analyst", "Analyst"))
    assert "part of the released record" in str(exc.value)

    #  Both the metadata and the bytes survive.
    assert [a.id for a in await svc.list_for_trf(trf.id)] == [saved.id]
    assert stored_files(storage) == [saved.storage_name]


@pytest.mark.asyncio
async def test_delete_removes_metadata_and_bytes(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)
    analyst = user("analyst", "Analyst")
    saved = await svc.upload(
        trf_id=trf.id, actor=analyst, filename="raw.pdf",
        content_type="application/pdf", stream=io.BytesIO(PDF),
    )

    await svc.delete(saved.id, analyst, reason="Wrong injection attached")

    assert await svc.list_for_trf(trf.id) == []
    assert stored_files(storage) == []
    with pytest.raises(NotFoundException):
        await svc.get(saved.id)


@pytest.mark.asyncio
async def test_only_the_uploader_or_an_admin_may_delete(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)
    saved = await svc.upload(
        trf_id=trf.id, actor=user("analyst", "Analyst"), filename="raw.pdf",
        content_type="application/pdf", stream=io.BytesIO(PDF),
    )

    with pytest.raises(ForbiddenException) as exc:
        await svc.delete(saved.id, user("other", "Analyst", user_id=9))
    assert "who uploaded a file" in str(exc.value)
    assert stored_files(storage) == [saved.storage_name]

    await svc.delete(saved.id, user("admin", "Admin", user_id=2))
    assert stored_files(storage) == []


# ── Property 17: one audit entry per mutation ────────────────────────


@pytest.mark.asyncio
async def test_upload_and_delete_each_write_one_audit_entry(db_session, storage):
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)
    analyst = user("analyst", "Analyst")
    saved = await svc.upload(
        trf_id=trf.id, actor=analyst, filename="raw.pdf",
        content_type="application/pdf", stream=io.BytesIO(PDF),
    )
    await svc.delete(saved.id, analyst, reason="Superseded")

    entries = await AuditLogRepositoryImpl(db_session).list_recent(limit=50)
    actions = [e.action for e in entries]
    assert actions.count("TRF_ATTACHMENT_UPLOADED") == 1
    assert actions.count("TRF_ATTACHMENT_DELETED") == 1

    #  The delete entry keeps enough to identify what went, since the row is gone.
    deleted = next(e for e in entries if e.action == "TRF_ATTACHMENT_DELETED")
    assert deleted.old_values["original_filename"] == "raw.pdf"
    assert deleted.old_values["storage_name"] == saved.storage_name
    assert deleted.new_values["reason"] == "Superseded"


@pytest.mark.asyncio
async def test_a_rejected_upload_writes_no_audit_entry(db_session, storage):
    """An attempt that stored nothing must not look like a stored file in the trail."""
    trf, _line = await seed_trf_with_line(db_session)
    svc = _service(db_session, storage)

    with pytest.raises(ValidationException):
        await svc.upload(
            trf_id=trf.id, actor=user("analyst", "Analyst"), filename="x.exe",
            content_type="application/x-msdownload", stream=io.BytesIO(b"MZ"),
        )

    entries = await AuditLogRepositoryImpl(db_session).list_recent(limit=50)
    assert [e.action for e in entries].count("TRF_ATTACHMENT_UPLOADED") == 0
