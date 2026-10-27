"""
Parity test for TPL-NITRO-0001 (Nitrosamine Routine analysis sheet) — the
formula-exact rebuild of sheet `Analysis` in
`Test types/Nitrosamine Routine analysis sheet.xls`.

Feeds the sheet's own inputs through the engine and asserts every gold value to
the sheet's full precision:
  * O11 standard conc (ppb)  = 1.0416537600000002
  * D23/D24/D25 standard stats (left block)
  * G23/G24/G25 BKT stats (right block — pools the standard average cell with
    the three filled BKT corrected areas; a reproduced sheet quirk)
  * every Sample Solution "Results in PPM" (O column), TRUNC'd to 4 dp.

Imports NITRO_ROUTINE_DEFINITION directly, so the test is independent of the live
lims.db while pinning the stored formulas.
"""
import pytest

from scripts.template_definitions.nitrosamine_routine import NITRO_ROUTINE_DEFINITION
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

# ── Standard preparation (sheet row 11) ──────────────────────────────
_STANDARD = {
    "name": "N-Nitroso Argatroban", "batch_no": "SRL-3019-20",
    "purity": 96.88, "weight_mg": 2.24,
    "stock_i": 20, "ml_stock_i": 0.15,
    "stock_ii": 10, "ml_stock_ii": 0.1,
    "stock_iii": 10, "ml_stock_iii": 0.64,
    "stock_iv": 10, "ml_stock_iv": 1,
    "standard_solution": 1,
}

#  Standard replicate areas C17:C22 (blank C15 = 0, so corrected == raw).
_STD_AREAS = [76906, 76729, 76472, 76610, 75583, 76136]
#  BKT standard areas F16:F18 filled; F19:F22 blank.
_BKT_AREAS = [78963, 86161, 83853]

#  Sample rows: (name, area M, dilution_3 L). All other columns identical:
#  avg_weight=1, label_claim=100, sample_weight=1, dilution_1=1, ml_1=0.4,
#  dilution_2=20, ml_2=1.
_SAMPLES = [
    ("Sample Solution-1", 8978, 1, 0.0611),
    ("Sample Solution-2", 9528, 1, 0.0649),
    ("Sample Solution-3", 26716, 10, 1.8211),
    ("Sample Solution-4", 23811, 10, 1.6230),
    ("Sample Solution-5", 16510, 10, 1.1254),
    ("Sample Solution-6", 16176, 10, 1.1026),
    ("Sample Solution-7", 18247, 10, 1.2438),
    ("Sample Solution-8", 16557, 10, 1.1286),
    ("Sample Solution-9", 21434, 10, 1.4610),
    ("Sample Solution-10", 21935, 10, 1.4952),
    ("Sample Solution-11", 184523, 1, 1.2578),
    ("Sample Solution-12", 188933, 1, 1.2878),
    ("Sample Solution-13", 211061, 1, 1.4387),
    ("Sample Solution-14", 209086, 1, 1.4252),
    ("Sample Solution-15", 274028, 1, 1.8679),
    ("Sample Solution-16", 275782, 1, 1.8798),
]


def _sample_row(name: str, area: int, dilution_3: int) -> dict:
    return {
        "name": name, "condition": "20-25°C", "avg_weight": 1,
        "label_claim": 100, "sample_weight": 1, "dilution_1": 1, "ml_1": 0.4,
        "dilution_2": 20, "ml_2": 1, "dilution_3": dilution_3, "area": area,
    }


def _evaluate():
    parsed = TemplateDefinition.parse(NITRO_ROUTINE_DEFINITION)
    group_values = {
        "standard": [_STANDARD],
        "blank": [{"blank_area": 0}],
        "std_areas": [{"area": a} for a in _STD_AREAS],
        "bkt": [{"area": a} for a in _BKT_AREAS],
        "samples": [_sample_row(n, a, l) for n, a, l, _gold in _SAMPLES],
    }
    return WorksheetEvaluator(parsed).evaluate({}, group_values)


class TestNitrosamineRoutineParity:
    def test_standard_concentration_O11(self):
        res = _evaluate()
        #  Displayed to 4 dp per the sheet: 1.0416537600000002 -> 1.0417.
        assert res.rows["standard"][0]["std_conc_ppb"] == pytest.approx(1.0417)

    def test_standard_statistics_left_block(self):
        s = _evaluate().rows["std_stats"][0]
        assert s["avg_area"] == pytest.approx(76406)   # D23
        assert s["sd_area"] == pytest.approx(479.69)   # D24 (round 2 dp)
        assert s["rsd_area"] == pytest.approx(0.6)     # D25 (round 1 dp)

    def test_bkt_statistics_right_block_pools_standard_average(self):
        s = _evaluate().rows["bkt_stats"][0]
        assert s["avg_area"] == pytest.approx(81345.75)           # G23
        assert s["sd_area"] == pytest.approx(4455.392341496613)   # G24
        assert s["rsd_area"] == pytest.approx(5.477105247043163)  # G25

    def test_sample_results_ppm(self):
        rows = _evaluate().rows["samples"]
        for i, (name, _area, _l, gold) in enumerate(_SAMPLES):
            assert rows[i]["name"] == name
            assert rows[i]["ppm"] == pytest.approx(gold), name

    def test_reportable_result_first_sample(self):
        res = _evaluate()
        assert res.reportable_result == pytest.approx(0.0611)

    def test_sst_rsd_criterion_present_and_blocking(self):
        parsed = TemplateDefinition.parse(NITRO_ROUTINE_DEFINITION)
        crits = [c for c in parsed.criteria if c.target == "std_stats.rsd_area"]
        assert len(crits) == 1
        c = crits[0]
        assert c.operator.value == "lte"
        assert c.limit == (2.0,)
        assert c.severity.value == "blocking"

    def test_bkt_rsd_not_a_criterion(self):
        parsed = TemplateDefinition.parse(NITRO_ROUTINE_DEFINITION)
        assert not [c for c in parsed.criteria if "bkt" in c.target]
