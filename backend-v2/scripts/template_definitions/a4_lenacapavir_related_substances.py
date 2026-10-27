"""
A4 — Related Substances for Lenacapavir Injection 309 mg/mL (compound-specific).

This template reproduces the Excel "Related Substance Calculation Sheet" for
**Lenacapavir Injection 309 mg/mL** (active: Lenacapavir Na). It is the A4
(chromatographic-against-standard) shape, adapted to the sheet's six weighed
standard preparations (STD-1..6) plus a bracketing-standard block, the sheet's
system-suitability / sensitivity criteria, a hard-coded known-impurity table,
an Unknown-1..27 table and the reporting roll-ups.

Everything compound-specific here — the impurity names, their RRT values and the
RRF (multiplication-factor) defaults — is transcribed VERBATIM from the
Lenacapavir sheet supplied by the requester. It is NOT correlated from, or copied
off, any other compound's impurity list. The sheet gives no numeric RRF for these
peaks, so every row's RRF defaults to 1.0 (the neutral value in both the multiply
and divide modes); no RRF numbers are fabricated.

Three behaviours carried over from the A4 family are load-bearing:

* **RRF direction is a mode, not a constant** (`rrf_mode`): applied as a
  multiplier by default, with a divide variant, exactly as the sheet's dropdown.
* **Below-reporting-threshold rows report `BLQ`, not a number.** A value under
  the per-row reporting threshold (LOQ) is not a measurement and must not print
  as one; it also contributes 0 to the totals.
* **Totals sum already-rounded rows** (`SUM(ROUND(...,3))`), not the rounded sum,
  so three impurities at 0.0004 total 0.000, not 0.001.

Only expression functions/operators the evaluator supports are used (verified in
`src/domain/services/calculation/expression.py`): mean/sum/sd/rsd/min/max/round/
trunc/abs/isblank/blank/pool/if, the arithmetic operators and comparisons. There
is no IFERROR — blank/division-by-zero propagation is automatic.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
    dilution_fields,
    sample_chain_terms,
    sst_rsd_criterion,
)

_RRF_MULTIPLY = "RRF (multiplication factor)"
_RRF_DIVIDE = "RRF (division factor)"

#  Applied to the raw percentage. `rrf` defaults to 1, so a method/peak that does
#  not use a response factor needs no special case.
_RRF_APPLIED = (
    f'if(rrf_mode = "{_RRF_MULTIPLY}", pct_uncorrected * rrf, pct_uncorrected / rrf)'
)


# ─────────────────────────────────────────────────────────────────────
#  Compound-specific known-impurity list — transcribed VERBATIM from the
#  Lenacapavir Injection 309 mg/mL "Related Substance" sheet.
#
#  `name`     primary (Gilead) name as printed on the sheet.
#  `rrt`      the sheet's fixed relative-retention-time value for the peak.
#  `alt_name` the Emcure / Hetero name the sheet lists alongside, where given.
#
#  The sheet gives NO numeric RRF for any of these peaks, so every row's RRF
#  defaults to 1.0 (set on the table's `rrf` field, not per row) — no RRF number
#  is invented here. Do NOT correlate or copy this list against another compound.
# ─────────────────────────────────────────────────────────────────────
_KNOWN_IMPURITIES: list[dict] = [
    #  Named / known (Gilead primary name — alt = Emcure / Hetero).
    {"name": "GS-832077 + GS-837509", "rrt": 0.60, "alt_name": "Amine + N-Acetyl / LCV3 Monomesyl + Acetyl"},
    {"name": "GS-833244", "rrt": 0.86, "alt_name": "Chloromethyl imp. / MSC amine"},
    {"name": "GS-833150", "rrt": 0.88, "alt_name": "Des Bromo Imp / Des Bromo Imp"},
    {"name": "GS-833248", "rrt": 0.90, "alt_name": "Keto imp. / LCV Keto"},
    {"name": "GS-837322", "rrt": 0.91, "alt_name": "Deschloro / Des Chloro"},
    {"name": "LENA-2076 or GS-832076", "rrt": 1.08, "alt_name": "LCA-V imp. / Bromo Impurity"},
    {"name": "LENA-2078 or GS-832078", "rrt": 1.20, "alt_name": "LCA-VI / Amine"},
    {"name": "LENA-3243 or GS-833243", "rrt": 1.21, "alt_name": "LCA-VII / LKH-IV(i)/LCV(i)/LSN(i)"},
    {"name": "GS-828793", "rrt": 1.26, "alt_name": "Methyl Impurity / Methyl Impurity"},
    {"name": "GS-941756", "rrt": 1.34, "alt_name": "Ethyl Impurity / Ethyl Impurity"},
    {"name": "GS-968750", "rrt": 1.49, "alt_name": "Double bond / Double bond"},
    #  Additional Emcure-named rows.
    {"name": "Hydroxide Impurity", "rrt": 1.03, "alt_name": "Emcure"},
    {"name": "LCA-VI", "rrt": 1.20, "alt_name": "Emcure"},
    {"name": "Trifluoroacetyl imp.", "rrt": 0.70, "alt_name": "Emcure"},
    {"name": "Diene imp.", "rrt": 1.56, "alt_name": "Emcure"},
    {"name": "Allene imp.", "rrt": 1.60, "alt_name": "Emcure"},
    {"name": "Keto Imp.", "rrt": 0.80, "alt_name": "Emcure"},
    #  Atropisomer rows.
    {"name": "Atropisomer-Chloromethyl", "rrt": 0.81, "alt_name": "Atropisomer"},
    {"name": "Atropisomer-N-Acetyl", "rrt": 0.49, "alt_name": "Atropisomer"},
    {"name": "Atropisomer-Trifluoro acetyl", "rrt": 0.63, "alt_name": "Atropisomer"},
    {"name": "Atropisomer-Deschloro", "rrt": 0.85, "alt_name": "Atropisomer"},
    {"name": "Atropisomer-LCA-VI", "rrt": 1.13, "alt_name": "Atropisomer"},
    {"name": "Atropisomer-LCA-VII", "rrt": 1.18, "alt_name": "Atropisomer"},
    {"name": "Atropisomer-Methyl imp", "rrt": 1.20, "alt_name": "Atropisomer"},
    {"name": "Atropisomer-Ethyl imp", "rrt": 1.29, "alt_name": "Atropisomer"},
    {"name": "Atropisomer-Double bond", "rrt": 1.37, "alt_name": "Atropisomer"},
    {"name": "Atropisomer-Keto Imp.", "rrt": 0.80, "alt_name": "Atropisomer"},
    #  GS-peak mapping rows (Peak-1 RRT assignments).
    {"name": "GS-832077 (LCV3 Monomesyl) Peak-1", "rrt": 0.46, "alt_name": "LCV3 Monomesyl"},
    {"name": "GS-837509 (Acetyl) Peak-1", "rrt": 0.49, "alt_name": "Acetyl"},
    {"name": "GS-833248 (LCV Keto) Peak-1", "rrt": 0.80, "alt_name": "LCV Keto"},
    {"name": "GS-833244 (MSC Amine) Peak-1", "rrt": 0.81, "alt_name": "MSC Amine"},
    {"name": "GS-837322 (Deschloro) Peak-1", "rrt": 0.85, "alt_name": "Deschloro"},
    {"name": "GS-828793 (Methyl) Peak-1", "rrt": 1.20, "alt_name": "Methyl"},
    {"name": "GS-941756 (Ethyl) Peak-1", "rrt": 1.29, "alt_name": "Ethyl"},
    {"name": "GS-968750 (Double bond) Peak-1", "rrt": 1.37, "alt_name": "Double bond"},
    {"name": "LENA-2078/GS-832078 (Amine) Peak-1", "rrt": 1.13, "alt_name": "Amine"},
    {"name": "LENA-3243/GS-833243 (LKH-IV(i)) Peak-1", "rrt": 1.18, "alt_name": "LKH-IV(i)"},
]


#  The core per-peak % formula, following the A4 against-standard structure but on
#  the STD-1..6 mean-area basis. The standard concentration chain reads the FIRST
#  weighed standard-prep row (`std_preps.*[0]`) — the engine supports `group.field
#  [index]` — and the sample make-up chain comes from `sample_prep`. `stats.mean_std`
#  is the six-injection mean standard area (NOT the pooled BKT mean). The result is
#  the uncorrected %; `_RRF_APPLIED` then applies the RRF and `pct` rounds to 3 dp,
#  mirroring A4's SUM(ROUND(...)) ordering.
_STD_CHAIN_FIRST_ROW = (
    "std_preps.weight_mg[0] / std_preps.vol_1[0] * std_preps.pip_1[0] "
    "/ std_preps.vol_2[0] * std_preps.pip_2[0] / std_preps.vol_3[0]"
)

_PCT_UNCORRECTED = (
    f"area / stats.mean_std * ({_STD_CHAIN_FIRST_ROW}) "
    f"* {sample_chain_terms(prefix='s_', group='sample_prep')} "
    "* std_preps.potency[0] / 100 "
    "* std_preps.mw_base[0] / std_preps.mw_salt[0] "
    "* 100"
)


def _peak_calculated_fields() -> list[dict]:
    """The four calculated columns shared by the known and unknown peak tables."""
    return [
        {
            "key": "pct_uncorrected",
            "kind": "calculated",
            "label": "% Impurity (before RRF)",
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
            #  Below-reporting-threshold rows contribute nothing to the totals.
            "expression": "if(pct < loq, 0, pct)",
        },
        {
            "key": "reported",
            "kind": "calculated",
            "label": "Reporting % Impurity",
            #  Text, not a number: a value under the reporting threshold is not a
            #  measurement and must print as BLQ.
            "expression": 'if(pct < loq, "BLQ", pct)',
        },
    ]


LENA_RS_DEFINITION = {
    "resultRef": "summary.total_all",
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
                "key": "product_name",
                "kind": "context",
                "type": "text",
                "label": "Product Name",
                "source": "product.name",
                "overridable": True,
            },
            {
                "key": "active_name",
                "kind": "context",
                "type": "text",
                "label": "Active",
                "default": "Lenacapavir Na",
                "overridable": True,
            },
            {
                "key": "standard_name",
                "kind": "context",
                "type": "text",
                "label": "Standard Name",
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
                "key": "sample_details",
                "kind": "context",
                "type": "text",
                "label": "Sample Details",
                "overridable": True,
            },
            {
                "key": "standard_details",
                "kind": "context",
                "type": "text",
                "label": "Standard Details",
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
        #  STD-1..6 weighed standard preparations (one row each). Every column the
        #  sheet's Standard block shows is present so the block reproduces; the
        #  concentration chain + MW correction mirror `_common.standard_group`.
        {
            "key": "std_preps",
            "kind": "table",
            "label": "Standard Preparations (STD-1..6)",
            "rows": {"min": 1, "max": 6, "default": 6, "labelFrom": "name"},
            "fields": [
                {"key": "name", "kind": "input", "type": "text", "label": "Standard Prep"},
                {"key": "weight_mg", "kind": "input", "label": "Weight", "unit": "mg", "required": True},
                {"key": "vol_1", "kind": "input", "label": "V.F. (mL)", "unit": "mL", "required": True},
                {"key": "pip_1", "kind": "input", "label": "Dil. (mL)", "unit": "mL", "default": 1},
                {"key": "vol_2", "kind": "input", "label": "V.F.1 (mL)", "unit": "mL", "default": 1},
                {"key": "pip_2", "kind": "input", "label": "Dil.1 (mL)", "unit": "mL", "default": 1},
                {"key": "vol_3", "kind": "input", "label": "V.F.2 (mL)", "unit": "mL", "default": 1},
                {"key": "lc_mg", "kind": "input", "label": "L.C.", "unit": "mg", "default": 1},
                {"key": "av_wt_mg", "kind": "input", "label": "Av. Wt.", "unit": "mg", "default": 1},
                {"key": "mw_base", "kind": "input", "label": "M.W. Base", "default": 1},
                {"key": "mw_salt", "kind": "input", "label": "M.W. Salt", "default": 1},
                {"key": "potency", "kind": "input", "label": "Potency", "unit": "%", "default": 100},
                {
                    "key": "conc_ppm",
                    "kind": "calculated",
                    "label": "Conc.",
                    "unit": "ppm",
                    "expression": (
                        "weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 "
                        "* mw_base / mw_salt * potency / 100 * 1000"
                    ),
                    "rounding": {"mode": "round", "digits": 3},
                },
                {"key": "area", "kind": "area", "label": "STD Area"},
            ],
        },
        #  Bracketing (BKT) standard injections — one area column, starts empty.
        {
            "key": "bkt",
            "kind": "table",
            "label": "Bracketing Standard (BKT)",
            "rows": {"min": 0, "max": 6, "default": 0},
            "fields": [
                {"key": "area", "kind": "area", "label": "BKT STD Area"},
            ],
        },
        #  Standard statistics: STD-1..6 mean/SD/%RSD and the BKT (pooled) mean +
        #  %RSD. The impurity denominator is `stats.mean_std` (the six-injection
        #  mean), matching the other RS/content templates.
        {
            "key": "stats",
            "kind": "singleton",
            "label": "Standard Statistics",
            "fields": [
                {
                    "key": "mean_std",
                    "kind": "calculated",
                    "label": "Mean STD Area",
                    "expression": "mean(std_preps.area)",
                    "rounding": {"mode": "round", "digits": 0},
                },
                {
                    "key": "sd_std",
                    "kind": "calculated",
                    "label": "SD",
                    "expression": "sd(std_preps.area)",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "rsd_std",
                    "kind": "calculated",
                    "label": "%RSD",
                    "unit": "%",
                    "expression": "rsd(std_preps.area)",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "mean_bkt",
                    "kind": "calculated",
                    "label": "BKT Mean STD Area",
                    "expression": "mean(pool(std_preps.area, bkt.area))",
                    "rounding": {"mode": "round", "digits": 0},
                },
                {
                    "key": "rsd_bkt",
                    "kind": "calculated",
                    "label": "BKT %RSD",
                    "unit": "%",
                    "expression": "rsd(pool(std_preps.area, bkt.area))",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
        #  System-suitability / sensitivity block. Observed values are inputs the
        #  analyst records off the UPLC; the sensitivity ratio is the one computed
        #  field. Tailing/resolution/RT are text-tolerant (allow "NA").
        {
            "key": "sst",
            "kind": "singleton",
            "label": "System Suitability / Sensitivity",
            "fields": [
                {
                    "key": "area_lena2_sensitivity",
                    "kind": "input",
                    "label": "Area of Lenacapavir-2 Peak from Sensitivity",
                },
                {
                    "key": "area_lena2_std",
                    "kind": "input",
                    "label": "Area of Lenacapavir-2 Peak from STD / Inj-1",
                },
                {
                    "key": "sensitivity_ratio",
                    "kind": "calculated",
                    "label": "Sensitivity Ratio",
                    "expression": "area_lena2_sensitivity / area_lena2_std",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "tailing_lena2",
                    "kind": "input",
                    "type": "text",
                    "label": "Tailing Factor for Lenacapavir-2 Peak (STD/Inj-5)",
                },
                {
                    "key": "resolution_desbromo_keto",
                    "kind": "input",
                    "type": "text",
                    "label": "Resolution Between GS-833150 & GS-833248 (Des Bromo & LCV Keto)",
                },
                {
                    "key": "resolution_amine_lkh",
                    "kind": "input",
                    "type": "text",
                    "label": "Resolution Between LENA-2078 & LENA-3243 (Amine Imp. & LKH IV(i))",
                },
                {
                    "key": "rt_lena2_sample",
                    "kind": "input",
                    "type": "text",
                    "label": "Retention time of Lenacapavir-2 Peak from Sample",
                },
                {
                    "key": "dilution_factor",
                    "kind": "input",
                    "type": "text",
                    "label": "Dilution Factor",
                },
                {
                    "key": "result",
                    "kind": "input",
                    "type": "text",
                    "label": "Result",
                },
                {
                    "key": "limit",
                    "kind": "input",
                    "type": "text",
                    "label": "Limit",
                },
            ],
        },
        #  Sample preparation: weight, the three-stage dilution chain (prefix s_)
        #  that `sample_chain_terms` resolves, plus Av. Wt. and L.C.
        {
            "key": "sample_prep",
            "kind": "singleton",
            "label": "Sample Preparation",
            "fields": [
                {
                    "key": "sample_weight",
                    "kind": "input",
                    "label": "Weight",
                    "unit": "mg",
                    "required": True,
                },
                *dilution_fields("s_"),
                {"key": "av_wt", "kind": "input", "label": "Av. Wt.", "unit": "mg", "default": 1},
                {"key": "lc_mg", "kind": "input", "label": "L.C.", "unit": "mg", "default": 1},
            ],
        },
        #  Known impurities — hard-coded names + RRT from `_KNOWN_IMPURITIES`.
        #  RRT is an INPUT (the sheet gives fixed RRTs per named impurity). RRF
        #  defaults to 1.0; the sheet gives no RRF for these peaks.
        {
            "key": "known_impurities",
            "kind": "table",
            "label": "Known Impurities",
            "rows": {
                "min": 1,
                "max": max(40, len(_KNOWN_IMPURITIES)),
                "default": len(_KNOWN_IMPURITIES),
                "labelFrom": "name",
            },
            "fields": [
                {"key": "name", "kind": "input", "type": "text", "label": "Impurity"},
                {"key": "alt_name", "kind": "input", "type": "text", "label": "Alt. Name (Emcure/Hetero)"},
                {"key": "rrt", "kind": "input", "label": "RRT"},
                {"key": "rrf", "kind": "input", "label": "RRF", "default": 1},
                {"key": "loq", "kind": "input", "label": "Reporting Threshold", "unit": "%", "default": 0.05},
                {"key": "area", "kind": "area", "label": "Area"},
                *_peak_calculated_fields(),
            ],
        },
        #  Unknown impurities — generic names, RT/RRT recorded, RRF default 1.0.
        {
            "key": "unknowns",
            "kind": "table",
            "label": "Unknown Impurities (Unknown-1..27)",
            "rows": {"min": 1, "max": 27, "default": 5, "labelFrom": "name"},
            "fields": [
                {"key": "name", "kind": "input", "type": "text", "label": "Unknown"},
                {"key": "rt", "kind": "input", "label": "RT", "unit": "min"},
                {"key": "rrt", "kind": "input", "label": "RRT"},
                {"key": "rrf", "kind": "input", "label": "RRF", "default": 1},
                {"key": "loq", "kind": "input", "label": "Reporting Threshold", "unit": "%", "default": 0.05},
                {"key": "area", "kind": "area", "label": "Area"},
                *_peak_calculated_fields(),
            ],
        },
        #  Reporting roll-ups. Each guarded with isblank(mean(...)) so an untouched
        #  sheet reports blank, not 0.000. Knowns and unknowns live in separate
        #  tables so each total sums its own column without a dependency cycle.
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
                {
                    "key": "total_knowns",
                    "kind": "calculated",
                    "label": "Total of Known Impurities",
                    "unit": "%",
                    "expression": (
                        "if(isblank(mean(known_impurities.pct)), blank(), "
                        "sum(known_impurities.pct_for_total))"
                    ),
                    "rounding": {"mode": "round", "digits": 3},
                },
                {
                    "key": "total_all",
                    "kind": "calculated",
                    "label": "Total Known + Unknown Impurities",
                    "unit": "%",
                    "expression": (
                        "if(isblank(mean(pool(known_impurities.pct, unknowns.pct))), "
                        "blank(), "
                        "sum(known_impurities.pct_for_total) + sum(unknowns.pct_for_total))"
                    ),
                    "rounding": {"mode": "round", "digits": 3},
                },
            ],
        },
    ],
    "criteria": [
        #  STD-1..6 %RSD, NMT 1.5.
        sst_rsd_criterion("stats.rsd_std", 1.5),
        #  BKT %RSD, NMT 1.5.
        {
            "key": "sst_bkt_rsd",
            "label": "%RSD of bracketing standard injections",
            "target": "stats.rsd_bkt",
            "operator": "lte",
            "limit": 1.5,
            "severity": "blocking",
            "limitText": "NMT 1.5 %",
        },
        #  Sensitivity ratio BETWEEN 0.70 and 1.30.
        {
            "key": "sensitivity_ratio_range",
            "label": "Sensitivity Ratio",
            "target": "sst.sensitivity_ratio",
            "operator": "between",
            "limit": [0.70, 1.30],
            "severity": "blocking",
            "limitText": "0.70 to 1.30",
        },
        #  Tailing BETWEEN 0.8 and 1.5 (advisory; a text "NA" entry evaluates
        #  blank → not assessed).
        {
            "key": "tailing_range",
            "label": "Tailing Factor for Lenacapavir-2 Peak",
            "target": "sst.tailing_lena2",
            "operator": "between",
            "limit": [0.8, 1.5],
            "severity": "advisory",
            "limitText": "0.8 to 1.5",
        },
    ],
}

LENA_RS = SeedTemplate(
    code="TPL-A4-0003",
    name="Related substance_RS-1_Lenacapavir injection",
    archetype="A4",
    result_unit="%",
    test_code="TST-RS-LENA",
    test_name="Related Substances — Lenacapavir Injection 309mg/mL",
    test_type="Quantitative",
    definition=LENA_RS_DEFINITION,
)

TEMPLATES = [LENA_RS]
