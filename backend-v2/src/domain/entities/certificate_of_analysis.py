"""
Certificate of Analysis domain entity, plus the pass/fail evaluation that drives it.

A COA is generated once, e-signed, and never edited. Its `snapshot` holds the
whole certificate — header, per-test rows, and the release signature chain — so
the document stays reproducible even if the product, specification, or template
data behind it later changes (Requirement 8.3 / Property 16).

The interesting logic here is `evaluate_result`, which decides Pass/Fail. It
lives in the domain because it is the certificate's central claim, and it is
deliberately conservative: anything it cannot judge numerically comes back as
`NOT_EVALUATED` rather than being assumed to pass. A COA that silently passes a
result it did not understand would be worse than one that admits it needs a human.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.domain.entities.base_entity import BaseEntity
from src.domain.entities.specification import units_comparable


class COAStatus(str, Enum):
    #  Only one status: a COA exists or it does not. There is no draft — an
    #  unsigned certificate has no meaning, so generation is the signing.
    RELEASED = "Released"


class Verdict(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"
    #  A result that cannot be compared to a numeric limit: a qualitative test
    #  ("Complies"), a missing specification, or an unparseable result.
    NOT_EVALUATED = "NotEvaluated"


@dataclass(frozen=True)
class COATestRow:
    """One test line on the certificate."""

    test_id: int
    test_code: str | None
    test_name: str | None
    specification_text: str
    result_text: str
    verdict: str
    #  Provenance: `Worksheet` when a template produced the number, `FreeText`
    #  when the analyst typed it. Requirement 8.6 asks for both to appear, and a
    #  reviewer needs to know which they are looking at.
    source: str
    trf_number: str | None = None
    ar_number: str | None = None
    template_code: str | None = None
    template_version: int | None = None
    #  Populated only for worksheet-derived rows.
    numeric_result: float | None = None
    unit: str | None = None
    min_limit: float | None = None
    max_limit: float | None = None
    limit_unit: str | None = None
    #  Why a row could not be judged, when it could not be. Printed on the
    #  certificate so a `NotEvaluated` is never left looking like an omission.
    not_evaluated_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "test_code": self.test_code,
            "test_name": self.test_name,
            "specification_text": self.specification_text,
            "result_text": self.result_text,
            "verdict": self.verdict,
            "source": self.source,
            "trf_number": self.trf_number,
            "ar_number": self.ar_number,
            "template_code": self.template_code,
            "template_version": self.template_version,
            "numeric_result": self.numeric_result,
            "unit": self.unit,
            "min_limit": self.min_limit,
            "max_limit": self.max_limit,
            "limit_unit": self.limit_unit,
            "not_evaluated_reason": self.not_evaluated_reason,
        }


@dataclass
class CertificateOfAnalysis(BaseEntity):
    """
    An issued certificate for one product/batch.

    `snapshot` is the certificate. The columns beside it exist only so a COA can
    be found without opening the JSON.
    """

    coa_number: str = field(default="")
    product_id: int = field(default=0)
    batch_number: str = field(default="")
    status: str = field(default=COAStatus.RELEASED.value)

    snapshot: dict = field(default_factory=dict)

    released_by: str = field(default="")
    released_at: datetime | None = field(default=None)

    # ── Denormalized for list projection ──
    product_code: str | None = field(default=None)
    product_name: str | None = field(default=None)

    @property
    def overall_verdict(self) -> str:
        """
        The certificate's conclusion, read from the frozen snapshot rather than
        recomputed — recomputing could disagree with the issued document.
        """
        return str(self.snapshot.get("overall_verdict", Verdict.NOT_EVALUATED.value))

    @property
    def test_count(self) -> int:
        tests = self.snapshot.get("tests")
        return len(tests) if isinstance(tests, list) else 0

    @property
    def has_failure(self) -> bool:
        return self.overall_verdict == Verdict.FAIL.value


def evaluate_result(
    numeric_result: float | None,
    min_limit: float | None,
    max_limit: float | None,
    result_unit: str | None = None,
    limit_unit: str | None = None,
) -> tuple[str, str | None]:
    """
    Compare a numeric result against specification limits.

    Returns `(verdict, reason)` where `reason` explains a `NOT_EVALUATED` — never
    `PASS` — when there is nothing legitimate to compare:

    * no numeric result (a qualitative test such as "Description: white powder");
    * no limits at all — a COA claiming to have verified something against limits
      that do not exist would be a false statement;
    * **units that definitely disagree.** This is the case that produced a Fail
      comparing an assay of 108.84 % against limits of 9 to 11. Refusing to judge
      is right: the comparison is meaningless, and neither Pass nor Fail is an
      honest answer.

    One-sided limits are honoured: a specification with only `max_limit` ("NMT
    0.5 %") is a valid comparison and is evaluated as such.
    """
    if numeric_result is None:
        return Verdict.NOT_EVALUATED.value, "No numeric result to compare"
    if min_limit is None and max_limit is None:
        return Verdict.NOT_EVALUATED.value, "No numeric specification limits"
    if not units_comparable(result_unit, limit_unit):
        return (
            Verdict.NOT_EVALUATED.value,
            f"Result is in {result_unit!r} but the specification limits are in "
            f"{limit_unit!r} — the two are not comparable",
        )

    if min_limit is not None and numeric_result < min_limit:
        return Verdict.FAIL.value, None
    if max_limit is not None and numeric_result > max_limit:
        return Verdict.FAIL.value, None
    return Verdict.PASS.value, None


def overall_verdict(verdicts: list[str]) -> str:
    """
    Roll per-test verdicts into the certificate's conclusion.

    Any single failure fails the batch. If nothing failed but nothing could be
    evaluated either, the result is `NOT_EVALUATED` rather than `PASS` — a
    certificate must not claim a pass it never established.
    """
    if not verdicts:
        return Verdict.NOT_EVALUATED.value
    if Verdict.FAIL.value in verdicts:
        return Verdict.FAIL.value
    if Verdict.PASS.value in verdicts:
        return Verdict.PASS.value
    return Verdict.NOT_EVALUATED.value


def format_specification(
    min_limit: float | None, max_limit: float | None, expected_result: str | None
) -> str:
    """
    Render a specification for the printed certificate.

    `expected_result` wins when present: for a qualitative test it is the actual
    specification ("White to off-white powder"), and where a lab has written both
    it is the more precise statement of intent.
    """
    if expected_result and expected_result.strip():
        return expected_result.strip()
    if min_limit is not None and max_limit is not None:
        return f"{_num(min_limit)} to {_num(max_limit)}"
    if max_limit is not None:
        return f"NMT {_num(max_limit)}"
    if min_limit is not None:
        return f"NLT {_num(min_limit)}"
    return "-"


def _num(value: float) -> str:
    """Trim float-repr artefacts so a limit of 0.5 does not print as 0.5000000001."""
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text or "0"
