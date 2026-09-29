"""
Specification-unit comparability.

Closes a real defect: a COA compared an assay of 108.84 % against limits of 9 to
11 and reported Fail. The limits were mg/mL, the result was a percentage, and
nothing in the system could tell — `SpecificationTest` carried bare floats.

Two defences, tested here:

* **At worksheet-attach time**, a template whose `result_unit` definitely
  disagrees with the active specification's limit unit is refused. That is one
  dialog for the analyst instead of a released result nothing can judge.
* **At certificate time**, a definite mismatch yields `NotEvaluated` with a stated
  reason — never Pass, and never Fail. Neither would be an honest answer to a
  meaningless comparison.

Unknown units stay permitted throughout, because most existing specifications have
none and refusing them all would block certificates that are fine.
"""
import pytest

from src.application.exceptions.application_exceptions import ValidationException
from src.application.services.worksheet_service import WorksheetService
from src.domain.entities.certificate_of_analysis import Verdict, evaluate_result
from src.domain.entities.specification import normalise_unit, units_comparable
from src.infrastructure.database.models.test_template_model import TestTemplateModel
from src.infrastructure.database.repositories.audit_repository_impl import (
    AuditLogRepositoryImpl,
)
from src.infrastructure.database.repositories.product_repository_impl import (
    ProductRepositoryImpl,
)
from src.infrastructure.database.repositories.specification_repository_impl import (
    SpecificationRepositoryImpl,
)
from src.infrastructure.database.repositories.test_template_repository_impl import (
    TestTemplateRepositoryImpl,
    TestWorksheetRepositoryImpl,
)
from src.infrastructure.database.repositories.trf_repository_impl import TRFRepositoryImpl
from tests.calculation.conftest import seed_test, seed_trf_with_line, user
from tests.calculation.test_coa_service import (
    BATCH,
    _service as coa_service,
    line_for,
    qa_user,
    seed_product,
    seed_released_trf,
    seed_spec,
)

ANALYST = "analyst"


# ── Unit normalisation ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("%", "%"),
        (" % ", "%"),
        ("mg/mL", "mg/ml"),
        ("MG/ML", "mg/ml"),
        ("mg / mL", "mg/ml"),
        #  Three spellings of the same unit.
        ("ug/mL", "µg/ml"),
        ("mcg/mL", "µg/ml"),
        ("µg/mL", "µg/ml"),
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_unit_normalisation(raw, expected):
    assert normalise_unit(raw) == expected


@pytest.mark.parametrize(
    "left, right, comparable",
    [
        ("%", "%", True),
        ("mg/mL", "MG/ML", True),
        ("ug/mL", "mcg/mL", True),
        #  Unknown on either side is permitted — most specs carry no unit.
        (None, "%", True),
        ("%", None, True),
        (None, None, True),
        #  The case that caused the bug.
        ("%", "mg/mL", False),
        ("ppm", "%", False),
        #  Deliberately NOT comparable: treating these as compatible would mean
        #  choosing a scale factor, and silently rescaling a GxP result is worse
        #  than refusing to judge it.
        ("mg", "g", False),
        ("%", "ppm", False),
    ],
)
def test_unit_comparability(left, right, comparable):
    assert units_comparable(left, right) is comparable


# ── Verdict refuses a meaningless comparison ─────────────────────────


def test_a_definite_unit_mismatch_is_not_evaluated_rather_than_failed():
    """The exact case observed: 108.84 % against limits of 9 to 11 mg/mL."""
    verdict, reason = evaluate_result(108.84, 9.0, 11.0, "%", "mg/mL")
    assert verdict == Verdict.NOT_EVALUATED.value
    assert "not comparable" in reason
    #  Emphatically not a Fail — the batch may be perfectly good.
    assert verdict != Verdict.FAIL.value


def test_matching_units_still_evaluate_normally():
    assert evaluate_result(99.5, 95.0, 105.0, "%", "%") == (Verdict.PASS.value, None)
    assert evaluate_result(110.0, 95.0, 105.0, "%", "%") == (Verdict.FAIL.value, None)


def test_an_absent_limit_unit_does_not_block_evaluation():
    """Backward compatibility: existing specifications have no unit recorded."""
    assert evaluate_result(99.5, 95.0, 105.0, "%", None) == (Verdict.PASS.value, None)


@pytest.mark.parametrize(
    "value, lo, hi, expected_reason_fragment",
    [
        (None, 95.0, 105.0, "No numeric result"),
        (99.5, None, None, "No numeric specification limits"),
    ],
)
def test_other_not_evaluated_cases_state_their_reason(
    value, lo, hi, expected_reason_fragment
):
    verdict, reason = evaluate_result(value, lo, hi, "%", "%")
    assert verdict == Verdict.NOT_EVALUATED.value
    assert expected_reason_fragment in reason


# ── Certificate behaviour ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_certificate_reports_a_mismatch_instead_of_a_false_fail(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    #  Limits in mg/mL, result reported as a percentage.
    await seed_spec(db_session, product, [(assay.id, 9.0, 11.0, None, True)])
    spec = await SpecificationRepositoryImpl(db_session).get_active_for_product(product.id)
    from sqlalchemy import select

    from src.infrastructure.database.models.specification_model import (
        SpecificationTestModel,
    )

    limits = (
        await db_session.execute(
            select(SpecificationTestModel).where(
                SpecificationTestModel.specification_id == spec.id
            )
        )
    ).scalar_one()
    limits.unit = "mg/mL"
    await db_session.flush()

    trf = await seed_released_trf(db_session, product, [(assay.id, "9 to 11", "108.84 %")])
    line = await line_for(db_session, trf, assay.id)

    template = TestTemplateModel(
        code="TPL-A1-0001", name="Assay by HPLC", archetype="A1", test_id=assay.id,
        version=1, status="Active", result_unit="%", definition={},
        created_by="admin", modified_by="admin",
    )
    db_session.add(template)
    await db_session.flush()

    from datetime import datetime, timezone

    from src.infrastructure.database.models.test_template_model import TestWorksheetModel

    db_session.add(
        TestWorksheetModel(
            trf_test_line_id=line.id, template_id=template.id, template_version=1,
            status="Confirmed", context_values={}, group_values={},
            computed_snapshot={
                "template": {"id": template.id, "code": "TPL-A1-0001", "name": "Assay",
                             "archetype": "A1", "version": 1, "result_unit": "%"},
                "reportable_result": 108.84,
            },
            reportable_result="108.84 %", confirmed_by="analyst",
            confirmed_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
            created_by="analyst", modified_by="analyst",
        )
    )
    await db_session.flush()

    coa = await coa_service(db_session).generate(product.id, BATCH, qa_user())
    row = coa.snapshot["tests"][0]

    assert row["unit"] == "%"
    assert row["limit_unit"] == "mg/mL"
    #  The whole point: NOT a Fail.
    assert row["verdict"] == Verdict.NOT_EVALUATED.value
    assert "not comparable" in row["not_evaluated_reason"]
    assert coa.overall_verdict == Verdict.NOT_EVALUATED.value


@pytest.mark.asyncio
async def test_matching_units_produce_a_normal_verdict_on_the_certificate(db_session):
    product = await seed_product(db_session)
    assay = await seed_test(db_session, code="TST-A", name="Assay")
    await seed_spec(db_session, product, [(assay.id, 95.0, 105.0, None, True)])
    await seed_released_trf(db_session, product, [(assay.id, "95 to 105", "99.8 %")])

    coa = await coa_service(db_session).generate(product.id, BATCH, qa_user())
    row = coa.snapshot["tests"][0]
    assert row["verdict"] == Verdict.PASS.value
    assert row["not_evaluated_reason"] is None


# ── Attach-time refusal ──────────────────────────────────────────────


def _worksheet_service(session) -> WorksheetService:
    return WorksheetService(
        TestWorksheetRepositoryImpl(session),
        TestTemplateRepositoryImpl(session),
        TRFRepositoryImpl(session),
        ProductRepositoryImpl(session),
        AuditLogRepositoryImpl(session),
        SpecificationRepositoryImpl(session),
    )


async def _attach_scenario(db_session, *, spec_unit: str | None, template_unit: str | None):
    test = await seed_test(db_session, code="TST-A", name="Assay")
    trf, line = await seed_trf_with_line(db_session, status="InProgress", test=test)
    trf.analyst_accepted_by = ANALYST
    await db_session.flush()

    product_id = trf.product_id
    spec = None
    if spec_unit is not None:
        from sqlalchemy import select

        from src.infrastructure.database.models.specification_model import (
            SpecificationModel,
            SpecificationTestModel,
        )

        spec = SpecificationModel(
            product_id=product_id, version=1, status="Active", document_no="SPEC-1",
            created_by="qa", modified_by="qa",
        )
        db_session.add(spec)
        await db_session.flush()
        db_session.add(
            SpecificationTestModel(
                specification_id=spec.id, test_id=test.id,
                min_limit=95.0, max_limit=105.0, unit=spec_unit, display_in_coa=True,
            )
        )
        await db_session.flush()

    template = TestTemplateModel(
        code="TPL-A1-0001", name="Assay by HPLC", archetype="A1", test_id=test.id,
        version=1, status="Active", result_unit=template_unit,
        definition={
            "resultRef": "s.r",
            "groups": [{"key": "s", "kind": "singleton", "fields": [
                {"key": "a", "kind": "area"},
                {"key": "r", "kind": "calculated", "expression": "a"},
            ]}],
        },
        created_by="admin", modified_by="admin",
    )
    db_session.add(template)
    await db_session.flush()
    return line, template


@pytest.mark.asyncio
async def test_attaching_a_template_with_a_mismatched_unit_is_refused(db_session):
    line, template = await _attach_scenario(
        db_session, spec_unit="mg/mL", template_unit="%"
    )
    svc = _worksheet_service(db_session)

    with pytest.raises(ValidationException) as exc:
        await svc.create_worksheet(line.id, template.id, user(ANALYST, "Analyst"))

    message = str(exc.value)
    assert "'%'" in message and "'mg/mL'" in message
    #  Actionable: it says what to do, not merely that something is wrong.
    assert "Correct the specification unit" in message
    #  And nothing was created.
    assert await svc.get_worksheet_for_line(line.id) is None


@pytest.mark.parametrize(
    "spec_unit, template_unit",
    [
        ("%", "%"),
        ("MG/ML", "mg/mL"),
        #  No specification unit recorded — the common existing case.
        (None, "%"),
        #  Template with no declared unit.
        ("%", None),
    ],
)
@pytest.mark.asyncio
async def test_comparable_or_unknown_units_attach_normally(
    db_session, spec_unit, template_unit
):
    line, template = await _attach_scenario(
        db_session, spec_unit=spec_unit, template_unit=template_unit
    )
    svc = _worksheet_service(db_session)

    worksheet = await svc.create_worksheet(line.id, template.id, user(ANALYST, "Analyst"))
    assert worksheet.id > 0


@pytest.mark.asyncio
async def test_the_check_is_skipped_when_no_specification_repo_is_wired(db_session):
    """
    The dependency is optional so existing constructions keep working. Without it
    the check is skipped rather than the service refusing to build.
    """
    line, template = await _attach_scenario(
        db_session, spec_unit="mg/mL", template_unit="%"
    )
    svc = WorksheetService(
        TestWorksheetRepositoryImpl(db_session),
        TestTemplateRepositoryImpl(db_session),
        TRFRepositoryImpl(db_session),
        ProductRepositoryImpl(db_session),
        AuditLogRepositoryImpl(db_session),
    )
    worksheet = await svc.create_worksheet(line.id, template.id, user(ANALYST, "Analyst"))
    assert worksheet.id > 0
