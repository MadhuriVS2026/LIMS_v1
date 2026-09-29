"""
A12 — derived roll-ups: results computed from other tests' results.

Sources:
  * `Bupivacaine Free & Entrrapted Drug Calculation.xlsx` (sheet `Sheet `) —
    free vs liposome-entrapped drug, which needs the total assay of the same
    sample.
  * `Bupivacaine Lipid & Drug to lipid Ratio.xlsx`, sheet
    `Drug to Lipid ratio Auto Calc` — drug-to-lipid ratio, which needs the lipid
    content of four components *and* the drug assay.

What makes this family different from every other archetype is the input, not the
arithmetic: at least one number comes from a **different test on the same sample**.
The workbooks handle that by hand — the free/entrapped sheet has `% Assay of
Bupivacaine` typed into column M, and the ratio sheet reaches across to the lipid
sheet with `='Lipid '!O43`.

## How the cross-test input is modelled, and what is still open

Each carried-over value is an explicit, required input, labelled with the test it
comes from, and the source TRF / A.R. number is recorded in context beside it. That
is what the lab does today, with two things it did not have: the value is inside a
worksheet whose every edit is in the audit trail, and the template states which test
each number must come from.

It is not yet a *link*. The engine resolves context from the TRF, the product, the
sample and the session; referencing another test's released result would need a new
context source (something like `resultOf('TST-03')`) resolved in
`WorksheetService._seed_context`, which is a service change rather than a template
change. Recorded as a follow-up. Until it exists, a transposed digit here is caught
by review rather than by the system, so the criteria below check what can be
checked: that the carried assay is a plausible percentage.

## The free/entrapped sheet has a one-column reference slip

Its two entrapment cells substitute an already-normalised quantity where the
measured one belongs:

    Q28 = (M28 − O28) / M28 × 100      % Entrapped
    R28 = (N28 − P28) / N28 × L.C.     Entrapped (mg/mL)

`O28` is `% Free Drug`, already expressed as a fraction of the *measured* content
(`%Con / %Assay × 100`), while `M28` is `% Assay` against label claim. Subtracting
one from the other mixes two bases. `P28` in `R28` is the same slip: it is free drug
already rescaled to label claim, subtracted from the measured total `N28`.

Substituting the un-normalised partner in each — `%Con` for `O28`, the measured free
concentration for `P28` — makes both cells reconcile with the obvious identity, and
that is what is implemented here:

    % Entrapped        = 100 − % Free
    Entrapped (mg/mL)  = L.C. − Free (mg/mL)

For scale: with `%Assay` 101.5 and `%Con` 5.0 the sheet gives 95.15 % entrapped and
the corrected form 95.07 %; on the mg/mL pair, 12.6544 against 12.6448. Small, and
zero when the assay happens to be exactly 100 %, which is presumably why it went
unnoticed. Not reproduced, because the two forms cannot both be right and the
identity `free + entrapped = whole` is not negotiable. Flagged for lab confirmation
in the plan rather than changed quietly.

## Both reportables are LC-normalised, and both bases are shown

`P28` and `R28` express free and entrapped drug per label claim rather than as the
concentrations actually measured, so the pair sums to the label claim rather than to
the measured content. That is a presentation choice, not an error, and it is the one
the sheet reports — so it is kept, with the measured concentrations shown alongside
it under their own labels. A worksheet that showed only the normalised pair would
make a batch assaying at 90 % look like it contained a full label claim of drug
split between two compartments.

## No standard block on the ratio template

The drug-to-lipid template has no standard, no dilution chain and no area fields at
all: every number in it was measured by another test. Giving it an HPLC shape to
look like its siblings would ask an analyst to record injections that belong to a
different worksheet.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
    replicate_area_group,
    standard_chain_terms,
    standard_group,
    sst_rsd_criterion,
)

# ─────────────────────────────────────────────────────────────────────
#  Shared: provenance of a carried-over result
# ─────────────────────────────────────────────────────────────────────


def _source_context(*sources: tuple[str, str, str]) -> list[dict]:
    """
    Context fields naming where each carried-over result came from.

    A transcribed number with no provenance cannot be checked by a reviewer, which
    is the one control left while the link is manual.
    """
    return [
        {
            "key": key,
            "kind": "context",
            "type": "text",
            "label": label,
            "overridable": True,
            **({"default": default} if default else {}),
        }
        for key, label, default in sources
    ]


def _plausible_assay_criterion(target: str, label: str) -> dict:
    """
    A carried-over assay must at least be a percentage in a believable range.

    This catches a decimal-point slip (10.15 for 101.5), which would otherwise
    propagate silently into every reportable on the sheet. Advisory: an unusual but
    real assay must still be recordable.
    """
    return {
        "key": "carried_assay_plausible",
        "label": label,
        "target": target,
        "operator": "between",
        "limit": [50.0, 150.0],
        "severity": "advisory",
        "limitText": "50 % to 150 % — outside this, check the transcription",
    }


# ─────────────────────────────────────────────────────────────────────
#  A12-0001 — Free & Entrapped Drug
# ─────────────────────────────────────────────────────────────────────

#  Bracketing blocks start empty and grow as brackets are actually injected.
#  Pre-filling six blank rows per block would show six injections that never
#  happened on a worksheet that is meant to be a record of what was run.
_BKT_ROWS = {"min": 0, "max": 6, "default": 0}


_FED_STATS_GROUP = {
    "key": "stats",
    "kind": "singleton",
    "label": "Standard Statistics",
    "fields": [
        {
            "key": "mean_std",
            "kind": "calculated",
            "label": "Mean STD Area",
            "expression": "mean(std_areas.area)",
        },
        {
            "key": "sd_std",
            "kind": "calculated",
            "label": "SD",
            "expression": "sd(std_areas.area)",
        },
        {
            "key": "rsd_std",
            "kind": "calculated",
            "label": "%RSD",
            "unit": "%",
            "expression": "rsd(std_areas.area)",
        },
        {
            "key": "rsd_bkt",
            "kind": "calculated",
            "label": "%RSD (pooled with bracketing standards)",
            "unit": "%",
            #  Cumulative pooling, as in A1: a bracket averaged on its own would
            #  let a drifting system pass suitability.
            "expression": "rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))",
        },
    ],
}


def _prep_fields() -> list[dict]:
    return [
        {"key": "prep_ref", "kind": "input", "type": "text", "label": "Prep. Ref."},
        {
            "key": "sample_ml",
            "kind": "input",
            "label": "Sample Taken",
            "unit": "mL",
            "required": True,
            "default": 1,
        },
        {"key": "s_vol_1", "kind": "input", "label": "Vol", "unit": "mL", "required": True},
        {"key": "s_pip_1", "kind": "input", "label": "Pip", "unit": "mL", "default": 1},
        {"key": "s_vol_2", "kind": "input", "label": "Vol", "unit": "mL", "default": 1},
        {
            "key": "area",
            "kind": "area",
            "label": "Free Drug (supernatant) Area",
        },
        {
            "key": "free_conc",
            "kind": "calculated",
            "label": "Free Drug — measured",
            "unit": "mg/mL",
            #  Sheet P28's numerator: the standard chain gives mg/mL at the injected
            #  concentration, the sample chain multiplies back up to the original
            #  suspension.
            "expression": (
                f"area / stats.mean_std * {standard_chain_terms()} "
                "* standard.mw_base / standard.mw_salt * standard.potency / 100 "
                "* s_vol_1 / sample_ml * s_vol_2 / s_pip_1"
            ),
        },
        {
            "key": "pct_con",
            "kind": "calculated",
            "label": "% Con. — free drug against label claim",
            "unit": "%",
            #  Sheet L28. That cell multiplies by potency as a percentage instead of
            #  potency/100 and then omits the ×100, which comes to the same thing;
            #  written the readable way round here.
            "expression": "free_conc / label_claim * 100",
        },
        {
            "key": "pct_assay_total",
            "kind": "input",
            "label": "% Assay of total drug — carried from the Assay test",
            "unit": "%",
            "required": True,
        },
        {
            "key": "total_mg_ml",
            "kind": "calculated",
            "label": "Total Drug — measured",
            "unit": "mg/mL",
            #  Sheet N28.
            "expression": "pct_assay_total * label_claim / 100",
        },
        {
            "key": "pct_free",
            "kind": "calculated",
            "label": "% Free Drug",
            "unit": "%",
            #  Sheet O28: free as a fraction of what the sample actually contains,
            #  not of the label claim.
            "expression": "pct_con / pct_assay_total * 100",
        },
        {
            "key": "pct_entrapped",
            "kind": "calculated",
            "label": "% Entrapped Drug",
            "unit": "%",
            #  Corrected form of sheet Q28 — see the module docstring. Equivalently
            #  (%Assay − %Con) / %Assay × 100.
            "expression": "100 - pct_free",
        },
        {
            "key": "free_mg_ml_lc",
            "kind": "calculated",
            "label": "Free Drug — per label claim",
            "unit": "mg/mL",
            #  Sheet P28 in full.
            "expression": "free_conc / total_mg_ml * label_claim",
        },
        {
            "key": "entrapped_mg_ml_lc",
            "kind": "calculated",
            "label": "Entrapped Drug — per label claim",
            "unit": "mg/mL",
            #  Corrected form of sheet R28. Pairs with `free_mg_ml_lc` to the label
            #  claim by construction.
            "expression": "label_claim - free_mg_ml_lc",
        },
        {
            "key": "entrapped_conc",
            "kind": "calculated",
            "label": "Entrapped Drug — measured",
            "unit": "mg/mL",
            #  The measured partner of the normalised pair above: what is actually
            #  in the vial, not what would be there at full label claim.
            "expression": "total_mg_ml - free_conc",
        },
        {
            "key": "mean_pct_entrapped",
            "kind": "calculated",
            "label": "Mean % Entrapped Drug",
            "unit": "%",
            "expression": "mean(preps.pct_entrapped)",
            "rounding": {"mode": "round", "digits": 2},
        },
        {
            "key": "mean_pct_free",
            "kind": "calculated",
            "label": "Mean % Free Drug",
            "unit": "%",
            "expression": "mean(preps.pct_free)",
            "rounding": {"mode": "round", "digits": 2},
        },
    ]


A12_FED_DEFINITION = {
    #  Entrapment is the point of the test; % free is reported alongside it and the
    #  two sum to 100 by construction.
    "resultRef": "preps.mean_pct_entrapped",
    "context": context_header(
        #  `label_claim` is the drug's declared strength in mg/mL and divides into
        #  every reportable here, so it stays an entered number rather than the TRF's
        #  free-text label-claim column.
        avg_weight=False,
        extra=_source_context(
            (
                "assay_source",
                "% Assay carried from — test / TRF / A.R. No.",
                "",
            ),
        ),
    ),
    "groups": [
        standard_group(conc_label="Concentration"),
        replicate_area_group(default_rows=6),
        {
            "key": "bkt_1",
            "kind": "table",
            "label": "Bracketing Standard — Block 1",
            "rows": _BKT_ROWS,
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
        },
        {
            "key": "bkt_2",
            "kind": "table",
            "label": "Bracketing Standard — Block 2",
            "rows": _BKT_ROWS,
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
        },
        _FED_STATS_GROUP,
        {
            "key": "preps",
            "kind": "table",
            "label": "Sample Preparations",
            "rows": {"min": 1, "max": 12, "default": 2, "labelFrom": "prep_ref"},
            "fields": _prep_fields(),
        },
    ],
    "criteria": [
        sst_rsd_criterion(),
        {
            "key": "sst_bkt_rsd",
            "label": "%RSD of pooled bracketing standards",
            "target": "stats.rsd_bkt",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        _plausible_assay_criterion(
            "mean(preps.pct_assay_total)",
            "Carried-over % Assay of total drug",
        ),
    ],
}

A12_FED = SeedTemplate(
    code="TPL-A12-0001",
    name="Free & Entrapped Drug (liposomal)",
    archetype="A12",
    result_unit="%",
    test_code="TST-FED",
    test_name="Free & Entrapped Drug",
    test_type="Quantitative",
    definition=A12_FED_DEFINITION,
)


# ─────────────────────────────────────────────────────────────────────
#  A12-0002 — Drug-to-Lipid Ratio
# ─────────────────────────────────────────────────────────────────────

_LIPIDS_GROUP = {
    "key": "lipids",
    "kind": "table",
    "label": "Lipid Components — carried from the Lipid Content test",
    #  Four components in the source product; the range allows a different lipid
    #  panel without a new template, since nothing here is per-component arithmetic.
    "rows": {"min": 1, "max": 8, "default": 4, "labelFrom": "name"},
    "fields": [
        {"key": "name", "kind": "input", "type": "text", "label": "Component"},
        {
            "key": "lc",
            "kind": "input",
            "label": "Label Claim",
            "unit": "mg/mL",
            "required": True,
        },
        {
            "key": "pct_mean",
            "kind": "input",
            "label": "% Mean content — carried from the Lipid Content test",
            "unit": "%",
            "required": True,
        },
        {
            "key": "mg_per_ml",
            "kind": "calculated",
            "label": "Content",
            "unit": "mg/mL",
            #  Ratio sheet I18: %Mean × L.C. / 100.
            "expression": "pct_mean * lc / 100",
        },
    ],
}

_DRUG_GROUP = {
    "key": "drug",
    "kind": "singleton",
    "label": "Drug — carried from the Assay test",
    "fields": [
        {"key": "name", "kind": "input", "type": "text", "label": "Drug"},
        {
            "key": "lc",
            "kind": "input",
            "label": "Label Claim",
            "unit": "mg/mL",
            "required": True,
        },
        {
            "key": "pct_assay",
            "kind": "input",
            "label": "% Assay — carried from the Assay test",
            "unit": "%",
            "required": True,
        },
        {
            "key": "mg_per_ml",
            "kind": "calculated",
            "label": "Content",
            "unit": "mg/mL",
            #  Ratio sheet M18.
            "expression": "pct_assay * lc / 100",
        },
    ],
}

_RATIO_GROUP = {
    "key": "ratio",
    "kind": "singleton",
    "label": "Drug-to-Lipid Ratio",
    "fields": [
        {
            "key": "sum_lipid",
            "kind": "calculated",
            "label": "Σ Lipid Content",
            "unit": "mg/mL",
            #  Ratio sheet J18. Guarded: `sum` of an empty range is 0, and a zero
            #  total would read as "no lipid detected" on an untouched worksheet
            #  before dividing into it made the ratio blank anyway.
            "expression": (
                "if(count(lipids.mg_per_ml) > 0, sum(lipids.mg_per_ml), blank())"
            ),
        },
        {
            "key": "drug_to_lipid",
            "kind": "calculated",
            "label": "Drug / Lipid Ratio",
            #  Ratio sheet N18. Dimensionless: mg/mL over mg/mL.
            "expression": "drug.mg_per_ml / sum_lipid",
            #  The sheet applies no rounding; 4 dp is well inside the precision of
            #  the two assays it divides and stops float artefacts reaching a
            #  certificate.
            "rounding": {"mode": "round", "digits": 4},
        },
    ],
}


A12_RATIO_DEFINITION = {
    "resultRef": "ratio.drug_to_lipid",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=_source_context(
            ("assay_source", "% Assay carried from — test / TRF / A.R. No.", ""),
            (
                "lipid_source",
                "Lipid content carried from — test / TRF / A.R. No.",
                "",
            ),
        ),
    ),
    "groups": [_LIPIDS_GROUP, _DRUG_GROUP, _RATIO_GROUP],
    "criteria": [
        #  No suitability criteria: there is no injection on this worksheet to
        #  qualify. Both source tests carry their own, and they were enforced when
        #  those results were released.
        _plausible_assay_criterion(
            "drug.pct_assay",
            "Carried-over % Assay of drug",
        ),
    ],
}

A12_RATIO = SeedTemplate(
    code="TPL-A12-0002",
    name="Drug-to-Lipid Ratio",
    archetype="A12",
    #  A ratio of two concentrations. Left unitless rather than invented as "w/w",
    #  which it is not.
    result_unit=None,
    test_code="TST-DLR",
    test_name="Drug to Lipid Ratio",
    test_type="Quantitative",
    definition=A12_RATIO_DEFINITION,
)


TEMPLATES = [A12_FED, A12_RATIO]
