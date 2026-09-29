"""
Archetype A1 — assay / potency against an external standard.

Source: `Test types/Assay by HPLC.xlsx` (Amphotericin B Liposome 50 mg/vial).
Proven end to end in `tests/calculation/test_assay_template_e2e.py`; that sheet's
own inputs give a reportable mean assay of 108.838 %.

This is the master equation the majority of the chromatographic workbooks reduce
to. Read it as four independent factors:

    response ratio  ×  standard dilution chain  ×  sample dilution chain  ×  basis

Two changes from the test's copy, both needed for it to work through the
application rather than only through the evaluator:

1. Context `source` paths are rewritten to ones `WorksheetService._seed_context`
   actually resolves. The test drove the evaluator directly and passed context in
   by hand, so its `product.labelClaim` / `test.methodNo` paths resolved nowhere.
2. Context fields with no resolvable source are marked `overridable`. A context
   field with no source, not overridable and no default can never hold a value —
   it renders as a permanently blank read-only box.

`label_claim` is deliberately not sourced from `trf.label_claim`: that column is
free text ("50 mg/vial") and this field is a divisor, so a string would blank the
whole chain.
"""
from scripts.template_definitions.common import (
    analyst_context,
    batch_context,
    product_context,
    numeric_context,
    text_context,
)

A1_ASSAY_HPLC = {
    "resultRef": "samples.pct_mean_assay",
    "context": [
        product_context("generic_name", "Generic Name"),
        batch_context("batch_no", "Batch No."),
        numeric_context("label_claim", "Label Claim", unit="mg"),
        numeric_context("avg_weight", "Average Weight / Vial", default=1),
        text_context("method_no", "Method No."),
        text_context("instrument_id", "Instrument ID"),
        analyst_context("analysed_by", "Analysed By"),
        {
            "key": "date_of_analysis",
            "kind": "context",
            "type": "date",
            "label": "Date of Analysis",
            "source": "session.date",
        },
    ],
    "groups": [
        {
            "key": "standard",
            "kind": "singleton",
            "label": "Standard Details",
            "fields": [
                {"key": "name", "kind": "input", "type": "text", "label": "Standard Name"},
                {"key": "weight_mg", "kind": "input", "label": "Weight", "unit": "mg", "required": True},
                {"key": "vol_1", "kind": "input", "label": "Vol 1", "unit": "mL", "required": True},
                {"key": "pip_1", "kind": "input", "label": "Pip 1", "unit": "mL", "default": 1},
                {"key": "vol_2", "kind": "input", "label": "Vol 2", "unit": "mL", "default": 1},
                {"key": "pip_2", "kind": "input", "label": "Pip 2", "unit": "mL", "default": 1},
                {"key": "vol_3", "kind": "input", "label": "Vol 3", "unit": "mL", "default": 1},
                {"key": "mw_base", "kind": "input", "label": "MW — Base", "default": 1},
                {"key": "mw_salt", "kind": "input", "label": "MW — Salt", "default": 1},
                {"key": "potency", "kind": "input", "label": "Potency", "unit": "%", "default": 100},
                {
                    "key": "conc_ppm",
                    "kind": "calculated",
                    "label": "Concentration",
                    "unit": "ppm",
                    "expression": (
                        "weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 "
                        "* mw_base / mw_salt * potency / 100 * 1000"
                    ),
                },
            ],
        },
        {
            "key": "std_areas",
            "kind": "table",
            "label": "Standard Replicate Injections",
            "rows": {"min": 1, "max": 6, "default": 5},
            "fields": [{"key": "area", "kind": "area", "label": "STD Area"}],
        },
        {
            "key": "bkt_1",
            "kind": "table",
            "label": "Bracketing Standard — Block 1",
            "rows": {"min": 0, "max": 6, "default": 2},
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
        },
        {
            "key": "bkt_2",
            "kind": "table",
            "label": "Bracketing Standard — Block 2",
            "rows": {"min": 0, "max": 6, "default": 1},
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
        },
        {
            "key": "std_2",
            "kind": "singleton",
            "label": "Second Standard (co-relation)",
            "fields": [
                {"key": "weight_mg", "kind": "input", "label": "STD-2 Weight", "unit": "mg"},
                {"key": "area_1", "kind": "area", "label": "Area 1"},
                {"key": "area_2", "kind": "area", "label": "Area 2"},
                {
                    "key": "mean_area",
                    "kind": "calculated",
                    "label": "Mean Area",
                    "expression": "mean([area_1, area_2])",
                },
            ],
        },
        {
            "key": "stats",
            "kind": "singleton",
            "label": "Standard Statistics",
            "fields": [
                {"key": "mean_std", "kind": "calculated", "label": "Mean STD Area",
                 "expression": "mean(std_areas.area)"},
                {"key": "sd_std", "kind": "calculated", "label": "SD",
                 "expression": "sd(std_areas.area)"},
                {"key": "rsd_std", "kind": "calculated", "label": "%RSD", "unit": "%",
                 "expression": "rsd(std_areas.area)"},
                #  Decision 6: bracketing statistics pool the initial replicates
                #  in, cumulatively — never the bracketing injections alone.
                {"key": "mean_bkt_1", "kind": "calculated", "label": "Mean (pooled BKT 1)",
                 "expression": "mean(pool(std_areas.area, bkt_1.area))"},
                {"key": "rsd_bkt_1", "kind": "calculated", "label": "%RSD (pooled BKT 1)",
                 "unit": "%", "expression": "rsd(pool(std_areas.area, bkt_1.area))"},
                {"key": "mean_bkt_2", "kind": "calculated", "label": "Mean (pooled BKT 2)",
                 "expression": "mean(pool(std_areas.area, bkt_1.area, bkt_2.area))"},
                {"key": "rsd_bkt_2", "kind": "calculated", "label": "%RSD (pooled BKT 2)",
                 "unit": "%", "expression": "rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))"},
                {
                    "key": "std_corelation",
                    "kind": "calculated",
                    "label": "Standard Co-relation",
                    "unit": "%",
                    #  Sheet Q23: truncation happens on the ratio, then ×100.
                    "expression": (
                        "trunc(stats.mean_std / std_2.mean_area "
                        "* std_2.weight_mg / standard.weight_mg, 3) * 100"
                    ),
                },
            ],
        },
        {
            "key": "samples",
            "kind": "table",
            "label": "Sample Preparations",
            "rows": {"min": 1, "max": 32, "default": 2},
            "fields": [
                {"key": "prep_ref", "kind": "input", "type": "text", "label": "Prep. Ref."},
                {"key": "packing_detail", "kind": "input", "type": "text", "label": "Packing"},
                {"key": "sample_weight", "kind": "input", "label": "Sample Wt.", "required": True},
                {"key": "s_vol_1", "kind": "input", "label": "Vol 1", "unit": "mL", "required": True},
                {"key": "s_pip_1", "kind": "input", "label": "Pip 1", "unit": "mL", "default": 1},
                {"key": "s_vol_2", "kind": "input", "label": "Vol 2", "unit": "mL", "default": 1},
                {"key": "s_pip_2", "kind": "input", "label": "Pip 2", "unit": "mL", "default": 1},
                {"key": "s_vol_3", "kind": "input", "label": "Vol 3", "unit": "mL", "default": 1},
                {"key": "area_1", "kind": "area", "label": "Area 1"},
                {"key": "area_2", "kind": "area", "label": "Area 2"},
                {"key": "avg_area", "kind": "calculated", "label": "Avg. Area",
                 "expression": "mean([area_1, area_2])"},
                {
                    "key": "pct_assay",
                    "kind": "calculated",
                    "label": "% Assay",
                    "unit": "%",
                    "expression": (
                        "avg_area / stats.mean_std "
                        "* standard.weight_mg / standard.vol_1 "
                        "* standard.pip_1 / standard.vol_2 "
                        "* standard.pip_2 / standard.vol_3 "
                        "* s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 "
                        "* s_vol_1 / sample_weight "
                        "* avg_weight / label_claim "
                        "* standard.potency * standard.mw_base / standard.mw_salt"
                    ),
                },
                {
                    "key": "pct_mean_assay",
                    "kind": "calculated",
                    "label": "% Mean Assay",
                    "unit": "%",
                    "expression": "mean(samples.pct_assay)",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
    ],
    "criteria": [
        {
            "key": "sst_std_rsd",
            "label": "%RSD of standard replicate injections",
            "target": "stats.rsd_std",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        {
            "key": "sst_bkt_rsd",
            "label": "%RSD of pooled bracketing standards",
            "target": "stats.rsd_bkt_2",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        {
            "key": "std_corelation",
            "label": "Standard co-relation",
            "target": "stats.std_corelation",
            "operator": "between",
            "limit": [98.0, 102.0],
            "severity": "advisory",
            "limitText": "98.0 % to 102.0 %",
        },
    ],
}
