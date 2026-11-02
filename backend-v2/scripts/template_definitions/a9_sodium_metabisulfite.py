"""
A9 — Content of Sodium Metabisulfite by Titrimetry (iodometric back-titration).

Transcribed from `Calculation of Sodium Metabisulfite by Titrimetry.xlsx`
(product: Amikacin Sulfate Injection USP 250 mg/mL, an injectable in which
sodium metabisulfite is the antioxidant). The sheet titles itself
"Content by Titrimetry Calculation Sheet" and reports
"Content of Sodium Metabisulfite" as a % of its label claim.

## What the sheet does

Each determination is a direct back-titration readout — no chromatography, so
this is the A9 (titration) archetype with no standard block or area fields.

Mapping the sheet columns (row 14 headers, data from row 15) onto fields:

* **ml of Sample**            (col F) -> `sample_ml`
* **ml of Titrant**           (col G) -> `titre_ml`
* **Normality**               (col I) -> `normality`  (per-row input; sheet $D$10 = 0.1019 N)
* **L.C. Of Sodium metabisulfite** (col H) -> `label_claim` (per-row, from context)
* **Factor**                  (col J) -> `equivalence_factor` (sheet $G$10 = 47.5)
* **mg/ml**                   (col K) -> `mg_per_ml`
* **% Result**                (col L) -> `pct_lc`
* **% Mean**                  (col M) -> `result.mean_pct_lc` (singleton + footer)

The sheet formulas, verbatim:

    K (mg/ml)   = (G*I*J*1000) / (F*1000)
                = (titre_ml * normality * factor * 1000) / (sample_ml * 1000)
    L (%)       = K / H * 100
                = mg_per_ml / label_claim * 100
    M (% mean)  = AVERAGE(L block)

The paired `*1000 / *1000` cancel; they are kept in the expression so a reviewer
comparing against the sheet sees the same algebra. Verified against the sheet's
own gold numbers (Initial_Set-1): F=10, G=11.9, I=0.1019, J=47.5, H=6.6 ->
K = 5.7598975, L = 87.2712 %; second row G=11.8 -> L = 86.5378 %; set mean
M = 86.9045 %. Reproduced exactly.

## Titrant, normality, factor

The titrant on this sheet is **K2Cr2O7** (potassium dichromate) standardised to
**0.1019 N**, with an **equivalence factor of 47.5 mg per mL of 1 N** titrant
(the milliequivalent weight of sodium metabisulfite, Na2S2O5 MW 190.1,
delivering 2 electrons per SO2 pair -> 190.1/4 ~= 47.5).

**Normality is a per-row input column** (sheet col I carried $D$10 on every row),
placed immediately after "ml of Titrant", defaulting to 0.1019 N so it auto-fills
but can be edited per determination when a titrant lot differs. The titrant name
and the equivalence factor remain overridable header context fields with the
sheet values as defaults, so a different salt factor is a one-field edit.

## Blank titre

Unlike the generic A9 template this sheet carries **no reagent-blank column**, so
a `blank_ml` default of 0 keeps the net titre equal to the titre. It remains
overridable for methods that do run a blank, so the one template serves both.

## Rounding

mg/mL to 4 dp and the percentages to 2 dp, matching the generic A9 titration
template and ordinary assay reporting. The sheet itself stores full precision and
formats on display; rounding the reported % to 2 dp is the lab convention.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
)

A9_SMBS_DEFINITION = {
    "resultRef": "result.mean_pct_lc",
    "context": context_header(
        avg_weight=False,
        extra=[
            {
                "key": "test_name_hdr",
                "kind": "context",
                "type": "text",
                "label": "Test",
                #  Sheet A7/B7 — the test title printed on the worksheet.
                "default": "Content of Sodium Metabisulfite",
                "overridable": True,
            },
            {
                "key": "analysis_as_per",
                "kind": "context",
                "type": "text",
                "label": "Analysis as per",
                #  Sheet A8/B8 — the test method / SOP the analysis follows.
                "default": "QC-DP-MOA-006-05 (For US Market)",
                "overridable": True,
            },
            {
                "key": "lnb_no",
                "kind": "context",
                "type": "text",
                "label": "LNB No.",
                #  Sheet I9 — the lab notebook reference for this worksheet; a
                #  per-worksheet free-text entry with no default.
                "overridable": True,
            },
            {
                "key": "packing_detail_hdr",
                "kind": "context",
                "type": "text",
                "label": "Packing Detail",
                #  Sheet "Packing Detail" cell ("Glass Vial") — auto-fetched from
                #  the bound TRF, overridable for manual entry.
                "source": "trf.pack_details",
                "overridable": True,
            },
            {
                "key": "titrant",
                "kind": "context",
                "type": "text",
                "label": "Titrant",
                #  K2Cr2O7 on the source sheet; free text so any titrant reads back.
                "default": "K2Cr2O7",
                "overridable": True,
            },
            {
                "key": "equivalence_factor",
                "kind": "context",
                "label": "Factor (mg per mL of 1 N)",
                #  Sheet $G$10 — milliequivalent weight of sodium metabisulfite.
                "default": 47.5,
                "overridable": True,
            },
            {
                "key": "blank_ml",
                "kind": "context",
                "label": "Blank Titre",
                "unit": "mL",
                #  No blank column on this sheet; 0 leaves net titre == titre.
                "default": 0,
                "overridable": True,
            },
        ],
    ),
    "groups": [
        {
            "key": "determinations",
            "kind": "table",
            "label": "Sample Details",
            #  The sheet lays out repeated determination rows (Initial_Set-1,
            #  Initial_Set-2, ...); default 2 matches the two populated rows.
            "rows": {"min": 1, "max": 12, "default": 2, "labelFrom": "prep_ref"},
            #  No headerContext strip: Test / Analysis as per / LNB No. / Packing
            #  Detail / Titrant / Factor / L.C. all live in the editable Context
            #  card at the top of the worksheet. A headerContext echo renders them
            #  a second time here as read-only dashes, which looks broken and
            #  duplicates the editable fields — so it is deliberately omitted.
            "fields": [
                {"key": "prep_ref", "kind": "input", "type": "text", "label": "LNB No. / Set"},
                {
                    "key": "sample_ml",
                    "kind": "input",
                    "label": "ml of Sample",
                    "unit": "mL",
                    "default": 1,
                    "required": True,
                },
                {
                    "key": "titre_ml",
                    "kind": "input",
                    "label": "ml of Titrant",
                    "unit": "mL",
                    "required": True,
                },
                {
                    "key": "normality",
                    "kind": "input",
                    "label": "Normality (N)",
                    #  Per-row column, matching the sheet (col I carried $D$10 on
                    #  every row). Defaults to the standardised titrant normality
                    #  (sheet $D$10 = 0.1019 N); edit per row if a lot differs.
                    "default": 0.1019,
                    "required": True,
                },
                {
                    "key": "net_titre",
                    "kind": "calculated",
                    "label": "Net Titre",
                    "unit": "mL",
                    #  Blank defaults to 0, so this equals the titre unless a blank
                    #  is entered; a reagent blank consumes titrant too.
                    "expression": "titre_ml - blank_ml",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "mg_per_ml",
                    "kind": "calculated",
                    "label": "mg/ml",
                    "unit": "mg/mL",
                    #  Sheet K: (G*I*J*1000)/(F*1000). The 1000s cancel but are
                    #  kept so the expression matches the sheet a reviewer checks.
                    "expression": (
                        "(net_titre * normality * equivalence_factor * 1000) "
                        "/ (sample_ml * 1000)"
                    ),
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "key": "pct_lc",
                    "kind": "calculated",
                    "label": "% Result",
                    "unit": "%",
                    #  Sheet L: K / H * 100.
                    "expression": "mg_per_ml / label_claim * 100",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
            "footer": [
                {"label": "% Mean", "ref": "result.mean_pct_lc", "unit": "%"},
            ],
        },
        {
            "key": "result",
            "kind": "singleton",
            "label": "Result",
            "fields": [
                {
                    "key": "mean_pct_lc",
                    "kind": "calculated",
                    "label": "% Mean",
                    "unit": "%",
                    #  Sheet M: AVERAGE over the determination rows. Kept as the
                    #  reportable result but moved out of the per-row table into a
                    #  singleton, so it no longer renders as a repeating column —
                    #  it shows once in the table footer and as the Result group.
                    "expression": "mean(determinations.pct_lc)",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
    ],
    "criteria": [
        {
            "key": "determination_agreement",
            "label": "%RSD between determinations",
            "target": "rsd(determinations.pct_lc)",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
    ],
}

A9_SMBS = SeedTemplate(
    code="TPL-A9-0002",
    name="Calculation of Sodium Metabisulfite by Titrimetry",
    archetype="A9",
    result_unit="%",
    test_code="TST-SMBS-TITR",
    test_name="Sodium Metabisulfite by titrimetry",
    test_type="Quantitative",
    definition=A9_SMBS_DEFINITION,
)

TEMPLATES = [A9_SMBS]
