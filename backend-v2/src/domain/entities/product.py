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

    def update_details(
        self,
        editor: str,
        *,
        name: str | None = None,
        description: str | None = None,
        material_type: str | None = None,
        retest_period_days: int | None = None,
        storage_condition: str | None = None,
    ) -> None:
        """
        Apply an edit to the master data. Any field left as None is unchanged.

        Editing an already-approved (Active) product invalidates its prior
        approval: it returns to "Pending Approval" and must be re-approved by a
        Supervisor/QA before it can be used again. A record still awaiting its
        first approval simply stays pending.
        """
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if material_type is not None:
            self.material_type = material_type
        if retest_period_days is not None:
            self.retest_period_days = retest_period_days
        if storage_condition is not None:
            self.storage_condition = storage_condition

        if self.status == "Active":
            self.status = "Pending Approval"
            self.approved_by = None
            self.approved_at = None
        self.mark_modified(editor)

    def deactivate(self, actor: str) -> None:
        """Soft-delete: retire the product without removing the record."""
        self.status = "Inactive"
        self.mark_modified(actor)
