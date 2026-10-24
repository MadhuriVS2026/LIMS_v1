"""
A1 — Assay for Finished Product, reported in both % and mg/mL.

A clone of the live **TPL-A1-0002 "Assay for Finished Product"** that adds the
two per-sample columns from `Bupivacaine Assay mg ml & Percentage.xlsx`
(sheet '1'): **Assay (mg/mL)** (sheet column Q) and its overall mean
**Mean (mg/mL)** (sheet column R). Everything else — the standard block, the
replicate/bracketing/co-relation tables, the statistics and the base `% Assay` /
`% Mean Assay` — is reproduced verbatim from TPL-A1-0002 so the live DB row stays
byte-for-byte equal to this module.

The base definition is transcribed from the live DB (TPL-A1-0002 exists only in
`lims.db`, never as a declarative module); item-6's byte-for-byte parity check
guards against transcription drift.

## The mg/mL column

Sheet column O (% Assay) and column Q (Assay mg/mL) are algebraically related.
Dropping the terms common to both (and I14/J14 = MW base/salt = 1), the ONLY
differences between the two sheet formulas are:

* O divides by G (the row's L.C.); Q divides by 1.
* O multiplies potency as K14; Q as K14/100.

Therefore **Q = O × L.C. / 100**, i.e. `assay_mgml = pct_assay * label_claim /
100`. This holds to floating-point noise (~1e-15) against the full sheet-Q chain.

This product form (rather than restating the full Q chain) is chosen because the
engine (`evaluator._apply_rounding`) feeds a calculated field's *rounded* value
downstream, and the base `samples.pct_assay` declares **no** rounding — so
`assay_mgml` reads the full-precision % Assay and the product equals the full Q
chain exactly, reproducing the sheet's 2-dp mg/mL gold. It also mirrors the
already-shipped TPL-A12-0001 convention
("Bupivacaine (mg/mL) = %AssayBup × L.C. / 100"). Had `pct_assay` carried
mid-chain rounding, the full Q chain would have been required instead.

`stats.mean_mgml = mean(samples.assay_mgml)` is the overall mean mg/mL across the
sample rows, surfaced the same way as `stats.pct_mean_assay` (a samples-table
footer ref), and reproduces the sheet's block R-mean on the two populated rows.
The base `pct_assay` / `pct_mean_assay` are UNCHANGED; `result_unit` stays `%`
and `resultRef` stays `stats.pct_mean_assay`.
"""
from scripts.template_definitions._common import SeedTemplate

A1_FP_MGML_DEFINITION = {
    "resultRef": "stats.pct_mean_assay",
    "context": [
        {"key": "generic_name", "kind": "context", "type": "text", "label": "Generic Name", "source": "product.name"},
        {"key": "batch_no", "kind": "context", "type": "text", "label": "Batch No.", "source": "trf.batch_number"},
        {"key": "label_claim", "kind": "context", "type": "number", "label": "Label Claim", "source": "trf.label_claim_numeric", "overridable": True},
        {"key": "avg_weight", "kind": "context", "label": "Average Weight / Vial", "default": 1, "overridable": True},
        {"key": "stability_condition", "kind": "context", "type": "text", "label": "Stability Condition", "source": "trf.stage_of_sample"},
        {"key": "packing_detail_hdr", "kind": "context", "type": "text", "label": "Packing Detail", "source": "trf.pack_details"},
        {"key": "trf_no", "kind": "context", "type": "text", "label": "TRF No.", "source": "trf.trf_number"},
        {"key": "ar_no", "kind": "context", "type": "text", "label": "AR No.", "source": "trf.ar_number"},
        {"key": "method_no", "kind": "context", "type": "text", "label": "Method No.", "overridable": True},
        {"key": "instrument_id", "kind": "context", "type": "text", "label": "Instrument ID", "overridable": True},
        {"key": "analysed_by", "kind": "context", "type": "text", "label": "Analysed By", "source": "session.analyst"},
        {"key": "date_of_analysis", "kind": "context", "type": "date", "label": "Date of Analysis", "source": "session.date"},
    ],
    "groups": [
        {
            "key": "standard", "kind": "singleton", "label": "Standard Details",
            "fields": [
                {"key": "name", "kind": "input", "type": "text", "label": "Standard Name"},
                {"key": "weight_mg", "kind": "input", "label": "Weight", "unit": "mg", "required": True},
                {"key": "vol_1", "kind": "input", "label": "Vol 1", "unit": "mL", "required": True},
                {"key": "pip_1", "kind": "input", "label": "Pip 1", "unit": "mL", "default": 1},
                {"key": "vol_2", "kind": "input", "label": "Vol 2", "unit": "mL", "default": 1},
                {"key": "pip_2", "kind": "input", "label": "Pip 2", "unit": "mL", "default": 1},
                {"key": "vol_3", "kind": "input", "label": "Vol 3", "unit": "mL", "default": 1},
                {"key": "mw_base", "kind": "input", "label": "MW \u2014 Base", "default": 1},
                {"key": "mw_salt", "kind": "input", "label": "MW \u2014 Salt", "default": 1},
                {"key": "potency", "kind": "input", "label": "Potency", "unit": "%", "default": 100},
                {"key": "conc_ppm", "kind": "calculated", "label": "Concentration", "unit": "ppm", "expression": "weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000"},
            ],
        },
        {
            "key": "std_areas", "kind": "table", "label": "Standard Replicate Injections",
            "rows": {"min": 1, "max": 6, "default": 5},
            "fields": [{"key": "area", "kind": "area", "label": "STD Area"}],
            "footer": [
                {"label": "Mean", "ref": "stats.mean_std"},
                {"label": "SD", "ref": "stats.sd_std"},
                {"label": "% RSD", "ref": "stats.rsd_std", "unit": "%"},
            ],
        },
        {
            "key": "bkt_1", "kind": "table", "label": "Bracketing Standard \u2014 Block 1",
            "rows": {"min": 0, "max": 20, "default": 2},
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
            "footer": [
                {"label": "Mean (pooled)", "ref": "stats.mean_bkt_1"},
                {"label": "SD (pooled)", "ref": "stats.sd_bkt_1"},
                {"label": "% RSD (pooled)", "ref": "stats.rsd_bkt_1", "unit": "%"},
            ],
        },
        {
            "key": "corel_weights", "kind": "singleton", "label": "Standard Co-relation \u2014 Weights",
            "fields": [
                {"key": "std1_weight", "kind": "calculated", "label": "STD-1 Weight", "unit": "mg", "expression": "standard.weight_mg"},
                {"key": "std2_weight", "kind": "input", "label": "STD-2 Weight", "unit": "mg"},
            ],
        },
        {
            "key": "corel_areas", "kind": "table", "label": "Standard Co-relation \u2014 Areas (STD 2)",
            "rows": {"min": 1, "max": 6, "default": 6},
            "fields": [{"key": "std2_area", "kind": "area", "label": "STD 2 Area"}],
            "footer": [
                {"label": "Mean (STD 1) \u2014 from replicates", "ref": "stats.mean_std"},
                {"label": "Mean (STD 2)", "ref": "stats.mean_std2"},
                {"label": "Standard Co-relation", "ref": "stats.std_corelation", "unit": "%"},
            ],
        },
        {
            "key": "stats", "kind": "singleton", "label": "Standard Statistics",
            "fields": [
                {"key": "mean_std", "kind": "calculated", "label": "Mean STD Area", "expression": "mean(std_areas.area)"},
                {"key": "sd_std", "kind": "calculated", "label": "SD", "expression": "sd(std_areas.area)"},
                {"key": "rsd_std", "kind": "calculated", "label": "%RSD", "unit": "%", "expression": "rsd(std_areas.area)"},
                {"key": "mean_bkt_1", "kind": "calculated", "label": "Mean (pooled BKT 1)", "expression": "mean(pool(std_areas.area, bkt_1.area))"},
                {"key": "sd_bkt_1", "kind": "calculated", "label": "SD (pooled BKT 1)", "expression": "sd(pool(std_areas.area, bkt_1.area))"},
                {"key": "rsd_bkt_1", "kind": "calculated", "label": "%RSD (pooled BKT 1)", "unit": "%", "expression": "rsd(pool(std_areas.area, bkt_1.area))"},
                {"key": "mean_std2", "kind": "calculated", "label": "Mean STD 2 Area", "expression": "mean(corel_areas.std2_area)"},
                {"key": "std_corelation", "kind": "calculated", "label": "Standard Co-relation", "unit": "%", "expression": "trunc(stats.mean_std / stats.mean_std2 * corel_weights.std2_weight / standard.weight_mg, 3) * 100"},
                {"key": "pct_mean_assay", "kind": "calculated", "label": "% Mean Assay", "unit": "%", "expression": "mean(samples.pct_assay)", "rounding": {"mode": "round", "digits": 2}},
                #  Overall mean mg/mL across the sample rows — the sheet's column R
                #  (Mean (mg/mL)). Surfaced like pct_mean_assay (samples footer ref).
                {"key": "mean_mgml", "kind": "calculated", "label": "Mean (mg/mL)", "unit": "mg/mL", "expression": "mean(samples.assay_mgml)", "rounding": {"mode": "round", "digits": 2}},
            ],
        },
        {
            "key": "samples", "kind": "table", "label": "Sample Preparations",
            "rows": {"min": 1, "max": 32, "default": 2},
            "headerContext": [
                {"label": "Batch No.", "ref": "batch_no"},
                {"label": "Stability Condition", "ref": "stability_condition"},
                {"label": "Packing Detail", "ref": "packing_detail_hdr"},
                {"label": "TRF No.", "ref": "trf_no"},
                {"label": "AR No.", "ref": "ar_no"},
            ],
            "fields": [
                {"key": "prep_ref", "kind": "input", "type": "text", "label": "Prep. Ref."},
                {"key": "avg_wt", "kind": "calculated", "label": "Avg Weight", "expression": "avg_weight"},
                {"key": "lc", "kind": "calculated", "label": "Label Claim (L.C.)", "expression": "label_claim"},
                {"key": "sample_weight", "kind": "input", "label": "Sample Wt.", "unit": "mg", "required": True},
                {"key": "s_vol_1", "kind": "input", "label": "Vol 1", "unit": "mL", "required": True},
                {"key": "s_pip_1", "kind": "input", "label": "Pip 1", "unit": "mL", "default": 1},
                {"key": "s_vol_2", "kind": "input", "label": "Vol 2", "unit": "mL", "default": 1},
                {"key": "s_pip_2", "kind": "input", "label": "Pip 2", "unit": "mL", "default": 1},
                {"key": "s_vol_3", "kind": "input", "label": "Vol 3", "unit": "mL", "default": 1},
                {"key": "area_1", "kind": "area", "label": "Area 1"},
                {"key": "area_2", "kind": "area", "label": "Area 2"},
                {"key": "avg_area", "kind": "calculated", "label": "Avg. Area", "expression": "mean([area_1, area_2])"},
                {"key": "pct_assay", "kind": "calculated", "label": "% Assay", "unit": "%", "expression": "avg_area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 * s_vol_1 / sample_weight * avg_weight / label_claim * standard.potency * standard.mw_base / standard.mw_salt"},
                #  Sheet column Q (Assay mg/mL) = % Assay x L.C. / 100 (see module
                #  docstring for the algebraic derivation from the sheet formulas).
                {"key": "assay_mgml", "kind": "calculated", "label": "Assay (mg/mL)", "unit": "mg/mL", "expression": "pct_assay * label_claim / 100"},
            ],
            "footer": [
                {"label": "% Mean Assay", "ref": "stats.pct_mean_assay", "unit": "%"},
                {"label": "Mean (mg/mL)", "ref": "stats.mean_mgml", "unit": "mg/mL"},
            ],
        },
    ],
    "criteria": [],
}

A1_FP_MGML = SeedTemplate(
    code="TPL-A1-0003",
    name="Assay for finished product mg/ml",
    archetype="A1",
    result_unit="%",
    test_code="TST-ASSAY-FP-MGML",
    test_name="Assay for Finished Product-mgperml &%",
    test_type="Quantitative",
    definition=A1_FP_MGML_DEFINITION,
)

TEMPLATES = [A1_FP_MGML]
