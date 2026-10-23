"""
GxP parity for TPL-A12-0003 (Amphotericin B — Drug-to-Lipid Ratio).

The template is a derived roll-up like its A12 siblings — every number is a
component assay carried from another test, there is no injection block — but the
source sheet lists MULTIPLE batches, so it is ONE multi-batch TABLE (`batches`),
one row per batch. Each row carries the four component assays (%) as inputs and
computes the four contents (mg/vial), the summed LIPID content (drug excluded)
and the drug-to-lipid ratio:

    Content (mg/vial)        = Assay% × LC / 100
    Lipid content (mg/vial)  = Chol + HSPC + DSPG contents (Ampho EXCLUDED)
    Drug / Lipid Ratio       = Ampho content / Lipid content

The per-component label claims (content factors) are overridable context fields,
reverse-engineered from the gold data: Chol 52.0 / HSPC 213.0 / DSPG 81.6 /
Ampho 50.0 mg/vial.

Every expected value below is the task's authoritative oracle (three INITIAL
batches), asserted to the sheet's shown rounding — contents to 4 dp, the ratio to
4 dp — NOT copied from a run.
"""
import pytest

from scripts.template_definitions.a12_ampho_drug_lipid import (
    A12_AMPHO_RATIO_DEFINITION,
)
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition


def _evaluator() -> WorksheetEvaluator:
    return WorksheetEvaluator(TemplateDefinition.parse(A12_AMPHO_RATIO_DEFINITION))


#  Three INITIAL batches: the four component assays (%) entered per batch.
BATCHES = [
    {"batch_no": "10009697", "condition": "INITIAL",
     "chol_assay": 105.3, "hspc_assay": 107.5, "dspg_assay": 100.8, "ampho_assay": 110.6},
    {"batch_no": "10010727", "condition": "INITIAL",
     "chol_assay": 105.6, "hspc_assay": 107.1, "dspg_assay": 104.3, "ampho_assay": 108.7},
    {"batch_no": "040598M", "condition": "INITIAL",
     "chol_assay": 106.1, "hspc_assay": 106.3, "dspg_assay": 101.7, "ampho_assay": 109.4},
]

#  Authoritative oracle (task GOLD VALUES): per batch, the four contents, the
#  lipid content and the ratio.
#
#  NOTE on batch 0 Amphotericin B content: the task text prints "55.3200" in the
#  content column, but the formula it also specifies — Content = Assay × LC/100 =
#  110.6 × 50/100 — gives 55.3000, and ONLY 55.3000 reproduces the authoritative
#  gold ratio 0.1511 (55.32/365.9838 rounds to 0.1512). So "55.3200" is a
#  transcription slip in the content column; the formula-derived, ratio-consistent
#  value 55.3000 is the true oracle and is asserted here. (Verified: 55.30/365.9838
#  = 0.1511; 55.32/365.9838 = 0.1512.)
GOLD = {
    0: {"chol": 54.7560, "hspc": 228.9750, "dspg": 82.2528, "ampho": 55.3000,
        "lipid": 365.9838, "ratio": 0.1511},
    #  Same content-column slip as batch 0: task prints 54.3650 but 108.7×50/100
    #  = 54.3500, and 54.35/368.1438 = 0.1476 (the gold); 54.365 gives 0.1477.
    1: {"chol": 54.9120, "hspc": 228.1230, "dspg": 85.1088, "ampho": 54.3500,
        "lipid": 368.1438, "ratio": 0.1476},
    #  Task prints 54.6900 but 109.4×50/100 = 54.7000, and 54.70/364.5782 = 0.1500
    #  (the gold); 54.69 gives 0.1500 too but 54.70 is the formula-exact value.
    2: {"chol": 55.1720, "hspc": 226.4190, "dspg": 82.9872, "ampho": 54.7000,
        "lipid": 364.5782, "ratio": 0.1500},
}


class TestA12_0003AmphoParity:
    @pytest.fixture()
    def result(self):
        #  Context left to defaults — the four LC context fields default to the
        #  reverse-engineered label claims, so the fixture exercises those.
        return _evaluator().evaluate({}, {"batches": BATCHES})

    def test_component_contents(self, result):
        #  Content = Assay% × LC / 100, to the sheet's 4 dp.
        for i, gold in GOLD.items():
            assert result.row_value("batches", i, "chol_content") == pytest.approx(gold["chol"], abs=1e-4)
            assert result.row_value("batches", i, "hspc_content") == pytest.approx(gold["hspc"], abs=1e-4)
            assert result.row_value("batches", i, "dspg_content") == pytest.approx(gold["dspg"], abs=1e-4)
            assert result.row_value("batches", i, "ampho_content") == pytest.approx(gold["ampho"], abs=1e-4)

    def test_lipid_content_excludes_drug(self, result):
        #  Lipid = Chol + HSPC + DSPG contents; Amphotericin B excluded.
        for i, gold in GOLD.items():
            assert result.row_value("batches", i, "lipid_content") == pytest.approx(gold["lipid"], abs=1e-4)

    def test_drug_lipid_ratio(self, result):
        #  Ratio = Ampho content / Lipid content, to the sheet's 4 dp.
        for i, gold in GOLD.items():
            assert result.row_value("batches", i, "drug_lipid_ratio") == pytest.approx(gold["ratio"], abs=1e-4)

    def test_reportable_result_is_first_batch_ratio(self, result):
        #  Multi-row group: the engine returns the first non-blank ratio down the
        #  rows as the reportable.
        assert result.reportable_result == pytest.approx(GOLD[0]["ratio"], abs=1e-4)

    def test_passes_on_gold_data(self, result):
        #  All four assays and the ratio are inside their acceptance ranges.
        assert result.has_blocking_failure is False

    def test_criteria_exist_with_correct_limits(self, result):
        parsed = TemplateDefinition.parse(A12_AMPHO_RATIO_DEFINITION)
        by_key = {c.key: c for c in parsed.criteria}
        #  Four component-assay ranges and the ratio range, all blocking.
        expected = {
            "chol_assay_range": (90.0, 120.0),
            "hspc_assay_range": (90.0, 120.0),
            "dspg_assay_range": (80.0, 120.0),
            "ampho_assay_range": (90.0, 120.0),
            "drug_lipid_ratio_range": (0.11, 0.17),
        }
        assert set(by_key) == set(expected)
        for key, (low, high) in expected.items():
            crit = by_key[key]
            assert crit.operator.value == "between"
            assert crit.severity.value == "blocking"
            assert crit.limit == pytest.approx((low, high))

    def test_ratio_criterion_fails_when_out_of_range(self):
        #  A batch whose ratio falls below 0.11 must raise a blocking failure on
        #  the ratio criterion (confirms the limit is wired and enforced).
        low_ratio_batch = [{
            "batch_no": "LOW", "condition": "INITIAL",
            "chol_assay": 120.0, "hspc_assay": 120.0, "dspg_assay": 120.0,
            "ampho_assay": 10.0,  # tiny drug -> ratio well under 0.11
        }]
        result = _evaluator().evaluate({}, {"batches": low_ratio_batch})
        ratio_crit = next(c for c in result.criteria if c.key == "drug_lipid_ratio_range")
        assert ratio_crit.passed is False
        assert result.has_blocking_failure is True
