"""Apply two in-place additions to the LIVE Draft template TPL-A6D-0002 (id=43).

Reads the LIVE definition for TPL-A6D-0002 from lims.db (source of truth),
deep-copies it, applies two purely-additive edits, validates with the service's
two-pass gate (TemplateDefinition.parse + WorksheetEvaluator.evaluate({}, {})),
writes the definition back to the SAME row, and re-reads to assert byte-equality.
Pattern follows `_apply_a6d_sampling_details.py` / `_apply_cu30_kedit.py`.

ADDITION 1 — a new "Standard Tapinarof for Linearity" section.
  ONE add-ROW `sequence` group `key="linearity"` inserted immediately after `qc`
  and before `cells`, with eight input fields and
  `rows = {min:9, max:15, default:9, labelFrom:"calibration_curve"}`. One
  continuous table (the user chose "use 1" — not two set-blocks). The group opens
  with nine blank rows; the nine fixed row labels (Calibration standard-1..6,
  LQC, MQC, HQC) and their Concentration (%) values are analyst-entered — they are
  NOT baked into the stored definition because the schema has no per-row seed
  mechanism (RowSpec holds only counts; FieldDef.default is one value for all
  rows). Columns 3–4 (`std_weight_mg`, `diluted_to_ml_1`) are ordinary blank
  per-row inputs filled once per block by convention (no merge primitive exists).
  The pasted example figures (89.73, 50.0, 5.0, …) are NOT stored.

ADDITION 2 — fill the Additional-Info right column.
  Append exactly SIX new `context[]` fields: `trf_number` (source
  `trf.trf_number`) and `ar_number` (source `trf.ar_number`) as non-overridable
  auto-fetch; `working_std_no`, `use_before_date`, `time_points_min`,
  `avg_weight_mg` as `overridable:true` blank manual inputs (no source). The five
  already-present right-column fields (`date_of_analysis`, `potency`,
  `temperature_c`, `donor_area`, `batch_no`) are NOT duplicated.

Both additions are purely additive; `resultRef` stays `flux.mean_flux`; no
existing group/expression is touched; no status change (stays Draft).
"""
import argparse
import asyncio
import copy
import json

from sqlalchemy import select

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition
from src.infrastructure.database.models.test_template_model import TestTemplateModel
from src.infrastructure.database.session import async_session_factory

CODE = "TPL-A6D-0002"

#  ── Addition 1: the "linearity" sequence group (design Addition 1 JSON) ──
LINEARITY_GROUP = {
    "key": "linearity",
    "kind": "sequence",
    "label": "Standard Tapinarof for Linearity",
    "rows": {"min": 9, "max": 15, "default": 9, "labelFrom": "calibration_curve"},
    "fields": [
        {"key": "calibration_curve", "kind": "input", "type": "text", "label": "Calibration curve"},
        {"key": "concentration_pct", "kind": "input", "type": "number", "label": "Concentration", "unit": "%"},
        {"key": "std_weight_mg", "kind": "input", "type": "number", "label": "Standard Weight", "unit": "mg"},
        {"key": "diluted_to_ml_1", "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL"},
        {"key": "ml_a", "kind": "input", "type": "number", "label": "mL", "unit": "mL"},
        {"key": "ml_b", "kind": "input", "type": "number", "label": "mL", "unit": "mL"},
        {"key": "ml_taken", "kind": "input", "type": "number", "label": "mL taken", "unit": "mL"},
        {"key": "diluted_to_ml_2", "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL"},
    ],
}

#  ── Addition 2: the six new context fields (design Addition 2 JSON) ──
NEW_CONTEXT_FIELDS = [
    {"key": "trf_number", "kind": "context", "type": "text", "label": "TRF Number", "source": "trf.trf_number"},
    {"key": "ar_number", "kind": "context", "type": "text", "label": "A.R. No.", "source": "trf.ar_number"},
    {"key": "working_std_no", "kind": "context", "type": "text", "label": "Working / Reference Standard No.", "overridable": True},
    {"key": "use_before_date", "kind": "context", "type": "date", "label": "Use Before Date", "overridable": True},
    {"key": "time_points_min", "kind": "context", "type": "text", "label": "Time Points", "unit": "min", "overridable": True},
    {"key": "avg_weight_mg", "kind": "context", "type": "number", "label": "Average Weight", "unit": "mg", "overridable": True},
]

#  Five right-column items that ALREADY exist and must NOT be duplicated.
ALREADY_PRESENT = ["date_of_analysis", "potency", "temperature_c", "donor_area", "batch_no"]

#  Example figures from the user's paste — must appear NOWHERE in the stored def.
EXAMPLE_FIGURES = ["89.73", "50.0", "5.0", "1.0", "15.0", "3.0", "4.0", "6.0"]


def build_edited_definition(source_definition: dict) -> dict:
    """Deep-copy the live definition and apply both additions."""
    definition = copy.deepcopy(source_definition)

    # Addition 1: insert linearity immediately after `qc`, before `cells`.
    groups = definition["groups"]
    if any(g["key"] == "linearity" for g in groups):
        raise RuntimeError("definition already has a 'linearity' group")
    qc_index = next(i for i, g in enumerate(groups) if g["key"] == "qc")
    groups.insert(qc_index + 1, copy.deepcopy(LINEARITY_GROUP))

    # Addition 2: append the six new context fields; never duplicate existing.
    context = definition["context"]
    existing_keys = {c["key"] for c in context}
    for nf in NEW_CONTEXT_FIELDS:
        if nf["key"] in existing_keys:
            raise RuntimeError(f"context already has key {nf['key']!r}")
        context.append(copy.deepcopy(nf))

    return definition


def assert_additive(source_definition: dict, definition: dict) -> None:
    """The edit must change ONLY: (a) one inserted `linearity` group, and
    (b) six appended context fields. Every other group and every retained
    context field must be byte-for-byte identical to the live source."""
    src_groups = {g["key"]: g for g in source_definition["groups"]}
    new_groups = {g["key"]: g for g in definition["groups"]}

    assert set(new_groups) - set(src_groups) == {"linearity"}, (
        f"unexpected group changes: added {set(new_groups) - set(src_groups)}"
    )
    assert set(src_groups) - set(new_groups) == set(), "a source group went missing"
    for key, g in src_groups.items():
        assert json.dumps(new_groups[key], sort_keys=True) == json.dumps(g, sort_keys=True), (
            f"group {key!r} was altered (only 'linearity' may be new)"
        )

    src_ctx = {c["key"]: c for c in source_definition["context"]}
    new_ctx = {c["key"]: c for c in definition["context"]}
    added = set(new_ctx) - set(src_ctx)
    assert added == {f["key"] for f in NEW_CONTEXT_FIELDS}, f"unexpected context additions: {added}"
    assert set(src_ctx) - set(new_ctx) == set(), "a source context field went missing"
    for key, c in src_ctx.items():
        assert json.dumps(new_ctx[key], sort_keys=True) == json.dumps(c, sort_keys=True), (
            f"context field {key!r} was altered"
        )

    # No example figures baked anywhere in the linearity group.
    lin_json = json.dumps(new_groups["linearity"])
    for fig in EXAMPLE_FIGURES:
        assert fig not in lin_json, f"example figure {fig!r} leaked into the linearity group"
    # No per-row content / field defaults in the linearity group.
    for f in new_groups["linearity"]["fields"]:
        assert "default" not in f, f"linearity field {f['key']!r} must have no default"
    assert new_groups["linearity"]["rows"]["default"] == 9

    # resultRef untouched.
    assert definition.get("resultRef") == source_definition.get("resultRef") == "flux.mean_flux"

    # Everything used as a context source stays within the allowed catalogue.
    for f in NEW_CONTEXT_FIELDS:
        if "source" in f:
            assert f["source"] in {"trf.trf_number", "trf.ar_number"}, f["source"]

    print("additive-check OK: only +linearity group and +6 context fields; "
          "no example figures, no field defaults, resultRef unchanged")


def validate(definition: dict) -> None:
    """The service's two-pass gate: parse + dry-run evaluate on blank inputs."""
    parsed = TemplateDefinition.parse(definition)
    result = WorksheetEvaluator(parsed).evaluate({}, {})
    assert result.has_blocking_failure is False, "blank evaluate reported a blocking failure"
    print("validation OK: parse + evaluate({}, {}) succeeded, no blocking failure")


async def _load_source() -> tuple[dict, int]:
    """Return (source_definition, row_id) for the live TPL-A6D-0002."""
    async with async_session_factory() as sess:
        src = (
            await sess.execute(
                select(TestTemplateModel).where(TestTemplateModel.code == CODE)
            )
        ).scalar_one()
        return copy.deepcopy(src.definition), src.id


async def main(validate_only: bool = False) -> None:
    source_definition, row_id = await _load_source()
    definition = build_edited_definition(source_definition)

    assert_additive(source_definition, definition)
    validate(definition)

    if validate_only:
        print("--validate-only: no DB write performed.")
        return

    async with async_session_factory() as sess:
        row = (
            await sess.execute(
                select(TestTemplateModel).where(TestTemplateModel.code == CODE)
            )
        ).scalar_one()
        assert row.id == row_id
        row.definition = definition
        await sess.commit()

    async with async_session_factory() as sess:
        row = (
            await sess.execute(
                select(TestTemplateModel).where(TestTemplateModel.code == CODE)
            )
        ).scalar_one()
        assert json.dumps(row.definition, sort_keys=True) == json.dumps(
            definition, sort_keys=True
        ), "re-read definition is not byte-equal to the written definition"
    print(f"wrote {CODE} id={row_id} status=Draft; re-read byte-equal OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()
    asyncio.run(main(validate_only=args.validate_only))
