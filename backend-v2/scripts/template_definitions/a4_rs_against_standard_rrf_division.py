"""
A4 — Related substances by HPLC, calculated against a (main-analyte) standard,
with the RRF applied as a DIVISION factor.

Source workbook: "Related substance by HPLC_Calculation aginst standard_RRF
division factor.xls" (the Amsacrine for Injection 75 mg/1.5 mL
"Releated Substance Calculation Sheet"). It is the A4 against-standard shape,
distinct from TPL-A4-0001 (against an *impurity* standard) in three ways that
are load-bearing and easy to get wrong:

* **The result is calculated against the main-analyte standard**, so each
  impurity carries the full assay-style make-up, exactly as the sheet's
  Calculation Formula cell spells it out:

      (Sample area / Std area)
    × (Std weight / Std dilution)
    × (Sample dilution / Sample weight)
    × (Average wt. / Label claim)
    × (M.W.-1 / M.W.-2)
    × Standard Potency

  The `(Average wt. / Label claim)` term is what separates this from the
  impurity-standard sheet (TPL-A4-0001), which has no label-claim divisor.

* **RRF direction defaults to DIVISION.** The sheet's dropdown offers
  "RRF (multiplication factor)" and "RRF (Division factor)"; this sheet's
  default — and its name — is the division factor. The same relative response
  factor applied the wrong way misreports every impurity by the square of the
  factor, so the default here is DIVIDE (the inverse of TPL-A4-0001). The mode
  stays overridable so a method that multiplies can still use this template.

* **Below-LOQ rows report `BLQ`, not a number**, and **the totals sum
  already-rounded rows** (`SUM(ROUND(...,3))`), not the rounded sum — the same
  two conventions carried across the whole A4 family. Three impurities at
  0.0004 total 0.000, not 0.001.

This sheet reports **only unknown impurities** (Unknown impurity-1..11),
calculated against the main-analyte standard. The worksheet has a single
"Calculation of unknown impurities against standard" table and reports
**Single maximum unknown impurity** and **Total unknown impurities**. (An
earlier revision also carried a separate Known Impurities table and
known/known+unknown totals; those were removed when the method was reduced to
unknown-impurity reporting only.)

Only expression functions/operators the evaluator supports are used
(mean/sum/sd/rsd/min/max/round/trunc/abs/isblank/blank/pool/if, arithmetic and
comparisons) — verified against `src/domain/services/calculation/expression.py`
via the other A4 modules. There is no IFERROR; blank / divide-by-zero
propagation is automatic.
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

#  Applied to the raw percentage. `rrf` defaults to 1, so a peak/method that
#  does not use a response factor needs no special case. The DEFAULT mode here
#  is DIVIDE (this is the "RRF division factor" sheet); the branch still honours
#  a method that overrides to multiply.
_RRF_APPLIED = (
    f'if(rrf_mode = "{_RRF_MULTIPLY}", pct_uncorrected * rrf, pct_uncorrected / rrf)'
)

#  The against-standard per-peak % chain, matching the sheet's Calculation
#  Formula cell. `standard_chain_terms()` is Std weight / Std dilution;
#  `sample_chain_terms(group="sample_prep")` is the inverted sample make-up
#  (Sample dilution / Sample weight). `avg_weight / label_claim` is the Average
#  wt. / Label claim term that distinguishes this sheet from TPL-A4-0001.
_PCT_UNCORRECTED = (
    f"response / stats.mean_std * {standard_chain_terms()} "
    f"* {sample_chain_terms(group='sample_prep')} "
    "* avg_weight / label_claim "
    "* standard.mw_base / standard.mw_salt "
    "* standard.potency / 100 "
    "* 100"
)


def _peak_calculated_fields() -> list[dict]:
    """
    The calculated columns of the unknown-impurity table.

    `rrt` is the retention time relative to the main peak; `pct_uncorrected`
    is the against-standard % before the RRF; `pct` applies the RRF (division
    by default) and rounds to 3 dp; `pct_for_total` zeroes below-LOQ rows for
    the totals; `reported` prints BLQ below the LOQ. The peak area is the
    single `response` input column, not a mean of duplicate injections.
    """
    return [
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
            "expression": _PCT_UNCORRECTED,
        },
        {
            "key": "pct",
            "kind": "calculated",
            "label": "% Impurity",
            "unit": "%",
            "expression": _RRF_APPLIED,
            #  Rounded HERE; the totals sum these rounded rows (SUM(ROUND(...))).
            "rounding": {"mode": "round", "digits": 3},
        },
        {
            "key": "pct_for_total",
            "kind": "calculated",
            "label": "% counted in total",
            "unit": "%",
            #  Calculation-only helper. Keep it in the definition because the
            #  reportable total and acceptance criteria use it, but omit the
            #  column from the worksheet, preview, and print layouts.
            "hidden": True,
            #  Below-LOQ rows contribute nothing to the totals.
            "expression": "if(pct < loq, 0, pct)",
        },
        {
            "key": "reported",
            "kind": "calculated",
            "label": "Reporting % Impurity",
            #  Text, not a number: a value under the LOQ is not a measurement and
            #  must print as BLQ.
            "expression": 'if(pct < loq, "BLQ", pct)',
        },
    ]


def _impurity_input_fields(name_label: str) -> list[dict]:
    """
    The input columns of the unknown-impurity table, in sheet order:
    Impurity | RT | Response | LOQ | RRF (Division factor).

    The sheet records a single peak **Response** per impurity (not duplicate
    injections), so the area is one `response` column. LOQ defaults to 0 to
    match the sheet (every LOQ cell reads 0.000); a method with a real LOQ
    overrides it per row.
    """
    return [
        {"key": "name", "kind": "input", "type": "text", "label": name_label},
        {"key": "rt", "kind": "input", "label": "RT", "unit": "min"},
        {"key": "response", "kind": "area", "label": "Response"},
        {"key": "loq", "kind": "input", "label": "LOQ", "unit": "%", "default": 0},
        {
            "key": "rrf",
            "kind": "input",
            "label": "RRF (Division factor)",
            "default": 1,
            #  1 is the neutral value in both modes, so a peak without a response
            #  factor needs no branch.
        },
    ]


A4_RRF_DIV_DEFINITION = {
    "resultRef": "summary.total_unknowns",
    "context": context_header(
        extra=[
            {
                "key": "rrf_mode",
                "kind": "context",
                "type": "text",
                "label": "RRF Application",
                #  DIVISION by default — this is the "RRF division factor" sheet.
                "default": _RRF_DIVIDE,
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
            {
                "key": "product_name",
                "kind": "context",
                "type": "text",
                "label": "Product Name",
                "source": "product.name",
                "overridable": True,
            },
            {
                "key": "trf_no",
                "kind": "context",
                "type": "text",
                "label": "TRF No.",
                "source": "trf.trf_number",
                "overridable": True,
            },
            {
                "key": "ar_no",
                "kind": "context",
                "type": "text",
                "label": "AR.No.",
                "source": "trf.ar_number",
                "overridable": True,
            },
            {
                "key": "storage_condition",
                "kind": "context",
                "type": "text",
                "label": "Storage pack/condition",
                "overridable": True,
            },
            {
                "key": "analysis_as_per",
                "kind": "context",
                "type": "text",
                "label": "Analysis as per",
                "overridable": True,
            },
            {
                "key": "checked_by",
                "kind": "context",
                "type": "text",
                "label": "Checked By",
                "overridable": True,
            },
        ]
    ),
    "groups": [
        #  The weighed main-analyte standard: weight, dilution chain, MW
        #  base/salt correction and potency. The impurity % is calculated
        #  against THIS standard (`stats.mean_std` + its concentration chain).
        #  Preserve the singleton's scalar evaluator scope (`standard.weight_mg`,
        #  etc.) while presenting its one standard-preparation record as a
        #  spreadsheet-style table. Changing the group kind to `table` would turn
        #  those scalar formula references into column lists.
        {
            **standard_group(
                label="Standard Details", conc_label="Standard Concentration"
            ),
            "renderAsTable": True,
        },
        replicate_area_group(label="Standard Replicate Injections"),
        standard_statistics_group(),
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
        #  Unknown impurities (Unknown impurity-1..11 on the sheet) —
        #  calculated against the main-analyte standard. This is the only
        #  impurity table: the sheet reports unknown impurities only.
        {
            "key": "unknowns",
            "kind": "table",
            "label": "Calculation of unknown impurities against standard",
            "rows": {"min": 1, "max": 20, "default": 1, "labelFrom": "name"},
            "fields": [
                *_impurity_input_fields("Unknown Impurity"),
                *_peak_calculated_fields(),
            ],
        },
        #  Reporting roll-ups. Each guarded with isblank(mean(...)) so an
        #  untouched sheet reports blank, not 0.000.
        {
            "key": "summary",
            "kind": "singleton",
            "label": "Summary",
            "fields": [
                {
                    "key": "max_single_unknown",
                    "kind": "calculated",
                    "label": "Single Maximum Unknown Impurity",
                    "unit": "%",
                    "expression": (
                        "if(isblank(mean(unknowns.pct)), blank(), "
                        "max(unknowns.pct_for_total))"
                    ),
                    "rounding": {"mode": "round", "digits": 3},
                },
                {
                    "key": "total_unknowns",
                    "kind": "calculated",
                    "label": "Total Unknown Impurities",
                    "unit": "%",
                    "expression": (
                        "if(isblank(mean(unknowns.pct)), blank(), "
                        "sum(unknowns.pct_for_total))"
                    ),
                    "rounding": {"mode": "round", "digits": 3},
                },
            ],
        },
    ],
    "criteria": [
        #  %RSD of the standard replicate injections, NMT 2.0.
        sst_rsd_criterion(),
        {
            "key": "single_max_unknown",
            "label": "Single maximum unknown impurity",
            "target": "max(unknowns.pct_for_total)",
            "operator": "lte",
            "limit": 0.2,
            "severity": "advisory",
            "limitText": "NMT 0.2 %",
        },
        {
            "key": "total_max",
            "label": "Total unknown impurities",
            "target": "sum(unknowns.pct_for_total)",
            "operator": "lte",
            "limit": 1.0,
            "severity": "advisory",
            "limitText": "NMT 1.0 %",
        },
    ],
}

A4_RRF_DIVISION = SeedTemplate(
    code="TPL-A4-0004",
    name="Related Substances by HPLC (against standard, RRF division factor)",
    archetype="A4",
    result_unit="%",
    test_code="TST-RS-STD-RRFDIV",
    test_name="Related Substances by HPLC (against standard, RRF division factor)",
    test_type="Quantitative",
    definition=A4_RRF_DIV_DEFINITION,
)

TEMPLATES = [A4_RRF_DIVISION]
