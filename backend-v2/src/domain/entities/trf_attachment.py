"""
TRF attachment domain entity.

An attachment is a file pinned to a TRF — in practice the chromatogram PDFs and
raw-data exports that support the results, which today are transcribed by hand
into worksheet area fields and will later arrive automatically from the Waters
CDS integration.

Two rules live here:

* **The client's filename is never a path.** `original_filename` is kept for
  display and as the download name; the bytes live under `storage_name`, which
  the application generates.
* **A Released TRF's attachments are immutable** (Requirement 7.5). Release is
  the point at which the record becomes the reportable one, so its supporting
  files must stop moving — and that outranks role, since it is a
  records-integrity rule rather than a permission.
"""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base_entity import BaseEntity

#  TRF statuses at which attachments may no longer be added or removed.

_FROZEN_TRF_STATUSES = frozenset({"Released"})


@dataclass
class TRFAttachment(BaseEntity):
    """
    One uploaded file belonging to a TRF, optionally scoped to a single test line.

    `trf_test_line_id` is nullable on purpose: a chromatogram supports one test
    while a signed batch record supports the whole request, and forcing every file
    onto a line would misfile the latter.
    """

    trf_id: int = field(default=0)
    trf_test_line_id: int | None = field(default=None)

    #  As supplied by the client, sanitised for display. Never used to build a path.
    original_filename: str = field(default="")
    #  Application-generated, unique, and the only name used on disk.
    storage_name: str = field(default="")
    content_type: str = field(default="")
    size_bytes: int = field(default=0)
    #  SHA-256 of the stored bytes, so a file can be shown to be the one uploaded.
    checksum_sha256: str = field(default="")

    description: str | None = field(default=None)

    uploaded_by: str = field(default="")
    uploaded_at: datetime | None = field(default=None)

    # ── Denormalized for API projection ──
    test_line_no: int | None = field(default=None)

    # ── Guards ──

    @staticmethod
    def can_mutate(trf_status: str) -> bool:
        """
        Whether a TRF at this status accepts attachment uploads or deletions.

        Deliberately permissive across the workflow — an analyst gathering raw
        data before submission, and a reviewer adding a note at a gate, are both
        legitimate. Only release closes it.
        """
        return trf_status not in _FROZEN_TRF_STATUSES

    def can_delete_by(self, actor_username: str, actor_is_admin: bool) -> bool:
        """
        Who may remove this file, assuming the TRF still permits mutation.

        The uploader may remove their own and an Admin may remove any. A reviewer
        should not be able to quietly drop someone else's supporting data.
        """
        return actor_is_admin or self.uploaded_by == actor_username

    # ── Display ──

    @property
    def size_display(self) -> str:
        """
        Human-readable size for the UI, so every client renders it identically.

        KB is the smallest unit shown: these are chromatograms and raw-data
        exports, and "0.4 KB" reads better in a file list than "409 bytes"
        alongside neighbours measured in megabytes.
        """
        size = float(self.size_bytes)
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"
