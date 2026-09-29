"""Domain service: generates unique Sample codes (A.R. Numbers)."""
from datetime import datetime, timezone


class SampleCodeGenerator:
    """
    Generates Sample codes in the format SMP-YYYYMMDD-XXXX.
    Sequence resets daily and is unique across the system (per URS requirement
    that the AR number resets every year and is unique across plants).
    """

    @staticmethod
    def generate(existing_count_today: int, when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        date_str = when.strftime("%Y%m%d")
        seq = existing_count_today + 1
        return f"SMP-{date_str}-{seq:04d}"

    @staticmethod
    def date_prefix(when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        return f"SMP-{when.strftime('%Y%m%d')}-"
