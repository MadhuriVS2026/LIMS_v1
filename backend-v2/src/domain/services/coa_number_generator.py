"""Domain service: generates unique COA (Certificate of Analysis) numbers."""
from datetime import datetime, timezone


class COANumberGenerator:
    """
    Generates COA numbers in the format `COA-YYYYMMDD-XXXX`.

    Date-scoped with a daily-resetting sequence, matching TRFNumberGenerator and
    ARNumberGenerator — a certificate is a dated document, so the issue date
    belongs in its identifier.
    """

    @staticmethod
    def generate(existing_count_today: int, when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        seq = existing_count_today + 1
        return f"COA-{when.strftime('%Y%m%d')}-{seq:04d}"

    @staticmethod
    def date_prefix(when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        return f"COA-{when.strftime('%Y%m%d')}-"
