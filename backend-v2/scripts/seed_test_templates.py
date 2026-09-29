"""
Seed test calculation templates for every archetype in scope.

Unlike `seed_data.py` this is **additive and idempotent** — it never drops the
schema and it skips any template whose code already exists, so it is safe to run
against a database that already holds TRFs and worksheets. Re-running after
adding an archetype inserts only the new one.

It also creates any missing Test Master entry, because a template bound to a Test
that does not exist can never be selected on a TRF test line — seeding a template
without its Test would look like success and produce nothing usable.

Usage: python -m scripts.seed_test_templates            (seed as Active)
       python -m scripts.seed_test_templates --draft    (route through approval)
       python -m scripts.seed_test_templates --validate-only

Templates are seeded `Active` by default so they are immediately selectable, with
`approved_by` stamped `seed` rather than a username — it must be obvious in the UI
and the audit trail that no human signed these off. A validated environment should
use `--draft` and put them through the real submit/approve gate.
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from scripts.template_definitions import SEED_TEMPLATES, SeedTemplate
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition
from src.infrastructure.database.models.base_model import Base
from src.infrastructure.database.models.test_model import TestModel
from src.infrastructure.database.models.test_template_model import TestTemplateModel
from src.infrastructure.database.session import async_session_factory, engine


def validate(seed: SeedTemplate) -> TemplateDefinition:
    """
    Parse and dry-run a definition — the same two passes `TestTemplateService`
    applies. A seed that inserted an unevaluable template would fail at result
    entry instead of here, in front of whoever ran the script.
    """
    parsed = TemplateDefinition.parse(seed.definition)
    WorksheetEvaluator(parsed).evaluate({}, {})
    return parsed


def describe(parsed: TemplateDefinition) -> str:
    inputs = sum(1 for g in parsed.groups for f in g.fields if f.kind.value == "input")
    calculated = sum(
        1 for g in parsed.groups for f in g.fields if f.kind.value == "calculated"
    )
    return (
        f"{len(parsed.groups)} groups, {inputs} inputs, "
        f"{len(parsed.area_field_refs)} area fields, {calculated} calculated, "
        f"{len(parsed.criteria)} criteria"
    )


async def ensure_test(session, seed: SeedTemplate) -> TestModel:
    """Fetch the Test Master entry for this template, creating it if absent."""
    test = (
        await session.execute(select(TestModel).where(TestModel.code == seed.test_code))
    ).scalar_one_or_none()
    if test is not None:
        return test

    test = TestModel(
        code=seed.test_code,
        name=seed.test_name,
        type=seed.test_type,
        status="Active",
        created_by="seed",
        modified_by="seed",
    )
    session.add(test)
    await session.flush()
    print(f"        + Test Master: {seed.test_code} — {seed.test_name}")
    return test


async def seed(as_draft: bool = False, validate_only: bool = False) -> int:
    #  Validate everything before touching the database, so a bad definition
    #  cannot leave a half-seeded catalogue behind.
    parsed_by_code: dict[str, TemplateDefinition] = {}
    failures: list[str] = []
    for item in SEED_TEMPLATES:
        try:
            parsed_by_code[item.code] = validate(item)
        except Exception as exc:  # noqa: BLE001 — report all, not just the first
            failures.append(f"  {item.code} ({item.archetype}): {exc}")

    print(f"Validating {len(SEED_TEMPLATES)} template definition(s)...")
    for item in SEED_TEMPLATES:
        parsed = parsed_by_code.get(item.code)
        if parsed is not None:
            print(f"  ok   {item.code} [{item.archetype}] {describe(parsed)}")

    if failures:
        print("\nINVALID DEFINITIONS — nothing was seeded:")
        for line in failures:
            print(line)
        return 1

    if validate_only:
        print("\nAll definitions valid. --validate-only, so nothing was written.")
        return 0

    #  Additive only. This may run against a database holding real worksheets, and
    #  a dropped table would take their GxP snapshots with it.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    now = datetime.now(timezone.utc)
    status = "Draft" if as_draft else "Active"
    added = 0

    print(f"\nSeeding as {status}...")
    async with async_session_factory() as session:
        for item in SEED_TEMPLATES:
            existing = (
                await session.execute(
                    select(TestTemplateModel).where(TestTemplateModel.code == item.code)
                )
            ).scalars().first()
            if existing is not None:
                print(f"  skip {item.code} — already present (v{existing.version}, {existing.status})")
                continue

            test = await ensure_test(session, item)
            session.add(
                TestTemplateModel(
                    code=item.code,
                    name=item.name,
                    archetype=item.archetype,
                    test_id=test.id,
                    version=1,
                    status=status,
                    result_unit=item.result_unit,
                    definition=item.definition,
                    #  Stamped `seed`, not a username: it must be visible that no
                    #  human signed this off.
                    approved_by=None if as_draft else "seed",
                    approved_at=None if as_draft else now,
                    created_by="seed",
                    modified_by="seed",
                )
            )
            print(f"  add  {item.code} [{item.archetype}] {item.name} -> {item.test_code}")
            added += 1

        await session.commit()

    print(f"\nDone. {added} template(s) added, {len(SEED_TEMPLATES) - added} already present.")
    if not as_draft and added:
        print(
            "Seeded as Active for immediate use. In a validated environment seed with "
            "--draft and route them through the submit/approve gate instead."
        )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed test calculation templates.")
    parser.add_argument(
        "--draft", action="store_true", help="Seed as Draft instead of pre-approved Active."
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Parse and dry-run every definition without writing anything.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(seed(as_draft=args.draft, validate_only=args.validate_only)))
