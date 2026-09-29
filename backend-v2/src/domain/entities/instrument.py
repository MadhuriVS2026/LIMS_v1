"""Instrument domain entity — Resource Manager module."""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base_entity import BaseEntity


@dataclass
class Instrument(BaseEntity):
    """Laboratory instrument master with calibration tracking."""

    code: str = field(default="")
    name: str = field(default="")
    category: str | None = field(default=None)
    manufacturer: str | None = field(default=None)
    model_number: str | None = field(default=None)
    serial_number: str | None = field(default=None)
    location: str | None = field(default=None)
    status: str = field(default="Active")  # Active, Under Calibration, Under Maintenance, Inactive
    calibration_due_date: datetime | None = field(default=None)
    calibration_frequency_days: int | None = field(default=None)
    last_calibrated_at: datetime | None = field(default=None)
    last_calibrated_by: str | None = field(default=None)
    qualification_status: str | None = field(default=None)

    def record_calibration(self, when: datetime, by: str, next_due: datetime | None, result: str) -> None:
        self.last_calibrated_at = when
        self.last_calibrated_by = by
        self.calibration_due_date = next_due
        if result == "Pass":
            self.status = "Active"
            self.qualification_status = "Qualified"
        self.mark_modified(by)

    def is_calibration_due_within(self, days: int, now: datetime) -> bool:
        if not self.calibration_due_date:
            return False
        from datetime import timedelta
        return self.calibration_due_date <= now + timedelta(days=days)
