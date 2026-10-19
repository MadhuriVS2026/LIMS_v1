"""
GxP parity for TPL-A2-0004 (Bupivacaine Lipid Content & Drug-to-Lipid Ratio)
after the tabular transpose of the standard replicate / BKT injection blocks.

The two injection blocks are laid out as INJECTIONS-AS-ROWS / COMPOUNDS-AS-COLUMNS
(one row per injection; four area columns tri/dppg/chol/depc; no per-row
Mean/SD/%RSD). Per-compound Mean/SD/%RSD aggregate DOWN each compound column and
are published by the `stats` singleton — `mean(std_areas.<c>_area)` for the
replicate block and `mean(pool(std_areas.<c>_area, bkt_areas.<c>_area))` for the
pooled BKT block. Every `stats.*` KEY is unchanged, so the %Assay chain and the 8
SST criteria are untouched.

Every expected value below is derived by hand from the workbook
`_dumps/Bupivacaine Lipid _ Drug to lipid Ratio.txt` (sheet cells named in the
comments), not copied from a run — a copied number would pin whatever the code
currently does, including a bug.
"""
import pytest

from scripts.template_definitions.a2_bupivacaine_lipid_ratio import (
    LIPID_RATIO_DEFINITION,
)
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition


def _evaluator() -> WorksheetEvaluator:
    return WorksheetEvaluator(TemplateDefinition.parse(LIPID_RATIO_DEFINITION))


#  Standard Details (sheet rows 18–21, columns B..J).
STANDARD = [
    {"name": "Tricaprylin", "weight": 99.1, "vol1": 50, "pip1": 6, "vol2": 100,
     "pip2": 1, "vol3": 1, "potency": 100, "mw_base": 1, "mw_salt": 1},
    {"name": "DPPG Na", "weight": 46.79, "vol1": 50, "pip1": 6, "vol2": 100,
     "pip2": 1, "vol3": 1, "potency": 99.3, "mw_base": 721.9602, "mw_salt": 744.95},
    {"name": "Cholesterol", "weight": 28.51, "vol1": 100, "pip1": 1, "vol2": 1,
     "pip2": 1, "vol3": 1, "potency": 100, "mw_base": 1, "mw_salt": 1},
    {"name": "DEPC", "weight": 49.32, "vol1": 100, "pip1": 1, "vol2": 1,
     "pip2": 1, "vol3": 1, "potency": 99.2, "mw_base": 1, "mw_salt": 1},
]

#  Standard replicate injections (sheet rows 25–30, cols B/C/D/E) — one row per
#  injection, one column per compound (tri/dppg/chol/depc).
STD_AREAS = [
    {"inj_label": "Injection 1", "tri_area": 8711513, "dppg_area": 4437526, "chol_area": 32277247, "depc_area": 44369260},
    {"inj_label": "Injection 2", "tri_area": 8674291, "dppg_area": 4473096, "chol_area": 32439471, "depc_area": 44366857},
    {"inj_label": "Injection 3", "tri_area": 8679908, "dppg_area": 4461331, "chol_area": 32393636, "depc_area": 44211085},
    {"inj_label": "Injection 4", "tri_area": 8671826, "dppg_area": 4528571, "chol_area": 32357224, "depc_area": 43613144},
    {"inj_label": "Injection 5", "tri_area": 8715229, "dppg_area": 4403707, "chol_area": 32429381, "depc_area": 43626749},
    {"inj_label": "Injection 6", "tri_area": 8695954, "dppg_area": 4463992, "chol_area": 32523530, "depc_area": 43893218},
]

#  BKT injections (sheet rows 25–28, cols H/I/J/K) — four injection rows, one
#  column per compound; injections 5/6 absent (blanks skipped by the aggregate).
BKT_AREAS = [
    {"inj_label": "Injection 1", "tri_area": 8713270, "dppg_area": 4473297, "chol_area": 32509936, "depc_area": 43884434},
    {"inj_label": "Injection 2", "tri_area": 8686255, "dppg_area": 4509972, "chol_area": 32485699, "depc_area": 43979519},
    {"inj_label": "Injection 3", "tri_area": 8719164, "dppg_area": 4448498, "chol_area": 32455877, "depc_area": 43323151},
    {"inj_label": "Injection 4", "tri_area": 8729929, "dppg_area": 4472750, "chol_area": 32460029, "depc_area": 44269558},
]

#  Batch EP20_117-299-B (sheet rows 39/43): inj-1 areas only (inj-2 blank → %Mean
#  == inj-1), avg_weight H39, sample_weight I39, vol/pip J39/K39/L39.
LIPID_SAMPLES = [
    {"batch_no": "EP20_117-299-B", "avg_weight": 1.005, "sample_weight": 1.5008,
     "vol_j": 25, "pip_k": 1, "vol_l": 1,
     "tri_area1": 8729574, "dppg_area1": 3826195,
     "chol_area1": 32474189, "depc_area1": 44235393},
]
DRUG_LIPID = [{"batch_no": "EP20_117-299-B", "pct_assay_bupi": 99.9}]
CONTEXT = {"lc_tri": 2, "lc_dppg": 0.9, "lc_chol": 4.7, "lc_depc": 8.2, "lc_bupi": 13.3}


class TestA2_0004TabularParity:
    @pytest.fixture()
    def result(self):
        return _evaluator().evaluate(
            CONTEXT,
            {
                "standard": STANDARD,
                "std_areas": STD_AREAS,
                "bkt_areas": BKT_AREAS,
                "lipid_samples": LIPID_SAMPLES,
                "drug_lipid": DRUG_LIPID,
            },
        )

    def test_standard_concentrations(self, result):
        #  K18..K21 = B/C*D/E*F/G*H/100*I/J*1000, rounded 2dp.
        assert result.row_value("standard", 0, "conc_ppm") == pytest.approx(118.92, abs=1e-2)
        assert result.row_value("standard", 1, "conc_ppm") == pytest.approx(54.03, abs=1e-2)
        assert result.row_value("standard", 2, "conc_ppm") == pytest.approx(285.1, abs=1e-2)
        assert result.row_value("standard", 3, "conc_ppm") == pytest.approx(489.25, abs=1e-2)

    def test_std_area_column_means(self, result):
        #  Per-compound mean DOWN each column of six replicate injections
        #  (sheet B31/C31/D31/E31), published by the stats singleton.
        assert result.values["stats.mean_std_tri"] == pytest.approx(8691453.5, abs=1e-2)
        assert result.values["stats.mean_std_dppg"] == pytest.approx(4461370.5, abs=1e-2)
        assert result.values["stats.mean_std_chol"] == pytest.approx(32403414.83, abs=1e-2)
        assert result.values["stats.mean_std_depc"] == pytest.approx(44013385.5, abs=1e-2)

    def test_bkt_pooled_tricaprylin(self, result):
        #  H31 = AVERAGE(H25:H30, B25:B30): the six std + four bkt Tricaprylin
        #  injections = (52148721 + 34848618) / 10 = 8699733.9; %RSD ≈ 0.2383.
        assert result.values["stats.mean_pool_tri"] == pytest.approx(8699733.9, abs=1e-2)
        assert result.values["stats.rsd_pool_tri"] == pytest.approx(0.2383, abs=1e-4)

    def test_stats_indirection_still_resolves(self, result):
        #  The singleton must publish the per-compound column aggregates under the
        #  unchanged stats.* keys that the %Assay chain and SST criteria reference.
        assert result.values["stats.mean_std_tri"] == pytest.approx(8691453.5, abs=1e-2)
        assert result.values["stats.rsd_pool_tri"] == pytest.approx(0.2383, abs=1e-4)

    def test_batch_b_percent_assay_inj1(self, result):
        #  N39..N42 for batch B (inj-1), via the stats indirection.
        assert result.row_value("lipid_samples", 0, "tri_assay1") == pytest.approx(99.979, abs=1e-2)
        assert result.row_value("lipid_samples", 0, "dppg_assay1") == pytest.approx(86.200, abs=1e-2)
        assert result.row_value("lipid_samples", 0, "chol_assay1") == pytest.approx(101.772, abs=1e-2)
        assert result.row_value("lipid_samples", 0, "depc_assay1") == pytest.approx(100.390, abs=1e-2)

    def test_drug_lipid_ratio_chain(self, result):
        #  Sheet 2 I18 (tri mg/mL), J18 (sum), M18 (bupi mg/mL), N18 (ratio).
        assert result.row_value("drug_lipid", 0, "tri_mgml") == pytest.approx(1.99958, abs=1e-4)
        assert result.row_value("drug_lipid", 0, "sum_lipid") == pytest.approx(15.790645, abs=1e-4)
        assert result.row_value("drug_lipid", 0, "mgml_bupi") == pytest.approx(13.2867, abs=1e-4)
        assert result.row_value("drug_lipid", 0, "ratio") == pytest.approx(0.841429, abs=1e-4)
        assert result.reportable_result == pytest.approx(0.841429, abs=1e-4)

    def test_suitability_does_not_block_on_this_data(self, result):
        assert result.has_blocking_failure is False
