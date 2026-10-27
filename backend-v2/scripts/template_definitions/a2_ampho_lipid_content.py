"""
A2 — Lipid content Ampho (Cholesterol / Alpha tocopherol / DSPG / HSPC).

Reproduces the single-sheet workbook `_dumps/Lipid content_ Ampho.xlsx`
(sheet `PTF_142HIN-400-A`, dims A1:K64) as one seed template. Every table and
formula below is traced to a sheet cell in the inline comments.

This template is modelled on the sibling `a2_bupivacaine_lipid_ratio.py`
(TPL-A2-0004) but is reduced to a PURE lipid-content assay. The differences from
the Bupivacaine template are deliberate and documented here so this module is the
source of record.

────────────────────────────────────────────────────────────────────────────
Sheet → template map

* Header (sheet A5–A17): Generic Name (B5), Product Name (B6), Batch No. (B7),
  TRF No. (B8), AR No. (B9), Storage Condition (B11), Packing Detail (B12),
  Test (B13), Analysis as per (B14), Analysed By (B15), Instrument Id. (B16),
  Date of Analysis (B17). Carried as context fields via `context_header` plus the
  overridable extras below, exactly as the Lyso content template does.

* Standard Details = TABLE, one ROW per compound (sheet rows 22–25, order
  Cholesterol, Alpha tocopherol, DSPG, HSPC). The %Assay chain reaches a
  compound's standard values by its row index `standard.<field>[idx]`.

  TWO-STAGE DILUTION ONLY — this is the key structural difference from
  Bupivacaine. The Ampho standard table has columns Weight (B) / Vol (C) /
  Pip (D) / Vol (E) and then Potency (F) / LC (G) / M.W of Base (H) /
  M.W. of Salt (I). There is NO second pipette/third-volume stage (no pip2/vol3)
  and NO printed Conc. (ppm) column. So `_standard_fields` omits pip2/vol3 and the
  `conc_ppm` calculated column that the Bupivacaine standard table carries, and the
  %Assay chain has a single aliquot stage `pip1/vol2` rather than two.

  Note also the column-letter shift versus Bupivacaine's wider table: on the Ampho
  sheet F = Potency, G = LC, H = MW Base, I = MW Salt (rows 22–25). The %Assay
  mapping below uses the Ampho letters; it does NOT copy Bupivacaine's offsets.

* Standard Replicate Injections (sheet rows 29–34, cols B/C/D/E) = TABLE,
  transposed to one ROW per injection and one AREA COLUMN per compound
  (`chol_area/alpha_area/dspg_area/hspc_area`), each column header auto-fetching
  the compound name from Standard Details via `labelFrom="standard.name[idx]"`.
  Six injections by default. Per-compound Mean (row 35 = AVERAGE), SD (row 36 =
  STDEV) and %RSD (row 37 = SD*100/Mean) aggregate DOWN each compound column and
  are published by the `stats` singleton and rendered in the footer.

* BKT Standard Injections (sheet rows 41–45) = TABLE, same transposed shape, up
  to five bracketing injections. Pooled Mean/SD/%RSD (sheet rows 46–48) are
  computed over the bracketing rows POOLED with the six replicate rows
  (`AVERAGE(B41:B45,B29:B34)` etc.), expressed as
  `mean/sd/rsd(pool(std_areas.<c>_area, bkt_areas.<c>_area))`. The %Assay
  denominator (sheet E56 divides by B35) is the SIX-injection REPLICATE mean
  `stats.mean_std_<c>`, NOT the pooled BKT mean.

* Sample prep = SINGLETON (sheet single prep row 53): Avg Weight (F53=1),
  Sample Weight (G53=1), Vol (H53=250), Pip (I53=1), Vol (J53=1). A single prep
  row → singleton, consistent with the sheet and with `a2_lyso_content.py`'s
  `sample_prep`. The sample table references these fully qualified
  (`sample_prep.vol_h` etc.) because bare names only resolve within the current
  row.

* Sample Details = flat TABLE pinned min==max==default==4 (sheet rows 56–59), one
  ROW per compound, compound name from `standard.name[(rowno - 1)]`. Columns:
  Area-1 (B), Area-2 (C), calculated Avg Area (D56 = (B56+C56)/2), calculated
  % Assay (E56). Pinning min==max hides the add/remove-row controls — the same
  device the Bupivacaine fixed blocks use.

────────────────────────────────────────────────────────────────────────────
Design decisions

(a) NO drug-to-lipid ratio / NO cross-set / NO 2-SET tall layout. This is a pure
    content assay: the sheet has no Bupivacaine mg/mL, no Drug/Lipid ratio, no
    "% Mean each compound" cross-set summary, and a single preparation (not two
    SET blocks). So none of the Bupivacaine `drug_lipid`, `mean_each_compound` or
    tall `lipid_samples` machinery is reproduced. The sample table is flat: exactly
    four rows, one compound each, chosen by row index (`rowno - 1`), so no hidden
    `cidx` modulo selector is needed.

(b) LC as OVERRIDABLE CONTEXT (`lc_chol/lc_alpha/lc_dspg/lc_hspc`, defaults 52,
    0.64, 81.6, 213 — sheet G22..G25), mirroring Bupivacaine's `lc_*`. LC is
    constant per compound across the sheet and is a divisor in the %Assay
    denominator (sheet `.../G22`), so context is the right home. If the lab ever
    needs a per-row LC override, promote them to per-row inputs — the arithmetic
    is unchanged.

(c) EIGHT blocking SST criteria, %RSD NMT 2.0 %, per compound × {replicate,
    pooled bracketing} — the house convention (Bupivacaine, Lyso). Per-compound
    because the sheet computes %RSD per compound column (rows 37 and 48); 2.0 %
    because that is the established NMT in every sibling HPLC template and the
    sheet states no numeric limit. No acceptance range on %Assay (the sheet
    prints none). If the lab later supplies a printed limit, only
    `limit`/`limitText` change.

(d) NO mid-chain rounding. The sheet wraps every formula in IFERROR with no
    ROUND, so %Assay (and Avg Area) are left unrounded; display rounding is the
    front end's concern. Rounding mid-chain would perturb the formula outputs.

%Assay verified numerically against sheet E56..E59 with the replicate means
[1572872.83, 451519.0, 290188.17, 748650.0]: Cholesterol 125.30, Alpha
tocopherol 115.10, DSPG 122.70, HSPC 129.86 — an exact match to the stated
outputs. These are the FORMULA's outputs (the sheet stores no %Assay result), so
the FORMULA is reproduced; the values are not hardcoded.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
)

#  The four lipid compounds, in sheet row order (rows 22–25 of the standard
#  block; rows 56–59 of the sample block).
_COMPOUNDS = [
    ("chol", "Cholesterol"),
    ("alpha", "Alpha tocopherol"),
    ("dspg", "DSPG"),
    ("hspc", "HSPC"),
]

#  Per-compound default LC / label claim (sheet G22..G25).
_LC_DEFAULTS = {"chol": 52, "alpha": 0.64, "dspg": 81.6, "hspc": 213}

#  Standard-detail default rows 22–25, two-stage dilution only:
#  (weight, vol1, pip1, vol2, potency, mw_base, mw_salt)
#  = sheet (B, C, D, E, F, H, I). LC (col G) lives in context (_LC_DEFAULTS).
_STANDARD_DEFAULTS = {
    "chol": (21.04, 100, 1, 1, 99.68, 1, 1),
    "alpha": (32.6, 250, 2, 100, 96.4, 1, 1),
    "dspg": (34.64, 100, 1, 1, 100, 778.07, 801.06),
    "hspc": (86.14, 100, 1, 1, 100, 1, 1),
}

#  Seed sample Area-1 / Area-2 per compound (sheet B56..C59).
_SAMPLE_AREA_DEFAULTS = {
    "chol": (1955799, 1953318),
    "alpha": (532209, 526196),
    "dspg": (353084, 337734),
    "hspc": (964486, 958712),
}

#  Injection rows are expandable. The sheet records six replicate injections
#  (rows 29–34) and up to five bracketing injections (rows 41–45). Cap the row
#  count at 10; blank injection cells are tolerated by mean/sd/rsd (they skip
#  blanks), so a higher cap never perturbs the aggregates.
_MAX_INJ_ROWS = 10
_DEFAULT_STD_ROWS = 6
_DEFAULT_BKT_ROWS = 5


def _standard_fields() -> list[dict]:
    """
    Standard Details as a TABLE — one ROW per compound (sheet rows 22–25).

    TWO dilution stages only (weight, vol1, pip1, vol2): the Ampho sheet has no
    pip2/vol3 third stage and no Conc. (ppm) column, so neither is declared here.
    The %Assay chain reaches a compound's standard values by its row index
    `standard.<field>[idx]`. Per-row seed values are documented in
    `_standard_default_rows()` (the engine seeds the ROW COUNT from `rows.default`;
    the per-row values are entered on the worksheet, matching the sibling A2
    Bupivacaine template — a single field-level `default` cannot differ per row).
    """
    return [
        {"key": "name", "kind": "input", "type": "text", "label": "Compound Name"},
        {"key": "weight", "kind": "input", "label": "Weight in mg", "unit": "mg"},
        {"key": "vol1", "kind": "input", "label": "Vol", "unit": "mL"},
        {"key": "pip1", "kind": "input", "label": "Pip", "unit": "mL"},
        {"key": "vol2", "kind": "input", "label": "Vol", "unit": "mL"},
        {"key": "potency", "kind": "input", "label": "Potency", "unit": "%"},
        {"key": "mw_base", "kind": "input", "label": "M.W of Base"},
        {"key": "mw_salt", "kind": "input", "label": "M.W. of Salt"},
    ]


def _standard_default_rows() -> list[dict]:
    """Seed rows for the 4 compounds, in _COMPOUNDS order (sheet rows 22–25)."""
    rows: list[dict] = []
    for prefix, name in _COMPOUNDS:
        w, v1, p1, v2, pot, mwb, mws = _STANDARD_DEFAULTS[prefix]
        rows.append({
            "name": name, "weight": w, "vol1": v1, "pip1": p1, "vol2": v2,
            "potency": pot, "mw_base": mwb, "mw_salt": mws,
        })
    return rows


def _area_columns() -> list[dict]:
    """
    One AREA column per compound (chol, alpha, dspg, hspc — in _COMPOUNDS order),
    shared by the transposed replicate and BKT tables. Each column HEADER
    auto-fetches the compound name from Standard Details (row idx) via
    `labelFrom="standard.name[<idx>]"`, so renaming a standard renames the column.
    """
    return [
        {
            "key": f"{prefix}_area",
            "kind": "area",
            "label": f"{name} Area",
            "labelFrom": f"standard.name[{idx}]",
        }
        for idx, (prefix, name) in enumerate(_COMPOUNDS)
    ]


def _std_area_fields() -> list[dict]:
    """
    Standard replicate injections as a TABLE — one ROW per injection, one COLUMN
    per compound (sheet rows 29–34). Row label is a plain `inj_label` text input;
    the four area columns carry `labelFrom` headers. No per-row Mean/SD/%RSD —
    those aggregate DOWN each compound column and are published by the `stats`
    singleton, so the column series `std_areas.<c>_area` holds ONLY injection rows.
    """
    return [
        {"key": "inj_label", "kind": "input", "type": "text", "label": "Injection"},
        *_area_columns(),
    ]


def _bkt_area_fields() -> list[dict]:
    """
    BKT (bracketing) standard injections as a TABLE — same transposed shape as
    `std_areas` (sheet rows 41–45). Pooling with the matching replicate column
    lives in the `stats` singleton (`pool(std_areas.<c>_area, bkt_areas.<c>_area)`),
    matching the sheet's `AVERAGE(B41:B45,B29:B34)`, so `bkt_areas` carries no
    calculated fields.
    """
    return [
        {"key": "inj_label", "kind": "input", "type": "text", "label": "Injection"},
        *_area_columns(),
    ]


def _stats_fields() -> list[dict]:
    """
    Per-compound statistics singleton. Each stat aggregates DOWN a compound COLUMN
    of the transposed injection tables:
        mean_std_<c>  = mean(std_areas.<c>_area)              (sheet row 35)
        sd_std_<c>    = sd(std_areas.<c>_area)                (sheet row 36)
        rsd_std_<c>   = rsd(std_areas.<c>_area)               (sheet row 37)
        mean_pool_<c> = mean(pool(std_areas.<c>_area, bkt_areas.<c>_area))  (row 46)
        sd_pool_<c>   = sd(pool(...))                         (sheet row 47)
        rsd_pool_<c>  = rsd(pool(...))                        (sheet row 48)
    `rsd()` is sd*100/mean (matching the sheet's SD*100/Mean) and needs ≥2 values;
    the six replicates satisfy this. The %Assay denominator reads `mean_std_<c>`.
    """
    fields: list[dict] = []
    for prefix, name in _COMPOUNDS:
        col = f"{prefix}_area"
        std = f"std_areas.{col}"
        pooled = f"pool(std_areas.{col}, bkt_areas.{col})"
        fields += [
            {"key": f"mean_std_{prefix}", "kind": "calculated", "label": f"{name} Mean STD", "expression": f"mean({std})"},
            {"key": f"sd_std_{prefix}", "kind": "calculated", "label": f"{name} SD", "expression": f"sd({std})"},
            {"key": f"rsd_std_{prefix}", "kind": "calculated", "label": f"{name} %RSD", "unit": "%", "expression": f"rsd({std})"},
            {"key": f"mean_pool_{prefix}", "kind": "calculated", "label": f"{name} Pooled Mean", "expression": f"mean({pooled})"},
            {"key": f"sd_pool_{prefix}", "kind": "calculated", "label": f"{name} Pooled SD", "expression": f"sd({pooled})"},
            {"key": f"rsd_pool_{prefix}", "kind": "calculated", "label": f"{name} Pooled %RSD", "unit": "%", "expression": f"rsd({pooled})"},
        ]
    return fields


def _assay_expression(idx: int, prefix: str) -> str:
    """
    Per-compound %Assay (sheet E56 for Cholesterol):
        D56/B35 * B22/C22 * D22/E22 * J53/I53 * H53/G53 * F53/G22 * F22 * H22/I22
    mapped field-for-field onto the Ampho column letters (F=Potency, G=LC,
    H=MW Base, I=MW Salt):
        avg_area / stats.mean_std_<c>                      (D56/B35)
      * standard.weight[idx] / standard.vol1[idx]          (B22/C22)
      * standard.pip1[idx]   / standard.vol2[idx]          (D22/E22)
      * sample_prep.vol_j    / sample_prep.pip_i           (J53/I53)
      * sample_prep.vol_h    / sample_prep.sample_weight   (H53/G53)
      * sample_prep.avg_weight / lc_<c>                    (F53/G22; G22 = LC)
      * standard.potency[idx]                              (F22 = Potency)
      * standard.mw_base[idx] / standard.mw_salt[idx]      (H22/I22)
    `avg_area` is this row's calculated Avg Area; `mean_std_<c>` is this
    compound's six-injection replicate mean. NO mid-chain rounding.
    """
    return (
        f"avg_area / stats.mean_std_{prefix} "
        f"* standard.weight[{idx}] / standard.vol1[{idx}] "
        f"* standard.pip1[{idx}] / standard.vol2[{idx}] "
        f"* sample_prep.vol_j / sample_prep.pip_i "
        f"* sample_prep.vol_h / sample_prep.sample_weight "
        f"* sample_prep.avg_weight / lc_{prefix} "
        f"* standard.potency[{idx}] "
        f"* standard.mw_base[{idx}] / standard.mw_salt[{idx}]"
    )


def _pct_assay_expression() -> str:
    """
    Select the per-compound %Assay chain for THIS row by its index (rowno - 1).

    The sample table is flat — exactly four rows, one compound each, in
    _COMPOUNDS order — so the row's compound is fixed by its position. A
    `coalesce(if(rowno == k+1, <chain k>, blank()), ...)` over k = 0..3 binds the
    correct `lc_<c>` context key and `stats.mean_std_<c>` key per row (these are
    not index-addressable the way `standard.<field>[idx]` is). `if()` is lazy, so
    only the matching branch evaluates; `coalesce` returns the single non-blank
    branch. This mirrors Bupivacaine's `_compound_select`, keyed on `rowno`.
    """
    branches = [
        f"if(rowno == {k + 1}, {_assay_expression(k, prefix)}, blank())"
        for k, (prefix, _name) in enumerate(_COMPOUNDS)
    ]
    return "coalesce(" + ", ".join(branches) + ")"


def _sample_fields() -> list[dict]:
    """
    Flat sample table — one ROW per compound (sheet rows 56–59). The row's
    compound is its position (`rowno - 1`): row 1 Cholesterol .. row 4 HSPC.
    Columns: Compound Name (read-only, from Standard Details), Area-1, Area-2,
    calculated Avg Area, calculated % Assay.
    """
    return [
        #  Compound Name — read-only, fetched from Standard Details by row index
        #  so it renames when a standard is renamed (sheet A56 = A22, etc.).
        {
            "key": "compound_name",
            "kind": "calculated",
            "type": "text",
            "label": "Compound Name",
            "expression": "standard.name[(rowno - 1)]",
        },
        #  Sheet B56 / C56 — the two sample injection areas.
        {"key": "area1", "kind": "area", "label": "Area-1"},
        {"key": "area2", "kind": "area", "label": "Area-2"},
        #  Sheet D56 = (B56 + C56) / 2. NO rounding.
        {
            "key": "avg_area",
            "kind": "calculated",
            "label": "Avg. Area",
            "expression": "(area1 + area2) / 2",
        },
        #  Sheet E56 — per-compound %Assay, bound to this row's compound by index.
        {
            "key": "pct_assay",
            "kind": "calculated",
            "label": "% Assay",
            "unit": "%",
            "expression": _pct_assay_expression(),
        },
    ]


def _rsd_criterion(key: str, label: str, target: str) -> dict:
    """`sst_rsd_criterion` shape with a distinct key — eight are needed here."""
    return {
        "key": key,
        "label": label,
        "target": target,
        "operator": "lte",
        "limit": 2.0,
        "severity": "blocking",
        "limitText": "NMT 2.0 %",
    }


AMPHO_LIPID_DEFINITION = {
    "resultRef": "samples.pct_assay",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {"key": "product_name", "kind": "context", "type": "text", "label": "Product Name", "overridable": True},
            {"key": "storage_condition", "kind": "context", "type": "text", "label": "Storage Condition", "overridable": True},
            {"key": "packing_detail", "kind": "context", "type": "text", "label": "Packing Detail", "overridable": True},
            {"key": "test_name_ctx", "kind": "context", "type": "text", "label": "Test", "overridable": True},
            {"key": "analysis_as_per", "kind": "context", "type": "text", "label": "Analysis as per", "overridable": True},
            {"key": "trf_no", "kind": "context", "type": "text", "label": "TRF No.", "overridable": True},
            {"key": "ar_no", "kind": "context", "type": "text", "label": "AR No.", "overridable": True},
            #  Per-compound LC / label claim (sheet G22..G25). Constant per
            #  compound across the sheet, a divisor in the %Assay denominator →
            #  overridable context. Read directly by the %Assay chain as `lc_<c>`.
            {"key": "lc_chol", "kind": "context", "label": "LC — Cholesterol", "default": _LC_DEFAULTS["chol"], "overridable": True},
            {"key": "lc_alpha", "kind": "context", "label": "LC — Alpha tocopherol", "default": _LC_DEFAULTS["alpha"], "overridable": True},
            {"key": "lc_dspg", "kind": "context", "label": "LC — DSPG", "default": _LC_DEFAULTS["dspg"], "overridable": True},
            {"key": "lc_hspc", "kind": "context", "label": "LC — HSPC", "default": _LC_DEFAULTS["hspc"], "overridable": True},
        ],
    ),
    "groups": [
        #  Weighed standard details — one row per compound (sheet rows 22–25).
        #  Two-stage dilution only; defaults seed the sheet's values.
        {
            "key": "standard",
            "kind": "table",
            "label": "Standard Details",
            "rows": {"min": 1, "max": _MAX_INJ_ROWS, "default": len(_COMPOUNDS), "labelFrom": "name"},
            "fields": _standard_fields(),
        },
        #  Standard replicate injections, transposed to one ROW per injection /
        #  one COLUMN per compound (sheet rows 29–34). Per-compound Mean/SD/%RSD
        #  (rows 35–37) render in the footer from the `stats` singleton.
        {
            "key": "std_areas",
            "kind": "table",
            "label": "Standard Replicate Injections",
            "rows": {"min": 1, "max": _MAX_INJ_ROWS, "default": _DEFAULT_STD_ROWS, "labelFrom": "inj_label"},
            "fields": _std_area_fields(),
            "footer": [
                {"label": "Mean", "ref": "stats.mean_std_chol"},
                {"ref": "stats.mean_std_alpha"},
                {"ref": "stats.mean_std_dspg"},
                {"ref": "stats.mean_std_hspc"},
                {"label": "SD", "ref": "stats.sd_std_chol"},
                {"ref": "stats.sd_std_alpha"},
                {"ref": "stats.sd_std_dspg"},
                {"ref": "stats.sd_std_hspc"},
                {"label": "% RSD", "ref": "stats.rsd_std_chol", "unit": "%"},
                {"ref": "stats.rsd_std_alpha", "unit": "%"},
                {"ref": "stats.rsd_std_dspg", "unit": "%"},
                {"ref": "stats.rsd_std_hspc", "unit": "%"},
            ],
        },
        #  Bracketing standard injections (sheet rows 41–45). Footer Mean/SD/%RSD
        #  (rows 46–48) are POOLED per compound column with the matching std_areas
        #  column (stats.*_pool_*), matching AVERAGE(B41:B45,B29:B34). Blanks ok.
        {
            "key": "bkt_areas",
            "kind": "table",
            "label": "BKT Standard Injections",
            "rows": {"min": 1, "max": _MAX_INJ_ROWS, "default": _DEFAULT_BKT_ROWS, "labelFrom": "inj_label"},
            "fields": _bkt_area_fields(),
            "footer": [
                {"label": "Mean", "ref": "stats.mean_pool_chol"},
                {"ref": "stats.mean_pool_alpha"},
                {"ref": "stats.mean_pool_dspg"},
                {"ref": "stats.mean_pool_hspc"},
                {"label": "SD", "ref": "stats.sd_pool_chol"},
                {"ref": "stats.sd_pool_alpha"},
                {"ref": "stats.sd_pool_dspg"},
                {"ref": "stats.sd_pool_hspc"},
                {"label": "% RSD", "ref": "stats.rsd_pool_chol", "unit": "%"},
                {"ref": "stats.rsd_pool_alpha", "unit": "%"},
                {"ref": "stats.rsd_pool_dspg", "unit": "%"},
                {"ref": "stats.rsd_pool_hspc", "unit": "%"},
            ],
        },
        #  Standard statistics (rows 35–37) + pooled BKT statistics (rows 46–48).
        {
            "key": "stats",
            "kind": "singleton",
            "label": "Standard Statistics",
            "fields": _stats_fields(),
        },
        #  Sample preparation — single prep row (sheet row 53).
        {
            "key": "sample_prep",
            "kind": "singleton",
            "label": "Sample Details",
            "fields": [
                {"key": "avg_weight", "kind": "input", "label": "Avg Weight", "default": 1},        # F53
                {"key": "sample_weight", "kind": "input", "label": "Sample Weight", "unit": "mg", "default": 1},  # G53
                {"key": "vol_h", "kind": "input", "label": "Vol", "unit": "mL", "default": 250},    # H53
                {"key": "pip_i", "kind": "input", "label": "Pip", "unit": "mL", "default": 1},      # I53
                {"key": "vol_j", "kind": "input", "label": "Vol", "unit": "mL", "default": 1},      # J53
            ],
        },
        #  Sample Details — flat table, FIXED at 4 rows (pinned min==max==4), one
        #  compound per row by index (sheet rows 56–59). Area-1/Area-2 seeded.
        {
            "key": "samples",
            "kind": "table",
            "label": "Sample Details",
            "rows": {"min": 4, "max": 4, "default": 4},
            "fields": _sample_fields(),
        },
    ],
    "criteria": [
        _rsd_criterion("sst_std_rsd_chol", "%RSD of Cholesterol standard replicate injections", "stats.rsd_std_chol"),
        _rsd_criterion("sst_std_rsd_alpha", "%RSD of Alpha tocopherol standard replicate injections", "stats.rsd_std_alpha"),
        _rsd_criterion("sst_std_rsd_dspg", "%RSD of DSPG standard replicate injections", "stats.rsd_std_dspg"),
        _rsd_criterion("sst_std_rsd_hspc", "%RSD of HSPC standard replicate injections", "stats.rsd_std_hspc"),
        _rsd_criterion("sst_pool_rsd_chol", "%RSD of Cholesterol pooled bracketing injections", "stats.rsd_pool_chol"),
        _rsd_criterion("sst_pool_rsd_alpha", "%RSD of Alpha tocopherol pooled bracketing injections", "stats.rsd_pool_alpha"),
        _rsd_criterion("sst_pool_rsd_dspg", "%RSD of DSPG pooled bracketing injections", "stats.rsd_pool_dspg"),
        _rsd_criterion("sst_pool_rsd_hspc", "%RSD of HSPC pooled bracketing injections", "stats.rsd_pool_hspc"),
    ],
}

AMPHO_LIPID_CONTENT = SeedTemplate(
    code="TPL-A2-0005",
    name="Lipid content Ampho",
    archetype="A2",
    result_unit="%",
    test_code="TST-LIPID-AMPHO",
    test_name="Lipid Content (Ampho) by HPLC",
    test_type="Quantitative",
    definition=AMPHO_LIPID_DEFINITION,
)

TEMPLATES = [AMPHO_LIPID_CONTENT]
