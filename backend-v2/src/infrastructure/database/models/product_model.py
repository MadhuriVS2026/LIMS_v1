"""SQLAlchemy ORM model for Product/Material."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base_model import BaseModel


class ProductModel(BaseModel):
    __tablename__ = "products"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    material_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    retest_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_condition: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Pending Approval")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    specifications = relationship("SpecificationModel", back_populates="product")
