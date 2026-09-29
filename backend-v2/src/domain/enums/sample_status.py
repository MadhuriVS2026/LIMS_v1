"""Sample lifecycle status enum."""
from enum import StrEnum


class SampleStatus(StrEnum):
    LOGGED = "Logged"
    RECEIVED = "Received"
    UNDER_REVIEW = "Under Review"
    OOS_INVESTIGATION = "OOS Investigation"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class UserRole(StrEnum):
    ADMIN = "Admin"
    ANALYST = "Analyst"
    SUPERVISOR = "Supervisor"
    QA = "QA"
