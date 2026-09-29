"""
A7 — dissolution profile comparison (f1 difference factor / f2 similarity factor).

Source: `F1F2 Calculation_sheet_Dissolution.xlsx`, sheet `f1f2` — Amphotericin B
Liposome for Injection (test) against AmBisome® (reference), 12 units, 9
time-points.

This is not a sample test. It compares a *test* product's mean release profile
against a *reference* product's, and both profiles are results that already exist:
each comes from its own dissolution worksheet on its own TRF, released
independently. So the two profiles arrive here as recorded inputs, one row per
time-point, and the worksheet's job is the comparison arithmetic and the validity
rules around it. See the note on cross-test linkage at the bottom.

## The arithmetic *is* in the source sheet

The spec recorded f1/f2 as absent from the workbook and needing a lab decision on
convention. Re-reading the raw dump, they are present — just off to the right of
the printed area, in the `AA`/`AB`/`AE`/`AH`/`AK`/`AL` block, spelled out one step
per cell:

    AA36 = IF(Z36-Y36>0, Z36-Y36, 0-(Z36-Y36))     |R − T| per time-point
    AB36 = AA36^2                                   squared difference
    AF31 = COUNT(X36:X51)                           n
    AL31 = SUM(AA36:AA51)                           Σ|R − T|
    AL32 = SUM(Z36:Z51)                             Σ of the denominator column
    AL33 = IF(AL31/AL32*100>0, …, 0-(…))            f1  (absolute value)
    AH35 = SUM(AB36:AB51) ; AH36 = AH35/AF31 ; AH37 = 1+AH36
    AH38 = SQRT(AH37) ; AH41 = 100/AH38 ; AH44 = LOG10(AH41) ; AH50 = 50*AH44

which is exactly the FDA/EMA pair, so no convention had to be chosen:

    f1 = Σ|R(t) − T(t)| / Σ R(t) × 100
    f2 = 50 · log₁₀ { [1 + (1/n) Σ (R(t) − T(t))²]^(−0.5) × 100 }

Reproduced here as one expression per step, matching the sheet's own decomposition
rather than collapsing it, because that is what a reviewer will compare against.

## The R(t)/T(t) headings in the source sheet are swapped

Worth knowing before anyone reconciles this template against the workbook. The
mirror table feeds the column headed `R(t)` from the **test** product's mean row
(`S36 = D25`, the left-hand Test Product block) and the column headed `T(t)` from
the **reference** product's (`U36 = W25`, the right-hand Reference Product block).
The hand-typed comparison block matches: its `R(t)` column reads 7, 21, 39, 56, 84
— the test product's means rounded — and its `T(t)` column reads 9, 23, 41, 58, 89,
the reference product's.

f1 then divides by `SUM(Z…)`, the column headed `T(t)`, which holds the reference
product. So **the sheet's numbers are right and only its labels are wrong**: the
denominator really is Σ reference, per the guideline. Had the labels been taken at
face value and the denominator read as Σ test, that dataset's f1 would come out
6.3 instead of 5.9.

Here the fields are named `ref_*` and `test_*` and labelled with the product they
belong to, so the swap cannot recur. `f1`'s denominator is the reference series,
named as such.

## Validity rules are blocking; the similarity verdict is not

The sheet lists five requirements (B47:C52). Four are conditions on whether an
f1/f2 comparison is *meaningful at all*, and they are blocking:

  1. at least 3 time-points,
  2. the same time-points for both products,
  3. not more than one mean above 85 % dissolved, per product,
  4. %RSD below 20 % at the first time-point and below 10 % thereafter.

Requirement 2 is enforced structurally: one row carries both products' means, so
there is no way to compare a 4 h reference value against a 6 h test value.

`f2 ≥ 50` is deliberately **advisory**. A failing f2 is a real, reportable outcome
— the profiles are not similar — and a blocking criterion would refuse to record
it, which is the one thing a comparison worksheet must always be able to do.

## Excluding a time-point is the analyst's decision, not the template's

Requirement 3 caps the number of >85 % points that may be *included*. Auto-dropping
the surplus would silently change the reportable, so each row carries an `included`
switch and a criterion counts what remains. The analyst decides; the criterion
holds them to the rule; the audit trail records both.

`included` also covers the 0-hour row, which the source sheet keeps in the profile
tables (mean 0, %RSD "−") and leaves out of the comparison block. Entering it and
setting `included` to 0 keeps the worksheet a faithful record of the study without
letting a pair of zeroes flatter Σ|R − T|.

## Rounding

The sheet rounds the profile means to 1 dp and then applies **no** rounding to f1
or f2. "No rounding" is not a reportable precision, so f1 and f2 are rounded to
1 dp here — enough to state a verdict against limits of 15 and 50, and stable
against float artefacts. Flagged in the plan as a lab confirmation: a boundary case
(f2 = 49.96) rounds to 50.0 and would read as a pass, so if the lab reports f2 as
an integer or truncates, this one line changes.

The means themselves are entered as recorded, at 1 dp, not re-rounded to the
integers the source sheet's comparison block was typed with. Rounding a profile to
whole percent moves f2 by around a unit, and the more precise value is also the one
that is traceable to the dissolution worksheet it came from.

## Cross-test linkage — the open item

Both profiles are transcribed. The engine can resolve context from the TRF, the
product, the sample and the session, but it has no way to reference *another test's
released result*, so an automatic link would need a new context source
(`resultOf(...)`) in `WorksheetService`, not a template change. Until then the
transcription is at least fully auditable: the values live in the worksheet, every
edit is in the audit trail, and the reference batch is recorded alongside them.
"""
from scripts.template_definitions._common import SeedTemplate, context_header

#  Nine time-points in the source study; the cap allows a longer profile without
#  a new template, and the minimum is the guideline's three.
_MAX_TIMEPOINTS = 20


def _timepoint_fields() -> list[dict]:
    return [
        {
            "key": "time",
            "kind": "input",
            "label": "Time Point",
            "required": True,
        },
        {
            "key": "included",
            "kind": "input",
            "label": "Included in comparison (1 = yes, 0 = no)",
            #  Included by default: dropping a time-point has to be a visible act.
            "default": 1,
        },
        {
            "key": "ref_mean",
            "kind": "input",
            "label": "Reference product — mean % dissolved, R(t)",
            "unit": "%",
        },
        {
            "key": "ref_rsd",
            "kind": "input",
            "label": "Reference product — %RSD",
            "unit": "%",
        },
        {
            "key": "test_mean",
            "kind": "input",
            "label": "Test product — mean % dissolved, T(t)",
            "unit": "%",
        },
        {
            "key": "test_rsd",
            "kind": "input",
            "label": "Test product — %RSD",
            "unit": "%",
        },
        {
            "key": "abs_diff",
            "kind": "calculated",
            "label": "| R(t) − T(t) |",
            "unit": "%",
            #  Sheet AA36. `abs()` replaces the sheet's IF(d>0, d, 0-d), which is
            #  the same thing written before ABS was to hand. Blank in, blank out:
            #  a half-entered row contributes nothing rather than counting as zero
            #  difference.
            "expression": "if(included > 0, abs(ref_mean - test_mean), blank())",
        },
        {
            "key": "sq_diff",
            "kind": "calculated",
            "label": "[ R(t) − T(t) ]²",
            #  Sheet AB36.
            "expression": "abs_diff ^ 2",
        },
        {
            "key": "ref_in_scope",
            "kind": "calculated",
            "label": "R(t) counted in Σ R(t)",
            "unit": "%",
            #  f1's denominator must cover exactly the time-points the numerator
            #  does, so it is masked by the same condition rather than summing the
            #  whole column.
            "expression": "if(isblank(abs_diff), blank(), ref_mean)",
        },
        {
            "key": "ref_over_85",
            "kind": "calculated",
            "label": "Reference > 85 % (counted)",
            "expression": "if(isblank(abs_diff), 0, if(ref_mean > 85, 1, 0))",
        },
        {
            "key": "test_over_85",
            "kind": "calculated",
            "label": "Test > 85 % (counted)",
            "expression": "if(isblank(abs_diff), 0, if(test_mean > 85, 1, 0))",
        },
        {
            "key": "worst_rsd",
            "kind": "calculated",
            "label": "Worst %RSD of the two products",
            "unit": "%",
            #  The limit applies to both profiles, so the worse of the pair is what
            #  is assessed.
            "expression": "max([ref_rsd, test_rsd])",
        },
        {
            "key": "has_rsd",
            "kind": "calculated",
            "label": "%RSD recorded",
            "expression": "if(isblank(worst_rsd), 0, 1)",
        },
        {
            "key": "rsd_limit",
            "kind": "calculated",
            "label": "Applicable %RSD limit",
            "unit": "%",
            #  20 % applies to the *first time-point with an RSD*, not to row 1.
            #  `sum(prior.has_rsd)` is what makes that robust: a leading 0-hour row
            #  carries no RSD, so the 20 % allowance lands on the first real
            #  time-point instead of being spent on the zero.
            "expression": "if(has_rsd > 0 and sum(prior.has_rsd) = 0, 20, 10)",
        },
        {
            "key": "rsd_breach",
            "kind": "calculated",
            "label": "%RSD outside limit",
            "expression": "if(isblank(worst_rsd), 0, if(worst_rsd > rsd_limit, 1, 0))",
        },
    ]


_TIMEPOINTS_GROUP = {
    "key": "timepoints",
    #  A sequence, not a table: order carries meaning here, and `prior` is what
    #  identifies the first time-point that has an RSD.
    "kind": "sequence",
    "label": "Mean % Dissolved by Time Point",
    "rows": {"min": 1, "max": _MAX_TIMEPOINTS, "default": 9, "labelFrom": "time"},
    "fields": _timepoint_fields(),
}


_COMPARISON_GROUP = {
    "key": "comparison",
    "kind": "singleton",
    "label": "f1 / f2 Comparison",
    "fields": [
        {
            "key": "n_points",
            "kind": "calculated",
            "label": "n (time points compared)",
            #  Sheet AF31. Blank rather than 0 when nothing has been entered:
            #  every criterion below keys off this, and "0 time points" would be
            #  assessed as a failure on a worksheet nobody has filled in yet.
            "expression": (
                "if(count(timepoints.sq_diff) > 0, count(timepoints.sq_diff), blank())"
            ),
        },
        {
            "key": "sum_abs_diff",
            "kind": "calculated",
            "label": "Σ | R(t) − T(t) |",
            "unit": "%",
            #  Sheet AL31. Guarded because `sum` of an empty range is 0 by Excel
            #  semantics, and a bare 0 here reads as "the profiles are identical".
            "expression": "if(isblank(n_points), blank(), sum(timepoints.abs_diff))",
        },
        {
            "key": "sum_ref",
            "kind": "calculated",
            "label": "Σ R(t) — reference product",
            "unit": "%",
            #  Sheet AL32, whose range points at the column the sheet labels T(t)
            #  but fills from the reference product. Named for what it holds.
            "expression": "if(isblank(n_points), blank(), sum(timepoints.ref_in_scope))",
        },
        {
            "key": "sum_sq_diff",
            "kind": "calculated",
            "label": "Σ [ R(t) − T(t) ]²",
            #  Sheet AH35.
            "expression": "if(isblank(n_points), blank(), sum(timepoints.sq_diff))",
        },
        {
            "key": "mean_sq_diff",
            "kind": "calculated",
            "label": "Σ [ R(t) − T(t) ]² / n",
            #  Sheet AH36.
            "expression": "sum_sq_diff / n_points",
        },
        {
            "key": "f1",
            "kind": "calculated",
            "label": "f1 — difference factor",
            #  Sheet AL33. Already non-negative: the numerator is a sum of absolute
            #  differences, so the sheet's sign-flipping IF has nothing to flip.
            "expression": "sum_abs_diff / sum_ref * 100",
            "rounding": {"mode": "round", "digits": 1},
        },
        {
            "key": "f2",
            "kind": "calculated",
            "label": "f2 — similarity factor",
            #  Sheet AH37/38/41/44/50 in one line: 50 · log₁₀(100 / √(1 + Σd²/n)).
            "expression": "50 * log10(100 / sqrt(1 + mean_sq_diff))",
            "rounding": {"mode": "round", "digits": 1},
        },
        {
            "key": "points_over_85",
            "kind": "calculated",
            "label": "Included time points above 85 % (worse product)",
            #  Per product, then the worse of the two — one product carrying two
            #  points above 85 % breaks the rule regardless of the other.
            "expression": (
                "if(isblank(n_points), blank(), "
                "max([sum(timepoints.ref_over_85), sum(timepoints.test_over_85)]))"
            ),
        },
        {
            "key": "rsd_breaches",
            "kind": "calculated",
            "label": "Time points outside the %RSD limit",
            "expression": "if(isblank(n_points), blank(), sum(timepoints.rsd_breach))",
        },
    ],
}


A7_DEFINITION = {
    #  f2 is the number the comparison turns on; f1 is reported alongside it.
    "resultRef": "comparison.f2",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {
                "key": "reference_product",
                "kind": "context",
                "type": "text",
                "label": "Reference (innovator) Product",
                "overridable": True,
            },
            {
                "key": "reference_batch",
                "kind": "context",
                "type": "text",
                "label": "Reference Product Batch No.",
                "overridable": True,
            },
            {
                "key": "reference_trf",
                "kind": "context",
                "type": "text",
                #  Where the reference profile came from. Without it the transcribed
                #  numbers have no provenance, which is the whole weakness of the
                #  manual link.
                "label": "Reference Profile — source TRF / A.R. No.",
                "overridable": True,
            },
            {
                "key": "test_trf",
                "kind": "context",
                "type": "text",
                "label": "Test Profile — source TRF / A.R. No.",
                "overridable": True,
            },
            {
                "key": "time_unit",
                "kind": "context",
                "type": "text",
                "label": "Time Points In",
                "default": "Hr",
                "overridable": True,
            },
            {
                "key": "media",
                "kind": "context",
                "type": "text",
                "label": "Dissolution Media",
                "overridable": True,
            },
            {
                "key": "media_volume",
                "kind": "context",
                "label": "Media Volume (mL)",
                "default": 500,
                "overridable": True,
            },
            {
                "key": "rpm",
                "kind": "context",
                "label": "RPM",
                "default": 75,
                "overridable": True,
            },
            {
                "key": "units_per_profile",
                "kind": "context",
                "label": "Units per Profile",
                #  12 in the source study. Recorded because f2's confidence depends
                #  on it, even though the arithmetic here works on the means.
                "default": 12,
                "overridable": True,
            },
        ],
    ),
    "groups": [_TIMEPOINTS_GROUP, _COMPARISON_GROUP],
    "criteria": [
        {
            "key": "min_timepoints",
            "label": "Time points included in the comparison",
            "target": "comparison.n_points",
            "operator": "gte",
            "limit": 3,
            "severity": "blocking",
            "limitText": "NLT 3",
        },
        {
            "key": "single_point_over_85",
            "label": "Included mean values above 85 % dissolved, per product",
            "target": "comparison.points_over_85",
            "operator": "lte",
            "limit": 1,
            "severity": "blocking",
            "limitText": "NMT 1",
        },
        {
            "key": "profile_precision",
            "label": (
                "Time points outside the %RSD limit "
                "(NMT 20 % at the first, NMT 10 % thereafter)"
            ),
            "target": "comparison.rsd_breaches",
            "operator": "lte",
            "limit": 0,
            "severity": "blocking",
            "limitText": "None",
        },
        {
            "key": "f2_similarity",
            "label": "f2 — similarity factor",
            "target": "comparison.f2",
            "operator": "gte",
            "limit": 50.0,
            #  Advisory on purpose: "not similar" is a result, not an invalid run.
            "severity": "advisory",
            "limitText": "NLT 50 for similar profiles",
        },
        {
            "key": "f1_difference",
            "label": "f1 — difference factor",
            "target": "comparison.f1",
            "operator": "lte",
            "limit": 15.0,
            "severity": "advisory",
            "limitText": "NMT 15 for similar profiles",
        },
    ],
}

A7 = SeedTemplate(
    code="TPL-A7-0001",
    name="Dissolution Profile Comparison (f1 / f2)",
    archetype="A7",
    #  Dimensionless: f2 is a similarity factor on a 0–100 scale, not a percentage
    #  of anything.
    result_unit=None,
    test_code="TST-F1F2",
    test_name="Dissolution Profile Comparison (f1/f2)",
    test_type="Quantitative",
    definition=A7_DEFINITION,
)

TEMPLATES = [A7]
