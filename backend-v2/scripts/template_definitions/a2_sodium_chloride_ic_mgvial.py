"""
TPL-A2-0006 — Sodium chloride content by IC (mg/vial).

This template transcribes `Test types/Sodium_chloride_content by IC_ mgvial_Ampho.xlsx`
for Amphotericin B Liposome for injection. It uses the established A2
external-standard content shape: a weighed sodium-chloride standard, six standard
injections, six pooled bracketing-standard (BKT) injections, a blank-area table,
and per-condition sample preparations.

The supplied worksheet's reference values are reproduced by the following chain:

* standard concentration = weight / Vol-1 * Pip-1 / Vol-2 * MW base / MW salt
  * 1000;
* corrected standard/sample/BKT areas subtract the mean blank area;
* BKT statistics pool the standard and BKT injection areas, as in the regular
  BKT table convention; and
* sodium content per vial = corrected sample response / corrected standard mean
  * standard concentration (ppm -> mg/mL) * the inverted sample dilution chain.

The regular standard table retains the final neutral Pip-2 / Vol-3 stage and the
potency field. Their source-sheet defaults are 1/1 and 100 %, so the generic
concentration expression returns the source-sheet result while remaining usable
when a controlled method revision changes those values.

A worksheet represents one TRF batch. Its default two sample rows hold the two
conditions/preparations that the source sheet labels SET-1 and SET-2; their
average is the reportable mg/vial result.
"""
from scripts.template_definitions._common import (
    STANDARD_ROW_LABEL,
    STANDARD_ROWS,
    SeedTemplate,
)


_STD_ROWS = 6
_BKT_ROWS = 6
_BLANK_ROWS = 6


def _two_area_footer(
    raw_mean: str,
    corrected_mean: str,
    raw_sd: str,
    corrected_sd: str,
    raw_rsd: str,
    corrected_rsd: str,
) -> list[dict]:
    """Spreadsheet-style Mean / SD / %RSD rows under raw and corrected areas."""
    return [
        {"label": "Mean", "ref": raw_mean},
        {"ref": corrected_mean},
        {"label": "SD", "ref": raw_sd},
        {"ref": corrected_sd},
        {"label": "% RSD", "ref": raw_rsd, "unit": "%"},
        {"ref": corrected_rsd, "unit": "%"},
    ]


SODIUM_CHLORIDE_IC_DEFINITION = {
    "resultRef": "result.mean_mg_per_vial",
    "context": [
        {
            "key": "generic_name",
            "kind": "context",
            "type": "text",
            "label": "Generic Name",
            "source": "product.name",
        },
        {
            "key": "product_name",
            "kind": "context",
            "type": "text",
            "label": "Product Name",
            "source": "product.name",
        },
        {
            "key": "batch_no",
            "kind": "context",
            "type": "text",
            "label": "Batch No.",
            "source": "trf.batch_number",
        },
        {
            "key": "packing_detail",
            "kind": "context",
            "type": "text",
            "label": "Packing Detail",
            "source": "trf.pack_details",
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
            "label": "AR No.",
            "source": "trf.ar_number",
            "overridable": True,
        },
        {
            "key": "avg_weight",
            "kind": "context",
            "label": "Avg Weight",
            "default": 1,
            "overridable": True,
        },
        {
            "key": "sodium_label_claim",
            "kind": "context",
            "label": "L.C.",
            "default": 1,
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
            "key": "instrument_id",
            "kind": "context",
            "type": "text",
            "label": "Instrument ID.",
            "overridable": True,
        },
        {
            "key": "analysed_by",
            "kind": "context",
            "type": "text",
            "label": "Analysed By",
            "source": "session.analyst",
        },
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
            "kind": "table",
            "label": "Standard Details",
            "rows": dict(STANDARD_ROWS),
            "rowLabel": dict(STANDARD_ROW_LABEL),
            "fields": [
                {
                    "key": "name",
                    "kind": "input",
                    "type": "text",
                    "label": "Compound Name",
                    "default": "Sodium chloride",
                },
                {
                    "key": "weight_mg",
                    "kind": "input",
                    "label": "Weight in mg",
                    "unit": "mg",
                    "required": True,
                },
                {
                    "key": "vol_1",
                    "kind": "input",
                    "label": "Vol 1",
                    "unit": "mL",
                    "default": 100,
                    "required": True,
                },
                {
                    "key": "pip_1",
                    "kind": "input",
                    "label": "Pip 1",
                    "unit": "mL",
                    "default": 2,
                    "required": True,
                },
                {
                    "key": "vol_2",
                    "kind": "input",
                    "label": "Vol 2",
                    "unit": "mL",
                    "default": 100,
                    "required": True,
                },
                {
                    "key": "pip_2",
                    "kind": "input",
                    "label": "Pip 2",
                    "unit": "mL",
                    "default": 1,
                },
                {
                    "key": "vol_3",
                    "kind": "input",
                    "label": "Vol 3",
                    "unit": "mL",
                    "default": 1,
                },
                {
                    "key": "mw_base",
                    "kind": "input",
                    "label": "M.W. of Base",
                    "default": 22.99,
                    "required": True,
                },
                {
                    "key": "mw_salt",
                    "kind": "input",
                    "label": "M.W. of Salt",
                    "default": 58.44,
                    "required": True,
                },
                {
                    "key": "potency",
                    "kind": "input",
                    "label": "Potency",
                    "unit": "%",
                    "default": 100,
                    "required": True,
                },
                {
                    "key": "conc_ppm",
                    "kind": "calculated",
                    "label": "Conc. (ppm)",
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
            "label": "Standard Injections — Sodium",
            "rowLabel": {"header": "Injection No.", "format": "{n}"},
            "rows": {"min": 1, "max": _STD_ROWS, "default": _STD_ROWS},
            "fields": [
                {"key": "area", "kind": "area", "label": "Area"},
                {
                    "key": "corrected_area",
                    "kind": "calculated",
                    "label": "Corrected Area",
                    "expression": "area - stats.mean_blank",
                },
            ],
            "footer": _two_area_footer(
                "stats.mean_std_raw",
                "stats.mean_std_corrected",
                "stats.sd_std_raw",
                "stats.sd_std_corrected",
                "stats.rsd_std_raw",
                "stats.rsd_std_corrected",
            ),
        },
        {
            "key": "bkt_areas",
            "kind": "table",
            "label": "BKT Standard Injections — Sodium",
            "rowLabel": {"header": "BKT Injection No.", "format": "{n}"},
            "rows": {"min": 1, "max": _BKT_ROWS, "default": _BKT_ROWS},
            "fields": [
                {"key": "area", "kind": "area", "label": "Area"},
                {
                    "key": "corrected_area",
                    "kind": "calculated",
                    "label": "Corrected Area",
                    "expression": "area - stats.mean_blank",
                },
            ],
            "footer": _two_area_footer(
                "stats.mean_bkt_raw",
                "stats.mean_bkt_corrected",
                "stats.sd_bkt_raw",
                "stats.sd_bkt_corrected",
                "stats.rsd_bkt_raw",
                "stats.rsd_bkt_corrected",
            ),
        },
        {
            "key": "blank_areas",
            "kind": "table",
            "label": "Blank Area — Sodium",
            "rowLabel": {
                "header": "Injection No.",
                "headerGroup": "Blank Area",
                "format": "{n}",
            },
            #  The source worksheet always provides six blank-injection slots.
            "rows": {"min": _BLANK_ROWS, "max": _BLANK_ROWS, "default": _BLANK_ROWS},
            "fields": [
                {
                    "key": "area",
                    "kind": "area",
                    "label": "Area",
                    "headerGroup": "Sodium",
                },
            ],
            #  `column` keeps these source-sheet statistics beneath the Sodium
            #  Area column rather than as a separate summary card.
            "footer": [
                {
                    "label": "Mean",
                    "ref": "stats.mean_blank",
                    "column": "area",
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "label": "SD",
                    "ref": "stats.sd_blank",
                    "column": "area",
                    "rounding": {"mode": "round", "digits": 1},
                },
                {
                    "label": "% RSD",
                    "ref": "stats.rsd_blank",
                    "unit": "%",
                    "column": "area",
                    "rounding": {"mode": "round", "digits": 1},
                },
            ],
        },
        {
            "key": "blank_interference",
            "kind": "singleton",
            "label": "% Interference",
            "fields": [
                {
                    "key": "sodium",
                    "kind": "calculated",
                    "label": "Sodium",
                    "unit": "%",
                    "expression": "stats.blank_interference",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
        {
            "key": "stats",
            "kind": "singleton",
            "label": "Standard and BKT Statistics",
            "hidden": True,
            "fields": [
                {
                    "key": "mean_blank",
                    "kind": "calculated",
                    "label": "Mean Blank Area",
                    "expression": "mean(blank_areas.area)",
                },
                {
                    "key": "sd_blank",
                    "kind": "calculated",
                    "label": "Blank Area SD",
                    "expression": "sd(blank_areas.area)",
                },
                {
                    "key": "rsd_blank",
                    "kind": "calculated",
                    "label": "Blank Area %RSD",
                    "unit": "%",
                    "expression": "rsd(blank_areas.area)",
                },
                {
                    "key": "mean_std_raw",
                    "kind": "calculated",
                    "label": "Standard Mean Area",
                    "expression": "mean(std_areas.area)",
                },
                {
                    "key": "sd_std_raw",
                    "kind": "calculated",
                    "label": "Standard Area SD",
                    "expression": "sd(std_areas.area)",
                },
                {
                    "key": "rsd_std_raw",
                    "kind": "calculated",
                    "label": "Standard Area %RSD",
                    "unit": "%",
                    "expression": "rsd(std_areas.area)",
                },
                {
                    "key": "mean_std_corrected",
                    "kind": "calculated",
                    "label": "Corrected Standard Mean Area",
                    "expression": "mean(std_areas.corrected_area)",
                },
                {
                    "key": "sd_std_corrected",
                    "kind": "calculated",
                    "label": "Corrected Standard Area SD",
                    "expression": "sd(std_areas.corrected_area)",
                },
                {
                    "key": "rsd_std_corrected",
                    "kind": "calculated",
                    "label": "Corrected Standard Area %RSD",
                    "unit": "%",
                    "expression": "rsd(std_areas.corrected_area)",
                },
                {
                    "key": "mean_bkt_raw",
                    "kind": "calculated",
                    "label": "Pooled BKT Mean Area",
                    "expression": "mean(pool(std_areas.area, bkt_areas.area))",
                },
                {
                    "key": "sd_bkt_raw",
                    "kind": "calculated",
                    "label": "Pooled BKT Area SD",
                    "expression": "sd(pool(std_areas.area, bkt_areas.area))",
                },
                {
                    "key": "rsd_bkt_raw",
                    "kind": "calculated",
                    "label": "Pooled BKT Area %RSD",
                    "unit": "%",
                    "expression": "rsd(pool(std_areas.area, bkt_areas.area))",
                },
                {
                    "key": "mean_bkt_corrected",
                    "kind": "calculated",
                    "label": "Corrected Pooled BKT Mean Area",
                    "expression": (
                        "mean(pool(std_areas.corrected_area, bkt_areas.corrected_area))"
                    ),
                },
                {
                    "key": "sd_bkt_corrected",
                    "kind": "calculated",
                    "label": "Corrected Pooled BKT Area SD",
                    "expression": (
                        "sd(pool(std_areas.corrected_area, bkt_areas.corrected_area))"
                    ),
                },
                {
                    "key": "rsd_bkt_corrected",
                    "kind": "calculated",
                    "label": "Corrected Pooled BKT Area %RSD",
                    "unit": "%",
                    "expression": (
                        "rsd(pool(std_areas.corrected_area, bkt_areas.corrected_area))"
                    ),
                },
                {
                    "key": "blank_interference",
                    "kind": "calculated",
                    "label": "% Interference",
                    "unit": "%",
                    "expression": "mean_blank / mean_bkt_raw * 100",
                },
            ],
        },
        {
            "key": "samples",
            "kind": "table",
            "label": "Sample Details",
            "rows": {"min": 1, "max": 12, "default": 2, "labelFrom": "condition"},
            "headerContext": [
                {"label": "Batch No.", "ref": "batch_no"},
                {"label": "Packing Detail", "ref": "packing_detail"},
                {"label": "TRF No.", "ref": "trf_no"},
                {"label": "AR No.", "ref": "ar_no"},
            ],
            "fields": [
                {
                    "key": "condition",
                    "kind": "input",
                    "type": "text",
                    "label": "Stability Condition",
                },
                {
                    "key": "avg_wt",
                    "kind": "calculated",
                    "label": "Avg Weight",
                    "expression": "avg_weight",
                },
                {
                    "key": "lc",
                    "kind": "calculated",
                    "label": "L.C.",
                    "expression": "sodium_label_claim",
                },
                {
                    "key": "sample_weight",
                    "kind": "input",
                    "label": "Sample Weight",
                    "unit": "mg",
                    "required": True,
                },
                {
                    "key": "s_vol_1",
                    "kind": "input",
                    "label": "Vol 1",
                    "unit": "mL",
                    "default": 12,
                    "required": True,
                },
                {
                    "key": "s_pip_1",
                    "kind": "input",
                    "label": "Pip 1",
                    "unit": "mL",
                    "default": 1,
                    "required": True,
                },
                {
                    "key": "s_vol_2",
                    "kind": "input",
                    "label": "Vol 2",
                    "unit": "mL",
                    "default": 100,
                    "required": True,
                },
                {
                    "key": "s_pip_2",
                    "kind": "input",
                    "label": "Pip 2",
                    "unit": "mL",
                    "default": 1,
                    "required": True,
                },
                {
                    "key": "s_vol_3",
                    "kind": "input",
                    "label": "Vol 3",
                    "unit": "mL",
                    "default": 1,
                    "required": True,
                },
                {"key": "area_1", "kind": "area", "label": "Area-1"},
                {"key": "area_2", "kind": "area", "label": "Area-2"},
                {
                    "key": "avg_area",
                    "kind": "calculated",
                    "label": "Avg. Area",
                    "expression": "mean([area_1, area_2])",
                },
                {
                    "key": "corrected_avg_area",
                    "kind": "calculated",
                    "label": "Corrected Avg. Area",
                    "expression": "avg_area - stats.mean_blank",
                },
                {
                    "key": "mg_per_vial",
                    "kind": "calculated",
                    "label": "mg/vial",
                    "unit": "mg/vial",
                    "expression": (
                        "corrected_avg_area / stats.mean_std_corrected "
                        "* standard.conc_ppm / 1000 "
                        "* s_vol_1 / sample_weight "
                        "* s_vol_2 / s_pip_1 "
                        "* s_vol_3 / s_pip_2"
                    ),
                },
            ],
            "footer": [
                {
                    "label": "Avg. Result",
                    "ref": "result.mean_mg_per_vial",
                    "unit": "mg/vial",
                },
            ],
        },
        {
            "key": "result",
            "kind": "singleton",
            "label": "Result",
            "fields": [
                {
                    "key": "mean_mg_per_vial",
                    "kind": "calculated",
                    "label": "Avg. Result",
                    "unit": "mg/vial",
                    "expression": "mean(samples.mg_per_vial)",
                },
            ],
        },
    ],
    "criteria": [
        {
            "key": "sst_std_rsd",
            "label": "%RSD of corrected standard injections",
            "target": "stats.rsd_std_corrected",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        {
            "key": "sst_bkt_rsd",
            "label": "%RSD of corrected pooled BKT injections",
            "target": "stats.rsd_bkt_corrected",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
    ],
}

SODIUM_CHLORIDE_IC = SeedTemplate(
    code="TPL-A2-0006",
    name="Sodium_chloride_content by IC_ mgvial_Ampho",
    archetype="A2",
    result_unit="mg/vial",
    test_code="TST-NACL-IC",
    test_name="NaCl content",
    test_type="Quantitative",
    definition=SODIUM_CHLORIDE_IC_DEFINITION,
)

TEMPLATES = [SODIUM_CHLORIDE_IC]
