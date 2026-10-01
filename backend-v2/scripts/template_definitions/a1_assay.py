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
    "resultRef": "stats.pct_mean_assay",
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
            #  Weights for the two standards in the co-relation. STD-1 weight is
            #  taken from Standard Details; STD-2 weight is entered manually.
            "key": "corel_weights",
            "kind": "singleton",
            "label": "Standard Co-relation — Weights",
            "fields": [
                {
                    "key": "std1_weight",
                    "kind": "calculated",
                    "label": "STD-1 Weight",
                    "unit": "mg",
                    "expression": "standard.weight_mg",
                },
                {"key": "std2_weight", "kind": "input", "label": "STD-2 Weight", "unit": "mg"},
            ],
        },
        {
            #  STD-2 injection areas only (add rows up to 6). STD-1's side of the
            #  co-relation is taken from the Standard Replicate Injections mean,
            #  so it is not re-entered here. The column mean feeds the co-relation.
            "key": "corel_areas",
            "kind": "table",
            "label": "Standard Co-relation — Areas (STD 2)",
            "rows": {"min": 1, "max": 6, "default": 6},
            "fields": [
                {"key": "std2_area", "kind": "area", "label": "STD 2 Area"},
            ],
            "footer": [
                {"label": "Mean (STD 1) — from replicates", "ref": "std_2.mean_std1"},
                {"label": "Mean (STD 2)", "ref": "std_2.mean_std2"},
                {"label": "Standard Co-relation", "ref": "stats.std_corelation", "unit": "%"},
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
                    #  Co-relation STD-2 mean area (STD-1 side is `mean_std`,
                    #  autofetched from the replicate injections).
                    "key": "mean_std2",
                    "kind": "calculated",
                    "label": "Mean STD 2 Area",
                    "expression": "mean(corel_areas.std2_area)",
                },
                {
                    "key": "std_corelation",
                    "kind": "calculated",
                    "label": "Standard Co-relation",
                    "unit": "%",
                    #  Weight-normalised response ratio: (mean STD-1 area /
                    #  mean STD-2 area) × (STD-2 weight / STD-1 weight). STD-1 mean
                    #  comes from the replicate injections (stats.mean_std). TRUNC
                    #  the ratio, then ×100 — so 0.9997 becomes 99.9, not 100.0.
                    "expression": (
                        "trunc(stats.mean_std / stats.mean_std2 "
                        "* corel_weights.std2_weight / standard.weight_mg, 3) * 100"
                    ),
                },
                {
                    #  Reportable mean assay across all sample preparations. Shown
                    #  in bold below the Sample Preparations table (its footer).
                    "key": "pct_mean_assay",
                    "kind": "calculated",
                    "label": "% Mean Assay",
                    "unit": "%",
                    "expression": "mean(samples.pct_assay)",
                    "rounding": {"mode": "round", "digits": 2},
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
                #  Label Claim shown per row (read-only), echoing the single
                #  worksheet Label Claim — auto-filled from the TRF when numeric,
                #  else entered manually in the Context section. Divisor in %Assay.
                {
                    "key": "lc",
                    "kind": "calculated",
                    "label": "Label Claim (L.C.)",
                    "expression": "label_claim",
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
            ],
            #  % Mean Assay is a single value for the whole sample set, so it is
            #  shown once in bold below the table rather than repeated per row.
            "footer": [
                {"label": "% Mean Assay", "ref": "stats.pct_mean_assay", "unit": "%"},
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
            "target": "stats.rsd_bkt_1",
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
