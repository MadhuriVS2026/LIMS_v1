"""
A1 — assay / potency against an external standard.

The reference archetype, proven against the real `Assay by HPLC.xlsx` in
`tests/calculation/test_assay_template_e2e.py`: that sheet's own inputs give a
reportable mean assay of 108.838 %.

Two features here are unique to A1 among the seeded templates:

* **Bracketing standards pool cumulatively.** Block *k*'s statistics run over the
  initial replicates ∪ blocks 1..k, never over the bracketing injections alone.
  Averaging a bracket by itself would let a drifting system pass suitability.
* **Standard co-relation** between two independently weighed standards, as a
  weight-normalised response ratio. Advisory, because a co-relation slightly out
  is a weighing question rather than grounds to discard the run.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
    dilution_fields,
    sample_chain_terms,
    standard_chain_terms,
    standard_group,
)

A1_DEFINITION = {
    "resultRef": "samples.pct_mean_assay",
    #  Extra context auto-fetched from the TRF header for the Sample Preparations
    #  header strip (batch is already seeded by context_header as `batch_no`).
    "context": context_header(
        extra=[
            {
                "key": "stability_condition",
                "kind": "context",
                "type": "text",
                "label": "Stability Condition",
                "source": "trf.stage_of_sample",
            },
            {
                "key": "packing_detail_hdr",
                "kind": "context",
                "type": "text",
                "label": "Packing Detail",
                "source": "trf.pack_details",
            },
            {
                "key": "trf_no",
                "kind": "context",
                "type": "text",
                "label": "TRF No.",
                "source": "trf.trf_number",
            },
            {
                "key": "ar_no",
                "kind": "context",
                "type": "text",
                "label": "AR No.",
                "source": "trf.ar_number",
            },
        ],
    ),
    "groups": [
        standard_group(conc_label="Concentration"),
        {
            "key": "std_areas",
            "kind": "table",
            "label": "Standard Replicate Injections",
            "rows": {"min": 1, "max": 6, "default": 5},
            "fields": [{"key": "area", "kind": "area", "label": "STD Area"}],
            #  Compact summary rendered under the table (display-only; the values
            #  themselves are computed in the `stats` group below).
            "footer": [
                {"label": "Mean", "ref": "stats.mean_std"},
                {"label": "SD", "ref": "stats.sd_std"},
                {"label": "% RSD", "ref": "stats.rsd_std", "unit": "%"},
            ],
        },
        {
            "key": "bkt_1",
            "kind": "table",
            "label": "Bracketing Standard — Block 1",
            "rows": {"min": 0, "max": 20, "default": 2},
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
            #  Pooled with the initial replicates (std_areas ∪ bkt_1), matching
            #  the statistics section — averaging a bracket alone would let a
            #  drifting system pass suitability.
            "footer": [
                {"label": "Mean (pooled)", "ref": "stats.mean_bkt_1"},
                {"label": "SD (pooled)", "ref": "stats.sd_bkt_1"},
                {"label": "% RSD (pooled)", "ref": "stats.rsd_bkt_1", "unit": "%"},
            ],
        },
        {
            "key": "bkt_2",
            "kind": "table",
            "label": "Bracketing Standard — Block 2",
            "rows": {"min": 0, "max": 20, "default": 1},
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
            #  Pooled with std_areas ∪ bkt_1 ∪ bkt_2.
            "footer": [
                {"label": "Mean (pooled)", "ref": "stats.mean_bkt_2"},
                {"label": "SD (pooled)", "ref": "stats.sd_bkt_2"},
                {"label": "% RSD (pooled)", "ref": "stats.rsd_bkt_2", "unit": "%"},
            ],
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
                {
                    "key": "mean_std",
                    "kind": "calculated",
                    "label": "Mean STD Area",
                    "expression": "mean(std_areas.area)",
                },
                {"key": "sd_std", "kind": "calculated", "label": "SD",
                 "expression": "sd(std_areas.area)"},
                {"key": "rsd_std", "kind": "calculated", "label": "%RSD", "unit": "%",
                 "expression": "rsd(std_areas.area)"},
                {
                    "key": "mean_bkt_1",
                    "kind": "calculated",
                    "label": "Mean (pooled BKT 1)",
                    "expression": "mean(pool(std_areas.area, bkt_1.area))",
                },
                {
                    "key": "sd_bkt_1",
                    "kind": "calculated",
                    "label": "SD (pooled BKT 1)",
                    "expression": "sd(pool(std_areas.area, bkt_1.area))",
                },
                {
                    "key": "rsd_bkt_1",
                    "kind": "calculated",
                    "label": "%RSD (pooled BKT 1)",
                    "unit": "%",
                    "expression": "rsd(pool(std_areas.area, bkt_1.area))",
                },
                {
                    "key": "mean_bkt_2",
                    "kind": "calculated",
                    "label": "Mean (pooled BKT 2)",
                    "expression": "mean(pool(std_areas.area, bkt_1.area, bkt_2.area))",
                },
                {
                    "key": "sd_bkt_2",
                    "kind": "calculated",
                    "label": "SD (pooled BKT 2)",
                    "expression": "sd(pool(std_areas.area, bkt_1.area, bkt_2.area))",
                },
                {
                    "key": "rsd_bkt_2",
                    "kind": "calculated",
                    "label": "%RSD (pooled BKT 2)",
                    "unit": "%",
                    "expression": "rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))",
                },
                {
                    "key": "std_corelation",
                    "kind": "calculated",
                    "label": "Standard Co-relation",
                    "unit": "%",
                    #  TRUNC applied to the ratio, then ×100 — so 0.9997 becomes
                    #  99.9, not 100.0.
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
            #  Read-only summary auto-fetched from the TRF header, shown above the
            #  editable preparation rows.
            "headerContext": [
                {"label": "Batch No.", "ref": "batch_no"},
                {"label": "Stability Condition", "ref": "stability_condition"},
                {"label": "Packing Detail", "ref": "packing_detail_hdr"},
                {"label": "TRF No.", "ref": "trf_no"},
                {"label": "AR No.", "ref": "ar_no"},
            ],
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
                {"key": "area_1", "kind": "area", "label": "Area 1"},
                {"key": "area_2", "kind": "area", "label": "Area 2"},
                {
                    "key": "avg_area",
                    "kind": "calculated",
                    "label": "Avg. Area",
                    "expression": "mean([area_1, area_2])",
                },
                {
                    "key": "pct_assay",
                    "kind": "calculated",
                    "label": "% Assay",
                    "unit": "%",
                    "expression": (
                        f"avg_area / stats.mean_std * {standard_chain_terms()} "
                        f"* {sample_chain_terms()} "
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

A1 = SeedTemplate(
    code="TPL-A1-0001",
    name="Assay by HPLC (external standard)",
    archetype="A1",
    result_unit="%",
    test_code="TST-03",
    test_name="Assay (Propofol)",
    test_type="Quantitative",
    definition=A1_DEFINITION,
)

TEMPLATES = [A1]
