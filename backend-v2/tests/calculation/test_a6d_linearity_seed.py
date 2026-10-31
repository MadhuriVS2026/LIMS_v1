"""
Per-row `rows.seed` capability of the MERGED "Calibration Standards" table
(TPL-A6D-0002, the single `linearity` sequence group).

After the calibration/linearity merge, `linearity` carries the twelve
user-visible columns (dilution inputs + Theoretical/Observed/%Recovery) plus two
hidden regression-scoping masks, and its seed opens with six calibration-standard
rows carrying their dilution inputs and three QC rows carrying label + pct only.

Three proofs, matching the design's runtime-proof plan:

  * **parse** — the `sequence` group carrying `rows.seed` round-trips through
    `TemplateDefinition.parse`: the six standard rows keep their dilution inputs,
    the three QC rows name only `calibration_curve`/`concentration_pct`, and a
    blank `evaluate({}, {})` reports no blocking failure.
  * **create_worksheet** — the seeded rows land verbatim in a freshly created
    worksheet's `group_values`, through the real `WorksheetService`.
  * **regression** — a fit over the six seeded standard rows (with the user's six
    Area Response values) reproduces slope 53797.61 / intercept 28844.87 /
    correl 0.9999, over the six standards only.
"""
import pytest

from src.application.services.worksheet_service import WorksheetService
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.expression import evaluate
from src.domain.services.calculation.template_schema import TemplateDefinition
from tests.calculation.conftest import seed_test, seed_trf_with_line, user
from tests.calculation.test_worksheet_service import _seed_active_template, _service

#  The six standards carry their dilution inputs; the three QC rows carry only
#  label + concentration (no dilution values in the user's data set).
SEED_ROWS = [
    {"calibration_curve": "Calibration standard-1", "concentration_pct": 1,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 5, "ml_b": 50, "ml_taken": 1, "diluted_to_ml_2": 50},
    {"calibration_curve": "Calibration standard-2", "concentration_pct": 5,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 5, "ml_b": 50, "ml_taken": 5, "diluted_to_ml_2": 50},
    {"calibration_curve": "Calibration standard-3", "concentration_pct": 15,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 5, "ml_b": 50, "ml_taken": 15, "diluted_to_ml_2": 50},
    {"calibration_curve": "Calibration standard-4", "concentration_pct": 30,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 1, "ml_b": 1, "ml_taken": 3, "diluted_to_ml_2": 50},
    {"calibration_curve": "Calibration standard-5", "concentration_pct": 40,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 1, "ml_b": 1, "ml_taken": 4, "diluted_to_ml_2": 50},
    {"calibration_curve": "Calibration standard-6", "concentration_pct": 60,
     "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 1, "ml_b": 1, "ml_taken": 6, "diluted_to_ml_2": 50},
    {"calibration_curve": "LQC", "concentration_pct": 1},
    {"calibration_curve": "MQC", "concentration_pct": 15},
    {"calibration_curve": "HQC", "concentration_pct": 30},
]

STANDARD_KEYS = {
    "calibration_curve", "concentration_pct", "std_weight_mg", "diluted_to_ml_1",
    "ml_a", "ml_b", "ml_taken", "diluted_to_ml_2",
}
QC_KEYS = {"calibration_curve", "concentration_pct"}

_IS_STANDARD = " or ".join(
    f'(calibration_curve = "Calibration standard-{n}")' for n in range(1, 7)
)

LINEARITY_GROUP = {
    "key": "linearity",
    "kind": "sequence",
    "label": "Calibration Standards",
    "rows": {
        "min": 9,
        "max": 15,
        "default": 9,
        "labelFrom": "calibration_curve",
        "seed": SEED_ROWS,
    },
    "fields": [
        {"key": "calibration_curve", "kind": "input", "type": "text", "label": "Calibration curve"},
        {"key": "concentration_pct", "kind": "input", "type": "number", "label": "Concentration", "unit": "%"},
        {"key": "std_weight_mg", "kind": "input", "type": "number", "label": "Standard Weight", "unit": "mg"},
        {"key": "diluted_to_ml_1", "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL"},
        {"key": "ml_a", "kind": "input", "type": "number", "label": "mL", "unit": "mL"},
        {"key": "ml_b", "kind": "input", "type": "number", "label": "mL", "unit": "mL"},
        {"key": "ml_taken", "kind": "input", "type": "number", "label": "mL taken", "unit": "mL"},
        {"key": "diluted_to_ml_2", "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL"},
        {"key": "theoretical_ppm", "kind": "calculated", "type": "number",
         "label": "Theoretical concentration", "unit": "ppm",
         "expression": "std_weight_mg / diluted_to_ml_1 * ml_a / ml_b "
                       "* ml_taken / diluted_to_ml_2 * potency / 100 * 1000"},
        {"key": "area", "kind": "area", "type": "number", "label": "Area Response", "unit": "µV·s"},
        {"key": "observed_ppm", "kind": "calculated", "type": "number",
         "label": "Observed concentration", "unit": "ppm",
         "expression": "(area - curve.curve_intercept) / curve.curve_slope"},
        {"key": "recovery_pct", "kind": "calculated", "type": "number",
         "label": "% Recovery", "unit": "%",
         "expression": "observed_ppm / theoretical_ppm * 100",
         "rounding": {"mode": "round", "digits": 2}},
        {"key": "is_standard", "kind": "calculated", "type": "boolean",
         "label": "Is calibration standard", "expression": _IS_STANDARD},
        {"key": "is_qc", "kind": "calculated", "type": "boolean",
         "label": "Is bracketing QC", "expression": "not is_standard"},
    ],
}

#  A minimal, self-contained template that exercises only the seed capability.
#  A singleton result group keeps `resultRef` valid without pulling in the full
#  A6D flux chain, which is irrelevant to what these tests prove.
DEFINITION = {
    "resultRef": "result.value",
    "context": [{"key": "potency", "kind": "context", "unit": "%", "default": 99.67, "overridable": True}],
    "groups": [
        LINEARITY_GROUP,
        {
            "key": "result",
            "kind": "singleton",
            "label": "Result",
            "fields": [{"key": "value", "kind": "input", "type": "number", "label": "Value"}],
        },
    ],
    "criteria": [],
}


def test_rows_seed_round_trips_through_parse():
    parsed = TemplateDefinition.parse(DEFINITION)
    group = parsed.group("linearity")
    assert group is not None

    seed = group.rows.seed
    assert len(seed) == 9

    pairs = [(r["calibration_curve"], r["concentration_pct"]) for r in seed]
    assert pairs == [
        ("Calibration standard-1", 1),
        ("Calibration standard-2", 5),
        ("Calibration standard-3", 15),
        ("Calibration standard-4", 30),
        ("Calibration standard-5", 40),
        ("Calibration standard-6", 60),
        ("LQC", 1),
        ("MQC", 15),
        ("HQC", 30),
    ]

    #  Six standards carry their dilution inputs; three QC rows name label+pct only.
    for row in seed[:6]:
        assert set(row) == STANDARD_KEYS, row
        assert row["std_weight_mg"] == 89.73
    for row in seed[6:]:
        assert set(row) == QC_KEYS, row

    #  A blank sheet still evaluates with no blocking failure.
    result = WorksheetEvaluator(parsed).evaluate({}, {})
    assert result.has_blocking_failure is False


def test_seeded_standards_reproduce_the_regression():
    """A fit over the six seeded standard rows (with the user's six areas)
    reproduces slope 53797.61 / intercept 28844.87 / correl 0.9999, over the six
    standards only even with QC rows present."""
    parsed = TemplateDefinition.parse(DEFINITION)
    areas = [200754, 974514, 2922207, 5786622, 7842177, 11507227]
    rows = []
    for seed, area in zip(SEED_ROWS[:6], areas):
        row = dict(seed)
        row["area"] = area
        rows.append(row)
    rows.extend(dict(seed) for seed in SEED_ROWS[6:])

    result = WorksheetEvaluator(parsed).evaluate({"potency": 99.67}, {"linearity": rows})
    lin = result.rows["linearity"]

    theo = [lin[i]["theoretical_ppm"] for i in range(6)]
    flags = [lin[i]["is_standard"] for i in range(9)]
    area_col = [lin[i].get("area") for i in range(9)]
    theo_col = [lin[i].get("theoretical_ppm") for i in range(9)]

    assert flags == [True] * 6 + [False] * 3
    assert evaluate("count(where(a, m))", {"a": area_col, "m": flags}) == 6.0

    slope = evaluate("slope(where(y, m), where(x, m))", {"y": area_col, "x": theo_col, "m": flags})
    intercept = evaluate("intercept(where(y, m), where(x, m))", {"y": area_col, "x": theo_col, "m": flags})
    correl = evaluate("correl(where(y, m), where(x, m))", {"y": area_col, "x": theo_col, "m": flags})
    assert round(slope, 2) == 53797.61
    assert round(intercept, 2) == 28844.87
    assert round(correl, 4) == 0.9999

    expected_theo = [3.57735564, 17.8867782, 53.6603346, 107.3206692, 143.0942256, 214.6413384]
    for got, want in zip(theo, expected_theo):
        assert got == pytest.approx(want, abs=1e-3)


def test_unknown_seed_field_is_rejected():
    from src.domain.services.calculation.template_schema import TemplateSchemaError

    broken = {
        **DEFINITION,
        "groups": [
            {
                **LINEARITY_GROUP,
                "rows": {
                    **LINEARITY_GROUP["rows"],
                    "seed": [{"calibration_curve": "x", "not_a_field": 1}],
                },
            },
            DEFINITION["groups"][1],
        ],
    }
    with pytest.raises(TemplateSchemaError) as exc:
        TemplateDefinition.parse(broken)
    assert "not_a_field" in str(exc.value)


@pytest.mark.asyncio
async def test_seeded_rows_land_in_a_created_worksheet(db_session):
    test = await seed_test(db_session)
    trf, line = await seed_trf_with_line(db_session, status="InProgress", test=test)
    trf.analyst_accepted_by = "analyst"
    await db_session.flush()

    template = await _seed_active_template(db_session, test.id, definition=DEFINITION)
    svc: WorksheetService = _service(db_session)
    worksheet = await svc.create_worksheet(line.id, template.id, user("analyst", "Analyst"))

    rows = worksheet.group_values["linearity"]
    assert len(rows) == 9

    pairs = [(r["calibration_curve"], r["concentration_pct"]) for r in rows]
    assert pairs == [
        ("Calibration standard-1", 1),
        ("Calibration standard-2", 5),
        ("Calibration standard-3", 15),
        ("Calibration standard-4", 30),
        ("Calibration standard-5", 40),
        ("Calibration standard-6", 60),
        ("LQC", 1),
        ("MQC", 15),
        ("HQC", 30),
    ]
    #  Standard rows carry dilution inputs; QC rows carry label+pct only.
    for row in rows[:6]:
        assert set(row) == STANDARD_KEYS
    for row in rows[6:]:
        assert set(row) == QC_KEYS
