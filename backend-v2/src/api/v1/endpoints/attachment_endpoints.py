"""
TRF attachment API endpoints.

Downloads are served **through** the API rather than from a static directory, so
every download passes the same authentication as the rest of the TRF. The storage
directory must not be web-exposed.

Upload is gated to Admin/Analyst at the route as well as in the service: a
Supervisor or QA reviews raw data but does not produce it, so they can list and
download but not attach.
"""
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_role
from src.api.v1.schemas.attachment_schemas import (
    AttachmentLimitsResponse,
    AttachmentResponse,
)
from src.config.dependency_injection import Container
from src.config.settings import settings
from src.domain.entities.user import User

router = APIRouter(tags=["TRF Attachments"])

_ANY_ROLE = ("Admin", "Analyst", "Supervisor", "QA")
_UPLOAD_ROLES = ("Admin", "Analyst")


@router.get("/attachments/limits", response_model=AttachmentLimitsResponse)
async def attachment_limits(
    current_user: User = Depends(require_role(*_ANY_ROLE)),
):
    """The upload constraints, so the UI can reject a bad file before sending it."""
    return AttachmentLimitsResponse(
        max_bytes=settings.ATTACHMENT_MAX_BYTES,
        allowed_content_types=settings.ATTACHMENT_ALLOWED_CONTENT_TYPES,
    )


@router.post("/trf/{trf_id}/attachments", response_model=AttachmentResponse)
async def upload_attachment(
    trf_id: int,
    file: UploadFile = File(...),
    test_line_id: int | None = Form(default=None),
    description: str | None = Form(default=None),
    current_user: User = Depends(require_role(*_UPLOAD_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    """
    Requirement 7.1, 7.2, 7.3: upload a supporting file.

    `file.file` is handed to the service as a stream rather than read here, so the
    size cap is enforced against the bytes as they arrive instead of after the
    whole body has been buffered.
    """
    service = Container.get_attachment_service(session)
    return await service.upload(
        trf_id=trf_id,
        actor=current_user,
        filename=file.filename or "",
        content_type=file.content_type,
        stream=file.file,
        test_line_id=test_line_id,
        description=description,
    )


@router.get("/trf/{trf_id}/attachments", response_model=list[AttachmentResponse])
async def list_attachments(
    trf_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 7.4: every attachment on a TRF, newest first."""
    service = Container.get_attachment_service(session)
    return await service.list_for_trf(trf_id)


@router.get(
    "/trf/test-lines/{line_id}/attachments", response_model=list[AttachmentResponse]
)
async def list_test_line_attachments(
    line_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """Attachments scoped to one test line — the chromatograms behind its result."""
    service = Container.get_attachment_service(session)
    return await service.list_for_test_line(line_id)


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
):
    """
    Requirement 7.4: stream the stored bytes back under the original filename.

    The filename is stripped of quotes and newlines before going into
    `Content-Disposition` — it is client-supplied, so it would otherwise allow
    header injection.
    """
    service = Container.get_attachment_service(session)
    attachment, path = await service.open_path(attachment_id)

    safe_name = (
        attachment.original_filename.replace('"', "").replace("\r", "").replace("\n", "")
    )
    return FileResponse(
        path=path,
        media_type=attachment.content_type,
        filename=safe_name,
        #  Lets a caller confirm the bytes match what was stored.
        headers={"X-Checksum-SHA256": attachment.checksum_sha256},
    )


@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    reason: str | None = Query(default=None),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Requirement 7.5: refused once the TRF is Released.

    Not gated to `_UPLOAD_ROLES` at the route, because the meaningful rule is
    ownership — the uploader or an Admin — which only the service can evaluate.
    """
    service = Container.get_attachment_service(session)
    await service.delete(attachment_id, current_user, reason=reason)
    return {"success": True, "message": "Attachment removed"}
