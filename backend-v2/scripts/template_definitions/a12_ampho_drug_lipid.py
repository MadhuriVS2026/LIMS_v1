"""
A12 — Amphotericin B drug-to-lipid ratio (liposomal), per batch.

Source: a batch-release sheet for a liposomal Amphotericin B product that lists,
per batch, the microbial assay of the drug and the assays of three lipid
components, then derives the total lipid content and the drug-to-lipid ratio.

Like its A12 siblings this is a *derived roll-up*: every number on the worksheet
is a result carried from another test (the component assays), there is no
injection / standard / area block, and the reportable is a ratio computed from
those carried values. It differs from `TPL-A12-0002` only in shape — the source
sheet lists MULTIPLE batches, so this is ONE multi-batch TABLE (one row per
batch) rather than the singleton carry-over blocks of A12-0002.

## Reverse-engineered label claims (content factors)

The sheet prints a content (mg/vial) beside each assay but not the per-component
label claim it used. The label claims below were reverse-engineered from the gold
data — each is `content / assay * 100`, constant across all three batches — and
are the content factor in `Content = Assay% × LC / 100`:

    Cholesterol      LC = 52.0   mg/vial   (e.g. 105.3 % → 54.7560)
    HSPC             LC = 213.0  mg/vial   (e.g. 107.5 % → 228.9750)
    DSPG             LC = 81.6   mg/vial   (e.g. 100.8 % → 82.2528)
    Amphotericin B   LC = 50.0   mg/vial   (e.g. 110.6 % → 55.3200)   ← the DRUG

They are modelled as OVERRIDABLE CONTEXT fields (`lc_chol`, `lc_hspc`, `lc_dspg`,
`lc_ampho`) so a lab can adjust a label claim without a new template, exactly as
`a2_bupivacaine_lipid_ratio.py` models its per-component label claims. Each
content column reads its component's assay times that component's LC:
`<c>_content = <c>_assay * lc_<c> / 100`.

## Formula derivations

    Content (mg/vial)        = Assay% × LC / 100           (per component)
    Lipid content (mg/vial)  = Chol + HSPC + DSPG contents (the three LIPIDS only;
                               the drug Amphotericin B is EXCLUDED)
    Drug / Lipid Ratio       = Ampho content / Lipid content

No mid-chain rounding is applied in the stored expressions — the sheet shows the
ratio to 4 dp as display rounding, and the unrounded stored ratio reproduces every
gold value to that precision (verified against all three batches).

## resultRef and criteria targeting

`resultRef = "batches.drug_lipid_ratio"`. For a multi-row group the engine returns
the first non-blank value down the rows (the per-batch reportable), consistent with
the other multi-batch templates.

Acceptance criteria follow the sheet's limit row. The content columns are "N/A" in
the sheet, so they carry no criterion. The four assay ranges are the stated limits
and the ratio range is the product acceptance range; all five are BLOCKING,
matching the sibling convention (A12-0001's suitability criteria are blocking; the
ratio spec here is a release limit). The engine needs a scalar target for a
per-row table, so each criterion targets the MEAN across the batch rows
(`mean(batches.<field>)`), the same aggregate `TPL-A12-0001` uses to target its
carried per-row assay (`mean(preps.pct_assay_total)`).

## Acceptance Ranges strip (additive, editable, display-only)

An `acceptance_ranges` singleton of five EDITABLE free-text fields is placed
immediately before the `batches` group so it renders as a ranges header after the
section title. The fields are purely INFORMATIONAL — they are inputs in their own
group, pre-filled with the stated acceptance ranges and editable/persisted, but
they are NEVER referenced by any expression, criterion target, or `resultRef`.
They do NOT drive pass/fail; enforcement stays entirely in the five blocking
`criteria` below, which are unchanged. This addition is purely additive: no gold
value, batch formula, context field, or criterion is altered.
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
)

#  Per-component label claim (mg/vial), reverse-engineered from the gold data as
#  content / assay * 100 (constant across the three batches). Modelled as
#  overridable context below so a lab can adjust without a new template.
_LC_DEFAULTS = {
    "chol": 52.0,
    "hspc": 213.0,
    "dspg": 81.6,
    "ampho": 50.0,
}

#  The three LIPID components (drug excluded) in sheet column order, with the
#  assay label the sheet prints for each.
_LIPIDS = [
    ("chol", "Cholesterol", "Assay of Cholesterol", "Content of Cholesterol (mg/vial)"),
    ("hspc", "HSPC", "Assay of HSPC", "Content of HSPC (mg/vial)"),
    ("dspg", "DSPG", "Assay of DSPG", "Content of DSPG (mg/vial)"),
]


def _batch_fields() -> list[dict]:
    """
    One ROW per batch. Columns, in sheet order: Batch No., Condition, then each
    lipid's assay (%) + content (mg/vial), the drug's assay (%) + content, the
    summed lipid content and the drug/lipid ratio.
    """
    fields: list[dict] = [
        {"key": "batch_no", "kind": "input", "type": "text", "label": "Batch No."},
        {"key": "condition", "kind": "input", "type": "text", "label": "Condition"},
    ]
    for prefix, _name, assay_label, content_label in _LIPIDS:
        fields.append(
            {
                "key": f"{prefix}_assay",
                "kind": "input",
                "label": assay_label,
                "unit": "%",
                "required": True,
            }
        )
        fields.append(
            {
                "key": f"{prefix}_content",
                "kind": "calculated",
                "label": content_label,
                "unit": "mg/vial",
                #  Content = Assay% × LC / 100, LC an overridable context field.
                "expression": f"{prefix}_assay * lc_{prefix} / 100",
            }
        )
    #  Amphotericin B — the DRUG. Same Content = Assay × LC / 100 shape, but its
    #  content is EXCLUDED from the lipid total and feeds the ratio numerator.
    fields += [
        {
            "key": "ampho_assay",
            "kind": "input",
            "label": "Microbial assay of Amphotericin B",
            "unit": "%",
            "required": True,
        },
        {
            "key": "ampho_content",
            "kind": "calculated",
            "label": "Content of Amphotericin B (mg/vial)",
            "unit": "mg/vial",
            "expression": "ampho_assay * lc_ampho / 100",
        },
        {
            "key": "lipid_content",
            "kind": "calculated",
            "label": "Calculated Lipid content (mg/vial)",
            "unit": "mg/vial",
            #  The three LIPIDS only; the drug Amphotericin B is excluded.
            "expression": "chol_content + hspc_content + dspg_content",
        },
        {
            "key": "drug_lipid_ratio",
            "kind": "calculated",
            "label": "Calculated Drug to Lipid ratio",
            #  Ampho content / Lipid content. Dimensionless. No mid-chain
            #  rounding — the stored value is unrounded and reproduces the sheet's
            #  4-dp gold figures exactly.
            "expression": "ampho_content / lipid_content",
        },
    ]
    return fields


def _acceptance_ranges_group() -> dict:
    """
    Editable, display-only "Acceptance Ranges" strip rendered immediately before
    the batch table. Five free-text inputs pre-filled with the stated acceptance
    ranges. INFORMATIONAL only — never referenced by any expression, criterion
    target, or resultRef, so they cannot change batch math, the ratio, or the
    five blocking criteria. Enforcement stays in `criteria`.
    """
    return {
        "key": "acceptance_ranges",
        "kind": "singleton",
        "label": "Acceptance Ranges",
        "fields": [
            {"key": "range_chol", "kind": "input", "type": "text", "label": "Assay of Cholesterol", "default": "90.0% to 120.0%"},
            {"key": "range_hspc", "kind": "input", "type": "text", "label": "Assay of HSPC", "default": "90.0% to 120.0%"},
            {"key": "range_dspg", "kind": "input", "type": "text", "label": "Assay of DSPG", "default": "80.0% to 120.0%"},
            {"key": "range_ampho", "kind": "input", "type": "text", "label": "Microbial assay of Amphotericin B", "default": "90.0% to 120.0%"},
            {"key": "range_ratio", "kind": "input", "type": "text", "label": "Calculated Drug to Lipid ratio", "default": "Between 0.11 to 0.17"},
        ],
    }


def _assay_criterion(key: str, prefix: str, label: str, low: float, high: float) -> dict:
    """Blocking %-range criterion on a component assay, targeted at the batch mean."""
    return {
        "key": key,
        "label": label,
        "target": f"mean(batches.{prefix}_assay)",
        "operator": "between",
        "limit": [low, high],
        "severity": "blocking",
        "limitText": f"{low:.1f} % to {high:.1f} %",
    }


A12_AMPHO_RATIO_DEFINITION = {
    "resultRef": "batches.drug_lipid_ratio",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {"key": "product_name", "kind": "context", "type": "text", "label": "Product Name", "overridable": True},
            {"key": "assay_source", "kind": "context", "type": "text", "label": "Assays carried from — test / TRF / A.R. No.", "overridable": True},
            #  Per-component label claims (mg/vial), reverse-engineered from the
            #  gold data. Constant per component across batches → overridable
            #  context, feeding each component's Content = Assay × LC / 100.
            {"key": "lc_chol", "kind": "context", "label": "LC — Cholesterol", "unit": "mg/vial", "default": _LC_DEFAULTS["chol"], "overridable": True},
            {"key": "lc_hspc", "kind": "context", "label": "LC — HSPC", "unit": "mg/vial", "default": _LC_DEFAULTS["hspc"], "overridable": True},
            {"key": "lc_dspg", "kind": "context", "label": "LC — DSPG", "unit": "mg/vial", "default": _LC_DEFAULTS["dspg"], "overridable": True},
            {"key": "lc_ampho", "kind": "context", "label": "LC — Amphotericin B", "unit": "mg/vial", "default": _LC_DEFAULTS["ampho"], "overridable": True},
        ],
    ),
    "groups": [
        #  Editable, display-only acceptance-ranges strip, rendered above the
        #  batch table. Additive and informational — does NOT drive pass/fail.
        _acceptance_ranges_group(),
        {
            "key": "batches",
            "kind": "table",
            "label": "Batches — assays carried from the component tests",
            #  Multiple batches per sheet; the range allows more or fewer without a
            #  new template. Row label is the batch number.
            "rows": {"min": 1, "max": 24, "default": 3, "labelFrom": "batch_no"},
            "fields": _batch_fields(),
        },
    ],
    "criteria": [
        _assay_criterion("chol_assay_range", "chol", "Assay of Cholesterol", 90.0, 120.0),
        _assay_criterion("hspc_assay_range", "hspc", "Assay of HSPC", 90.0, 120.0),
        _assay_criterion("dspg_assay_range", "dspg", "Assay of DSPG", 80.0, 120.0),
        _assay_criterion("ampho_assay_range", "ampho", "Microbial assay of Amphotericin B", 90.0, 120.0),
        {
            "key": "drug_lipid_ratio_range",
            "label": "Drug to Lipid ratio",
            #  Product acceptance range — blocking. Scalar target over the batch
            #  rows, matching how A12-0001 targets its per-row carried assay.
            "target": "mean(batches.drug_lipid_ratio)",
            "operator": "between",
            "limit": [0.11, 0.17],
            "severity": "blocking",
            "limitText": "0.11 to 0.17",
        },
    ],
}

A12_AMPHO_RATIO = SeedTemplate(
    code="TPL-A12-0003",
    name="Amphotericin B — Drug-to-Lipid Ratio",
    archetype="A12",
    #  A ratio of two mg/vial contents. Left unitless, matching TPL-A12-0002.
    result_unit=None,
    test_code="TST-ALDR",
    test_name="Ampho-lipid to drug ratio",
    test_type="Quantitative",
    definition=A12_AMPHO_RATIO_DEFINITION,
)


TEMPLATES = [A12_AMPHO_RATIO]
