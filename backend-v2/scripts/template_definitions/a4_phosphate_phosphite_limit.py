"""
A4 — Limit of Phosphate & Phosphite by ion chromatography.

A limit test for two inorganic anions reported against weighed reference
standards. It is the A4 (chromatographic-against-standard) shape, but the
single weighed-standard block is replaced by a **per-element standard table**
("Standard Details for Elements"): one row per element (Phosphate, Phosphite),
each with its own salt form, molecular weights, weight, dilution chain, potency
and resulting concentration. The sample table then back-calculates each analyte
against its own element's standard concentration and its own mean standard area.

## Standard Details for Elements (tabular)

The requested columns, in order:

    Element | Salt Form | M.W. of Base | M.W. of Salt | Std Wt (mg) |
    mL (V.F.) | Pipette1 | mL (V.F.)1 | Pipette2 | mL (V.F.)2 | Potency |
    Conc. (ppm)

`Conc. (ppm)` is calculated with the generalised concentration chain used by
every other HPLC/IC archetype (weight → aliquot ÷ diluted-to per stage → MW
base/salt correction → potency → ×1000 for ppm). Verified against the supplied
gold rows:

    Phosphate  NaH2PO4·H2O  MWb 94.97  MWs 137.99  Wt 349.79
               VF 100 / Pip 10 / VF 50 / Pip 5 / VF 25  Pot 100  -> 96.296 ppm
    Phosphite  Na2HPO3·5H2O MWb 78.97  MWs 216.04  Wt 333.34
               VF 100 / Pip 10 / VF 50 / Pip 5 / VF 25  Pot 99.7 -> 48.593 ppm

Both reproduce exactly (see `_STANDARD_ROWS`). The standard table opens with two
blank element rows; the schema cannot pre-seed distinct per-row values, so the
gold rows live in `_STANDARD_ROWS` as the canonical record.

The dilution-chain column keys map onto the generalised three-stage chain:
`vol_1` = mL (V.F.), `pip_1` = Pipette1, `vol_2` = mL (V.F.)1, `pip_2` =
Pipette2, `vol_3` = mL (V.F.)2.

## Standard & bracketing injections — one area COLUMN per element

The source worksheet records each standard injection as a row with a **Standard
Area column for each element** (Phosphate, Phosphite) rather than a single shared
area. Both the main "Standard Replicate Injections" table and the bracketing
block follow that shape: `area_phosphate` and `area_phosphite` columns, with
Mean / SD / %RSD computed **per element** in the footer and in the statistics
group. Row number is the Sr. No. (the 1-based row index).

Verified against the supplied gold set (6 injections):

    Phosphate  Mean 172376  SD 511.90  %RSD 0.30
    Phosphite  Mean  71886  SD 240.57  %RSD 0.33

Both reproduce exactly.

## Why bracketing standards

The run brackets the sample injections with standard injections and judges
suitability on the *pooled* %RSD (initial replicates + the bracket), not on the
opening replicates alone — a system that drifts over a long sequence would pass
on its first injections and still misreport samples run hours later. The pooled
%RSD is computed per element: `rsd(pool(std_areas.area_<el>, bkt_1.area_<el>))`.
The bracketing block starts empty (0 rows) so a worksheet never shows injections
that were not run.

## Sampling Details & the % Results maths

The sample section is "Sampling Details": one ROW per sample/condition, with the
two elements laid out as COLUMNS across Sample Area and % Results, mirroring the
source sheet:

    Sample Details | Sample Dilution | Sample Area       | % Results
    Batch · Cond · AR · TRF · LC | mL · mL | Phosphate · Phosphite | Phosphate · Phosphite

Each element's % Result is, with the standard looked up by fixed column position
(Phosphate = standard row 0 / `stats.mean_phosphate`; Phosphite = row 1 /
`stats.mean_phosphite`):

    % Result = sample area / element mean standard area
               × element standard concentration (ppm)
               × (dilution mL-2 / mL-1)
               / label claim
               / 10

Reverse-engineered from the gold worksheet and verified to 3 dp on all four
cells (25°C: Phosphate 4824→0.056, Phosphite 39878→0.562; 40°C: 6036→0.070,
45410→0.639). The `/10` is the ppm→% bridge for this make-up basis.

The reportable (`resultRef`) is the worst-case % Result across both element
columns and every sample row. Acceptance is per element against an overridable
context limit (`limit_pct_phosphate` / `limit_pct_phosphite`); the sheet prints
no numeric limit, so those carry no default until a method supplies one.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
)

#  The two elements, in the fixed positional order shared by the standard table,
#  the area columns and the sample table. Index 0 = Phosphate, 1 = Phosphite.
_ELEMENTS = [("phosphate", "Phosphate"), ("phosphite", "Phosphite")]

#  Bracketing blocks start empty and grow as brackets are actually injected.
_BKT_ROWS = {"min": 0, "max": 6, "default": 0}


#  The supplied gold data for the two elements, kept here as the canonical
#  reference the `conc_ppm` expression was verified against. The schema cannot
#  pre-seed distinct per-row values, so the standard table opens blank and the
#  analyst enters these; this records exactly what those entries are. Column keys
#  map to the generalised chain: vol_1 = mL (V.F.), pip_1 = Pipette1,
#  vol_2 = mL (V.F.)1, pip_2 = Pipette2, vol_3 = mL (V.F.)2.
_STANDARD_ROWS = [
    {
        "name": "Phosphate",
        "salt_form": "NaH2PO4 * H2O",
        "mw_base": 94.97,
        "mw_salt": 137.99,
        "weight_mg": 349.79,
        "vol_1": 100,
        "pip_1": 10,
        "vol_2": 50,
        "pip_2": 5,
        "vol_3": 25,
        "potency": 100,
    },
    {
        "name": "Phosphite",
        "salt_form": "Na2HPO3 * 5H2O",
        "mw_base": 78.97,
        "mw_salt": 216.04,
        "weight_mg": 333.34,
        "vol_1": 100,
        "pip_1": 10,
        "vol_2": 50,
        "pip_2": 5,
        "vol_3": 25,
        "potency": 99.7,
    },
]


def _area_columns(label_prefix: str = "") -> list[dict]:
    """
    One Standard Area column per element — the "Standard Area: Phosphate |
    Phosphite" layout. `label_prefix` lets the bracketing blocks read
    "BKT Phosphate" etc. without colliding with the main table's labels.
    """
    #  A leading "Sr. No." text column so the Mean/SD/%RSD footer labels have a
    #  column to sit under and the two element values align under the two area
    #  columns (the renderer puts the footer label under field[0] and the values
    #  under field[1..]). Editable so the analyst can match the sequence log.
    return [
        {"key": "sr_no", "kind": "input", "type": "text", "label": "Sr. No."},
        *[
            {
                "key": f"area_{el_key}",
                "kind": "area",
                "label": f"{label_prefix}{el_label}",
            }
            for el_key, el_label in _ELEMENTS
        ],
    ]


def _standard_element_fields() -> list[dict]:
    """
    Columns of the "Standard Details for Elements" table, in the requested order.
    `conc_ppm` is the only calculated column; everything else is an editable
    input. The per-element mean standard area the sample rows divide by lives in
    the `stats` group (Mean — Phosphate / Phosphite), not in this table.
    """
    return [
        {"key": "name", "kind": "input", "type": "text", "label": "Element"},
        {"key": "salt_form", "kind": "input", "type": "text", "label": "Salt Form"},
        {"key": "mw_base", "kind": "input", "label": "M.W. of Base", "required": True},
        {"key": "mw_salt", "kind": "input", "label": "M.W. of Salt", "required": True},
        {"key": "weight_mg", "kind": "input", "label": "Std Wt", "unit": "mg", "required": True},
        {"key": "vol_1", "kind": "input", "label": "mL (V.F.)", "unit": "mL", "required": True},
        {"key": "pip_1", "kind": "input", "label": "Pipette1", "unit": "mL", "default": 1},
        {"key": "vol_2", "kind": "input", "label": "mL (V.F.)1", "unit": "mL", "default": 1},
        {"key": "pip_2", "kind": "input", "label": "Pipette2", "unit": "mL", "default": 1},
        {"key": "vol_3", "kind": "input", "label": "mL (V.F.)2", "unit": "mL", "default": 1},
        {"key": "potency", "kind": "input", "label": "Potency", "unit": "%", "default": 100},
        {
            "key": "conc_ppm",
            "kind": "calculated",
            "label": "Conc.",
            "unit": "ppm",
            #  Generalised concentration chain, ×1000 for ppm. Reproduces the two
            #  gold rows exactly (96.296 and 48.593).
            "expression": (
                "weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 "
                "* mw_base / mw_salt * potency / 100 * 1000"
            ),
            "rounding": {"mode": "round", "digits": 3},
        },
    ]


def _area_stats_fields(group: str, key_prefix: str = "", label_prefix: str = "") -> list[dict]:
    """
    Per-element Mean / SD / %RSD over one area group's two columns.

    `key_prefix` namespaces the stat field keys (e.g. "bkt_" for the bracketing
    block's own stats, so they don't collide with the replicate stats);
    `label_prefix` prepends to the human labels (e.g. "BKT ").
    """
    fields: list[dict] = []
    for el_key, el_label in _ELEMENTS:
        col = f"{group}.area_{el_key}"
        fields.extend(
            [
                {
                    "key": f"{key_prefix}mean_{el_key}",
                    "kind": "calculated",
                    "label": f"{label_prefix}Mean — {el_label}",
                    "expression": f"mean({col})",
                    "rounding": {"mode": "round", "digits": 0},
                },
                {
                    "key": f"{key_prefix}sd_{el_key}",
                    "kind": "calculated",
                    "label": f"{label_prefix}SD — {el_label}",
                    "expression": f"sd({col})",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": f"{key_prefix}rsd_{el_key}",
                    "kind": "calculated",
                    "label": f"{label_prefix}%RSD — {el_label}",
                    "unit": "%",
                    "expression": f"rsd({col})",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ]
        )
    return fields


def _area_footer(stat_key_prefix: str = "") -> list[dict]:
    """
    Column-aligned Mean / SD / %RSD footer rendered as a grid directly below an
    area table, with Phosphate and Phosphite values lined up under their own area
    columns. Used by both the Standard Replicate Injections and the Bracketing
    Standard tables.

    `stat_key_prefix` selects which `stats.*` fields the footer reads: "" for the
    replicate stats (`stats.mean_phosphate` ...), "bkt_" for the bracketing
    block's own stats (`stats.bkt_mean_phosphate` ...).

    Shape contract (see frontend `groupFooter.ts`): each statistic is ONE row —
    a LABELED leading item (the row label, which the renderer places under the
    table's first column, Sr. No.) followed by one UNLABELED item per element
    column, in the same left-to-right order as the area columns (Phosphate then
    Phosphite). The presence of unlabeled items is what switches the renderer
    from the flat label/value strip to the aligned grid.
    """
    footer: list[dict] = []
    for stat_label, stat_name, unit in (
        ("Mean", "mean", None),
        ("SD", "sd", None),
        ("% RSD", "rsd", "%"),
    ):
        for position, (el_key, _el_label) in enumerate(_ELEMENTS):
            item: dict = {"ref": f"stats.{stat_key_prefix}{stat_name}_{el_key}"}
            #  The first element's item carries the row label; the rest are
            #  unlabeled so they render as aligned value cells.
            if position == 0:
                item["label"] = stat_label
            if unit:
                item["unit"] = unit
            footer.append(item)
    return footer


#  Standard statistics: per-element Mean/SD/%RSD over the opening replicates, plus
#  a per-element %RSD pooled with both bracketing blocks for drift control.
_PP_STATS_GROUP = {
    "key": "stats",
    "kind": "singleton",
    "label": "Standard Statistics",
    "fields": [
        #  Replicate-injection Mean/SD/%RSD (keys: mean_<el>, sd_<el>, rsd_<el>).
        *_area_stats_fields("std_areas"),
        #  POOLED Mean/SD/%RSD over the replicate injections AND the bracketing
        #  block together — this is what the worksheet's bracketing summary
        #  reports (a bracket judged on its own would let a drifting system pass
        #  suitability). Keys: bkt_mean_<el>, bkt_sd_<el>, bkt_rsd_<el> — these are
        #  the refs the Bracketing Standard footer reads.
        *[
            field
            for el_key, el_label in _ELEMENTS
            for field in (
                {
                    "key": f"bkt_mean_{el_key}",
                    "kind": "calculated",
                    "label": f"Pooled Mean — {el_label}",
                    "expression": (
                        f"mean(pool(std_areas.area_{el_key}, bkt_1.area_{el_key}))"
                    ),
                    "rounding": {"mode": "round", "digits": 0},
                },
                {
                    "key": f"bkt_sd_{el_key}",
                    "kind": "calculated",
                    "label": f"Pooled SD — {el_label}",
                    "expression": (
                        f"sd(pool(std_areas.area_{el_key}, bkt_1.area_{el_key}))"
                    ),
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": f"bkt_rsd_{el_key}",
                    "kind": "calculated",
                    "label": f"Pooled %RSD — {el_label}",
                    "unit": "%",
                    "expression": (
                        f"rsd(pool(std_areas.area_{el_key}, bkt_1.area_{el_key}))"
                    ),
                    "rounding": {"mode": "round", "digits": 2},
                },
            )
        ],
    ],
}


def _pct_result_expression(el_key: str, position: int) -> str:
    """
    % Result for one element on a sample row (elements are COLUMNS here).

    Reverse-engineered from the gold worksheet and verified to 3 dp on all four
    cells:

        % Result = sample area / element mean STD area
                   × element standard concentration (ppm)
                   × (dilution mL-2 / mL-1)      [the sample make-up chain]
                   / label claim
                   / 10                          [ppm→% bridge for this basis]

    The element's standard concentration and mean area are fixed-position scalars
    because each element is a column: Phosphate is standard row 0 /
    `stats.mean_phosphate`, Phosphite is row 1 / `stats.mean_phosphite`.

    Worked check (25°C row): Phosphate 4824/172376×96.296×(20/4)/24/10 = 0.056;
    Phosphite 39878/71886×48.593×(20/4)/24/10 = 0.562.
    """
    mean_ref = f"stats.mean_{el_key}"
    conc_ref = f"standards.conc_ppm[{position}]"
    return (
        f"area_{el_key} / {mean_ref} * {conc_ref} "
        "* dil_ml_2 / dil_ml_1 / label_claim / 10"
    )


def _sampling_fields() -> list[dict]:
    """
    One row per sample/condition. Elements (Phosphate, Phosphite) are COLUMNS
    across Sample Area and % Results — mirrors the requested sheet layout:

        Sample Details | Sample Dilution | Sample Area | % Results
        Condition · Label Claim | mL · mL | Phosphate · Phosphite |
        Phosphate · Phosphite

    Batch No. / AR.No. / TRF No. are NOT columns here: they are auto-fetched from
    the bound TRF and rendered in the group's headerContext strip above the rows.
    """
    fields: list[dict] = [
        #  Sample Details. Batch No. / AR.No. / TRF No. are auto-fetched from the
        #  bound TRF and shown in the group's headerContext strip (one TRF per
        #  worksheet), so only the per-row Condition and Label Claim are columns.
        {"key": "condition", "kind": "input", "type": "text", "label": "Condition"},
        {
            "key": "label_claim",
            "kind": "input",
            "label": "Label Claim",
            "required": True,
        },
        #  Sample Dilution (two make-up volumes: aliquot mL -> made up to mL).
        {"key": "dil_ml_1", "kind": "input", "label": "mL", "unit": "mL", "required": True},
        {"key": "dil_ml_2", "kind": "input", "label": "mL", "unit": "mL", "required": True},
        #  Sample Area — one column per element.
        {"key": "area_phosphate", "kind": "area", "label": "Phosphate"},
        {"key": "area_phosphite", "kind": "area", "label": "Phosphite"},
    ]
    #  % Results — one calculated column per element.
    for position, (el_key, el_label) in enumerate(_ELEMENTS):
        fields.append(
            {
                "key": f"pct_{el_key}",
                "kind": "calculated",
                "label": el_label,
                "unit": "%",
                "expression": _pct_result_expression(el_key, position),
                "rounding": {"mode": "round", "digits": 3},
            }
        )
    return fields


A4_PP_DEFINITION = {
    #  Reportable: the worst-case % Result across both elements and all samples.
    "resultRef": "summary.max_pct_result",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {
                "key": "test_name_hdr",
                "kind": "context",
                "type": "text",
                "label": "Test",
                "default": "Limit of Phosphate & Phosphite",
                "overridable": True,
            },
            {
                "key": "analysis_as_per",
                "kind": "context",
                "type": "text",
                "label": "Analysis as per",
                "overridable": True,
            },
            #  Auto-fetched from the bound TRF, shown as a read-only header strip
            #  above the Sampling Details rows. One TRF per worksheet, so these are
            #  worksheet-level context rather than per-row columns; overridable for
            #  manual correction. (Batch No. already comes from `context_header`,
            #  sourced from `trf.batch_number`, so it is not repeated here.)
            {
                "key": "ar_no",
                "kind": "context",
                "type": "text",
                "label": "AR.No.",
                "source": "trf.ar_number",
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
            #  Per-element % Result acceptance limits (NMT). Overridable context so
            #  a method can set its own spec without a new template. The sheet
            #  prints no numeric limit, so these carry no default until supplied.
            {
                "key": "limit_pct_phosphate",
                "kind": "context",
                "label": "Limit — Phosphate",
                "unit": "%",
                "overridable": True,
            },
            {
                "key": "limit_pct_phosphite",
                "kind": "context",
                "label": "Limit — Phosphite",
                "unit": "%",
                "overridable": True,
            },
        ],
    ),
    "groups": [
        #  Per-element standard preparation table.
        {
            "key": "standards",
            "kind": "table",
            "label": "Standard Details for Elements",
            "rows": {"min": 1, "max": 6, "default": 2, "labelFrom": "name"},
            "fields": _standard_element_fields(),
        },
        #  Standard replicate injections — one Standard Area column per element,
        #  Sr. No. is the row index, six injections by default. Per-element footer.
        {
            "key": "std_areas",
            "kind": "table",
            "label": "Standard Replicate Injections",
            "rows": {"min": 1, "max": 10, "default": 6},
            "fields": _area_columns(),
            "footer": _area_footer(),
        },
        #  Bracketing-standard block, same two columns, starting empty.
        {
            "key": "bkt_1",
            "kind": "table",
            "label": "Bracketing Standard",
            "rows": _BKT_ROWS,
            "fields": _area_columns("BKT "),
            #  Same aligned Mean/SD/%RSD grid as the replicate table, over this
            #  block's own injections (stats keys prefixed `bkt_`).
            "footer": _area_footer("bkt_"),
        },
        _PP_STATS_GROUP,
        {
            "key": "sampling",
            "kind": "table",
            "label": "Sampling Details",
            #  One row per sample/condition; elements are columns. Row label is the
            #  condition so multiple conditions of one batch read clearly.
            "rows": {"min": 1, "max": 24, "default": 2, "labelFrom": "condition"},
            #  Batch No. / AR.No. / TRF No. auto-fetched from the TRF, shown as a
            #  read-only strip above the rows.
            "headerContext": [
                {"label": "Batch No.", "ref": "batch_no"},
                {"label": "AR.No.", "ref": "ar_no"},
                {"label": "TRF No.", "ref": "trf_no"},
            ],
            "fields": _sampling_fields(),
        },
        {
            "key": "summary",
            "kind": "singleton",
            "label": "Summary",
            "fields": [
                {
                    "key": "max_pct_result",
                    "kind": "calculated",
                    "label": "Maximum % Result",
                    "unit": "%",
                    #  Worst case across both element columns and every sample row.
                    #  Guarded so an untouched worksheet does not report 0.000 %.
                    "expression": (
                        "if(isblank(mean(pool(sampling.pct_phosphate, "
                        "sampling.pct_phosphite))), blank(), "
                        "max(pool(sampling.pct_phosphate, sampling.pct_phosphite)))"
                    ),
                    "rounding": {"mode": "round", "digits": 3},
                },
            ],
        },
    ],
    "criteria": [
        #  Per-element replicate %RSD.
        {
            "key": "sst_rsd_phosphate",
            "label": "%RSD of standard replicate injections — Phosphate",
            "target": "stats.rsd_phosphate",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        {
            "key": "sst_rsd_phosphite",
            "label": "%RSD of standard replicate injections — Phosphite",
            "target": "stats.rsd_phosphite",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        #  Per-element pooled bracketing %RSD.
        {
            "key": "sst_bkt_rsd_phosphate",
            "label": "%RSD of pooled bracketing standards — Phosphate",
            "target": "stats.bkt_rsd_phosphate",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        {
            "key": "sst_bkt_rsd_phosphite",
            "label": "%RSD of pooled bracketing standards — Phosphite",
            "target": "stats.bkt_rsd_phosphite",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        #  Each element's worst-case % Result against its own limit. The target is
        #  the max % Result MINUS the limit; `lte 0` passes when every sample is
        #  at or under the limit. Using the difference keeps the limit an editable
        #  context value rather than a hard-coded number in the criterion.
        {
            "key": "within_limit_phosphate",
            "label": "Phosphate within specification limit",
            "target": "max(sampling.pct_phosphate) - limit_pct_phosphate",
            "operator": "lte",
            "limit": 0.0,
            "severity": "blocking",
            "limitText": "NMT the Phosphate limit",
        },
        {
            "key": "within_limit_phosphite",
            "label": "Phosphite within specification limit",
            "target": "max(sampling.pct_phosphite) - limit_pct_phosphite",
            "operator": "lte",
            "limit": 0.0,
            "severity": "blocking",
            "limitText": "NMT the Phosphite limit",
        },
    ],
}

A4_PHOSPHATE_PHOSPHITE = SeedTemplate(
    code="TPL-A4-0002",
    name="Limit of Phosphate & Phosphite",
    archetype="A4",
    result_unit="%",
    test_code="TST-LIM-PP",
    test_name="Limit of Phosphate & Phosphite",
    test_type="Quantitative",
    definition=A4_PP_DEFINITION,
)

TEMPLATES = [A4_PHOSPHATE_PHOSPHITE]
