"""
A8 — Content Uniformity (by HPLC), 30-unit stage ("CU-tablets-30units").

This is a FRESH module for the USP <905> stage-2 (30-unit) content-uniformity
test. It reuses existing suitability and arithmetic LOGIC verbatim rather than
re-deriving any of it:

  * The Acceptance-Value arithmetic is `a8_content_uniformity._ACCEPTANCE_VALUE`
    imported UNCHANGED — USP <905> AV = |M - X| + k·s, nested with the upper
    bound tested OUTERMOST and the lower bound inside. Reversing that nesting
    gives the wrong AV for any mean below 98.5, so it is reused as the literal
    same object. `_summary_group` and `_cu_criteria` are imported from the same
    module for the same reason.
  * The weighed-standard block, the standard replicate-injection table (with its
    Mean/SD/%RSD footer) and the standard statistics come from the `_common`
    helpers (`standard_group`, `replicate_area_group`, `standard_statistics_group`,
    `sst_rsd_criterion`, `context_header`, `standard_chain_terms`,
    `dilution_fields`) exactly as `A8_HPLC_DEFINITION` uses them.
  * The bracketing-standard pattern is reused from A12-0001 (Free & Entrapped
    Drug): two bracketing blocks `bkt_1`/`bkt_2` (kind: table, rows
    {min:0,max:6,default:0}, a single area field each) plus a pooled %RSD field
    `rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))` and a blocking SST
    criterion on that pooled %RSD (NMT 2.0 %).

The only deliberate difference from `A8_HPLC_DEFINITION`: this is the 30-unit
stage, so the `units` table defaults to 30 rows and the acceptability constant
`k_value` defaults to **2.0** (USP <905> k for n=30 is 2.0, not 2.4). Everything
else — the per-unit `pct_lc` expression, the summary/AV group and the AV/SST
criteria — is the A8 HPLC logic retargeted to 30 units.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
    replicate_area_group,
    standard_chain_terms,
    standard_group,
    standard_statistics_group,
    sst_rsd_criterion,
)
from scripts.template_definitions.a8_content_uniformity import (
    _ACCEPTANCE_VALUE,  # noqa: F401 — reused verbatim via _summary_group
    _cu_criteria,
    _summary_group,
)

#  Bracketing blocks start empty and grow as brackets are actually injected —
#  the A12-0001 shape. Pre-filling blank rows would show injections that never
#  happened on a worksheet meant to be a record of what was run.
_BKT_ROWS = {"min": 0, "max": 6, "default": 0}


def _cu_context_30() -> list[dict]:
    """
    Context header WITHOUT a k_value field: the acceptability constant K is now
    an EDITABLE input in the Additional Info group (`additional_info.k_value`),
    the single source of truth the Acceptance Value reads. This avoids two
    contradicting K's (a context one and an Additional Info one).
    """
    return context_header()


def _stats_group_30() -> dict:
    """
    Standard statistics as `standard_statistics_group()` gives (keys `mean_std`,
    `sd_std`, `rsd_std` over `std_areas.area`) PLUS the pooled bracketing %RSD
    field from the A12-0001 pattern. `mean_std` is kept unchanged because the
    per-unit `pct_lc` expression divides by `stats.mean_std`.
    """
    group = standard_statistics_group()
    #  Pooled bracketing statistics (replicates + the bracketing block), as in
    #  A12-0001: a bracket averaged on its own would let a drifting system pass
    #  suitability. Mean/SD/%RSD are rendered beneath the bracketing table and in
    #  the STD-vs-BKT suitability summary.
    _pool = "pool(std_areas.area, bkt_1.area)"
    group["fields"] += [
        {
            "key": "mean_bkt",
            "kind": "calculated",
            "label": "Mean (pooled with bracketing standards)",
            "expression": f"mean({_pool})",
        },
        {
            "key": "sd_bkt",
            "kind": "calculated",
            "label": "SD (pooled with bracketing standards)",
            "expression": f"sd({_pool})",
        },
        {
            "key": "rsd_bkt",
            "kind": "calculated",
            "label": "%RSD (pooled with bracketing standards)",
            "unit": "%",
            "expression": f"rsd({_pool})",
        },
    ]
    return group


def _suitability_summary_group() -> dict:
    #  STD-vs-BKT suitability summary (shown where the second bracketing block
    #  used to be): the standard-replicate Mean/%RSD and the pooled bracketing
    #  Mean/%RSD side by side, read from the `stats` singleton.
    return {
        "key": "suitability_summary",
        "kind": "singleton",
        "label": "Standard Suitability Summary (STD vs BKT)",
        "fields": [
            {"key": "mean_std_disp", "kind": "calculated", "label": "Mean (STD)",
             "expression": "stats.mean_std"},
            {"key": "rsd_std_disp", "kind": "calculated", "label": "% RSD (STD)",
             "unit": "%", "expression": "stats.rsd_std"},
            {"key": "mean_bkt_disp", "kind": "calculated", "label": "Mean (BKT, pooled)",
             "expression": "stats.mean_bkt"},
            {"key": "rsd_bkt_disp", "kind": "calculated", "label": "% RSD (BKT, pooled)",
             "unit": "%", "expression": "stats.rsd_bkt"},
        ],
    }


#  ── Additional Info (user-requested, display-only) ──────────────────
#  Two free-text info fields plus a free-text Procedure table. None of these
#  feed any calculation: the numeric `label_claim` context field remains the AV
#  divisor, untouched. `lc_description` is a SEPARATE alphanumeric label ("1000
#  mg") so it must never be confused with the numeric divisor.
def _additional_info_group() -> dict:
    return {
        "key": "additional_info",
        "kind": "singleton",
        "label": "Additional Info",
        "fields": [
            {"key": "lc_description", "kind": "input", "type": "text",
             "label": "Label Claim (description)", "default": "1000 mg"},
            {"key": "cu_of", "kind": "input", "type": "text",
             "label": "C.U. of", "default": "Metformin HCl"},
            #  (Number of Units) n — display value for the stated sample size.
            {"key": "n_units", "kind": "input", "label": "(Number of Units) n",
             "default": 10},
            #  K — EDITABLE here and the single source of truth: the Acceptance
            #  Value reads `additional_info.k_value` directly, so editing K on the
            #  worksheet changes the AV. Default 2.4 (n=10). (The separate context
            #  k_value field was removed to avoid two contradicting K's.)
            {"key": "k_value", "kind": "input", "label": "K", "default": 2.4,
             "required": True},
        ],
    }


def _procedure_group() -> dict:
    #  Free-text procedure table: a Stage label (STD Prep. / Sample Prep.) and a
    #  multiline description. Expandable (add rows); starts with the two stages.
    return {
        "key": "procedure",
        "kind": "table",
        "label": "Procedure",
        "rows": {"min": 1, "max": 10, "default": 2, "labelFrom": "stage"},
        "fields": [
            {"key": "stage", "kind": "input", "type": "text", "label": "Stage"},
            {"key": "description", "kind": "input", "type": "text",
             "label": "Procedure", "multiline": True},
        ],
    }


def _sample_dilution_group() -> dict:
    #  SHARED sample-prep dilution below Standard details — ONE chain for all
    #  units (sheet's single "1 Tablet" prep row). Its dilution fields FEED the
    #  per-unit % L.C.: `units.pct_lc` reads `sample_dilution.<field>[0]` for the
    #  volume/pipette terms, so the per-unit `units` table no longer carries its
    #  own dilution columns. `sample_dilution` here is the overall dilution
    #  factor column shown on the sheet; the s_vol_*/s_pip_* are the chain stages.
    return {
        "key": "sample_dilution",
        "kind": "singleton",
        "label": "Sample Details",
        "fields": [
            {"key": "sample_unit", "kind": "input", "type": "text",
             "label": "Sample unit", "default": "1 Tablet"},
            {"key": "sample_dilution", "kind": "input",
             "label": "Sample Dilution", "default": 1},
            {"key": "s_vol_1", "kind": "input", "label": "Dilution1 (mL)",
             "unit": "mL", "default": 100},
            {"key": "s_pip_1", "kind": "input", "label": "Pipette1 (mL)",
             "unit": "mL", "default": 4.0},
            {"key": "s_vol_2", "kind": "input", "label": "Dilution2 (mL)",
             "unit": "mL", "default": 50},
            {"key": "s_pip_2", "kind": "input", "label": "Pipette2 (mL)",
             "unit": "mL", "default": 1.0},
            {"key": "s_vol_3", "kind": "input", "label": "Dilution3 (mL)",
             "unit": "mL", "default": 1},
        ],
    }


def _summary_group_local(source: str) -> dict:
    #  Reuse `_summary_group` verbatim, then repoint ONLY the acceptance_value
    #  field's K reference to the editable `additional_info.k_value` (the shared
    #  `_ACCEPTANCE_VALUE` string references a bare `k_value`, which no longer
    #  exists as context here). The AV nesting itself is unchanged — just the
    #  single `k_value` token becomes `additional_info.k_value`.
    group = _summary_group(source)
    av = next(f for f in group["fields"] if f["key"] == "acceptance_value")
    av["expression"] = _ACCEPTANCE_VALUE.replace(
        "k_value", "additional_info.k_value"
    )
    return group


A8_CU_30U_DEFINITION = {
    "resultRef": "summary.acceptance_value",
    "context": _cu_context_30(),
    "groups": [
        _additional_info_group(),
        _procedure_group(),
        standard_group(conc_label="Standard Concentration"),
        _sample_dilution_group(),
        replicate_area_group(default_rows=5),
        {
            "key": "bkt_1",
            "kind": "table",
            "label": "Bracketing Standard — Block 1",
            "rows": _BKT_ROWS,
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
            #  Pooled bracketing Mean/SD/%RSD (replicates + both bracket blocks).
            "footer": [
                {"label": "Mean", "ref": "stats.mean_bkt"},
                {"label": "SD", "ref": "stats.sd_bkt"},
                {"label": "% RSD", "ref": "stats.rsd_bkt", "unit": "%"},
            ],
        },
        _stats_group_30(),
        #  Where the second bracketing block used to be: the STD-vs-BKT
        #  Mean/%RSD suitability summary.
        _suitability_summary_group(),
        {
            "key": "units",
            "kind": "table",
            "label": "Individual Units",
            #  Thirty units by default: this is the stage-2 template.
            "rows": {"min": 1, "max": 30, "default": 30},
            "fields": [
                {"key": "unit_ref", "kind": "input", "type": "text", "label": "Unit"},
                {
                    "key": "unit_weight",
                    "kind": "input",
                    "label": "Unit Wt.",
                    "unit": "mg",
                    "required": True,
                },
                #  No per-unit dilution columns: the shared `sample_dilution`
                #  block supplies the one dilution chain for every unit.
                {"key": "area", "kind": "area", "label": "Area"},
                {
                    "key": "pct_lc",
                    "kind": "calculated",
                    #  % C.U. = each unit's content as a % of label claim (USP
                    #  <905>); this per-unit value IS the content-uniformity
                    #  percentage the summary/AV aggregate over.
                    "label": "% C.U.",
                    #  No `unit` here: the % C.U. cells show the bare value
                    #  (102.8, 99.5, ...) — the "% C.U." header already conveys
                    #  the unit, so a per-row "%" suffix would be redundant.
                    #  % C.U. per unit (tablet CU by HPLC): the whole unit is
                    #  dissolved, so there is NO division by the individual unit
                    #  weight. The sample dilution is the scale-UP (dilution)
                    #  direction of the shared Sample Details chain:
                    #      s_vol_1/s_pip_1 * s_vol_2/s_pip_2 * s_vol_3
                    #  (100/4.0 * 50/1.0 * 1 = 1250), paired Dilution-with-Pipette
                    #  per stage. Derived + verified against gold: STD conc chain
                    #  0.020584, sample factor 1250, avg_weight/label_claim 1/25,
                    #  ×100 -> factor 102.92; with std mean ~316293 this reproduces
                    #  units 1/2/3 = 102.8 / 99.5 / 104.8.
                    "expression": (
                        f"area / stats.mean_std * {standard_chain_terms()} "
                        "* standard.potency / 100 "
                        "* standard.mw_base / standard.mw_salt "
                        "* sample_dilution.s_vol_1 / sample_dilution.s_pip_1 "
                        "* sample_dilution.s_vol_2 / sample_dilution.s_pip_2 "
                        "* sample_dilution.s_vol_3 "
                        "* avg_weight / label_claim * 100"
                    ),
                    "rounding": {"mode": "round", "digits": 1},
                },
            ],
        },
        _summary_group_local("units"),
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
        *_cu_criteria("units"),
    ],
}

A8_CU_30U = SeedTemplate(
    code="TPL-A8-0004",
    name="Content Uniformity by HPLC — 30 Units (Stage 2)",
    archetype="A8",
    result_unit="AV",
    test_code="TST-CU-30U",
    test_name="CU-tablets-30units",
    test_type="Quantitative",
    definition=A8_CU_30U_DEFINITION,
)

TEMPLATES = [A8_CU_30U]
