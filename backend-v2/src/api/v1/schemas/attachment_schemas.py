"""Pydantic schemas for TRF attachment endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    """
    Deliberately omits `storage_name`. It is the only value that maps to a path,
    clients have no use for it, and exposing it would invite one to try building
    its own download URL.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    trf_id: int
    trf_test_line_id: int | None = None
    test_line_no: int | None = None
    original_filename: str
    content_type: str
    size_bytes: int
    #  Formatted server-side so every client renders sizes identically.
    size_display: str
    #  Returned so a downloader can verify the bytes received are the bytes stored.
    checksum_sha256: str
    description: str | None = None
    uploaded_by: str
    uploaded_at: datetime | None = None


class AttachmentLimitsResponse(BaseModel):
    """
    Lets the UI reject an oversized or wrong-typed file before uploading it.

    Advisory only — the server enforces all of this regardless of what a client
    does with the values.
    """

    max_bytes: int
    allowed_content_types: list[str]
