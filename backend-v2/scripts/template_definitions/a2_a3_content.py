"""
A2 — multi-analyte content, and A3 — saturation solubility.

**A2** (`Content of Lyso PC PG`): the analyte response is the *sum* of several
named peaks per injection rather than a single peak, and a zero sum must read as
blank instead of zero — the sheet wraps it in `IF(SUM(...)=0,"",SUM(...))`.

The `_mgvial_` and `_mgmL_` workbooks turned out to be the same sheet differing
only by a ×12.5 vial factor, so that is a `vial_factor` context field rather than
a second template.

**A3** (saturation solubility): the same master equation reported as mg/mL in the
dissolution medium rather than as a percentage of label claim, so there is no
label-claim divisor at all.
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

#  Four peak slots. More analytes means a new template version, which is the
#  correct GxP outcome — the reported composition changed.
_PEAK_SLOTS = 4
_PEAK_KEYS = [f"peak_{i}" for i in range(1, _PEAK_SLOTS + 1)]
_PEAK_LIST = "[" + ", ".join(_PEAK_KEYS) + "]"
#  `blank()` rather than 0: an un-injected row must not read as a zero response.
_PEAK_SUM = f"if(sum({_PEAK_LIST}) = 0, blank(), sum({_PEAK_LIST}))"


def _peak_fields(label_prefix: str) -> list[dict]:
    return [
        {
            "key": key,
            "kind": "area",
            "label": f"{label_prefix} {index}",
            "unit": "µV·s",
        }
        for index, key in enumerate(_PEAK_KEYS, start=1)
    ]


# ─────────────────────────────────────────────────────────────────────
#  A2 — Multi-analyte content
# ─────────────────────────────────────────────────────────────────────

A2_DEFINITION = {
    "resultRef": "samples.mean_pct_lc",
    "context": context_header(
        extra=[
            {
                "key": "vial_factor",
                "kind": "context",
                "label": "Vial Factor (1 = per mL, 12.5 = per vial)",
                "default": 1,
                "overridable": True,
            }
        ]
    ),
    "groups": [
        standard_group(conc_label="Standard Concentration"),
        {
            "key": "std_areas",
            "kind": "table",
            "label": "Standard Injections (peak areas summed)",
            "rows": {"min": 1, "max": 6, "default": 5},
            "fields": [
                *_peak_fields("STD Peak"),
                {
                    "key": "area",
                    "kind": "calculated",
                    "label": "Total STD Area",
                    "expression": _PEAK_SUM,
                },
            ],
        },
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
                *_peak_fields("Peak"),
                {
                    "key": "area",
                    "kind": "calculated",
                    "label": "Total Area",
                    "expression": _PEAK_SUM,
                },
                {
                    "key": "content",
                    "kind": "calculated",
                    "label": "Content",
                    "unit": "mg",
                    #  Master equation, then the vial factor. Multiplying at the end
                    #  keeps the per-mL and per-vial sheets one template.
                    "expression": (
                        f"area / stats.mean_std * {standard_chain_terms()} "
                        f"* {sample_chain_terms()} "
                        "* standard.potency / 100 "
                        "* standard.mw_base / standard.mw_salt "
                        "* vial_factor"
                    ),
                    "rounding": {"mode": "round", "digits": 3},
                },
                {
                    "key": "pct_lc",
                    "kind": "calculated",
                    "label": "% of Label Claim",
                    "unit": "%",
                    "expression": "content * 100 / label_claim",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "mean_pct_lc",
                    "kind": "calculated",
                    "label": "Mean % of Label Claim",
                    "unit": "%",
                    "expression": "mean(samples.pct_lc)",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
    ],
    "criteria": [
        sst_rsd_criterion(),
        {
            "key": "content_range",
            "label": "Mean content as % of label claim",
            "target": "mean(samples.pct_lc)",
            "operator": "between",
            "limit": [90.0, 110.0],
            "severity": "advisory",
            "limitText": "90.0 % to 110.0 %",
        },
    ],
}

A2 = SeedTemplate(
    code="TPL-A2-0001",
    name="Multi-Analyte Content by HPLC (summed peaks)",
    archetype="A2",
    result_unit="%",
    test_code="TST-CONT",
    test_name="Content of Related Analytes by HPLC",
    test_type="Quantitative",
    definition=A2_DEFINITION,
)


# ─────────────────────────────────────────────────────────────────────
#  A3 — Saturation solubility
# ─────────────────────────────────────────────────────────────────────

A3_DEFINITION = {
    "resultRef": "samples.mean_solubility",
    #  No label claim: solubility is an absolute concentration in the medium, not
    #  a proportion of a declared strength.
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {
                "key": "medium",
                "kind": "context",
                "type": "text",
                "label": "Medium",
                "overridable": True,
            },
            {
                "key": "temperature_c",
                "kind": "context",
                "label": "Temperature",
                "unit": "°C",
                "default": 37,
                "overridable": True,
            },
        ],
    ),
    "groups": [
        standard_group(conc_label="Standard Concentration"),
        replicate_area_group(),
        standard_statistics_group(),
        {
            "key": "samples",
            "kind": "table",
            "label": "Saturated Solution Preparations",
            "rows": {"min": 1, "max": 12, "default": 3},
            "fields": [
                {"key": "prep_ref", "kind": "input", "type": "text", "label": "Prep. Ref."},
                {"key": "time_point", "kind": "input", "type": "text", "label": "Equilibration"},
                #  The filtrate is diluted, not weighed — so the chain runs from a
                #  volume aliquot rather than from a sample weight.
                {
                    "key": "aliquot_ml",
                    "kind": "input",
                    "label": "Aliquot",
                    "unit": "mL",
                    "default": 1,
                    "required": True,
                },
                {
                    "key": "diluted_to_ml",
                    "kind": "input",
                    "label": "Diluted To",
                    "unit": "mL",
                    "default": 1,
                    "required": True,
                },
                {"key": "area", "kind": "area", "label": "Area", "unit": "µV·s"},
                {
                    "key": "solubility",
                    "kind": "calculated",
                    "label": "Solubility",
                    "unit": "mg/mL",
                    #  Standard is in ppm (µg/mL), so /1000 converts to mg/mL.
                    "expression": (
                        "area / stats.mean_std * standard.conc_ppm "
                        "* diluted_to_ml / aliquot_ml / 1000"
                    ),
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "key": "mean_solubility",
                    "kind": "calculated",
                    "label": "Mean Solubility",
                    "unit": "mg/mL",
                    "expression": "mean(samples.solubility)",
                    "rounding": {"mode": "round", "digits": 4},
                },
            ],
        },
    ],
    "criteria": [
        sst_rsd_criterion(),
        {
            "key": "prep_agreement",
            "label": "%RSD across saturated solution preparations",
            "target": "rsd(samples.solubility)",
            "operator": "lte",
            "limit": 5.0,
            "severity": "advisory",
            "limitText": "NMT 5.0 %",
        },
    ],
}

A3 = SeedTemplate(
    code="TPL-A3-0001",
    name="Saturation Solubility by HPLC",
    archetype="A3",
    result_unit="mg/mL",
    test_code="TST-SOLB",
    test_name="Saturation Solubility",
    test_type="Quantitative",
    definition=A3_DEFINITION,
)

TEMPLATES = [A2, A3]
