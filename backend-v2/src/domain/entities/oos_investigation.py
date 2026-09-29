"""Out-of-Specification (OOS) Investigation domain entity."""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base_entity import BaseEntity


@dataclass
class OOSInvestigation(BaseEntity):
    """
    OOS Investigation aggregate.

    Business Rules:
    - Auto-created by the system when a SampleResult is flagged OOS.
    - Must capture root_cause + corrective_action before closing.
    - Closing the last Open OOS on a Sample returns Sample to 'Under Review'.
    """

    sample_id: int = field(default=0)
    test_id: int = field(default=0)
    investigation_type: str = field(default="OOS")  # OOS, OOT
    phase1_comments: str = field(default="")
    root_cause: str | None = field(default=None)
    corrective_action: str | None = field(default=None)
    status: str = field(default="Open")  # Open, Closed
    closed_by: str | None = field(default=None)
    closed_at: datetime | None = field(default=None)

    def close(self, closer: str, when: datetime, root_cause: str, corrective_action: str) -> None:
        self.root_cause = root_cause
        self.corrective_action = corrective_action
        self.status = "Closed"
        self.closed_by = closer
        self.closed_at = when
        self.mark_modified(closer)
