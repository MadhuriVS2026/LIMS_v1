"""
TPL-A6A-0005 — Dissolution-Leuprolide-microsphere (archetype A6a, cumulative release).

Formula-exact rebuild of the workbook
`Test types/Dissolution sheet_Leuprolide_Microsphere.xlsx` (sheet `ZEG0572A`,
A1:Q193), per the approved design at
`.agents/tasks/a6a-leuprolide-microsphere/design.md` and the trace oracle
`.agents/tasks/a6a-leuprolide-microsphere/trace.md`. The user's ask was to copy
the base template `Dissolution sheet_ without replacement_ QC release-6`
(TPL-A6A-0002 v1), rename it `Dissolution-Leuprolide-microsphere`, and rebind it
to a new Test of the same name. TPL-A6A-0002 is a DB-only seeded row (no module
exists for it), so this is a brand-new seed module cloning the base's *structure*
(its `timepoints_release` cumulative-carry sequence and standard chain) and
adapting it to this sheet's actual constants and its fixed-media,
replace-fraction carry model. Closest pattern module: `a6b_octreotide_ph10.py`.

ARCHETYPE-vs-NAME discrepancy (documented, deliberate — do NOT "correct" it):
the base sheet is named "without replacement" and the archetype is kept at `A6a`
to match the base family it is copied from. HOWEVER, this sheet actually carries
the cumulative replacement add-back — the L/C columns implement a running carry:
  C40 = J40                          (1 Hr: first timepoint, no carry)
  C46 = IF(J46="","", J46 + L46)     with L46 = K40
  C52 = IF(J52="","", J52 + L52)     with L52 = K46 + L46
  => L[b,u] = K[b-1,u] + L[b-1,u] = Σ K[1..b-1, u];  K = J * A37/A35.
We reproduce the sheet's ACTUAL formulas (a live cumulative chain), not the
label's implied "without replacement" semantics. A future reader must NOT strip
the carry to match the archetype name.

CARRY FORM — non-recursive `sum(prior.*)`, NOT recursive `prev.carry`. This is
the exact form the only DB-pinned cumulative-release template (TPL-A6A-0004)
uses (see tests/calculation/test_dissolution_a6a_release.py:
`unit_N = uncorrected_N + sum(prior.correction_N)`). A per-row hidden
`kfrac_u = jassay_u * A37/A35` (a real dependency edge to `jassay_u`) and the
reported `unit_u = jassay_u + sum(prior.kfrac_u)`. `sum` of an empty range
returns 0 (expression.py::_f_sum), so row 1 gives `unit = J` (= C40) and later
rows give `J + Σ K[1..b-1]` (= C46 = J46 + L46, C52 = J52 + L52). The recursive
`prev.carry` form is rejected because `_evaluation_order` skips `prev`/`prior`
dependency paths, so it has no ordering edge to `jassay_u` and could silently
collapse to 0. The three field families are declared in three contiguous loops
(`jassay` -> `kfrac` -> `unit`), matching the proven TPL-A6A-0004 module.

Acceptance criteria: exactly one blocking criterion, the standard-replicate %RSD
SST (B29 = `std_stats.rsd_std`, NMT 2.0 %) — the only numeric suitability limit
the sheet carries. Because the standard statistics group is renamed `std_stats`,
the criterion MUST pass `target="std_stats.rsd_std"` explicitly — a bare
`sst_rsd_criterion()` would target the non-existent `stats.rsd_std` and never
evaluate. The pooled bracketing %RSD (D29) and pellet-weight %RSD (F30) are
computed and displayed but NOT carried as blocking criteria (the sheet shows no
numeric limit on either; a lab decision to add one later).

Signature block (sheet rows ~190+) — handled outside the definition, matching
A6B-0001/0002.
"""
from scripts.template_definitions._common import SeedTemplate, sst_rsd_criterion

_UNITS = 6


# ── Context header (sheet rows 2-15) ─────────────────────────────────
#  Every box is sourced OR overridable so none renders as a permanently-blank
#  read-only field. Display-only header text carries no formula.
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
         "label": "Analysis as per", "default": "AD/TATP/220/01",
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
    #  I19 = E19/F19*G19/H19*C19/D19*B19/100*1000. Gold I19 = 78.726628.
    return {
        "key": "standard", "kind": "singleton", "label": "Standard detail",
        "fields": [
            {"key": "name", "kind": "input", "type": "text", "label": "Standard name",
             "default": "Leuprolide Acetate"},                              # A19
            {"key": "potency", "kind": "input", "label": "Potency", "unit": "%",
             "required": True, "default": 97.87},                           # B19
            {"key": "mw_base", "kind": "input", "label": "MW of base",
             "default": 1},                                                 # C19
            {"key": "mw_salt", "kind": "input", "label": "MW of salt",
             "default": 1},                                                 # D19
            {"key": "weight_mg", "kind": "input", "label": "Weight (mg)",
             "unit": "mg", "required": True, "default": 20.11},             # E19
            {"key": "dilution_1", "kind": "input", "label": "Dilution-1 (mL)",
             "default": 50},                                                # F19
            {"key": "volume_1", "kind": "input", "label": "Volume-1 (mL)",
             "default": 5},                                                 # G19
            {"key": "dilution_2", "kind": "input", "label": "Dilution-2 (mL)",
             "default": 25},                                                # H19
            {"key": "conc_ppm", "kind": "calculated",
             "label": "Concentration (ppm)", "unit": "ppm",
             "expression": "weight_mg / dilution_1 * volume_1 / dilution_2"
                           " * mw_base / mw_salt * potency / 100 * 1000"},  # I19
        ],
    }


# ── Standard / BKT areas and statistics (sheet rows 21-29) ───────────
def _std_areas_group() -> dict:
    #  B22:B26 raw replicate areas. Footer refs point at std_stats.
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
    #  D22:D26 bracketing standard areas (5 filled on the sheet).
    return {
        "key": "bkt", "kind": "table", "label": "Bracketing standard area",
        "rows": {"min": 0, "max": 5, "default": 5},
        "fields": [{"key": "area", "kind": "area", "label": "Standard area"}],
        #  Pooled bracketing statistics (sheet D27/D28/D29 = over B22:B26 + D22:D26).
        "footer": [
            {"label": "Mean", "ref": "std_stats.mean_bkt"},
            {"label": "STDev", "ref": "std_stats.sd_bkt"},
            {"label": "% RSD", "ref": "std_stats.rsd_bkt", "unit": "%"},
        ],
    }


def _std_stats_group() -> dict:
    #  B27 = AVERAGE(B22:B26); B28 = STDEV(B22:B26); B29 = B28*100/B27.
    #  D27 = AVERAGE(B22:B26,D22:D26) — pooled over the 5 replicates + 5 BKT (10).
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


# ── Dissolution parameters (sheet rows 21-27, H/I cols) ──────────────
def _params_group() -> dict:
    #  Context/inputs only — only volume_ml feeds a formula (via prep.media_vol).
    return {
        "key": "params", "kind": "singleton", "label": "Dissolution Parameter",
        "fields": [
            {"key": "volume_ml", "kind": "input", "label": "Volume in mL", "unit": "mL",
             "default": 50},                                                # I22
            {"key": "apparatus", "kind": "input", "type": "text", "label": "Apparatus",
             "default": "Bottle Rotating"},                                 # I23
            {"key": "rpm", "kind": "input", "label": "RPM", "unit": "rpm",
             "default": 6},                                                 # I24
            {"key": "temperature", "kind": "input", "type": "text", "label": "Temp °C",
             "default": "50"},                                              # I25
            {"key": "media", "kind": "input", "type": "text", "label": "Media",
             #  Long buffer text (sheet H26/H27): auto-growing multi-line textarea.
             "multiline": True, "overridable": True,
             "default": "0.5% W/V PVA IN WATER pH 5.50"},                   # H26/H27
        ],
    }


# ── Pellet-weight table + stats (sheet rows 21-30, E/F cols) ─────────
def _weights_group() -> dict:
    #  F22:F27 "Pellets Weight in mg", one row per Dissolution Unit (Unit-1..6).
    #  Only 3 filled on the sheet (F22=49.17, F23=50.56, F24=49.77); rest blank.
    return {
        "key": "weights", "kind": "table", "label": "Pellets Weight in mg",
        "rows": {"min": 1, "max": _UNITS, "default": _UNITS, "labelFrom": "unit_label"},
        "fields": [
            {"key": "unit_label", "kind": "input", "type": "text",
             "label": "Dissolution Unit"},                                  # E22:E27
            {"key": "weight", "kind": "input", "label": "Pellets Weight", "unit": "mg"},  # F22:F27
        ],
        "footer": [
            {"label": "Mean", "ref": "weight_stats.mean_wt", "unit": "mg"},
            {"label": "STDev", "ref": "weight_stats.sd_wt", "unit": "mg"},
            {"label": "% RSD", "ref": "weight_stats.rsd_wt", "unit": "%"},
        ],
    }


def _weight_stats_group() -> dict:
    #  Sheet quirk, reproduced deliberately: F28 = AVERAGE(F22:F27) but
    #  F29 = STDEV(F22:F28) — the STDEV range INCLUDES the mean cell F28. So the
    #  SD is taken over the filled raw weights POOLED WITH the mean cell.
    #  F30 = F29*100/F28.
    return {
        "key": "weight_stats", "kind": "singleton",
        "label": "Pellet weight statistics",
        "fields": [
            {"key": "mean_wt", "kind": "calculated", "label": "Mean", "unit": "mg",
             "expression": "mean(weights.weight)"},                         # F28
            {"key": "sd_wt", "kind": "calculated", "label": "STDev", "unit": "mg",
             "expression": "sd(pool(weights.weight, [mean_wt]))"},          # F29
            {"key": "rsd_wt", "kind": "calculated", "label": "% RSD", "unit": "%",
             "expression": "sd_wt * 100 / mean_wt"},                        # F30
        ],
    }


# ── Blend params / media / pipette / V.F. / replace (sheet rows 31-37) ─
def _prep_group() -> dict:
    return {
        "key": "prep", "kind": "singleton",
        "label": "Blend parameters / media / replace",
        "fields": [
            {"key": "avg_weight", "kind": "input", "label": "Average weight", "unit": "mg",
             "default": 100},                                               # A32
            {"key": "label_claim", "kind": "input", "label": "Label claim", "unit": "mg",
             "default": 9.8},                                               # B32
            #  A35 = I22 — fixed media numerator, kept calculated so it cannot
            #  drift from the Volume-in-mL input. Media does NOT shrink per
            #  timepoint on this sheet.
            {"key": "media_vol", "kind": "calculated", "label": "Media volume",
             "unit": "mL", "expression": "params.volume_ml"},               # A35 (=I22)
            {"key": "pipette_vol", "kind": "input", "label": "Pipette Vol. mL",
             "unit": "mL", "default": 1},                                   # B35
            {"key": "vf_vol", "kind": "input", "label": "V.F. Vol. mL", "unit": "mL",
             "default": 1},                                                 # C35
            {"key": "withdraw_replace", "kind": "input",
             "label": "Sample withdraw / Replace", "unit": "mL", "default": 1},  # A37
        ],
    }


# ── Timepoint release sequence (sheet rows 40-189) ───────────────────
#  25 six-unit blocks (rows 40, 46, 52, ...). 7 real labeled timepoints
#  (1/24/48/96/120/144/168 Hr); 18 trailing spare blocks. Timepoints are the row
#  axis, the 6 dissolution units are columns (unit_1..unit_6).
_TIME_LABELS = ["1 Hr", "24 Hr", "48 Hr", "96 Hr", "120 Hr", "144 Hr", "168 Hr"]


def _jassay_expression(u: int) -> str:
    #  J40 = IF(B40="","", B40/$B$27*$E$19/$F$19*$G$19/$H$19*$C$35/$B$35
    #                       *$A$35/$F22*$B$19*$C$19/$D$19*$A$32/$B$32)
    #  i.e. area / mean_std * E19/F19 * G19/H19 * C35/B35 * A35/(unit pellet wt)
    #       * B19 (PLAIN potency) * C19/D19 * A32/B32.
    #  Each unit divides by ITS OWN pellet weight F22..F27, read by 0-based index.
    return (
        f"area_{u} / std_stats.mean_std"
        f" * standard.weight_mg / standard.dilution_1"
        f" * standard.volume_1 / standard.dilution_2"
        f" * prep.vf_vol / prep.pipette_vol"
        f" * prep.media_vol / weights.weight[{u} - 1]"
        f" * standard.potency"
        f" * standard.mw_base / standard.mw_salt"
        f" * prep.avg_weight / prep.label_claim"
    )


def _timepoints_release_group() -> dict:
    fields: list[dict] = [
        {"key": "time_hr", "kind": "input", "type": "text",
         "label": "Timepoint"},                                            # A-label
    ]
    #  area_1..area_6 — per-unit Sample Area (sheet column B within each block).
    for u in range(1, _UNITS + 1):
        fields.append({"key": f"area_{u}", "kind": "area",
                       "label": f"Sample Area {u}"})                        # B[block+u-1]
    #  Loop A: jassay_1..6 — raw per-unit %Assay J (hidden). Real edge to area_u.
    for u in range(1, _UNITS + 1):
        fields.append({"key": f"jassay_{u}", "kind": "calculated", "hidden": True,
                       "expression": _jassay_expression(u)})                # J column
    #  Loop B: kfrac_1..6 — this row's replace fraction K = J*A37/A35 (hidden).
    #          Depends on the SAME row's jassay_u (real dependency edge).
    for u in range(1, _UNITS + 1):
        fields.append({"key": f"kfrac_{u}", "kind": "calculated", "hidden": True,
                       "expression": f"jassay_{u} * prep.withdraw_replace"
                                     f" / prep.media_vol"})                 # K column
    #  Loop C: unit_1..6 — reported Cumulative %Release C = J + Σ K[1..b-1].
    #          sum(prior.kfrac_u) is 0 on row 1 (=> unit = J = C40), else = L.
    for u in range(1, _UNITS + 1):
        fields.append({"key": f"unit_{u}", "kind": "calculated",
                       "label": f"Unit-{u}", "unit": "%",
                       "expression": f"jassay_{u} + sum(prior.kfrac_{u})"})  # C column
    #  Per-block aggregates over the 6 unit_n (sheet D/E/F/G on block-start row).
    ul = "[" + ", ".join(f"unit_{u}" for u in range(1, _UNITS + 1)) + "]"
    fields.append({"key": "mean", "kind": "calculated", "label": "Mean", "unit": "%",
                   "expression": f"mean({ul})"})                            # D
    fields.append({"key": "min_val", "kind": "calculated", "label": "Min", "unit": "%",
                   "expression": f"min({ul})"})                             # E
    fields.append({"key": "max_val", "kind": "calculated", "label": "Max", "unit": "%",
                   "expression": f"max({ul})"})                             # F
    fields.append({"key": "rsd", "kind": "calculated", "label": "%RSD", "unit": "%",
                   "expression": f"sd({ul}) * 100 / mean"})                 # G
    return {
        "key": "timepoints_release", "kind": "sequence",
        "label": "Cumulative % Release",
        "rows": {"min": 1, "max": 25, "default": 7, "labelFrom": "time_hr"},
        "fields": fields,
    }


A6A_LEUP_DEFINITION = {
    #  Per-timepoint mean %Release; the natural A6a release result. (_extract_result
    #  for a multi-row group returns the first non-blank per-row value — the 1 Hr
    #  block mean — matching existing A6A precedent; a lab decision if the terminal
    #  timepoint mean is later wanted as the single reportable.)
    "resultRef": "timepoints_release.mean",
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
        _timepoints_release_group(),
    ],
    #  Explicit target: the stats group is renamed std_stats, so a bare
    #  sst_rsd_criterion() (default stats.rsd_std) would never evaluate.
    "criteria": [sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)],
}

A6A_LEUP = SeedTemplate(
    code="TPL-A6A-0005",
    name="Dissolution-Leuprolide-microsphere",
    archetype="A6a",
    result_unit="%",
    test_code="TST-DISS-LEUP-MS",
    test_name="Dissolution-Leuprolide-microsphere",
    test_type="Quantitative",
    definition=A6A_LEUP_DEFINITION,
)

TEMPLATES = [A6A_LEUP]
