"""SQLAlchemy ORM model for TRF attachments."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class TRFAttachmentModel(BaseModel):
    """
    A file attached to a TRF, optionally scoped to one of its test lines.

    `storage_name` is unique: it is the application-generated name the bytes are
    written under, so a collision would mean one upload silently overwriting
    another's file. `original_filename` is retained for display only and is never
    used to build a path.
    """

    __tablename__ = "trf_attachments"
    __table_args__ = (
        UniqueConstraint("storage_name", name="uq_trf_attachment_storage_name"),
    )

    trf_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("test_request_forms.id"), nullable=False, index=True
    )
    #  Nullable: a chromatogram belongs to one test, a signed worksheet scan to
    #  the whole request.
    trf_test_line_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("trf_test_lines.id"), nullable=True, index=True
    )

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    trf = relationship("TestRequestFormModel")
    test_line = relationship("TRFTestLineModel")
