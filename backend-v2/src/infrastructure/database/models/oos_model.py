"""SQLAlchemy ORM model for OOS Investigation."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class OOSInvestigationModel(BaseModel):
    __tablename__ = "oos_investigations"

    sample_id: Mapped[int] = mapped_column(Integer, ForeignKey("samples.id"), nullable=False)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("tests.id"), nullable=False)
    investigation_type: Mapped[str] = mapped_column(String(20), default="OOS")
    phase1_comments: Mapped[str] = mapped_column(String(1000), nullable=False)
    root_cause: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    corrective_action: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Open")
    closed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sample = relationship("SampleModel")
    test = relationship("TestModel")
