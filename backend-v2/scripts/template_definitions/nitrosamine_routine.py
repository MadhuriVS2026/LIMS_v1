"""
TPL-NITRO-0001 — Nitrosamine Routine analysis sheet (archetype A2, content by
external standard with a serial-dilution standard chain).

Formula-exact rebuild of the workbook
`Test types/Nitrosamine Routine analysis sheet.xls` (sheet `Analysis`). The
user's ask was to create a new test template for "Nitrosamine Routine analysis
sheet" keeping every field as given and matching the sheet's calculations to the
inputs. This is an HRMS trace-impurity (N-Nitroso Argatroban) quantification: a
weighed standard taken through a four-stage serial dilution (Solution I-IV) gives
a ppb standard concentration, and each sample's result in ppm is computed as the
area ratio to the standard average area scaled by the full standard/sample
dilution algebra and TRUNC'd to 4 decimals.

ARCHETYPE choice (documented): the closest existing family is the A2/A3 content
archetype — a weighed-standard chain feeding a per-sample result via a
standard-ratio. It is NOT a dissolution (no cumulative carry) and NOT related
substances (single named impurity, external-standard quant). `A2` is used for the
shape; the result unit is ppm and the standard conc is reported in ppb, which is
an analyte-specific display, not a new archetype.

SHEET QUIRKS reproduced verbatim (do NOT "correct" these):

* Standard conc O11 term order is
  `E11/F11*G11/H11*I11/J11*D11/100*1000*K11/L11*M11/N11*1000` — note `D11/100*1000`
  sits MID-expression (between the Solution II and Solution III terms), not at
  the end. Reproduced as written. Gold O11 = 1.0416537600000002.

* The right-hand "BKT" statistics block averages G15:G22, and G15 is the BLANK
  chromatogram's corrected area = D23 (the left-block standard average, 76406),
  NOT a BKT area. So the BKT "Average Area" pools the standard-average cell with
  the three filled BKT corrected areas: mean(76406, 78963, 86161, 83853) =
  81345.75. This is a sheet quirk — the blank-chromatogram row feeds the BKT
  average — and it is reproduced by pooling `std_stats.avg_area` with the BKT
  corrected column. Unused BKT rows are left BLANK so the blank-tolerant
  mean/sd exclude them (mirroring AVERAGEIF(<>0) / STDEV(IF(<>0))).

* The corrected-area columns subtract the blank area C15, which is 0 on this
  sheet, so corrected == raw. `blank` carries that C15 value (default 0) so the
  subtraction is explicit rather than dropped.

* The sample result O column is TRUNC(...,4). The full term order of the sample
  formula is preserved exactly, with the $-anchored standard-prep constants and
  the un-anchored per-row Dilution/mL/Avg-Weight/Label-Claim/Wt columns.

ACCEPTANCE CRITERIA: exactly one blocking criterion — the standard replicate
%RSD (D25 = `std_stats.rsd_area`), NMT 2.0 %, the only natural suitability limit.
The BKT %RSD (G25, ~5.48 % in the real data) is DISPLAYED but NOT blocking: the
sheet carries no numeric limit on it and it exceeds 2 %, so making it blocking
would wrongly fail valid data. Because the stats group is named `std_stats`, the
criterion passes `target="std_stats.rsd_area"` explicitly (a bare
`sst_rsd_criterion()` would target the non-existent `stats.rsd_std`).

Signature block (sheet rows 61-63: Analysed By / Date / Checked By / Date) is
handled outside the definition, matching A6A/A6B. Not modelled as fields.
"""
from scripts.template_definitions._common import SeedTemplate, sst_rsd_criterion

#  Left block carries up to 6 Standard replicate rows (Standard-01..06).
_STD_ROWS = 6
#  Right block carries up to 7 BKT Standard rows (BKT Standard-01..07); only 3
#  are filled in the fixture, the rest stay blank.
_BKT_ROWS = 7
#  Sample table: 16 real Sample Solution rows on the sheet; the sheet has spare
#  formula rows beyond that, so cap at 25 with a default of 16.
_SAMPLE_MAX = 25
_SAMPLE_DEFAULT = 16


# ── Context header (sheet rows 2-6) ──────────────────────────────────
def _context() -> list[dict]:
    return [
        {"key": "date_of_analysis", "kind": "context", "type": "date",
         "label": "Date of Analysis", "source": "session.date",
         "overridable": True},                                              # C3
        {"key": "product_name", "kind": "context", "type": "text",
         "label": "Product", "source": "product.name",
         "default": " Argatroban Injection", "overridable": True},          # C4
        {"key": "instrument_id", "kind": "context", "type": "text",
         "label": "Instrument ID.", "default": "AD/HRMS/001",
         "overridable": True},                                              # C5
        {"key": "content_test", "kind": "context", "type": "text",
         "label": "Content (Test)", "default": "N-Nitroso Argatroban",
         "overridable": True},                                              # C6
    ]


# ── Standard preparation (sheet rows 8-11) ───────────────────────────
def _standard_group() -> dict:
    #  O11 = E11/F11*G11/H11*I11/J11*D11/100*1000*K11/L11*M11/N11*1000
    #  (exact term order; D11/100*1000 sits mid-expression). Gold = 1.0416537600000002.
    return {
        "key": "standard", "kind": "singleton", "label": "Standard Preparation",
        "fields": [
            {"key": "name", "kind": "input", "type": "text", "label": "Name",
             "default": "N-Nitroso Argatroban"},                            # B11
            {"key": "batch_no", "kind": "input", "type": "text",
             "label": "Batch No.", "default": "SRL-3019-20"},               # C11
            {"key": "purity", "kind": "input", "label": "Purity/Potency",
             "unit": "%", "required": True, "default": 96.88},              # D11
            {"key": "weight_mg", "kind": "input", "label": "Weight in mg",
             "unit": "mg", "required": True, "default": 2.24},              # E11
            {"key": "stock_i", "kind": "input", "label": "Stock Solution I",
             "default": 20},                                                # F11
            {"key": "ml_stock_i", "kind": "input", "label": "mL of Stock Solution I",
             "unit": "mL", "default": 0.15},                                # G11
            {"key": "stock_ii", "kind": "input", "label": "Stock Solution II",
             "default": 10},                                                # H11
            {"key": "ml_stock_ii", "kind": "input", "label": "mL of Stock Solution II",
             "unit": "mL", "default": 0.1},                                 # I11
            {"key": "stock_iii", "kind": "input", "label": "Stock Solution III",
             "default": 10},                                                # J11
            {"key": "ml_stock_iii", "kind": "input", "label": "mL of Stock Solution III",
             "unit": "mL", "default": 0.64},                                # K11
            {"key": "stock_iv", "kind": "input", "label": "Stock Solution IV",
             "default": 10},                                                # L11
            {"key": "ml_stock_iv", "kind": "input", "label": "mL of Stock Solution IV",
             "unit": "mL", "default": 1},                                   # M11
            {"key": "standard_solution", "kind": "input",
             "label": "Standard solution", "default": 1},                   # N11
            {"key": "std_conc_ppb", "kind": "calculated",
             "label": "Standard Conc. In ppb", "unit": "ppb",
             "expression": "weight_mg / stock_i * ml_stock_i / stock_ii"
                           " * ml_stock_ii / stock_iii * purity / 100 * 1000"
                           " * ml_stock_iii / stock_iv * ml_stock_iv"
                           " / standard_solution * 1000",
             #  Displayed to 4 dp per the sheet: 1.0416537600000002 -> 1.0417.
             "rounding": {"mode": "round", "digits": 4}},                   # O11
        ],
    }


# ── Blank chromatogram area (sheet C15) ──────────────────────────────
def _blank_group() -> dict:
    #  Sheet rows 14-15: the Blank is the first row of the Name/Area/Corrected
    #  area block (B15="Blank", C15=0, D15=0). Modelled as a single-row table so
    #  it renders with the same three columns as the Standard area table. C15 = 0
    #  is the blank area subtracted from every raw area (corrected = area - C15),
    #  referenced downstream as `blank.area[0]`.
    return {
        "key": "blank", "kind": "table", "label": "Blank chromatogram",
        "rows": {"min": 1, "max": 1, "default": 1, "labelFrom": "name"},
        "fields": [
            {"key": "name", "kind": "input", "type": "text", "label": "Name",
             "default": "Blank"},                                           # B15
            {"key": "area", "kind": "area", "label": "Area", "default": 0}, # C15
            {"key": "corrected", "kind": "calculated", "label": "Corrected area",
             "expression": "area - area"},                                  # D15 = C15 - C15 = 0
        ],
    }


# ── Standard & blank chromatogram areas — left block (rows 15-25) ─────
def _std_areas_group() -> dict:
    #  B17..B22 Standard-01..06 (Name of Standard); C17..C22 Area;
    #  D17..D22 corrected = Cn - C$15.
    return {
        "key": "std_areas", "kind": "table", "label": "Standard area",
        "rows": {"min": 1, "max": _STD_ROWS, "default": _STD_ROWS,
                 "labelFrom": "name"},
        "fields": [
            {"key": "name", "kind": "input", "type": "text",
             "label": "Name of Standard"},                                  # B17..B22
            {"key": "area", "kind": "area", "label": "Area"},               # C17..C22
            {"key": "corrected", "kind": "calculated", "label": "Corrected area",
             "expression": "area - blank.area[0]"},                        # D17..D22
        ],
        "footer": [
            {"label": "Average Area", "ref": "std_stats.avg_area"},
            {"label": "Std deviation", "ref": "std_stats.sd_area"},
            {"label": "%RSD", "ref": "std_stats.rsd_area", "unit": "%"},
        ],
    }


def _std_stats_group() -> dict:
    #  D23 = AVERAGEIF(D17:D22,"<>0"); D24 = STDEV(IF(D17:D22<>0,...));
    #  D25 = D24*100/D23. Blank-tolerant mean/sd reproduce the AVERAGEIF/STDEV-IF.
    return {
        "key": "std_stats", "kind": "singleton", "label": "Standard statistics",
        "fields": [
            {"key": "avg_area", "kind": "calculated", "label": "Average Area",
             "expression": "mean(std_areas.corrected)"},                    # D23
            {"key": "sd_area", "kind": "calculated", "label": "Std deviation",
             "expression": "sd(std_areas.corrected)",
             #  Displayed to 2 dp per the sheet: 479.69365... -> 479.69.
             "rounding": {"mode": "round", "digits": 2}},                   # D24
            #  %RSD = D24*100/D23 computed from the UNROUNDED sd (matching the
            #  sheet, which divides the full-precision STDEV by the average),
            #  then displayed to 1 dp: 0.6278... -> 0.6.
            {"key": "rsd_area", "kind": "calculated", "label": "%RSD", "unit": "%",
             "expression": "sd(std_areas.corrected) * 100 / avg_area",
             "rounding": {"mode": "round", "digits": 1}},                   # D25
        ],
    }


# ── BKT standard areas — right block (rows 15-25) ────────────────────
def _bkt_group() -> dict:
    #  E16..E22 BKT Standard-01..07 (Bracketing Standard Name); F16..F22 Area;
    #  G16..G22 corrected = Fn - C$15.
    return {
        "key": "bkt", "kind": "table", "label": "BKT standard area",
        "rows": {"min": 0, "max": _BKT_ROWS, "default": _BKT_ROWS,
                 "labelFrom": "name"},
        "fields": [
            {"key": "name", "kind": "input", "type": "text",
             "label": "Bracketing Standard Name"},                          # E16..E22
            {"key": "area", "kind": "area", "label": "Area"},               # F16..F22
            {"key": "corrected", "kind": "calculated", "label": "Corrected area",
             "expression": "area - blank.area[0]"},                        # G16..G22
        ],
        "footer": [
            {"label": "Average Area", "ref": "bkt_stats.avg_area"},
            {"label": "Std deviation", "ref": "bkt_stats.sd_area"},
            {"label": "%RSD", "ref": "bkt_stats.rsd_area", "unit": "%"},
        ],
    }


def _bkt_stats_group() -> dict:
    #  Sheet quirk: G23 = AVERAGEIF(G15:G22,"<>0") where G15 = D23 (the
    #  left-block standard average, a blank-chromatogram corrected area), so the
    #  BKT statistics POOL the standard average cell with the BKT corrected
    #  areas. G24 = STDEV over the same pool; G25 = G24*100/G23.
    #  Gold G23=81345.75, G24=4455.392341496613, G25=5.477105247043163.
    pool = "pool([std_stats.avg_area], bkt.corrected)"
    return {
        "key": "bkt_stats", "kind": "singleton", "label": "BKT statistics",
        "fields": [
            {"key": "avg_area", "kind": "calculated", "label": "Average Area",
             "expression": f"mean({pool})"},                                # G23
            {"key": "sd_area", "kind": "calculated", "label": "Std deviation",
             "expression": f"sd({pool})"},                                  # G24
            {"key": "rsd_area", "kind": "calculated", "label": "%RSD", "unit": "%",
             "expression": "sd_area * 100 / avg_area"},                     # G25
        ],
    }


# ── Sample preparation table (sheet rows 28-45) ──────────────────────
def _ppm_expression() -> str:
    #  O30 = TRUNC( N/$D$23 * $E$11/$F$11 * $G$11/$H$11 * $I$11/$J$11
    #               * $K$11/$L$11 * $M$11/$N$11 * $D$11/100
    #               * J/I * L/K * E/F * H/G * 1000000 , 4 )
    #  $-anchored = standard-prep constants (std_stats.avg_area = D23; standard.*);
    #  un-anchored J,I,L,K,E,F,H,G = THIS sample row's own columns.
    return (
        "corrected / std_stats.avg_area"
        " * standard.weight_mg / standard.stock_i"
        " * standard.ml_stock_i / standard.stock_ii"
        " * standard.ml_stock_ii / standard.stock_iii"
        " * standard.ml_stock_iii / standard.stock_iv"
        " * standard.ml_stock_iv / standard.standard_solution"
        " * standard.purity / 100"
        " * dilution_2 / ml_1"
        " * dilution_3 / ml_2"
        " * avg_weight / label_claim"
        " * dilution_1 / sample_weight"
        " * 1000000"
    )


def _samples_group() -> dict:
    return {
        "key": "samples", "kind": "table", "label": "Sample Preparation",
        "rows": {"min": 1, "max": _SAMPLE_MAX, "default": _SAMPLE_DEFAULT,
                 "labelFrom": "name"},
        "fields": [
            {"key": "name", "kind": "input", "type": "text",
             "label": "Sample Solution"},                                   # B30..
            {"key": "condition", "kind": "input", "type": "text",
             "label": "Condition", "default": "20-25°C"},                   # D
            {"key": "avg_weight", "kind": "input", "label": "Avg Weight",
             "default": 1},                                                 # E
            {"key": "label_claim", "kind": "input", "label": "Label Claim",
             "default": 100},                                               # F ("Lable Claim")
            {"key": "sample_weight", "kind": "input",
             "label": "Wt. of sample (mg)", "unit": "mg", "default": 1},    # G
            {"key": "dilution_1", "kind": "input", "label": "Dilution", "default": 1},  # H
            {"key": "ml_1", "kind": "input", "label": "mL", "unit": "mL",
             "default": 0.4},                                               # I
            {"key": "dilution_2", "kind": "input", "label": "Dilution", "default": 20},  # J
            {"key": "ml_2", "kind": "input", "label": "mL", "unit": "mL",
             "default": 1},                                                 # K
            {"key": "dilution_3", "kind": "input", "label": "Dilution", "default": 1},  # L
            {"key": "area", "kind": "area", "label": "Area"},               # M
            {"key": "corrected", "kind": "calculated", "label": "Corrected area",
             "expression": "area - blank.area[0]"},                        # N = M - C$15
            {"key": "ppm", "kind": "calculated", "label": "Results in PPM",
             "unit": "ppm", "expression": _ppm_expression(),
             "rounding": {"mode": "trunc", "digits": 4}},                   # O (TRUNC 4)
        ],
    }


NITRO_ROUTINE_DEFINITION = {
    #  Per-row "Results in PPM" (O column) — the natural reportable. A multi-row
    #  group returns the first non-blank per-row value (matches A6A precedent).
    "resultRef": "samples.ppm",
    "context": _context(),
    "groups": [
        _standard_group(),
        _blank_group(),
        _std_areas_group(),
        _std_stats_group(),
        _bkt_group(),
        _bkt_stats_group(),
        _samples_group(),
    ],
    #  Explicit target: the stats group is renamed std_stats, so a bare
    #  sst_rsd_criterion() (default stats.rsd_std) would never evaluate. The BKT
    #  %RSD (bkt_stats.rsd_area) is displayed but deliberately NOT blocking.
    "criteria": [sst_rsd_criterion(target="std_stats.rsd_area", limit=2.0)],
}

NITRO_ROUTINE = SeedTemplate(
    code="TPL-NITRO-0001",
    name="Nitrosamine Routine analysis sheet",
    archetype="A2",
    result_unit="ppm",
    test_code="TST-NITRO-ARGA",
    test_name="Nitrosamine Routine analysis sheet",
    test_type="Quantitative",
    definition=NITRO_ROUTINE_DEFINITION,
)

TEMPLATES = [NITRO_ROUTINE]
