"""One-off author script: two additions to the LIVE Draft TPL-A6D-0002 (id=43).

Reads the live definition of TPL-A6D-0002 from lims.db (source of truth),
deep-copies it, mutates in memory, validates with the service's two-pass gate
(TemplateDefinition.parse + WorksheetEvaluator.evaluate({}, {})), then writes
id=43's `.definition` and re-reads it byte-equal. Pattern follows
`_apply_cu30_kedit.py` (edit-in-place by code) and `_apply_a6d_sampling_details.py`
(deep-copy + two-pass validate + byte-equal re-read).

ADDITION 1 — a `linearity` `sequence` group ("Standard Tapinarof for Linearity"),
eight columns, add-row (min 9 / default 9 / max 15), inserted immediately after
`qc` and before `cells`. It carries a per-row `rows.seed`: the sheet opens with
nine rows whose `calibration_curve` label and `concentration_pct` are seeded; the
other six columns open blank. The seed capability is the additive `rows.seed`
mechanism added to `template_schema.py` + `worksheet_service.py`.

ADDITION 2 — eleven fixed Additional-Info defaults on `context[]` (the user's
option (a): fixed values that override any TRF auto-fetch). Five map to existing
keys (`date_of_analysis`, `potency`, `temperature_c`, `donor_area`, `batch_no`);
six are new (`working_std_no`, `use_before_date`, `time_points_min`,
`avg_weight_mg`, `trf_number`, `ar_number`). Any competing `source` is dropped so
the baked default is what `_seed_context` seeds and the UI renders.

The example weight/volume figures the user pasted (89.73, 50.0, 5.0, 50, 1.0,
15.0, 3.0, 4.0, 6.0) are EXAMPLES ONLY and are asserted ABSENT from the stored
definition — the six non-seeded linearity columns are blank reusable inputs.

TPL-A6D-0001 (id=26, Active) is not touched. Only id=43's `.definition` changes;
its code/name/version/status(Draft)/test_id/archetype/result_unit stay as-is.

Run `--validate-only` for a dry run that makes NO DB write.
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
EXPECTED_ID = 43

#  The nine mandated standards/QCs and their concentrations, opening order.
LINEARITY_SEED = [
    {"calibration_curve": "Calibration standard-1", "concentration_pct": 1},
    {"calibration_curve": "Calibration standard-2", "concentration_pct": 5},
    {"calibration_curve": "Calibration standard-3", "concentration_pct": 15},
    {"calibration_curve": "Calibration standard-4", "concentration_pct": 30},
    {"calibration_curve": "Calibration standard-5", "concentration_pct": 40},
    {"calibration_curve": "Calibration standard-6", "concentration_pct": 60},
    {"calibration_curve": "LQC", "concentration_pct": 1},
    {"calibration_curve": "MQC", "concentration_pct": 15},
    {"calibration_curve": "HQC", "concentration_pct": 30},
]

LINEARITY_GROUP = {
    "key": "linearity",
    "kind": "sequence",
    "label": "Standard Tapinarof for Linearity",
    "rows": {
        "min": 9,
        "max": 15,
        "default": 9,
        "labelFrom": "calibration_curve",
        "seed": LINEARITY_SEED,
    },
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

#  The six new Additional-Info context fields (none carry a `source`).
NEW_CONTEXT_FIELDS = [
    {"key": "working_std_no", "kind": "context", "type": "text", "label": "Working / Reference Standard No.", "default": "WS/25/079", "overridable": True},
    {"key": "use_before_date", "kind": "context", "type": "text", "label": "Use Before Date", "default": "26-May", "overridable": True},
    {"key": "time_points_min", "kind": "context", "type": "text", "label": "Time Points (Min)", "default": "40, 80, 120, 160, 200, 240", "overridable": True},
    {"key": "avg_weight_mg", "kind": "context", "type": "number", "unit": "mg", "label": "Average Weight", "default": 100, "overridable": True},
    {"key": "trf_number", "kind": "context", "type": "text", "label": "TRF Number", "default": "TRF-021-26-053", "overridable": True},
    {"key": "ar_number", "kind": "context", "type": "text", "label": "A.R. No.", "default": "AD/048/26/0121", "overridable": True},
]

#  The six non-seeded linearity columns — must open blank (no default).
UNSEEDED_COLUMNS = {
    "std_weight_mg",
    "diluted_to_ml_1",
    "ml_a",
    "ml_b",
    "ml_taken",
    "diluted_to_ml_2",
}

#  The distinctive weight/volume figure the user pasted as an EXAMPLE cell value
#  (89.73 mg). It must not be baked into the stored definition — the six
#  non-seeded linearity columns are blank reusable inputs. (The other pasted
#  examples — 50.0, 5.0, 1.0, 15.0, 3.0, 4.0, 6.0, 50 — are not checked by
#  substring because those digit runs collide with legitimate numbers already in
#  the definition such as the criteria limits 85.0 / 115.0; the structural check
#  below that every seed row names ONLY calibration_curve/concentration_pct, plus
#  the assertion that the six input columns carry no default, is the real guard
#  that no example cell value is stored.)
FORBIDDEN_EXAMPLE_FIGURES = ["89.73"]


def add_linearity_group(definition: dict) -> None:
    groups = definition["groups"]
    if any(g["key"] == "linearity" for g in groups):
        raise RuntimeError("definition already has a 'linearity' group")
    qc_index = next(i for i, g in enumerate(groups) if g["key"] == "qc")
    #  Insert immediately after qc (and before cells, which follows qc).
    groups.insert(qc_index + 1, copy.deepcopy(LINEARITY_GROUP))
    #  Confirm placement: linearity sits between qc and cells.
    keys = [g["key"] for g in groups]
    assert keys[keys.index("qc") + 1] == "linearity", keys
    assert keys[keys.index("linearity") + 1] == "cells", keys


def edit_context(definition: dict) -> None:
    ctx = definition["context"]
    by_key = {c["key"]: c for c in ctx}
    if len(by_key) != len(ctx):
        raise RuntimeError("duplicate context key in live definition")

    #  date_of_analysis: drop source, store the literal human string as text.
    doa = by_key["date_of_analysis"]
    doa.pop("source", None)
    doa["type"] = "text"
    doa["default"] = "06 April 2026"
    doa["overridable"] = True

    #  batch_no: drop source, bake the fixed batch.
    batch = by_key["batch_no"]
    batch.pop("source", None)
    batch["default"] = "LE6001"
    batch["overridable"] = True

    #  potency: default 100 -> 99.67 (unit %, overridable unchanged).
    pot = by_key["potency"]
    assert pot.get("default") == 100, pot
    pot["default"] = 99.67
    pot["overridable"] = True

    #  temperature_c / donor_area already carry the required defaults — assert.
    assert by_key["temperature_c"].get("default") == 32, by_key["temperature_c"]
    assert by_key["donor_area"].get("default") == 1.76, by_key["donor_area"]

    #  Add the six new fields after date_of_analysis; none carries a source.
    for key in (f["key"] for f in NEW_CONTEXT_FIELDS):
        if key in by_key:
            raise RuntimeError(f"context already has key {key!r}")
    doa_index = next(i for i, c in enumerate(ctx) if c["key"] == "date_of_analysis")
    for offset, f in enumerate(NEW_CONTEXT_FIELDS, start=1):
        ctx.insert(doa_index + offset, copy.deepcopy(f))

    #  No competing source on any of the eleven Additional-Info fields.
    eleven = {
        "date_of_analysis", "working_std_no", "use_before_date", "potency",
        "temperature_c", "time_points_min", "avg_weight_mg", "batch_no",
        "trf_number", "ar_number", "donor_area",
    }
    by_key = {c["key"]: c for c in ctx}
    for k in eleven:
        assert "source" not in by_key[k], f"{k} still has a competing source"


def build_mutated(source_definition: dict) -> dict:
    definition = copy.deepcopy(source_definition)
    add_linearity_group(definition)
    edit_context(definition)
    return definition


def validate(definition: dict) -> None:
    """Two-pass gate: parse + dry-run evaluate on blank inputs."""
    parsed = TemplateDefinition.parse(definition)
    result = WorksheetEvaluator(parsed).evaluate({}, {})
    assert result.has_blocking_failure is False, "blank evaluate reported a blocking failure"
    assert parsed.result_ref == "flux.mean_flux", f"resultRef changed: {parsed.result_ref}"

    #  Linearity group seeded correctly, six columns blank.
    lin = parsed.group("linearity")
    assert lin is not None and lin.kind.value == "sequence"
    assert (lin.rows.min, lin.rows.default, lin.rows.max) == (9, 9, 15)
    assert lin.rows.label_from == "calibration_curve"
    assert len(lin.rows.seed) == 9
    for row in lin.rows.seed:
        assert set(row) == {"calibration_curve", "concentration_pct"}, row
    for f in lin.fields:
        if f.key in UNSEEDED_COLUMNS:
            assert f.default is None, f"{f.key} must open blank"

    #  Eleven Additional-Info defaults present with the exact values.
    expected = {
        "date_of_analysis": "06 April 2026",
        "working_std_no": "WS/25/079",
        "use_before_date": "26-May",
        "potency": 99.67,
        "temperature_c": 32,
        "time_points_min": "40, 80, 120, 160, 200, 240",
        "avg_weight_mg": 100,
        "batch_no": "LE6001",
        "trf_number": "TRF-021-26-053",
        "ar_number": "AD/048/26/0121",
        "donor_area": 1.76,
    }
    for key, value in expected.items():
        cf = parsed.context_field(key)
        assert cf is not None, f"missing context field {key}"
        assert cf.default == value, f"{key} default {cf.default!r} != {value!r}"
        assert cf.source is None, f"{key} still has a source"

    #  No example figures baked into the stored definition.
    blob = json.dumps(definition)
    for fig in FORBIDDEN_EXAMPLE_FIGURES:
        assert fig not in blob, f"example figure {fig} leaked into definition"

    print("validation OK: parse + evaluate({}, {}) no blocking failure; "
          "linearity seeded, 11 Additional-Info defaults, no example figures")


async def _load() -> tuple[dict, int, str]:
    async with async_session_factory() as sess:
        row = (
            await sess.execute(select(TestTemplateModel).where(TestTemplateModel.code == CODE))
        ).scalar_one()
        return copy.deepcopy(row.definition), row.id, row.status


async def main(validate_only: bool = False) -> None:
    source_definition, row_id, status = await _load()
    assert row_id == EXPECTED_ID, f"{CODE} is id={row_id}, expected {EXPECTED_ID}"
    assert status == "Draft", f"{CODE} is {status}, expected Draft"

    definition = build_mutated(source_definition)
    validate(definition)

    if validate_only:
        print("--validate-only: no DB write performed.")
        return

    async with async_session_factory() as sess:
        row = (
            await sess.execute(select(TestTemplateModel).where(TestTemplateModel.code == CODE))
        ).scalar_one()
        assert row.id == EXPECTED_ID and row.status == "Draft"
        row.definition = definition
        await sess.commit()

    async with async_session_factory() as sess:
        row = (
            await sess.execute(select(TestTemplateModel).where(TestTemplateModel.code == CODE))
        ).scalar_one()
        assert json.dumps(row.definition, sort_keys=True) == json.dumps(
            definition, sort_keys=True
        ), "re-read definition is not byte-equal to the written definition"
    print(f"wrote/updated id={row.id} ({CODE}) status={row.status} … re-read byte-equal OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()
    asyncio.run(main(validate_only=args.validate_only))
