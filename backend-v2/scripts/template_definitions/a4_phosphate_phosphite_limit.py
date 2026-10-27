"""
A4 — Limit of Phosphate & Phosphite by ion chromatography.

A limit test for two inorganic anions reported against a weighed reference
standard. It is the A4 (chromatographic-against-standard) shape: a weighed
standard with its dilution chain, a replicate-injection set with Mean/SD/%RSD
suitability, bracketing standards pooled into the %RSD for drift control, and a
sample table that back-calculates each analyte from the standard response.

## Why bracketing standards

The sheet brackets the sample injections with standard injections and judges
suitability on the *pooled* %RSD (initial replicates + each bracket), not on the
opening replicates alone — a system that drifts over a long sequence would pass
on its first five injections and still misreport the samples run hours later.
This reuses the same pooled-%RSD construction as the liposomal Free & Entrapped
template (`TPL-A12-0001`): `rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))`,
with both bracketing blocks starting empty (0 rows) so a worksheet never shows
injections that were not run.

## Standard and sample tables — reused generalised blocks

The main-standard block, its replicate table, and the statistics footer are the
shared helpers in `_common.py` (`standard_group`, `replicate_area_group`,
`standard_statistics_group`), identical to every other HPLC/IC archetype, so a
fix to the concentration chain or the %RSD maths lands here too. The two analytes
(phosphate, phosphite) are rows in one sample table rather than fixed columns,
so the same template serves a method that reports only one of them.

## The limit maths

Each analyte is expressed as a percentage of its label-claim limit:

    content (ppm) = area / mean_std
                    × (standard concentration chain, ppm)
                    × (sample chain, inverted)
    % of limit    = content / limit_ppm × 100

The standard concentration and the sample chain are the generalised chain terms
(`standard_chain_terms`, `sample_chain_terms`), so the algebra matches the assay
and related-substances sheets a reviewer compares against. `limit_ppm` is a
per-row input (each anion carries its own specification), defaulting to the
Phosphate / Phosphite limits but editable.

Reported to the pass/fail against the limit as a percentage; the reportable
(`resultRef`) is the larger of the two analytes' % of limit, since the test
passes only if *every* anion is within its limit.
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

#  Bracketing blocks start empty and grow as brackets are actually injected.
#  Pre-filling blank rows would show injections that never happened on a
#  worksheet meant to be a record of what was run — same convention as A12-0001.
_BKT_ROWS = {"min": 0, "max": 6, "default": 0}


#  Standard statistics with the pooled-bracketing %RSD alongside the opening
#  replicate %RSD, so suitability is judged across the whole injection sequence.
_PP_STATS_GROUP = {
    "key": "stats",
    "kind": "singleton",
    "label": "Standard Statistics",
    "fields": [
        {
            "key": "mean_std",
            "kind": "calculated",
            "label": "Mean STD Area",
            "expression": "mean(std_areas.area)",
        },
        {
            "key": "sd_std",
            "kind": "calculated",
            "label": "SD",
            "expression": "sd(std_areas.area)",
        },
        {
            "key": "rsd_std",
            "kind": "calculated",
            "label": "%RSD",
            "unit": "%",
            "expression": "rsd(std_areas.area)",
        },
        {
            "key": "rsd_bkt",
            "kind": "calculated",
            "label": "%RSD (pooled with bracketing standards)",
            "unit": "%",
            #  Cumulative pooling: a bracket averaged on its own would let a
            #  drifting system pass suitability.
            "expression": "rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))",
        },
    ],
}


def _analyte_fields() -> list[dict]:
    """
    One row per anion (Phosphate, Phosphite). Each row carries its own dilution
    chain, its injected area, and its specification limit, then back-calculates
    the content and expresses it as a percentage of that limit.
    """
    return [
        {"key": "name", "kind": "input", "type": "text", "label": "Analyte"},
        {
            "key": "sample_weight",
            "kind": "input",
            "label": "Sample Wt.",
            "unit": "mg",
            "required": True,
        },
        *dilution_fields("s_"),
        {"key": "area", "kind": "area", "label": "Area", "unit": "µS·min"},
        {
            "key": "limit_ppm",
            "kind": "input",
            "label": "Specification Limit",
            "unit": "ppm",
            #  Per-row: each anion carries its own limit. Editable per method.
            "default": 100,
            "required": True,
        },
        {
            "key": "content_ppm",
            "kind": "calculated",
            "label": "Content",
            "unit": "ppm",
            #  area / mean_std × standard conc chain (ppm) × inverted sample chain.
            #  The sample-prep fields live in this same row, so the chain terms are
            #  unqualified. ×1e3 in the standard chain already yields ppm.
            "expression": (
                f"area / stats.mean_std * {standard_chain_terms()} "
                "* standard.mw_base / standard.mw_salt * standard.potency / 100 "
                f"* {sample_chain_terms('s_')} * 1000"
            ),
            #  Truncated, as for the trace-impurity sheet: a limit test must not
            #  round a result up across its specification.
            "rounding": {"mode": "trunc", "digits": 4},
        },
        {
            "key": "pct_of_limit",
            "kind": "calculated",
            "label": "% of Limit",
            "unit": "%",
            "expression": "content_ppm / limit_ppm * 100",
            "rounding": {"mode": "trunc", "digits": 2},
        },
    ]


A4_PP_DEFINITION = {
    #  The test passes only if every anion is within its limit, so the reportable
    #  is the worst case — the largest % of limit across the analyte rows.
    "resultRef": "summary.max_pct_of_limit",
    "context": context_header(
        #  Label claim is not a divisor here (each analyte carries its own
        #  `limit_ppm`), so it is not needed; average weight likewise.
        label_claim=False,
        avg_weight=False,
        extra=[
            {
                "key": "test_name_hdr",
                "kind": "context",
                "type": "text",
                "label": "Test",
                "default": "Limit of Phosphate & Phosphite",
                "overridable": True,
            },
            {
                "key": "analysis_as_per",
                "kind": "context",
                "type": "text",
                "label": "Analysis as per",
                "overridable": True,
            },
        ],
    ),
    "groups": [
        #  Generalised weighed-standard block + its dilution chain + concentration.
        standard_group(
            label="Standard Details", conc_label="Standard Concentration"
        ),
        #  Generalised replicate-injection table with the Mean/SD/%RSD footer.
        replicate_area_group(label="Standard Replicate Injections", default_rows=5),
        #  Two bracketing-standard blocks, starting empty, pooled into suitability.
        {
            "key": "bkt_1",
            "kind": "table",
            "label": "Bracketing Standard — Block 1",
            "rows": _BKT_ROWS,
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
        },
        {
            "key": "bkt_2",
            "kind": "table",
            "label": "Bracketing Standard — Block 2",
            "rows": _BKT_ROWS,
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
        },
        _PP_STATS_GROUP,
        {
            "key": "analytes",
            "kind": "table",
            "label": "Sample — Phosphate & Phosphite",
            #  Two anions by default; the range lets a single-anion method or an
            #  extra ion use the same template. Row label is the analyte name.
            "rows": {"min": 1, "max": 6, "default": 2, "labelFrom": "name"},
            "fields": _analyte_fields(),
        },
        {
            "key": "summary",
            "kind": "singleton",
            "label": "Summary",
            "fields": [
                {
                    "key": "max_pct_of_limit",
                    "kind": "calculated",
                    "label": "Maximum % of Limit",
                    "unit": "%",
                    #  Guarded so an untouched worksheet does not report 0.00 % —
                    #  a positive claim that both anions are well within limit from
                    #  an analysis nobody has run.
                    "expression": (
                        "if(isblank(mean(analytes.pct_of_limit)), blank(), "
                        "max(analytes.pct_of_limit))"
                    ),
                    "rounding": {"mode": "trunc", "digits": 2},
                },
            ],
        },
    ],
    "criteria": [
        sst_rsd_criterion(),
        {
            "key": "sst_bkt_rsd",
            "label": "%RSD of pooled bracketing standards",
            "target": "stats.rsd_bkt",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        {
            "key": "within_limit",
            "label": "Each anion within its specification limit",
            "target": "max(analytes.pct_of_limit)",
            "operator": "lte",
            "limit": 100.0,
            "severity": "blocking",
            "limitText": "NMT 100.0 % of limit",
        },
    ],
}

A4_PHOSPHATE_PHOSPHITE = SeedTemplate(
    code="TPL-A4-0002",
    name="Limit of Phosphate & Phosphite",
    archetype="A4",
    result_unit="%",
    test_code="TST-LIM-PP",
    test_name="Limit of Phosphate & Phosphite",
    test_type="Quantitative",
    definition=A4_PP_DEFINITION,
)

TEMPLATES = [A4_PHOSPHATE_PHOSPHITE]
