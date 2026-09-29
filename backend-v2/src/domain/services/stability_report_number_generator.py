"""Domain service: generates unique Stability Report numbers."""
from datetime import datetime, timezone


class StabilityReportNumberGenerator:
    """
    Generates Stability Report numbers in the format STAB-RPT-YYYYMMDD-XXXX.
    Sequence resets daily and is unique across the system, mirroring
    StabilityCodeGenerator's convention.
    """

    @staticmethod
    def generate(existing_count_today: int, when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        date_str = when.strftime("%Y%m%d")
        seq = existing_count_today + 1
        return f"STAB-RPT-{date_str}-{seq:04d}"

    @staticmethod
    def date_prefix(when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        return f"STAB-RPT-{when.strftime('%Y%m%d')}-"
