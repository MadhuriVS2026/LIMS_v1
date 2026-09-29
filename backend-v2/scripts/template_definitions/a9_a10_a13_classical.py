"""
A9 titrimetry, A10 gravimetric (two variants), A13 trace/nitrosamine impurities.

A9 and A10 need no chromatography at all, which is why they have no standard
block or area fields — a template forcing them through the HPLC shape would ask
the analyst for injections that do not exist.

A13 is chromatographic but adds two things the assay archetype does not:

* **Blank subtraction before anything else.** Trace analysis at ppm level has a
  non-negligible reagent blank, so the corrected area is `area - blank`, and that
  correction has to happen before the concentration chain rather than after.
* **Blank interference as system suitability.** If the blank is a large fraction
  of the standard response, the method is not fit for the level being reported —
  so that ratio is a blocking criterion, not a note.

The result is truncated rather than rounded, matching the source sheet's `TRUNC`.
Truncation is deliberate for an impurity: it cannot round a result *up* across a
specification limit.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
    dilution_fields,
    replicate_area_group,
    standard_chain_terms,
    standard_group,
    standard_statistics_group,
    sst_rsd_criterion,
)

# ─────────────────────────────────────────────────────────────────────
#  A9 — Assay by titration
# ─────────────────────────────────────────────────────────────────────

A9_DEFINITION = {
    "resultRef": "determinations.mean_pct_lc",
    "context": context_header(
        avg_weight=False,
        extra=[
            {
                "key": "titrant",
                "kind": "context",
                "type": "text",
                "label": "Titrant",
                "overridable": True,
            },
            {
                "key": "normality",
                "kind": "context",
                "label": "Titrant Normality",
                "default": 0.1,
                "overridable": True,
            },
            {
                "key": "equivalence_factor",
                "kind": "context",
                "label": "Equivalence Factor (mg per mL of 1N)",
                "overridable": True,
            },
            {
                "key": "blank_ml",
                "kind": "context",
                "label": "Blank Titre",
                "unit": "mL",
                "default": 0,
                "overridable": True,
            },
        ],
    ),
    "groups": [
        {
            "key": "determinations",
            "kind": "table",
            "label": "Determinations",
            "rows": {"min": 1, "max": 6, "default": 2},
            "fields": [
                {"key": "prep_ref", "kind": "input", "type": "text", "label": "Prep. Ref."},
                {
                    "key": "sample_ml",
                    "kind": "input",
                    "label": "Sample Volume",
                    "unit": "mL",
                    "default": 1,
                    "required": True,
                },
                {
                    "key": "titre_ml",
                    "kind": "input",
                    "label": "Titre",
                    "unit": "mL",
                    "required": True,
                },
                {
                    "key": "net_titre",
                    "kind": "calculated",
                    "label": "Net Titre",
                    "unit": "mL",
                    #  A reagent blank consumes titrant too; not subtracting it
                    #  overstates content by the blank volume every time.
                    "expression": "titre_ml - blank_ml",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "mg_per_ml",
                    "kind": "calculated",
                    "label": "Content",
                    "unit": "mg/mL",
                    #  (mL × N × factor × 1000) / (mL sample × 1000). The paired
                    #  1000s cancel but are kept so the expression matches the
                    #  sheet a reviewer will compare it against.
                    "expression": (
                        "(net_titre * normality * equivalence_factor * 1000) "
                        "/ (sample_ml * 1000)"
                    ),
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "key": "pct_lc",
                    "kind": "calculated",
                    "label": "% of Label Claim",
                    "unit": "%",
                    "expression": "mg_per_ml / label_claim * 100",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "mean_pct_lc",
                    "kind": "calculated",
                    "label": "Mean % of Label Claim",
                    "unit": "%",
                    "expression": "mean(determinations.pct_lc)",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
    ],
    "criteria": [
        {
            "key": "determination_agreement",
            "label": "%RSD between determinations",
            "target": "rsd(determinations.pct_lc)",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
    ],
}

A9 = SeedTemplate(
    code="TPL-A9-0001",
    name="Assay by Titration",
    archetype="A9",
    result_unit="%",
    test_code="TST-TITR",
    test_name="Assay by Titration",
    test_type="Quantitative",
    definition=A9_DEFINITION,
)


# ─────────────────────────────────────────────────────────────────────
#  A10 — Loss on drying / water content
# ─────────────────────────────────────────────────────────────────────

A10_LOD_DEFINITION = {
    "resultRef": "determinations.mean_pct_loss",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {
                "key": "drying_conditions",
                "kind": "context",
                "type": "text",
                "label": "Drying Conditions",
                "overridable": True,
            },
        ],
    ),
    "groups": [
        {
            "key": "determinations",
            "kind": "table",
            "label": "Determinations",
            "rows": {"min": 1, "max": 6, "default": 2},
            "fields": [
                {"key": "prep_ref", "kind": "input", "type": "text", "label": "Dish Ref."},
                {
                    "key": "dish_weight",
                    "kind": "input",
                    "label": "Empty Dish (W1)",
                    "unit": "g",
                    "required": True,
                },
                {
                    "key": "dish_plus_sample",
                    "kind": "input",
                    "label": "Dish + Sample (W2)",
                    "unit": "g",
                    "required": True,
                },
                {
                    "key": "dish_plus_dried",
                    "kind": "input",
                    "label": "Dish + Dried (W3)",
                    "unit": "g",
                    "required": True,
                },
                {
                    "key": "sample_weight",
                    "kind": "calculated",
                    "label": "Sample Wt.",
                    "unit": "g",
                    "expression": "dish_plus_sample - dish_weight",
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "key": "pct_loss",
                    "kind": "calculated",
                    "label": "Loss on Drying",
                    "unit": "%",
                    #  (W2 - W3) / (W2 - W1) × 100
                    "expression": (
                        "(dish_plus_sample - dish_plus_dried) "
                        "/ (dish_plus_sample - dish_weight) * 100"
                    ),
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "mean_pct_loss",
                    "kind": "calculated",
                    "label": "Mean Loss on Drying",
                    "unit": "%",
                    "expression": "mean(determinations.pct_loss)",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
    ],
    "criteria": [
        {
            "key": "determination_agreement",
            "label": "Spread between determinations",
            "target": "max(determinations.pct_loss) - min(determinations.pct_loss)",
            "operator": "lte",
            "limit": 0.5,
            "severity": "advisory",
            "limitText": "NMT 0.5 % absolute",
        },
    ],
}

A10_LOD = SeedTemplate(
    code="TPL-A10-0001",
    name="Loss on Drying",
    archetype="A10",
    result_unit="%",
    test_code="TST-LOD",
    test_name="Loss on Drying",
    test_type="Quantitative",
    definition=A10_LOD_DEFINITION,
)


# ─────────────────────────────────────────────────────────────────────
#  A10 — Weight per mL
# ─────────────────────────────────────────────────────────────────────

A10_WPM_DEFINITION = {
    "resultRef": "determinations.mean_weight_per_ml",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {
                "key": "water_factor",
                "kind": "context",
                "label": "Water Density Factor at Test Temperature",
                #  0.99704 g/mL at 25 °C — the sheet's constant, exposed rather
                #  than buried so a different test temperature is a field edit.
                "default": 0.99704,
                "overridable": True,
            },
            {
                "key": "temperature_c",
                "kind": "context",
                "label": "Temperature",
                "unit": "°C",
                "default": 25,
                "overridable": True,
            },
        ],
    ),
    "groups": [
        {
            "key": "determinations",
            "kind": "table",
            "label": "Pycnometer Determinations",
            "rows": {"min": 1, "max": 6, "default": 2},
            "fields": [
                {"key": "prep_ref", "kind": "input", "type": "text", "label": "Pycnometer"},
                {
                    "key": "empty_weight",
                    "kind": "input",
                    "label": "Empty (W)",
                    "unit": "g",
                    "required": True,
                },
                {
                    "key": "with_sample",
                    "kind": "input",
                    "label": "With Sample (W1)",
                    "unit": "g",
                    "required": True,
                },
                {
                    "key": "with_water",
                    "kind": "input",
                    "label": "With Water (W2)",
                    "unit": "g",
                    "required": True,
                },
                {
                    "key": "ratio",
                    "kind": "calculated",
                    "label": "Relative Density",
                    #  Rounded to 4 dp BEFORE the density factor, as the sheet
                    #  does — rounding after would shift the last reported digit.
                    "expression": (
                        "(with_sample - empty_weight) / (with_water - empty_weight)"
                    ),
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "key": "weight_per_ml",
                    "kind": "calculated",
                    "label": "Weight per mL",
                    "unit": "g/mL",
                    "expression": "ratio * water_factor",
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "key": "mean_weight_per_ml",
                    "kind": "calculated",
                    "label": "Mean Weight per mL",
                    "unit": "g/mL",
                    "expression": "mean(determinations.weight_per_ml)",
                    "rounding": {"mode": "round", "digits": 4},
                },
            ],
        },
    ],
    "criteria": [],
}

A10_WPM = SeedTemplate(
    code="TPL-A10-0002",
    name="Weight per mL (pycnometer)",
    archetype="A10",
    result_unit="g/mL",
    test_code="TST-WPML",
    test_name="Weight per mL",
    test_type="Quantitative",
    definition=A10_WPM_DEFINITION,
)


# ─────────────────────────────────────────────────────────────────────
#  A13 — Trace / nitrosamine impurities
# ─────────────────────────────────────────────────────────────────────

A13_DEFINITION = {
    "resultRef": "samples.mean_ppm",
    "context": context_header(
        extra=[
            {
                "key": "blank_area",
                "kind": "context",
                "label": "Mean Blank Area",
                "default": 0,
                "overridable": True,
            },
        ]
    ),
    "groups": [
        standard_group(
            label="Nitrosamine Standard", with_mw=False, conc_label="Standard Concentration"
        ),
        replicate_area_group(label="Standard Injections", default_rows=6),
        standard_statistics_group(),
        {
            "key": "samples",
            "kind": "table",
            "label": "Sample Preparations",
            "rows": {"min": 1, "max": 12, "default": 2},
            "fields": [
                {"key": "prep_ref", "kind": "input", "type": "text", "label": "Prep. Ref."},
                {
                    "key": "sample_weight",
                    "kind": "input",
                    "label": "Sample Wt.",
                    "unit": "mg",
                    "required": True,
                },
                *dilution_fields("s_"),
                {"key": "area", "kind": "area", "label": "Area", "unit": "µV·s"},
                {
                    "key": "corrected_area",
                    "kind": "calculated",
                    "label": "Blank-Corrected Area",
                    #  Applied before the concentration chain, not after — at ppm
                    #  level the reagent blank is a real fraction of the response.
                    "expression": "area - blank_area",
                },
                {
                    "key": "ppm",
                    "kind": "calculated",
                    "label": "Content",
                    "unit": "ppm",
                    #  ×1e6 for ppm rather than ×100 for percent.
                    "expression": (
                        f"corrected_area / stats.mean_std * {standard_chain_terms()} "
                        "* standard.potency / 100 "
                        "* s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 "
                        "* s_vol_1 / sample_weight "
                        "* avg_weight / label_claim * 1000000"
                    ),
                    #  Truncated, per the sheet. For an impurity this is the safe
                    #  direction: truncation cannot round a result up across a limit.
                    "rounding": {"mode": "trunc", "digits": 4},
                },
                {
                    "key": "mean_ppm",
                    "kind": "calculated",
                    "label": "Mean Content",
                    "unit": "ppm",
                    "expression": "mean(samples.ppm)",
                    "rounding": {"mode": "trunc", "digits": 4},
                },
            ],
        },
        {
            "key": "suitability",
            "kind": "singleton",
            "label": "Blank Assessment",
            "fields": [
                {
                    "key": "blank_interference",
                    "kind": "calculated",
                    "label": "Blank Interference",
                    "unit": "%",
                    "expression": "blank_area / stats.mean_std * 100",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
    ],
    "criteria": [
        sst_rsd_criterion(),
        {
            "key": "blank_interference",
            "label": "Blank interference against standard response",
            "target": "suitability.blank_interference",
            "operator": "lte",
            "limit": 5.0,
            #  Blocking: a blank this large means the method cannot support the
            #  level being reported, so the number should not be released.
            "severity": "blocking",
            "limitText": "NMT 5.0 %",
        },
    ],
}

A13 = SeedTemplate(
    code="TPL-A13-0001",
    name="Trace / Nitrosamine Impurities by LC-MS",
    archetype="A13",
    result_unit="ppm",
    test_code="TST-NITR",
    test_name="Nitrosamine Impurities",
    test_type="Quantitative",
    definition=A13_DEFINITION,
)

TEMPLATES = [A9, A10_LOD, A10_WPM, A13]
