"""
A6d — in-vitro release testing (IVRT) on a Franz diffusion cell.

Source: `Dissolution sheet_ Franz diffusion cell_Tapinarof.xls`.

Grouped under A6 because the carry-over problem is identical to dissolution —
each sampling removes receptor fluid that contained drug, so the cumulative
amount released has to add back what earlier samplings took out. Two things make
it its own variant rather than a configuration of A6a/A6b:

* **Quantitation is by calibration curve, not by a single-point standard.** Six
  calibration levels are regressed, and every sample response is read back as
  `(area - intercept) / slope`. A6a/b divide by the mean standard area, which
  assumes a line through the origin; here the intercept is 28,844 area units
  against a level-1 response of 200,754, so forcing it through zero would
  overstate the lowest timepoints by around 14 %.
* **The reportable result is a flux, not a percentage.** IVRT reports the
  Higuchi slope — cumulative amount per unit area against the square root of
  time — so the result is µg/cm²/√h and comes from a regression *down* the
  timepoint rows, one per cell.

Because flux is a regression over timepoints, timepoints have to be the row axis
and the six cells become columns, exactly as in A6.

## Derived from cached values, not from formulas

The source is a legacy `.xls`, so the dump carries cached numbers with no
formulas. Every relation below was reverse-engineered from those numbers and
checked to full displayed precision:

* `theoretical_ppm` — cal-1: 89.73/50 × 5/50 × 1/50 × 1000 × 0.9967 = 3.5773556,
  matching the sheet's 3.5773556399999995.
* `observed_ppm` — cal-1: (200754 − 28844.9)/53797.61 = 3.195478386, matching
  3.195478386493378.
* `amount_ug` — cell 1 at 40 min: (1069016 − 28844.9)/53797.61 × 7 = 135.34426,
  matching 135.34425971711383.
* the correction column — the sheet's row-*t* entry is the *previous* timepoint's
  amount × 1 mL ÷ 7 mL (cell 1 at 80 min: 135.34426 × 1/7 = 19.334894, matching
  19.334894245301975). Summing that column to timepoint *t* is the same quantity
  as `sum(prior.amount_n) * replacement / volume`, which is how it is written
  here — one expression instead of a column plus a hidden running total.

## Not in the source sheet — flagged for confirmation

The workbook stops at the correction column: it never sums the corrections, and
it computes neither flux nor percentage released. Those are added here because a
release test that stops before the release figure is not a result. Specifically:

1. **√time is taken in hours**, so flux is µg/cm²/√h — the SUPAC-SS reporting
   convention. The sheet records timepoints in minutes; if the lab reports
   µg/cm²/√min the divisor is the one field to change.
2. **Percent released** uses the recorded per-cell applied dose and the label
   claim (% w/w). The applied weights are on the sheet; the division is not.
3. **Acceptance limits** are conventional, not quoted from the sheet, which
   states none: 85–115 % QC recovery (advisory) and R ≥ 0.97 on the Higuchi
   plot (SUPAC-SS). Only the calibration correlation is blocking, since a curve
   that does not fit invalidates every number derived from it.
"""
from scripts.template_definitions._common import SeedTemplate, context_header, dilution_fields

#  Six cells is the standard Franz apparatus loading, and matches the sheet.
_CELLS = 6
_CELL_RANGE = range(1, _CELLS + 1)


def _series(prefix: str) -> str:
    """`[flux_1, flux_2, …]` — a literal list, for aggregating across cells within
    one row (as opposed to down a column, which `group.field` already gives)."""
    return "[" + ", ".join(f"{prefix}_{n}" for n in _CELL_RANGE) + "]"


# ─────────────────────────────────────────────────────────────────────
#  Calibration curve
# ─────────────────────────────────────────────────────────────────────

_CALIBRATION_GROUP = {
    "key": "calibration",
    "kind": "table",
    "label": "Calibration Standards",
    "rows": {"min": 2, "max": 10, "default": 6, "labelFrom": "level"},
    "fields": [
        {"key": "level", "kind": "input", "type": "text", "label": "Standard"},
        {"key": "nominal_pct", "kind": "input", "label": "Nominal", "unit": "%"},
        {
            "key": "weight_mg",
            "kind": "input",
            "label": "Std. Wt.",
            "unit": "mg",
            "required": True,
        },
        #  Each level carries its own chain: the sheet takes cal-1..3 through a
        #  5 mL → 50 mL intermediate and cal-4..6 straight from the primary stock
        #  (its stage-2 cells read 1 mL → 1 mL). Per-row stages express both
        #  without a second template.
        *dilution_fields("c_"),
        {
            "key": "theoretical_ppm",
            "kind": "calculated",
            "label": "Theoretical Conc.",
            "unit": "ppm",
            "expression": (
                "weight_mg / c_vol_1 * c_pip_1 / c_vol_2 * c_pip_2 / c_vol_3 "
                "* potency / 100 * 1000"
            ),
        },
        {"key": "area", "kind": "area", "label": "Area Response", "unit": "µV·s"},
        {
            "key": "observed_ppm",
            "kind": "calculated",
            "label": "Observed Conc.",
            "unit": "ppm",
            #  Read back through the fitted line, intercept included.
            "expression": "(area - curve.curve_intercept) / curve.curve_slope",
        },
        {
            "key": "recovery_pct",
            "kind": "calculated",
            "label": "% Recovery",
            "unit": "%",
            "expression": "observed_ppm / theoretical_ppm * 100",
            "rounding": {"mode": "round", "digits": 2},
        },
    ],
}

_CURVE_GROUP = {
    "key": "curve",
    "kind": "singleton",
    "label": "Regression",
    "fields": [
        {
            "key": "curve_slope",
            "kind": "calculated",
            "label": "Slope",
            "unit": "area / ppm",
            #  slope(ys, xs): response on concentration.
            "expression": "slope(calibration.area, calibration.theoretical_ppm)",
            "rounding": {"mode": "round", "digits": 2},
        },
        {
            "key": "curve_intercept",
            "kind": "calculated",
            "label": "Intercept",
            "expression": "intercept(calibration.area, calibration.theoretical_ppm)",
            "rounding": {"mode": "round", "digits": 2},
        },
        {
            "key": "correlation",
            "kind": "calculated",
            "label": "Correlation (r)",
            "expression": "correl(calibration.area, calibration.theoretical_ppm)",
            "rounding": {"mode": "round", "digits": 4},
        },
    ],
}

#  The bracketing LQC/MQC/HQC block. Theoretical concentration is an input here
#  rather than a second dilution chain: the sheet copies it across from the
#  matching calibration level, and re-deriving it would let the two drift apart.
_QC_GROUP = {
    "key": "qc",
    "kind": "table",
    "label": "Bracketing QC Standards",
    "rows": {"min": 0, "max": 24, "default": 6, "labelFrom": "level"},
    "fields": [
        {"key": "level", "kind": "input", "type": "text", "label": "QC"},
        {
            "key": "theoretical_ppm",
            "kind": "input",
            "label": "Theoretical Conc.",
            "unit": "ppm",
        },
        {"key": "area", "kind": "area", "label": "Area Response", "unit": "µV·s"},
        {
            "key": "observed_ppm",
            "kind": "calculated",
            "label": "Observed Conc.",
            "unit": "ppm",
            "expression": "(area - curve.curve_intercept) / curve.curve_slope",
        },
        {
            "key": "recovery_pct",
            "kind": "calculated",
            "label": "% Recovery",
            "unit": "%",
            "expression": "observed_ppm / theoretical_ppm * 100",
            "rounding": {"mode": "round", "digits": 2},
        },
    ],
}


# ─────────────────────────────────────────────────────────────────────
#  Cells and timepoints
# ─────────────────────────────────────────────────────────────────────

_CELLS_GROUP = {
    "key": "cells",
    "kind": "singleton",
    "label": "Cell Loading",
    "fields": [
        {
            "key": f"applied_mg_{n}",
            "kind": "input",
            "label": f"Cell {n} Applied Dose",
            "unit": "mg",
        }
        for n in _CELL_RANGE
    ],
}


def _cell_area_fields() -> list[dict]:
    return [
        {"key": f"area_{n}", "kind": "area", "label": f"Cell {n} Area", "unit": "µV·s"}
        for n in _CELL_RANGE
    ]


def _cell_calculated_fields() -> list[dict]:
    fields: list[dict] = []

    for n in _CELL_RANGE:
        fields.append(
            {
                "key": f"conc_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Conc.",
                "unit": "ppm",
                "expression": f"(area_{n} - curve.curve_intercept) / curve.curve_slope",
            }
        )
    for n in _CELL_RANGE:
        fields.append(
            {
                "key": f"amount_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Amount (uncorrected)",
                "unit": "µg",
                #  Concentration × receptor volume, times any dilution applied to
                #  the withdrawn aliquot before injection.
                "expression": (
                    f"conc_{n} * sample_vol / sample_pip * receptor_volume"
                ),
            }
        )
    for n in _CELL_RANGE:
        fields.append(
            {
                "key": f"carry_{n}",
                "kind": "calculated",
                "label": f"Cell {n} carry-over",
                "unit": "µg",
                #  Everything withdrawn at earlier timepoints, at the concentration
                #  it was withdrawn at. Equivalent to summing the sheet's
                #  single-step correction column up to this row.
                "expression": (
                    f"sum(prior.amount_{n}) * replacement_volume / receptor_volume"
                ),
            }
        )
    for n in _CELL_RANGE:
        fields.append(
            {
                "key": f"cumulative_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Cumulative",
                "unit": "µg",
                #  Unrounded. The sheet rounds nothing in this chain, and this
                #  value feeds the flux regression — rounding here would move the
                #  reported release rate rather than just its display.
                "expression": f"amount_{n} + carry_{n}",
            }
        )
    for n in _CELL_RANGE:
        fields.append(
            {
                "key": f"per_area_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Cumulative / Area",
                "unit": "µg/cm²",
                #  The Higuchi y-axis. Normalising by the donor orifice area is
                #  what makes cells with different applied doses comparable.
                #  Also unrounded: it is the regression's y-axis.
                "expression": f"cumulative_{n} / donor_area",
            }
        )
    for n in _CELL_RANGE:
        fields.append(
            {
                "key": f"released_pct_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Released",
                "unit": "%",
                #  Applied dose × % w/w claim × 1000 = µg of drug applied.
                "expression": (
                    f"cumulative_{n} / (cells.applied_mg_{n} * label_claim / 100 * 1000) * 100"
                ),
                "rounding": {"mode": "round", "digits": 2},
            }
        )
    return fields


_TIMEPOINT_GROUP = {
    "key": "timepoints",
    "kind": "sequence",
    "label": "Sampling Timepoints",
    "rows": {"min": 2, "max": 12, "default": 6, "labelFrom": "time_min"},
    "fields": [
        #  Numeric, not text as in A6 — the flux regression takes its square root.
        {"key": "time_min", "kind": "input", "label": "Time", "unit": "min", "required": True},
        *_cell_area_fields(),
        {
            "key": "sqrt_hours",
            "kind": "calculated",
            "label": "√Time",
            "unit": "√h",
            #  The regression's x-axis, so left unrounded for the same reason.
            "expression": "sqrt(time_min / 60)",
        },
        *_cell_calculated_fields(),
        {
            "key": "mean_per_area",
            "kind": "calculated",
            "label": "Mean Cumulative / Area",
            "unit": "µg/cm²",
            "expression": f"mean({_series('per_area')})",
            "rounding": {"mode": "round", "digits": 3},
        },
        {
            "key": "rsd_per_area",
            "kind": "calculated",
            "label": "%RSD Across Cells",
            "unit": "%",
            "expression": f"rsd({_series('per_area')})",
            "rounding": {"mode": "round", "digits": 1},
        },
    ],
}


def _flux_fields() -> list[dict]:
    fields: list[dict] = []
    for n in _CELL_RANGE:
        fields.append(
            {
                "key": f"flux_{n}",
                "kind": "calculated",
                "label": f"Cell {n} Flux",
                "unit": "µg/cm²/√h",
                #  Higuchi slope down the timepoint rows for this cell.
                "expression": f"slope(timepoints.per_area_{n}, timepoints.sqrt_hours)",
                "rounding": {"mode": "round", "digits": 2},
            }
        )
    for n in _CELL_RANGE:
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
                "expression": f"mean({_series('flux')})",
                "rounding": {"mode": "round", "digits": 2},
            },
            {
                "key": "rsd_flux",
                "kind": "calculated",
                "label": "%RSD of Flux",
                "unit": "%",
                "expression": f"rsd({_series('flux')})",
                "rounding": {"mode": "round", "digits": 1},
            },
            {
                "key": "min_fit",
                "kind": "calculated",
                "label": "Poorest Higuchi Fit",
                "expression": f"min({_series('fit')})",
                "rounding": {"mode": "round", "digits": 4},
            },
        ]
    )
    return fields


_FLUX_GROUP = {
    "key": "flux",
    "kind": "singleton",
    "label": "Release Rate",
    "fields": _flux_fields(),
}


A6D_DEFINITION = {
    "resultRef": "flux.mean_flux",
    "context": context_header(
        #  Label claim is a % w/w for a topical, and is used as such below.
        avg_weight=False,
        extra=[
            {
                "key": "potency",
                "kind": "context",
                "label": "Standard Potency",
                "unit": "%",
                "default": 100,
                "overridable": True,
            },
            {
                "key": "membrane",
                "kind": "context",
                "type": "text",
                "label": "Membrane Type / Make",
                "overridable": True,
            },
            {
                "key": "membrane_lot",
                "kind": "context",
                "type": "text",
                "label": "Membrane B. No.",
                "overridable": True,
            },
            {
                "key": "receptor_media",
                "kind": "context",
                "type": "text",
                "label": "Receptor Media",
                "overridable": True,
            },
            {
                "key": "receptor_volume",
                "kind": "context",
                "label": "Total Receptor Volume",
                "unit": "mL",
                "default": 7,
                "overridable": True,
            },
            {
                "key": "replacement_volume",
                "kind": "context",
                "label": "Media Replacement Volume",
                "unit": "mL",
                "default": 1,
                "overridable": True,
            },
            {
                "key": "sample_pip",
                "kind": "context",
                "label": "Withdrawn Aliquot",
                "unit": "mL",
                "default": 1,
                "overridable": True,
            },
            {
                "key": "sample_vol",
                "kind": "context",
                "label": "Diluted to",
                "unit": "mL",
                "default": 1,
                "overridable": True,
            },
            {
                "key": "donor_area",
                "kind": "context",
                "label": "Donor Chamber Area",
                "unit": "cm²",
                "default": 1.76,
                "overridable": True,
            },
            {
                "key": "temperature_c",
                "kind": "context",
                "label": "Temperature",
                "unit": "°C",
                "default": 32,
                "overridable": True,
            },
        ],
    ),
    "groups": [
        _CALIBRATION_GROUP,
        _CURVE_GROUP,
        _QC_GROUP,
        _CELLS_GROUP,
        _TIMEPOINT_GROUP,
        _FLUX_GROUP,
    ],
    "criteria": [
        {
            "key": "calibration_correlation",
            "label": "Correlation of the calibration curve",
            "target": "curve.correlation",
            "operator": "gte",
            #  Blocking: every reported number is read off this line.
            "limit": 0.99,
            "severity": "blocking",
            "limitText": "NLT 0.99",
        },
        {
            "key": "qc_recovery_low",
            "label": "Lowest bracketing QC recovery",
            "target": "min(qc.recovery_pct)",
            "operator": "gte",
            "limit": 85.0,
            #  Advisory — the source sheet states no QC limits, so this is the
            #  conventional window pending lab confirmation.
            "severity": "advisory",
            "limitText": "NLT 85 % (convention)",
        },
        {
            "key": "qc_recovery_high",
            "label": "Highest bracketing QC recovery",
            "target": "max(qc.recovery_pct)",
            "operator": "lte",
            "limit": 115.0,
            "severity": "advisory",
            "limitText": "NMT 115 % (convention)",
        },
        {
            "key": "higuchi_linearity",
            "label": "Poorest per-cell Higuchi correlation",
            "target": "flux.min_fit",
            "operator": "gte",
            "limit": 0.97,
            "severity": "advisory",
            "limitText": "NLT 0.97 (SUPAC-SS)",
        },
        {
            "key": "flux_precision",
            "label": "%RSD of flux across cells",
            "target": "flux.rsd_flux",
            "operator": "lte",
            "limit": 15.0,
            "severity": "advisory",
            "limitText": "NMT 15 % (convention)",
        },
    ],
}

A6D = SeedTemplate(
    code="TPL-A6D-0001",
    name="In-Vitro Release (Franz Diffusion Cell)",
    archetype="A6d",
    result_unit="µg/cm²/√h",
    test_code="TST-IVRT",
    test_name="In-Vitro Release Rate (IVRT)",
    test_type="Quantitative",
    definition=A6D_DEFINITION,
)

TEMPLATES = [A6D]
