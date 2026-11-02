"""One-off author script: merge the calibration/linearity section of the LIVE
TPL-A6D-0002 (id=43) into ONE table and add a title singleton above it.

Reads the live definition of TPL-A6D-0002 from lims.db (source of truth),
deep-copies it, performs ONE coherent transform in memory, validates with the
service's two-pass gate (TemplateDefinition.parse + WorksheetEvaluator.evaluate)
plus a numeric acceptance harness over the user's six calibration-standard rows,
then writes id=43's `.definition` + `status='Active'` and re-reads it byte-equal.
Pattern follows `_apply_a6d_linearity.py` / `_apply_a6d_sampling_details.py`
(deep-copy + two-pass validate + byte-equal re-read).

THE MERGE (single `linearity` sequence table, twelve user-visible columns):
  1 calibration_curve  2 concentration_pct  3 std_weight_mg  4 diluted_to_ml_1
  5 ml_a  6 ml_b  7 ml_taken  8 diluted_to_ml_2
  9 theoretical_ppm (NEW calculated)  10 area (NEW area)
  11 observed_ppm (NEW calculated)   12 recovery_pct (NEW calculated)
plus two HIDDEN calculated boolean masks appended after the twelve
(`is_standard`, `is_qc`) used only to scope the regression to the six standards.

  theoretical_ppm = std_weight_mg / diluted_to_ml_1 * ml_a / ml_b
                    * ml_taken / diluted_to_ml_2 * potency / 100 * 1000
  observed_ppm    = (area - curve.curve_intercept) / curve.curve_slope
  recovery_pct    = observed_ppm / theoretical_ppm * 100   (round 2)

The `curve` regression is RE-POINTED to fit over the six standards only, via the
additive `where(series, mask)` engine built-in:
  curve_slope     = slope(where(linearity.area, linearity.is_standard),
                          where(linearity.theoretical_ppm, linearity.is_standard))
  curve_intercept = intercept(where(...), where(...))
  correlation     = correl(where(...), where(...))

The OLD `calibration` and `qc` groups are REMOVED; the two advisory QC-recovery
criteria are re-pointed at the QC rows now living in `linearity`. A free-text
TITLE singleton (`linearity_title`) is inserted IMMEDIATELY BEFORE `linearity`
(following the `sri1_header` precedent in a4_a5_related_substances.py), purely
informational — referenced by no expression/criterion/limit/resultRef.

Final group order: curve, linearity_title, linearity, cells, sampling_details,
timepoints, flux. resultRef stays flux.mean_flux; context/cells/sampling_details/
timepoints/flux are untouched.

TPL-A6D-0001 (id=26, Active) is never queried or touched.

Run `--validate-only` for a dry run that makes NO DB write.
"""
import argparse
import asyncio
import copy
import json

from sqlalchemy import select

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.expression import EMPTY
from src.domain.services.calculation.template_schema import TemplateDefinition
from src.infrastructure.database.models.test_template_model import TestTemplateModel
from src.infrastructure.database.session import async_session_factory

CODE = "TPL-A6D-0002"
EXPECTED_ID = 43
POTENCY = 99.67

#  Exact seeded standard labels the regression mask binds to.
STANDARD_LABELS = [f"Calibration standard-{n}" for n in range(1, 7)]

_IS_STANDARD_EXPR = " or ".join(
    f'(calibration_curve = "{label}")' for label in STANDARD_LABELS
)

#  The merged twelve user-visible columns (exact order) + two hidden masks.
LINEARITY_FIELDS = [
    {"key": "calibration_curve", "kind": "input", "type": "text", "label": "Calibration curve"},
    {"key": "concentration_pct", "kind": "input", "type": "number", "label": "Concentration", "unit": "%"},
    {"key": "std_weight_mg", "kind": "input", "type": "number", "label": "Standard Weight", "unit": "mg"},
    {"key": "diluted_to_ml_1", "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL"},
    {"key": "ml_a", "kind": "input", "type": "number", "label": "mL", "unit": "mL"},
    {"key": "ml_b", "kind": "input", "type": "number", "label": "mL", "unit": "mL"},
    {"key": "ml_taken", "kind": "input", "type": "number", "label": "mL taken", "unit": "mL"},
    {"key": "diluted_to_ml_2", "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL"},
    {
        "key": "theoretical_ppm",
        "kind": "calculated",
        "type": "number",
        "label": "Theoretical concentration",
        "unit": "ppm",
        "expression": (
            "std_weight_mg / diluted_to_ml_1 * ml_a / ml_b "
            "* ml_taken / diluted_to_ml_2 * potency / 100 * 1000"
        ),
    },
    {"key": "area", "kind": "area", "type": "number", "label": "Area Response", "unit": "\u00b5V\u00b7s"},
    {
        "key": "observed_ppm",
        "kind": "calculated",
        "type": "number",
        "label": "Observed concentration",
        "unit": "ppm",
        "expression": "(area - curve.curve_intercept) / curve.curve_slope",
    },
    {
        "key": "recovery_pct",
        "kind": "calculated",
        "type": "number",
        "label": "% Recovery",
        "unit": "%",
        "expression": "observed_ppm / theoretical_ppm * 100",
        "rounding": {"mode": "round", "digits": 2},
    },
    #  Hidden regression-scoping masks (never rendered as inputs; no unit).
    {
        "key": "is_standard",
        "kind": "calculated",
        "type": "boolean",
        "label": "Is calibration standard",
        "expression": _IS_STANDARD_EXPR,
    },
    {
        "key": "is_qc",
        "kind": "calculated",
        "type": "boolean",
        "label": "Is bracketing QC",
        "expression": "not is_standard",
    },
]

#  Six standard rows carry their dilution inputs; three QC rows carry label+pct.
LINEARITY_SEED = [
    {"calibration_curve": "Calibration standard-1", "concentration_pct": 1,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 5, "ml_b": 50, "ml_taken": 1, "diluted_to_ml_2": 50},
    {"calibration_curve": "Calibration standard-2", "concentration_pct": 5,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 5, "ml_b": 50, "ml_taken": 5, "diluted_to_ml_2": 50},
    {"calibration_curve": "Calibration standard-3", "concentration_pct": 15,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 5, "ml_b": 50, "ml_taken": 15, "diluted_to_ml_2": 50},
    {"calibration_curve": "Calibration standard-4", "concentration_pct": 30,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 1, "ml_b": 1, "ml_taken": 3, "diluted_to_ml_2": 50},
    {"calibration_curve": "Calibration standard-5", "concentration_pct": 40,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 1, "ml_b": 1, "ml_taken": 4, "diluted_to_ml_2": 50},
    {"calibration_curve": "Calibration standard-6", "concentration_pct": 60,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 1, "ml_b": 1, "ml_taken": 6, "diluted_to_ml_2": 50},
    {"calibration_curve": "LQC", "concentration_pct": 1},
    {"calibration_curve": "MQC", "concentration_pct": 15},
    {"calibration_curve": "HQC", "concentration_pct": 30},
]

LINEARITY_TITLE_GROUP = {
    "key": "linearity_title",
    "kind": "singleton",
    "label": "Calibration Standards",
    "fields": [
        {"key": "title", "kind": "input", "type": "text", "label": "Title",
         "default": "Calibration Standards"},
    ],
}

#  Re-pointed curve expressions (masked to the six standards).
_WHERE_AREA = "where(linearity.area, linearity.is_standard)"
_WHERE_THEO = "where(linearity.theoretical_ppm, linearity.is_standard)"
CURVE_EXPR = {
    "curve_slope": f"slope({_WHERE_AREA}, {_WHERE_THEO})",
    "curve_intercept": f"intercept({_WHERE_AREA}, {_WHERE_THEO})",
    "correlation": f"correl({_WHERE_AREA}, {_WHERE_THEO})",
}

#  Numeric acceptance targets (design §7, potency = 99.67).
EXPECT_THEORETICAL = [3.57735564, 17.8867782, 53.6603346, 107.3206692, 143.0942256, 214.6413384]
EXPECT_OBSERVED = [3.195478386, 17.57827346, 53.7823539, 107.0266337, 145.2356731, 213.3623055]
EXPECT_RECOVERY_RAW = [89.32515266, 98.27523583, 100.227392, 99.72602157, 101.4965296, 99.40410691]
EXPECT_SLOPE = 53797.61
EXPECT_INTERCEPT = 28844.87
EXPECT_CORREL = 0.9999

FINAL_GROUP_ORDER = [
    "curve", "linearity_title", "linearity", "cells",
    "sampling_details", "timepoints", "flux",
]


# ─────────────────────────── transform ───────────────────────────


def _extend_linearity(definition: dict) -> None:
    groups = definition["groups"]
    lin = next(g for g in groups if g["key"] == "linearity")
    assert lin["kind"] == "sequence", lin["kind"]
    lin["fields"] = copy.deepcopy(LINEARITY_FIELDS)
    lin["rows"] = {
        "min": 9,
        "max": 15,
        "default": 9,
        "labelFrom": "calibration_curve",
        "seed": copy.deepcopy(LINEARITY_SEED),
    }


def _insert_title(definition: dict) -> None:
    groups = definition["groups"]
    assert not any(g["key"] == "linearity_title" for g in groups)
    lin_index = next(i for i, g in enumerate(groups) if g["key"] == "linearity")
    groups.insert(lin_index, copy.deepcopy(LINEARITY_TITLE_GROUP))


def _repoint_curve(definition: dict) -> None:
    curve = next(g for g in definition["groups"] if g["key"] == "curve")
    by_key = {f["key"]: f for f in curve["fields"]}
    for key, expr in CURVE_EXPR.items():
        by_key[key]["expression"] = expr


def _remove_old_groups(definition: dict) -> None:
    definition["groups"] = [
        g for g in definition["groups"] if g["key"] not in ("calibration", "qc")
    ]


def _repoint_criteria(definition: dict) -> None:
    by_key = {c["key"]: c for c in definition["criteria"]}
    by_key["qc_recovery_low"]["target"] = "min(where(linearity.recovery_pct, linearity.is_qc))"
    by_key["qc_recovery_high"]["target"] = "max(where(linearity.recovery_pct, linearity.is_qc))"


def build_mutated(source_definition: dict) -> dict:
    definition = copy.deepcopy(source_definition)
    _extend_linearity(definition)
    _insert_title(definition)
    _repoint_curve(definition)
    _repoint_criteria(definition)
    _remove_old_groups(definition)
    #  Confirm final order.
    assert [g["key"] for g in definition["groups"]] == FINAL_GROUP_ORDER, [
        g["key"] for g in definition["groups"]
    ]
    return definition


# ─────────────────────────── validate ───────────────────────────


def _close(actual, expected, tol=1e-3):
    return actual is not EMPTY and abs(float(actual) - expected) <= tol


def _standard_rows_with_areas():
    areas = [200754, 974514, 2922207, 5786622, 7842177, 11507227]
    rows = []
    for seed, area in zip(LINEARITY_SEED[:6], areas):
        row = dict(seed)
        row["area"] = area
        rows.append(row)
    #  QC rows: label + pct only (no dilutions, no area).
    rows.extend(dict(seed) for seed in LINEARITY_SEED[6:])
    return rows


def validate(definition: dict) -> None:
    parsed = TemplateDefinition.parse(definition)

    #  Structure.
    assert parsed.result_ref == "flux.mean_flux", parsed.result_ref
    keys = [g.key for g in parsed.groups]
    assert keys == FINAL_GROUP_ORDER, keys
    assert keys[keys.index("linearity") - 1] == "linearity_title", keys

    #  Title singleton is purely informational — referenced by nothing.
    blob = json.dumps(definition)
    assert "linearity_title.title" not in blob, "title is referenced somewhere"
    title_group = parsed.group("linearity_title")
    assert title_group is not None and title_group.kind.value == "singleton"
    tf = title_group.field("title")
    assert tf is not None and tf.is_editable, "title must be an editable input"
    assert tf.default == "Calibration Standards", tf.default

    #  Merged linearity column order (visible 12 then 2 hidden masks).
    lin = parsed.group("linearity")
    assert [f.key for f in lin.fields] == [f["key"] for f in LINEARITY_FIELDS]
    assert lin.rows.default == 9 and lin.rows.label_from == "calibration_curve"
    assert len(lin.rows.seed) == 9

    #  Blank evaluate: no blocking failure, no circular reference.
    blank = WorksheetEvaluator(parsed).evaluate({}, {})
    assert blank.has_blocking_failure is False

    #  Numeric harness over the six standards + three QC rows.
    ctx = {"potency": POTENCY, "label_claim": 100}
    tp_rows = [
        {"time_min": 40, "area_1": 100000, "area_2": 101000, "area_3": 99000,
         "area_4": 100500, "area_5": 99500, "area_6": 100200},
        {"time_min": 80, "area_1": 150000, "area_2": 151000, "area_3": 149000,
         "area_4": 150500, "area_5": 149500, "area_6": 150200},
        {"time_min": 120, "area_1": 200000, "area_2": 201000, "area_3": 199000,
         "area_4": 200500, "area_5": 199500, "area_6": 200200},
    ]
    gv = {"linearity": _standard_rows_with_areas(), "timepoints": tp_rows}
    result = WorksheetEvaluator(parsed).evaluate(ctx, gv)

    lin_rows = result.rows["linearity"]
    for i in range(6):
        assert _close(lin_rows[i]["theoretical_ppm"], EXPECT_THEORETICAL[i]), (
            i, lin_rows[i]["theoretical_ppm"], EXPECT_THEORETICAL[i])
        assert _close(lin_rows[i]["observed_ppm"], EXPECT_OBSERVED[i]), (
            i, lin_rows[i]["observed_ppm"], EXPECT_OBSERVED[i])
        assert lin_rows[i]["recovery_pct"] == round(EXPECT_RECOVERY_RAW[i], 2), (
            i, lin_rows[i]["recovery_pct"], round(EXPECT_RECOVERY_RAW[i], 2))

    #  Masks tag the right rows.
    assert [lin_rows[i]["is_standard"] for i in range(9)] == [True] * 6 + [False] * 3
    assert [lin_rows[i]["is_qc"] for i in range(9)] == [False] * 6 + [True] * 3

    #  Curve fit over the six standards only (post-rounding, exact).
    slope = result.values["curve.curve_slope"]
    intercept = result.values["curve.curve_intercept"]
    correl = result.values["curve.correlation"]
    assert slope == EXPECT_SLOPE, slope
    assert intercept == EXPECT_INTERCEPT, intercept
    assert correl == EXPECT_CORREL, correl

    #  NIT 3: exactly six rows feed the fit.
    from src.domain.services.calculation.expression import evaluate as _eval
    areas = [r.get("area", EMPTY) for r in lin_rows]
    flags = [r.get("is_standard", EMPTY) for r in lin_rows]
    kept = _eval("count(where(a, m))", {"a": areas, "m": flags})
    assert kept == 6.0, kept

    #  Mask robustness: give QC rows skewing dilutions AND areas — fit unchanged.
    skew = _standard_rows_with_areas()
    for row in skew[6:]:
        row.update({"std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 1,
                    "ml_b": 1, "ml_taken": 10, "diluted_to_ml_2": 50, "area": 20_000_000})
    skewed = WorksheetEvaluator(parsed).evaluate(ctx, {"linearity": skew, "timepoints": tp_rows})
    assert skewed.values["curve.curve_slope"] == EXPECT_SLOPE
    assert skewed.values["curve.curve_intercept"] == EXPECT_INTERCEPT
    assert skewed.values["curve.correlation"] == EXPECT_CORREL

    #  Flux chain still resolves to a finite number through the re-pointed curve.
    mean_flux = result.values.get("flux.mean_flux")
    assert isinstance(mean_flux, (int, float)) and not isinstance(mean_flux, bool), mean_flux

    #  The example weight 89.73 lives only in the seeded standard rows.
    for row in lin.rows.seed[:6]:
        assert row["std_weight_mg"] == 89.73
    for row in lin.rows.seed[6:]:
        assert set(row) == {"calibration_curve", "concentration_pct"}, row
    #  No input column carries a baked default (seed drives opening values).
    for f in lin.fields:
        if f.kind.value == "input":
            assert f.default is None, f"{f.key} must not carry a default"

    print("validation OK: parse + evaluate pass; "
          f"theoretical/observed/recovery match §7; "
          f"curve slope={slope} intercept={intercept} correl={correl} over 6 standards; "
          f"mask excludes QC (n={int(kept)}); title singleton informational; "
          f"flux.mean_flux={mean_flux} finite (chain intact).")


# ─────────────────────────── DB write ───────────────────────────


async def _load() -> tuple[dict, int, str]:
    async with async_session_factory() as sess:
        row = (
            await sess.execute(select(TestTemplateModel).where(TestTemplateModel.code == CODE))
        ).scalar_one()
        return copy.deepcopy(row.definition), row.id, row.status


async def main(validate_only: bool = False) -> None:
    source_definition, row_id, status = await _load()
    assert row_id == EXPECTED_ID, f"{CODE} is id={row_id}, expected {EXPECTED_ID}"

    definition = build_mutated(source_definition)
    validate(definition)

    if validate_only:
        print("--validate-only: no DB write performed.")
        return

    async with async_session_factory() as sess:
        row = (
            await sess.execute(select(TestTemplateModel).where(TestTemplateModel.code == CODE))
        ).scalar_one()
        assert row.id == EXPECTED_ID, row.id
        row.definition = definition
        row.status = "Active"
        await sess.commit()

    async with async_session_factory() as sess:
        row = (
            await sess.execute(select(TestTemplateModel).where(TestTemplateModel.code == CODE))
        ).scalar_one()
        assert row.id == EXPECTED_ID
        assert row.status == "Active", row.status
        assert json.dumps(row.definition, sort_keys=True) == json.dumps(
            definition, sort_keys=True
        ), "re-read definition is not byte-equal to the written definition"
    print(f"wrote/updated id={row.id} ({CODE}) status={row.status} … re-read byte-equal OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()
    asyncio.run(main(validate_only=args.validate_only))
