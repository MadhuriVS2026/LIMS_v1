"""
Parity test for TPL-A1-0003 "Assay for finished product mg/ml".

Source workbook: `Bupivacaine Assay mg ml & Percentage.xlsx`, sheet '1'
(cell + formula dump in `_dumps/Bupivacaine Assay mg ml _ Percentage.txt`).

This template clones the live TPL-A1-0002 "Assay for Finished Product" and adds
two per-sample columns from the sheet: **Assay (mg/mL)** (column Q) and its mean
**Mean (mg/mL)** (column R). This test pins the new template against the sheet's
own gold values AND confirms the base `% Assay` / `% Mean Assay` logic is
unchanged.

Every expected value below is derived by hand from the sheet formula in the
comment above it (not copied from a prior run), so a regression fails.

Sheet constants (standard row 14, '$'-anchored in every formula):
  C14 Wt 50.59 | D14/E14/F14/G14/H14 chain 100/10/50/1/1 | I14/J14 MW 1/1
  K14 Potency 99.64 | B24 = AVERAGE(B18:B22) of the five STD areas.
Sample context: L.C. (G) = 13.3, Avg Weight (F) = 1.005, Vol/Pip/Vol 100/1/1.
"""
import pytest

from scripts.template_definitions import SEED_TEMPLATES
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

BY_CODE = {item.code: item for item in SEED_TEMPLATES}
CODE = "TPL-A1-0003"


def evaluator() -> WorksheetEvaluator:
    return WorksheetEvaluator(TemplateDefinition.parse(BY_CODE[CODE].definition))


# ── Fixture (sheet standard row 14 + STD areas B18:B22) ──────────────

CONTEXT = {"label_claim": 13.3, "avg_weight": 1.005}
STANDARD = [{
    "name": "Bupivacaine", "weight_mg": 50.59, "vol_1": 100.0, "pip_1": 10.0,
    "vol_2": 50.0, "pip_2": 1.0, "vol_3": 1.0,
    "mw_base": 1.0, "mw_salt": 1.0, "potency": 99.64,
}]
STD_AREAS = [
    {"area": 2387569.0}, {"area": 2388066.0}, {"area": 2392223.0},
    {"area": 2389532.0}, {"area": 2382677.0},
]
#  Set-1 (sheet row 31) + Set-2 (sheet row 33). Area-2 blank ⇒ N = Area-1.
TWO_ROW = {
    "standard": STANDARD,
    "std_areas": STD_AREAS,
    "samples": [
        {"prep_ref": "EP20_117-307 Set-1", "sample_weight": 0.7621, "s_vol_1": 100.0,
         "s_pip_1": 1.0, "s_vol_2": 1.0, "s_pip_2": 1.0, "s_vol_3": 1.0, "area_1": 2496042.0},
        {"prep_ref": "EP20_117-307 Set-2", "sample_weight": 0.7469, "s_vol_1": 100.0,
         "s_pip_1": 1.0, "s_vol_2": 1.0, "s_pip_2": 1.0, "s_vol_3": 1.0, "area_1": 2410763.0},
    ],
}
#  Sheet row 35 (EP20_117-295, 2-8°C 180 Days) — the user's quoted "99.5 / 13.23".
ROW35 = {
    "standard": STANDARD,
    "std_areas": STD_AREAS,
    "samples": [
        {"prep_ref": "EP20_117-295", "sample_weight": 0.7646, "s_vol_1": 100.0,
         "s_pip_1": 1.0, "s_vol_2": 1.0, "s_pip_2": 1.0, "s_vol_3": 1.0, "area_1": 2383966.0},
    ],
}


class TestA1FPMgml:
    """Gold values hand-derived from the sheet's O/P/Q/R formulas."""

    @pytest.fixture()
    def result(self):
        return evaluator().evaluate(CONTEXT, TWO_ROW)

    @pytest.fixture()
    def row35(self):
        return evaluator().evaluate(CONTEXT, ROW35)

    def test_mean_standard_area(self, result):
        # B24 = AVERAGE(2387569, 2388066, 2392223, 2389532, 2382677) = 2388013.4
        assert result.values["stats.mean_std"] == pytest.approx(2388013.4)

    def test_set1_percent_assay(self, result):
        # O31 = N31/B24 * C14/D14 * E14/F14 * G14/H14 * K/J * I/H * F/G * K14
        #     = 2496042/2388013.4 * 50.59/100 * 10/50 * 1/1 * 1/1 * 100/0.7621
        #       * 1.005/13.3 * 99.64 = 104.48308384718301 → 104.5 (1 dp)
        assert result.row_value("samples", 0, "pct_assay") == pytest.approx(
            104.48308384718301, abs=1e-6
        )

    def test_set1_assay_mgml(self, result):
        # Q31 (full chain) = 13.896250151675343 → 13.90 (2 dp)
        assert result.row_value("samples", 0, "assay_mgml") == pytest.approx(
            13.896250151675343, abs=1e-6
        )

    def test_set2_percent_assay(self, result):
        # O33 = 2410763/2388013.4 * 50.59/100 * 10/50 * 100/0.7469 * 1.005/13.3
        #       * 99.64 = 102.9670127290888 → 103.0 (1 dp)
        assert result.row_value("samples", 1, "pct_assay") == pytest.approx(
            102.9670127290888, abs=1e-6
        )

    def test_set2_assay_mgml(self, result):
        # Q33 = 13.69461269296881 → 13.69 (2 dp)
        assert result.row_value("samples", 1, "assay_mgml") == pytest.approx(
            13.69461269296881, abs=1e-6
        )

    def test_mgml_equals_pct_times_lc_over_100_identity(self, result):
        # Sheet Q = sheet O × L.C. / 100 (the ONLY differences between the O and
        # Q formulas are: O divides by G (L.C.), Q by 1; and O's potency K14 vs
        # Q's K14/100). So assay_mgml ≡ pct_assay × 13.3 / 100 to FP noise.
        pct0 = result.row_value("samples", 0, "pct_assay")
        assert result.row_value("samples", 0, "assay_mgml") == pytest.approx(
            pct0 * 13.3 / 100, abs=1e-9
        )

    def test_block_percent_mean_assay_unchanged(self, result):
        # P-block % Mean Assay = mean(O31, O33) = 103.7250482881359; the base
        # stats.pct_mean_assay keeps its live round-2dp → 103.73 (sheet displays
        # 1 dp, 103.7 — the base rounding is deliberately left unchanged).
        assert result.values["stats.pct_mean_assay"] == pytest.approx(103.73)
        # Reportable result still rides on % Mean Assay (resultRef unchanged).
        assert result.reportable_result == pytest.approx(103.73)

    def test_block_mean_mgml(self, result):
        # R-block Mean (mg/mL) = mean(Q31, Q33) = 13.795431422322077 → 13.80 (2 dp)
        assert result.values["stats.mean_mgml"] == pytest.approx(13.80)

    def test_row35_percent_assay(self, row35):
        # O35 = 2383966/2388013.4 * 50.59/100 * 10/50 * 100/0.7646 * 1.005/13.3
        #       * 99.64 = 99.46535083649894 → 99.5 (1 dp)  ✔ user gold "99.5"
        assert row35.row_value("samples", 0, "pct_assay") == pytest.approx(
            99.46535083649894, abs=1e-6
        )

    def test_row35_assay_mgml(self, row35):
        # Q35 = 13.22889166125436 → 13.23 (2 dp)  ✔ user gold "13.23"
        # Cross-check: 99.5 × 13.3 / 100 = 13.23.
        assert row35.row_value("samples", 0, "assay_mgml") == pytest.approx(
            13.22889166125436, abs=1e-6
        )
