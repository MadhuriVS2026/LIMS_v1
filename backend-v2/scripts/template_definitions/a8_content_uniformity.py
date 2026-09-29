"""
A8 — content uniformity, two variants.

The Acceptance Value is the part worth reading carefully. USP <905>:

    AV = |M - X| + k·s

where M is 98.5 when X < 98.5, 101.5 when X > 101.5, and X itself in between —
so the first term vanishes for a well-centred batch and AV reduces to k·s. The
sheets express it as a nested `IF`, and the nesting order matters: testing the
upper bound first and the lower bound second gives the wrong answer for a mean
below 98.5.

`k` is 2.4 for 10 units and 2.0 for 30, which the sheet does as a lookup. Here it
is an overridable context field defaulting to 2.4 with a criterion on the unit
count, because a hard-coded lookup silently produces a wrong AV if someone runs
a 30-unit stage-2 test on a 10-unit template.

The **weight variation** variant substitutes net weight for a chromatographic
assay: net = filled - empty, scaled by the batch assay. Same AV arithmetic.
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

#  Nested exactly as the source sheet: upper bound outermost, lower bound inside.
#  Reversing these two tests breaks every batch whose mean sits below 98.5.
_ACCEPTANCE_VALUE = (
    "if(mean_pct < 101.5, "
    "if(mean_pct < 98.5, (98.5 - mean_pct) + k_value * sd_pct, k_value * sd_pct), "
    "(mean_pct - 101.5) + k_value * sd_pct)"
)


def _cu_context(extra: list[dict] | None = None) -> list[dict]:
    return context_header(
        extra=[
            {
                "key": "k_value",
                "kind": "context",
                "label": "Acceptability Constant k (2.4 for n=10, 2.0 for n=30)",
                "default": 2.4,
                "overridable": True,
            },
            *(extra or []),
        ]
    )


def _summary_group(source: str) -> dict:
    """Mean, SD, k·s and the Acceptance Value over the per-unit percentages."""
    return {
        "key": "summary",
        "kind": "singleton",
        "label": "Uniformity Assessment",
        "fields": [
            {
                "key": "unit_count",
                "kind": "calculated",
                "label": "Units Tested",
                "expression": f"count({source}.pct_lc)",
            },
            {
                "key": "mean_pct",
                "kind": "calculated",
                "label": "Mean (X)",
                "unit": "%",
                "expression": f"mean({source}.pct_lc)",
                #  Rounded before entering the AV chain, matching the sheet.
                "rounding": {"mode": "round", "digits": 1},
            },
            {
                "key": "sd_pct",
                "kind": "calculated",
                "label": "SD (s)",
                "expression": f"sd({source}.pct_lc)",
                "rounding": {"mode": "round", "digits": 4},
            },
            {
                "key": "rsd_pct",
                "kind": "calculated",
                "label": "%RSD",
                "unit": "%",
                "expression": f"rsd({source}.pct_lc)",
                "rounding": {"mode": "round", "digits": 1},
            },
            {
                "key": "min_pct",
                "kind": "calculated",
                "label": "Minimum",
                "unit": "%",
                "expression": f"min({source}.pct_lc)",
            },
            {
                "key": "max_pct",
                "kind": "calculated",
                "label": "Maximum",
                "unit": "%",
                "expression": f"max({source}.pct_lc)",
            },
            {
                "key": "acceptance_value",
                "kind": "calculated",
                "label": "Acceptance Value (AV)",
                "expression": _ACCEPTANCE_VALUE,
                "rounding": {"mode": "round", "digits": 1},
            },
        ],
    }


def _cu_criteria(source: str) -> list[dict]:
    return [
        {
            "key": "acceptance_value",
            "label": "Acceptance Value",
            "target": "summary.acceptance_value",
            "operator": "lte",
            "limit": 15.0,
            "severity": "blocking",
            "limitText": "NMT 15.0",
        },
        {
            "key": "unit_count",
            "label": "Units tested (stage 1)",
            "target": f"count({source}.pct_lc)",
            "operator": "gte",
            "limit": 10,
            #  Advisory, not blocking: a stage-2 test legitimately has 30 units,
            #  and blocking on an exact count would obstruct that.
            "severity": "advisory",
            "limitText": "NLT 10 units",
        },
    ]


# ─────────────────────────────────────────────────────────────────────
#  A8 — Content uniformity by HPLC
# ─────────────────────────────────────────────────────────────────────

A8_HPLC_DEFINITION = {
    "resultRef": "summary.acceptance_value",
    "context": _cu_context(),
    "groups": [
        standard_group(conc_label="Standard Concentration"),
        replicate_area_group(default_rows=5),
        standard_statistics_group(),
        {
            "key": "units",
            "kind": "table",
            "label": "Individual Units",
            "rows": {"min": 1, "max": 30, "default": 10},
            "fields": [
                {"key": "unit_ref", "kind": "input", "type": "text", "label": "Unit"},
                {
                    "key": "unit_weight",
                    "kind": "input",
                    "label": "Unit Wt.",
                    "unit": "mg",
                    "required": True,
                },
                *dilution_fields("s_"),
                {"key": "area", "kind": "area", "label": "Area", "unit": "µV·s"},
                {
                    "key": "pct_lc",
                    "kind": "calculated",
                    "label": "% of Label Claim",
                    "unit": "%",
                    "expression": (
                        f"area / stats.mean_std * {standard_chain_terms()} "
                        "* standard.potency / 100 "
                        "* standard.mw_base / standard.mw_salt "
                        "* s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 "
                        "* s_vol_1 / unit_weight "
                        "* avg_weight / label_claim * 100"
                    ),
                    "rounding": {"mode": "round", "digits": 1},
                },
            ],
        },
        _summary_group("units"),
    ],
    "criteria": [sst_rsd_criterion(), *_cu_criteria("units")],
}

A8_HPLC = SeedTemplate(
    code="TPL-A8-0001",
    name="Content Uniformity by HPLC",
    archetype="A8",
    result_unit="AV",
    test_code="TST-CU",
    test_name="Uniformity of Dosage Units by HPLC",
    test_type="Quantitative",
    definition=A8_HPLC_DEFINITION,
)


# ─────────────────────────────────────────────────────────────────────
#  A8 — Content uniformity by weight variation
# ─────────────────────────────────────────────────────────────────────

A8_WV_DEFINITION = {
    "resultRef": "summary.acceptance_value",
    "context": _cu_context(
        extra=[
            {
                "key": "batch_assay",
                "kind": "context",
                "label": "Batch Assay",
                "unit": "%",
                "default": 100,
                "overridable": True,
            },
            {
                "key": "mean_fill_weight",
                "kind": "context",
                "label": "Declared Mean Fill Weight",
                "unit": "mg",
                "overridable": True,
            },
        ]
    ),
    #  No standard block at all: weight variation needs no chromatography, which is
    #  why it is a separate template rather than a flag on the HPLC one.
    "groups": [
        {
            "key": "units",
            "kind": "table",
            "label": "Individual Units (gravimetric)",
            "rows": {"min": 1, "max": 30, "default": 10},
            "fields": [
                {"key": "unit_ref", "kind": "input", "type": "text", "label": "Unit"},
                {
                    "key": "filled_weight",
                    "kind": "input",
                    "label": "Filled Wt.",
                    "unit": "mg",
                    "required": True,
                },
                {
                    "key": "empty_weight",
                    "kind": "input",
                    "label": "Empty Wt.",
                    "unit": "mg",
                    "required": True,
                },
                {
                    "key": "net_weight",
                    "kind": "calculated",
                    "label": "Net Wt.",
                    "unit": "mg",
                    "expression": "filled_weight - empty_weight",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "pct_lc",
                    "kind": "calculated",
                    "label": "% of Label Claim",
                    "unit": "%",
                    #  Content is inferred from mass, scaled by the batch's measured
                    #  assay — the substitution USP <905> permits when the dosage
                    #  form is highly uniform.
                    "expression": "net_weight / mean_fill_weight * batch_assay",
                    "rounding": {"mode": "round", "digits": 1},
                },
            ],
        },
        _summary_group("units"),
    ],
    "criteria": _cu_criteria("units"),
}

A8_WV = SeedTemplate(
    code="TPL-A8-0002",
    name="Content Uniformity by Weight Variation",
    archetype="A8",
    result_unit="AV",
    test_code="TST-CUWV",
    test_name="Uniformity of Dosage Units by Weight Variation",
    test_type="Quantitative",
    definition=A8_WV_DEFINITION,
)

TEMPLATES = [A8_HPLC, A8_WV]
