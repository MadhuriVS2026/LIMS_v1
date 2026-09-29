"""
TRF Attachment Application Service.

Handles the chromatogram PDFs and raw-data files that support TRF results.

The validation is the point of the module, so it is worth being explicit about
what each check stops (Property 15 — attachment validation cannot be bypassed):

* **Declared content type against an allow-list.** Checked before a single byte is
  read, so an unwanted type costs nothing.
* **The file's own leading bytes against that declared type.** This is the check
  that matters. A client controls both the filename and the declared type, so
  neither is evidence about the content — only the content is. An executable
  renamed to `.pdf` and posted as `application/pdf` is caught here.
* **Size cap, enforced while streaming.** Counted on the bytes actually received,
  not on `Content-Length`, which the client also controls. Tripping mid-stream is
  the normal case for a large file, which is why the write is staged.
* **A generated storage name.** Traversal is not merely filtered but unreachable:
  the client's filename never contributes to the path.

Bytes stream through a hidden `.part` file and are renamed into place only once
every check has passed, so a rejected upload leaves nothing behind on disk.

Deletion is refused once the TRF is `Released` (Requirement 7.5) — records
integrity, not permission, so it outranks Admin.

Every upload and delete writes exactly one `AuditLog` entry; a rejected upload
writes none.
"""
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

from src.application.exceptions.application_exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.trf_attachment import TRFAttachment
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.trf_attachment_repository import ITRFAttachmentRepository
from src.domain.repositories.trf_repository import ITRFRepository
from src.infrastructure.storage.file_storage import (
    CHUNK_SIZE,
    LocalFileStorage,
    StorageError,
)

#  Leading-byte signatures per accepted content type. A tuple means "any of these".
#  `text/csv` has none — plain text legitimately starts with anything — so it is
#  validated by a decode check plus the binary backstop below.
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
}

#  Prefixes never accepted whatever the declared type claims. A backstop, not the
#  primary defence: the positive signature match above already covers the typed
#  formats, so this only bites for signature-less types such as `text/csv`.
_BINARY_PREFIXES: tuple[bytes, ...] = (
    b"MZ",  # Windows PE / DOS executable
    b"\x7fELF",  # Linux ELF
    b"\xca\xfe\xba\xbe",  # Java class / Mach-O fat binary
    b"\xfe\xed\xfa",  # Mach-O
    b"PK\x03\x04",  # zip container
    b"#!",  # script shebang
)

#  Roles that may attach files. Supervisor and QA review raw data but do not
#  produce it, so they can read and download without being able to upload.
_UPLOAD_ROLES = ("Admin", "Analyst")


class AttachmentService:
    def __init__(
        self,
        attachment_repo: ITRFAttachmentRepository,
        trf_repo: ITRFRepository,
        audit_repo: IAuditLogRepository,
        storage_path: str,
        max_bytes: int,
        allowed_content_types: list[str],
    ) -> None:
        self._repo = attachment_repo
        self._trf_repo = trf_repo
        self._audit_repo = audit_repo
        self._storage = LocalFileStorage(storage_path)
        self._max_bytes = max_bytes
        self._allowed = [t.lower() for t in allowed_content_types]

    # ── Read ─────────────────────────────────────────────────────────

    async def get(self, attachment_id: int) -> TRFAttachment:
        attachment = await self._repo.get_by_id(attachment_id)
        if attachment is None:
            raise NotFoundException("Attachment not found")
        return attachment

    async def list_for_trf(self, trf_id: int) -> list[TRFAttachment]:
        """Requirement 7.4: every attachment on a TRF, newest first."""
        await self._get_trf(trf_id)
        return await self._repo.list_by_trf(trf_id)

    async def list_for_test_line(self, line_id: int) -> list[TRFAttachment]:
        """Attachments scoped to one test line — the chromatograms behind its result."""
        return await self._repo.list_by_test_line(line_id)

    async def open_path(self, attachment_id: int) -> tuple[TRFAttachment, Path]:
        """
        Requirement 7.4: the attachment plus the path its bytes live at.

        A path rather than the bytes, so the caller can hand it to a streaming
        response and a 25MB PDF never sits in memory. Downloads still go through
        the API rather than a static directory, so each one passes the same
        authorisation as the rest of the TRF.
        """
        attachment = await self.get(attachment_id)
        if not self._storage.exists(attachment.storage_name):
            #  Metadata without bytes means storage was cleared underneath us.
            #  Better a clear error than a zero-byte file an analyst might trust
            #  as the raw data.
            raise NotFoundException(
                f"{attachment.original_filename!r} is missing from attachment storage"
            )
        return attachment, self._storage.path(attachment.storage_name)

    # ── Upload ───────────────────────────────────────────────────────

    async def upload(
        self,
        trf_id: int,
        actor: User,
        filename: str,
        content_type: str | None,
        stream: BinaryIO,
        test_line_id: int | None = None,
        description: str | None = None,
    ) -> TRFAttachment:
        """
        Requirement 7.1, 7.2, 7.3, 7.6: validate while streaming, then commit.

        Cheap checks run first so a bad request never touches the filesystem. The
        two that need the content — signature and size — run against the bytes as
        they arrive, and the staged write is discarded if either fails.
        """
        if not actor.has_role(*_UPLOAD_ROLES):
            raise ForbiddenException(
                f"Only {' or '.join(_UPLOAD_ROLES)} may attach files to a TRF"
            )

        trf = await self._get_trf(trf_id)
        if not TRFAttachment.can_mutate(trf.status):
            raise ValidationException(
                f"Attachments cannot be added once the TRF is {trf.status}"
            )

        if test_line_id is not None:
            line = await self._trf_repo.get_test_line_by_id(test_line_id)
            if line is None or line.trf_id != trf_id:
                raise NotFoundException("Test line not found on this TRF")

        display_name = self._sanitise_filename(filename)
        resolved_type = self._validate_content_type(content_type)

        storage_name = self._storage.build_storage_name(display_name)
        size, checksum = await self._stream_to_storage(
            stream, storage_name, resolved_type, display_name
        )

        attachment = TRFAttachment(
            trf_id=trf_id,
            trf_test_line_id=test_line_id,
            original_filename=display_name,
            storage_name=storage_name,
            content_type=resolved_type,
            size_bytes=size,
            checksum_sha256=checksum,
            description=description,
            uploaded_by=actor.username,
            uploaded_at=datetime.now(timezone.utc),
            created_by=actor.username,
            modified_by=actor.username,
        )

        try:
            saved = await self._repo.create(attachment)
        except Exception:
            #  Never leave bytes with no row pointing at them — an orphan is
            #  invisible to the application and impossible to clean up through it.
            self._storage.delete(storage_name)
            raise

        await self._audit(
            actor,
            "TRF_ATTACHMENT_UPLOADED",
            saved.id,
            new_values={
                "trf_id": trf_id,
                "trf_test_line_id": test_line_id,
                "original_filename": saved.original_filename,
                "storage_name": saved.storage_name,
                "content_type": saved.content_type,
                "size_bytes": saved.size_bytes,
                "checksum_sha256": saved.checksum_sha256,
            },
        )
        return saved

    async def _stream_to_storage(
        self, stream: BinaryIO, storage_name: str, content_type: str, display_name: str
    ) -> tuple[int, str]:
        """
        Copy the upload into storage, validating as it goes.

        The signature is checked on the first chunk — before the bulk of a large
        file has been read, so a renamed executable is rejected almost
        immediately. The size cap is checked per chunk, so it trips as soon as it
        is exceeded rather than after buffering the whole body.

        Any failure leaves nothing behind: the staged write is unlinked on the way
        out of the context manager.
        """
        digest = hashlib.sha256()
        size = 0
        first_chunk = True

        try:
            with self._storage.open_writer(storage_name) as writer:
                while True:
                    chunk = stream.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    if first_chunk:
                        self._validate_signature(chunk, content_type, display_name)
                        first_chunk = False

                    size += len(chunk)
                    if size > self._max_bytes:
                        raise ValidationException(
                            f"{display_name!r} exceeds the maximum upload size of "
                            f"{self._max_bytes / (1024 * 1024):.0f}MB"
                        )

                    digest.update(chunk)
                    writer.write(chunk)

                if size == 0:
                    raise ValidationException(f"{display_name!r} is empty")

                writer.commit()
        except StorageError as exc:
            raise ValidationException(f"Could not store the attachment: {exc}") from exc

        return size, digest.hexdigest()

    # ── Delete ───────────────────────────────────────────────────────

    async def delete(
        self, attachment_id: int, actor: User, reason: str | None = None
    ) -> None:
        """
        Requirement 7.5: refused once the TRF is Released.

        Note the ordering — the release check comes before the ownership check, so
        an Admin gets the records-integrity message rather than being told they
        lack permission. Release is not something a role overrides.
        """
        attachment = await self.get(attachment_id)
        trf = await self._get_trf(attachment.trf_id)

        if not TRFAttachment.can_mutate(trf.status):
            raise ValidationException(
                f"{attachment.original_filename!r} is part of the released record for "
                f"{trf.trf_number} and cannot be removed"
            )
        if not attachment.can_delete_by(actor.username, actor.has_role("Admin")):
            raise ForbiddenException(
                "Only the user who uploaded a file, or an Admin, may remove it"
            )

        #  Metadata first: an orphaned file is invisible and harmless, whereas a
        #  row pointing at bytes that no longer exist is a broken download.
        await self._repo.delete(attachment_id)
        self._storage.delete(attachment.storage_name)

        await self._audit(
            actor,
            "TRF_ATTACHMENT_DELETED",
            attachment_id,
            #  The row is gone, so the trail has to carry enough to identify what
            #  went — including the storage name, for reconciling the directory.
            old_values={
                "trf_id": attachment.trf_id,
                "original_filename": attachment.original_filename,
                "storage_name": attachment.storage_name,
                "checksum_sha256": attachment.checksum_sha256,
                "uploaded_by": attachment.uploaded_by,
            },
            new_values={"reason": reason},
        )

    # ── Validation ───────────────────────────────────────────────────

    @staticmethod
    def _sanitise_filename(filename: str) -> str:
        """
        Reduce a client filename to a display name.

        Directory components are stripped rather than rejected: browsers on some
        platforms send a full path, and failing an upload for that would be wrong.
        Leading dots go too, so a name can never render as a hidden file. This is
        defence in depth — the value is never used to build a path either way.
        """
        name = (filename or "").replace("\\", "/").split("/")[-1]
        name = name.replace("\0", "").strip().lstrip(".").strip()
        if not name:
            raise ValidationException("A filename is required")
        return name[:255]

    def _validate_content_type(self, content_type: str | None) -> str:
        """Requirement 7.2, 7.6: the declared type must be on the allow-list."""
        #  Drop any `; charset=` parameter — browsers send one for text types.
        declared = (content_type or "").split(";")[0].strip().lower()
        if not declared:
            raise ValidationException("A content type is required")
        if declared not in self._allowed:
            raise ValidationException(
                f"Files of type {declared!r} are not accepted "
                f"(allowed: {', '.join(self._allowed)})"
            )
        return declared

    def _validate_signature(self, head: bytes, content_type: str, display_name: str) -> None:
        """
        Requirement 7.2: the bytes must match the declared type.

        Runs on the first chunk only. That is sufficient — every format here is
        identified by a fixed prefix — and it means a large hostile upload is cut
        off early rather than read in full.
        """
        expected = _SIGNATURES.get(content_type)
        if expected is not None:
            if not any(head.startswith(sig) for sig in expected):
                raise ValidationException(
                    f"The contents of {display_name!r} do not match the declared type "
                    f"{content_type!r}"
                )
            return

        #  Signature-less types (text/csv): reject known binary prefixes outright,
        #  then require the head to actually decode as text.
        if any(head.startswith(prefix) for prefix in _BINARY_PREFIXES):
            raise ValidationException(
                f"The contents of {display_name!r} are binary and do not match the "
                f"declared type {content_type!r}"
            )
        try:
            #  Decode a prefix that cannot split a multi-byte character mid-way at
            #  the chunk boundary in a way that matters for this check.
            head[: min(len(head), 4096)].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise ValidationException(
                f"The contents of {display_name!r} are not valid UTF-8 text and do not "
                f"match the declared type {content_type!r}"
            ) from None

    # ── Helpers ──────────────────────────────────────────────────────

    async def _get_trf(self, trf_id: int):
        trf = await self._trf_repo.get_by_id(trf_id)
        if trf is None:
            raise NotFoundException("Test Request Form not found")
        return trf

    @staticmethod
    def checksum(data: bytes) -> str:
        """Exposed so a caller can verify received bytes against the stored digest."""
        return hashlib.sha256(data).hexdigest()

    async def _audit(
        self,
        actor: User,
        action: str,
        record_id: int | None,
        old_values: dict | None = None,
        new_values: dict | None = None,
    ) -> None:
        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action=action,
                table_name="trf_attachments",
                record_id=record_id,
                old_values=old_values,
                new_values=new_values,
            )
        )
