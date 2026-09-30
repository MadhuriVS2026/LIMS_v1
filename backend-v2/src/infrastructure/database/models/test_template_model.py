"""SQLAlchemy ORM models for test templates and worksheets."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class TestTemplateModel(BaseModel):
    """
    A versioned analytical calculation template.

    `(code, version)` is unique: every version of a template shares one code and
    is distinguished by its version number, so the pair is the natural key.
    `definition` holds the JSON body parsed by `TemplateDefinition.parse()`.
    """

    __tablename__ = "test_templates"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_test_template_code_version"),
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    archetype: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("tests.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Draft", index=True)
    result_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    definition: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    #  Self-referential: points at the version that replaced this one.
    superseded_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("test_templates.id"), nullable=True
    )

    test = relationship("TestModel")


class TestWorksheetModel(BaseModel):
    """
    A filled-in template instance bound to one TRF test line.

    `trf_test_line_id` is unique — at most one worksheet per test line
    (Requirement 5.2). `template_version` is stored alongside `template_id` so an
    executed worksheet records which version produced its numbers even if the
    template row is later superseded (Requirement 2.7).
    """

    __tablename__ = "test_worksheets"
    __table_args__ = (
        UniqueConstraint("trf_test_line_id", name="uq_test_worksheet_test_line"),
    )

    trf_test_line_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trf_test_lines.id"), nullable=False, index=True
    )
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("test_templates.id"), nullable=False
    )
    template_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="InProgress")

    context_values: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    group_values: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    #  Frozen at confirmation so a reported result stays reproducible.
    computed_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reportable_result: Mapped[str | None] = mapped_column(String(255), nullable=True)

    confirmed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Review cycle (analyst submit -> supervisor approve / refer back) ──
    submitted_for_review_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_for_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submission_comments: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_comments: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    template = relationship("TestTemplateModel")
    test_line = relationship("TRFTestLineModel")
