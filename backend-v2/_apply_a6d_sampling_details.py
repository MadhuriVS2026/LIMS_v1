"""Duplicate TPL-A6D-0001 into TPL-A6D-0002 (Draft) adding a blank per-cell
"Sampling details" sub-section, with a single cell range that mirrors across
every per-cell group.

Reads the LIVE definition of TPL-A6D-0001 from lims.db (source of truth) and
deep-copies it. Every per-cell group in this template -- `cells`, `timepoints`
(area + the full calculated chain + the cross-cell `_series(...)` aggregates),
`flux` (flux/fit + the `_series(...)` aggregates), and the NEW `sampling_details`
sub-section -- is regenerated from a SINGLE module constant `CELL_RANGE`. That
one constant is the add-column / cross-section "mirror" contract: changing only
`CELL_RANGE` extends (or trims) the `*_{n}` columns in all four per-cell groups
together, keeping the cell count in lock-step. A dry-run at range(1, 8)
demonstrates the mirror (see `--mirror-demo`) without touching the DB.

At the default `CELL_RANGE = range(1, 7)` (six Franz cells, matching the source
template) the regenerated per-cell groups are byte-identical to the live
TPL-A6D-0001 definition, so the ONLY difference between the duplicate and its
source is the inserted `sampling_details` group. This is asserted before writing.

The per-cell field generators below mirror the seed module
`scripts/template_definitions/a6d_franz_ivrt.py` exactly (same keys, labels,
units, expressions, rounding and field order); they are reproduced here,
parameterised by `CELL_RANGE`, so the single range genuinely drives the mirror
rather than relying on the verbatim copied groups.

Validates with the service's two-pass gate (TemplateDefinition.parse +
WorksheetEvaluator.evaluate({}, {})) before writing, then writes a new Draft row
and asserts byte-equality on re-read. Pattern follows `_apply_cu30_kedit.py`.
Idempotent: aborts without writing if a TPL-A6D-0002 row already exists.

The example figures the user gave (257.0 / 229.4 / 227.0 / 218.2 / 254.3 /
257.2) are EXAMPLES ONLY and are NOT stored -- the Sample-weight fields are
blank reusable inputs (no `default`).
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

SOURCE_CODE = "TPL-A6D-0001"
NEW_CODE = "TPL-A6D-0002"
NEW_NAME = "In-Vitro Release (Franz Diffusion Cell) — with Sampling Details"

#  THE single cell range: the add-column / cross-section mirror contract.
#  Changing only this one line regenerates the `*_{n}` columns in every per-cell
#  group together (sampling_details, cells, timepoints, flux) and widens the
#  cross-cell `_series(...)` aggregates. The default Franz loading is 6 cells,
#  matching the source template TPL-A6D-0001.
CELL_RANGE = range(1, 7)


# ─────────────────────────────────────────────────────────────────────
#  Per-cell field generators driven by the single CELL_RANGE.
#  These mirror scripts/template_definitions/a6d_franz_ivrt.py exactly.
# ─────────────────────────────────────────────────────────────────────

def _series(prefix: str, cell_range: range) -> str:
    """`[flux_1, flux_2, …]` — a literal list for aggregating across cells."""
    return "[" + ", ".join(f"{prefix}_{n}" for n in cell_range) + "]"


def build_sampling_details_group(cell_range: range) -> dict:
    """The NEW sub-section: one blank per-cell Sample-weight input per cell.

    No `default` key -> blank reusable input. The field labels carry the cell
    identity (Cell {n}), matching how the existing `cells` group renders.
    """
    return {
        "key": "sampling_details",
        "kind": "singleton",
        "label": "Sampling details",
        "fields": [
            {
                "key": f"sample_weight_mg_{n}",
                "kind": "input",
                "type": "number",
                "label": f"Cell {n} Sample Weight",
                "unit": "mg",
                # no "default" -> blank reusable input
            }
            for n in cell_range
        ],
    }


def build_cells_fields(cell_range: range) -> list[dict]:
    return [
        {
            "key": f"applied_mg_{n}",
            "kind": "input",
            "label": f"Cell {n} Applied Dose",
            "unit": "mg",
        }
        for n in cell_range
    ]


def _cell_area_fields(cell_range: range) -> list[dict]:
    return [
        {"key": f"area_{n}", "kind": "area", "label": f"Cell {n} Area", "unit": "µV·s"}
        for n in cell_range
    ]


def _cell_calculated_fields(cell_range: range) -> list[dict]:
    fields: list[dict] = []
    for n in cell_range:
        fields.append(
            {
                "key": f"conc_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Conc.",
                "unit": "ppm",
                "expression": f"(area_{n} - curve.curve_intercept) / curve.curve_slope",
            }
        )
    for n in cell_range:
        fields.append(
            {
                "key": f"amount_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Amount (uncorrected)",
                "unit": "µg",
                "expression": f"conc_{n} * sample_vol / sample_pip * receptor_volume",
            }
        )
    for n in cell_range:
        fields.append(
            {
                "key": f"carry_{n}",
                "kind": "calculated",
                "label": f"Cell {n} carry-over",
                "unit": "µg",
                "expression": f"sum(prior.amount_{n}) * replacement_volume / receptor_volume",
            }
        )
    for n in cell_range:
        fields.append(
            {
                "key": f"cumulative_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Cumulative",
                "unit": "µg",
                "expression": f"amount_{n} + carry_{n}",
            }
        )
    for n in cell_range:
        fields.append(
            {
                "key": f"per_area_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Cumulative / Area",
                "unit": "µg/cm²",
                "expression": f"cumulative_{n} / donor_area",
            }
        )
    for n in cell_range:
        fields.append(
            {
                "key": f"released_pct_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Released",
                "unit": "%",
                "expression": (
                    f"cumulative_{n} / (cells.applied_mg_{n} * label_claim / 100 * 1000) * 100"
                ),
                "rounding": {"mode": "round", "digits": 2},
            }
        )
    return fields


def build_timepoints_fields(cell_range: range) -> list[dict]:
    """Full `timepoints` field list in the live/seed order: time_min, areas,
    sqrt_hours, calculated chain, then the two cross-cell aggregates."""
    return [
        {"key": "time_min", "kind": "input", "label": "Time", "unit": "min", "required": True},
        *_cell_area_fields(cell_range),
        {
            "key": "sqrt_hours",
            "kind": "calculated",
            "label": "√Time",
            "unit": "√h",
            "expression": "sqrt(time_min / 60)",
        },
        *_cell_calculated_fields(cell_range),
        {
            "key": "mean_per_area",
            "kind": "calculated",
            "label": "Mean Cumulative / Area",
            "unit": "µg/cm²",
            "expression": f"mean({_series('per_area', cell_range)})",
            "rounding": {"mode": "round", "digits": 3},
        },
        {
            "key": "rsd_per_area",
            "kind": "calculated",
            "label": "%RSD Across Cells",
            "unit": "%",
            "expression": f"rsd({_series('per_area', cell_range)})",
            "rounding": {"mode": "round", "digits": 1},
        },
    ]


def build_flux_fields(cell_range: range) -> list[dict]:
    fields: list[dict] = []
    for n in cell_range:
        fields.append(
            {
                "key": f"flux_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Flux",
                "unit": "µg/cm²/√h",
                "expression": f"slope(timepoints.per_area_{n}, timepoints.sqrt_hours)",
                "rounding": {"mode": "round", "digits": 2},
            }
        )
    for n in cell_range:
        fields.append(
            {
                "key": f"fit_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Higuchi r",
                "expression": f"correl(timepoints.per_area_{n}, timepoints.sqrt_hours)",
                "rounding": {"mode": "round", "digits": 4},
            }
        )
    fields.extend(
        [
            {
                "key": "mean_flux",
                "kind": "calculated",
                "label": "Mean Flux",
                "unit": "µg/cm²/√h",
                "expression": f"mean({_series('flux', cell_range)})",
                "rounding": {"mode": "round", "digits": 2},
            },
            {
                "key": "rsd_flux",
                "kind": "calculated",
                "label": "%RSD of Flux",
                "unit": "%",
                "expression": f"rsd({_series('flux', cell_range)})",
                "rounding": {"mode": "round", "digits": 1},
            },
            {
                "key": "min_fit",
                "kind": "calculated",
                "label": "Poorest Higuchi Fit",
                "expression": f"min({_series('fit', cell_range)})",
                "rounding": {"mode": "round", "digits": 4},
            },
        ]
    )
    return fields


# ─────────────────────────────────────────────────────────────────────
#  Apply the single CELL_RANGE across every per-cell group.
# ─────────────────────────────────────────────────────────────────────

def regenerate_per_cell_groups(definition: dict, cell_range: range) -> dict:
    """Rewrite the per-cell field lists of `cells`, `timepoints` and `flux`
    from the single `cell_range`, so a range change mirrors across all of them.
    Non-per-cell group metadata (kind/label/rows) is preserved as-is."""
    by_key = {g["key"]: g for g in definition["groups"]}
    by_key["cells"]["fields"] = build_cells_fields(cell_range)
    by_key["timepoints"]["fields"] = build_timepoints_fields(cell_range)
    by_key["flux"]["fields"] = build_flux_fields(cell_range)
    return definition


def add_sampling_details(definition: dict, cell_range: range) -> dict:
    """Insert the sampling_details group immediately before `timepoints`."""
    groups = definition["groups"]
    if any(g["key"] == "sampling_details" for g in groups):
        raise RuntimeError("definition already has a 'sampling_details' group")
    tp_index = next(i for i, g in enumerate(groups) if g["key"] == "timepoints")
    groups.insert(tp_index, build_sampling_details_group(cell_range))
    return definition


def build_duplicate_definition(source_definition: dict, cell_range: range) -> dict:
    """The full duplicate definition: deep-copy of the live source, every
    per-cell group regenerated from `cell_range`, plus the new sampling_details
    sub-section inserted before `timepoints`."""
    definition = copy.deepcopy(source_definition)
    regenerate_per_cell_groups(definition, cell_range)
    add_sampling_details(definition, cell_range)
    return definition


def validate(definition: dict) -> None:
    """The service's two-pass gate: parse + dry-run evaluate on blank inputs."""
    parsed = TemplateDefinition.parse(definition)
    result = WorksheetEvaluator(parsed).evaluate({}, {})
    assert result.has_blocking_failure is False, "blank evaluate reported a blocking failure"
    print("validation OK: parse + evaluate({}, {}) succeeded, no blocking failure")


def _per_cell_counts(definition: dict) -> dict:
    by_key = {g["key"]: g for g in definition["groups"]}

    def count(group_key: str, prefix: str) -> int:
        return sum(
            1
            for f in by_key[group_key]["fields"]
            if f["key"].startswith(prefix)
            and f["key"][len(prefix):].isdigit()
        )

    return {
        "sampling_details.sample_weight_mg": count("sampling_details", "sample_weight_mg_"),
        "cells.applied_mg": count("cells", "applied_mg_"),
        "timepoints.area": count("timepoints", "area_"),
        "flux.flux": count("flux", "flux_"),
    }


async def _load_source() -> tuple[dict, int, bool]:
    """Return (source_definition, source_test_id, new_code_exists)."""
    async with async_session_factory() as sess:
        src = (
            await sess.execute(
                select(TestTemplateModel).where(TestTemplateModel.code == SOURCE_CODE)
            )
        ).scalar_one()
        existing_new = (
            await sess.execute(
                select(TestTemplateModel).where(TestTemplateModel.code == NEW_CODE)
            )
        ).scalar_one_or_none()
        return copy.deepcopy(src.definition), src.test_id, existing_new is not None


async def mirror_demo(cells: int) -> None:
    """Dry-run: rebuild the duplicate at range(1, cells+1) from the SAME single
    CELL_RANGE path used for the real write, prove every per-cell group (and the
    _series aggregates) picks up the new index, and that it still parses +
    evaluates. NO DB write."""
    source_definition, _test_id, _exists = await _load_source()
    rng = range(1, cells + 1)
    definition = build_duplicate_definition(source_definition, rng)
    counts = _per_cell_counts(definition)

    top = cells  # highest cell index
    by_key = {g["key"]: g for g in definition["groups"]}
    keys = {f["key"] for grp in definition["groups"] for f in grp["fields"]}
    expected_fields = {
        f"sample_weight_mg_{top}",
        f"applied_mg_{top}",
        f"area_{top}",
        f"conc_{top}",
        f"amount_{top}",
        f"carry_{top}",
        f"cumulative_{top}",
        f"per_area_{top}",
        f"released_pct_{top}",
        f"flux_{top}",
        f"fit_{top}",
    }
    missing = expected_fields - keys
    assert not missing, f"mirror FAILED: missing fields {sorted(missing)}"
    assert all(v == cells for v in counts.values()), f"mirror FAILED: counts {counts}"

    mean_flux_expr = next(
        f["expression"] for f in by_key["flux"]["fields"] if f["key"] == "mean_flux"
    )
    assert f"flux_{top}" in mean_flux_expr, "mirror FAILED: _series aggregate missing new index"

    validate(definition)
    print(f"MIRROR DEMO range(1,{cells + 1}): all per-cell groups mirrored, counts={counts}")
    print(f"  mean_flux series includes flux_{top}: {mean_flux_expr}")
    print("  parse + evaluate({}, {}) OK; NO DB write performed.")


async def main(validate_only: bool = False) -> None:
    source_definition, source_test_id, new_code_exists = await _load_source()

    if new_code_exists:
        print(f"{NEW_CODE} already exists; aborting without write.")
        return

    definition = build_duplicate_definition(source_definition, CELL_RANGE)

    #  At the default range the ONLY change vs the live source must be the added
    #  sampling_details group: regenerating the per-cell groups must reproduce
    #  the source byte-for-byte. Assert that so the mirror rewrite never silently
    #  alters the duplicate's existing sections.
    check = copy.deepcopy(definition)
    check["groups"] = [g for g in check["groups"] if g["key"] != "sampling_details"]
    assert json.dumps(check, sort_keys=True) == json.dumps(
        source_definition, sort_keys=True
    ), "regenerated per-cell groups differ from the live source (only sampling_details may change)"
    print("byte-equal check OK: duplicate == source + sampling_details group only")

    validate(definition)

    counts = _per_cell_counts(definition)
    assert len(set(counts.values())) == 1, f"per-cell parity broken: {counts}"
    print(f"per-cell parity OK across all groups: {counts}")

    if validate_only:
        print("--validate-only: no DB write performed.")
        return

    async with async_session_factory() as sess:
        row = TestTemplateModel(
            code=NEW_CODE,
            name=NEW_NAME,
            archetype="A6d",
            test_id=source_test_id,
            version=1,
            status="Draft",
            result_unit="µg/cm²/√h",
            definition=definition,
            approved_by=None,
            approved_at=None,
            created_by="seed",
            modified_by="seed",
        )
        sess.add(row)
        await sess.commit()
        new_id = row.id

    async with async_session_factory() as sess:
        new = (
            await sess.execute(
                select(TestTemplateModel).where(TestTemplateModel.code == NEW_CODE)
            )
        ).scalar_one()
        assert json.dumps(new.definition, sort_keys=True) == json.dumps(
            definition, sort_keys=True
        ), "re-read definition is not byte-equal to the written definition"
    print(f"wrote {NEW_CODE} id={new_id} status=Draft; re-read byte-equal OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument(
        "--mirror-demo",
        type=int,
        metavar="CELLS",
        help="dry-run: rebuild the duplicate at this cell count to demonstrate the "
        "cross-section mirror; makes NO DB write",
    )
    args = ap.parse_args()
    if args.mirror_demo is not None:
        asyncio.run(mirror_demo(args.mirror_demo))
    else:
        asyncio.run(main(validate_only=args.validate_only))
