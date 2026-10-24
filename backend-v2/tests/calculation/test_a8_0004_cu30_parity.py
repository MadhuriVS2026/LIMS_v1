"""
GxP parity for TPL-A8-0004 (Content Uniformity by HPLC — 30 units, "CU-tablets-30units").

This stage-2 template reuses A8_HPLC's Acceptance-Value arithmetic
(`a8_content_uniformity._ACCEPTANCE_VALUE`, via `_summary_group`), the `_common`
standard / replicate helpers, and A12-0001's bracketing + pooled-%RSD pattern.
The only deliberate differences from A8_HPLC are: the `units` table defaults to
30 rows, and the acceptability constant `k_value` defaults to 2.0 (USP <905> k
for n=30).

The fixtures below are built so that each unit's `% of Label Claim` (`pct_lc`)
equals the unit's entered area directly: the standard chain, the sample chain,
potency, MW correction, average weight and label claim are all set to the
neutral value 1 (potency 100 %), and the five standard replicate areas are all
100 so `stats.mean_std == 100`. The per-unit expression then reduces to
`area / 100 * 100 == area`, which makes the mean/SD feeding the AV exactly the
mean/SD of the chosen areas. Every expected AV and pooled %RSD is HAND-DERIVED
from those inputs (USP <905>), not copied from a run.
"""
import statistics

import pytest

from scripts.template_definitions.a8_content_uniformity import _ACCEPTANCE_VALUE
from scripts.template_definitions.a8_cu_tablets_30units import (
    A8_CU_30U,
    A8_CU_30U_DEFINITION,
)
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition


def _evaluator() -> WorksheetEvaluator:
    return WorksheetEvaluator(TemplateDefinition.parse(A8_CU_30U_DEFINITION))


#  Neutral standard block: every chain term is 1, potency 100 %, MW 1/1.
_STD = {
    "weight_mg": 1, "vol_1": 1, "pip_1": 1, "vol_2": 1, "pip_2": 1, "vol_3": 1,
    "mw_base": 1, "mw_salt": 1, "potency": 100,
}
#  Five replicates all 100 -> stats.mean_std == 100.
_STD_AREAS = [{"area": 100.0} for _ in range(5)]
#  Context: k = 2.0 for n=30; avg_weight and label_claim neutral.
_CTX = {"k_value": 2.0, "avg_weight": 1, "label_claim": 1}


def _unit(pct: float) -> dict:
    #  Neutral sample chain + unit_weight 1 so pct_lc == area == `pct`.
    return {
        "unit_ref": "u", "unit_weight": 1,
        "s_vol_1": 1, "s_pip_1": 1, "s_vol_2": 1, "s_pip_2": 1, "s_vol_3": 1,
        "area": pct,
    }


def _evaluate(areas: list[float]):
    return _evaluator().evaluate(
        _CTX,
        {
            "standard": [_STD],
            "std_areas": _STD_AREAS,
            "units": [_unit(a) for a in areas],
        },
    )


class TestA8_0004CU30Structure:
    def test_units_default_and_max_are_thirty(self):
        parsed = TemplateDefinition.parse(A8_CU_30U_DEFINITION)
        units = parsed.group("units")
        assert units is not None
        assert units.rows.default == 30
        assert units.rows.max == 30

    def test_k_value_defaults_to_two(self):
        parsed = TemplateDefinition.parse(A8_CU_30U_DEFINITION)
        k = next(cf for cf in parsed.context if cf.key == "k_value")
        assert k.default == 2.0

    def test_identity(self):
        assert A8_CU_30U.code == "TPL-A8-0004"
        assert A8_CU_30U.archetype == "A8"
        assert A8_CU_30U.result_unit == "AV"
        assert A8_CU_30U.test_code == "TST-CU-30U"
        assert A8_CU_30U.test_name == "CU-tablets-30units"


class TestA8_0004CU30AcceptanceValue:
    #  AV = |M - X| + k·s, upper bound tested outermost, lower bound inside.
    #  The summary uses mean rounded to 1 dp and sd rounded to 4 dp; the AV is
    #  then rounded to 1 dp. Expected AVs are hand-derived from those rounded
    #  values with k = 2.0.

    def test_centred_case_av_is_k_times_s(self):
        #  Mean exactly 100.0 (inside [98.5, 101.5]) -> |M - X| term is 0,
        #  AV == k·s == 2.0·s.
        areas = [99.0, 100.0, 101.0] * 10  # 30 units, mean 100.0
        mean = round(statistics.mean(areas), 1)
        sd = round(statistics.stdev(areas), 4)
        assert 98.5 <= mean <= 101.5  # the centred branch
        expected_av = round(2.0 * sd, 1)

        result = _evaluate(areas)
        assert result.values["summary.mean_pct"] == pytest.approx(mean)
        assert result.values["summary.sd_pct"] == pytest.approx(sd)
        assert result.values["summary.acceptance_value"] == pytest.approx(expected_av)
        #  Sanity: the hand-derived number, independent of the template.
        assert expected_av == pytest.approx(1.7)

    def test_off_centre_low_case_adds_lower_bound_gap(self):
        #  Mean 97.0 (< 98.5) -> AV == (98.5 - M) + k·s. If the AV nesting were
        #  reversed (upper bound inside), this mean would wrongly take the
        #  centred branch and the (98.5 - M) gap would be dropped.
        areas = [96.0, 97.0, 98.0] * 10  # 30 units, mean 97.0
        mean = round(statistics.mean(areas), 1)
        sd = round(statistics.stdev(areas), 4)
        assert mean < 98.5  # the low branch
        expected_av = round((98.5 - mean) + 2.0 * sd, 1)

        result = _evaluate(areas)
        assert result.values["summary.mean_pct"] == pytest.approx(mean)
        assert result.values["summary.sd_pct"] == pytest.approx(sd)
        assert result.values["summary.acceptance_value"] == pytest.approx(expected_av)
        assert expected_av == pytest.approx(3.2)

    def test_av_expression_is_the_a8_hplc_object(self):
        #  Reused verbatim: the summary group's AV expression is literally the
        #  same string imported from a8_content_uniformity.
        summary = A8_CU_30U_DEFINITION["groups"][-1]
        av_field = next(f for f in summary["fields"] if f["key"] == "acceptance_value")
        assert av_field["expression"] is _ACCEPTANCE_VALUE


class TestA8_0004CU30BracketingRSD:
    def test_pooled_bracketing_rsd(self):
        #  stats.rsd_bkt == rsd(pool(std_areas.area, bkt_1.area, bkt_2.area)).
        std_areas = [100.0, 101.0, 99.0, 100.5, 99.5]
        bkt_1 = [100.2, 99.8]
        bkt_2 = [101.0]
        pool = std_areas + bkt_1 + bkt_2
        expected = statistics.stdev(pool) / statistics.mean(pool) * 100

        result = _evaluator().evaluate(
            _CTX,
            {
                "standard": [_STD],
                "std_areas": [{"area": a} for a in std_areas],
                "bkt_1": [{"area": a} for a in bkt_1],
                "bkt_2": [{"area": a} for a in bkt_2],
                "units": [_unit(100.0)],
            },
        )
        assert result.values["stats.rsd_bkt"] == pytest.approx(expected)


class TestA8_0004CU30Criteria:
    def test_criteria_present_with_correct_limits(self):
        parsed = TemplateDefinition.parse(A8_CU_30U_DEFINITION)
        by_key = {c.key: c for c in parsed.criteria}

        assert by_key["sst_std_rsd"].target == "stats.rsd_std"
        assert by_key["sst_std_rsd"].operator.value == "lte"
        assert by_key["sst_std_rsd"].limit == pytest.approx((2.0,))
        assert by_key["sst_std_rsd"].severity.value == "blocking"

        assert by_key["sst_bkt_rsd"].target == "stats.rsd_bkt"
        assert by_key["sst_bkt_rsd"].operator.value == "lte"
        assert by_key["sst_bkt_rsd"].limit == pytest.approx((2.0,))
        assert by_key["sst_bkt_rsd"].severity.value == "blocking"

        assert by_key["acceptance_value"].target == "summary.acceptance_value"
        assert by_key["acceptance_value"].operator.value == "lte"
        assert by_key["acceptance_value"].limit == pytest.approx((15.0,))
        assert by_key["acceptance_value"].severity.value == "blocking"

        assert by_key["unit_count"].target == "count(units.pct_lc)"
        assert by_key["unit_count"].operator.value == "gte"
        assert by_key["unit_count"].limit == pytest.approx((10,))
        assert by_key["unit_count"].severity.value == "advisory"


class TestA8_0004CU30Invariants:
    def test_empty_evaluate_has_no_blocking_failure_and_blank_reportable(self):
        from src.domain.services.calculation.evaluator import EMPTY

        result = _evaluator().evaluate({}, {})
        assert result.has_blocking_failure is False
        assert result.reportable_result is EMPTY
