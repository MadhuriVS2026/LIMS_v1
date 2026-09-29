"""
WorksheetService tests.

Covers the four worksheet properties:

  * **Property 11** — blocking criteria gate result confirmation
  * **Property 12** — worksheet mutation respects TRF status and role
  * **Property 13** — the confirmed result reaches the test line unchanged
  * **Property 14** — area source is always recorded

Every expected number below is hand-derived from the template's own formula
rather than copied from a previous run, which is what makes these tests able to
catch an engine regression rather than just pin current behaviour.

The template used is a deliberately small stand-in for archetype A1: two
standard-area rows and one sample, assay = sample area / mean standard area
× 100, rounded to 2dp, with a %RSD system-suitability criterion.
"""
import pytest

from src.application.exceptions.application_exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.application.services.worksheet_service import WorksheetService
from src.domain.entities.test_template import WorksheetStatus
from src.infrastructure.database.repositories.audit_repository_impl import (
    AuditLogRepositoryImpl,
)
from src.infrastructure.database.repositories.product_repository_impl import (
    ProductRepositoryImpl,
)
from src.infrastructure.database.repositories.test_template_repository_impl import (
    TestTemplateRepositoryImpl,
    TestWorksheetRepositoryImpl,
)
from src.infrastructure.database.repositories.trf_repository_impl import TRFRepositoryImpl
from src.infrastructure.database.models.test_template_model import TestTemplateModel
from tests.calculation.conftest import seed_test, seed_trf_with_line, set_trf_status, user

DEFINITION = {
    "resultRef": "sample.assay",
    "context": [
        {"key": "batch", "kind": "context", "type": "text", "source": "trf.batch_number"},
        {"key": "product", "kind": "context", "type": "text", "source": "product.name"},
        {"key": "analyst", "kind": "context", "type": "text", "source": "session.analyst"},
        {
            "key": "std_wt",
            "kind": "context",
            "type": "number",
            "default": 100,
            "overridable": True,
        },
    ],
    "groups": [
        {
            "key": "std",
            "kind": "table",
            "label": "Standard injections",
            "rows": {"min": 1, "max": 6, "default": 2},
            "fields": [{"key": "area", "kind": "area", "label": "Area"}],
        },
        {
            "key": "sample",
            "kind": "singleton",
            "label": "Sample",
            "fields": [
                {"key": "area", "kind": "area", "label": "Area"},
                {
                    "key": "assay",
                    "kind": "calculated",
                    "label": "Assay",
                    "expression": "area / mean(std.area) * 100",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
    ],
    "criteria": [
        {
            "key": "std_rsd",
            "label": "Standard area %RSD",
            "target": "rsd(std.area)",
            "operator": "lte",
            "limit": 2.0,
            "limitText": "NMT 2.0%",
            "severity": "blocking",
        }
    ],
}

#  Two standards 1000 apart on a 100000 mean → %RSD well inside 2.0%.
GOOD_STD = [{"area": 100500}, {"area": 99500}]
#  30% apart → %RSD ≈ 24.6%, far outside the limit.
BAD_STD = [{"area": 115000}, {"area": 85000}]

ANALYST = "analyst"


def _service(session) -> WorksheetService:
    return WorksheetService(
        TestWorksheetRepositoryImpl(session),
        TestTemplateRepositoryImpl(session),
        TRFRepositoryImpl(session),
        ProductRepositoryImpl(session),
        AuditLogRepositoryImpl(session),
    )


async def _seed_active_template(
    session, test_id: int, definition: dict | None = None, status: str = "Active"
) -> TestTemplateModel:
    """
    Insert the template directly rather than driving TestTemplateService.

    These tests are about worksheets; going through the authoring lifecycle here
    would couple them to a service they are not exercising.
    """
    model = TestTemplateModel(
        code="TPL-A1-0001",
        name="Assay by HPLC",
        archetype="A1",
        test_id=test_id,
        version=1,
        status=status,
        result_unit="%",
        definition=definition or DEFINITION,
        created_by="admin",
        modified_by="admin",
    )
    session.add(model)
    await session.flush()
    return model


async def _worksheet_in_progress(session, trf_status: str = "InProgress"):
    """A TRF at `trf_status` with an Active template attached to its one line."""
    test = await seed_test(session)
    trf, line = await seed_trf_with_line(session, status="InProgress", test=test)
    trf.analyst_accepted_by = ANALYST
    await session.flush()

    template = await _seed_active_template(session, test.id)
    svc = _service(session)
    worksheet = await svc.create_worksheet(line.id, template.id, user(ANALYST, "Analyst"))

    if trf_status != "InProgress":
        await set_trf_status(session, trf, trf_status)
    return svc, worksheet, line, trf, template


# ── Creation ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_worksheet_binds_the_template_version_and_seeds_context(db_session):
    svc, worksheet, line, trf, template = await _worksheet_in_progress(db_session)

    assert worksheet.trf_test_line_id == line.id
    assert worksheet.template_id == template.id
    assert worksheet.template_version == 1
    assert worksheet.status == WorksheetStatus.IN_PROGRESS.value
    assert worksheet.template_code == "TPL-A1-0001"

    #  Context resolved from the TRF header, the product and the session — not
    #  left blank for the analyst to retype.
    assert worksheet.context_values["batch"] == trf.batch_number
    assert worksheet.context_values["product"] == "Paracetamol Tablets"
    assert worksheet.context_values["analyst"] == ANALYST
    #  A context field with no source falls back to its declared default.
    assert worksheet.context_values["std_wt"] == 100


@pytest.mark.asyncio
async def test_one_worksheet_per_test_line(db_session):
    svc, worksheet, line, _trf, template = await _worksheet_in_progress(db_session)

    with pytest.raises(ValidationException) as exc:
        await svc.create_worksheet(line.id, template.id, user(ANALYST, "Analyst"))
    assert "already has a worksheet" in str(exc.value)


@pytest.mark.asyncio
async def test_only_an_active_template_can_be_attached(db_session):
    test = await seed_test(db_session)
    trf, line = await seed_trf_with_line(db_session, status="InProgress", test=test)
    trf.analyst_accepted_by = ANALYST
    await db_session.flush()

    draft = await _seed_active_template(db_session, test.id, status="Draft")
    svc = _service(db_session)

    with pytest.raises(ValidationException) as exc:
        await svc.create_worksheet(line.id, draft.id, user(ANALYST, "Analyst"))
    assert "Active" in str(exc.value)
    assert await svc.get_worksheet_for_line(line.id) is None


@pytest.mark.asyncio
async def test_template_must_be_defined_for_this_line_s_test(db_session):
    test = await seed_test(db_session)
    other_test = await seed_test(db_session, code="TST-02", name="Dissolution")
    trf, line = await seed_trf_with_line(db_session, status="InProgress", test=test)
    trf.analyst_accepted_by = ANALYST
    await db_session.flush()

    mismatched = await _seed_active_template(db_session, other_test.id)
    svc = _service(db_session)

    with pytest.raises(ValidationException) as exc:
        await svc.create_worksheet(line.id, mismatched.id, user(ANALYST, "Analyst"))
    assert "different test" in str(exc.value)


@pytest.mark.asyncio
async def test_unknown_line_or_template_is_a_404(db_session):
    test = await seed_test(db_session)
    trf, line = await seed_trf_with_line(db_session, status="InProgress", test=test)
    trf.analyst_accepted_by = ANALYST
    await db_session.flush()
    svc = _service(db_session)

    with pytest.raises(NotFoundException):
        await svc.create_worksheet(9999, 1, user(ANALYST, "Analyst"))
    with pytest.raises(NotFoundException):
        await svc.create_worksheet(line.id, 9999, user(ANALYST, "Analyst"))


# ── Preview does not persist ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_computes_without_persisting(db_session):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)

    _, _, result = await svc.preview(
        worksheet.id,
        group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]},
    )

    #  mean(100500, 99500) = 100000; 101000 / 100000 * 100 = 101.0
    assert result.values["sample.assay"] == pytest.approx(101.0)

    reloaded = await svc.get_worksheet(worksheet.id)
    assert reloaded.group_values == {}
    assert reloaded.computed_snapshot is None

    audit = await AuditLogRepositoryImpl(db_session).list_recent(limit=50)
    assert [e.action for e in audit].count("WORKSHEET_VALUES_SAVED") == 0


# ── Property 12: mutation respects TRF status and role ───────────────


@pytest.mark.parametrize(
    "trf_status",
    ["Draft", "PendingFDGLApproval", "PendingADGLAcceptance", "PendingAnalystAcceptance",
     "Released", "ReferredBack", "Rejected"],
)
@pytest.mark.asyncio
async def test_values_cannot_be_saved_outside_the_permitted_statuses(db_session, trf_status):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session, trf_status)
    before = (await svc.get_worksheet(worksheet.id)).group_values

    with pytest.raises(ValidationException):
        await svc.save_values(
            worksheet.id,
            user(ANALYST, "Analyst"),
            group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]},
        )

    #  A rejected mutation is a genuine no-op.
    assert (await svc.get_worksheet(worksheet.id)).group_values == before


@pytest.mark.parametrize("role", ["Supervisor", "QA"])
@pytest.mark.asyncio
async def test_entry_is_analyst_only_while_in_progress(db_session, role):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)

    with pytest.raises(ForbiddenException):
        await svc.save_values(
            worksheet.id, user("someone", role, user_id=7), group_values={"std": GOOD_STD}
        )
    assert (await svc.get_worksheet(worksheet.id)).group_values == {}


@pytest.mark.parametrize("role", ["Analyst", "Supervisor"])
@pytest.mark.asyncio
async def test_correction_is_qa_only_while_pending_release(db_session, role):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(
        db_session, "PendingADGLRelease"
    )

    with pytest.raises(ForbiddenException):
        await svc.save_values(
            worksheet.id,
            user("someone", role, user_id=7),
            group_values={"std": GOOD_STD},
            reason="fix",
        )


@pytest.mark.asyncio
async def test_a_different_analyst_cannot_enter_results_on_an_assigned_trf(db_session):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)

    with pytest.raises(ForbiddenException) as exc:
        await svc.save_values(
            worksheet.id, user("other_analyst", "Analyst", user_id=9), group_values={"std": GOOD_STD}
        )
    assert "assigned to this TRF" in str(exc.value)

    #  Admin overrides the assignment.
    saved, _, _ = await svc.save_values(
        worksheet.id, user("admin", "Admin", user_id=2), group_values={"std": GOOD_STD}
    )
    assert saved.group_values["std"] == GOOD_STD


@pytest.mark.asyncio
async def test_correction_requires_a_reason(db_session):
    svc, worksheet, _line, trf, _template = await _worksheet_in_progress(db_session)
    await svc.save_values(
        worksheet.id,
        user(ANALYST, "Analyst"),
        group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]},
    )
    await set_trf_status(db_session, trf, "PendingADGLRelease")
    qa = user("qa1", "QA", user_id=3)

    with pytest.raises(ValidationException) as exc:
        await svc.save_values(
            worksheet.id, qa, group_values={"sample": [{"area": 102_000}]}, reason="  "
        )
    assert "reason is required" in str(exc.value)

    corrected, _, result = await svc.save_values(
        worksheet.id,
        qa,
        group_values={"std": GOOD_STD, "sample": [{"area": 102_000}]},
        reason="Transcription error against the chromatogram",
    )
    assert corrected.group_values["sample"] == [{"area": 102_000}]
    assert result.values["sample.assay"] == pytest.approx(102.0)


@pytest.mark.asyncio
async def test_calculated_fields_cannot_be_overwritten_by_a_client(db_session):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)

    saved, _, result = await svc.save_values(
        worksheet.id,
        user(ANALYST, "Analyst"),
        group_values={
            "std": GOOD_STD,
            #  A client echoing back the whole row, assay included.
            "sample": [{"area": 101_000, "assay": 999.99}],
        },
    )

    assert "assay" not in saved.group_values["sample"][0]
    assert result.values["sample.assay"] == pytest.approx(101.0)


@pytest.mark.asyncio
async def test_non_overridable_context_is_refused(db_session):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)

    with pytest.raises(ValidationException) as exc:
        await svc.save_values(
            worksheet.id, user(ANALYST, "Analyst"), context_values={"batch": "TAMPERED"}
        )
    assert "cannot be overridden" in str(exc.value)

    #  The overridable one is accepted.
    saved, _, _ = await svc.save_values(
        worksheet.id, user(ANALYST, "Analyst"), context_values={"std_wt": 250}
    )
    assert saved.context_values["std_wt"] == 250
    assert saved.context_values["batch"] == "B-2601"


@pytest.mark.asyncio
async def test_row_bounds_are_enforced(db_session):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)

    with pytest.raises(ValidationException) as exc:
        await svc.save_values(
            worksheet.id,
            user(ANALYST, "Analyst"),
            group_values={"std": [{"area": 100_000}] * 7},
        )
    assert "at most 6 rows" in str(exc.value)

    with pytest.raises(ValidationException):
        await svc.save_values(
            worksheet.id,
            user(ANALYST, "Analyst"),
            group_values={"sample": [{"area": 1}, {"area": 2}]},
        )


# ── Property 14: area source is always recorded ──────────────────────


@pytest.mark.asyncio
async def test_area_source_is_recorded_for_every_populated_area(db_session):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)
    await svc.save_values(
        worksheet.id,
        user(ANALYST, "Analyst"),
        group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]},
    )

    entry = next(
        e
        for e in await AuditLogRepositoryImpl(db_session).list_recent(limit=50)
        if e.action == "WORKSHEET_VALUES_SAVED"
    )
    sources = entry.new_values["area_sources"]
    assert sources == {"std.area": "ManualEntry", "sample.area": "ManualEntry"}


@pytest.mark.asyncio
async def test_unpopulated_areas_are_not_claimed_to_have_a_source(db_session):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)
    await svc.save_values(
        worksheet.id, user(ANALYST, "Analyst"), group_values={"std": GOOD_STD}
    )

    entry = next(
        e
        for e in await AuditLogRepositoryImpl(db_session).list_recent(limit=50)
        if e.action == "WORKSHEET_VALUES_SAVED"
    )
    assert entry.new_values["area_sources"] == {"std.area": "ManualEntry"}


@pytest.mark.asyncio
async def test_only_changed_fields_are_logged(db_session):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)
    analyst = user(ANALYST, "Analyst")
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]}
    )
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": GOOD_STD, "sample": [{"area": 102_000}]}
    )

    entries = [
        e
        for e in await AuditLogRepositoryImpl(db_session).list_recent(limit=50)
        if e.action == "WORKSHEET_VALUES_SAVED"
    ]
    latest = entries[0]
    assert latest.old_values == {"sample[1].area": 101_000}
    assert latest.new_values["sample[1].area"] == 102_000
    #  The unchanged standard rows stay out of the diff.
    assert "std[1].area" not in latest.new_values


# ── Property 11: blocking criteria gate confirmation ─────────────────


@pytest.mark.asyncio
async def test_confirmation_is_refused_while_a_blocking_criterion_fails(db_session):
    svc, worksheet, line, _trf, _template = await _worksheet_in_progress(db_session)
    analyst = user(ANALYST, "Analyst")
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": BAD_STD, "sample": [{"area": 101_000}]}
    )

    with pytest.raises(ValidationException) as exc:
        await svc.confirm_result(worksheet.id, analyst)
    assert "blocking acceptance criterion" in str(exc.value)
    assert "Standard area %RSD" in str(exc.value)

    after = await svc.get_worksheet(worksheet.id)
    assert after.status == WorksheetStatus.IN_PROGRESS.value
    assert after.computed_snapshot is None
    #  Crucially, nothing reached the test line.
    assert (await TRFRepositoryImpl(db_session).get_test_line_by_id(line.id)).result is None


@pytest.mark.asyncio
async def test_an_advisory_criterion_does_not_block(db_session):
    advisory = {
        **DEFINITION,
        "criteria": [{**DEFINITION["criteria"][0], "severity": "advisory"}],
    }
    test = await seed_test(db_session)
    trf, line = await seed_trf_with_line(db_session, status="InProgress", test=test)
    trf.analyst_accepted_by = ANALYST
    await db_session.flush()
    template = await _seed_active_template(db_session, test.id, definition=advisory)

    svc = _service(db_session)
    analyst = user(ANALYST, "Analyst")
    worksheet = await svc.create_worksheet(line.id, template.id, analyst)
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": BAD_STD, "sample": [{"area": 101_000}]}
    )

    confirmed, _, result = await svc.confirm_result(worksheet.id, analyst)
    assert confirmed.is_confirmed
    #  The failure is still recorded, just not gating.
    assert [c["passed"] for c in confirmed.computed_snapshot["criteria"]] == [False]
    assert result.has_blocking_failure is False


@pytest.mark.asyncio
async def test_a_blank_reportable_result_cannot_be_confirmed(db_session):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)
    analyst = user(ANALYST, "Analyst")
    #  Standards entered but no sample area — assay stays blank.
    await svc.save_values(worksheet.id, analyst, group_values={"std": GOOD_STD})

    with pytest.raises(ValidationException) as exc:
        await svc.confirm_result(worksheet.id, analyst)
    assert "blank" in str(exc.value)


@pytest.mark.asyncio
async def test_confirmation_only_while_in_progress(db_session):
    svc, worksheet, _line, trf, _template = await _worksheet_in_progress(db_session)
    analyst = user(ANALYST, "Analyst")
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]}
    )
    await set_trf_status(db_session, trf, "PendingADGLRelease")

    with pytest.raises(ForbiddenException):
        await svc.confirm_result(worksheet.id, analyst)
    with pytest.raises(ValidationException) as exc:
        await svc.confirm_result(worksheet.id, user("qa1", "QA", user_id=3))
    assert "InProgress" in str(exc.value)


# ── Property 13: the confirmed result reaches the test line unchanged ─


@pytest.mark.asyncio
async def test_confirmed_result_reaches_the_test_line_with_its_unit(db_session):
    svc, worksheet, line, _trf, template = await _worksheet_in_progress(db_session)
    analyst = user(ANALYST, "Analyst")
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]}
    )

    confirmed, saved_line, result = await svc.confirm_result(worksheet.id, analyst)

    #  101000 / mean(100500, 99500) * 100 = 101.0, rounded to 2dp by the template.
    assert result.values["sample.assay"] == pytest.approx(101.0)
    assert confirmed.reportable_result == "101 %"
    assert saved_line.result == "101 %"
    assert saved_line.has_result() is True

    #  And it survives a reload — the write went to the database, not just the entity.
    reloaded = await TRFRepositoryImpl(db_session).get_test_line_by_id(line.id)
    assert reloaded.result == "101 %"


@pytest.mark.asyncio
async def test_the_result_is_not_re_rounded_on_its_way_to_the_test_line(db_session):
    """
    The template's own rounding is authoritative. A 2dp template result of
    100.34 must arrive as `100.34 %`, not `100.3 %` or `100.34000000000001 %`.
    """
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)
    analyst = user(ANALYST, "Analyst")
    #  100340 / 100000 * 100 = 100.34 exactly.
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": GOOD_STD, "sample": [{"area": 100_340}]}
    )

    confirmed, saved_line, _ = await svc.confirm_result(worksheet.id, analyst)
    assert confirmed.reportable_result == "100.34 %"
    assert saved_line.result == "100.34 %"


@pytest.mark.asyncio
async def test_confirmation_snapshots_inputs_computed_values_and_criteria(db_session):
    svc, worksheet, _line, trf, template = await _worksheet_in_progress(db_session)
    analyst = user(ANALYST, "Analyst")
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]}
    )

    confirmed, _, _ = await svc.confirm_result(worksheet.id, analyst)
    snap = confirmed.computed_snapshot

    assert snap["template"] == {
        "id": template.id,
        "code": "TPL-A1-0001",
        "name": "Assay by HPLC",
        "archetype": "A1",
        "version": 1,
        "result_unit": "%",
    }
    assert snap["inputs"]["groups"]["std"] == GOOD_STD
    assert snap["inputs"]["context"]["batch"] == trf.batch_number
    assert snap["computed"]["rows"]["sample"][0]["assay"] == pytest.approx(101.0)
    assert snap["criteria"][0]["passed"] is True
    assert snap["reportable_result"] == pytest.approx(101.0)
    assert snap["confirmed_by"] == ANALYST
    assert confirmed.confirmed_by == ANALYST
    assert confirmed.confirmed_at is not None


@pytest.mark.asyncio
async def test_a_qa_correction_reopens_and_republishes_the_result(db_session):
    svc, worksheet, line, trf, _template = await _worksheet_in_progress(db_session)
    analyst = user(ANALYST, "Analyst")
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]}
    )
    await svc.confirm_result(worksheet.id, analyst)
    first_snapshot = (await svc.get_worksheet(worksheet.id)).computed_snapshot

    await set_trf_status(db_session, trf, "PendingADGLRelease")
    corrected, _, _ = await svc.save_values(
        worksheet.id,
        user("qa1", "QA", user_id=3),
        group_values={"std": GOOD_STD, "sample": [{"area": 102_000}]},
        reason="Area transposed from the wrong chromatogram",
    )

    #  Reopened for correction, but the prior snapshot is retained until the next
    #  confirmation replaces it — a released TRF never has an unsupported result.
    assert corrected.status == WorksheetStatus.IN_PROGRESS.value
    assert corrected.computed_snapshot == first_snapshot
    #  The test line still shows the previously confirmed value until reconfirmed.
    assert (await TRFRepositoryImpl(db_session).get_test_line_by_id(line.id)).result == "101 %"

    entry = next(
        e
        for e in await AuditLogRepositoryImpl(db_session).list_recent(limit=50)
        if e.action == "WORKSHEET_VALUES_CORRECTED"
    )
    assert entry.new_values["reason"] == "Area transposed from the wrong chromatogram"
    assert entry.username == "qa1"


@pytest.mark.asyncio
async def test_confirmation_writes_one_audit_entry(db_session):
    svc, worksheet, _line, _trf, _template = await _worksheet_in_progress(db_session)
    analyst = user(ANALYST, "Analyst")
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]}
    )
    await svc.confirm_result(worksheet.id, analyst)

    actions = [e.action for e in await AuditLogRepositoryImpl(db_session).list_recent(limit=50)]
    assert actions.count("WORKSHEET_CREATED") == 1
    assert actions.count("WORKSHEET_VALUES_SAVED") == 1
    assert actions.count("WORKSHEET_RESULT_CONFIRMED") == 1


# ── Property 10 at the worksheet boundary ────────────────────────────


@pytest.mark.asyncio
async def test_a_worksheet_keeps_computing_against_the_version_it_was_created_on(db_session):
    """
    Requirement 2.7: re-versioning or deactivating a template must not change
    what an executed worksheet resolves against.
    """
    svc, worksheet, _line, _trf, template = await _worksheet_in_progress(db_session)
    analyst = user(ANALYST, "Analyst")
    await svc.save_values(
        worksheet.id, analyst, group_values={"std": GOOD_STD, "sample": [{"area": 101_000}]}
    )

    #  A v2 of the same code with a completely different formula, plus v1
    #  deactivated — the two things that would break a lazily-resolved binding.
    db_session.add(
        TestTemplateModel(
            code="TPL-A1-0001",
            name="Assay by HPLC",
            archetype="A1",
            test_id=template.test_id,
            version=2,
            status="Active",
            result_unit="%",
            definition={
                **DEFINITION,
                "groups": [
                    DEFINITION["groups"][0],
                    {
                        "key": "sample",
                        "kind": "singleton",
                        "fields": [
                            {"key": "area", "kind": "area"},
                            {
                                "key": "assay",
                                "kind": "calculated",
                                "expression": "area / mean(std.area) * 999",
                            },
                        ],
                    },
                ],
            },
            created_by="admin",
            modified_by="admin",
        )
    )
    template_model = await db_session.get(TestTemplateModel, template.id)
    template_model.status = "Inactive"
    await db_session.flush()

    _, _, result = await svc.preview(worksheet.id)
    assert result.values["sample.assay"] == pytest.approx(101.0)

    confirmed, saved_line, _ = await svc.confirm_result(worksheet.id, analyst)
    assert saved_line.result == "101 %"
    assert confirmed.computed_snapshot["template"]["version"] == 1
