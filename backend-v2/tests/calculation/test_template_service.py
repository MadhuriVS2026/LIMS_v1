"""
TestTemplateService tests.

Covers Property 9 (a malformed definition never reaches evaluation) at the
application boundary, Property 10 (versioning preserves executed worksheets),
the Admin-only authoring gate, and the audit trail (Property 17).

The Property 9 cases here are deliberately the ones the *parser alone* cannot
catch — circular references and unparseable expressions only surface once the
dependency graph is built, which is why the service runs the evaluator once
against empty values before persisting anything.
"""
import pytest

from src.application.exceptions.application_exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.application.services.test_template_service import TestTemplateService
from src.domain.entities.test_template import TemplateStatus
from src.infrastructure.database.repositories.audit_repository_impl import (
    AuditLogRepositoryImpl,
)
from src.infrastructure.database.repositories.test_repository_impl import TestRepositoryImpl
from src.infrastructure.database.repositories.test_template_repository_impl import (
    TestTemplateRepositoryImpl,
)
from tests.calculation.conftest import seed_test, user

VALID_DEFINITION = {
    "resultRef": "sample.assay",
    "groups": [
        {
            "key": "std",
            "kind": "table",
            "rows": {"min": 1, "max": 6, "default": 2},
            "fields": [{"key": "area", "kind": "area"}],
        },
        {
            "key": "sample",
            "kind": "singleton",
            "fields": [
                {"key": "area", "kind": "area"},
                {
                    "key": "assay",
                    "kind": "calculated",
                    "expression": "area / mean(std.area) * 100",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
    ],
}


def _service(session) -> TestTemplateService:
    return TestTemplateService(
        TestTemplateRepositoryImpl(session),
        TestRepositoryImpl(session),
        AuditLogRepositoryImpl(session),
    )


async def _active_template(session, test_id: int) -> tuple[TestTemplateService, int]:
    svc = _service(session)
    admin = user("admin", "Admin")
    tpl = await svc.create_template(
        name="Assay by HPLC",
        archetype="A1",
        test_id=test_id,
        definition=VALID_DEFINITION,
        result_unit="%",
        actor=admin,
    )
    await svc.submit_for_approval(tpl.id, admin)
    await svc.approve(tpl.id, user("qa1", "QA", user_id=2))
    return svc, tpl.id


# ── Authoring ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_template_generates_code_and_starts_as_draft(db_session):
    svc = _service(db_session)
    test = await seed_test(db_session)

    tpl = await svc.create_template(
        name="Assay by HPLC",
        archetype="A1",
        test_id=test.id,
        definition=VALID_DEFINITION,
        result_unit="%",
        actor=user("admin", "Admin"),
    )

    assert tpl.code == "TPL-A1-0001"
    assert tpl.version == 1
    assert tpl.status == TemplateStatus.DRAFT.value
    assert tpl.test_code == "TST-01"

    #  The sequence runs per archetype, so a second A1 gets 0002 while an A4
    #  starts its own sequence.
    second = await svc.create_template(
        name="Assay by HPLC (alt)",
        archetype="A1",
        test_id=test.id,
        definition=VALID_DEFINITION,
        result_unit="%",
        actor=user("admin", "Admin"),
    )
    other = await svc.create_template(
        name="Related Substances",
        archetype="A4",
        test_id=test.id,
        definition=VALID_DEFINITION,
        result_unit="%",
        actor=user("admin", "Admin"),
    )
    assert second.code == "TPL-A1-0002"
    assert other.code == "TPL-A4-0001"


@pytest.mark.asyncio
async def test_authoring_is_admin_only(db_session):
    svc = _service(db_session)
    test = await seed_test(db_session)

    for role in ("Analyst", "Supervisor", "QA"):
        with pytest.raises(ForbiddenException):
            await svc.create_template(
                name="Assay",
                archetype="A1",
                test_id=test.id,
                definition=VALID_DEFINITION,
                result_unit="%",
                actor=user("someone", role),
            )

    assert await svc.list_templates() == []


@pytest.mark.asyncio
async def test_create_template_requires_an_existing_test(db_session):
    svc = _service(db_session)
    with pytest.raises(NotFoundException):
        await svc.create_template(
            name="Assay",
            archetype="A1",
            test_id=4242,
            definition=VALID_DEFINITION,
            result_unit="%",
            actor=user("admin", "Admin"),
        )


# ── Property 9: a malformed definition never reaches evaluation ───────


@pytest.mark.parametrize(
    "definition, expected_fragment",
    [
        #  Structural — caught by the parser.
        ({"groups": [{"key": "g", "kind": "wat", "fields": [{"key": "a", "kind": "input"}]}]}, "GroupKind"),
        ({"groups": [{"key": "g", "kind": "singleton", "fields": []}]}, "non-empty"),
        (
            {"groups": [{"key": "g", "kind": "singleton", "fields": [{"key": "a", "kind": "calculated"}]}]},
            "needs an 'expression'",
        ),
        (
            {"groups": [{"key": "g", "kind": "singleton", "fields": [{"key": "row", "kind": "input"}]}]},
            "reserved",
        ),
        (
            {
                "resultRef": "g.nope",
                "groups": [{"key": "g", "kind": "singleton", "fields": [{"key": "a", "kind": "input"}]}],
            },
            "does not resolve",
        ),
        #  Relational — only visible once the dependency graph is built.
        (
            {
                "groups": [
                    {
                        "key": "g",
                        "kind": "singleton",
                        "fields": [
                            {"key": "a", "kind": "calculated", "expression": "b + 1"},
                            {"key": "b", "kind": "calculated", "expression": "a + 1"},
                        ],
                    }
                ]
            },
            "Circular reference",
        ),
        (
            {
                "groups": [
                    {
                        "key": "g",
                        "kind": "singleton",
                        "fields": [{"key": "a", "kind": "calculated", "expression": "1 +"}],
                    }
                ]
            },
            "invalid expression",
        ),
    ],
)
@pytest.mark.asyncio
async def test_malformed_definitions_are_rejected_and_nothing_is_persisted(
    db_session, definition, expected_fragment
):
    svc = _service(db_session)
    test = await seed_test(db_session)

    with pytest.raises(ValidationException) as exc:
        await svc.create_template(
            name="Bad template",
            archetype="A1",
            test_id=test.id,
            definition=definition,
            result_unit="%",
            actor=user("admin", "Admin"),
        )
    assert expected_fragment in str(exc.value)
    assert await svc.list_templates() == []


@pytest.mark.asyncio
async def test_unknown_function_is_rejected(db_session):
    """Property 2 at the service boundary: nothing outside the function table."""
    svc = _service(db_session)
    test = await seed_test(db_session)

    with pytest.raises(ValidationException):
        await svc.create_template(
            name="Sneaky",
            archetype="A1",
            test_id=test.id,
            definition={
                "groups": [
                    {
                        "key": "g",
                        "kind": "singleton",
                        "fields": [
                            {"key": "a", "kind": "calculated", "expression": "__import__('os')"}
                        ],
                    }
                ]
            },
            result_unit="%",
            actor=user("admin", "Admin"),
        )


# ── Lifecycle ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_definition_is_editable_only_while_draft(db_session):
    svc = _service(db_session)
    test = await seed_test(db_session)
    admin = user("admin", "Admin")

    tpl = await svc.create_template(
        name="Assay",
        archetype="A1",
        test_id=test.id,
        definition=VALID_DEFINITION,
        result_unit="%",
        actor=admin,
    )

    edited = {**VALID_DEFINITION, "resultRef": None}
    updated = await svc.update_definition(tpl.id, edited, admin)
    assert updated.definition["resultRef"] is None

    await svc.submit_for_approval(tpl.id, admin)
    with pytest.raises(ValidationException) as exc:
        await svc.update_definition(tpl.id, VALID_DEFINITION, admin)
    assert "Draft" in str(exc.value)


@pytest.mark.asyncio
async def test_approval_requires_a_reviewer_role_and_activates(db_session):
    svc = _service(db_session)
    test = await seed_test(db_session)
    admin = user("admin", "Admin")

    tpl = await svc.create_template(
        name="Assay",
        archetype="A1",
        test_id=test.id,
        definition=VALID_DEFINITION,
        result_unit="%",
        actor=admin,
    )
    await svc.submit_for_approval(tpl.id, admin)

    with pytest.raises(ForbiddenException):
        await svc.approve(tpl.id, user("an1", "Analyst"))

    approved = await svc.approve(tpl.id, user("qa1", "QA", user_id=2))
    assert approved.status == TemplateStatus.ACTIVE.value
    assert approved.approved_by == "qa1"
    assert approved.approved_at is not None
    assert approved.is_selectable is True


@pytest.mark.asyncio
async def test_rejection_returns_it_to_draft_and_requires_a_comment(db_session):
    svc = _service(db_session)
    test = await seed_test(db_session)
    admin = user("admin", "Admin")

    tpl = await svc.create_template(
        name="Assay",
        archetype="A1",
        test_id=test.id,
        definition=VALID_DEFINITION,
        result_unit="%",
        actor=admin,
    )
    await svc.submit_for_approval(tpl.id, admin)

    with pytest.raises(ValidationException):
        await svc.reject(tpl.id, user("qa1", "QA", user_id=2), "   ")

    rejected = await svc.reject(tpl.id, user("qa1", "QA", user_id=2), "Wrong dilution chain")
    assert rejected.status == TemplateStatus.DRAFT.value


@pytest.mark.asyncio
async def test_only_active_templates_are_offered_for_a_test(db_session):
    svc = _service(db_session)
    test = await seed_test(db_session)
    _, active_id = await _active_template(db_session, test.id)

    await svc.create_template(
        name="Draft one",
        archetype="A1",
        test_id=test.id,
        definition=VALID_DEFINITION,
        result_unit="%",
        actor=user("admin", "Admin"),
    )

    offered = await svc.templates_for_test(test.id)
    assert [t.id for t in offered] == [active_id]

    await svc.deactivate(active_id, user("admin", "Admin"))
    assert await svc.templates_for_test(test.id) == []


# ── Property 10: versioning preserves executed worksheets ─────────────


@pytest.mark.asyncio
async def test_new_version_leaves_the_approved_version_untouched(db_session):
    test = await seed_test(db_session)
    svc, v1_id = await _active_template(db_session, test.id)
    admin = user("admin", "Admin")

    draft = await svc.new_version(v1_id, admin)
    assert draft.version == 2
    assert draft.status == TemplateStatus.DRAFT.value

    #  Rewrite the clone's formula entirely.
    mutated = {
        **VALID_DEFINITION,
        "groups": [
            VALID_DEFINITION["groups"][0],
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
    }
    await svc.update_definition(draft.id, mutated, admin)

    v1 = await svc.get_template(v1_id)
    assert v1.status == TemplateStatus.ACTIVE.value
    assert (
        v1.definition["groups"][1]["fields"][1]["expression"]
        == "area / mean(std.area) * 100"
    )


@pytest.mark.asyncio
async def test_approving_a_new_version_supersedes_the_old_one(db_session):
    test = await seed_test(db_session)
    svc, v1_id = await _active_template(db_session, test.id)
    admin = user("admin", "Admin")
    qa = user("qa1", "QA", user_id=2)

    draft = await svc.new_version(v1_id, admin)
    await svc.submit_for_approval(draft.id, admin)
    v2 = await svc.approve(draft.id, qa)

    v1 = await svc.get_template(v1_id)
    assert v1.status == TemplateStatus.INACTIVE.value
    assert v1.superseded_by_id == v2.id
    #  Exactly one selectable version, so the analyst is never asked to choose.
    assert [t.id for t in await svc.templates_for_test(test.id)] == [v2.id]


@pytest.mark.asyncio
async def test_only_one_unapproved_version_at_a_time(db_session):
    test = await seed_test(db_session)
    svc, v1_id = await _active_template(db_session, test.id)
    admin = user("admin", "Admin")

    await svc.new_version(v1_id, admin)
    with pytest.raises(ValidationException) as exc:
        await svc.new_version(v1_id, admin)
    assert "already has an unapproved version" in str(exc.value)


@pytest.mark.asyncio
async def test_a_draft_cannot_be_branched(db_session):
    svc = _service(db_session)
    test = await seed_test(db_session)
    tpl = await svc.create_template(
        name="Assay",
        archetype="A1",
        test_id=test.id,
        definition=VALID_DEFINITION,
        result_unit="%",
        actor=user("admin", "Admin"),
    )
    with pytest.raises(ValidationException):
        await svc.new_version(tpl.id, user("admin", "Admin"))


# ── Property 17: one audit entry per mutation ────────────────────────


@pytest.mark.asyncio
async def test_each_lifecycle_transition_writes_one_audit_entry(db_session):
    test = await seed_test(db_session)
    svc = _service(db_session)
    admin = user("admin", "Admin")
    qa = user("qa1", "QA", user_id=2)
    audit = AuditLogRepositoryImpl(db_session)

    tpl = await svc.create_template(
        name="Assay",
        archetype="A1",
        test_id=test.id,
        definition=VALID_DEFINITION,
        result_unit="%",
        actor=admin,
    )
    await svc.update_definition(tpl.id, VALID_DEFINITION, admin)
    await svc.submit_for_approval(tpl.id, admin)
    await svc.approve(tpl.id, qa)
    await svc.new_version(tpl.id, admin)
    await svc.deactivate(tpl.id, admin)

    actions = [e.action for e in await audit.list_recent(limit=50)]
    for expected in (
        "TEMPLATE_CREATED",
        "TEMPLATE_DEFINITION_UPDATED",
        "TEMPLATE_SUBMITTED",
        "TEMPLATE_APPROVED",
        "TEMPLATE_VERSIONED",
        "TEMPLATE_DEACTIVATED",
    ):
        assert actions.count(expected) == 1, f"{expected} should be logged exactly once"
