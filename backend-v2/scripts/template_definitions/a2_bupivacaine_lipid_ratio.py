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
matching SET's Lipid `% Mean`. The `lipid_samples` group is now TALL (SET blocks
of 4 compound rows), each carrying a per-row `pct_mean` (= that compound's %Mean;
single injection so it equals `pct_assay`, both unrounded). Each `drug_lipid` row
n (SET n) reads its four compounds via `lipid_samples.pct_mean[(rowno-1)*4 + idx]`
(tri 0, dppg 1, chol 2, depc 3) — a whole-column series indexed by the row's SET
position. Chosen over recomputing mg/mL inside `lipid_samples` because it keeps
the reference legible and mirrors the sheet's cross-sheet `='Lipid '!O43`.

Injection-block orientation (decisions D1–D8): the Standard Replicate Injections
(`std_areas`) and BKT Standard Injections (`bkt_areas`) are laid out as
INJECTIONS-AS-ROWS / COMPOUNDS-AS-COLUMNS — one row per injection (Injection
1..N, expandable, cap 12) and one AREA column per compound (`tri_area`,
`dppg_area`, `chol_area`, `depc_area`, in _COMPOUNDS order), each column header
auto-fetching the compound name from Standard Details via
`labelFrom="standard.name[<idx>]"`. Per-compound Mean/SD/%RSD aggregate DOWN each
compound column (`mean(std_areas.<c>_area)` etc., blanks skipped) and are
published by the `stats` singleton and rendered in each group's footer (one ref
per compound column). BKT Mean/SD/%RSD are POOLED per compound column with the
matching `std_areas` column (`pool(std_areas.<c>_area, bkt_areas.<c>_area)`),
matching the sheet's `AVERAGE(H25:H30,B25:B30)` / `STDEV(B25:B30,H25:H30)`.
Because the aggregates live in `stats`/footer and NOT in data rows, each column
series holds only injection values, so the whole-column aggregate is exactly the
intended span and adapts to the expandable row count. The `stats.*` KEYS are
UNCHANGED, so the `lipid_samples` %Assay chain and the 8 SST criteria are
untouched — only each stat's SOURCE expression moved to a per-column aggregate.

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


#  Injection rows are EXPANDABLE: the sheet records up to six replicate
#  injections (rows 25–30) and up to six bracketing injections, but the user may
#  add more. Cap the row count at 12; blank injection cells are tolerated by
#  mean/sd/rsd (they skip blanks), so a higher cap never perturbs the aggregates.
_MAX_INJ_ROWS = 12
_DEFAULT_INJ_ROWS = 6


def _area_columns() -> list[dict]:
    """
    One AREA column per compound (tri, dppg, chol, depc — in _COMPOUNDS order),
    shared by the transposed replicate and BKT tables. Each column HEADER
    auto-fetches the compound name from Standard Details (row idx) via the
    generic `labelFrom="standard.name[<idx>]"` resolver, so renaming a standard
    renames the column.
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
    per compound (sheet rows 25–30, cols B/C/D/E transposed).

    Orientation (decision D1/D2): injections-as-rows, compounds-as-columns. The
    row label is a plain `inj_label` text input ("Injection 1" ..); the four
    area columns are `tri_area/dppg_area/chol_area/depc_area` with `labelFrom`
    headers. No per-row Mean/SD/%RSD — those aggregate DOWN each compound column
    and are published by the `stats` singleton (and rendered in the group
    footer), so the column series `std_areas.<c>_area` contains ONLY injection
    rows and `mean(std_areas.<c>_area)` is the exact per-compound mean.
    """
    return [
        {"key": "inj_label", "kind": "input", "type": "text", "label": "Injection"},
        *_area_columns(),
    ]


def _bkt_area_fields() -> list[dict]:
    """
    BKT (bracketing) standard injections as a TABLE — one ROW per injection, one
    COLUMN per compound (sheet rows 25–28, cols H/I/J/K transposed).

    Same shape as `std_areas` (inj_label + four area columns). Pooling with the
    matching `std_areas` compound column now lives in the `stats` singleton
    (`pool(std_areas.<c>_area, bkt_areas.<c>_area)`), matching the sheet's
    `AVERAGE(H25:H30,B25:B30)` / `STDEV(B25:B30,H25:H30)`, so `bkt_areas` carries
    no calculated fields.
    """
    return [
        {"key": "inj_label", "kind": "input", "type": "text", "label": "Injection"},
        *_area_columns(),
    ]


def _stats_fields() -> list[dict]:
    """
    Per-compound statistics singleton. Each stat now aggregates DOWN a compound
    COLUMN of the transposed injection tables (decision D5/D6):
        mean_std_<c>  = mean(std_areas.<c>_area)
        mean_pool_<c> = mean(pool(std_areas.<c>_area, bkt_areas.<c>_area))
        (and sd/rsd likewise)
    The whole-column series spans every injection row and skips blanks, so the
    aggregate adapts to the expandable row count for free. The `stats.*` KEYS,
    labels and units are UNCHANGED (decision D7) — only each expression's SOURCE
    moved from a per-row table cell to a per-column aggregate — so the
    `lipid_samples` %Assay chain and the 8 SST criteria need no change.
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


#  Hidden per-row compound index: cidx = (rowno-1) mod 4, so 0=tri, 1=dppg,
#  2=chol, 3=depc down every SET block of four rows. The engine has no `mod` but
#  exposes `trunc`, so modulo-4 is spelled out with trunc (decision D1). Proved
#  to yield 0/1/2/3 across rows 1..8 before this was written.
_CIDX_EXPRESSION = "rowno - 1 - trunc((rowno - 1) / 4, 0) * 4"


def _compound_select(per_compound) -> str:
    """
    Build a `coalesce(if(cidx == k, <expr for compound k>, blank()), ...)` over
    the four compounds (k = 0..3). `if()` is lazy in this engine, so the three
    non-selected branches never evaluate and cannot poison the result; `coalesce`
    returns the single non-blank branch. `per_compound(k, prefix)` returns the
    sub-expression for compound k. This one builder drives the Compound Name, LC
    and %Assay selections so they stay in lock-step with `cidx`.
    """
    branches = []
    for k, (prefix, _name) in enumerate(_COMPOUNDS):
        branches.append(f"if(cidx == {k}, {per_compound(k, prefix)}, blank())")
    return "coalesce(" + ", ".join(branches) + ")"


def _lipid_sample_fields() -> list[dict]:
    """
    TALL per-SET layout — each SET is a block of exactly 4 compound ROWS
    (Tricaprylin, DPPG Na, Cholesterol, DEPC, in _COMPOUNDS order); FIXED at 2
    SETs = 8 rows (the group `rows` is pinned {min:8, max:8, default:8}).

    There is NO in-table SET column. The SET is rendered by the frontend as a
    "Set N" HEADING above each 4-row block (block boundaries detected from the
    hidden `cidx` resetting to 0); the backend carries no per-row SET value
    because it feeds no formula. A row's compound is chosen by its position
    within its SET via the hidden `cidx = (rowno-1) mod 4` (decision D1).
    Columns, in order: Compound Name, LC, Avg Weight, Sample Weight, Vol (vol_j),
    Pip (pip_k), Vol (vol_l), Area, % Assay, % Mean.

    * `cidx` — hidden calculated compound index 0..3 (decision D1). Doubles as
      the frontend's block-boundary signal (a new "Set N" block starts when it
      resets to 0); never rendered as a column.
    * `compound_name` — read-only, selects `standard.name[cidx]` so it tracks the
      Standard Details names (decision D4).
    * `lc` — read-only, mirrors the matching `lc_<c>` context field (decision D5).
    * `avg_weight / sample_weight / vol_j / pip_k / vol_l` — per-row inputs
      (decision D2). The %Assay formula reads these UNQUALIFIED from the current
      row, and this engine's `mirrorFrom` is a frontend-only display hint that
      never copies a value, so each of a SET's 4 rows must physically carry the
      shared prep values. Defaults match the old wide layout (avg_weight 1.005,
      vol_j 25, pip_k 1, vol_l 1); sample_weight is entered per SET.
    * `area` — ONE area column per row (single injection; the wide layout's 2nd
      injection is dropped).
    * `pct_assay` — ONE calculated %Assay per row, the SAME algebra as
      `_assay_expression(prefix, "area")` but bound to THIS row's compound via
      `_compound_select`. NO mid-chain rounding (decision D6): `drug_lipid` reads
      the unrounded value; the 2-dp sheet gold figures are display rounding.
    * `pct_mean` — ONE calculated %Mean per row (sheet O column). Single injection,
      so %Mean = `mean([pct_assay])` = that row's %Assay; kept as a blank-skipping
      mean so a future 2nd-injection %Assay would average correctly. NO rounding;
      `drug_lipid` reads this (equals `pct_assay`, so the gold ratio is exact).
    """
    fields: list[dict] = [
        #  Hidden compound index 0..3 within the SET (decision D1). With the SET
        #  column removed, this is also the frontend's block-boundary signal: a
        #  new "Set N" heading starts wherever cidx resets to 0 (rows 1-4 = Set 1,
        #  5-8 = Set 2). Always hidden; never a rendered column.
        {
            "key": "cidx",
            "kind": "calculated",
            "label": "Compound Index",
            "hidden": True,
            "expression": _CIDX_EXPRESSION,
        },
        #  Compound Name — read-only, fetched from Standard Details by cidx so it
        #  renames when a standard is renamed (decision D4). `labelFrom` is a
        #  frontend header hint; the per-row value itself comes from the selector.
        {
            "key": "compound_name",
            "kind": "calculated",
            "type": "text",
            "label": "Compound Name",
            #  Header is the static "Compound Name": this column holds a DIFFERENT
            #  compound on every row (tri/dppg/chol/depc down the SET block), so a
            #  per-compound `labelFrom` header would be wrong. The per-row VALUE
            #  still comes from the selector below.
            "expression": _compound_select(lambda k, _p: f"standard.name[{k}]"),
        },
        #  LC — read-only mirror of the matching lc_<c> context field (decision
        #  D5). Display-only; the %Assay denominator reads lc_<c> directly.
        {
            "key": "lc",
            "kind": "calculated",
            "label": "LC",
            "expression": _compound_select(lambda _k, p: f"lc_{p}"),
        },
        #  Shared SET prep — per-row inputs (decision D2); mirrorFrom is a UI hint.
        {"key": "avg_weight", "kind": "input", "label": "Avg Weight", "default": 1.005},   # H
        {"key": "sample_weight", "kind": "input", "label": "Sample Weight", "unit": "mg"},  # I
        {"key": "vol_j", "kind": "input", "label": "Vol", "unit": "mL", "default": 25},      # J
        {"key": "pip_k", "kind": "input", "label": "Pip", "unit": "mL", "default": 1},       # K
        {"key": "vol_l", "kind": "input", "label": "Vol", "unit": "mL", "default": 1},        # L
        #  ONE Area column per row — single injection (decision D6). Static "Area"
        #  header (the column spans all four compounds down the SET block, so no
        #  per-compound labelFrom).
        {"key": "area", "kind": "area", "label": "Area"},
        #  ONE % Assay per row, bound to this row's compound via cidx (decision
        #  D1/D6). Same algebra as the old _assay_expression; NO rounding.
        {
            "key": "pct_assay",
            "kind": "calculated",
            "label": "% Assay",
            "unit": "%",
            "expression": _compound_select(lambda _k, p: _assay_expression(p, "area")),
        },
        #  % Mean per compound row (sheet O column). This tall layout has a SINGLE
        #  injection per row, so the mean of the one % Assay value is that value
        #  itself. Expressed as `mean([pct_assay])` to keep blank-skipping mean
        #  semantics — if a 2nd injection %Assay is ever added to the list later,
        #  the average still works. NO rounding (decision D6): drug_lipid reads
        #  the unrounded value.
        {
            "key": "pct_mean",
            "kind": "calculated",
            "label": "% Mean",
            "unit": "%",
            "expression": "mean([pct_assay])",
        },
    ]
    return fields


def _mean_each_compound_fields() -> list[dict]:
    """
    "% Mean each compound" — a read-only cross-set summary (ADDITIVE; added for
    the user's "% Mean of each compound = Average of set1 and set2" request).

    Shape: a TABLE FIXED at exactly 4 rows (pinned min==max==default==4), ONE row
    per compound in _COMPOUNDS order (row 0 Tricaprylin, 1 DPPG Na, 2 Cholesterol,
    3 DEPC). The row's compound index is simply `rowno - 1` (0..3) — there are
    exactly four rows, one per compound, so no `cidx`-style modulo is needed.
    Columns, in order: Compound Name and the cross-set "% Mean".

    * `compound_name` — read-only, auto-fetched from Standard Details by the row's
      compound index: `standard.name[(rowno - 1)]`. Same mechanism the TALL
      `lipid_samples.compound_name` uses (there via the hidden `cidx`; here the
      index is the row position), so renaming a standard renames this too.
    * `pct_mean` — the classic "mean across replicate sets": for compound at index
      idx = rowno-1, the mean of that compound's % Assay in Set 1 (lipid_samples
      row idx) and Set 2 (lipid_samples row idx+4), blank-skipping:
      `mean([ lipid_samples.pct_assay[(rowno-1)], lipid_samples.pct_assay[(rowno-1)+4] ])`.
      This references a DIFFERENT group (`lipid_samples`) by absolute column
      index — the SAME cross-group absolute-index pattern `drug_lipid` already
      uses (`lipid_samples.pct_mean[(rowno-1)*4 + idx]`), and the dependency graph
      resolves it to the single path ('lipid_samples','pct_assay') (indexing is
      truncated in `referenced_paths`), so the new field depends only on
      `lipid_samples.pct_assay` with NO circular dependency. `mean([...])` skips
      blanks, so when Set 2 is empty the mean of the one Set-1 value equals that
      compound's Set-1 % Assay. NO rounding — this is a read-only display summary
      that feeds no downstream formula (drug_lipid still reads lipid_samples
      directly), so the drug/lipid ratio and per-set pct_mean are untouched.
    """
    return [
        {
            "key": "compound_name",
            "kind": "calculated",
            "type": "text",
            "label": "Compound Name",
            "expression": "standard.name[(rowno - 1)]",
        },
        {
            "key": "pct_mean",
            "kind": "calculated",
            "label": "% Mean",
            "unit": "%",
            "expression": (
                "mean([ lipid_samples.pct_assay[(rowno - 1)], "
                "lipid_samples.pct_assay[(rowno - 1) + 4] ])"
            ),
        },
    ]


def _drug_lipid_fields() -> list[dict]:
    """
    One batch per row (same order as `lipid_samples`): the four mg/mL(Lipid)
    columns, their sum, the Bupivacaine mg/mL and the Drug/Lipid ratio.
    """
    fields: list[dict] = [
        {"key": "batch_no", "kind": "input", "type": "text", "label": "Batch No."},
    ]
    #  I18 = H18 * G18 / 100 = (Lipid % Mean for this SET) * compound LC / 100.
    #  The tall lipid_samples carries a per-row `pct_mean` (= that compound's
    #  % Mean; single injection so it equals `pct_assay`, both unrounded). This
    #  mirrors the sheet's cross-sheet `='Lipid '!O43` (the %Mean column). drug_lipid
    #  row n (SET n) reads its four compounds at lipid_samples rows (n-1)*4 + idx,
    #  where idx is tri 0 / dppg 1 / chol 2 / depc 3 (the _COMPOUNDS position).
    #  Because `pct_mean == pct_assay` (both unrounded), the gold ratio 0.841429 is
    #  reproduced exactly; reading the semantically-correct %Mean matches the sheet.
    for idx, (prefix, name) in enumerate(_COMPOUNDS):
        fields.append(
            {
                "key": f"{prefix}_mgml",
                "kind": "calculated",
                "label": f"{name} mg/mL (Lipid)",
                "unit": "mg/mL",
                "labelFrom": f"standard.name[{idx}]",
                "expression": (
                    f"lipid_samples.pct_mean[(rowno - 1) * 4 + {idx}] "
                    f"* lc_{prefix} / 100"
                ),
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
        #  Standard replicate injections, transposed to one ROW per injection /
        #  one COLUMN per compound (sheet rows 25–30, cols B/C/D/E). Rows are
        #  EXPANDABLE (Injection 1..N, cap 12); the four area columns are
        #  tri/dppg/chol/depc with labelFrom headers. Per-compound Mean/SD/%RSD
        #  aggregate DOWN each column and are rendered in the footer (one ref per
        #  compound column) from the `stats` singleton — footers are frontend-only
        #  pass-throughs and never feed the calculation, so the column series
        #  stays clean (decision D4).
        {
            "key": "std_areas",
            "kind": "table",
            "label": "Standard Replicate Injections",
            "rows": {"min": 1, "max": _MAX_INJ_ROWS, "default": _DEFAULT_INJ_ROWS, "labelFrom": "inj_label"},
            "fields": _std_area_fields(),
            "footer": [
                {"label": "Mean", "ref": "stats.mean_std_tri"},
                {"ref": "stats.mean_std_dppg"},
                {"ref": "stats.mean_std_chol"},
                {"ref": "stats.mean_std_depc"},
                {"label": "SD", "ref": "stats.sd_std_tri"},
                {"ref": "stats.sd_std_dppg"},
                {"ref": "stats.sd_std_chol"},
                {"ref": "stats.sd_std_depc"},
                {"label": "% RSD", "ref": "stats.rsd_std_tri", "unit": "%"},
                {"ref": "stats.rsd_std_dppg", "unit": "%"},
                {"ref": "stats.rsd_std_chol", "unit": "%"},
                {"ref": "stats.rsd_std_depc", "unit": "%"},
            ],
        },
        #  Bracketing standard injections, transposed to one ROW per injection /
        #  one COLUMN per compound (sheet rows 25–28, cols H/I/J/K). Same shape as
        #  std_areas; the footer Mean/SD/%RSD are POOLED per compound column with
        #  the matching std_areas column (stats.*_pool_*), matching the sheet's
        #  AVERAGE(H25:H30,B25:B30) / STDEV(B25:B30,H25:H30). Blank rows tolerated.
        {
            "key": "bkt_areas",
            "kind": "table",
            "label": "BKT Standard Injections",
            "rows": {"min": 1, "max": _MAX_INJ_ROWS, "default": _DEFAULT_INJ_ROWS, "labelFrom": "inj_label"},
            "fields": _bkt_area_fields(),
            "footer": [
                {"label": "Mean", "ref": "stats.mean_pool_tri"},
                {"ref": "stats.mean_pool_dppg"},
                {"ref": "stats.mean_pool_chol"},
                {"ref": "stats.mean_pool_depc"},
                {"label": "SD", "ref": "stats.sd_pool_tri"},
                {"ref": "stats.sd_pool_dppg"},
                {"ref": "stats.sd_pool_chol"},
                {"ref": "stats.sd_pool_depc"},
                {"label": "% RSD", "ref": "stats.rsd_pool_tri", "unit": "%"},
                {"ref": "stats.rsd_pool_dppg", "unit": "%"},
                {"ref": "stats.rsd_pool_chol", "unit": "%"},
                {"ref": "stats.rsd_pool_depc", "unit": "%"},
            ],
        },
        #  Standard statistics (rows 31–33) + pooled BKT statistics (rows 31–33).
        {
            "key": "stats",
            "kind": "singleton",
            "label": "Standard Statistics",
            "fields": _stats_fields(),
        },
        #  Sample details — TALL, FIXED 2 SET blocks of 4 compound rows (8 rows,
        #  pinned min==max==8). Each SET is Tricaprylin/DPPG Na/Cholesterol/DEPC
        #  (in _COMPOUNDS order), the compound chosen per row by the hidden
        #  cidx = (rowno-1) mod 4. There is NO in-table SET column: the frontend
        #  renders a "Set N" heading above each 4-row block (block boundary = cidx
        #  resetting to 0). Pinning min==max hides the Add/Remove Row controls.
        {
            "key": "lipid_samples",
            "kind": "table",
            "label": "Sample Details",
            "rows": {"min": 8, "max": 8, "default": 8},
            "fields": _lipid_sample_fields(),
        },
        #  "% Mean each compound" — ADDITIVE read-only cross-set summary rendered
        #  DIRECTLY BELOW the Sample Details (Set 2) block (placed immediately
        #  after lipid_samples so the generic frontend renders it as a labeled
        #  4-row table beneath Set 2). One row per compound; each row shows the
        #  compound name (from Standard Details), a static "Average of set1 and
        #  set2" label, and the cross-set % Mean = mean(Set1 %Assay, Set2 %Assay).
        #  Read-only: it feeds NO downstream formula, so the per-set lipid_samples
        #  pct_mean and the drug/lipid ratio are unchanged.
        {
            "key": "mean_each_compound",
            "kind": "table",
            "label": "% Mean each compound",
            "rows": {"min": 4, "max": 4, "default": 4},
            "fields": _mean_each_compound_fields(),
        },
        #  Drug-to-Lipid section — one ROW per SET (same SET order as the tall
        #  lipid_samples), FIXED at 2 rows (pinned min==max==2) to match the 2
        #  fixed SETs. Each mg/mL column reads the per-SET, per-compound % Mean
        #  from lipid_samples by indexing (rowno-1)*4 + compound idx (rows 1-4 =
        #  SET 1, 5-8 = SET 2).
        {
            "key": "drug_lipid",
            "kind": "table",
            "label": "Drug to Lipid Ratio",
            "rows": {"min": 2, "max": 2, "default": 2},
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
