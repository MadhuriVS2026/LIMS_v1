"""
A2 — Content of Lyso PC / Lyso PG (mg/vial).

The mg/vial sibling of `a2_lyso_content.py` (mg/mL). It reproduces the
Amphotericin B Liposome `Content of Lyso PC PG_mgvial` workbook, which is
structurally identical to the mg/mL sheet — the same two-compound standard
block, the summed PC/PG sub-peaks, the standard and pooled-bracketing
statistics, and the sample section — differing only in that the reportable
content is a per-vial amount: each sheet content formula (C61/D61) carries one
extra trailing factor of 12.5 (the aliquot-to-vial multiplier) over its mg/mL
counterpart.

Two decisions shape this module:

* **The vial factor is an overridable context field `vial_factor` (default
  12.5), referenced bare as `* vial_factor` in both content expressions**, never
  a buried literal — mirroring how `a8_content_uniformity.py` exposes `k_value`.
  Context fields are seeded into every row scope by the evaluator, so a bare
  `vial_factor` inside a `sample_results` row expression resolves. The default
  reproduces the sheet out of the box; overriding it to 1.0 recovers the mg/mL
  numbers.

* **The structure is duplicated from the mg/mL module rather than shared.**
  `TPL-A2-0002` carries no `vial_factor` field today; a shared builder that
  injected the overridable field would change its stored `definition` JSON, which
  must stay byte-for-byte unchanged. Only `context_header` is reused, exactly as
  the mg/mL module reuses it.

As in the mg/mL sheet, the mean-std denominators are the six-injection standard
means (`stats.mean_std_pc`/`stats.mean_std_pg`), NOT the pooled BKT means.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
)

#  Five PC sub-peak slots (sheet columns C–G), two PG slots (H–I).
_PC_KEYS = [f"pc_{i}" for i in range(1, 6)]
_PG_KEYS = [f"pg_{i}" for i in range(1, 3)]
_PC_LIST = "[" + ", ".join(_PC_KEYS) + "]"
_PG_LIST = "[" + ", ".join(_PG_KEYS) + "]"
#  `blank()` rather than 0: an un-injected row must read as no response, matching
#  the sheet's `IF(SUM(...)=0," ",SUM(...))`.
_PC_SUM = f"if(sum({_PC_LIST}) = 0, blank(), sum({_PC_LIST}))"
_PG_SUM = f"if(sum({_PG_LIST}) = 0, blank(), sum({_PG_LIST}))"


def _subpeak_fields() -> list[dict]:
    """The five PC and two PG sub-peak AREA columns plus their summed columns."""
    fields: list[dict] = [
        {"key": key, "kind": "area", "label": f"Lyso PC-{i}", "unit": "µV·s"}
        for i, key in enumerate(_PC_KEYS, start=1)
    ]
    fields += [
        {"key": key, "kind": "area", "label": f"Lyso PG-{i}", "unit": "µV·s"}
        for i, key in enumerate(_PG_KEYS, start=1)
    ]
    fields += [
        {"key": "sum_pc", "kind": "calculated", "label": "Lyso PC Sum Area", "expression": _PC_SUM},
        {"key": "sum_pg", "kind": "calculated", "label": "Lyso PG Sum Area", "expression": _PG_SUM},
    ]
    return fields


def _rsd_criterion(key: str, label: str, target: str) -> dict:
    """`sst_rsd_criterion` shape with a distinct key — four are needed here."""
    return {
        "key": key,
        "label": label,
        "target": target,
        "operator": "lte",
        "limit": 2.0,
        "severity": "blocking",
        "limitText": "NMT 2.0 %",
    }


LYSO_MGVIAL_DEFINITION = {
    "resultRef": "sample_results.pc_mgvial",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {
                "key": "vial_factor",
                "kind": "context",
                "label": "Vial Factor",
                "default": 12.5,
                "overridable": True,
            },
            {
                "key": "product_name",
                "kind": "context",
                "type": "text",
                "label": "Product Name",
                "overridable": True,
            },
            {
                "key": "storage_condition",
                "kind": "context",
                "type": "text",
                "label": "Storage Condition",
                "overridable": True,
            },
            {
                "key": "packing_detail",
                "kind": "context",
                "type": "text",
                "label": "Packing Detail",
                "overridable": True,
            },
            {
                "key": "test_name_ctx",
                "kind": "context",
                "type": "text",
                "label": "Test",
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
                "key": "trf_no",
                "kind": "context",
                "type": "text",
                "label": "TRF No.",
                "overridable": True,
            },
            {
                "key": "ar_no",
                "kind": "context",
                "type": "text",
                "label": "AR No.",
                "overridable": True,
            },
        ],
    ),
    "groups": [
        #  Per-compound weighed standard details (sheet rows 22–24).
        {
            "key": "standard",
            "kind": "singleton",
            "label": "Standard Details",
            "fields": [
                {"key": "pc_weight", "kind": "input", "label": "Lyso PC Weight", "unit": "mg", "default": 17.547},
                {"key": "pc_vol1", "kind": "input", "label": "Lyso PC Vol 1", "unit": "mL", "default": 50},
                {"key": "pc_pip", "kind": "input", "label": "Lyso PC Pip", "unit": "mL", "default": 4},
                {"key": "pc_vol2", "kind": "input", "label": "Lyso PC Vol 2", "unit": "mL", "default": 20},
                {"key": "pc_mw_base", "kind": "input", "label": "Lyso PC MW — Base", "default": 1},
                {"key": "pc_mw_salt", "kind": "input", "label": "Lyso PC MW — Salt", "default": 1},
                {"key": "pc_potency", "kind": "input", "label": "Lyso PC Potency", "unit": "%", "default": 98},
                {"key": "pc_lc", "kind": "input", "label": "Lyso PC Label Claim", "default": 1},
                {"key": "pg_weight", "kind": "input", "label": "Lyso PG Weight", "unit": "mg", "default": 18.411},
                {"key": "pg_vol1", "kind": "input", "label": "Lyso PG Vol 1", "unit": "mL", "default": 100},
                {"key": "pg_pip", "kind": "input", "label": "Lyso PG Pip", "unit": "mL", "default": 4},
                {"key": "pg_vol2", "kind": "input", "label": "Lyso PG Vol 2", "unit": "mL", "default": 20},
                {"key": "pg_mw_base", "kind": "input", "label": "Lyso PG MW — Base", "default": 511.61},
                {"key": "pg_mw_salt", "kind": "input", "label": "Lyso PG MW — Salt", "default": 534.6},
                {"key": "pg_potency", "kind": "input", "label": "Lyso PG Potency", "unit": "%", "default": 98.3},
                {"key": "pg_lc", "kind": "input", "label": "Lyso PG Label Claim", "default": 1},
            ],
        },
        #  Six standard replicate injections (sheet rows 28–33).
        {
            "key": "std_injections",
            "kind": "table",
            "label": "Standard Details",
            "rows": {"min": 1, "max": 6, "default": 6},
            "fields": _subpeak_fields(),
            "footer": [
                {"label": "Mean", "ref": "stats.mean_std_pc"},
                {"label": "SD", "ref": "stats.sd_std_pc"},
                {"label": "% RSD", "ref": "stats.rsd_std_pc", "unit": "%"},
            ],
        },
        #  Bracketing standard injections (sheet rows 40–45); blank rows tolerated.
        {
            "key": "bkt_injections",
            "kind": "table",
            "label": "BKT Standard Details",
            "rows": {"min": 1, "max": 6, "default": 6},
            "fields": _subpeak_fields(),
            "footer": [
                {"label": "Mean", "ref": "stats.mean_pool_pc"},
                {"label": "SD", "ref": "stats.sd_pool_pc"},
                {"label": "% RSD", "ref": "stats.rsd_pool_pc", "unit": "%"},
            ],
        },
        #  Standard statistics (rows 34–36) and pooled BKT statistics (rows 46–48).
        {
            "key": "stats",
            "kind": "singleton",
            "label": "Standard Statistics",
            "fields": [
                {"key": "mean_std_pc", "kind": "calculated", "label": "Lyso PC Mean STD", "expression": "mean(std_injections.sum_pc)"},
                {"key": "sd_std_pc", "kind": "calculated", "label": "Lyso PC SD", "expression": "sd(std_injections.sum_pc)"},
                {"key": "rsd_std_pc", "kind": "calculated", "label": "Lyso PC %RSD", "unit": "%", "expression": "rsd(std_injections.sum_pc)"},
                {"key": "mean_std_pg", "kind": "calculated", "label": "Lyso PG Mean STD", "expression": "mean(std_injections.sum_pg)"},
                {"key": "sd_std_pg", "kind": "calculated", "label": "Lyso PG SD", "expression": "sd(std_injections.sum_pg)"},
                {"key": "rsd_std_pg", "kind": "calculated", "label": "Lyso PG %RSD", "unit": "%", "expression": "rsd(std_injections.sum_pg)"},
                {"key": "mean_pool_pc", "kind": "calculated", "label": "Lyso PC Pooled Mean", "expression": "mean(pool(std_injections.sum_pc, bkt_injections.sum_pc))"},
                {"key": "sd_pool_pc", "kind": "calculated", "label": "Lyso PC Pooled SD", "expression": "sd(pool(std_injections.sum_pc, bkt_injections.sum_pc))"},
                {"key": "rsd_pool_pc", "kind": "calculated", "label": "Lyso PC Pooled %RSD", "unit": "%", "expression": "rsd(pool(std_injections.sum_pc, bkt_injections.sum_pc))"},
                {"key": "mean_pool_pg", "kind": "calculated", "label": "Lyso PG Pooled Mean", "expression": "mean(pool(std_injections.sum_pg, bkt_injections.sum_pg))"},
                {"key": "sd_pool_pg", "kind": "calculated", "label": "Lyso PG Pooled SD", "expression": "sd(pool(std_injections.sum_pg, bkt_injections.sum_pg))"},
                {"key": "rsd_pool_pg", "kind": "calculated", "label": "Lyso PG Pooled %RSD", "unit": "%", "expression": "rsd(pool(std_injections.sum_pg, bkt_injections.sum_pg))"},
            ],
        },
        #  Sample dilution details (sheet row 52–53). mg/vial sheet inputs.
        {
            "key": "sample_prep",
            "kind": "singleton",
            "label": "Sample Details",
            "fields": [
                {"key": "ml", "kind": "input", "label": "mL", "unit": "mL", "default": 10},
                {"key": "vol", "kind": "input", "label": "Vol", "unit": "mL", "default": 200},
                {"key": "pip", "kind": "input", "label": "Pip", "unit": "mL", "default": 10},
                {"key": "vol2", "kind": "input", "label": "Vol 2", "unit": "mL", "default": 20},
            ],
        },
        #  Sample injections and the four reportable columns (sheet rows 57–63).
        {
            "key": "sample_results",
            "kind": "table",
            "label": "Sample Injections",
            "rows": {"min": 1, "max": 2, "default": 2},
            "fields": [
                *_subpeak_fields(),
                {
                    "key": "pc_mgvial",
                    "kind": "calculated",
                    "label": "Lyso PC mg/vial",
                    "unit": "mg/vial",
                    #  Sheet C61 = L57/L34 * C23/D23 * E23/F23 * G23/H23 * H53/G53 * J53/I53 * I23/100 * 12.5
                    "expression": (
                        "sum_pc / stats.mean_std_pc "
                        "* standard.pc_weight / standard.pc_vol1 "
                        "* standard.pc_pip / standard.pc_vol2 "
                        "* standard.pc_mw_base / standard.pc_mw_salt "
                        "* sample_prep.vol / sample_prep.ml "
                        "* sample_prep.vol2 / sample_prep.pip "
                        "* standard.pc_potency / 100 "
                        "* vial_factor"
                    ),
                    "rounding": {"mode": "round", "digits": 6},
                },
                {
                    "key": "pg_mgvial",
                    "kind": "calculated",
                    "label": "Lyso PG mg/vial",
                    "unit": "mg/vial",
                    #  Sheet D61 = M57/M34 * C24/D24 * E24/F24 * J53/I53 * H53/G53 * G24/H24 * I24/100 * 12.5
                    "expression": (
                        "sum_pg / stats.mean_std_pg "
                        "* standard.pg_weight / standard.pg_vol1 "
                        "* standard.pg_pip / standard.pg_vol2 "
                        "* sample_prep.vol2 / sample_prep.pip "
                        "* sample_prep.vol / sample_prep.ml "
                        "* standard.pg_mw_base / standard.pg_mw_salt "
                        "* standard.pg_potency / 100 "
                        "* vial_factor"
                    ),
                    "rounding": {"mode": "round", "digits": 6},
                },
                {
                    "key": "pc_assay",
                    "kind": "calculated",
                    "label": "Lyso PC Assay",
                    "unit": "%",
                    #  Sheet E61 = C61 * 100 / J23
                    "expression": "pc_mgvial * 100 / standard.pc_lc",
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "key": "pg_assay",
                    "kind": "calculated",
                    "label": "Lyso PG Assay",
                    "unit": "%",
                    #  Sheet F61 = D61 * 100 / J24
                    "expression": "pg_mgvial * 100 / standard.pg_lc",
                    "rounding": {"mode": "round", "digits": 4},
                },
                #  Avg row (sheet 63). `mean` skips a blank second injection, so a
                #  single filled injection still reports that injection's value —
                #  the blank-tolerant form, matching the A2 `mean_pct_lc` pattern.
                {
                    "key": "avg_pc_mgvial",
                    "kind": "calculated",
                    "label": "Avg Lyso PC mg/vial",
                    "unit": "mg/vial",
                    "expression": "mean(sample_results.pc_mgvial)",
                    "rounding": {"mode": "round", "digits": 6},
                },
                {
                    "key": "avg_pg_mgvial",
                    "kind": "calculated",
                    "label": "Avg Lyso PG mg/vial",
                    "unit": "mg/vial",
                    "expression": "mean(sample_results.pg_mgvial)",
                    "rounding": {"mode": "round", "digits": 6},
                },
                {
                    "key": "avg_pc_assay",
                    "kind": "calculated",
                    "label": "Avg Lyso PC Assay",
                    "unit": "%",
                    "expression": "mean(sample_results.pc_assay)",
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "key": "avg_pg_assay",
                    "kind": "calculated",
                    "label": "Avg Lyso PG Assay",
                    "unit": "%",
                    "expression": "mean(sample_results.pg_assay)",
                    "rounding": {"mode": "round", "digits": 4},
                },
            ],
        },
    ],
    "criteria": [
        _rsd_criterion("sst_std_rsd_pc", "%RSD of Lyso PC standard replicate injections", "stats.rsd_std_pc"),
        _rsd_criterion("sst_std_rsd_pg", "%RSD of Lyso PG standard replicate injections", "stats.rsd_std_pg"),
        _rsd_criterion("sst_pool_rsd_pc", "%RSD of Lyso PC pooled bracketing injections", "stats.rsd_pool_pc"),
        _rsd_criterion("sst_pool_rsd_pg", "%RSD of Lyso PG pooled bracketing injections", "stats.rsd_pool_pg"),
    ],
}

LYSO_MGVIAL = SeedTemplate(
    code="TPL-A2-0003",
    name="Content of Lyso PC / Lyso PG (mg/vial)",
    archetype="A2",
    result_unit="mg/vial",
    test_code="TST-LYSO",
    test_name="Content of Lyso PC & Lyso PG by HPLC",
    test_type="Quantitative",
    definition=LYSO_MGVIAL_DEFINITION,
)

TEMPLATES = [LYSO_MGVIAL]
