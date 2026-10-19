"""
A2 — Bupivacaine Lipid Content & Drug-to-Lipid Ratio.

Reproduces the two-sheet workbook
`Test types/Bupivacaine Lipid & Drug to lipid Ratio.xlsx`
(sheets `'Lipid '` and `'Drug to Lipid ratio Auto Calc'`) in one template. Every
table and formula below is traced to a sheet cell in the inline comments.

────────────────────────────────────────────────────────────────────────────
Design decisions (restated from the task plan; the reasoning lives here so the
module is the source of record).

(a) ONE template, two sheets modelled as groups.
    The workbook produces ONE reportable per batch — the Drug/Lipid Ratio — and
    sheet 2 is pure arithmetic over sheet 1's `%Mean` outputs
    (`'Drug to Lipid ratio Auto Calc'!H18 = 'Lipid '!O43`). So both sheets become
    groups of one template, and the Drug-to-Lipid group reads the Lipid sample
    group's `%Mean` directly rather than re-typing it.

    DISTINCT from the existing `TPL-A12-0002 "Drug-to-Lipid Ratio"`, which carries
    the lipid `%Mean` and drug `%Assay` in by hand and performs NO HPLC
    lipid-content calculation. Here the lipid content is computed from first
    principles (weighed standard → replicate + pooled bracketing suitability →
    per-compound %Assay) and the ratio falls out of it. `a12_derived_rollups.py`
    / `TPL-A12-0002` / `TST-DLR` are NOT touched.

(b) Per-compound layout: compounds as fixed COLUMNS/scalars (mirrors
    `a2_lyso_content.py`), NOT table rows.
    Sheet `N39` (Tricaprylin %Assay) divides by that compound's own replicate
    mean (`$B$31`/`$C$31`/`$D$31`/`$E$31`) and multiplies by that compound's own
    standard-detail row (`B18..J18` for Tricaprylin, row 19 for DPPG, etc.). A
    compounds-as-rows layout would have to reach "the DPPG column mean" and "the
    DPPG standard row" by aligned row index — fragile. Fixed columns keep every
    cross-reference a plain scalar (`stats.mean_std_tri`, `standard.tri_weight`),
    exactly as the sibling A2 content template already does.

(c) resultRef = "drug_lipid.ratio" — the Drug/Lipid Ratio. The Drug-to-Lipid
    group is a table (one batch per row); the engine returns the LAST non-blank
    ratio down the rows, the correct reportable for a multi-batch sheet. Each
    batch row also exposes its own ratio for display.

(d) Archetype / code: A2, next free code TPL-A2-0004. The dominant, novel work
    is a multi-analyte (4-lipid) HPLC content assay with weighed standard,
    replicate + pooled-bracketing suitability and per-compound %Assay — the A2
    family (TPL-A2-0001..0003 are all multi-analyte HPLC content). A12 "derived
    roll-ups" is the wrong home: A12's defining trait is inputs carried from other
    tests with no injections on the worksheet; this template computes the lipid
    content from its own injections. The Drug-to-Lipid ratio is a downstream
    arithmetic section, not the archetype's identity.
    result_unit = None (unitless ratio), matching TPL-A12-0002.
    Test Master: TST-LIPID-RATIO / "Lipid Content & Drug-to-Lipid Ratio by HPLC"
    / Quantitative — created via `ensure_test` if absent. NOT TST-DLR (that Test
    is bound to the carried-over TPL-A12-0002; this is a different method).

(e) SST / acceptance criteria. The sheet computes %RSD per compound for both the
    replicate injections (row 33) and the pooled replicate+bracketing block
    (row 33, BKT) but prints no numeric limit text. Following the house
    convention (`a2_lyso_content.py` uses NMT 2.0 % per compound), add EIGHT
    blocking criteria: replicate %RSD and pooled-bracketing %RSD, each NMT 2.0 %,
    for each of the 4 compounds. Per-compound (not overall) because the sheet
    computes RSD per compound column; 2.0 % because that is the established NMT in
    every sibling HPLC template and the sheet states none. If the lab later
    supplies a printed limit, only `limit`/`limitText` change.

LC placement: the four per-compound label claims (sheet `G39=2`, `G40=0.9`,
`G41=4.7`, `G42=8.2`) and Bupivacaine LC (`L18=13.3`) are constant per compound
across every batch on the sheet, so they are modelled as OVERRIDABLE CONTEXT
fields `lc_tri/lc_dppg/lc_chol/lc_depc`/`lc_bupi`. They feed both the Lipid
%Assay denominator (`.../G39`) and the Drug-to-Lipid `I = %Mean*LC/100` column.
If the lab needs per-batch LC override, promote them to per-row inputs — the
arithmetic is unchanged.

mg/mL(Lipid) reference: the Drug-to-Lipid `I` column (`H18*G18/100`) reads the
matching batch's Lipid `%Mean`. Because `lipid_samples` and `drug_lipid` carry
the batches in the SAME order, each `drug_lipid` row reads its partner via
`lipid_samples.<cmp>_mean[rowno-1]` (whole-column series indexed by the current
row number). Chosen over recomputing mg/mL inside `lipid_samples` because it
keeps the reference legible and mirrors the sheet's cross-sheet `='Lipid '!O43`.

Rounding: the sheet wraps every formula in IFERROR but applies NO explicit ROUND,
so NO mid-chain rounding is applied here (rounding mid-chain would perturb the
gold values). The reportable `ratio` is left unrounded; display rounding is the
front end's concern.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
)

#  The four lipid compounds, in sheet column order (B/C/D/E of the standard and
#  replicate blocks; F39..F42 of the sample block).
_COMPOUNDS = [
    ("tri", "Tricaprylin"),
    ("dppg", "DPPG Na"),
    ("chol", "Cholesterol"),
    ("depc", "DEPC"),
]

#  Per-compound default label claim (sheet G39/G40/G41/G42) and standard-detail
#  rows 18–21 (B=weight, C=vol1, D=pip1, E=vol2, F=pip2, G=vol3, H=potency,
#  I=mw_base, J=mw_salt).
_LC_DEFAULTS = {"tri": 2, "dppg": 0.9, "chol": 4.7, "depc": 8.2}
_STANDARD_DEFAULTS = {
    #  prefix: (weight, vol1, pip1, vol2, pip2, vol3, potency, mw_base, mw_salt)
    "tri": (99.1, 50, 6, 100, 1, 1, 100, 1, 1),
    "dppg": (46.79, 50, 6, 100, 1, 1, 99.3, 721.9602, 744.95),
    "chol": (28.51, 100, 1, 1, 1, 1, 100, 1, 1),
    "depc": (49.32, 100, 1, 1, 1, 1, 99.2, 1, 1),
}


def _standard_fields() -> list[dict]:
    """
    Standard Details as a TABLE — one ROW per compound (sheet rows 18–21).

    House rule: with more than 2 standards, the standard-details block is a
    tabular group (compound per row) rather than per-compound column scalars.
    The %Assay chain reaches a compound's standard values by row index:
    `standard.<field>[idx]`, where idx is the compound's position in _COMPOUNDS.
    """
    fields = [
        {"key": "name", "kind": "input", "type": "text", "label": "Compound Name"},
        {"key": "weight", "kind": "input", "label": "Weight in mg", "unit": "mg"},
        {"key": "vol1", "kind": "input", "label": "Vol", "unit": "mL"},
        {"key": "pip1", "kind": "input", "label": "Pip", "unit": "mL"},
        {"key": "vol2", "kind": "input", "label": "Vol", "unit": "mL"},
        {"key": "pip2", "kind": "input", "label": "Pip", "unit": "mL"},
        {"key": "vol3", "kind": "input", "label": "Vol", "unit": "mL"},
        {"key": "potency", "kind": "input", "label": "Potency", "unit": "%"},
        {"key": "mw_base", "kind": "input", "label": "M.W of Base"},
        {"key": "mw_salt", "kind": "input", "label": "M.W. of Salt"},
        {
            "key": "conc_ppm",
            "kind": "calculated",
            "label": "Conc. (ppm)",
            "unit": "ppm",
            #  Sheet K18 = IFERROR(B/C*D/E*F/G*H/100*I/J*1000, "") — per row.
            "expression": (
                "weight / vol1 * pip1 / vol2 * pip2 / vol3 "
                "* potency / 100 * mw_base / mw_salt * 1000"
            ),
            "rounding": {"mode": "round", "digits": 2},
        },
    ]
    return fields


def _standard_default_rows() -> list[dict]:
    """Seed rows for the 4 compounds, in _COMPOUNDS order (sheet rows 18–21)."""
    rows: list[dict] = []
    for prefix, name in _COMPOUNDS:
        w, v1, p1, v2, p2, v3, pot, mwb, mws = _STANDARD_DEFAULTS[prefix]
        rows.append({
            "name": name, "weight": w, "vol1": v1, "pip1": p1, "vol2": v2,
            "pip2": p2, "vol3": v3, "potency": pot, "mw_base": mwb, "mw_salt": mws,
        })
    return rows


def _area_columns() -> list[dict]:
    """The 4 per-compound AREA columns shared by the replicate and BKT tables."""
    return [
        {"key": f"{prefix}_area", "kind": "area", "label": f"{name} Area", "unit": "µV·s"}
        for prefix, name in _COMPOUNDS
    ]


def _stats_fields() -> list[dict]:
    """
    Replicate stats (sheet B31/B32/B33) and pooled replicate+bracketing stats
    (sheet H31/H32/H33) per compound. The pooled mean/SD/%RSD combine the six
    replicate injections with the bracketing injections via pool(...), matching
    the sheet's `AVERAGE(H25:H30,B25:B30)` / `STDEV(B25:B30,H25:H30)`.
    """
    fields: list[dict] = []
    for prefix, name in _COMPOUNDS:
        rep = f"std_areas.{prefix}_area"
        pooled = f"pool(std_areas.{prefix}_area, bkt_areas.{prefix}_area)"
        fields += [
            {"key": f"mean_std_{prefix}", "kind": "calculated", "label": f"{name} Mean STD", "expression": f"mean({rep})"},
            {"key": f"sd_std_{prefix}", "kind": "calculated", "label": f"{name} SD", "expression": f"sd({rep})"},
            {"key": f"rsd_std_{prefix}", "kind": "calculated", "label": f"{name} %RSD", "unit": "%", "expression": f"rsd({rep})"},
            {"key": f"mean_pool_{prefix}", "kind": "calculated", "label": f"{name} Pooled Mean", "expression": f"mean({pooled})"},
            {"key": f"sd_pool_{prefix}", "kind": "calculated", "label": f"{name} Pooled SD", "expression": f"sd({pooled})"},
            {"key": f"rsd_pool_{prefix}", "kind": "calculated", "label": f"{name} Pooled %RSD", "unit": "%", "expression": f"rsd({pooled})"},
        ]
    return fields


def _assay_expression(prefix: str, area_key: str) -> str:
    """
    Per-compound %Assay (sheet N39 for Tricaprylin):
        M39/$B$31 * B18/C18 * D18/E18 * F18/G18 * J39/I39 * L39/K39
              * H18/G39 * I18/J18 * H39
    mapped field-for-field:
        area / stats.mean_std_<c>
      * standard.<c>_weight / standard.<c>_vol1
      * standard.<c>_pip1  / standard.<c>_vol2
      * standard.<c>_pip2  / standard.<c>_vol3
      * vol_j / sample_weight          (J39/I39)
      * vol_l / pip_k                  (L39/K39)
      * standard.<c>_potency / lc_<c>  (H18/G39; G39 is the compound LC)
      * standard.<c>_mw_base / standard.<c>_mw_salt  (I18/J18)
      * avg_weight                     (H39)
    """
    #  Standard Details is a table (compound per row); reach this compound's
    #  standard values by its row index in _COMPOUNDS.
    idx = [p for p, _ in _COMPOUNDS].index(prefix)
    return (
        f"{area_key} / stats.mean_std_{prefix} "
        f"* standard.weight[{idx}] / standard.vol1[{idx}] "
        f"* standard.pip1[{idx}] / standard.vol2[{idx}] "
        f"* standard.pip2[{idx}] / standard.vol3[{idx}] "
        f"* vol_j / sample_weight "
        f"* vol_l / pip_k "
        f"* standard.potency[{idx}] / lc_{prefix} "
        f"* standard.mw_base[{idx}] / standard.mw_salt[{idx}] "
        f"* avg_weight"
    )


def _lipid_sample_fields() -> list[dict]:
    """
    One batch per row: the text/prep inputs, then per compound two injection area
    columns and the %Assay-1 / %Assay-2 / %Mean calculated columns.
    """
    fields: list[dict] = [
        {"key": "batch_no", "kind": "input", "type": "text", "label": "Batch No."},
        {"key": "storage", "kind": "input", "type": "text", "label": "Storage Condition"},
        {"key": "packing", "kind": "input", "type": "text", "label": "Packing Detail"},
        {"key": "trf_no", "kind": "input", "type": "text", "label": "TRF No."},
        {"key": "ar_no", "kind": "input", "type": "text", "label": "AR No."},
        {"key": "avg_weight", "kind": "input", "label": "Avg Weight", "default": 1.005},   # H
        {"key": "sample_weight", "kind": "input", "label": "Sample Weight", "unit": "mg"},  # I
        {"key": "vol_j", "kind": "input", "label": "Vol", "unit": "mL", "default": 25},      # J
        {"key": "pip_k", "kind": "input", "label": "Pip", "unit": "mL", "default": 1},       # K
        {"key": "vol_l", "kind": "input", "label": "Vol", "unit": "mL", "default": 1},        # L
    ]
    #  Per-compound injection-1 and injection-2 area columns (sheet M39 / M43 ...).
    for prefix, name in _COMPOUNDS:
        fields.append({"key": f"{prefix}_area1", "kind": "area", "label": f"{name} Area (Inj 1)", "unit": "µV·s"})
        fields.append({"key": f"{prefix}_area2", "kind": "area", "label": f"{name} Area (Inj 2)", "unit": "µV·s"})
    #  Per-compound %Assay (inj 1 / inj 2) and %Mean (sheet N/O columns).
    for prefix, name in _COMPOUNDS:
        fields += [
            {
                "key": f"{prefix}_assay1",
                "kind": "calculated",
                "label": f"{name} % Assay (Inj 1)",
                "unit": "%",
                "expression": _assay_expression(prefix, f"{prefix}_area1"),
            },
            {
                "key": f"{prefix}_assay2",
                "kind": "calculated",
                "label": f"{name} % Assay (Inj 2)",
                "unit": "%",
                "expression": _assay_expression(prefix, f"{prefix}_area2"),
            },
            {
                "key": f"{prefix}_mean",
                "kind": "calculated",
                "label": f"{name} % Mean",
                "unit": "%",
                #  Sheet O43 = AVERAGE(N39, N43); a blank 2nd injection leaves the
                #  inj-1 value (mean skips blanks), matching the sheet.
                "expression": f"mean([{prefix}_assay1, {prefix}_assay2])",
            },
        ]
    return fields


def _drug_lipid_fields() -> list[dict]:
    """
    One batch per row (same order as `lipid_samples`): the four mg/mL(Lipid)
    columns, their sum, the Bupivacaine mg/mL and the Drug/Lipid ratio.
    """
    fields: list[dict] = [
        {"key": "batch_no", "kind": "input", "type": "text", "label": "Batch No."},
    ]
    #  I18 = H18 * G18 / 100 = (Lipid %Mean for this batch) * compound LC / 100.
    #  `lipid_samples.<c>_mean[rowno-1]` reads the matching batch row.
    for prefix, name in _COMPOUNDS:
        fields.append(
            {
                "key": f"{prefix}_mgml",
                "kind": "calculated",
                "label": f"{name} mg/mL (Lipid)",
                "unit": "mg/mL",
                "expression": f"lipid_samples.{prefix}_mean[rowno - 1] * lc_{prefix} / 100",
            }
        )
    fields += [
        {
            "key": "sum_lipid",
            "kind": "calculated",
            "label": "mg/mL (Sum of Lipid)",
            "unit": "mg/mL",
            #  Sheet J18 = SUM(I18:I21) — the 4 compound mg/mL columns.
            "expression": "tri_mgml + dppg_mgml + chol_mgml + depc_mgml",
        },
        {
            "key": "pct_assay_bupi",
            "kind": "input",
            "label": "% Assay of Bupivacaine",
            "unit": "%",
            #  Sheet K18/K23/K28 — a per-batch entered value (99.9 / 97.8 / 100.3).
            "required": True,
        },
        {
            "key": "mgml_bupi",
            "kind": "calculated",
            "label": "mg/mL of Bupivacaine",
            "unit": "mg/mL",
            #  Sheet M18 = IFERROR(K18*L18/100, "")  (L18 = Bupivacaine LC).
            "expression": "pct_assay_bupi * lc_bupi / 100",
        },
        {
            "key": "ratio",
            "kind": "calculated",
            "label": "Drug/Lipid Ratio",
            #  Sheet N18 = IFERROR(M18/J18, "").
            "expression": "mgml_bupi / sum_lipid",
        },
    ]
    return fields


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


LIPID_RATIO_DEFINITION = {
    "resultRef": "drug_lipid.ratio",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {"key": "product_name", "kind": "context", "type": "text", "label": "Product Name", "overridable": True},
            {"key": "test_name_ctx", "kind": "context", "type": "text", "label": "Test", "overridable": True},
            {"key": "analysis_as_per", "kind": "context", "type": "text", "label": "Analysis as per", "overridable": True},
            {"key": "trf_no", "kind": "context", "type": "text", "label": "TRF No.", "overridable": True},
            {"key": "ar_no", "kind": "context", "type": "text", "label": "AR No.", "overridable": True},
            #  Per-compound label claims (sheet G39..G42) and Bupivacaine LC
            #  (sheet L18). Constant per compound across batches → overridable
            #  context. Feed both the Lipid %Assay denominator and the
            #  Drug-to-Lipid mg/mL columns.
            {"key": "lc_tri", "kind": "context", "label": "LC — Tricaprylin", "default": _LC_DEFAULTS["tri"], "overridable": True},
            {"key": "lc_dppg", "kind": "context", "label": "LC — DPPG", "default": _LC_DEFAULTS["dppg"], "overridable": True},
            {"key": "lc_chol", "kind": "context", "label": "LC — Cholesterol", "default": _LC_DEFAULTS["chol"], "overridable": True},
            {"key": "lc_depc", "kind": "context", "label": "LC — DEPC", "default": _LC_DEFAULTS["depc"], "overridable": True},
            {"key": "lc_bupi", "kind": "context", "label": "LC — Bupivacaine", "default": 13.3, "overridable": True},
        ],
    ),
    "groups": [
        #  Weighed standard details as a table — one row per compound (sheet
        #  rows 18–21). House rule: >2 standards -> tabular standard details.
        {
            "key": "standard",
            "kind": "table",
            "label": "Standard Details",
            "rows": {"min": 1, "max": 10, "default": len(_COMPOUNDS), "labelFrom": "name"},
            "fields": _standard_fields(),
        },
        #  Six standard replicate injections (sheet rows 25–30, columns B/C/D/E).
        {
            "key": "std_areas",
            "kind": "table",
            "label": "Standard Replicate Injections",
            "rows": {"min": 1, "max": 6, "default": 6},
            "fields": _area_columns(),
            "footer": [
                {"label": "Mean", "ref": "stats.mean_std_tri"},
                {"label": "SD", "ref": "stats.sd_std_tri"},
                {"label": "% RSD", "ref": "stats.rsd_std_tri", "unit": "%"},
            ],
        },
        #  Bracketing standard injections (sheet rows 25–28, columns H/I/J/K);
        #  only four rows carry data, blank rows tolerated by pool().
        {
            "key": "bkt_areas",
            "kind": "table",
            "label": "BKT Standard Injections",
            "rows": {"min": 1, "max": 6, "default": 4},
            "fields": _area_columns(),
            "footer": [
                {"label": "Mean", "ref": "stats.mean_pool_tri"},
                {"label": "SD", "ref": "stats.sd_pool_tri"},
                {"label": "% RSD", "ref": "stats.rsd_pool_tri", "unit": "%"},
            ],
        },
        #  Standard statistics (rows 31–33) + pooled BKT statistics (rows 31–33).
        {
            "key": "stats",
            "kind": "singleton",
            "label": "Standard Statistics",
            "fields": _stats_fields(),
        },
        #  Sample details — one batch per row (sheet rows 39–46, 48–55, 57–64).
        {
            "key": "lipid_samples",
            "kind": "table",
            "label": "Sample Details",
            "rows": {"min": 1, "max": 8, "default": 3},
            "fields": _lipid_sample_fields(),
        },
        #  Drug-to-Lipid section — one batch per row (sheet 2 rows 18–21, ...).
        {
            "key": "drug_lipid",
            "kind": "table",
            "label": "Drug to Lipid Ratio",
            "rows": {"min": 1, "max": 8, "default": 3},
            "fields": _drug_lipid_fields(),
        },
    ],
    "criteria": [
        _rsd_criterion("sst_std_rsd_tri", "%RSD of Tricaprylin standard replicate injections", "stats.rsd_std_tri"),
        _rsd_criterion("sst_std_rsd_dppg", "%RSD of DPPG standard replicate injections", "stats.rsd_std_dppg"),
        _rsd_criterion("sst_std_rsd_chol", "%RSD of Cholesterol standard replicate injections", "stats.rsd_std_chol"),
        _rsd_criterion("sst_std_rsd_depc", "%RSD of DEPC standard replicate injections", "stats.rsd_std_depc"),
        _rsd_criterion("sst_pool_rsd_tri", "%RSD of Tricaprylin pooled bracketing injections", "stats.rsd_pool_tri"),
        _rsd_criterion("sst_pool_rsd_dppg", "%RSD of DPPG pooled bracketing injections", "stats.rsd_pool_dppg"),
        _rsd_criterion("sst_pool_rsd_chol", "%RSD of Cholesterol pooled bracketing injections", "stats.rsd_pool_chol"),
        _rsd_criterion("sst_pool_rsd_depc", "%RSD of DEPC pooled bracketing injections", "stats.rsd_pool_depc"),
    ],
}

BUPI_LIPID_RATIO = SeedTemplate(
    code="TPL-A2-0004",
    name="Bupivacaine Lipid Content & Drug-to-Lipid Ratio",
    archetype="A2",
    result_unit=None,
    test_code="TST-LIPID-RATIO",
    test_name="Lipid Content & Drug-to-Lipid Ratio by HPLC",
    test_type="Quantitative",
    definition=LIPID_RATIO_DEFINITION,
)

TEMPLATES = [BUPI_LIPID_RATIO]
