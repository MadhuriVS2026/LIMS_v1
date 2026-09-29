"""
A11 — microbial cylinder-plate (agar diffusion) bioassay.

Two workbooks: `Assay_ Microbial_Amphotericin B_API.xlsx` and
`Assay_Microbial_Amphotericin B_FP.xlsx`.

This is the one archetype whose measurement is not a chromatographic area. The
analyst measures the *diameter of the zone of growth inhibition* around cylinders
of sample and standard on a seeded agar plate, and quantitation is by
interpolation on a log-dose / zone-diameter straight line. Three consequences
shape the template:

1. **The response is logarithmic, so the curve is fitted in log space.** The
   x-axis is `ln(concentration)` and the sample is back-calculated with
   `exp((U - intercept) / slope)`. The engine already has `ln`, `exp`, `slope`
   and `intercept`; nothing new was needed.

2. **Plate-position correction is mandatory.** Plates differ in agar depth,
   inoculum density and incubation position, so every plate carries the *same*
   reference dose (S3) in alternate cylinders. A dose level's corrected mean is

       corrected = sample_zone_mean - (reference_zone_mean - grand_reference_mean)

   i.e. each plate set is shifted by however far its own reference readings drift
   from the reference mean across all plates. Without this the curve is fitted
   through plate-to-plate noise rather than through dose.

3. **The reference dose has no plate set of its own.** S3 *is* the reference
   half of every plate, so its point on the curve is `(ln C3, grand reference
   mean)`. Rather than special-casing it with a blank-detection heuristic — which
   would misfire on a half-entered worksheet and quietly invent a data point —
   the reference position is declared as `reference_row` on the stock group and
   the corrected mean switches on `rowno`. Changing which dose is the reference
   is then a field edit, not a template rewrite.

Ordering note: `curve.ref_grand` reads `standard.ref_avg` while
`standard.corrected_mean` reads `curve.ref_grand`. That is not circular — the two
touch different fields of the same group — and it only resolves because
dependency tracking is per *field*. A per-group model rejects this template.

## Deviation from the source workbooks — read before validating

Both sheets contain a fill-handle error in the results block. On the API sheet
every row divides by `I21`, the *second* preparation's nominal concentration, and
rows 2 and 3 mix set-2/set-1 dilution terms:

    H70 = ROUND(EXP(F70)/I21*100,2)     ← set 1, but uses set 2's nominal
    G71 = ROUND(EXP(F71)*H21/G21*E20/D20*C20/B20,0)   ← set 2 dilutions, set 1 weights

The intent is unambiguous — each preparation is quantified against its own
weights and dilutions — so this template computes each row from its own row, and
therefore will *not* reproduce the cached values in the workbook for sets 1 and 3.
That is deliberate. It is called out here because a reviewer comparing against
the spreadsheet will otherwise read it as a defect.
"""
from scripts.template_definitions._common import SeedTemplate, context_header

# ─────────────────────────────────────────────────────────────────────
#  Zone grid
# ─────────────────────────────────────────────────────────────────────

#  A cylinder-plate assay uses six cylinders per plate, alternating standard and
#  sample around the circle so that each is flanked by the other. Odd positions
#  carry the reference dose, even positions the test solution.
_PLATES = 3
_REFERENCE_ZONES = (1, 3, 5)
_SAMPLE_ZONES = (2, 4, 6)


def _zone_keys(side: str) -> list[str]:
    zones = _REFERENCE_ZONES if side == "ref" else _SAMPLE_ZONES
    return [f"{side}_p{plate}_z{zone}" for plate in range(1, _PLATES + 1) for zone in zones]


def _zone_inputs(side: str) -> list[dict]:
    """One numeric input per cylinder. Raw readings are captured, never averages —
    a worksheet that stores only the mean cannot be re-verified."""
    label_side = "Ref." if side == "ref" else "Sample"
    out: list[dict] = []
    for plate in range(1, _PLATES + 1):
        zones = _REFERENCE_ZONES if side == "ref" else _SAMPLE_ZONES
        for zone in zones:
            out.append(
                {
                    "key": f"{side}_p{plate}_z{zone}",
                    "kind": "input",
                    "label": f"P{plate} {label_side} Zone {zone}",
                    "unit": "mm",
                }
            )
    return out


def _zone_list(side: str) -> str:
    """The nine readings of one side as an argument list, so `mean(...)` spans all
    three plates exactly as the sheet's `AVERAGE(D42:F44)` does."""
    return ", ".join(_zone_keys(side))


def _zone_statistics(side: str, label: str) -> list[dict]:
    #  Left unrounded on purpose. The sheet rounds only log concentration, the
    #  regression coefficients and the final result; rounding the zone means here
    #  would move the last digit of the reported assay.
    return [
        {
            "key": f"{side}_avg",
            "kind": "calculated",
            "label": f"{label} Mean",
            "unit": "mm",
            "expression": f"mean({_zone_list(side)})",
        },
        {
            "key": f"{side}_rsd",
            "kind": "calculated",
            "label": f"{label} %RSD",
            "unit": "%",
            "expression": f"rsd({_zone_list(side)})",
        },
    ]


# ─────────────────────────────────────────────────────────────────────
#  Shared blocks
# ─────────────────────────────────────────────────────────────────────

#  Potency is carried as µg/mg, not as a percentage, because that is the unit on
#  the USP reference-standard label the analyst copies from (994 µg/mg). Storing
#  it as 99.4 % and multiplying by 1000 elsewhere adds a conversion for no gain.
_STOCK_GROUP = {
    "key": "std_stock",
    "kind": "singleton",
    "label": "Standard Stock Solution",
    "fields": [
        {"key": "name", "kind": "input", "type": "text", "label": "Standard Name"},
        {"key": "std_lot", "kind": "input", "type": "text", "label": "Standard Lot / Batch"},
        {"key": "weight_mg", "kind": "input", "label": "Weight", "unit": "mg", "required": True},
        {"key": "vol_1", "kind": "input", "label": "Dissolved to", "unit": "mL", "required": True},
        {"key": "potency", "kind": "input", "label": "Potency", "unit": "µg/mg", "default": 1000},
        {"key": "pip_final", "kind": "input", "label": "Aliquot to Buffer", "unit": "mL", "default": 1},
        {"key": "vol_final", "kind": "input", "label": "Diluted to (buffer)", "unit": "mL", "default": 20},
        {
            "key": "reference_row",
            "kind": "input",
            "label": "Reference Dose (row no.)",
            #  S3, the mid dose of five — the level plated in the reference
            #  cylinders of every plate.
            "default": 3,
        },
    ],
}

_STANDARD_GROUP = {
    "key": "standard",
    "kind": "table",
    "label": "Standard Dose Levels",
    #  Five levels, fixed. The regression and the reference-row index both assume
    #  the classic 5-dose design; a variable count would let a worksheet be saved
    #  with the reference pointing past the end of the table.
    "rows": {"min": 5, "max": 5, "default": 5, "labelFrom": "dose"},
    "fields": [
        {"key": "dose", "kind": "input", "type": "text", "label": "Dose"},
        {"key": "pip_dose", "kind": "input", "label": "Stock Taken", "unit": "mL", "required": True},
        {"key": "vol_dose", "kind": "input", "label": "Diluted to", "unit": "mL", "required": True},
        {
            "key": "conc",
            "kind": "calculated",
            "label": "Concentration",
            "unit": "µg/mL",
            "expression": (
                "std_stock.weight_mg / std_stock.vol_1 * pip_dose / vol_dose "
                "* std_stock.pip_final / std_stock.vol_final * std_stock.potency"
            ),
        },
        {
            "key": "log_conc",
            "kind": "calculated",
            "label": "Log Concentration",
            "expression": "ln(conc)",
            #  4 dp, as the sheet's ROUND(LN(...),4). The regression is fitted on
            #  the rounded value, so the rounding is part of the result.
            "rounding": {"mode": "round", "digits": 4},
        },
        *_zone_inputs("ref"),
        *_zone_inputs("spl"),
        *_zone_statistics("ref", "Reference Zone"),
        *_zone_statistics("spl", "Test Zone"),
        {
            "key": "corrected_mean",
            "kind": "calculated",
            "label": "Corrected Mean",
            "unit": "mm",
            #  The reference dose's own point is the grand reference mean; every
            #  other level is shifted by its plate set's reference drift.
            "expression": (
                "if(rowno = std_stock.reference_row, curve.ref_grand, "
                "spl_avg - (ref_avg - curve.ref_grand))"
            ),
        },
    ],
}

_CURVE_GROUP = {
    "key": "curve",
    "kind": "singleton",
    "label": "Standard Curve",
    "fields": [
        {
            "key": "ref_grand",
            "kind": "calculated",
            "label": "Grand Reference Zone Mean",
            "unit": "mm",
            #  AVERAGE over the dose-level reference means. Equal cylinder counts
            #  per level make this identical to the mean of all raw readings.
            "expression": "mean(standard.ref_avg)",
        },
        {
            "key": "curve_slope",
            "kind": "calculated",
            "label": "Slope",
            #  slope(ys, xs) — Excel's argument order. y is zone diameter,
            #  x is log concentration.
            "expression": "slope(standard.corrected_mean, standard.log_conc)",
            "rounding": {"mode": "round", "digits": 4},
        },
        {
            "key": "curve_intercept",
            "kind": "calculated",
            "label": "Intercept",
            "expression": "intercept(standard.corrected_mean, standard.log_conc)",
            "rounding": {"mode": "round", "digits": 4},
        },
        {
            "key": "r_squared",
            "kind": "calculated",
            "label": "R²",
            "expression": "correl(standard.corrected_mean, standard.log_conc) ^ 2",
            "rounding": {"mode": "round", "digits": 4},
        },
    ],
}


def _sample_prep_fields() -> list[dict]:
    return [
        {"key": "prep_ref", "kind": "input", "type": "text", "label": "Preparation"},
        {
            "key": "sample_weight",
            "kind": "input",
            "label": "Sample Wt.",
            "unit": "mg",
            "required": True,
        },
        {"key": "s_vol_1", "kind": "input", "label": "Dissolved to", "unit": "mL", "required": True},
        {"key": "s_pip_1", "kind": "input", "label": "Aliquot", "unit": "mL", "default": 1},
        {"key": "s_vol_2", "kind": "input", "label": "Diluted to", "unit": "mL", "required": True},
        {"key": "s_pip_2", "kind": "input", "label": "Aliquot to Buffer", "unit": "mL", "default": 1},
        {
            "key": "s_vol_3",
            "kind": "input",
            "label": "Diluted to (buffer)",
            "unit": "mL",
            "default": 20,
        },
        {
            "key": "nominal_conc",
            "kind": "calculated",
            "label": "Nominal Concentration",
            "unit": "µg/mL",
            #  What the preparation *should* contain at 100 % of claim. ×1000
            #  converts the weighed mg to µg so it is comparable with the curve.
            "expression": (
                "sample_weight / s_vol_1 * s_pip_1 / s_vol_2 * 1000 * s_pip_2 / s_vol_3"
            ),
        },
    ]


def _sample_readout_fields() -> list[dict]:
    return [
        *_zone_inputs("ref"),
        *_zone_inputs("spl"),
        *_zone_statistics("ref", "Reference Zone"),
        *_zone_statistics("spl", "Test Zone"),
        {
            "key": "corrected_mean",
            "kind": "calculated",
            "label": "Corrected Mean (U)",
            "unit": "mm",
            #  Corrected against the *curve's* grand reference mean, not against
            #  this plate set alone — that is what puts sample and curve on one scale.
            "expression": "spl_avg - (ref_avg - curve.ref_grand)",
        },
        {
            "key": "log_conc_u",
            "kind": "calculated",
            "label": "Log Concentration (Lu)",
            "expression": "(corrected_mean - curve.curve_intercept) / curve.curve_slope",
        },
        {
            "key": "measured_conc",
            "kind": "calculated",
            "label": "Concentration Found (Cu)",
            "unit": "µg/mL",
            "expression": "exp(log_conc_u)",
        },
    ]


_ZONE_RSD_LIMIT = 10.0


def _criteria(*, sample_group: str = "sample") -> list[dict]:
    return [
        {
            "key": "zone_rsd_standard",
            "label": "Widest zone-diameter %RSD across standard plates",
            "target": "max(pool(standard.ref_rsd, standard.spl_rsd))",
            "operator": "lte",
            "limit": _ZONE_RSD_LIMIT,
            "severity": "blocking",
            "limitText": f"NMT {_ZONE_RSD_LIMIT} %",
        },
        {
            "key": "zone_rsd_sample",
            "label": "Widest zone-diameter %RSD across sample plates",
            "target": f"max(pool({sample_group}.ref_rsd, {sample_group}.spl_rsd))",
            "operator": "lte",
            "limit": _ZONE_RSD_LIMIT,
            "severity": "blocking",
            "limitText": f"NMT {_ZONE_RSD_LIMIT} %",
        },
        {
            "key": "curve_linearity",
            "label": "Correlation of the log-dose / zone-diameter line",
            "target": "curve.r_squared",
            "operator": "gte",
            #  The sheets note "R2 = NLT 95 %". Below this the interpolation the
            #  whole result rests on is not supportable, so it blocks.
            "limit": 0.95,
            "severity": "blocking",
            "limitText": "NLT 0.95",
        },
        {
            "key": "preparation_agreement",
            "label": "%RSD between sample preparations",
            "target": "results.rsd_assay",
            "operator": "lte",
            "limit": _ZONE_RSD_LIMIT,
            #  The sheets' "RSD : NMT 10 %" note sits beside this figure as well
            #  as beside the zone RSDs; applied to both rather than guessing which.
            "severity": "blocking",
            "limitText": f"NMT {_ZONE_RSD_LIMIT} %",
        },
    ]


# ─────────────────────────────────────────────────────────────────────
#  A11a — API, reported as potency µg/mg and % of assay
# ─────────────────────────────────────────────────────────────────────

A11_API_DEFINITION = {
    "resultRef": "results.mean_assay",
    "context": context_header(label_claim=False, avg_weight=False),
    "groups": [
        _STOCK_GROUP,
        _STANDARD_GROUP,
        _CURVE_GROUP,
        {
            "key": "sample",
            "kind": "table",
            "label": "Sample Preparations",
            "rows": {"min": 1, "max": 6, "default": 3, "labelFrom": "prep_ref"},
            "fields": [
                *_sample_prep_fields(),
                *_sample_readout_fields(),
                {
                    "key": "potency_ug_per_mg",
                    "kind": "calculated",
                    "label": "Potency",
                    "unit": "µg/mg",
                    #  The dilution chain multiplied back up to the weighed solid.
                    "expression": (
                        "measured_conc * s_vol_3 / s_pip_2 * s_vol_2 / s_pip_1 "
                        "* s_vol_1 / sample_weight"
                    ),
                    "rounding": {"mode": "round", "digits": 0},
                },
                {
                    "key": "assay_pct",
                    "kind": "calculated",
                    "label": "Assay",
                    "unit": "%",
                    "expression": "measured_conc / nominal_conc * 100",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
        {
            "key": "results",
            "kind": "singleton",
            "label": "Results",
            "fields": [
                {
                    "key": "mean_potency",
                    "kind": "calculated",
                    "label": "Mean Potency",
                    "unit": "µg/mg",
                    "expression": "mean(sample.potency_ug_per_mg)",
                    "rounding": {"mode": "round", "digits": 0},
                },
                {
                    "key": "mean_assay",
                    "kind": "calculated",
                    "label": "Mean Assay",
                    "unit": "%",
                    "expression": "mean(sample.assay_pct)",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "sd_assay",
                    "kind": "calculated",
                    "label": "SD",
                    "expression": "sd(sample.assay_pct)",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "rsd_assay",
                    "kind": "calculated",
                    "label": "%RSD",
                    "unit": "%",
                    "expression": "rsd(sample.assay_pct)",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
    ],
    "criteria": _criteria(),
}

A11_API = SeedTemplate(
    code="TPL-A11-0001",
    name="Assay by Microbial Bioassay — API",
    archetype="A11",
    result_unit="%",
    test_code="TST-BIOA-API",
    test_name="Assay by Microbial Bioassay (API)",
    test_type="Quantitative",
    definition=A11_API_DEFINITION,
)


# ─────────────────────────────────────────────────────────────────────
#  A11b — finished product, reported as % of label claim
# ─────────────────────────────────────────────────────────────────────

A11_FP_DEFINITION = {
    "resultRef": "results.mean_assay",
    "context": context_header(),
    "groups": [
        _STOCK_GROUP,
        _STANDARD_GROUP,
        _CURVE_GROUP,
        {
            "key": "sample",
            "kind": "table",
            "label": "Sample Preparations",
            "rows": {"min": 1, "max": 6, "default": 2, "labelFrom": "prep_ref"},
            "fields": [
                *_sample_prep_fields(),
                *_sample_readout_fields(),
                {
                    "key": "assay_pct",
                    "kind": "calculated",
                    "label": "Assay",
                    "unit": "%",
                    #  Same master equation as every other finished-product
                    #  archetype: found ÷ nominal, scaled from the weight taken
                    #  to one dosage unit, against the label claim.
                    "expression": (
                        "measured_conc / nominal_conc * avg_weight / label_claim * 100"
                    ),
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
        {
            "key": "results",
            "kind": "singleton",
            "label": "Results",
            "fields": [
                {
                    "key": "mean_assay",
                    "kind": "calculated",
                    "label": "Mean Assay",
                    "unit": "%",
                    "expression": "mean(sample.assay_pct)",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "sd_assay",
                    "kind": "calculated",
                    "label": "SD",
                    "expression": "sd(sample.assay_pct)",
                    "rounding": {"mode": "round", "digits": 2},
                },
                {
                    "key": "rsd_assay",
                    "kind": "calculated",
                    "label": "%RSD",
                    "unit": "%",
                    "expression": "rsd(sample.assay_pct)",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ],
        },
    ],
    "criteria": _criteria(),
}

A11_FP = SeedTemplate(
    code="TPL-A11-0002",
    name="Assay by Microbial Bioassay — Finished Product",
    archetype="A11",
    result_unit="%",
    test_code="TST-BIOA-FP",
    test_name="Assay by Microbial Bioassay (FP)",
    test_type="Quantitative",
    definition=A11_FP_DEFINITION,
)

TEMPLATES = [A11_API, A11_FP]
