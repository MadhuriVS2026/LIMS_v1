"""SQLAlchemy ORM model for Certificates of Analysis."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class CertificateOfAnalysisModel(BaseModel):
    """
    An issued certificate for one product/batch.

    `snapshot` is the certificate itself — header, per-test rows, and the release
    signature chain — captured at generation and never rewritten. The scalar
    columns beside it are query keys only, so a COA can be found without opening
    the JSON.

    `(product_id, batch_number)` is deliberately **not** unique: a batch can be
    re-certified after additional testing, and the later certificate supersedes
    the earlier one rather than replacing it.
    """

    __tablename__ = "certificates_of_analysis"
    __table_args__ = (UniqueConstraint("coa_number", name="uq_coa_number"),)

    coa_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Released")

    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    released_by: Mapped[str] = mapped_column(String(255), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    product = relationship("ProductModel")
