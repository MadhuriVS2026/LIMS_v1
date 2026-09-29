"""Specification domain entity — versioned test limits linked to a Product."""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base_entity import BaseEntity


def normalise_unit(unit: str | None) -> str | None:
    """
    Reduce a unit to a comparable form, or `None` when unspecified.

    Only casing, spacing and the common ASCII spellings of `µ` are normalised.
    Deliberately no conversion factors: treating `mg` and `g` as compatible would
    require deciding a scale, and silently rescaling a GxP result is far worse
    than refusing to judge it.
    """
    if unit is None:
        return None
    cleaned = unit.strip().lower().replace(" ", "")
    if not cleaned:
        return None
    #  `ug`, `mcg` and `µg` are the same unit written three ways.
    return cleaned.replace("μ", "µ").replace("mcg", "µg").replace("ug", "µg")


def units_comparable(result_unit: str | None, limit_unit: str | None) -> bool:
    """
    Whether a result may be compared against a limit.

    Unknown on either side is *permitted*: most existing specifications carry no
    unit, and refusing every one of them would block certificates that are fine.
    Only a definite disagreement is a problem — that is the case which produced a
    Fail verdict comparing 108.84 % against limits of 9 to 11.
    """
    left = normalise_unit(result_unit)
    right = normalise_unit(limit_unit)
    if left is None or right is None:
        return True
    return left == right


@dataclass
class SpecificationTest:
    """Value object: a single test's limits within a Specification."""

    test_id: int
    min_limit: float | None = None
    max_limit: float | None = None
    #  The unit the limits are expressed in. Optional for backward compatibility,
    #  but without it nothing can detect that a result and its limits are on
    #  different scales.
    unit: str | None = None
    expected_result: str | None = None
    display_in_coa: bool = True
    id: int = 0


@dataclass
class Specification(BaseEntity):
    """
    Specification aggregate — a versioned set of test limits for a Product.

    Business Rules:
    - Only one Specification per Product can be 'Active' at a time.
    - Approving a new version automatically deactivates the previous Active version.
    - version increments automatically per Product.
    """

    product_id: int = field(default=0)
    version: int = field(default=1)
    spec_type: str | None = field(default=None)
    document_no: str | None = field(default=None)
    status: str = field(default="Pending Approval")
    approved_by: str | None = field(default=None)
    approved_at: datetime | None = field(default=None)
    tests: list[SpecificationTest] = field(default_factory=list)

    def approve(self, approver: str, when: datetime) -> None:
        self.status = "Active"
        self.approved_by = approver
        self.approved_at = when
        self.mark_modified(approver)

    def update_details(
        self,
        editor: str,
        *,
        spec_type: str | None = None,
        document_no: str | None = None,
        tests: list["SpecificationTest"] | None = None,
    ) -> None:
        """
        Edit the specification. `spec_type`/`document_no` left as None are
        unchanged; passing `tests` replaces the full set of test limits.

        Editing an Active specification invalidates its approval: it returns to
        "Pending Approval" and must be re-approved before use.
        """
        if spec_type is not None:
            self.spec_type = spec_type
        if document_no is not None:
            self.document_no = document_no
        if tests is not None:
            self.tests = tests

        if self.status == "Active":
            self.status = "Pending Approval"
            self.approved_by = None
            self.approved_at = None
        self.mark_modified(editor)

    def deactivate(self, actor: str) -> None:
        """Soft-delete: retire this specification without removing the record."""
        self.status = "Inactive"
        self.mark_modified(actor)
