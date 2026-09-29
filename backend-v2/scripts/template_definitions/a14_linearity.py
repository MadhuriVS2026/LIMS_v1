"""
A14 — linearity / system qualification across multiple components.

Source: `Lipid content_Linearity _CAD_ Doxo.xlsx` (three lipid components of a
liposomal product, quantified by charged-aerosol detection).

This is the one archetype that is not a sample test. It qualifies the *method*:
three linearity levels are prepared from one stock, each component is regressed
against its own concentration series, and the worksheet passes or fails on two
stated criteria — replicate precision at 100 % and correlation across levels. It
is modelled as a template anyway because the arithmetic, the audit trail and the
approval route are the same as any other worksheet, and a validation number that
lives in a spreadsheet is a validation number nobody can trace.

Three structural points:

* **Levels are the row axis, components are columns.** The regression runs down
  the levels for each component, so components have to be columns — the same
  constraint as dissolution. Three components, fixed, matching the workbook.
  A method with a different component set is a new template, which is the right
  GxP outcome rather than a template that quietly accepts any shape.

* **One shared first dilution.** All three components are weighed into the *same*
  flask: the sheet writes `$D$12/$E$11` and `$D$13/$E$11`, i.e. component 2 and 3
  weights over component 1's dilution volume. That is not a fill error — it is
  one stock solution — so `dilution_1` sits on the standards group once instead of
  once per component.

* **The 0 % level is recorded but not regressed.** The sheet lists
  "Linearity level-4 (0%)" with zero concentration and zero area, then fits
  `CORREL(D27:D29, E27:E29)` — three points, excluding it. Rather than a hidden
  row-count assumption, each component carries masked `x`/`y` columns that go
  blank when `nominal_pct` is zero. Blank pairs are dropped from the regression,
  so the zero level stays visible on the worksheet and out of the line.

**Component 3 is a two-peak sum.** HSPC elutes as SPC-1 and SPC-2 and the sheet
reports their rounded sum. Every component here carries an optional second peak
defaulting to zero, so the sum is uniform and a single-peak component needs no
different expression.

## Deliberately not reproduced

Each component block carries three hardcoded cells labelled `a`, `b`, `c`
(e.g. 466.723 / 378.5945 / 0.0007). They are not derived anywhere in the workbook
and do not reconcile with a least-squares fit of the three plotted points —
recomputing the cholesterol line from its own data gives a slope of 386.25, not
378.59 — so they are quadratic coefficients pasted in from the chromatography
data system. They are omitted rather than carried as unexplained inputs. The
correlation the acceptance criterion actually uses *is* computed here, from the
worksheet's own numbers.
"""
from scripts.template_definitions._common import SeedTemplate, context_header

#  Three components, matching the workbook's lipid panel.
_COMPONENTS = 3
_COMPONENT_RANGE = range(1, _COMPONENTS + 1)


def _series(prefix: str) -> str:
    return "[" + ", ".join(f"{prefix}_{n}" for n in _COMPONENT_RANGE) + "]"


# ─────────────────────────────────────────────────────────────────────
#  Standard stock
# ─────────────────────────────────────────────────────────────────────


def _standard_fields() -> list[dict]:
    fields: list[dict] = [
        {
            "key": "dilution_1",
            "kind": "input",
            "label": "Dilution I (shared)",
            "unit": "mL",
            "required": True,
            #  Shared across all three components: they are weighed into one flask.
            "default": 100,
        },
    ]
    for n in _COMPONENT_RANGE:
        fields.extend(
            [
                {
                    "key": f"name_{n}",
                    "kind": "input",
                    "type": "text",
                    "label": f"Component {n} Name",
                },
                {
                    "key": f"lot_{n}",
                    "kind": "input",
                    "type": "text",
                    "label": f"Component {n} Lot / WS No.",
                },
                {
                    "key": f"purity_{n}",
                    "kind": "input",
                    "label": f"Component {n} Assigned Content",
                    "unit": "%",
                    "default": 100,
                },
                {
                    "key": f"weight_mg_{n}",
                    "kind": "input",
                    "label": f"Component {n} Weight",
                    "unit": "mg",
                },
                {
                    "key": f"label_claim_{n}",
                    "kind": "input",
                    "label": f"Component {n} Label Claim",
                    #  Recorded for the report; the linearity arithmetic does not
                    #  use it, since linearity is assessed against prepared
                    #  concentration rather than against claim.
                    "unit": "mg/mL",
                },
            ]
        )
    return fields


_STANDARDS_GROUP = {
    "key": "std",
    "kind": "singleton",
    "label": "Linearity Standard Stock Solution",
    "fields": _standard_fields(),
}


# ─────────────────────────────────────────────────────────────────────
#  Linearity levels
# ─────────────────────────────────────────────────────────────────────


def _level_fields() -> list[dict]:
    fields: list[dict] = [
        {"key": "level", "kind": "input", "type": "text", "label": "Linearity Level"},
        {
            "key": "nominal_pct",
            "kind": "input",
            "label": "Nominal",
            "unit": "%",
            #  Drives regression membership: a 0 % level is recorded but excluded.
            "required": True,
        },
        {
            "key": "stock_ml",
            "kind": "input",
            "label": "Stock Taken",
            "unit": "mL",
            "required": True,
        },
        {"key": "dil_ml", "kind": "input", "label": "Diluted to", "unit": "mL", "required": True},
    ]

    for n in _COMPONENT_RANGE:
        fields.append(
            {
                "key": f"conc_{n}",
                "kind": "calculated",
                "label": f"Conc. — Component {n}",
                "unit": "mg/mL",
                #  weight / shared dilution × aliquot / diluted-to × assigned content.
                "expression": (
                    f"std.weight_mg_{n} / std.dilution_1 * stock_ml / dil_ml "
                    f"* std.purity_{n} / 100"
                ),
                #  3 dp, and the regression is fitted on the rounded value —
                #  matching the sheet, where ROUND sits inside the CORREL range.
                "rounding": {"mode": "round", "digits": 3},
            }
        )
    for n in _COMPONENT_RANGE:
        fields.append(
            {
                "key": f"area_{n}",
                "kind": "area",
                "label": f"Area — Component {n}",
            }
        )
    for n in _COMPONENT_RANGE:
        fields.append(
            {
                "key": f"area_b_{n}",
                "kind": "area",
                "label": f"Area — Component {n} (2nd peak)",
                #  Zero, not blank: a single-peak component must not blank out its
                #  own total by adding an empty second peak.
                "default": 0,
            }
        )
    for n in _COMPONENT_RANGE:
        fields.append(
            {
                "key": f"total_area_{n}",
                "kind": "calculated",
                "label": f"Total Area — Component {n}",
                "expression": f"area_{n} + area_b_{n}",
                "rounding": {"mode": "round", "digits": 3},
            }
        )
    for n in _COMPONENT_RANGE:
        fields.extend(
            [
                {
                    "key": f"x_{n}",
                    "kind": "calculated",
                    "label": f"Regression x — Component {n}",
                    #  Masked pair: blanking both sides keeps the series aligned
                    #  when a level is excluded.
                    "expression": f"if(nominal_pct > 0, conc_{n}, blank())",
                },
                {
                    "key": f"y_{n}",
                    "kind": "calculated",
                    "label": f"Regression y — Component {n}",
                    "expression": f"if(nominal_pct > 0, total_area_{n}, blank())",
                },
            ]
        )
    return fields


_LEVELS_GROUP = {
    "key": "levels",
    "kind": "table",
    "label": "Linearity Levels",
    #  Three levels plus the recorded 0 % point; more levels are allowed for a
    #  five- or seven-point curve.
    "rows": {"min": 2, "max": 9, "default": 4, "labelFrom": "level"},
    "fields": _level_fields(),
}


# ─────────────────────────────────────────────────────────────────────
#  Regression
# ─────────────────────────────────────────────────────────────────────


def _regression_fields() -> list[dict]:
    fields: list[dict] = []
    for n in _COMPONENT_RANGE:
        fields.extend(
            [
                {
                    "key": f"slope_{n}",
                    "kind": "calculated",
                    "label": f"Slope — Component {n}",
                    "expression": f"slope(levels.y_{n}, levels.x_{n})",
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "key": f"intercept_{n}",
                    "kind": "calculated",
                    "label": f"Intercept — Component {n}",
                    "expression": f"intercept(levels.y_{n}, levels.x_{n})",
                    "rounding": {"mode": "round", "digits": 4},
                },
                {
                    "key": f"correlation_{n}",
                    "kind": "calculated",
                    "label": f"Correlation (R) — Component {n}",
                    "expression": f"correl(levels.y_{n}, levels.x_{n})",
                    #  5 dp. The sheet uses 6 for the first component and 5 for the
                    #  other two; 5 is enough for a 0.99 limit and is applied
                    #  uniformly rather than reproducing the inconsistency.
                    "rounding": {"mode": "round", "digits": 5},
                },
                {
                    "key": f"r_squared_{n}",
                    "kind": "calculated",
                    "label": f"R² — Component {n}",
                    "expression": f"correl(levels.y_{n}, levels.x_{n}) ^ 2",
                    "rounding": {"mode": "round", "digits": 5},
                },
            ]
        )
    fields.append(
        {
            "key": "min_correlation",
            "kind": "calculated",
            "label": "Poorest Correlation",
            #  The single number the qualification turns on: every component has
            #  to clear the limit, so the worst one is the reportable.
            "expression": f"min({_series('correlation')})",
            "rounding": {"mode": "round", "digits": 5},
        }
    )
    return fields


_REGRESSION_GROUP = {
    "key": "regression",
    "kind": "singleton",
    "label": "Regression Summary",
    "fields": _regression_fields(),
}


# ─────────────────────────────────────────────────────────────────────
#  Replicate precision at the 100 % level
# ─────────────────────────────────────────────────────────────────────


def _replicate_fields() -> list[dict]:
    fields: list[dict] = [
        {"key": "injection", "kind": "input", "type": "text", "label": "Injection"},
    ]
    for n in _COMPONENT_RANGE:
        fields.append({"key": f"area_{n}", "kind": "area", "label": f"Area — Component {n}"})
    for n in _COMPONENT_RANGE:
        fields.append(
            {
                "key": f"area_b_{n}",
                "kind": "area",
                "label": f"Area — Component {n} (2nd peak)",
                "default": 0,
            }
        )
    for n in _COMPONENT_RANGE:
        fields.append(
            {
                "key": f"total_{n}",
                "kind": "calculated",
                "label": f"Total Area — Component {n}",
                "expression": f"area_{n} + area_b_{n}",
                "rounding": {"mode": "round", "digits": 3},
            }
        )
    return fields


_REPLICATES_GROUP = {
    "key": "replicates",
    "kind": "table",
    "label": "Replicate Injections — Linearity Level 2 (100 %)",
    "rows": {"min": 2, "max": 10, "default": 5, "labelFrom": "injection"},
    "fields": _replicate_fields(),
}


def _precision_fields() -> list[dict]:
    fields: list[dict] = []
    for n in _COMPONENT_RANGE:
        fields.extend(
            [
                {
                    "key": f"mean_{n}",
                    "kind": "calculated",
                    "label": f"Mean — Component {n}",
                    "expression": f"mean(replicates.total_{n})",
                },
                {
                    "key": f"sd_{n}",
                    "kind": "calculated",
                    "label": f"SD — Component {n}",
                    "expression": f"sd(replicates.total_{n})",
                    "rounding": {"mode": "round", "digits": 5},
                },
                {
                    "key": f"rsd_{n}",
                    "kind": "calculated",
                    "label": f"%RSD — Component {n}",
                    "unit": "%",
                    #  sd/mean, using the already-rounded SD as the sheet does
                    #  (ROUND(STDEV,5) then ROUND(sd/mean*100,2)).
                    "expression": f"sd_{n} / mean_{n} * 100",
                    "rounding": {"mode": "round", "digits": 2},
                },
            ]
        )
    fields.append(
        {
            "key": "max_rsd",
            "kind": "calculated",
            "label": "Worst %RSD",
            "unit": "%",
            "expression": f"max({_series('rsd')})",
            "rounding": {"mode": "round", "digits": 2},
        }
    )
    return fields


_PRECISION_GROUP = {
    "key": "precision",
    "kind": "singleton",
    "label": "Replicate Precision",
    "fields": _precision_fields(),
}


A14_DEFINITION = {
    #  The qualification verdict, not a sample content.
    "resultRef": "regression.min_correlation",
    "context": context_header(
        label_claim=False,
        avg_weight=False,
        extra=[
            {
                "key": "detector",
                "kind": "context",
                "type": "text",
                "label": "Detector",
                "default": "CAD",
                "overridable": True,
            },
            {
                "key": "blank_interference",
                "kind": "context",
                "type": "text",
                "label": "Blank Interference",
                #  Criterion 1 on the sheet is an observation, not a number.
                "default": "Not observed",
                "overridable": True,
            },
        ],
    ),
    "groups": [
        _STANDARDS_GROUP,
        _REPLICATES_GROUP,
        _PRECISION_GROUP,
        _LEVELS_GROUP,
        _REGRESSION_GROUP,
    ],
    "criteria": [
        {
            "key": "replicate_precision",
            "label": "%RSD of five replicate injections at the 100 % level",
            "target": "precision.max_rsd",
            "operator": "lte",
            "limit": 10.0,
            "severity": "blocking",
            "limitText": "NMT 10.0 %",
        },
        {
            "key": "level_correlation",
            "label": "Correlation coefficient (R) across linearity levels",
            "target": "regression.min_correlation",
            "operator": "gte",
            "limit": 0.99,
            "severity": "blocking",
            "limitText": "NLT 0.99",
        },
    ],
}

A14 = SeedTemplate(
    code="TPL-A14-0001",
    name="Linearity Qualification — Multi-Component (CAD)",
    archetype="A14",
    #  Dimensionless: the reportable is a correlation coefficient.
    result_unit=None,
    test_code="TST-LINQ",
    test_name="Linearity Qualification",
    test_type="Quantitative",
    definition=A14_DEFINITION,
)

TEMPLATES = [A14]
