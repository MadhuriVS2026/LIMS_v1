"""
Parity test for TPL-A6A-0005 (Dissolution-Leuprolide-microsphere) — the
formula-exact rebuild of sheet `ZEG0572A` in
`Test types/Dissolution sheet_Leuprolide_Microsphere.xlsx`.

Feeds the sheet's own inputs through the engine and asserts every gold value from
`.agents/tasks/a6a-leuprolide-microsphere/trace.md` §5 to the sheet's full
precision (no stored rounding). The carry-critical assertions — C40 = J40 (no
carry on the first timepoint), C46 = J46 + L46 with L46 = K40, and C52 = J52 + L52
with L52 = K46 + L46 — fail loudly if the cumulative chain ever collapses to 0.

Imports the module's A6A_LEUP_DEFINITION directly, so the test is independent of
the live lims.db while pinning the stored formulas.
"""
import pytest

from scripts.template_definitions.a6a_leuprolide_microsphere import A6A_LEUP_DEFINITION
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

# ── Sheet inputs (ZEG0572A) ──────────────────────────────────────────
_STD_AREAS = [1108135, 1107954, 1107711, 1107762, 1109456]      # B22:B26
_BKT_AREAS = [1101413, 1101192, 1096506, 1094608, 1092402]      # D22:D26
_STANDARD = {
    "name": "Leuprolide Acetate", "potency": 97.87, "mw_base": 1, "mw_salt": 1,
    "weight_mg": 20.11, "dilution_1": 50, "volume_1": 5, "dilution_2": 25,
}
_PARAMS = {"volume_ml": 50, "apparatus": "Bottle Rotating", "rpm": 6,
           "temperature": "50", "media": "0.5% W/V PVA IN WATER pH 5.50"}
#  Pellet weights: only 3 filled (F22=49.17, F23=50.56, F24=49.77), rest blank.
_WEIGHTS = [
    {"unit_label": "Unit-1", "weight": 49.17},
    {"unit_label": "Unit-2", "weight": 50.56},
    {"unit_label": "Unit-3", "weight": 49.77},
    {"unit_label": "Unit-4"},
    {"unit_label": "Unit-5"},
    {"unit_label": "Unit-6"},
]
_PREP = {"avg_weight": 100, "label_claim": 9.8, "pipette_vol": 1, "vf_vol": 1,
         "withdraw_replace": 1}

#  Timepoint blocks (sheet §5): units 1-3 filled at 1/24/48 Hr.
_TIMEPOINTS = [
    {"time_hr": "1 Hr",  "area_1": 203438, "area_2": 231282, "area_3": 174411},
    {"time_hr": "24 Hr", "area_1": 681560},
    {"time_hr": "48 Hr", "area_1": 1013055},
]


def _evaluate():
    parsed = TemplateDefinition.parse(A6A_LEUP_DEFINITION)
    group_values = {
        "standard": [_STANDARD],
        "std_areas": [{"area": a} for a in _STD_AREAS],
        "bkt": [{"area": a} for a in _BKT_AREAS],
        "params": [_PARAMS],
        "weights": _WEIGHTS,
        "prep": [_PREP],
        "timepoints_release": _TIMEPOINTS,
    }
    return WorksheetEvaluator(parsed).evaluate({}, group_values)


class TestA6A0005LeuprolideParity:
    def test_standard_concentration_I19(self):
        res = _evaluate()
        assert res.rows["standard"][0]["conc_ppm"] == pytest.approx(78.726628)

    def test_standard_area_statistics(self):
        s = _evaluate().rows["std_stats"][0]
        assert s["mean_std"] == pytest.approx(1108203.6)        # B27
        assert s["sd_std"] == pytest.approx(719.9265934801964)  # B28
        assert s["rsd_std"] == pytest.approx(0.06496338700579897)  # B29
        assert s["mean_bkt"] == pytest.approx(1102713.9)        # D27 (pooled 10)
        assert s["sd_bkt"] == pytest.approx(6388.745720231615)  # D28
        assert s["rsd_bkt"] == pytest.approx(0.5793656650407342)  # D29

    def test_pellet_weight_statistics_stdev_includes_mean(self):
        w = _evaluate().rows["weight_stats"][0]
        assert w["mean_wt"] == pytest.approx(49.833333333333336)  # F28
        assert w["sd_wt"] == pytest.approx(0.569229498728081)     # F29 (n=4, incl mean)
        assert w["rsd_wt"] == pytest.approx(1.1422665526316007)   # F30

    def test_1hr_block_no_carry_C_equals_J(self):
        rel = _evaluate().rows["timepoints_release"]
        r0 = rel[0]
        #  C40 = J40 = 14.996085 from B40 = 203438; no carry on the first timepoint.
        assert r0["unit_1"] == pytest.approx(14.996084937889453)  # C40
        assert r0["unit_2"] == pytest.approx(16.579857409503386)  # C41
        assert r0["unit_3"] == pytest.approx(12.701419313269414)  # C42
        assert r0["mean"] == pytest.approx(14.759120553554084)    # D40
        assert r0["min_val"] == pytest.approx(12.701419313269414)  # E40
        assert r0["max_val"] == pytest.approx(16.579857409503386)  # F40
        assert r0["rsd"] == pytest.approx(13.212490048191508)     # G40

    def test_24hr_block_first_cumulative_add_back(self):
        rel = _evaluate().rows["timepoints_release"]
        #  C46 = J46 + L46, L46 = K40. B46 = 681560 -> J46 = 50.240032.
        assert rel[1]["unit_1"] == pytest.approx(50.53995379830622)  # C46

    def test_48hr_block_running_carry(self):
        rel = _evaluate().rows["timepoints_release"]
        #  C52 = J52 + L52, L52 = K46 + L46. B52 = 1013055 -> J52 = 74.675620.
        assert rel[2]["unit_1"] == pytest.approx(75.98034256289799)  # C52

    def test_sst_rsd_criterion_present(self):
        parsed = TemplateDefinition.parse(A6A_LEUP_DEFINITION)
        crits = [c for c in parsed.criteria if c.target == "std_stats.rsd_std"]
        assert len(crits) == 1
        c = crits[0]
        assert c.operator.value == "lte"
        assert c.limit == (2.0,)
        assert c.severity.value == "blocking"
