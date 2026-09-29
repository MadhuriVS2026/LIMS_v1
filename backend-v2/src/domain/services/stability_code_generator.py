"""Domain service: generates unique Stability Protocol codes."""
from datetime import datetime, timezone


class StabilityCodeGenerator:
    """
    Generates Stability Protocol codes in the format STAB-YYYYMMDD-XXXX.
    Sequence resets daily and is unique across the system, mirroring
    SampleCodeGenerator's/MRNNumberGenerator's convention.
    """

    @staticmethod
    def generate(existing_count_today: int, when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        date_str = when.strftime("%Y%m%d")
        seq = existing_count_today + 1
        return f"STAB-{date_str}-{seq:04d}"

    @staticmethod
    def date_prefix(when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        return f"STAB-{when.strftime('%Y%m%d')}-"
