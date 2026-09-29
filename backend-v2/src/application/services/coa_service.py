"""
Certificate of Analysis Application Service.

Compiles the released TRF results for one product/batch into an immutable,
e-signed certificate.

The design points that carry weight:

* **The snapshot is the certificate.** Everything printed is captured at
  generation — product header, per-test rows, specification limits, verdicts, and
  the release signature chain of every contributing TRF. Nothing is resolved at
  render time, so a later edit to the product, specification, or template cannot
  change an issued document (Requirement 8.3 / Property 16).
* **A COA is never revised.** The repository has no `update` and no `delete`; a
  correction is a new certificate that supersedes the old one.
* **Pass/fail is conservative.** A result that cannot be compared to numeric
  limits comes back `NotEvaluated`, never `Pass`. A certificate that silently
  passed something it did not understand would be worse than one that admits a
  human needs to look.
* **Results come from the worksheet snapshot where there is one.** The test line's
  `result` column is a formatted string shared with the free-text path
  (`"108.84 %"`); parsing it back apart would be guessing. The worksheet snapshot
  holds the number and the unit separately.

E-signature verification is performed by the caller (endpoint layer) before
`generate` runs, matching the MRN/TRF/template pattern. Generation writes one
`AuditLog` entry.
"""
import re
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.certificate_of_analysis import (
    CertificateOfAnalysis,
    COAStatus,
    COATestRow,
    Verdict,
    evaluate_result,
    format_specification,
    overall_verdict,
)
from src.domain.entities.product import Product
from src.domain.entities.specification import Specification, SpecificationTest
from src.domain.entities.trf import TestRequestForm, TRFTestLine
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.coa_repository import ICOARepository
from src.domain.repositories.product_repository import IProductRepository
from src.domain.repositories.specification_repository import ISpecificationRepository
from src.domain.repositories.test_template_repository import ITestWorksheetRepository
from src.domain.repositories.trf_repository import ITRFRepository
from src.domain.services.coa_number_generator import COANumberGenerator

#  A result string is treated as numeric only when the WHOLE value is a number
#  plus an optional unit token. `"99.8 %"` and `"1.5 mg/mL"` qualify;
#  `"Not more than 0.1"` and `"90.0 % to 110.0 %"` deliberately do not — reading a
#  number out of prose would invent a comparison the analyst never made.
_NUMERIC_RESULT = re.compile(r"^([+-]?\d+(?:\.\d+)?)\s*([^\s\d]*)$")

_SOURCE_WORKSHEET = "Worksheet"
_SOURCE_FREE_TEXT = "FreeText"


class COAService:
    def __init__(
        self,
        coa_repo: ICOARepository,
        trf_repo: ITRFRepository,
        worksheet_repo: ITestWorksheetRepository,
        spec_repo: ISpecificationRepository,
        product_repo: IProductRepository,
        audit_repo: IAuditLogRepository,
    ) -> None:
        self._repo = coa_repo
        self._trf_repo = trf_repo
        self._worksheet_repo = worksheet_repo
        self._spec_repo = spec_repo
        self._product_repo = product_repo
        self._audit_repo = audit_repo

    # ── Read ─────────────────────────────────────────────────────────

    async def get(self, coa_id: int) -> CertificateOfAnalysis:
        coa = await self._repo.get_by_id(coa_id)
        if coa is None:
            raise NotFoundException("Certificate of Analysis not found")
        return coa

    async def list_coas(
        self, product_id: int | None = None, batch_number: str | None = None
    ) -> list[CertificateOfAnalysis]:
        return await self._repo.list_all(product_id=product_id, batch_number=batch_number)

    # ── Preview ──────────────────────────────────────────────────────

    async def preview(self, product_id: int, batch_number: str) -> dict:
        """
        Compile what a COA *would* contain, without issuing one.

        Lets QA see the compiled certificate — and any failing or unevaluated
        test — before committing an e-signature to it. Nothing is persisted, so
        this is safe to call repeatedly.
        """
        product, trfs, spec = await self._gather(product_id, batch_number)
        rows = await self._compile_rows(trfs, spec)
        return self._build_snapshot(product, batch_number, trfs, spec, rows, actor=None)

    # ── Generate ─────────────────────────────────────────────────────

    async def generate(
        self,
        product_id: int,
        batch_number: str,
        actor: User,
        remarks: str | None = None,
    ) -> CertificateOfAnalysis:
        """
        Requirement 8.1, 8.2, 8.3, 8.5: compile, freeze, and issue.

        Rejects when the batch has no released results — a certificate compiled
        from nothing would be a document asserting that no testing was done.
        """
        if not actor.has_role("Admin", "QA"):
            raise ForbiddenException("Only QA or an Admin may issue a Certificate of Analysis")

        product, trfs, spec = await self._gather(product_id, batch_number)
        rows = await self._compile_rows(trfs, spec)
        if not rows:
            raise ValidationException(
                f"The released Test Request Forms for batch {batch_number!r} contain no "
                f"reported results, so there is nothing to certify"
            )

        now = datetime.now(timezone.utc)
        prefix = COANumberGenerator.date_prefix(now)
        count_today = await self._repo.count_by_number_prefix(prefix)
        coa_number = COANumberGenerator.generate(count_today, now)

        snapshot = self._build_snapshot(
            product, batch_number, trfs, spec, rows, actor=actor, remarks=remarks, when=now
        )
        snapshot["coa_number"] = coa_number

        coa = CertificateOfAnalysis(
            coa_number=coa_number,
            product_id=product_id,
            batch_number=batch_number,
            status=COAStatus.RELEASED.value,
            snapshot=snapshot,
            released_by=actor.username,
            released_at=now,
            created_by=actor.username,
            modified_by=actor.username,
        )
        saved = await self._repo.create(coa)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="COA_GENERATED",
                table_name="certificates_of_analysis",
                record_id=saved.id,
                new_values={
                    "coa_number": saved.coa_number,
                    "product_id": product_id,
                    "batch_number": batch_number,
                    "overall_verdict": snapshot["overall_verdict"],
                    "test_count": len(rows),
                    "source_trf_numbers": [t.trf_number for t in trfs],
                    "specification_version": spec.version if spec else None,
                },
            )
        )
        return saved

    # ── Compilation ──────────────────────────────────────────────────

    async def _gather(
        self, product_id: int, batch_number: str
    ) -> tuple[Product, list[TestRequestForm], Specification | None]:
        batch = (batch_number or "").strip()
        if not batch:
            raise ValidationException("A batch number is required")

        product = await self._product_repo.get_by_id(product_id)
        if product is None:
            raise NotFoundException("Product not found")

        trfs = await self._trf_repo.list_released_for_batch(product_id, batch)
        if not trfs:
            raise ValidationException(
                f"No released Test Request Forms exist for {product.name} batch {batch!r}. "
                f"Release the testing before issuing a certificate."
            )

        #  The Active specification, if there is one. Absent is not fatal: the
        #  certificate still reports results, with every verdict NotEvaluated.
        spec = await self._spec_repo.get_active_for_product(product_id)
        return product, trfs, spec

    async def _compile_rows(
        self, trfs: list[TestRequestForm], spec: Specification | None
    ) -> list[COATestRow]:
        """
        Build one row per test across every released TRF for the batch.

        TRFs arrive oldest-first, so keying by `test_id` means a later retest
        naturally supersedes an earlier result rather than appearing twice. A
        certificate listing the same test twice with different numbers would be
        unreadable — and the reportable result is the latest released one.
        """
        spec_by_test = {t.test_id: t for t in (spec.tests if spec else [])}
        rows: dict[int, COATestRow] = {}

        for trf in trfs:
            for line in trf.test_lines:
                spec_test = spec_by_test.get(line.test_id)
                #  An explicit `display_in_coa = False` is the specification
                #  author saying this test is not for the certificate.
                if spec_test is not None and not spec_test.display_in_coa:
                    continue

                row = await self._build_row(trf, line, spec_test)
                if row is not None:
                    rows[line.test_id] = row

        #  Order by the specification where one exists, so the certificate reads
        #  in the lab's own sequence rather than database order.
        spec_order = {t.test_id: i for i, t in enumerate(spec.tests)} if spec else {}
        return sorted(
            rows.values(),
            key=lambda r: (spec_order.get(r.test_id, len(spec_order)), r.test_code or ""),
        )

    async def _build_row(
        self,
        trf: TestRequestForm,
        line: TRFTestLine,
        spec_test: SpecificationTest | None,
    ) -> COATestRow | None:
        """One certificate row, or `None` when the line has no reported result."""
        worksheet = await self._worksheet_repo.get_by_test_line(line.id)

        numeric: float | None = None
        unit: str | None = None
        result_text = (line.result or "").strip()
        source = _SOURCE_FREE_TEXT
        template_code: str | None = None
        template_version: int | None = None

        if worksheet is not None and worksheet.is_confirmed and worksheet.computed_snapshot:
            #  Requirement 8.6: worksheet-derived where a template was used. The
            #  snapshot carries the number and unit separately, so nothing has to
            #  be parsed back out of the formatted result string.
            snap = worksheet.computed_snapshot
            reportable = snap.get("reportable_result")
            if isinstance(reportable, (int, float)) and not isinstance(reportable, bool):
                numeric = float(reportable)
            template = snap.get("template") or {}
            unit = template.get("result_unit")
            template_code = template.get("code")
            template_version = template.get("version")
            source = _SOURCE_WORKSHEET
            result_text = worksheet.reportable_result or result_text

        if not result_text:
            #  A test line that was released without a result contributes nothing.
            #  Printing an empty row would imply the test was reported.
            return None

        if numeric is None:
            #  Free-text path: accept a value only if the whole string is a number
            #  plus an optional unit.
            numeric, parsed_unit = _parse_numeric(result_text)
            unit = unit or parsed_unit

        min_limit = spec_test.min_limit if spec_test else None
        max_limit = spec_test.max_limit if spec_test else None
        expected = spec_test.expected_result if spec_test else None
        limit_unit = spec_test.unit if spec_test else None

        verdict, reason = evaluate_result(numeric, min_limit, max_limit, unit, limit_unit)

        return COATestRow(
            test_id=line.test_id,
            test_code=line.test_code,
            test_name=line.test_name,
            specification_text=(
                format_specification(min_limit, max_limit, expected)
                if spec_test is not None
                #  No specification entry at all — fall back to whatever the TRF
                #  line recorded, so the certificate is not silently blank.
                else (line.specification or "-")
            ),
            result_text=result_text,
            verdict=verdict,
            source=source,
            trf_number=trf.trf_number,
            ar_number=trf.ar_number,
            template_code=template_code,
            template_version=template_version,
            numeric_result=numeric,
            unit=unit,
            min_limit=min_limit,
            max_limit=max_limit,
            limit_unit=limit_unit,
            not_evaluated_reason=reason,
        )

    # ── Snapshot ─────────────────────────────────────────────────────

    def _build_snapshot(
        self,
        product: Product,
        batch_number: str,
        trfs: list[TestRequestForm],
        spec: Specification | None,
        rows: list[COATestRow],
        actor: User | None,
        remarks: str | None = None,
        when: datetime | None = None,
    ) -> dict:
        """
        The whole certificate as a single JSON document.

        Header values come from the TRFs rather than only the product master,
        because a TRF records what was actually submitted for this batch — the
        label claim and pack details as tested. Product master data is included
        alongside for identification.
        """
        #  Header fields are taken from the earliest released TRF and filled in
        #  from later ones only where it left them blank, so the certificate
        #  reflects the batch as first submitted without dropping detail.
        header = _merge_header(trfs)
        verdicts = [r.verdict for r in rows]

        return {
            #  Set by `generate`; absent on a preview, which is how a caller can
            #  tell an unissued compilation from a real certificate.
            "coa_number": None,
            "generated_at": (when or datetime.now(timezone.utc)).isoformat(),
            "product": {
                "id": product.id,
                "code": product.code,
                "name": product.name,
                "material_type": product.material_type,
                "storage_condition": product.storage_condition,
            },
            "batch": {
                "batch_number": batch_number,
                "label_claim": header.get("label_claim"),
                "stage_of_sample": header.get("stage_of_sample"),
                "pack_details": header.get("pack_details"),
                "manufactured_by": header.get("manufactured_by"),
                "mfg_date": header.get("mfg_date"),
                "expiry_or_retest_date": header.get("expiry_or_retest_date"),
                "quantity": header.get("quantity"),
                "storage_condition": header.get("storage_condition"),
            },
            "references": {
                "trf_numbers": [t.trf_number for t in trfs],
                "ar_numbers": [t.ar_number for t in trfs if t.ar_number],
            },
            "specification": (
                {
                    "id": spec.id,
                    "version": spec.version,
                    "document_no": spec.document_no,
                    "spec_type": spec.spec_type,
                    "approved_by": spec.approved_by,
                }
                if spec
                else None
            ),
            "tests": [r.to_dict() for r in rows],
            "overall_verdict": overall_verdict(verdicts),
            "verdict_counts": {
                Verdict.PASS.value: verdicts.count(Verdict.PASS.value),
                Verdict.FAIL.value: verdicts.count(Verdict.FAIL.value),
                Verdict.NOT_EVALUATED.value: verdicts.count(Verdict.NOT_EVALUATED.value),
            },
            #  Requirement 8.2: the release signature chain of every contributing
            #  TRF, captured here so the certificate stands alone as evidence.
            "signatures": [_signature_chain(t) for t in trfs],
            "issued_by": (
                {
                    "username": actor.username,
                    "full_name": actor.full_name,
                    "role": actor.role,
                }
                if actor
                else None
            ),
            "remarks": remarks,
        }


# ── Helpers ──────────────────────────────────────────────────────────


def _parse_numeric(text: str) -> tuple[float | None, str | None]:
    """
    Extract a number and unit from a result string, or `(None, None)`.

    Only matches when the entire string is a number plus an optional unit token,
    so prose like `"Not more than 0.1"` is left unevaluated rather than being
    misread as the value 0.1.
    """
    match = _NUMERIC_RESULT.match(text.strip())
    if match is None:
        return None, None
    try:
        return float(match.group(1)), (match.group(2) or None)
    except ValueError:
        return None, None


def _merge_header(trfs: list[TestRequestForm]) -> dict:
    """
    Batch header from the released TRFs — earliest wins, later ones fill gaps.

    Multiple TRFs for one batch normally repeat the same header, but a retest may
    have been raised with fewer fields completed. Taking the earliest as
    authoritative and only filling blanks avoids a partially-filled later form
    blanking detail the original recorded.
    """
    fields = (
        "label_claim",
        "stage_of_sample",
        "pack_details",
        "manufactured_by",
        "quantity",
        "storage_condition",
    )
    merged: dict = {}
    for trf in trfs:
        for name in fields:
            value = getattr(trf, name, None)
            if merged.get(name) in (None, "") and value not in (None, ""):
                merged[name] = value
        for name in ("mfg_date", "expiry_or_retest_date"):
            value = getattr(trf, name, None)
            if merged.get(name) is None and value is not None:
                merged[name] = value.isoformat() if hasattr(value, "isoformat") else value
    return merged


def _signature_chain(trf: TestRequestForm) -> dict:
    """The five-gate signature chain for one contributing TRF."""
    return {
        "trf_number": trf.trf_number,
        "ar_number": trf.ar_number,
        "initiated_by": trf.initiated_by,
        "initiated_at": _iso(trf.initiated_at),
        "fdgl_approved_by": trf.fdgl_approved_by,
        "fdgl_approved_at": _iso(trf.fdgl_approved_at),
        "adgl_accepted_by": trf.adgl_accepted_by,
        "adgl_accepted_at": _iso(trf.adgl_accepted_at),
        "analyst_accepted_by": trf.analyst_accepted_by,
        "analyst_accepted_at": _iso(trf.analyst_accepted_at),
        "results_submitted_by": trf.results_submitted_by,
        "results_submitted_at": _iso(trf.results_submitted_at),
        "released_by": trf.released_by,
        "released_at": _iso(trf.released_at),
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
