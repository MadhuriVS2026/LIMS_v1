"""
TPL-A6B-0002 — Dissolution (Octreotide Acetate, pH 10, WITH replacement).

Formula-exact rebuild of the workbook
`Test types/Dissolution sheet_Octreotide_PH 10.xlsx` (sheet `42_2-8°C_`,
A1:R91), per the approved design at
`.agents/tasks/a6b-0002-octreotide-ph10/design.md`. Authoritative formula source
is the full cell+formula dump `_dumps/Dissolution sheet_Octreotide_PH 10.txt`.

Unlike the 12-unit Doxorubicin A6B-0001 (which runs the recursive carry-over
*down* the timepoint rows and so puts timepoints on the row axis / units as
columns), this sheet is a **per-timepoint table, units as rows**: each timepoint
(1 hr @37°C, 4 hr @55°C, 24 hr @55°C) is a fixed 6-unit block (sheet rows 40-45,
46-51, 52-57), and each block's per-unit %Residue divides by *that unit's own
weight for that timepoint* — `$F22` for 1 hr, `$G22` for 4 hr, `$H22` for 24 hr.
So each timepoint is modelled as its own 6-row `table` group whose %Residue
reads the matching weight column by row index. This keeps every formula a single
row expression and reproduces the sheet exactly.

Deliberately NOT reproduced (see design "Deliberately NOT reproduced"):

* The rows 58-69 area-driven "%Release of Octreotide Base" block — its `K64`
  chain divides by the EMPTY `$F$19` cell and the per-unit area inputs were never
  entered, so the source's own cells are cached `#VALUE!` (`t="e"`). It is a
  broken, unused scaffold. The live %Release presentation is the rows 70-87
  residue-from-assay block, which IS reproduced.
* The L/M carry-over columns — L is an intermediate; M (M46→M52→M64→M70…) is the
  cumulative replacement running sum, but its continuation into the %Release rows
  is `#VALUE!` on the sheet (fed by the dead K64 path). No reportable value on
  the sheet depends on a live M, so the cumulative chain is not modelled.
  Re-enabling it would change the sheet's own behaviour and is a lab decision.
* Signature block (rows 89-90) — handled outside the definition, matching
  A6B-0001.

Acceptance criteria: exactly one blocking criterion, the standard-replicate %RSD
SST (B29 = `std_stats.rsd_std`, NMT 2.0 %) — the only machine-checkable limit on
the sheet and the shared convention across A6A/A6B/A6C. Because the standard
statistics group is renamed `std_stats` here (A6B-0001 calls it `stats`), the
criterion MUST pass `target="std_stats.rsd_std"` explicitly — a bare
`sst_rsd_criterion()` would target the non-existent `stats.rsd_std` and never
evaluate.
"""
from scripts.template_definitions._common import SeedTemplate, sst_rsd_criterion

_UNITS = 6


# ── Context header (sheet rows 2-15) ─────────────────────────────────
#  Every box is sourced OR overridable so none renders as a permanently-blank
#  read-only field (test_no_context_field_is_unfillable). Display-only header
#  text carries no formula.
def _context() -> list[dict]:
    return [
        {"key": "generic_name", "kind": "context", "type": "text",
         "label": "Generic Name", "source": "product.name"},               # B5
        {"key": "product_name", "kind": "context", "type": "text",
         "label": "Product Name", "source": "product.name",
         "overridable": True},                                              # B6 (=B5)
        {"key": "trf_no", "kind": "context", "type": "text",
         "label": "TRF No.", "source": "trf.trf_number", "overridable": True},  # B7
        {"key": "ar_no", "kind": "context", "type": "text",
         "label": "AR No.", "source": "trf.ar_number", "overridable": True},    # B8
        {"key": "batch_no", "kind": "context", "type": "text",
         "label": "Batch No.", "source": "trf.batch_number",
         "overridable": True},                                              # B9
        {"key": "stability_condition", "kind": "context", "type": "text",
         "label": "Stability Condition", "overridable": True},              # B10
        {"key": "test_performed", "kind": "context", "type": "text",
         "label": "Test", "default": "In Vitro Release", "overridable": True},  # B11
        {"key": "analysis_as_per", "kind": "context", "type": "text",
         "label": "Analysis as per", "default": "In house",
         "overridable": True},                                              # B12
        {"key": "analysed_by", "kind": "context", "type": "text",
         "label": "Analysed By", "source": "session.analyst",
         "overridable": True},                                              # B13
        {"key": "instrument_id", "kind": "context", "type": "text",
         "label": "Instrument Id.", "overridable": True},                   # B14
        {"key": "date_of_analysis", "kind": "context", "type": "date",
         "label": "Date of Analysis", "source": "session.date",
         "overridable": True},                                              # B15
    ]


# ── Standard detail (sheet rows 17-19) ───────────────────────────────
def _standard_group() -> dict:
    #  J19 = E19/G19*H19/I19*C19/D19*B19/100*1000. Gold J19 = 91.73466.
    return {
        "key": "standard", "kind": "singleton", "label": "Standard detail",
        "fields": [
            {"key": "name", "kind": "input", "type": "text", "label": "Standard name",
             "default": "Octreotide Acetate"},
            {"key": "potency", "kind": "input", "label": "Potency", "unit": "%",
             "required": True, "default": 89.41},                           # B19
            {"key": "mw_base", "kind": "input", "label": "Molecular weight of base",
             "default": 1},                                                 # C19
            {"key": "mw_salt", "kind": "input", "label": "Molecular weight of salt",
             "default": 1},                                                 # D19
            {"key": "weight_mg", "kind": "input", "label": "Weight (mg) of Standard",
             "unit": "mg", "required": True, "default": 25.65},             # E19
            {"key": "dilution_1", "kind": "input", "label": "Dilution-1 (mL)",
             "default": 25},                                                # G19
            {"key": "volume_1", "kind": "input", "label": "Volume-1 (mL)",
             "default": 5},                                                 # H19
            {"key": "dilution_2", "kind": "input", "label": "Dilution-2 (mL)",
             "default": 50},                                                # I19
            {"key": "conc_ppm", "kind": "calculated",
             "label": "Concentration (ppm)", "unit": "ppm",
             "expression": "weight_mg / dilution_1 * volume_1 / dilution_2"
                           " * mw_base / mw_salt * potency / 100 * 1000"},  # J19
        ],
    }


# ── Standard / BKT areas and statistics (sheet rows 21-29) ───────────
def _std_areas_group() -> dict:
    #  B22:B26 raw replicate areas. Footer refs point at std_stats (NOT the
    #  helper default stats.*), matching the renamed statistics group.
    return {
        "key": "std_areas", "kind": "table", "label": "Standard area",
        "rows": {"min": 1, "max": 6, "default": 5},
        "fields": [{"key": "area", "kind": "area", "label": "Standard area"}],
        "footer": [
            {"label": "Mean", "ref": "std_stats.mean_std"},
            {"label": "STDev", "ref": "std_stats.sd_std"},
            {"label": "% RSD", "ref": "std_stats.rsd_std", "unit": "%"},
        ],
    }


def _bkt_group() -> dict:
    #  D22:D26 bracketing standard areas (2 filled on the sheet; up to 5 slots).
    return {
        "key": "bkt", "kind": "table", "label": "Bracketing standard area",
        "rows": {"min": 0, "max": 5, "default": 2},
        "fields": [{"key": "area", "kind": "area", "label": "Standard area"}],
        #  Pooled bracketing statistics (sheet D27/D28/D29 = over B22:B26 + the
        #  BKT areas), shown beneath the BKT table: Mean / STDev / % RSD.
        "footer": [
            {"label": "Mean", "ref": "std_stats.mean_bkt"},
            {"label": "STDev", "ref": "std_stats.sd_bkt"},
            {"label": "% RSD", "ref": "std_stats.rsd_bkt", "unit": "%"},
        ],
    }


def _std_stats_group() -> dict:
    #  B27 = AVERAGE(B22:B26); B28 = STDEV(B22:B26); B29 = B28*100/B27.
    #  D27 = AVERAGE(B22:B26,D22:D26) — pooled over the 5 replicates + BKT.
    return {
        "key": "std_stats", "kind": "singleton", "label": "Standard statistics",
        "fields": [
            {"key": "mean_std", "kind": "calculated", "label": "Mean",
             "expression": "mean(std_areas.area)"},                         # B27
            {"key": "sd_std", "kind": "calculated", "label": "STDev",
             "expression": "sd(std_areas.area)"},                           # B28
            {"key": "rsd_std", "kind": "calculated", "label": "% RSD", "unit": "%",
             "expression": "sd(std_areas.area) * 100 / mean_std"},          # B29
            {"key": "mean_bkt", "kind": "calculated", "label": "Mean (bracketing)",
             "expression": "mean(pool(std_areas.area, bkt.area))"},         # D27
            {"key": "sd_bkt", "kind": "calculated", "label": "STDev (bracketing)",
             "expression": "sd(pool(std_areas.area, bkt.area))"},           # D28
            {"key": "rsd_bkt", "kind": "calculated", "label": "% RSD (bracketing)",
             "unit": "%",
             "expression": "sd(pool(std_areas.area, bkt.area)) * 100 / mean_bkt"},  # D29
        ],
    }


# ── Dissolution parameters (sheet rows 21-27, I/J cols) ──────────────
def _params_group() -> dict:
    #  Context/inputs only — none appears in a formula.
    return {
        "key": "params", "kind": "singleton", "label": "Dissolution Parameter",
        "fields": [
            {"key": "volume_ml", "kind": "input", "label": "Volume in mL", "unit": "mL",
             "default": 10},                                                # J22
            {"key": "apparatus", "kind": "input", "type": "text", "label": "Apparatus",
             "default": "Bottle Rotating"},                                 # J23
            {"key": "rpm", "kind": "input", "label": "RPM", "unit": "rpm",
             "default": 50},                                                # J24
            {"key": "temperature", "kind": "input", "type": "text", "label": "Temp °C",
             "default": "37°C and 55°C"},                                   # J25
            {"key": "media", "kind": "input", "type": "text", "label": "Media",
             #  Long buffer-prep paragraph (sheet I27): render as an auto-growing
             #  multi-line textarea so the whole text fits and wraps.
             "multiline": True, "overridable": True},                       # I26/I27
        ],
    }


# ── Sample weights + per-column stats (sheet rows 22-30, E/F/G/H) ────
def _weights_group() -> dict:
    #  F22:F27 (1 hr), G22:G27 (4 hr), H22:H27 (24 hr) per-unit weights in mg,
    #  one row per Dissolution Unit (Unit-1..Unit-6). The leading text column
    #  carries the Unit label so the column-aligned footer below can render
    #  Mean / STDev / % RSD as rows beneath the three weight columns.
    return {
        "key": "weights", "kind": "table", "label": "Dissolution Unit weights",
        "rows": {"min": 1, "max": _UNITS, "default": _UNITS, "labelFrom": "unit_label"},
        "fields": [
            {"key": "unit_label", "kind": "input", "type": "text",
             "label": "Dissolution Unit"},
            {"key": "w_1hr", "kind": "input", "label": "Weight in mg for 1 hr"},
            {"key": "w_4hr", "kind": "input", "label": "Weight in mg for 4 hr"},
            {"key": "w_24hr", "kind": "input", "label": "Weight in mg for 24 hr"},
        ],
        #  Column-aligned footer (sheet F/G/H rows 28-30): each labeled row starts
        #  with the stat name (under the Dissolution Unit column) then one value
        #  per weight column. Renders as Mean / STDev / % RSD rows beneath.
        "footer": [
            {"label": "Mean", "ref": "weight_stats.mean_1hr", "unit": "mg"},
            {"ref": "weight_stats.mean_4hr", "unit": "mg"},
            {"ref": "weight_stats.mean_24hr", "unit": "mg"},
            {"label": "STDev", "ref": "weight_stats.sd_1hr", "unit": "mg"},
            {"ref": "weight_stats.sd_4hr", "unit": "mg"},
            {"ref": "weight_stats.sd_24hr", "unit": "mg"},
            {"label": "% RSD", "ref": "weight_stats.rsd_1hr", "unit": "%"},
            {"ref": "weight_stats.rsd_4hr", "unit": "%"},
            {"ref": "weight_stats.rsd_24hr", "unit": "%"},
        ],
    }


def _weight_stats_group() -> dict:
    #  Sheet quirk, reproduced deliberately: F28 = AVERAGE(F22:F27) but
    #  F29 = STDEV(F22:F28) — the STDEV range INCLUDES the mean cell F28. So the
    #  SD is taken over the filled raw weights POOLED WITH the mean cell.
    #  F30 = F29*100/F28. Identical shape for G (4 hr) and H (24 hr).
    return {
        "key": "weight_stats", "kind": "singleton",
        "label": "Dissolution Unit weight statistics",
        "fields": [
            {"key": "mean_1hr", "kind": "calculated", "label": "Mean (1 hr)", "unit": "mg",
             "expression": "mean(weights.w_1hr)"},                          # F28
            {"key": "sd_1hr", "kind": "calculated", "label": "STDev (1 hr)", "unit": "mg",
             "expression": "sd(pool(weights.w_1hr, [mean_1hr]))"},          # F29
            {"key": "rsd_1hr", "kind": "calculated", "label": "% RSD (1 hr)", "unit": "%",
             "expression": "sd_1hr * 100 / mean_1hr"},                      # F30
            {"key": "mean_4hr", "kind": "calculated", "label": "Mean (4 hr)", "unit": "mg",
             "expression": "mean(weights.w_4hr)"},                          # G28
            {"key": "sd_4hr", "kind": "calculated", "label": "STDev (4 hr)", "unit": "mg",
             "expression": "sd(pool(weights.w_4hr, [mean_4hr]))"},          # G29
            {"key": "rsd_4hr", "kind": "calculated", "label": "% RSD (4 hr)", "unit": "%",
             "expression": "sd_4hr * 100 / mean_4hr"},                      # G30
            {"key": "mean_24hr", "kind": "calculated", "label": "Mean (24 hr)", "unit": "mg",
             "expression": "mean(weights.w_24hr)"},                         # H28
            {"key": "sd_24hr", "kind": "calculated", "label": "STDev (24 hr)", "unit": "mg",
             "expression": "sd(pool(weights.w_24hr, [mean_24hr]))"},        # H29
            {"key": "rsd_24hr", "kind": "calculated", "label": "% RSD (24 hr)", "unit": "%",
             "expression": "sd_24hr * 100 / mean_24hr"},                    # H30
        ],
    }


# ── Pooled-assay / media / replace prep (sheet rows 31-37) ───────────
def _prep_group() -> dict:
    return {
        "key": "prep", "kind": "singleton",
        "label": "Pooled sample / media / replace",
        "fields": [
            #  A32 — % Assay (w/w) in pooled sample (Blend); divisor in the
            #  release-from-assay block, number()-guarded there.
            {"key": "pct_assay", "kind": "input", "label": "% Assay in Pooled sample",
             "unit": "%", "default": 4.12},                                 # A32
            {"key": "media_vol", "kind": "input", "label": "Media volume", "unit": "mL",
             "default": 10},                                                # A35
            {"key": "pipette_vol", "kind": "input", "label": "Pipette Vol. mL",
             "unit": "mL", "default": 1},                                   # B35
            {"key": "vf_vol", "kind": "input", "label": "V.F. Vol. mL", "unit": "mL",
             "default": 1},                                                 # C35
            {"key": "withdraw_replace", "kind": "input",
             "label": "Sample withdraw / Replace", "unit": "mL", "default": 1},  # A37
        ],
    }


# ── %Residue timepoint blocks (sheet rows 40-45, 46-51, 52-57) ───────
#  K40 = B40/$B$27*$E$19/$G$19*$H$19/$I$19*$C$35/$B$35*$A$35/$F22*$B$19*$C$19/$D$19
#  i.e. area / mean_std * weight/dilution_1 * volume_1/dilution_2
#       * vf_vol/pipette_vol * media_vol / (this unit's weight)
#       * potency * mw_base / mw_salt.
#  Each block divides by its OWN weight column ($F for 1 hr, $G for 4 hr,
#  $H for 24 hr), read by this row's 1-based rowno -> [rowno - 1].
def _residue_expression(weight_field: str) -> str:
    return (
        f"area / std_stats.mean_std"
        f" * standard.weight_mg / standard.dilution_1"
        f" * standard.volume_1 / standard.dilution_2"
        f" * prep.vf_vol / prep.pipette_vol"
        f" * prep.media_vol / weights.{weight_field}[rowno - 1]"
        f" * standard.potency * standard.mw_base / standard.mw_salt"
    )


def _residue_group(key: str, label: str, weight_field: str) -> dict:
    #  C40 == K40, so the K-column holds the real formula; computed directly here.
    #  The data table shows ONLY Sample Area + %Residue; the block's
    #  Mean/Min/Max/RSD (D/E/F/G) are published by the companion stats singleton
    #  `<key>_stats` and rendered as a footer row beneath the table (see
    #  `_residue_stats_group` / the footer below), matching the sheet layout
    #  (timepoint title, two columns, then a Mean|Min|Max|RSD summary row).
    return {
        "key": key, "kind": "table", "label": label,
        "rows": {"min": 1, "max": _UNITS, "default": _UNITS},
        "fields": [
            {"key": "area", "kind": "area", "label": "Sample Area"},        # B40..
            {"key": "residue", "kind": "calculated",
             "label": "%Residue of Octreotide Base", "unit": "%",
             "expression": _residue_expression(weight_field)},             # K40 (=C40)
        ],
        "footer": [
            {"label": "Mean", "ref": f"{key}_stats.mean", "unit": "%"},
            {"label": "Min", "ref": f"{key}_stats.min_v", "unit": "%"},
            {"label": "Max", "ref": f"{key}_stats.max_v", "unit": "%"},
            {"label": "RSD", "ref": f"{key}_stats.rsd", "unit": "%"},
        ],
    }


def _residue_stats_group(key: str) -> dict:
    #  Per-block %Residue statistics (sheet D/E/F/G rows 40/46/52), referenced by
    #  the residue table footer. Kept as a singleton so the data table carries
    #  only the two entry/result columns.
    return {
        "key": f"{key}_stats", "kind": "singleton",
        "label": f"{key} statistics",
        "fields": [
            {"key": "mean", "kind": "calculated", "label": "Mean", "unit": "%",
             "expression": f"mean({key}.residue)"},                         # D
            {"key": "min_v", "kind": "calculated", "label": "Min", "unit": "%",
             "expression": f"min({key}.residue)"},                          # E
            {"key": "max_v", "kind": "calculated", "label": "Max", "unit": "%",
             "expression": f"max({key}.residue)"},                          # F
            {"key": "rsd", "kind": "calculated", "label": "RSD", "unit": "%",
             "expression": f"sd({key}.residue) * 100 / {key}_stats.mean"},   # G
        ],
    }


# ── %Release-from-assay blocks (sheet rows 70-75, 76-81, 82-87) ──────
#  C70 = ($A$32 - B70) / ($A$32) * 100, where B70 is a MANUALLY ENTERED
#  %Residue value and A32 = prep.pct_assay (number()-guarded as a divisor).
def _release_group(key: str, label: str) -> dict:
    #  Data table shows ONLY the entered %Residue + computed %Release; the block's
    #  Mean/Min/Max/RSD (D/E/F/G) are published by `<key>_stats` and rendered as a
    #  footer row beneath (same shape as the %Residue blocks).
    return {
        "key": key, "kind": "table", "label": label,
        "rows": {"min": 1, "max": _UNITS, "default": _UNITS},
        "fields": [
            {"key": "residue_in", "kind": "input",
             "label": "%Residue of Octreotide Base", "unit": "%"},          # B70..
            {"key": "rel", "kind": "calculated",
             "label": "%Release of Octreotide Base", "unit": "%",
             "expression": "(number(prep.pct_assay) - residue_in)"
                           " / number(prep.pct_assay) * 100"},              # C70
        ],
        "footer": [
            {"label": "Mean", "ref": f"{key}_stats.mean", "unit": "%"},
            {"label": "Min", "ref": f"{key}_stats.min_v", "unit": "%"},
            {"label": "Max", "ref": f"{key}_stats.max_v", "unit": "%"},
            {"label": "RSD", "ref": f"{key}_stats.rsd", "unit": "%"},
        ],
    }


def _release_stats_group(key: str) -> dict:
    #  Per-block %Release statistics (sheet D/E/F/G rows 70/76/82), referenced by
    #  the release table footer. Singleton so the data table carries only the two
    #  entry/result columns.
    return {
        "key": f"{key}_stats", "kind": "singleton",
        "label": f"{key} statistics",
        "fields": [
            {"key": "mean", "kind": "calculated", "label": "Mean", "unit": "%",
             "expression": f"mean({key}.rel)"},                             # D
            {"key": "min_v", "kind": "calculated", "label": "Min", "unit": "%",
             "expression": f"min({key}.rel)"},                              # E
            {"key": "max_v", "kind": "calculated", "label": "Max", "unit": "%",
             "expression": f"max({key}.rel)"},                              # F
            {"key": "rsd", "kind": "calculated", "label": "RSD", "unit": "%",
             "expression": f"sd({key}.rel) * 100 / {key}_stats.mean"},       # G
        ],
    }


A6B_OCT_DEFINITION = {
    #  The final live %Residue timepoint mean, now published by the 24 hr block's
    #  companion statistics singleton (the block's Mean/Min/Max/RSD moved out of
    #  the per-row table into `<key>_stats` + a footer).
    "resultRef": "residue_24hr_stats.mean",
    "context": _context(),
    "groups": [
        _standard_group(),
        _std_areas_group(),
        _bkt_group(),
        _std_stats_group(),
        _params_group(),
        _weights_group(),
        _weight_stats_group(),
        _prep_group(),
        _residue_group("residue_1hr", "%Residue — 1 hr at 37°C", "w_1hr"),
        _residue_stats_group("residue_1hr"),
        _residue_group("residue_4hr", "%Residue — 4 hr at 55°C", "w_4hr"),
        _residue_stats_group("residue_4hr"),
        _residue_group("residue_24hr", "%Residue — 24 hr at 55°C", "w_24hr"),
        _residue_stats_group("residue_24hr"),
        #  Section banner (sheet A58 "%Results") shown above the release blocks.
        #  The schema requires a non-empty `fields` list, so a single hidden
        #  calculated field carries the group while only its label renders.
        {
            "key": "results_banner", "kind": "singleton", "label": "% Results",
            "fields": [
                {"key": "_banner", "kind": "calculated", "label": "", "hidden": True,
                 "expression": "blank()"},
            ],
        },
        _release_group("release_1hr", "%Release — 1 hr at 37°C"),
        _release_stats_group("release_1hr"),
        _release_group("release_4hr", "%Release — 4 hr at 55°C"),
        _release_stats_group("release_4hr"),
        _release_group("release_24hr", "%Release — 24 hr at 55°C"),
        _release_stats_group("release_24hr"),
    ],
    #  Explicit target: this template renames the stats group to std_stats, so a
    #  bare sst_rsd_criterion() (default stats.rsd_std) would never evaluate.
    "criteria": [sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)],
}

A6B_OCT = SeedTemplate(
    code="TPL-A6B-0002",
    name="Dissolution (Octreotide Acetate, pH 10)",
    archetype="A6b",
    result_unit="%",
    test_code="TST-DISS-OCT-PH10",
    #  EXACT user tag, including the "Octreolide" spelling.
    test_name="Dissolution-Octreolide-pH-10",
    test_type="Quantitative",
    definition=A6B_OCT_DEFINITION,
)

TEMPLATES = [A6B_OCT]
