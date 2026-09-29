"""Test Parameter domain entity — analytical test master data."""
from dataclasses import dataclass, field

from src.domain.entities.base_entity import BaseEntity


@dataclass
class TestParameter(BaseEntity):
    """
    Test parameter master (named TestParameter to avoid pytest collision with 'Test').

    Business Rules:
    - Code must be unique.
    - Type determines how results are evaluated (Quantitative vs Qualitative).
    """

    code: str = field(default="")
    name: str = field(default="")
    type: str = field(default="Quantitative")  # Quantitative, Qualitative, Statistical-1/2, Multi-*
    unit: str | None = field(default=None)
    method_no: str | None = field(default=None)
    category: str | None = field(default=None)
    technique: str | None = field(default=None)
    status: str = field(default="Active")

    def is_quantitative(self) -> bool:
        return self.type == "Quantitative"
