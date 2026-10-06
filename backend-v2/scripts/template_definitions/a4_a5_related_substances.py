"""
A4 — related substances against an impurity standard, and A5 — area normalisation.

These are the four workbooks whose formulas `xlrd` silently hid (it returns only
cached values for legacy `.xls`), recovered by driving Excel via COM. Three
behaviours from those sheets are load-bearing and easy to get wrong:

* **RRF direction is a mode, not a constant.** The same relative response factor
  is applied as a multiplier in some methods and a divisor in others, and the
  sheets carry a dropdown for it. Guessing one direction would misreport every
  impurity by the square of the factor.
* **Below-LOQ rows report `BLQ`, not a number.** A value under the limit of
  quantitation is not a measurement, so it must not print as one.
* **The total sums already-rounded rows** (`SUM(ROUND(...,3))`), not the rounded
  sum. Three impurities at 0.0004 total 0.000, not 0.001. Reproducing this
  ordering matters in the third decimal of a reported impurity total.

**A5** is the same sheet without a weighed standard: each peak is expressed as a
percentage of the total peak area, so it needs no concentration chain at all.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
    dilution_fields,
    replicate_area_group,
    sample_chain_terms,
    standard_chain_terms,
    standard_group,
    standard_statistics_group,
    sst_rsd_criterion,
)

_RRF_MULTIPLY = "RRF (multiplication factor)"
_RRF_DIVIDE = "RRF (division factor)"

#  Applied to the raw percentage. `rrf` defaults to 1, so a method that does not
#  use response factors needs no special case.
_RRF_APPLIED = f'if(rrf_mode = "{_RRF_MULTIPLY}", pct_uncorrected * rrf, pct_uncorrected / rrf)'


# ─────────────────────────────────────────────────────────────────────
#  A4 — Related substances against an impurity standard
# ─────────────────────────────────────────────────────────────────────

A4_DEFINITION = {
    "resultRef": "summary.total_impurities",
    "context": context_header(
        extra=[
            {
                "key": "rrf_mode",
                "kind": "context",
                "type": "text",
                "label": "RRF Application",
                "default": _RRF_MULTIPLY,
                "overridable": True,
                "options": [_RRF_MULTIPLY, _RRF_DIVIDE],
            },
            {
                "key": "main_peak_rt",
                "kind": "context",
                "label": "Main Peak RT",
                "unit": "min",
                "overridable": True,
            },
        ]
    ),
    "groups": [
        #  The impurity standard is weighed and diluted like any standard, but the
        #  MW correction matters more here: many impurity standards are salts
        #  where the parent is not.
        standard_group(
            label="Reference Standard Details", conc_label="Standard Concentration"
        ),
        #  Second, independent reference standard (same fields + its own
        #  Standard Concentration). Recorded alongside the first; the impurity
        #  calculation still runs against `standard` (the first).
        standard_group(
            key="standard_2",
            label="Reference Standard 2 Details",
            conc_label="Standard Concentration",
        ),
        #  Free-text title for the first replicate set (alphanumeric).
        {
            "key": "sri1_header",
            "kind": "singleton",
            "label": "Standard Replicate Injections",
            "fields": [
                {"key": "title", "kind": "input", "type": "text", "label": "Title"},
            ],
        },
        replicate_area_group(label="Standard Replicate Injections"),
        standard_statistics_group(),
        #  A4-only: a second, independent replicate-injection set with its own
        #  Mean/SD/%RSD, shown directly below the first.
        #  Free-text title for the second replicate set (alphanumeric).
        {
            "key": "sri2_header",
            "kind": "singleton",
            "label": "Standard Replicate Injections 2",
            "fields": [
                {"key": "title", "kind": "input", "type": "text", "label": "Title"},
            ],
        },
        replicate_area_group(
            key="std_areas_2",
            label="Standard Replicate Injections 2",
            stats_group="stats_2",
        ),
        {
            "key": "stats_2",
            "kind": "singleton",
            "label": "Standard Statistics 2",
            "fields": [
                {"key": "mean_std", "kind": "calculated", "label": "Mean STD Area",
                 "expression": "mean(std_areas_2.area)"},
                {"key": "sd_std", "kind": "calculated", "label": "SD",
                 "expression": "sd(std_areas_2.area)"},
                {"key": "rsd_std", "kind": "calculated", "label": "%RSD", "unit": "%",
                 "expression": "rsd(std_areas_2.area)"},
            ],
        },
        {
            "key": "sample_prep",
            "kind": "singleton",
            "label": "Sample Preparation",
            "fields": [
                {
                    "key": "sample_weight",
                    "kind": "input",
                    "label": "Sample Wt.",
                    "unit": "mg",
                    "required": True,
                },
                *dilution_fields("s_"),
            ],
        },
        {
            "key": "impurities",
            "kind": "table",
            "label": "Impurities",
            "rows": {"min": 1, "max": 40, "default": 5, "labelFrom": "name"},
            "fields": [
                {"key": "name", "kind": "input", "type": "text", "label": "Impurity"},
                {"key": "rt", "kind": "input", "label": "RT", "unit": "min"},
                {
                    "key": "rrf",
                    "kind": "input",
                    "label": "RRF",
                    "default": 1,
                    #  1 is the neutral value in both modes, so a method without
                    #  response factors needs no branch.
                },
                {
                    "key": "loq",
                    "kind": "input",
                    "label": "LOQ",
                    "unit": "%",
                    "default": 0.05,
                },
                {"key": "area_1", "kind": "area", "label": "Area 1", "unit": "µV·s"},
                {"key": "area_2", "kind": "area", "label": "Area 2", "unit": "µV·s"},
                {
                    "key": "avg_area",
                    "kind": "calculated",
                    "label": "Avg. Area",
                    "expression": "mean([area_1, area_2])",
                },
                {
                    "key": "rrt",
                    "kind": "calculated",
                    "label": "RRT",
                    "expression": "rt / main_peak_rt",
                    "rounding": {"mode": "round", "digits": 3},
                },
                {
                    "key": "pct_uncorrected",
                    "kind": "calculated",
                    "label": "% (before RRF)",
                    "unit": "%",
                    "expression": (
                        f"avg_area / stats.mean_std * {standard_chain_terms()} "
                        #  Qualified: the prep fields live in `sample_prep`, and a
                        #  bare name would only resolve within this impurity row.
                        f"* {sample_chain_terms(group='sample_prep')} "
                        "* standard.potency / 100 "
                        "* standard.mw_base / standard.mw_salt "
                        "* 100"
                    ),
                },
                {
                    "key": "pct",
                    "kind": "calculated",
                    "label": "% w/w",
                    "unit": "%",
                    "expression": _RRF_APPLIED,
                    #  Rounded HERE, and the total sums these rounded values —
                    #  reproducing the sheet's SUM(ROUND(...)) ordering.
                    "rounding": {"mode": "round", "digits": 3},
                },
                {
                    "key": "pct_for_total",
                    "kind": "calculated",
                    "label": "% counted in total",
                    "unit": "%",
                    #  Below-LOQ rows contribute nothing. This is the common
                    #  pharmacopoeial convention but IS a convention — flagged for
                    #  lab confirmation rather than assumed silently.
                    "expression": "if(pct < loq, 0, pct)",
                },
                {
                    "key": "reported",
                    "kind": "calculated",
                    "label": "Reported",
                    #  Text, not a number: a value under the LOQ is not a
                    #  measurement and must not print as one.
                    "expression": 'if(pct < loq, "BLQ", pct)',
                },
            ],
        },
        {
            "key": "summary",
            "kind": "singleton",
            "label": "Summary",
            "fields": [
                #  Guarded against an untouched sheet. `sum([])` is 0 by Excel
                #  semantics, so without this a fresh worksheet would report
                #  "Total impurities: 0.000 %" — a positive claim that no
                #  impurities are present, from an analysis nobody has run.
                {
                    "key": "max_single_impurity",
                    "kind": "calculated",
                    "label": "Single Maximum Impurity",
                    "unit": "%",
                    "expression": (
                        "if(isblank(mean(impurities.pct)), blank(), "
                        "max(impurities.pct_for_total))"
                    ),
                    "rounding": {"mode": "round", "digits": 3},
                },
                {
                    "key": "total_impurities",
                    "kind": "calculated",
                    "label": "Total Impurities",
                    "unit": "%",
                    #  Sum of already-rounded rows, per the source sheet.
                    "expression": (
                        "if(isblank(mean(impurities.pct)), blank(), "
                        "sum(impurities.pct_for_total))"
                    ),
                    "rounding": {"mode": "round", "digits": 3},
                },
            ],
        },
    ],
    "criteria": [
        sst_rsd_criterion(),
        {
            "key": "single_max",
            "label": "Single maximum impurity",
            "target": "max(impurities.pct_for_total)",
            "operator": "lte",
            "limit": 0.2,
            "severity": "advisory",
            "limitText": "NMT 0.2 %",
        },
        {
            "key": "total_max",
            "label": "Total impurities",
            "target": "sum(impurities.pct_for_total)",
            "operator": "lte",
            "limit": 1.0,
            "severity": "advisory",
            "limitText": "NMT 1.0 %",
        },
    ],
}

A4 = SeedTemplate(
    code="TPL-A4-0001",
    name="Related Substances by HPLC (against impurity standard)",
    archetype="A4",
    result_unit="%",
    test_code="TST-RS",
    test_name="Related Substances by HPLC",
    test_type="Quantitative",
    definition=A4_DEFINITION,
)


# ─────────────────────────────────────────────────────────────────────
#  A5 — Area normalisation
# ─────────────────────────────────────────────────────────────────────

A5_DEFINITION = {
    "resultRef": "summary.total_impurities",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {
                "key": "rrf_mode",
                "kind": "context",
                "type": "text",
                "label": "RRF Application",
                "default": _RRF_MULTIPLY,
                "overridable": True,
                "options": [_RRF_MULTIPLY, _RRF_DIVIDE],
            },
        ],
    ),
    "groups": [
        #  Sample preparation header: average vial weight, sample weight and the
        #  dilution volumes. Recorded for the sheet; the normalisation maths does
        #  not use them, so they carry no formula.
        {
            "key": "sample_prep",
            "kind": "singleton",
            "label": "Sample Preparation",
            "fields": [
                {"key": "avg_wt", "kind": "input", "label": "Av. Wt.", "unit": "mg"},
                {"key": "sample_weight", "kind": "input", "label": "Sample Wt.", "unit": "mg"},
                {"key": "vol_1", "kind": "input", "label": "Vol 1", "unit": "mL", "default": 1},
                {"key": "vol_2", "kind": "input", "label": "Vol 2", "unit": "mL", "default": 1},
                {"key": "vol_3", "kind": "input", "label": "Vol 3", "unit": "mL", "default": 1},
            ],
        },
        {
            "key": "main",
            "kind": "singleton",
            "label": "Main Peak",
            "fields": [
                {"key": "rt", "kind": "input", "label": "Main Peak RT", "unit": "min"},
                {"key": "area", "kind": "area",
                 "label": "Main Peak Area in Test solution", "unit": "µV·s"},
            ],
        },
        #  Total area lives in its own group rather than in `summary`. Dependencies
        #  are tracked at group granularity, so putting it alongside the totals
        #  would make `peaks` depend on `summary` while `summary` depends on
        #  `peaks` — a genuine cycle the evaluator would (correctly) reject.
        {
            "key": "normalisation",
            "kind": "singleton",
            "label": "Normalisation Basis",
            "fields": [
                {
                    "key": "total_area",
                    "kind": "calculated",
                    "label": "Total Area",
                    #  Includes the main peak — normalising against the impurities
                    #  alone would inflate every result enormously.
                    "expression": "sum(peaks.area) + main.area",
                },
            ],
        },
        {
            "key": "peaks",
            "kind": "table",
            "label": "Impurity Peaks",
            "rows": {"min": 1, "max": 40, "default": 5, "labelFrom": "name"},
            "fields": [
                {"key": "name", "kind": "input", "type": "text", "label": "Impurity Name"},
                {"key": "rt", "kind": "input", "label": "RT", "unit": "min"},
                {"key": "area", "kind": "area", "label": "Area", "unit": "µV·s"},
                {
                    "key": "rrt",
                    "kind": "calculated",
                    "label": "RRT",
                    "expression": "rt / main.rt",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {"key": "rrf", "kind": "input", "label": "RRF", "default": 1},
                {
                    "key": "loq",
                    "kind": "input",
                    "label": "LOQ",
                    "unit": "%",
                    "default": 0.05,
                    "hidden": True,
                },
                {
                    #  Intermediate: still computed (feeds `pct`) but hidden from
                    #  the table to keep the visible columns to the reportables.
                    "key": "pct_uncorrected",
                    "kind": "calculated",
                    "label": "% area (before RRF)",
                    "unit": "%",
                    "expression": "area / normalisation.total_area * 100",
                    "hidden": True,
                },
                {
                    "key": "pct",
                    "kind": "calculated",
                    "label": "% Impurity",
                    "unit": "%",
                    "expression": _RRF_APPLIED,
                    "rounding": {"mode": "round", "digits": 3},
                },
                {
                    #  Feeds the total; hidden from the table.
                    "key": "pct_for_total",
                    "kind": "calculated",
                    "label": "% counted in total",
                    "unit": "%",
                    "expression": "if(pct < loq, 0, pct)",
                    "hidden": True,
                },
                {
                    #  BLQ display helper; hidden from the table.
                    "key": "reported",
                    "kind": "calculated",
                    "label": "Reported",
                    "expression": 'if(pct < loq, "BLQ", pct)',
                    "hidden": True,
                },
            ],
        },
        {
            "key": "summary",
            "kind": "singleton",
            "label": "Summary",
            "fields": [
                #  Single Maximum Impurity is entered manually by the analyst.
                {
                    "key": "max_single_impurity",
                    "kind": "input",
                    "label": "Single Maximum Impurity",
                    "unit": "%",
                },
                #  Total Impurities = sum of the displayed % Impurity column.
                #  Guarded so an untouched sheet does not report 0.000 %.
                {
                    "key": "total_impurities",
                    "kind": "calculated",
                    "label": "Total Impurities",
                    "unit": "%",
                    "expression": (
                        "if(isblank(mean(peaks.pct)), blank(), sum(peaks.pct))"
                    ),
                    "rounding": {"mode": "round", "digits": 3},
                },
            ],
        },
    ],
    "criteria": [
        {
            "key": "single_max",
            "label": "Single maximum impurity",
            "target": "max(peaks.pct_for_total)",
            "operator": "lte",
            "limit": 0.2,
            "severity": "advisory",
            "limitText": "NMT 0.2 %",
        },
        {
            "key": "total_max",
            "label": "Total impurities",
            "target": "sum(peaks.pct_for_total)",
            "operator": "lte",
            "limit": 1.0,
            "severity": "advisory",
            "limitText": "NMT 1.0 %",
        },
    ],
}

A5 = SeedTemplate(
    code="TPL-A5-0001",
    name="Related Substances by Area Normalisation",
    archetype="A5",
    result_unit="%",
    test_code="TST-RSAN",
    test_name="Related Substances by Area Normalisation",
    test_type="Quantitative",
    definition=A5_DEFINITION,
)

TEMPLATES = [A4, A5]
