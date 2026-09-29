"""Domain service: generates unique TRF (Test Request Form) numbers."""
from datetime import datetime, timezone


class TRFNumberGenerator:
    """
    Generates TRF numbers in the format TRF-YYYYMMDD-XXXX.
    Sequence resets daily and is unique across the system, mirroring
    MRNNumberGenerator's/SampleCodeGenerator's convention.
    """

    @staticmethod
    def generate(existing_count_today: int, when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        date_str = when.strftime("%Y%m%d")
        seq = existing_count_today + 1
        return f"TRF-{date_str}-{seq:04d}"

    @staticmethod
    def date_prefix(when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        return f"TRF-{when.strftime('%Y%m%d')}-"
