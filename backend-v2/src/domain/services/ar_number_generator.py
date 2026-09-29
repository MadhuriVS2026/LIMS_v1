"""Domain service: generates unique AR (Analyst Reference) numbers, assigned to a TRF at ADGL Accept."""
from datetime import datetime, timezone


class ARNumberGenerator:
    """
    Generates AR numbers in the format AR-YYYYMMDD-XXXX.
    Sequence resets daily and is unique across the system, mirroring
    TRFNumberGenerator's convention.
    """

    @staticmethod
    def generate(existing_count_today: int, when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        date_str = when.strftime("%Y%m%d")
        seq = existing_count_today + 1
        return f"AR-{date_str}-{seq:04d}"

    @staticmethod
    def date_prefix(when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        return f"AR-{when.strftime('%Y%m%d')}-"
