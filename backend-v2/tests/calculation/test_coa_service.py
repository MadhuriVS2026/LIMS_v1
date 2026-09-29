"""
COAService tests.

The two claims that matter on a certificate are covered here:

* **Property 16 — a captured snapshot never changes.** Editing the product,
  specification, or worksheet after issue must not alter the issued document.
* **Pass/fail is conservative.** Anything that cannot be compared to numeric
  limits comes back `NotEvaluated`, never `Pass`. A certificate that silently
  passed a result it did not understand would be worse than one that admits a
  human needs to look.

Expected verdicts are derived from the limits by hand rather than from a previous
run, so a regression in `evaluate_result` shows up as a failure rather than being
baked in.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from src.application.exceptions.application_exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.application.services.coa_service import COAService
from src.domain.entities.certificate_of_analysis import (
    Verdict,
    evaluate_result,
    format_specification,
    overall_verdict,
)
from src.infrastructure.database.models.coa_model import CertificateOfAnalysisModel
from src.infrastructure.database.models.product_model import ProductModel
from src.infrastructure.database.models.specification_model import (
    SpecificationModel,
    SpecificationTestModel,
)
from src.infrastructure.database.models.test_template_model import (
    TestTemplateModel,
    TestWorksheetModel,
)
from src.infrastructure.database.models.trf_model import (
    TestRequestFormModel,
    TRFTestLineModel,
)
from src.infrastructure.database.repositories.audit_repository_impl import (
    AuditLogRepositoryImpl,
)
from src.infrastructure.database.repositories.coa_repository_impl import COARepositoryImpl
from src.infrastructure.database.repositories.product_repository_impl import (
    ProductRepositoryImpl,
)
from src.infrastructure.database.repositories.specification_repository_impl import (
    SpecificationRepositoryImpl,
)
from src.infrastructure.database.repositories.test_template_repository_impl import (
    TestWorksheetRepositoryImpl,
)
from src.infrastructure.database.repositories.trf_repository_impl import TRFRepositoryImpl
from tests.calculation.conftest import seed_test, user

BATCH = "B-2601"
QA = "qa1"


def _service(session) -> COAService:
    return COAService(
        COARepositoryImpl(session),
        TRFRepositoryImpl(session),
        TestWorksheetRepositoryImpl(session),
        SpecificationRepositoryImpl(session),
        ProductRepositoryImpl(session),
        AuditLogRepositoryImpl(session),
    )


def qa_user():
    return user(QA, "QA", user_id=3)


async def seed_product(session, code="PRD-1", name="Paracetamol Tablets") -> ProductModel:
    product = ProductModel(
        code=code, name=name, material_type="FG", status="Active",
        storage_condition="Store below 25 C",
    )
    session.add(product)
    await session.flush()
    return product


async def seed_released_trf(
    session,
    product: ProductModel,
    lines: list[tuple[int, str | None, str | None]],
    *,
    trf_number="TRF-20260806-0001",
    ar_number="AR-20260806-0001",
    batch=BATCH,
    released_at: datetime | None = None,
    label_claim="500 mg",
) -> TestRequestFormModel:
    """A Released TRF carrying `(test_id, specification, result)` lines."""
    trf = TestRequestFormModel(
        trf_number=trf_number,
        ar_number=ar_number,
        product_id=product.id,
        batch_number=batch,
        label_claim=label_claim,
        stage_of_sample="Finished Product",
        pack_details="Alu-Alu blister",
        manufactured_by="Plant 1",
        status="Released",
        initiated_by="analyst",
        initiated_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        fdgl_approved_by="supervisor",
        fdgl_approved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        adgl_accepted_by=QA,
        adgl_accepted_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
        analyst_accepted_by="analyst",
        analyst_accepted_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
        results_submitted_by="analyst",
        results_submitted_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
        released_by=QA,
        released_at=released_at or datetime(2026, 8, 6, tzinfo=timezone.utc),
    )
    session.add(trf)
    await session.flush()

    for index, (test_id, spec_text, result) in enumerate(lines, start=1):
        session.add(
            TRFTestLineModel(
                trf_id=trf.id, line_no=index, test_id=test_id,
                specification=spec_text, result=result,
            )
        )
    await session.flush()
    return trf


async def line_for(session, trf: TestRequestFormModel, test_id: int) -> TRFTestLineModel:
    """
    Fetch a test line explicitly.

    `trf.test_lines` would lazy-load, which raises `MissingGreenlet` under the
    async session — the relationship is only eagerly loaded by the repository's
    own queries.
    """
    return (
        await session.execute(
            select(TRFTestLineModel).where(
                TRFTestLineModel.trf_id == trf.id,
                TRFTestLineModel.test_id == test_id,
            )
        )
    ).scalar_one()


async def seed_spec(
    session,
    product: ProductModel,
    entries: list[tuple[int, float | None, float | None, str | None, bool]],
    *,
    status="Active",
    version=1,
) -> SpecificationModel:
    """`(test_id, min, max, expected_result, display_in_coa)` entries."""
    spec = SpecificationModel(
        product_id=product.id, version=version, spec_type="Release",
        document_no="SPEC-001", status=status, approved_by=QA,
        approved_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    session.add(spec)
    await session.flush()
    for test_id, lo, hi, expected, display in entries:
        session.add(
            SpecificationTestModel(
                specification_id=spec.id, test_id=test_id,
                min_limit=lo, max_limit=hi,
                expected_result=expected, display_in_coa=display,
            )
        )
    await session.flush()
    return spec


# ── Domain: verdict logic ────────────────────────────────────────────


@pytest.mark.parametrize(
    "value, lo, hi, expected",
    [
        (99.5, 95.0, 105.0, Verdict.PASS.value),
        (95.0, 95.0, 105.0, Verdict.PASS.value),  # inclusive lower bound
        (105.0, 95.0, 105.0, Verdict.PASS.value),  # inclusive upper bound
        (94.9, 95.0, 105.0, Verdict.FAIL.value),
        (105.1, 95.0, 105.0, Verdict.FAIL.value),
        (0.3, None, 0.5, Verdict.PASS.value),  # one-sided max
        (0.6, None, 0.5, Verdict.FAIL.value),
        (99.0, 98.0, None, Verdict.PASS.value),  # one-sided min
        (97.0, 98.0, None, Verdict.FAIL.value),
        #  Nothing to compare against — must never be a Pass.
        (99.5, None, None, Verdict.NOT_EVALUATED.value),
        (None, 95.0, 105.0, Verdict.NOT_EVALUATED.value),
        (None, None, None, Verdict.NOT_EVALUATED.value),
    ],
)
def test_evaluate_result_is_conservative(value, lo, hi, expected):
    #  Returns `(verdict, reason)` — the reason states why a NotEvaluated could not
    #  be judged, and is `None` for a decided verdict.
    verdict, reason = evaluate_result(value, lo, hi)
    assert verdict == expected
    assert (reason is None) == (expected != Verdict.NOT_EVALUATED.value)


@pytest.mark.parametrize(
    "verdicts, expected",
    [
        (["Pass", "Pass"], Verdict.PASS.value),
        (["Pass", "Fail"], Verdict.FAIL.value),
        (["Fail", "NotEvaluated"], Verdict.FAIL.value),
        (["Pass", "NotEvaluated"], Verdict.PASS.value),
        #  Nothing evaluated at all must not report a pass.
        (["NotEvaluated"], Verdict.NOT_EVALUATED.value),
        ([], Verdict.NOT_EVALUATED.value),
    ],
)
def test_overall_verdict_rollup(verdicts, expected):
    assert overall_verdict(verdicts) == expected


@pytest.mark.parametrize(
    "lo, hi, expected_result, rendered",
    [
        (95.0, 105.0, None, "95 to 105"),
        (None, 0.5, None, "NMT 0.5"),
        (98.0, None, None, "NLT 98"),
        (None, None, None, "-"),
        #  A qualitative specification wins over numeric limits.
        (95.0, 105.0, "White powder", "White powder"),
        (None, None, "Complies", "Complies"),
    ],
)
def test_format_specification(lo, hi, expected_result, rendered):
    assert format_specification(lo, hi, expected_result) == rendered


# ── Generation ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_compiles_header_tests_and_signatures(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    ph = await seed_test(db_session, code="TST-B", name="pH")
    await seed_spec(
        db_session, product,
        [(assay.id, 95.0, 105.0, None, True), (ph.id, 4.0, 7.0, None, True)],
    )
    await seed_released_trf(
        db_session, product,
        [(assay.id, "95.0 to 105.0 %", "99.8 %"), (ph.id, "4.0 to 7.0", "5.2")],
    )

    svc = _service(db_session)
    coa = await svc.generate(product.id, BATCH, qa_user(), remarks="For release")

    assert coa.coa_number.startswith("COA-")
    assert coa.status == "Released"
    assert coa.released_by == QA
    assert coa.test_count == 2
    assert coa.overall_verdict == Verdict.PASS.value

    snap = coa.snapshot
    assert snap["coa_number"] == coa.coa_number
    assert snap["product"]["code"] == "PRD-1"
    assert snap["batch"]["batch_number"] == BATCH
    assert snap["batch"]["label_claim"] == "500 mg"
    assert snap["batch"]["pack_details"] == "Alu-Alu blister"
    assert snap["references"]["trf_numbers"] == ["TRF-20260806-0001"]
    assert snap["references"]["ar_numbers"] == ["AR-20260806-0001"]
    assert snap["specification"]["document_no"] == "SPEC-001"
    assert snap["remarks"] == "For release"
    assert snap["issued_by"]["username"] == QA
    assert snap["verdict_counts"] == {"Pass": 2, "Fail": 0, "NotEvaluated": 0}

    #  Requirement 8.2: the full release signature chain travels with the COA.
    chain = snap["signatures"][0]
    assert chain["trf_number"] == "TRF-20260806-0001"
    assert chain["fdgl_approved_by"] == "supervisor"
    assert chain["analyst_accepted_by"] == "analyst"
    assert chain["released_by"] == QA
    assert chain["released_at"] is not None

    #  99.8 within 95–105, 5.2 within 4–7.
    verdicts = {t["test_code"]: t["verdict"] for t in snap["tests"]}
    assert verdicts == {"TST-A": Verdict.PASS.value, "TST-B": Verdict.PASS.value}


@pytest.mark.asyncio
async def test_a_failing_result_fails_the_certificate(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_spec(db_session, product, [(assay.id, 95.0, 105.0, None, True)])
    #  110.2 is outside 95–105.
    await seed_released_trf(db_session, product, [(assay.id, "95.0 to 105.0 %", "110.2 %")])

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())

    assert coa.overall_verdict == Verdict.FAIL.value
    assert coa.has_failure is True
    assert coa.snapshot["tests"][0]["verdict"] == Verdict.FAIL.value
    #  A failing certificate is still issued — recording the failure is the point.
    assert coa.id > 0


@pytest.mark.asyncio
async def test_a_qualitative_result_is_not_evaluated_rather_than_passed(db_session):
    product = await seed_product(db_session)
    description = await seed_test(db_session, code="TST-D", name="Description")
    await seed_spec(
        db_session, product, [(description.id, None, None, "White to off-white powder", True)]
    )
    await seed_released_trf(
        db_session, product, [(description.id, "White powder", "Complies")]
    )

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())
    row = coa.snapshot["tests"][0]

    assert row["result_text"] == "Complies"
    assert row["numeric_result"] is None
    assert row["verdict"] == Verdict.NOT_EVALUATED.value
    assert row["specification_text"] == "White to off-white powder"
    #  Nothing was evaluated, so the certificate must not claim a pass.
    assert coa.overall_verdict == Verdict.NOT_EVALUATED.value


@pytest.mark.parametrize(
    "result_text, expected_numeric",
    [
        ("99.8 %", 99.8),
        ("99.8%", 99.8),
        ("5.2", 5.2),
        ("-0.5", -0.5),
        ("1.5 mg/mL", 1.5),
        #  Prose must NOT be mined for a number — that would invent a comparison
        #  the analyst never made.
        ("Not more than 0.1", None),
        ("90.0 % to 110.0 %", None),
        ("Complies", None),
        ("Pass", None),
        ("", None),
    ],
)
@pytest.mark.asyncio
async def test_free_text_results_are_parsed_only_when_unambiguous(
    db_session, result_text, expected_numeric
):
    product = await seed_product(db_session)
    test = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_spec(db_session, product, [(test.id, -1.0, 200.0, None, True)])
    await seed_released_trf(db_session, product, [(test.id, "spec", result_text or None)])

    svc = _service(db_session)
    if not result_text:
        #  A line with no result contributes nothing, so there is nothing to certify.
        with pytest.raises(ValidationException):
            await svc.generate(product.id, BATCH, qa_user())
        return

    coa = await svc.generate(product.id, BATCH, qa_user())
    assert coa.snapshot["tests"][0]["numeric_result"] == expected_numeric


# ── Requirement 8.6: worksheet-derived and free-text side by side ────


@pytest.mark.asyncio
async def test_worksheet_results_are_taken_from_the_snapshot_not_the_result_string(db_session):
    """
    The test line's `result` is a formatted string shared with the free-text path.
    The worksheet snapshot holds the number and unit separately, so nothing has to
    be parsed back out of `"108.84 %"`.
    """
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    ph = await seed_test(db_session, code="TST-B", name="pH")
    await seed_spec(
        db_session, product,
        [(assay.id, 95.0, 105.0, None, True), (ph.id, 4.0, 7.0, None, True)],
    )
    trf = await seed_released_trf(
        db_session, product,
        [(assay.id, "95.0 to 105.0 %", "108.84 %"), (ph.id, "4.0 to 7.0", "5.2")],
    )

    template = TestTemplateModel(
        code="TPL-A1-0001", name="Assay by HPLC", archetype="A1", test_id=assay.id,
        version=3, status="Active", result_unit="%", definition={},
        created_by="admin", modified_by="admin",
    )
    db_session.add(template)
    await db_session.flush()

    assay_line = await line_for(db_session, trf, assay.id)
    db_session.add(
        TestWorksheetModel(
            trf_test_line_id=assay_line.id,
            template_id=template.id,
            template_version=3,
            status="Confirmed",
            context_values={},
            group_values={},
            computed_snapshot={
                "template": {
                    "id": template.id, "code": "TPL-A1-0001", "name": "Assay by HPLC",
                    "archetype": "A1", "version": 3, "result_unit": "%",
                },
                "reportable_result": 108.84,
            },
            reportable_result="108.84 %",
            confirmed_by="analyst",
            confirmed_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
            created_by="analyst", modified_by="analyst",
        )
    )
    await db_session.flush()

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())
    rows = {t["test_code"]: t for t in coa.snapshot["tests"]}

    worksheet_row = rows["TST-A"]
    assert worksheet_row["source"] == "Worksheet"
    assert worksheet_row["numeric_result"] == 108.84
    assert worksheet_row["unit"] == "%"
    assert worksheet_row["template_code"] == "TPL-A1-0001"
    #  Records the version that produced the number, not the template's latest.
    assert worksheet_row["template_version"] == 3
    #  108.84 is outside 95–105.
    assert worksheet_row["verdict"] == Verdict.FAIL.value

    free_text_row = rows["TST-B"]
    assert free_text_row["source"] == "FreeText"
    assert free_text_row["template_code"] is None
    assert free_text_row["verdict"] == Verdict.PASS.value


@pytest.mark.asyncio
async def test_an_unconfirmed_worksheet_falls_back_to_the_free_text_result(db_session):
    """
    An in-progress worksheet has no trustworthy snapshot, so the certificate uses
    whatever the test line carries rather than a half-finished computation.
    """
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_spec(db_session, product, [(assay.id, 95.0, 105.0, None, True)])
    trf = await seed_released_trf(db_session, product, [(assay.id, "spec", "99.0 %")])

    template = TestTemplateModel(
        code="TPL-A1-0001", name="Assay", archetype="A1", test_id=assay.id,
        version=1, status="Active", result_unit="%", definition={},
        created_by="admin", modified_by="admin",
    )
    db_session.add(template)
    await db_session.flush()
    assay_line = await line_for(db_session, trf, assay.id)
    db_session.add(
        TestWorksheetModel(
            trf_test_line_id=assay_line.id,
            template_id=template.id, template_version=1,
            status="InProgress", context_values={}, group_values={},
            computed_snapshot=None,
            created_by="analyst", modified_by="analyst",
        )
    )
    await db_session.flush()

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())
    row = coa.snapshot["tests"][0]
    assert row["source"] == "FreeText"
    assert row["numeric_result"] == 99.0
    assert row["verdict"] == Verdict.PASS.value


# ── Compilation rules ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_test_excluded_from_the_coa_is_omitted(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    internal = await seed_test(db_session, code="TST-X", name="Internal check")
    await seed_spec(
        db_session, product,
        [(assay.id, 95.0, 105.0, None, True), (internal.id, 0.0, 1.0, None, False)],
    )
    await seed_released_trf(
        db_session, product, [(assay.id, "spec", "99.8 %"), (internal.id, "spec", "0.5")]
    )

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())
    assert [t["test_code"] for t in coa.snapshot["tests"]] == ["TST-A"]


@pytest.mark.asyncio
async def test_a_retest_supersedes_the_earlier_release(db_session):
    """
    A batch retested under a second TRF must appear once, showing the later
    result. Listing the same test twice with different numbers would make the
    certificate unreadable.
    """
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_spec(db_session, product, [(assay.id, 95.0, 105.0, None, True)])

    await seed_released_trf(
        db_session, product, [(assay.id, "spec", "110.0 %")],
        trf_number="TRF-20260806-0001", ar_number="AR-1",
        released_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )
    await seed_released_trf(
        db_session, product, [(assay.id, "spec", "99.8 %")],
        trf_number="TRF-20260807-0002", ar_number="AR-2",
        released_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
    )

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())

    assert len(coa.snapshot["tests"]) == 1
    row = coa.snapshot["tests"][0]
    assert row["result_text"] == "99.8 %"
    assert row["trf_number"] == "TRF-20260807-0002"
    assert coa.overall_verdict == Verdict.PASS.value
    #  Both TRFs are still referenced, so the retest is traceable.
    assert coa.snapshot["references"]["trf_numbers"] == [
        "TRF-20260806-0001", "TRF-20260807-0002",
    ]
    assert len(coa.snapshot["signatures"]) == 2


@pytest.mark.asyncio
async def test_tests_are_ordered_by_the_specification(db_session):
    product = await seed_product(db_session)
    a = await seed_test(db_session, code="TST-A", name="Assay")
    b = await seed_test(db_session, code="TST-B", name="pH")
    c = await seed_test(db_session, code="TST-C", name="Water")
    #  Specification order deliberately differs from insertion order.
    await seed_spec(
        db_session, product,
        [(c.id, None, 5.0, None, True), (a.id, 95.0, 105.0, None, True),
         (b.id, 4.0, 7.0, None, True)],
    )
    await seed_released_trf(
        db_session, product,
        [(a.id, "s", "99.8"), (b.id, "s", "5.2"), (c.id, "s", "2.0")],
    )

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())
    assert [t["test_code"] for t in coa.snapshot["tests"]] == ["TST-C", "TST-A", "TST-B"]


@pytest.mark.asyncio
async def test_a_test_with_no_specification_entry_is_still_reported(db_session):
    """
    Better to show the result with an honest NotEvaluated than to hide a test that
    was performed and released.
    """
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    orphan = await seed_test(db_session, code="TST-Z", name="Unspecified test")
    await seed_spec(db_session, product, [(assay.id, 95.0, 105.0, None, True)])
    await seed_released_trf(
        db_session, product,
        [(assay.id, "spec", "99.8 %"), (orphan.id, "As per method", "42.0")],
    )

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())
    rows = {t["test_code"]: t for t in coa.snapshot["tests"]}

    assert rows["TST-Z"]["verdict"] == Verdict.NOT_EVALUATED.value
    #  Falls back to the TRF line's own specification text.
    assert rows["TST-Z"]["specification_text"] == "As per method"
    assert coa.overall_verdict == Verdict.PASS.value


@pytest.mark.asyncio
async def test_a_line_released_without_a_result_is_omitted(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    pending = await seed_test(db_session, code="TST-B", name="pH")
    await seed_spec(
        db_session, product,
        [(assay.id, 95.0, 105.0, None, True), (pending.id, 4.0, 7.0, None, True)],
    )
    await seed_released_trf(
        db_session, product, [(assay.id, "spec", "99.8 %"), (pending.id, "spec", None)]
    )

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())
    #  Printing an empty row would imply the test was reported.
    assert [t["test_code"] for t in coa.snapshot["tests"]] == ["TST-A"]


@pytest.mark.asyncio
async def test_no_active_specification_still_produces_a_certificate(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_released_trf(db_session, product, [(assay.id, "As per method", "99.8 %")])

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())
    assert coa.snapshot["specification"] is None
    #  Nothing to compare against, so no verdict can be claimed.
    assert coa.snapshot["tests"][0]["verdict"] == Verdict.NOT_EVALUATED.value
    assert coa.overall_verdict == Verdict.NOT_EVALUATED.value


@pytest.mark.asyncio
async def test_a_pending_specification_is_not_used(db_session):
    """Only an Active specification defines limits; a draft must not silently apply."""
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_spec(
        db_session, product, [(assay.id, 95.0, 105.0, None, True)], status="Pending Approval"
    )
    await seed_released_trf(db_session, product, [(assay.id, "spec", "99.8 %")])

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())
    assert coa.snapshot["specification"] is None
    assert coa.snapshot["tests"][0]["verdict"] == Verdict.NOT_EVALUATED.value


# ── Rejection paths ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_batch_with_no_released_trfs_is_rejected(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    #  An in-progress TRF is not evidence of anything.
    trf = await seed_released_trf(db_session, product, [(assay.id, "spec", "99.8 %")])
    trf.status = "InProgress"
    await db_session.flush()

    with pytest.raises(ValidationException) as exc:
        await _service(db_session).generate(product.id, BATCH, qa_user())
    assert "No released Test Request Forms" in str(exc.value)


@pytest.mark.asyncio
async def test_a_different_batch_is_not_compiled(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_released_trf(db_session, product, [(assay.id, "spec", "99.8 %")], batch="OTHER")

    with pytest.raises(ValidationException):
        await _service(db_session).generate(product.id, BATCH, qa_user())


@pytest.mark.asyncio
async def test_unknown_product_is_a_404(db_session):
    with pytest.raises(NotFoundException):
        await _service(db_session).generate(9999, BATCH, qa_user())


@pytest.mark.asyncio
async def test_a_blank_batch_number_is_rejected(db_session):
    product = await seed_product(db_session)
    with pytest.raises(ValidationException) as exc:
        await _service(db_session).generate(product.id, "   ", qa_user())
    assert "batch number is required" in str(exc.value)


@pytest.mark.parametrize("role", ["Analyst", "Supervisor"])
@pytest.mark.asyncio
async def test_only_qa_or_admin_may_issue(db_session, role):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_released_trf(db_session, product, [(assay.id, "spec", "99.8 %")])

    svc = _service(db_session)
    with pytest.raises(ForbiddenException):
        await svc.generate(product.id, BATCH, user("someone", role, user_id=8))
    assert await svc.list_coas() == []


# ── Preview ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_compiles_without_issuing(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_spec(db_session, product, [(assay.id, 95.0, 105.0, None, True)])
    await seed_released_trf(db_session, product, [(assay.id, "spec", "110.5 %")])

    svc = _service(db_session)
    snapshot = await svc.preview(product.id, BATCH)

    #  The failure is visible before a signature is committed to it.
    assert snapshot["overall_verdict"] == Verdict.FAIL.value
    #  No number and no issuer — that is how a caller tells a preview from a COA.
    assert snapshot["coa_number"] is None
    assert snapshot["issued_by"] is None
    assert await svc.list_coas() == []

    audit = await AuditLogRepositoryImpl(db_session).list_recent(limit=20)
    assert [e.action for e in audit].count("COA_GENERATED") == 0


# ── Property 16: the snapshot is immutable ───────────────────────────


@pytest.mark.asyncio
async def test_the_snapshot_survives_later_master_data_changes(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    spec = await seed_spec(db_session, product, [(assay.id, 95.0, 105.0, None, True)])
    await seed_released_trf(db_session, product, [(assay.id, "spec", "99.8 %")])

    svc = _service(db_session)
    coa = await svc.generate(product.id, BATCH, qa_user())
    issued = coa.snapshot

    #  Rewrite everything the certificate drew on: rename the product, tighten the
    #  limits so 99.8 would now fail, and retire the specification.
    product.name = "Renamed Product"
    product.code = "PRD-CHANGED"
    spec.status = "Inactive"
    spec.document_no = "SPEC-999"

    limits = (
        await db_session.execute(
            select(SpecificationTestModel).where(
                SpecificationTestModel.specification_id == spec.id
            )
        )
    ).scalar_one()
    limits.min_limit = 100.0
    limits.max_limit = 110.0
    await db_session.flush()

    reloaded = await svc.get(coa.id)

    assert reloaded.snapshot == issued
    assert reloaded.snapshot["product"]["name"] == "Paracetamol Tablets"
    assert reloaded.snapshot["product"]["code"] == "PRD-1"
    assert reloaded.snapshot["specification"]["document_no"] == "SPEC-001"
    #  Still a Pass against the limits that were in force at issue.
    assert reloaded.snapshot["tests"][0]["verdict"] == Verdict.PASS.value
    assert reloaded.snapshot["tests"][0]["min_limit"] == 95.0
    assert reloaded.overall_verdict == Verdict.PASS.value


@pytest.mark.asyncio
async def test_the_repository_offers_no_way_to_change_a_certificate(db_session):
    """
    Immutability is structural, not a rule someone has to remember: there is no
    `update` and no `delete` on the port or the implementation.
    """
    repo = COARepositoryImpl(db_session)
    assert not hasattr(repo, "update")
    assert not hasattr(repo, "delete")


@pytest.mark.asyncio
async def test_re_certifying_a_batch_creates_a_second_certificate(db_session):
    """A correction is a new certificate that supersedes the old, never an edit."""
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_spec(db_session, product, [(assay.id, 95.0, 105.0, None, True)])
    await seed_released_trf(db_session, product, [(assay.id, "spec", "99.8 %")])

    svc = _service(db_session)
    first = await svc.generate(product.id, BATCH, qa_user())
    second = await svc.generate(product.id, BATCH, qa_user())

    assert first.coa_number != second.coa_number
    #  Newest first, so the current certificate is at the top.
    listed = await svc.list_coas(product_id=product.id, batch_number=BATCH)
    assert [c.id for c in listed] == [second.id, first.id]


# ── Numbering & audit ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_coa_numbers_are_sequential_within_a_day(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_released_trf(db_session, product, [(assay.id, "spec", "99.8 %")])

    svc = _service(db_session)
    first = await svc.generate(product.id, BATCH, qa_user())
    second = await svc.generate(product.id, BATCH, qa_user())

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    assert first.coa_number == f"COA-{stamp}-0001"
    assert second.coa_number == f"COA-{stamp}-0002"


@pytest.mark.asyncio
async def test_generation_writes_one_audit_entry(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    spec = await seed_spec(db_session, product, [(assay.id, 95.0, 105.0, None, True)])
    await seed_released_trf(db_session, product, [(assay.id, "spec", "99.8 %")])

    coa = await _service(db_session).generate(product.id, BATCH, qa_user())

    entries = await AuditLogRepositoryImpl(db_session).list_recent(limit=20)
    matching = [e for e in entries if e.action == "COA_GENERATED"]
    assert len(matching) == 1

    entry = matching[0]
    assert entry.username == QA
    assert entry.record_id == coa.id
    assert entry.new_values["coa_number"] == coa.coa_number
    assert entry.new_values["overall_verdict"] == Verdict.PASS.value
    assert entry.new_values["source_trf_numbers"] == ["TRF-20260806-0001"]
    #  Which specification version was applied is part of the release evidence.
    assert entry.new_values["specification_version"] == spec.version


@pytest.mark.asyncio
async def test_a_rejected_generation_writes_no_audit_entry(db_session):
    product = await seed_product(db_session)
    with pytest.raises(ValidationException):
        await _service(db_session).generate(product.id, "NO-SUCH-BATCH", qa_user())

    entries = await AuditLogRepositoryImpl(db_session).list_recent(limit=20)
    assert [e.action for e in entries].count("COA_GENERATED") == 0


@pytest.mark.asyncio
async def test_list_filters_by_product_and_batch(db_session):
    product_a = await seed_product(db_session, code="PRD-A", name="Product A")
    product_b = await seed_product(db_session, code="PRD-B", name="Product B")
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_released_trf(
        db_session, product_a, [(assay.id, "spec", "99.8 %")],
        trf_number="TRF-A", ar_number="AR-A", batch="BATCH-A",
    )
    await seed_released_trf(
        db_session, product_b, [(assay.id, "spec", "99.8 %")],
        trf_number="TRF-B", ar_number="AR-B", batch="BATCH-B",
    )

    svc = _service(db_session)
    coa_a = await svc.generate(product_a.id, "BATCH-A", qa_user())
    coa_b = await svc.generate(product_b.id, "BATCH-B", qa_user())

    assert [c.id for c in await svc.list_coas()] == [coa_b.id, coa_a.id]
    assert [c.id for c in await svc.list_coas(product_id=product_a.id)] == [coa_a.id]
    assert [c.id for c in await svc.list_coas(batch_number="BATCH-B")] == [coa_b.id]
    assert await svc.list_coas(batch_number="NOPE") == []


@pytest.mark.asyncio
async def test_unknown_coa_is_a_404(db_session):
    with pytest.raises(NotFoundException):
        await _service(db_session).get(9999)


@pytest.mark.asyncio
async def test_coa_number_is_uniquely_constrained(db_session):
    """The number is a document identifier; a duplicate would be a real problem."""
    product = await seed_product(db_session)
    db_session.add(
        CertificateOfAnalysisModel(
            coa_number="COA-20260806-0001", product_id=product.id, batch_number=BATCH,
            status="Released", snapshot={}, released_by=QA,
            created_by=QA, modified_by=QA,
        )
    )
    await db_session.flush()

    db_session.add(
        CertificateOfAnalysisModel(
            coa_number="COA-20260806-0001", product_id=product.id, batch_number="OTHER",
            status="Released", snapshot={}, released_by=QA,
            created_by=QA, modified_by=QA,
        )
    )
    with pytest.raises(Exception):
        await db_session.flush()
