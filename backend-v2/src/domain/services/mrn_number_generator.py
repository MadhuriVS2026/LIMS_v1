"""Domain service: generates unique MRN (Material Requisition Note) numbers."""
from datetime import datetime, timezone


class MRNNumberGenerator:
    """
    Generates MRN numbers in the format MRN-YYYYMMDD-XXXX.
    Sequence resets daily and is unique across the system, mirroring
    SampleCodeGenerator's convention for Sample codes.
    """

    @staticmethod
    def generate(existing_count_today: int, when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        date_str = when.strftime("%Y%m%d")
        seq = existing_count_today + 1
        return f"MRN-{date_str}-{seq:04d}"

    @staticmethod
    def date_prefix(when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        return f"MRN-{when.strftime('%Y%m%d')}-"
