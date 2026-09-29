"""Domain service: generates unique test-template codes."""


class TemplateCodeGenerator:
    """
    Generates template codes in the format `TPL-<ARCHETYPE>-XXXX`.

    Unlike the MRN/TRF/AR generators, this is not date-scoped: a template is
    long-lived master data, so the sequence runs per archetype rather than
    resetting daily. Versions of the same template share one code and are
    distinguished by `TestTemplate.version`.
    """

    @staticmethod
    def generate(archetype: str, existing_count_for_archetype: int) -> str:
        seq = existing_count_for_archetype + 1
        return f"TPL-{TemplateCodeGenerator._normalize(archetype)}-{seq:04d}"

    @staticmethod
    def archetype_prefix(archetype: str) -> str:
        """Prefix used to count existing codes for an archetype."""
        return f"TPL-{TemplateCodeGenerator._normalize(archetype)}-"

    @staticmethod
    def _normalize(archetype: str) -> str:
        """Uppercase, with anything non-alphanumeric collapsed to a hyphen."""
        cleaned = "".join(ch if ch.isalnum() else "-" for ch in (archetype or "GEN").upper())
        return cleaned.strip("-") or "GEN"
