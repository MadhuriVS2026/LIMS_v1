"""SQLAlchemy ORM models for Specification & SpecificationTest."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class SpecificationModel(BaseModel):
    __tablename__ = "specifications"

    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    spec_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    document_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Pending Approval")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    product = relationship("ProductModel", back_populates="specifications")
    tests = relationship("SpecificationTestModel", back_populates="specification")


class SpecificationTestModel(BaseModel):
    __tablename__ = "specification_tests"

    specification_id: Mapped[int] = mapped_column(Integer, ForeignKey("specifications.id"), nullable=False)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("tests.id"), nullable=False)
    min_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    #  Unit the limits are expressed in. Nullable for backward compatibility —
    #  existing specifications have none — but where present it is checked against
    #  the template's `result_unit` so a % result is never judged against mg/mL.
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expected_result: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_in_coa: Mapped[bool] = mapped_column(Boolean, default=True)

    specification = relationship("SpecificationModel", back_populates="tests")
    test = relationship("TestModel")
