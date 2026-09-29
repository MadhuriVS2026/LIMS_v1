"""Product/Material domain entity — master data for QC testing."""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base_entity import BaseEntity


@dataclass
class Product(BaseEntity):
    """
    Product/Material master entity.

    Business Rules:
    - Code must be unique.
    - Must be Approved by Supervisor/QA before it can be used in a Sample.
    """

    code: str = field(default="")
    name: str = field(default="")
    description: str | None = field(default=None)
    material_type: str | None = field(default=None)  # RM, PM, FG, IP
    retest_period_days: int | None = field(default=None)
    storage_condition: str | None = field(default=None)
    status: str = field(default="Pending Approval")  # Pending Approval, Active, Inactive
    approved_by: str | None = field(default=None)
    approved_at: datetime | None = field(default=None)

    def approve(self, approver: str, when: datetime) -> None:
        self.status = "Active"
        self.approved_by = approver
        self.approved_at = when
        self.mark_modified(approver)

    def is_active(self) -> bool:
        return self.status == "Active"
