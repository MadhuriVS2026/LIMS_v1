"""Pydantic schemas for Audit Log & Dashboard endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    username: str
    action: str
    table_name: str
    record_id: int | None = None
    old_values: dict | None = None
    new_values: dict | None = None
    comments: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DashboardStatsResponse(BaseModel):
    total_samples: int
    pending_samples: int
    oos_open: int
    samples_today: int
    instruments_due_calibration: int
    pending_reviews: int
    approved_today: int
    rejected_today: int
