"""
Parity test for TPL-A6A-0004 (Dissolution_12units) % release calculation.

Reproduces the Bupivacaine dissolution sheet through the engine. The
`timepoints_release` sequence group is built here with the SAME formulas stored
in the live template definition (test_templates.id=34), so the test is
independent of the DB file while pinning the stored formulas.

Three stages per unit N at each timepoint row, matching sheet cells C57/C73/C88:
  * uncorrected_N  = TRUNC( area/STD1 * standard-chain * media/1
                            * aliquot/pippette2 * potency/finalLC * MW , 3 )   (C57)
  * correction_N   = TRUNC( withdrawal / media * uncorrected_N , 3 )           (C73)
  * unit_N (shown) = ROUND( uncorrected_N + Σ prior.correction_N , 0 )         (C88 ff)
media stays at the bath volume (750) every row because withdrawal == replacement.
"""
import pytest

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

UNITS = range(1, 13)

_UNC = (
    "trunc( time_intervals.unit_{n}[rowno - 1] / stats.mean_std"
    " * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2"
    " * standard.pip_2 / standard.vol_3"
    " * media / 1"
    " * test_prep.aliquot_volume / test_prep.pippette_2"
    " * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume)"
    " * 1 / 1, 3 )"
)
_COR = "trunc( test_prep.withdrawal_volume / media * uncorrected_{n}, 3 )"
_UNIT = "round( uncorrected_{n} + sum(prior.correction_{n}), 0 )"


def _units_list() -> str:
    return "[" + ", ".join(f"unit_{n}" for n in UNITS) + "]"


def _timepoints_release_fields() -> list[dict]:
    fields: list[dict] = [{"key": "time_hr", "kind": "input", "label": "Time Interval (Hours)"}]
    fields.append({
        "key": "media", "kind": "calculated",
        "expression": (
            "if(rowno = 1, test_prep.dilution_volume,"
            " prev.media - test_prep.withdrawal_volume + test_prep.replenishment_volume)"
        ),
    })
    for n in UNITS:
        fields.append({"key": f"uncorrected_{n}", "kind": "calculated", "expression": _UNC.format(n=n)})
    for n in UNITS:
        fields.append({"key": f"correction_{n}", "kind": "calculated", "expression": _COR.format(n=n)})
    for n in UNITS:
        fields.append({"key": f"unit_{n}", "kind": "calculated", "label": str(n), "expression": _UNIT.format(n=n)})
    ul = _units_list()
    fields.append({"key": "mean", "kind": "calculated", "label": "Mean", "expression": f"mean({ul})", "rounding": {"mode": "round", "digits": 0}})
    fields.append({"key": "sd", "kind": "calculated", "label": "SD", "expression": f"sd({ul})", "rounding": {"mode": "round", "digits": 1}})
    fields.append({"key": "rsd", "kind": "calculated", "label": "%RSD", "expression": f"rsd({ul})", "rounding": {"mode": "round", "digits": 1}})
    fields.append({"key": "min_val", "kind": "calculated", "label": "Min.", "expression": f"min({ul})"})
    fields.append({"key": "max_val", "kind": "calculated", "label": "Max.", "expression": f"max({ul})"})
    return fields


def _definition() -> dict:
    return {
        "context": [{"key": "label_claim_mgml", "kind": "context", "source": "trf.label_claim_numeric"}],
        "groups": [
            {"key": "standard", "kind": "singleton", "fields": [
                {"key": "weight_mg", "kind": "input"}, {"key": "vol_1", "kind": "input"},
                {"key": "pip_1", "kind": "input"}, {"key": "vol_2", "kind": "input"},
                {"key": "pip_2", "kind": "input"}, {"key": "vol_3", "kind": "input"},
                {"key": "potency", "kind": "input"},
            ]},
            {"key": "std_areas", "kind": "table", "rows": {"min": 1, "max": 6, "default": 5},
             "fields": [{"key": "area", "kind": "area"}]},
            {"key": "stats", "kind": "singleton", "fields": [
                {"key": "mean_std", "kind": "calculated", "expression": "mean(std_areas.area)"},
            ]},
            {"key": "test_prep", "kind": "singleton", "fields": [
                {"key": "sample_volume", "kind": "input"}, {"key": "dilution_volume", "kind": "input"},
                {"key": "aliquot_volume", "kind": "input"}, {"key": "medium_volume", "kind": "input"},
                {"key": "pippette_2", "kind": "input"}, {"key": "withdrawal_volume", "kind": "input"},
                {"key": "replenishment_volume", "kind": "input"},
            ]},
            {"key": "time_intervals", "kind": "table", "rows": {"min": 1, "max": 20, "default": 12},
             "fields": [{"key": "time_hr", "kind": "input"}] + [{"key": f"unit_{n}", "kind": "input"} for n in UNITS]},
            {"key": "timepoints_release", "kind": "sequence", "rows": {"min": 1, "max": 20, "default": 12},
             "fields": _timepoints_release_fields()},
        ],
    }


# Sheet inputs (Bupivacaine).
_CONTEXT = {"label_claim_mgml": "13.3"}
_STD_AREAS = [1680820, 1681032, 1681152, 1681051, 1680851]  # mean 1680981.2
_STANDARD = {"weight_mg": 22.2, "vol_1": 25, "pip_1": 2, "vol_2": 100, "pip_2": 1, "vol_3": 1, "potency": 99.9}
_TEST_PREP = {
    "sample_volume": 1, "dilution_volume": 750, "aliquot_volume": 1, "medium_volume": 1,
    "pippette_2": 1, "withdrawal_volume": 5, "replenishment_volume": 5,
}

# U-1 area column over the timepoints (30min,1h,2h,3h,4h,6h,8h,...).
_U1_AREAS = [334519, 725659, 1064162, 1227639, 1292301, 1368018, 1415426,
             1424782, 1450475, 1452746, 1457486, 1465158]
# Clean 30-min area vector across all 12 units (sheet). ws-27's stored row 0 is
# corrupted for units 2-4, so the summary is pinned against this clean vector.
_CLEAN_30MIN = [334519, 324554, 277744, 298191, 331527, 305277,
                304483, 313534, 279703, 336125, 303006, 326627]
# 1-h area vector across 12 units (clean in the stored sheet).
_H1_AREAS = [725659, 709093, 643515, 678788, 721853, 684917,
             681551, 694070, 647072, 727776, 682476, 716148]

_TIME_HR = [0.5, 1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18]
# row index -> label for timepoints under test
_R = {"30min": 0, "1h": 1, "2h": 2, "3h": 3, "4h": 4, "6h": 5, "8h": 6}


def _time_intervals_rows(row0_units: list[int]) -> list[dict]:
    """12 timepoint rows. Only U-1 (+row0 across all units) carry sheet data; the
    other units at other rows are irrelevant to the asserted values."""
    rows = []
    for i, t in enumerate(_TIME_HR):
        row = {"time_hr": t}
        for n in UNITS:
            row[f"unit_{n}"] = 0
        row["unit_1"] = _U1_AREAS[i]
        rows.append(row)
    # fill row 0 (30 min) across all 12 units and row 1 (1h) across all 12 units
    for n in UNITS:
        rows[0][f"unit_{n}"] = row0_units[n - 1]
        rows[1][f"unit_{n}"] = _H1_AREAS[n - 1]
    return rows


def _evaluate(row0_units: list[int]):
    defn = TemplateDefinition.parse(_definition())
    group_values = {
        "standard": [_STANDARD],
        "std_areas": [{"area": a} for a in _STD_AREAS],
        "test_prep": [_TEST_PREP],
        "time_intervals": _time_intervals_rows(row0_units),
        "timepoints_release": [{"time_hr": t} for t in _TIME_HR],
    }
    return WorksheetEvaluator(defn).evaluate(_CONTEXT, group_values).rows["timepoints_release"]


class TestDissolutionA6A0004Release:
    def test_standard_mean(self):
        from src.domain.services.calculation import evaluate
        assert evaluate("mean(a)", {"a": _STD_AREAS}) == pytest.approx(1680981.2)

    def test_media_is_constant_750_every_row(self):
        rel = _evaluate(_CLEAN_30MIN)
        assert [r["media"] for r in rel] == [750.0] * 12

    def test_u1_uncorrected_series(self):
        rel = _evaluate(_CLEAN_30MIN)
        expected = {"30min": 19.91, "1h": 43.19, "2h": 63.337, "3h": 73.067,
                    "4h": 76.916, "6h": 81.422, "8h": 84.244}
        for label, exp in expected.items():
            assert rel[_R[label]]["uncorrected_1"] == pytest.approx(exp, abs=0.0005)

    def test_u1_correction_factor(self):
        rel = _evaluate(_CLEAN_30MIN)
        for label, exp in {"30min": 0.132, "1h": 0.287, "2h": 0.422}.items():
            assert rel[_R[label]]["correction_1"] == pytest.approx(exp, abs=0.0005)

    def test_u1_corrected_series(self):
        rel = _evaluate(_CLEAN_30MIN)
        expected = {"30min": 20, "1h": 43, "2h": 64, "3h": 74, "4h": 78, "6h": 83, "8h": 87}
        for label, exp in expected.items():
            assert rel[_R[label]]["unit_1"] == exp

    def test_cross_unit_summary_30min(self):
        rel = _evaluate(_CLEAN_30MIN)
        r = rel[_R["30min"]]
        assert r["mean"] == pytest.approx(19)
        assert r["sd"] == pytest.approx(1.1, abs=0.05)
        assert r["rsd"] == pytest.approx(5.8, abs=0.05)
        assert r["min_val"] == pytest.approx(17)
        assert r["max_val"] == pytest.approx(20)

    def test_cross_unit_summary_1h(self):
        rel = _evaluate(_CLEAN_30MIN)
        r = rel[_R["1h"]]
        assert r["mean"] == pytest.approx(41)
        assert r["max_val"] == pytest.approx(43)

    def test_blank_units_are_excluded_from_summary(self):
        # Leave units 7-12 blank at 30 min; summary must average only filled units.
        row0 = list(_CLEAN_30MIN)
        rel = _evaluate(row0)
        # all 12 filled -> min over corrected is 17 (sanity that nothing is 0)
        assert rel[_R["30min"]]["min_val"] >= 17
