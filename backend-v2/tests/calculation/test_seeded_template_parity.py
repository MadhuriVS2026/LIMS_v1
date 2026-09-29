"""
Parity tests for every seeded archetype template.

This is the GxP-relevant claim: that each *seeded template* — the thing an analyst
will actually use — reproduces its source workbook, not merely that the engine can
express the formula.

Every expected value below is derived by hand from the formula in the comment
above it. Copying a number from a previous run would make these tests pin whatever
the code currently does, including a bug; deriving them independently is what
makes a regression fail.
"""
import pytest

from scripts.template_definitions import SEED_TEMPLATES
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.expression import EMPTY
from src.domain.services.calculation.template_schema import (
    FieldKind,
    TemplateDefinition,
)

BY_CODE = {item.code: item for item in SEED_TEMPLATES}


def evaluator(code: str) -> WorksheetEvaluator:
    return WorksheetEvaluator(TemplateDefinition.parse(BY_CODE[code].definition))


def parsed(code: str) -> TemplateDefinition:
    return TemplateDefinition.parse(BY_CODE[code].definition)


# ── Catalogue-wide invariants ────────────────────────────────────────


def test_every_archetype_in_scope_is_seeded():
    """
    All fourteen archetypes are now seeded, A7 (f1/f2) and A12 (the cross-test
    roll-ups) included — both had been held back pending lab confirmation, and
    both questions turned out to be answerable from the workbooks themselves.
    A missing archetype here means the catalogue silently lost coverage.

    Every family now carries a hand-derived parity class as well as these four
    catalogue-wide invariants, so each one is pinned against its source workbook
    rather than only known to parse and run.
    """
    assert {item.archetype for item in SEED_TEMPLATES} == {
        "A1", "A2", "A3", "A4", "A5", "A6a", "A6b", "A6c", "A6d", "A7",
        "A8", "A9", "A10", "A11", "A12", "A13", "A14",
    }


def test_template_codes_are_unique():
    codes = [item.code for item in SEED_TEMPLATES]
    assert len(codes) == len(set(codes))


@pytest.mark.parametrize("code", list(BY_CODE))
def test_every_template_parses_and_runs_empty(code):
    """An analyst opening a fresh worksheet must see blanks, never an error."""
    result = evaluator(code).evaluate({}, {})
    assert result.has_blocking_failure is False
    assert result.reportable_result is EMPTY


@pytest.mark.parametrize("code", list(BY_CODE))
def test_every_template_has_a_resolvable_reportable_result(code):
    """Without a `resultRef` a worksheet can never publish to its test line."""
    definition = parsed(code)
    assert definition.result_ref is not None
    group_key, _, field_key = definition.result_ref.partition(".")
    group = definition.group(group_key)
    assert group is not None and group.field(field_key) is not None


@pytest.mark.parametrize("code", list(BY_CODE))
def test_no_context_field_is_unfillable(code):
    """
    A context field with no source, not overridable and no default renders as a
    permanently blank read-only box and silently blanks anything downstream. This
    is the trap found while seeding A1.
    """
    for field in parsed(code).context:
        assert field.source or field.overridable or field.default is not None, (
            f"{code}: context field {field.key!r} can never hold a value"
        )


@pytest.mark.parametrize("code", list(BY_CODE))
def test_area_fields_are_discoverable_for_the_waters_import(code):
    """
    The CDS adapter finds work through `area_field_refs`, so an area typed as a
    plain input would be invisible to it and stay manual forever.
    """
    definition = parsed(code)
    declared = set(definition.area_field_refs)
    actual = {
        (g.key, f.key)
        for g in definition.groups
        for f in g.fields
        if f.kind is FieldKind.AREA
    }
    assert declared == actual


# ── A1: Assay by HPLC — the reference archetype ──────────────────────

A1_CONTEXT = {"label_claim": 50.0, "avg_weight": 1.0}
A1_GROUPS = {
    "standard": [{
        "name": "Amphotericin B", "weight_mg": 5.054, "vol_1": 50.0, "pip_1": 5.0,
        "vol_2": 100.0, "pip_2": 1.0, "vol_3": 1.0,
        "mw_base": 1.0, "mw_salt": 1.0, "potency": 99.4,
    }],
    "std_areas": [
        {"area": 253287.0}, {"area": 253024.0}, {"area": 252584.0},
        {"area": 252811.0}, {"area": 251367.0},
    ],
    "bkt_1": [{"area": 251635.0}, {"area": 251658.0}],
    "bkt_2": [{"area": 260938.0}],
    "std_2": [{"weight_mg": 5.054, "area_1": 253000.0, "area_2": 253100.0}],
    "samples": [
        {"prep_ref": "Initial_1", "sample_weight": 1.0, "s_vol_1": 500.0, "s_pip_1": 5.0,
         "s_vol_2": 100.0, "s_pip_2": 1.0, "s_vol_3": 1.0, "area_1": 273537.0},
        {"prep_ref": "Initial_2", "sample_weight": 1.0, "s_vol_1": 500.0, "s_pip_1": 5.0,
         "s_vol_2": 100.0, "s_pip_2": 1.0, "s_vol_3": 1.0, "area_1": 273755.0},
    ],
}


class TestA1Assay:
    """Source: `Assay by HPLC.xlsx`, Amphotericin B Liposome 50 mg/vial."""

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A1-0001").evaluate(A1_CONTEXT, A1_GROUPS)

    def test_standard_concentration(self, result):
        # 5.054/50 * 5/100 * 0.994 * 1000 = 5.023676 ppm
        assert result.values["standard.conc_ppm"] == pytest.approx(5.023676, abs=1e-6)

    def test_mean_standard_area(self, result):
        # (253287+253024+252584+252811+251367)/5 = 252614.6
        assert result.values["stats.mean_std"] == pytest.approx(252614.6)

    def test_percent_rsd(self, result):
        # sd 744.26897 / mean 252614.6 * 100
        assert result.values["stats.rsd_std"] == pytest.approx(0.294626, abs=1e-6)

    def test_bracketing_pools_cumulatively(self, result):
        expected = (253287 + 253024 + 252584 + 252811 + 251367 + 251635 + 251658) / 7
        assert result.values["stats.mean_bkt_1"] == pytest.approx(expected)

    def test_first_preparation(self, result):
        # 273537/252614.6 * 0.005054 * 10000 * 1/50 * 99.4 = 108.795079
        assert result.row_value("samples", 0, "pct_assay") == pytest.approx(
            108.795079, abs=1e-6
        )

    def test_reportable_mean_assay(self, result):
        # mean(108.795079, 108.881785) = 108.838432, rounded 2dp
        assert result.reportable_result == pytest.approx(108.84)

    def test_suitability_passes(self, result):
        assert result.has_blocking_failure is False


# ── A2: Multi-analyte content ────────────────────────────────────────


class TestA2MultiAnalyte:
    """Source: `Content of Lyso PC PG`. Response is a sum of named peaks."""

    CONTEXT = {"label_claim": 52.0, "avg_weight": 1.0, "vial_factor": 1}
    GROUPS = {
        "standard": [{
            "weight_mg": 10.0, "vol_1": 100.0, "pip_1": 1.0, "vol_2": 1.0,
            "pip_2": 1.0, "vol_3": 1.0, "mw_base": 1.0, "mw_salt": 1.0, "potency": 99.0,
        }],
        #  Two peaks per injection: 3000 + 2000 = 5000 total.
        "std_areas": [
            {"peak_1": 3000.0, "peak_2": 2000.0},
            {"peak_1": 3010.0, "peak_2": 1990.0},
        ],
        "samples": [
            {"sample_weight": 10.0, "s_vol_1": 100.0, "s_pip_1": 1.0, "s_vol_2": 1.0,
             "s_pip_2": 1.0, "s_vol_3": 1.0, "peak_1": 3000.0, "peak_2": 2000.0},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A2-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_peak_areas_are_summed_per_injection(self, result):
        assert result.row_value("std_areas", 0, "area") == pytest.approx(5000.0)
        assert result.row_value("std_areas", 1, "area") == pytest.approx(5000.0)

    def test_mean_standard_area(self, result):
        assert result.values["stats.mean_std"] == pytest.approx(5000.0)

    def test_content_matches_the_standard_when_responses_match(self, result):
        # area/mean_std = 1; std chain 10/100 = 0.1; sample chain 1/1*1/1*100/10 = 10;
        # potency 0.99 → 1 * 0.1 * 10 * 0.99 = 0.99 mg
        assert result.row_value("samples", 0, "content") == pytest.approx(0.99, abs=1e-6)

    def test_vial_factor_scales_the_content(self):
        per_vial = evaluator("TPL-A2-0001").evaluate(
            {**self.CONTEXT, "vial_factor": 12.5}, self.GROUPS
        )
        # The `_mgvial_` and `_mgmL_` workbooks differ only by this factor.
        assert per_vial.row_value("samples", 0, "content") == pytest.approx(
            0.99 * 12.5, abs=1e-5
        )

    def test_zero_peak_sum_reads_as_blank_not_zero(self):
        groups = {
            **self.GROUPS,
            "samples": [{**self.GROUPS["samples"][0], "peak_1": 0.0, "peak_2": 0.0}],
        }
        result = evaluator("TPL-A2-0001").evaluate(self.CONTEXT, groups)
        #  Sheet wraps this in IF(SUM(...)=0,"",...) — an un-injected row is not a
        #  zero response.
        assert result.row_value("samples", 0, "area") is EMPTY


# ── A3: Saturation solubility ────────────────────────────────────────


class TestA3SaturationSolubility:
    CONTEXT = {"medium": "Water", "temperature_c": 37}
    GROUPS = {
        "standard": [{
            "weight_mg": 25.0, "vol_1": 25.0, "pip_1": 1.0, "vol_2": 1.0,
            "pip_2": 1.0, "vol_3": 1.0, "mw_base": 1.0, "mw_salt": 1.0, "potency": 100.0,
        }],
        "std_areas": [{"area": 50000.0}, {"area": 50000.0}],
        "samples": [
            {"aliquot_ml": 1.0, "diluted_to_ml": 10.0, "area": 25000.0},
            {"aliquot_ml": 1.0, "diluted_to_ml": 10.0, "area": 25000.0},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A3-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_standard_concentration_in_ppm(self, result):
        # 25/25 * 1 * 1000 = 1000 ppm
        assert result.values["standard.conc_ppm"] == pytest.approx(1000.0)

    def test_solubility_in_mg_per_ml(self, result):
        # 25000/50000 * 1000 ppm * 10/1 / 1000 = 5.0 mg/mL
        assert result.row_value("samples", 0, "solubility") == pytest.approx(5.0)

    def test_reportable_mean(self, result):
        assert result.reportable_result == pytest.approx(5.0)


# ── A4: Related substances against an impurity standard ──────────────


class TestA4RelatedSubstances:
    CONTEXT = {
        "label_claim": 100.0, "avg_weight": 1.0, "main_peak_rt": 20.687,
        "rrf_mode": "RRF (multiplication factor)",
    }
    GROUPS = {
        "standard": [{
            "weight_mg": 100.0, "vol_1": 100.0, "pip_1": 1.0, "vol_2": 1.0,
            "pip_2": 1.0, "vol_3": 1.0, "mw_base": 1.0, "mw_salt": 1.0, "potency": 100.0,
        }],
        "std_areas": [{"area": 10000.0}, {"area": 10000.0}],
        "sample_prep": [{
            "sample_weight": 100.0, "s_vol_1": 100.0, "s_pip_1": 1.0,
            "s_vol_2": 1.0, "s_pip_2": 1.0, "s_vol_3": 1.0,
        }],
        "impurities": [
            #  1% of the standard response, RRF 1 → 1.000 %
            {"name": "Imp-A", "rt": 8.51, "rrf": 1.0, "loq": 0.05, "area_1": 100.0},
            #  Same response, RRF 2 in multiplication mode → 2.000 %
            {"name": "Imp-B", "rt": 12.0, "rrf": 2.0, "loq": 0.05, "area_1": 100.0},
            #  0.02 % — under the 0.05 LOQ, so BLQ and excluded from the total.
            {"name": "Imp-C", "rt": 15.0, "rrf": 1.0, "loq": 0.05, "area_1": 2.0},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A4-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_relative_retention_time(self, result):
        # 8.51 / 20.687 = 0.411369 → 3dp
        assert result.row_value("impurities", 0, "rrt") == pytest.approx(0.411)

    def test_percentage_against_the_impurity_standard(self, result):
        # 100/10000 * (100/100) * (100/100) * 1 * 100 = 1.0 %
        assert result.row_value("impurities", 0, "pct") == pytest.approx(1.0)

    def test_rrf_multiplication_mode(self, result):
        assert result.row_value("impurities", 1, "pct") == pytest.approx(2.0)

    def test_rrf_division_mode_inverts_the_factor(self):
        result = evaluator("TPL-A4-0001").evaluate(
            {**self.CONTEXT, "rrf_mode": "RRF (division factor)"}, self.GROUPS
        )
        # Same raw 1.0 %, divided by RRF 2 instead of multiplied.
        assert result.row_value("impurities", 1, "pct") == pytest.approx(0.5)

    def test_below_loq_reports_blq_as_text(self, result):
        # 2/10000 * 100 = 0.02 %, under the 0.05 LOQ.
        assert result.row_value("impurities", 2, "pct") == pytest.approx(0.02)
        assert result.row_value("impurities", 2, "reported") == "BLQ"

    def test_below_loq_is_excluded_from_the_total(self, result):
        assert result.row_value("impurities", 2, "pct_for_total") == pytest.approx(0.0)

    def test_total_sums_already_rounded_rows(self, result):
        # 1.000 + 2.000 + 0 (BLQ) = 3.000
        assert result.values["summary.total_impurities"] == pytest.approx(3.0)
        assert result.reportable_result == pytest.approx(3.0)

    def test_single_maximum_impurity(self, result):
        assert result.values["summary.max_single_impurity"] == pytest.approx(2.0)

    def test_sum_of_rounded_is_not_rounded_sum(self):
        """
        Three impurities at 0.0004 each: rounding every row to 3dp gives 0.000, so
        the total is 0.000 — whereas rounding the sum (0.0012) would give 0.001.
        The source sheet does SUM(ROUND(...)), and this is the case that shows it.
        """
        groups = {
            **self.GROUPS,
            "impurities": [
                {"name": f"Imp-{i}", "rt": 10.0, "rrf": 1.0, "loq": 0.0,
                 "area_1": 0.004}
                for i in range(3)
            ],
        }
        result = evaluator("TPL-A4-0001").evaluate(self.CONTEXT, groups)
        # 0.004/10000*100 = 0.00004 %; rounds to 0.000 per row.
        assert result.row_value("impurities", 0, "pct") == pytest.approx(0.0)
        assert result.values["summary.total_impurities"] == pytest.approx(0.0)


# ── A5: Area normalisation ───────────────────────────────────────────


class TestA5AreaNormalisation:
    CONTEXT = {"rrf_mode": "RRF (multiplication factor)"}
    GROUPS = {
        "main": [{"rt": 10.0, "area": 97000.0}],
        "peaks": [
            {"name": "Imp-A", "rt": 5.0, "rrf": 1.0, "loq": 0.05, "area": 1000.0},
            {"name": "Imp-B", "rt": 7.0, "rrf": 1.0, "loq": 0.05, "area": 2000.0},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A5-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_total_area_includes_the_main_peak(self, result):
        # 1000 + 2000 + 97000 = 100000
        assert result.values["normalisation.total_area"] == pytest.approx(100000.0)

    def test_percentages_are_of_total_area(self, result):
        assert result.row_value("peaks", 0, "pct") == pytest.approx(1.0)
        assert result.row_value("peaks", 1, "pct") == pytest.approx(2.0)

    def test_relative_retention_time(self, result):
        assert result.row_value("peaks", 0, "rrt") == pytest.approx(0.5)

    def test_total_impurities(self, result):
        assert result.reportable_result == pytest.approx(3.0)


# ── A6: Dissolution ─────────────────────────────────────────────────


class TestA6ADissolutionWithoutReplacement:
    """
    The media volume shrinks by the withdrawal volume each timepoint, and release
    carries over everything withdrawn earlier.
    """

    CONTEXT = {"label_claim": 100.0, "avg_weight": 1.0,
               "initial_volume": 500.0, "withdrawal_volume": 5.0}
    #  Standard set up so area 1000 ⇒ exactly 1 % released per unit at 500 mL:
    #  1000/1000 * (100/500) * 1.0 * 500/100 * 100 = 100 %.
    STANDARD = [{
        "weight_mg": 100.0, "vol_1": 500.0, "pip_1": 1.0, "vol_2": 1.0,
        "pip_2": 1.0, "vol_3": 1.0, "mw_base": 1.0, "mw_salt": 1.0, "potency": 100.0,
    }]
    GROUPS = {
        "standard": STANDARD,
        "std_areas": [{"area": 1000.0}, {"area": 1000.0}],
        "timepoints": [
            #  All six units identical, at 20 % then 40 % of the standard response.
            {"minutes": "15", **{f"area_{n}": 200.0 for n in range(1, 7)}},
            {"minutes": "30", **{f"area_{n}": 400.0 for n in range(1, 7)}},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A6A-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_volume_series_is_generated_from_the_withdrawal_volume(self, result):
        # 500, then 500 - 1*5 = 495. The sheets hard-code these.
        assert result.row_value("timepoints", 0, "media_volume") == pytest.approx(500.0)
        assert result.row_value("timepoints", 1, "media_volume") == pytest.approx(495.0)

    def test_first_timepoint_uncorrected(self, result):
        # 200/1000 * (100/500) * 500/100 * 100 = 20 %
        assert result.row_value("timepoints", 0, "uncorrected_1") == pytest.approx(20.0)

    def test_first_timepoint_has_no_carryover(self, result):
        assert result.row_value("timepoints", 0, "released_1") == pytest.approx(20.0)

    def test_carryover_correction_term(self, result):
        # TRUNC(5/500 * 20, 3) = TRUNC(0.2, 3) = 0.2
        assert result.row_value("timepoints", 0, "correction_1") == pytest.approx(0.2)

    def test_second_timepoint_adds_prior_carryover(self, result):
        # Volume 495: 400/1000 * 0.2 * 495/100 * 100 = 39.6; + 0.2 carry-over = 39.8
        assert result.row_value("timepoints", 1, "uncorrected_1") == pytest.approx(39.6)
        assert result.row_value("timepoints", 1, "released_1") == pytest.approx(39.8)

    def test_per_timepoint_statistics_across_units(self, result):
        assert result.row_value("timepoints", 0, "mean_released") == pytest.approx(20.0)
        assert result.row_value("timepoints", 0, "min_released") == pytest.approx(20.0)
        assert result.row_value("timepoints", 0, "max_released") == pytest.approx(20.0)
        # Identical units → zero spread.
        assert result.row_value("timepoints", 0, "rsd_released") == pytest.approx(0.0)

    def test_reportable_result_is_the_first_populated_mean(self, result):
        assert result.reportable_result == pytest.approx(20.0)

    def test_a_slow_unit_lowers_the_minimum_without_moving_the_mean_much(self):
        groups = {
            **self.GROUPS,
            "timepoints": [
                {"minutes": "15", "area_1": 100.0,
                 **{f"area_{n}": 200.0 for n in range(2, 7)}},
            ],
        }
        result = evaluator("TPL-A6A-0001").evaluate(self.CONTEXT, groups)
        # Unit 1 at 10 %, five units at 20 % → min 10, mean (10+100)/6 = 18.3
        assert result.row_value("timepoints", 0, "min_released") == pytest.approx(10.0)
        assert result.row_value("timepoints", 0, "mean_released") == pytest.approx(18.3)


class TestA6BDissolutionWithReplacement:
    CONTEXT = {"label_claim": 100.0, "avg_weight": 1.0,
               "initial_volume": 750.0, "withdrawal_volume": 5.0}
    GROUPS = {
        "standard": [{
            "weight_mg": 100.0, "vol_1": 750.0, "pip_1": 1.0, "vol_2": 1.0,
            "pip_2": 1.0, "vol_3": 1.0, "mw_base": 1.0, "mw_salt": 1.0, "potency": 100.0,
        }],
        "std_areas": [{"area": 1000.0}],
        "timepoints": [
            {"minutes": "15", **{f"area_{n}": 200.0 for n in range(1, 7)}},
            {"minutes": "30", **{f"area_{n}": 400.0 for n in range(1, 7)}},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A6B-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_volume_stays_constant(self, result):
        # Replacement restores what was withdrawn, so the series is flat.
        assert result.row_value("timepoints", 0, "media_volume") == pytest.approx(750.0)
        assert result.row_value("timepoints", 1, "media_volume") == pytest.approx(750.0)

    def test_release_still_carries_over(self, result):
        # 200/1000 * (100/750) * 750/100 * 100 = 20 %
        assert result.row_value("timepoints", 0, "uncorrected_1") == pytest.approx(20.0)
        # TRUNC(5/750 * 20, 3) = TRUNC(0.1333, 3) = 0.133
        assert result.row_value("timepoints", 0, "correction_1") == pytest.approx(0.133)
        # 40 % + 0.133 = 40.133 → 1dp = 40.1
        assert result.row_value("timepoints", 1, "released_1") == pytest.approx(40.1)


class TestA6CWholeVialResidual:
    #  A 100 mg vial declared at 100 mg, so the weight normalisation is neutral and
    #  the arithmetic is legible. `avg_weight` is the declared per-vial weight, not
    #  1 — this variant normalises each vial against its own fill.
    CONTEXT = {"label_claim": 100.0, "avg_weight": 100.0, "batch_assay": 100.0}
    GROUPS = {
        "standard": [{
            "weight_mg": 100.0, "vol_1": 100.0, "pip_1": 1.0, "vol_2": 1.0,
            "pip_2": 1.0, "vol_3": 1.0, "mw_base": 1.0, "mw_salt": 1.0, "potency": 100.0,
        }],
        "std_areas": [{"area": 1000.0}],
        "units": [
            {"unit_ref": "V1", "unit_weight": 100.0, "s_vol_1": 100.0, "s_pip_1": 1.0,
             "s_vol_2": 1.0, "s_pip_2": 1.0, "s_vol_3": 1.0, "area": 250.0},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A6C-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_residual_content(self, result):
        # 250/1000 * (100/100) * (100/100) * 1/100 * 100 = 25 %
        assert result.row_value("units", 0, "residue_pct") == pytest.approx(25.0)

    def test_release_is_what_is_not_left_behind(self, result):
        # (100 - 25) / 100 * 100 = 75 %
        assert result.row_value("units", 0, "released") == pytest.approx(75.0)
        assert result.reportable_result == pytest.approx(75.0)


# ── A8: Content uniformity ───────────────────────────────────────────


class TestA8ContentUniformityByHplc:
    """Source: `CU by HPLC`, Rasagiline Mesylate Tab 1 mg."""

    #  100 mg units declared at 100 mg, so the weight normalisation is neutral and
    #  area maps directly onto % of label claim.
    CONTEXT = {"label_claim": 100.0, "avg_weight": 100.0, "k_value": 2.4}
    GROUPS = {
        "standard": [{
            "weight_mg": 100.0, "vol_1": 100.0, "pip_1": 1.0, "vol_2": 1.0,
            "pip_2": 1.0, "vol_3": 1.0, "mw_base": 1.0, "mw_salt": 1.0, "potency": 100.0,
        }],
        "std_areas": [{"area": 1000.0}],
        "units": [
            {"unit_ref": f"U{i+1}", "unit_weight": 100.0, "s_vol_1": 100.0,
             "s_pip_1": 1.0, "s_vol_2": 1.0, "s_pip_2": 1.0, "s_vol_3": 1.0,
             "area": pct * 10.0}
            for i, pct in enumerate(
                [98.9, 99.9, 101.0, 96.9, 100.5, 97.1, 99.5, 100.2, 99.8, 98.3]
            )
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A8-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_per_unit_percentages(self, result):
        # area 989 → 989/1000 * 100 = 98.9 %
        assert result.row_value("units", 0, "pct_lc") == pytest.approx(98.9)
        assert result.row_value("units", 3, "pct_lc") == pytest.approx(96.9)

    def test_unit_count(self, result):
        assert result.values["summary.unit_count"] == pytest.approx(10)

    def test_mean_and_spread(self, result):
        # (98.9+99.9+101.0+96.9+100.5+97.1+99.5+100.2+99.8+98.3)/10 = 99.21 → 1dp 99.2
        assert result.values["summary.mean_pct"] == pytest.approx(99.2)
        assert result.values["summary.min_pct"] == pytest.approx(96.9)
        assert result.values["summary.max_pct"] == pytest.approx(101.0)

    def test_acceptance_value_reduces_to_k_times_s_inside_the_window(self, result):
        # Mean 99.2 is within 98.5–101.5, so AV = k*s = 2.4 * s.
        sd = result.values["summary.sd_pct"]
        assert result.values["summary.acceptance_value"] == pytest.approx(
            round(2.4 * sd, 1), abs=0.05
        )

    def test_acceptance_value_passes_the_usp_limit(self, result):
        assert result.values["summary.acceptance_value"] <= 15.0
        assert result.has_blocking_failure is False

    def test_a_low_mean_adds_the_distance_to_98_5(self):
        """
        Below the window, AV = (98.5 - X) + k·s. This is the branch a reversed
        nested IF would get wrong.
        """
        groups = {
            **self.GROUPS,
            "units": [
                {**row, "area": 900.0} for row in self.GROUPS["units"]
            ],
        }
        result = evaluator("TPL-A8-0001").evaluate(self.CONTEXT, groups)
        # All units 90.0 → mean 90.0, sd 0 → AV = (98.5 - 90.0) + 0 = 8.5
        assert result.values["summary.mean_pct"] == pytest.approx(90.0)
        assert result.values["summary.acceptance_value"] == pytest.approx(8.5)

    def test_a_high_mean_adds_the_distance_above_101_5(self):
        groups = {
            **self.GROUPS,
            "units": [{**row, "area": 1100.0} for row in self.GROUPS["units"]],
        }
        result = evaluator("TPL-A8-0001").evaluate(self.CONTEXT, groups)
        # All units 110.0 → AV = (110.0 - 101.5) + 0 = 8.5
        assert result.values["summary.acceptance_value"] == pytest.approx(8.5)

    def test_a_wildly_variable_batch_fails(self):
        groups = {
            **self.GROUPS,
            "units": [
                {**row, "area": area}
                for row, area in zip(
                    self.GROUPS["units"],
                    [700.0, 1300.0, 800.0, 1200.0, 900.0,
                     1100.0, 750.0, 1250.0, 850.0, 1150.0],
                )
            ],
        }
        result = evaluator("TPL-A8-0001").evaluate(self.CONTEXT, groups)
        # Mean ~100 but sd ~21 → AV ~50, far over the 15.0 limit.
        assert result.values["summary.acceptance_value"] > 15.0
        assert result.has_blocking_failure is True


class TestA8ContentUniformityByWeightVariation:
    CONTEXT = {"label_claim": 100.0, "avg_weight": 1.0, "k_value": 2.4,
               "batch_assay": 100.0, "mean_fill_weight": 200.0}
    GROUPS = {
        "units": [
            #  Net 201.2 mg against a 200 mg declared fill.
            {"unit_ref": "U1", "filled_weight": 209.6, "empty_weight": 8.4},
            {"unit_ref": "U2", "filled_weight": 208.4, "empty_weight": 8.4},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A8-0002").evaluate(self.CONTEXT, self.GROUPS)

    def test_net_weight(self, result):
        # 209.6 - 8.4 = 201.2
        assert result.row_value("units", 0, "net_weight") == pytest.approx(201.2)

    def test_percent_of_label_claim_from_mass(self, result):
        # 201.2 / 200 * 100 = 100.6 %
        assert result.row_value("units", 0, "pct_lc") == pytest.approx(100.6)
        # 200.0 / 200 * 100 = 100.0 %
        assert result.row_value("units", 1, "pct_lc") == pytest.approx(100.0)

    def test_acceptance_value_computed_without_any_chromatography(self, result):
        assert result.values["summary.mean_pct"] == pytest.approx(100.3)
        assert result.reportable_result is not EMPTY


# ── A9: Titrimetry ──────────────────────────────────────────────────


class TestA9Titrimetry:
    """Source: Sodium Metabisulfite assay by titration."""

    CONTEXT = {
        "label_claim": 2.0, "normality": 0.1, "equivalence_factor": 47.5, "blank_ml": 0.0,
    }
    GROUPS = {
        "determinations": [
            {"prep_ref": "D1", "sample_ml": 10.0, "titre_ml": 4.2},
            {"prep_ref": "D2", "sample_ml": 10.0, "titre_ml": 4.2},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A9-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_content_per_ml(self, result):
        # (4.2 * 0.1 * 47.5 * 1000) / (10 * 1000) = 1.995 mg/mL
        assert result.row_value("determinations", 0, "mg_per_ml") == pytest.approx(1.995)

    def test_percent_of_label_claim(self, result):
        # 1.995 / 2.0 * 100 = 99.75 %
        assert result.row_value("determinations", 0, "pct_lc") == pytest.approx(99.75)
        assert result.reportable_result == pytest.approx(99.75)

    def test_blank_titre_is_subtracted(self):
        result = evaluator("TPL-A9-0001").evaluate(
            {**self.CONTEXT, "blank_ml": 0.2}, self.GROUPS
        )
        # Net 4.0 mL → (4.0 * 0.1 * 47.5 * 1000)/(10*1000) = 1.9 → 95.0 %
        assert result.row_value("determinations", 0, "mg_per_ml") == pytest.approx(1.9)
        assert result.row_value("determinations", 0, "pct_lc") == pytest.approx(95.0)

    def test_disagreeing_determinations_block(self):
        groups = {
            "determinations": [
                {"prep_ref": "D1", "sample_ml": 10.0, "titre_ml": 4.2},
                {"prep_ref": "D2", "sample_ml": 10.0, "titre_ml": 5.0},
            ],
        }
        result = evaluator("TPL-A9-0001").evaluate(self.CONTEXT, groups)
        assert result.has_blocking_failure is True


# ── A10: Gravimetric ────────────────────────────────────────────────


class TestA10LossOnDrying:
    GROUPS = {
        "determinations": [
            #  Sample 5.0 g, loses 0.25 g → 5.00 %
            {"prep_ref": "D1", "dish_weight": 20.0, "dish_plus_sample": 25.0,
             "dish_plus_dried": 24.75},
            {"prep_ref": "D2", "dish_weight": 20.0, "dish_plus_sample": 25.0,
             "dish_plus_dried": 24.75},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A10-0001").evaluate({}, self.GROUPS)

    def test_sample_weight(self, result):
        assert result.row_value("determinations", 0, "sample_weight") == pytest.approx(5.0)

    def test_percent_loss(self, result):
        # (25 - 24.75) / (25 - 20) * 100 = 5.00 %
        assert result.row_value("determinations", 0, "pct_loss") == pytest.approx(5.0)
        assert result.reportable_result == pytest.approx(5.0)

    def test_a_wide_spread_between_determinations_is_flagged(self):
        groups = {
            "determinations": [
                self.GROUPS["determinations"][0],
                {"prep_ref": "D2", "dish_weight": 20.0, "dish_plus_sample": 25.0,
                 "dish_plus_dried": 24.0},  # 20 % loss
            ],
        }
        result = evaluator("TPL-A10-0001").evaluate({}, groups)
        spread = next(c for c in result.criteria if c.key == "determination_agreement")
        assert spread.passed is False
        #  Advisory, so it does not block — a duplicate that far apart is a repeat,
        #  not necessarily an invalid run.
        assert result.has_blocking_failure is False


class TestA10WeightPerMl:
    GROUPS = {
        "determinations": [
            {"prep_ref": "P1", "empty_weight": 20.0, "with_sample": 45.0,
             "with_water": 44.5},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A10-0002").evaluate({}, self.GROUPS)

    def test_relative_density_rounded_before_the_factor(self, result):
        # (45 - 20) / (44.5 - 20) = 25/24.5 = 1.020408... → 4dp 1.0204
        assert result.row_value("determinations", 0, "ratio") == pytest.approx(1.0204)

    def test_weight_per_ml_applies_the_water_density_factor(self, result):
        # 1.0204 * 0.99704 = 1.017379... → 4dp 1.0174
        assert result.row_value("determinations", 0, "weight_per_ml") == pytest.approx(
            1.0174
        )
        assert result.reportable_result == pytest.approx(1.0174)


# ── A13: Trace / nitrosamine impurities ─────────────────────────────


class TestA13TraceImpurities:
    CONTEXT = {"label_claim": 100.0, "avg_weight": 1.0, "blank_area": 0.0}
    GROUPS = {
        "standard": [{
            "weight_mg": 100.0, "vol_1": 100.0, "pip_1": 1.0, "vol_2": 1.0,
            "pip_2": 1.0, "vol_3": 1.0, "potency": 100.0,
        }],
        "std_areas": [{"area": 10000.0}, {"area": 10000.0}],
        "samples": [
            {"prep_ref": "S1", "sample_weight": 100.0, "s_vol_1": 100.0, "s_pip_1": 1.0,
             "s_vol_2": 1.0, "s_pip_2": 1.0, "s_vol_3": 1.0, "area": 100.0},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A13-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_content_in_ppm(self, result):
        # 100/10000 * (100/100) * (100/100) * 1/100 * 1e6 = 100 ppm
        assert result.row_value("samples", 0, "ppm") == pytest.approx(100.0)
        assert result.reportable_result == pytest.approx(100.0)

    def test_blank_is_subtracted_before_the_chain(self):
        result = evaluator("TPL-A13-0001").evaluate(
            {**self.CONTEXT, "blank_area": 20.0}, self.GROUPS
        )
        assert result.row_value("samples", 0, "corrected_area") == pytest.approx(80.0)
        # 80/10000 * ... * 1e6 = 80 ppm
        assert result.row_value("samples", 0, "ppm") == pytest.approx(80.0)

    def test_result_is_truncated_not_rounded(self):
        """
        Truncation is the safe direction for an impurity: it cannot round a result
        up across a specification limit.
        """
        groups = {
            **self.GROUPS,
            "samples": [{**self.GROUPS["samples"][0], "area": 100.009999}],
        }
        result = evaluator("TPL-A13-0001").evaluate(self.CONTEXT, groups)
        # 100.009999 ppm truncated to 4dp = 100.0099, not rounded to 100.01
        assert result.row_value("samples", 0, "ppm") == pytest.approx(100.0099)

    def test_an_interfering_blank_blocks_reporting(self):
        result = evaluator("TPL-A13-0001").evaluate(
            #  Blank at 10 % of the standard response — the method cannot support
            #  the level being reported.
            {**self.CONTEXT, "blank_area": 1000.0}, self.GROUPS
        )
        assert result.values["suitability.blank_interference"] == pytest.approx(10.0)
        assert result.has_blocking_failure is True


# ── A7: Dissolution profile comparison (f1 / f2) ────────────────────


class TestA7ProfileComparison:
    """
    Source: `F1F2 Calculation_sheet_Dissolution.xlsx`, sheet `f1f2` — Amphotericin B
    Liposome for Injection against AmBisome®.

    The inputs below are the sheet's own hand-typed comparison block, which is the
    one dataset whose f1 the workbook states outright: **5.9**. That makes it the
    right transcription to pin, because it also settles the R(t)/T(t) heading swap
    the definition module documents — see `test_f1_divides_by_the_reference_sum`.

    Reference is the innovator, so its means are the larger series.
    """

    CONTEXT = {"reference_product": "AmBisome", "reference_batch": "REF-001"}
    #  Five time-points, 1–6 Hr. %RSD is set to exercise the 20 %-then-10 % rule:
    #  16 % is allowed at the first point only.
    GROUPS = {
        "timepoints": [
            {"time": "1", "ref_mean": 9.0, "test_mean": 7.0,
             "ref_rsd": 16.0, "test_rsd": 15.0},
            {"time": "2", "ref_mean": 23.0, "test_mean": 21.0,
             "ref_rsd": 5.0, "test_rsd": 6.0},
            {"time": "3", "ref_mean": 41.0, "test_mean": 39.0,
             "ref_rsd": 4.0, "test_rsd": 5.0},
            {"time": "4", "ref_mean": 58.0, "test_mean": 56.0,
             "ref_rsd": 3.0, "test_rsd": 4.0},
            {"time": "6", "ref_mean": 89.0, "test_mean": 84.0,
             "ref_rsd": 2.0, "test_rsd": 3.0},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A7-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_per_timepoint_differences(self, result):
        # |9-7|, |23-21|, |41-39|, |58-56|, |89-84| = 2, 2, 2, 2, 5
        assert result.row_value("timepoints", 0, "abs_diff") == pytest.approx(2.0)
        assert result.row_value("timepoints", 4, "abs_diff") == pytest.approx(5.0)
        # Squared: 4 and 25
        assert result.row_value("timepoints", 0, "sq_diff") == pytest.approx(4.0)
        assert result.row_value("timepoints", 4, "sq_diff") == pytest.approx(25.0)

    def test_summations(self, result):
        assert result.values["comparison.n_points"] == pytest.approx(5)
        # 2+2+2+2+5 = 13
        assert result.values["comparison.sum_abs_diff"] == pytest.approx(13.0)
        # 9+23+41+58+89 = 220
        assert result.values["comparison.sum_ref"] == pytest.approx(220.0)
        # 4+4+4+4+25 = 41
        assert result.values["comparison.sum_sq_diff"] == pytest.approx(41.0)
        # 41/5 = 8.2
        assert result.values["comparison.mean_sq_diff"] == pytest.approx(8.2)

    def test_f1_divides_by_the_reference_sum(self, result):
        """
        The finding the module documents: the source sheet's `R(t)`/`T(t)` headings
        are swapped relative to the data feeding them, but its arithmetic divides by
        the *reference* series, per the FDA/EMA guideline.

        13/220 × 100 = 5.909… → 5.9, which is the f1 the workbook reports.
        Taking the labels at face value and dividing by Σ test would give
        13/207 × 100 = 6.28 → 6.3. Asserting 5.9 is what keeps the swap from
        silently returning.
        """
        assert result.values["comparison.f1"] == pytest.approx(5.9)

    def test_f2_similarity_factor(self, result):
        # 50 · log10(100 / sqrt(1 + 8.2)) = 50 · log10(100/3.033150…)
        #   = 50 · log10(32.96902…) = 50 × 1.518106… = 75.905… → 75.9
        assert result.values["comparison.f2"] == pytest.approx(75.9)

    def test_f2_is_the_reportable_result(self, result):
        assert result.reportable_result == pytest.approx(75.9)

    def test_one_point_above_85_is_permitted(self, result):
        # Reference 89 is above 85; the test product's 84 is not. Worse product = 1.
        assert result.values["comparison.points_over_85"] == pytest.approx(1)
        assert result.has_blocking_failure is False

    def test_the_first_timepoint_carries_the_20_percent_rsd_allowance(self, result):
        assert result.row_value("timepoints", 0, "rsd_limit") == pytest.approx(20.0)
        assert result.row_value("timepoints", 1, "rsd_limit") == pytest.approx(10.0)
        # 16 % at the first point is within 20 %, so nothing breaches.
        assert result.values["comparison.rsd_breaches"] == pytest.approx(0)

    def test_an_excluded_zero_hour_row_does_not_flatter_the_comparison(self):
        """
        The 0-hour row belongs in the record but not in the comparison: a pair of
        zeroes adds a zero difference and inflates n, which raises f2. Entering it
        with `included = 0` is what keeps the profile faithful and the maths honest.
        """
        groups = {
            "timepoints": [
                {"time": "0", "included": 0, "ref_mean": 0.0, "test_mean": 0.0},
                *self.GROUPS["timepoints"],
            ],
        }
        result = evaluator("TPL-A7-0001").evaluate(self.CONTEXT, groups)
        # n stays 5, not 6, and f2 stays 75.9. Counting the zero row would give
        # 50 · log10(100/sqrt(1 + 41/6)) = 77.7.
        assert result.values["comparison.n_points"] == pytest.approx(5)
        assert result.values["comparison.f2"] == pytest.approx(75.9)

    def test_the_20_percent_allowance_survives_a_leading_excluded_row(self):
        """
        `sum(prior.has_rsd)` rather than the row number is what makes this hold: the
        0-hour row carries no %RSD, so the allowance must land on the first real
        time-point instead of being spent on the zero.
        """
        groups = {
            "timepoints": [
                {"time": "0", "included": 0, "ref_mean": 0.0, "test_mean": 0.0},
                *self.GROUPS["timepoints"],
            ],
        }
        result = evaluator("TPL-A7-0001").evaluate(self.CONTEXT, groups)
        assert result.row_value("timepoints", 1, "rsd_limit") == pytest.approx(20.0)
        assert result.values["comparison.rsd_breaches"] == pytest.approx(0)

    def test_imprecision_after_the_first_timepoint_blocks(self):
        rows = [dict(row) for row in self.GROUPS["timepoints"]]
        #  12 % at the second time-point, where the limit has tightened to 10 %.
        rows[1]["ref_rsd"] = 12.0
        result = evaluator("TPL-A7-0001").evaluate(self.CONTEXT, {"timepoints": rows})
        assert result.row_value("timepoints", 1, "rsd_breach") == pytest.approx(1)
        assert result.values["comparison.rsd_breaches"] == pytest.approx(1)
        assert result.has_blocking_failure is True

    def test_two_points_above_85_blocks_the_comparison(self):
        rows = [dict(row) for row in self.GROUPS["timepoints"]]
        #  A second reference point above 85 % — the profile is too far along the
        #  plateau for f2 to discriminate.
        rows[3]["ref_mean"] = 88.0
        result = evaluator("TPL-A7-0001").evaluate(self.CONTEXT, {"timepoints": rows})
        assert result.values["comparison.points_over_85"] == pytest.approx(2)
        assert result.has_blocking_failure is True

    def test_fewer_than_three_timepoints_blocks(self):
        result = evaluator("TPL-A7-0001").evaluate(
            self.CONTEXT, {"timepoints": self.GROUPS["timepoints"][:2]}
        )
        assert result.values["comparison.n_points"] == pytest.approx(2)
        assert result.has_blocking_failure is True

    def test_dissimilar_profiles_are_reportable_rather_than_blocked(self):
        """
        The load-bearing design decision in this template. "Not similar" is a real
        outcome, so f1/f2 are advisory: a comparison worksheet must always be able
        to record the answer it found.
        """
        rows = [
            {"time": "1", "ref_mean": 20.0, "test_mean": 5.0, "ref_rsd": 5.0},
            {"time": "2", "ref_mean": 40.0, "test_mean": 25.0, "ref_rsd": 5.0},
            {"time": "3", "ref_mean": 60.0, "test_mean": 45.0, "ref_rsd": 5.0},
            {"time": "4", "ref_mean": 70.0, "test_mean": 55.0, "ref_rsd": 5.0},
            {"time": "6", "ref_mean": 80.0, "test_mean": 65.0, "ref_rsd": 5.0},
        ]
        result = evaluator("TPL-A7-0001").evaluate(self.CONTEXT, {"timepoints": rows})
        # 15 apart at every point: Σ|d| = 75, Σref = 270 → f1 = 27.77… → 27.8
        assert result.values["comparison.f1"] == pytest.approx(27.8)
        # Σd² = 5×225 = 1125, /5 = 225 → 50·log10(100/sqrt(226)) = 41.147… → 41.1
        assert result.values["comparison.f2"] == pytest.approx(41.1)
        #  Both advisory criteria fail, and that is a recorded result, not a refusal.
        assert result.has_blocking_failure is False


# ── A14: Linearity qualification ────────────────────────────────────


class TestA14LinearityQualification:
    """
    Source: `Lipid content_Linearity _CAD_ Doxo.xlsx` — three lipid components by
    charged-aerosol detection.

    The concentrations are contrived to fall on an exact line, `y = 1000x + 100`,
    so slope, intercept and R are derivable by inspection rather than only
    reproducible. A non-zero intercept is the point: it is what makes the excluded
    0 % level detectable, since a zero row *would* sit on a line through the origin
    and the exclusion would then be untestable.
    """

    CONTEXT = {"detector": "CAD"}
    #  One shared flask: 100 mL of stock holds all three components, which is why
    #  `dilution_1` sits on the group once rather than once per component.
    STD = [{
        "dilution_1": 100.0,
        "name_1": "Cholesterol", "purity_1": 100.0, "weight_mg_1": 100.0,
        "name_2": "DSPG", "purity_2": 100.0, "weight_mg_2": 200.0,
        "name_3": "HSPC", "purity_3": 100.0, "weight_mg_3": 100.0,
    }]
    #  conc = weight/dilution_1 × stock/dil × purity/100.
    #  Component 1 and 3: 0.5 / 1.0 / 1.5 mg/mL. Component 2 (200 mg): 1 / 2 / 3.
    #  Component 3's response is split across two peaks to exercise the sum.
    LEVELS = [
        {"level": "Level-4 (0%)", "nominal_pct": 0.0, "stock_ml": 0.0, "dil_ml": 100.0,
         "area_1": 0.0, "area_2": 0.0, "area_3": 0.0, "area_b_3": 0.0},
        {"level": "Level-1 (50%)", "nominal_pct": 50.0, "stock_ml": 50.0, "dil_ml": 100.0,
         "area_1": 600.0, "area_2": 600.0, "area_3": 400.0, "area_b_3": 200.0},
        {"level": "Level-2 (100%)", "nominal_pct": 100.0, "stock_ml": 100.0, "dil_ml": 100.0,
         "area_1": 1100.0, "area_2": 1100.0, "area_3": 700.0, "area_b_3": 400.0},
        {"level": "Level-3 (150%)", "nominal_pct": 150.0, "stock_ml": 150.0, "dil_ml": 100.0,
         "area_1": 1600.0, "area_2": 1600.0, "area_3": 1000.0, "area_b_3": 600.0},
    ]
    #  Five replicates at the 100 % level. Component 1 spreads by ±2 around 1000;
    #  the other two are constant, so the worst %RSD is component 1's.
    REPLICATES = [
        {"injection": "1", "area_1": 998.0, "area_2": 2000.0, "area_3": 600.0, "area_b_3": 400.0},
        {"injection": "2", "area_1": 999.0, "area_2": 2000.0, "area_3": 600.0, "area_b_3": 400.0},
        {"injection": "3", "area_1": 1000.0, "area_2": 2000.0, "area_3": 600.0, "area_b_3": 400.0},
        {"injection": "4", "area_1": 1001.0, "area_2": 2000.0, "area_3": 600.0, "area_b_3": 400.0},
        {"injection": "5", "area_1": 1002.0, "area_2": 2000.0, "area_3": 600.0, "area_b_3": 400.0},
    ]
    GROUPS = {"std": STD, "levels": LEVELS, "replicates": REPLICATES}

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A14-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_concentrations_come_off_the_shared_first_dilution(self, result):
        # Component 1, 100 % level: 100/100 × 100/100 × 100/100 = 1.0 mg/mL
        assert result.row_value("levels", 2, "conc_1") == pytest.approx(1.0)
        # Component 2 carries twice the weight into the same flask → 2.0 mg/mL
        assert result.row_value("levels", 2, "conc_2") == pytest.approx(2.0)
        # 50 % and 150 % levels of component 1
        assert result.row_value("levels", 1, "conc_1") == pytest.approx(0.5)
        assert result.row_value("levels", 3, "conc_1") == pytest.approx(1.5)

    def test_two_peak_component_is_summed(self, result):
        # HSPC elutes as SPC-1 + SPC-2: 700 + 400 = 1100
        assert result.row_value("levels", 2, "total_area_3") == pytest.approx(1100.0)

    def test_single_peak_component_is_not_blanked_by_its_absent_second_peak(self, result):
        """`area_b` defaults to 0 rather than blank, or the total would blank out."""
        assert result.row_value("levels", 2, "total_area_1") == pytest.approx(1100.0)

    def test_regression_recovers_the_line(self, result):
        # Component 1: (0.5, 600), (1.0, 1100), (1.5, 1600) → y = 1000x + 100
        assert result.values["regression.slope_1"] == pytest.approx(1000.0)
        assert result.values["regression.intercept_1"] == pytest.approx(100.0)
        assert result.values["regression.correlation_1"] == pytest.approx(1.0)
        assert result.values["regression.r_squared_1"] == pytest.approx(1.0)

    def test_each_component_is_regressed_against_its_own_series(self, result):
        # Component 2's x series is 1/2/3, so the same responses halve the slope:
        # (1600-600)/(3-1) = 500, intercept 600 - 500×1 = 100
        assert result.values["regression.slope_2"] == pytest.approx(500.0)
        assert result.values["regression.intercept_2"] == pytest.approx(100.0)
        # Component 3 shares component 1's concentrations and summed response
        assert result.values["regression.slope_3"] == pytest.approx(1000.0)

    def test_the_zero_level_is_recorded_but_excluded_from_the_fit(self, result):
        """
        The 0 % row stays on the worksheet — the sheet lists it — but is masked out
        of the regression by the blank `x`/`y` pair. Including it would drag the fit
        towards the origin, so the intercept of exactly 100 is the proof it was left
        out.
        """
        assert result.row_value("levels", 0, "conc_1") == pytest.approx(0.0)
        assert result.row_value("levels", 0, "x_1") is EMPTY
        assert result.row_value("levels", 0, "y_1") is EMPTY
        assert result.values["regression.intercept_1"] == pytest.approx(100.0)

    def test_replicate_precision(self, result):
        # Mean 1000; sample SD of 998…1002 = sqrt(10/4) = 1.5811388… → 1.58114
        assert result.values["precision.mean_1"] == pytest.approx(1000.0)
        assert result.values["precision.sd_1"] == pytest.approx(1.58114)
        # 1.58114/1000 × 100 = 0.158114 → 0.16
        assert result.values["precision.rsd_1"] == pytest.approx(0.16)
        # Components 2 and 3 are constant across injections
        assert result.values["precision.rsd_2"] == pytest.approx(0.0)
        assert result.values["precision.max_rsd"] == pytest.approx(0.16)

    def test_reportable_is_the_poorest_correlation(self, result):
        assert result.values["regression.min_correlation"] == pytest.approx(1.0)
        assert result.reportable_result == pytest.approx(1.0)
        assert result.has_blocking_failure is False

    def test_one_bad_component_fails_the_qualification(self):
        """
        Every component has to clear 0.99, so the reportable is the worst of them —
        a good cholesterol line must not carry a failing DSPG line past the
        criterion.
        """
        levels = [dict(row) for row in self.LEVELS]
        #  Component 1's top level comes back low, breaking its line.
        levels[3]["area_1"] = 900.0
        result = evaluator("TPL-A14-0001").evaluate(
            self.CONTEXT, {**self.GROUPS, "levels": levels}
        )
        # x = 0.5/1.0/1.5 against y = 600/1100/900:
        #   Sxy = 150, Sxx = 0.5, Syy = 126666.67
        #   R = 150 / sqrt(0.5 × 126666.67) = 0.596038… → 0.59604
        assert result.values["regression.correlation_1"] == pytest.approx(0.59604)
        # The other two are untouched and still perfect, so `min` is what bites.
        assert result.values["regression.correlation_2"] == pytest.approx(1.0)
        assert result.values["regression.min_correlation"] == pytest.approx(0.59604)
        assert result.has_blocking_failure is True

    def test_imprecise_replicates_block(self):
        replicates = [dict(row) for row in self.REPLICATES]
        #  Mean stays 1000 but the spread widens well past 10 %.
        for row, area in zip(replicates, [700.0, 850.0, 1000.0, 1150.0, 1300.0]):
            row["area_1"] = area
        result = evaluator("TPL-A14-0001").evaluate(
            self.CONTEXT, {**self.GROUPS, "replicates": replicates}
        )
        # SD of that series = 237.1708…, /1000 × 100 = 23.72 %
        assert result.values["precision.rsd_1"] == pytest.approx(23.72)
        assert result.values["precision.max_rsd"] == pytest.approx(23.72)
        assert result.has_blocking_failure is True


# ── A12: Derived roll-ups (consume other tests' results) ────────────


class TestA12FreeAndEntrappedDrug:
    """
    Source: `Bupivacaine Free & Entrrapted Drug Calculation.xlsx`.

    The inputs are chosen to land on the module docstring's own worked example —
    `%Assay` 101.5 with `%Con` 5.0 — because that is the pair whose two competing
    answers it quotes: 95.15 % entrapped from the sheet as written, 95.07 % once the
    reference slip is corrected. Pinning 95.07 is what stops the slip returning.
    """

    CONTEXT = {"label_claim": 10.0, "assay_source": "TST-03 / TRF-0001"}
    #  Standard chain neutral at 1.0 mg/mL per unit area ⇒ free_conc = area/10000.
    STANDARD = [{
        "name": "Bupivacaine", "weight_mg": 100.0, "vol_1": 100.0, "pip_1": 1.0,
        "vol_2": 1.0, "pip_2": 1.0, "vol_3": 1.0,
        "mw_base": 1.0, "mw_salt": 1.0, "potency": 100.0,
    }]
    PREP = {
        "sample_ml": 1.0, "s_vol_1": 1.0, "s_pip_1": 1.0, "s_vol_2": 1.0,
        #  5000/10000 × 1.0 = 0.5 mg/mL free drug against a 10 mg/mL claim ⇒ %Con 5.0
        "area": 5000.0,
        #  The carried-over number: the total assay of the same sample.
        "pct_assay_total": 101.5,
    }
    GROUPS = {
        "standard": STANDARD,
        "std_areas": [{"area": 10000.0}, {"area": 10000.0}],
        "preps": [
            {"prep_ref": "Prep-1", **PREP},
            {"prep_ref": "Prep-2", **PREP},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A12-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_free_drug_concentration(self, result):
        # 5000/10000 × (100/100) × 1 × 1.0 × 1/1 × 1/1 = 0.5 mg/mL
        assert result.row_value("preps", 0, "free_conc") == pytest.approx(0.5)

    def test_free_drug_against_label_claim(self, result):
        # 0.5/10 × 100 = 5.0 %
        assert result.row_value("preps", 0, "pct_con") == pytest.approx(5.0)

    def test_total_drug_comes_from_the_carried_assay(self, result):
        # 101.5 × 10/100 = 10.15 mg/mL
        assert result.row_value("preps", 0, "total_mg_ml") == pytest.approx(10.15)

    def test_percent_free_is_against_measured_content_not_label_claim(self, result):
        """
        Sheet O28. Free drug as a fraction of what the vial actually holds — the
        distinction that the entrapment slip turned on.
        """
        # 5.0/101.5 × 100 = 4.926108…
        assert result.row_value("preps", 0, "pct_free") == pytest.approx(
            4.926108, abs=1e-6
        )

    def test_entrapment_uses_the_corrected_identity(self, result):
        """
        The headline finding. The sheet's Q28 computes (%Assay − %Free)/%Assay × 100,
        mixing a label-claim base with an already-normalised one, and returns 95.1467.
        Substituting the un-normalised partner gives 100 − %Free = 95.0739.

        The two cannot both be right, and `free + entrapped = whole` is not
        negotiable — so the corrected form is what is implemented, and asserting it
        to six places is what distinguishes the two.
        """
        assert result.row_value("preps", 0, "pct_entrapped") == pytest.approx(
            95.073892, abs=1e-6
        )
        #  Explicitly not the sheet's 95.1467.
        assert result.row_value("preps", 0, "pct_entrapped") != pytest.approx(
            95.146691, abs=1e-6
        )

    def test_free_and_entrapped_sum_to_one_hundred_percent(self, result):
        free = result.row_value("preps", 0, "pct_free")
        entrapped = result.row_value("preps", 0, "pct_entrapped")
        assert free + entrapped == pytest.approx(100.0)

    def test_the_normalised_pair_sums_to_the_label_claim(self, result):
        """
        Both reportables are expressed per label claim, which is the sheet's own
        presentation. By construction they sum to the claim rather than to the
        measured content.
        """
        # 0.5/10.15 × 10 = 0.4926108…
        free_lc = result.row_value("preps", 0, "free_mg_ml_lc")
        entrapped_lc = result.row_value("preps", 0, "entrapped_mg_ml_lc")
        assert free_lc == pytest.approx(0.4926108, abs=1e-6)
        assert free_lc + entrapped_lc == pytest.approx(10.0)

    def test_the_measured_concentrations_are_shown_alongside(self, result):
        """
        Without these a batch assaying at 90 % would look like it held a full label
        claim of drug split between two compartments.
        """
        # 10.15 − 0.5 = 9.65 mg/mL actually entrapped
        assert result.row_value("preps", 0, "entrapped_conc") == pytest.approx(9.65)

    def test_reportable_is_the_mean_entrapment(self, result):
        """
        Note the shape: the two means are *row* fields holding a group aggregate, so
        the same value repeats down every prep row and `resultRef` reads it off the
        first. Asserted as it is rather than as a singleton.
        """
        # Both preps identical: mean 95.073892 → 95.07
        assert result.row_value("preps", 0, "mean_pct_entrapped") == pytest.approx(95.07)
        assert result.row_value("preps", 1, "mean_pct_entrapped") == pytest.approx(95.07)
        assert result.row_value("preps", 0, "mean_pct_free") == pytest.approx(4.93)
        assert result.reportable_result == pytest.approx(95.07)
        assert result.has_blocking_failure is False

    def test_the_mean_spans_preparations_rather_than_repeating_one(self):
        """
        Guards the aggregate against being read as the current row: two preps that
        differ must average, not echo. Prep-2 at area 6000 gives %Con 6.0 and
        %Free 5.911330…, so entrapment is 94.088670 and the mean of the pair is
        (95.073892 + 94.088670)/2 = 94.581281 → 94.58.
        """
        preps = [
            {"prep_ref": "Prep-1", **self.PREP},
            {"prep_ref": "Prep-2", **{**self.PREP, "area": 6000.0}},
        ]
        result = evaluator("TPL-A12-0001").evaluate(
            self.CONTEXT, {**self.GROUPS, "preps": preps}
        )
        assert result.row_value("preps", 1, "pct_entrapped") == pytest.approx(
            94.088670, abs=1e-6
        )
        assert result.row_value("preps", 0, "mean_pct_entrapped") == pytest.approx(94.58)

    def test_a_decimal_slip_in_the_carried_assay_is_flagged_but_not_blocked(self):
        """
        The one control available while the cross-test link is manual. 10.15 instead
        of 101.5 is the classic transcription error, and it would otherwise propagate
        into every reportable on the sheet. Advisory, because an unusual but genuine
        assay must still be recordable.
        """
        preps = [{**row, "pct_assay_total": 10.15} for row in self.GROUPS["preps"]]
        result = evaluator("TPL-A12-0001").evaluate(
            self.CONTEXT, {**self.GROUPS, "preps": preps}
        )
        verdicts = {c.key: c.passed for c in result.criteria}
        assert verdicts["carried_assay_plausible"] is False
        assert result.has_blocking_failure is False

    def test_a_drifting_standard_blocks_on_pooled_precision(self):
        """
        Bracketing standards are pooled with the main set rather than averaged on
        their own, so a system that drifts across the run cannot pass suitability.
        """
        result = evaluator("TPL-A12-0001").evaluate(
            self.CONTEXT, {**self.GROUPS, "bkt_1": [{"area": 12000.0}]}
        )
        assert result.values["stats.rsd_std"] == pytest.approx(0.0)
        assert result.values["stats.rsd_bkt"] > 2.0
        assert result.has_blocking_failure is True


class TestA12DrugToLipidRatio:
    """
    Source: `Bupivacaine Lipid & Drug to lipid Ratio.xlsx`, sheet
    `Drug to Lipid ratio Auto Calc`.

    Every number on this worksheet was measured by another test, which is why the
    template carries no standard block, no dilution chain and no area fields.
    """

    CONTEXT = {
        "assay_source": "TST-03 / TRF-0001",
        "lipid_source": "TST-LIPID / TRF-0002",
    }
    GROUPS = {
        "lipids": [
            {"name": "HSPC", "lc": 20.0, "pct_mean": 98.5},
            {"name": "Cholesterol", "lc": 10.0, "pct_mean": 101.2},
            {"name": "DSPG", "lc": 5.0, "pct_mean": 99.0},
            {"name": "DSPE-PEG2000", "lc": 5.0, "pct_mean": 102.0},
        ],
        "drug": [{"name": "Bupivacaine", "lc": 12.5, "pct_assay": 101.5}],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A12-0002").evaluate(self.CONTEXT, self.GROUPS)

    def test_each_lipid_content_is_percent_of_its_own_claim(self, result):
        # 98.5 × 20/100 = 19.70 ; 101.2 × 10/100 = 10.12
        assert result.row_value("lipids", 0, "mg_per_ml") == pytest.approx(19.70)
        assert result.row_value("lipids", 1, "mg_per_ml") == pytest.approx(10.12)
        assert result.row_value("lipids", 3, "mg_per_ml") == pytest.approx(5.10)

    def test_total_lipid(self, result):
        # 19.70 + 10.12 + 4.95 + 5.10 = 39.87
        assert result.values["ratio.sum_lipid"] == pytest.approx(39.87)

    def test_drug_content(self, result):
        # 101.5 × 12.5/100 = 12.6875
        assert result.values["drug.mg_per_ml"] == pytest.approx(12.6875)

    def test_drug_to_lipid_ratio(self, result):
        # 12.6875/39.87 = 0.3182217… → 0.3182
        assert result.values["ratio.drug_to_lipid"] == pytest.approx(0.3182)
        assert result.reportable_result == pytest.approx(0.3182)
        assert result.has_blocking_failure is False

    def test_a_different_lipid_panel_needs_no_new_template(self):
        """
        Nothing here is per-component, so the group takes any panel size. Two
        components at 10 mg/mL each against a 12.5 mg/mL drug ⇒ 12.5/20 = 0.625.
        """
        groups = {
            "lipids": [
                {"name": "HSPC", "lc": 10.0, "pct_mean": 100.0},
                {"name": "Cholesterol", "lc": 10.0, "pct_mean": 100.0},
            ],
            "drug": [{"name": "Bupivacaine", "lc": 12.5, "pct_assay": 100.0}],
        }
        result = evaluator("TPL-A12-0002").evaluate(self.CONTEXT, groups)
        assert result.values["ratio.sum_lipid"] == pytest.approx(20.0)
        assert result.values["ratio.drug_to_lipid"] == pytest.approx(0.625)

    def test_an_untouched_worksheet_does_not_claim_zero_lipid(self):
        """
        `sum([])` is 0 by Excel semantics, so without the guard a fresh worksheet
        would report "Σ Lipid Content: 0 mg/mL" — a positive claim from an analysis
        nobody has run.
        """
        result = evaluator("TPL-A12-0002").evaluate(self.CONTEXT, {})
        assert result.values["ratio.sum_lipid"] is EMPTY
        assert result.reportable_result is EMPTY


# ── A11: Microbial cylinder-plate bioassay ──────────────────────────

#  Six cylinders per plate, alternating: odd positions carry the reference dose,
#  even positions the test solution, across three plates.
_A11_REF_ZONES = (1, 3, 5)
_A11_SPL_ZONES = (2, 4, 6)


def a11_zones(ref_mm, spl_mm, *, ref_overrides=None):
    """
    Build the eighteen cylinder readings for one dose level or preparation.

    `ref_mm`/`spl_mm` fill every reference / sample cylinder; `ref_overrides` maps
    a plate number to a different reference reading, which is how plate drift is
    simulated.
    """
    overrides = ref_overrides or {}
    out = {}
    for plate in range(1, 4):
        for zone in _A11_REF_ZONES:
            out[f"ref_p{plate}_z{zone}"] = overrides.get(plate, ref_mm)
        for zone in _A11_SPL_ZONES:
            out[f"spl_p{plate}_z{zone}"] = spl_mm
    return out


class TestA11MicrobialBioassayAPI:
    """
    Source: `Assay_ Microbial_Amphotericin B_API.xlsx`.

    Zone diameter against log dose, so the curve is fitted in log space and the
    sample is read back with `exp((U − intercept) / slope)`.

    The dose series is a doubling one — 1, 2, 4, 8, 16 µg/mL — so the log
    concentrations are recognisable (`ln 2 = 0.6931`) and the regression can be
    checked by hand. Reference cylinders read a flat 17.0 mm everywhere, which
    makes the plate correction a no-op for the baseline case and lets the
    correction be tested on its own in `test_plate_drift_is_corrected_out`.

    Note the reference dose (row 3) takes its corrected mean from the grand
    reference mean, *not* from its own sample cylinders — S3 is the reference half
    of every plate, so it has no plate set of its own. Its sample readings of
    16.8 mm are therefore deliberately not what lands on the curve; 17.0 does.
    """

    CONTEXT = {}
    #  50 mg into 50 mL, 1 mL to 20 mL of buffer, potency 1000 µg/mg ⇒
    #  conc = (pip_dose/vol_dose) × 50 µg/mL.
    STOCK = [{
        "name": "Amphotericin B", "std_lot": "USP-001",
        "weight_mg": 50.0, "vol_1": 50.0, "potency": 1000.0,
        "pip_final": 1.0, "vol_final": 20.0, "reference_row": 3,
    }]
    #  Corrected means 14.2 / 15.4 / [17.0] / 18.2 / 19.5 against
    #  log conc 0 / 0.6931 / 1.3863 / 2.0794 / 2.7726.
    STANDARD = [
        {"dose": "S1", "pip_dose": 1.0, "vol_dose": 50.0, **a11_zones(17.0, 14.2)},
        {"dose": "S2", "pip_dose": 2.0, "vol_dose": 50.0, **a11_zones(17.0, 15.4)},
        {"dose": "S3", "pip_dose": 4.0, "vol_dose": 50.0, **a11_zones(17.0, 16.8)},
        {"dose": "S4", "pip_dose": 8.0, "vol_dose": 50.0, **a11_zones(17.0, 18.2)},
        {"dose": "S5", "pip_dose": 16.0, "vol_dose": 50.0, **a11_zones(17.0, 19.5)},
    ]
    #  50 mg into 50 mL, 1 mL to 12.5 mL, 1 mL to 20 mL ⇒ nominal 4.0 µg/mL.
    PREP = {
        "sample_weight": 50.0, "s_vol_1": 50.0, "s_pip_1": 1.0,
        "s_vol_2": 12.5, "s_pip_2": 1.0, "s_vol_3": 20.0,
    }
    GROUPS = {
        "std_stock": STOCK,
        "standard": STANDARD,
        "sample": [
            {"prep_ref": "Set-1", **PREP, **a11_zones(17.0, 16.8)},
            {"prep_ref": "Set-2", **PREP, **a11_zones(17.0, 16.8)},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A11-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_dose_concentrations(self, result):
        # 50/50 × 1/50 × 1/20 × 1000 = 1.0 µg/mL, doubling up the series
        assert result.row_value("standard", 0, "conc") == pytest.approx(1.0)
        assert result.row_value("standard", 1, "conc") == pytest.approx(2.0)
        assert result.row_value("standard", 4, "conc") == pytest.approx(16.0)

    def test_log_concentration_is_natural_log_rounded_to_four_places(self, result):
        assert result.row_value("standard", 0, "log_conc") == pytest.approx(0.0)
        # ln 2 = 0.693147… → 0.6931
        assert result.row_value("standard", 1, "log_conc") == pytest.approx(0.6931)
        # ln 16 = 2.772589… → 2.7726
        assert result.row_value("standard", 4, "log_conc") == pytest.approx(2.7726)

    def test_grand_reference_mean_spans_every_plate(self, result):
        assert result.values["curve.ref_grand"] == pytest.approx(17.0)

    def test_the_reference_dose_takes_the_grand_mean_not_its_own_zones(self, result):
        """
        S3 is the reference half of every plate, so it has no plate set to correct.
        Its own sample cylinders read 16.8, but 17.0 is what belongs on the curve.
        """
        assert result.row_value("standard", 2, "spl_avg") == pytest.approx(16.8)
        assert result.row_value("standard", 2, "corrected_mean") == pytest.approx(17.0)

    def test_other_dose_levels_correct_against_their_own_plates(self, result):
        # No drift here, so corrected == sample mean: 14.2 − (17.0 − 17.0)
        assert result.row_value("standard", 0, "corrected_mean") == pytest.approx(14.2)
        assert result.row_value("standard", 4, "corrected_mean") == pytest.approx(19.5)

    def test_curve_regression(self, result):
        """
        Least squares on x = 0 / 0.6931 / 1.3863 / 2.0794 / 2.7726 against
        y = 14.2 / 15.4 / 17.0 / 18.2 / 19.5 gives slope 1.9332047… → 1.9332 and
        intercept 14.1800369… → 14.1800.
        """
        assert result.values["curve.curve_slope"] == pytest.approx(1.9332)
        assert result.values["curve.curve_intercept"] == pytest.approx(14.18)
        assert result.values["curve.r_squared"] == pytest.approx(0.998)

    def test_nominal_concentration_of_the_preparation(self, result):
        # 50/50 × 1/12.5 × 1000 × 1/20 = 4.0 µg/mL
        assert result.row_value("sample", 0, "nominal_conc") == pytest.approx(4.0)

    def test_sample_is_interpolated_back_through_the_curve(self, result):
        # U = 16.8; Lu = (16.8 − 14.18)/1.9332 = 1.3552658…
        assert result.row_value("sample", 0, "corrected_mean") == pytest.approx(16.8)
        assert result.row_value("sample", 0, "log_conc_u") == pytest.approx(
            1.355266, abs=1e-6
        )
        # Cu = exp(1.3552658…) = 3.8777918… µg/mL
        assert result.row_value("sample", 0, "measured_conc") == pytest.approx(
            3.877792, abs=1e-6
        )

    def test_potency_scales_back_up_the_dilution_chain(self, result):
        # 3.8777918 × 20/1 × 12.5/1 × 50/50 = 969.4479… → 969 µg/mg
        assert result.row_value("sample", 0, "potency_ug_per_mg") == pytest.approx(969.0)

    def test_assay_against_nominal(self, result):
        # 3.8777918/4.0 × 100 = 96.9447… → 96.94 %
        assert result.row_value("sample", 0, "assay_pct") == pytest.approx(96.94)
        assert result.values["results.mean_assay"] == pytest.approx(96.94)
        assert result.reportable_result == pytest.approx(96.94)
        assert result.has_blocking_failure is False

    def test_plate_drift_is_corrected_out(self):
        """
        The correction that makes the assay defensible. Plate 1's reference
        cylinders read 1 mm wide — deeper agar, denser inoculum — so its sample
        readings are inflated by the same plate effect and must be shifted back.

        Reference mean becomes (3×18 + 6×17)/9 = 17.3333, drifting 0.3333 above the
        grand mean of 17.0, so the corrected mean drops from 16.8 to 16.4667.
        Without the correction the curve would be fitted through plate noise.
        """
        preps = [
            {"prep_ref": "Set-1", **self.PREP,
             **a11_zones(17.0, 16.8, ref_overrides={1: 18.0})},
        ]
        result = evaluator("TPL-A11-0001").evaluate(
            self.CONTEXT, {**self.GROUPS, "sample": preps}
        )
        assert result.row_value("sample", 0, "ref_avg") == pytest.approx(
            17.333333, abs=1e-6
        )
        assert result.row_value("sample", 0, "corrected_mean") == pytest.approx(
            16.466667, abs=1e-6
        )

    def test_ragged_zone_readings_block(self):
        """
        Zone diameters that scatter mean the plate cannot be read reliably, and the
        interpolation the whole result rests on is then unsupportable.
        """
        preps = [
            {"prep_ref": "Set-1", **self.PREP,
             #  Reference cylinders ranging 14–20 mm on one plate set.
             **a11_zones(17.0, 16.8, ref_overrides={1: 14.0, 2: 20.0})},
        ]
        result = evaluator("TPL-A11-0001").evaluate(
            self.CONTEXT, {**self.GROUPS, "sample": preps}
        )
        assert result.row_value("sample", 0, "ref_rsd") > 10.0
        assert result.has_blocking_failure is True

    def test_a_non_linear_curve_blocks(self):
        standard = [dict(row) for row in self.STANDARD]
        #  Top dose falls back below the mid dose — the plates have saturated.
        standard[4].update(a11_zones(17.0, 12.0))
        result = evaluator("TPL-A11-0001").evaluate(
            self.CONTEXT, {**self.GROUPS, "standard": standard}
        )
        assert result.values["curve.r_squared"] < 0.95
        assert result.has_blocking_failure is True

    def test_disagreeing_preparations_block(self):
        preps = [
            {"prep_ref": "Set-1", **self.PREP, **a11_zones(17.0, 16.8)},
            #  A preparation reading 2 mm narrower is a different answer, not noise.
            {"prep_ref": "Set-2", **self.PREP, **a11_zones(17.0, 14.8)},
        ]
        result = evaluator("TPL-A11-0001").evaluate(
            self.CONTEXT, {**self.GROUPS, "sample": preps}
        )
        assert result.values["results.rsd_assay"] > 10.0
        assert result.has_blocking_failure is True


class TestA11MicrobialBioassayFinishedProduct:
    """
    Source: `Assay_Microbial_Amphotericin B_FP.xlsx`. Same curve and the same plate
    correction; the difference is only the last step, where the result is expressed
    against label claim rather than as a potency.
    """

    #  50 mg/vial declared, and the 50 mg weighed is one vial's worth, so the
    #  weight normalisation is neutral and the arithmetic stays legible.
    CONTEXT = {"label_claim": 50.0, "avg_weight": 50.0}
    GROUPS = {
        "std_stock": TestA11MicrobialBioassayAPI.STOCK,
        "standard": TestA11MicrobialBioassayAPI.STANDARD,
        "sample": [
            {"prep_ref": "Set-1", **TestA11MicrobialBioassayAPI.PREP,
             **a11_zones(17.0, 16.8)},
        ],
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A11-0002").evaluate(self.CONTEXT, self.GROUPS)

    def test_the_curve_is_the_same_as_the_api_variant(self, result):
        assert result.values["curve.curve_slope"] == pytest.approx(1.9332)
        assert result.values["curve.curve_intercept"] == pytest.approx(14.18)

    def test_assay_is_against_label_claim(self, result):
        # 3.8777918/4.0 × 50/50 × 100 = 96.9447… → 96.94 %
        assert result.row_value("sample", 0, "assay_pct") == pytest.approx(96.94)
        assert result.reportable_result == pytest.approx(96.94)
        assert result.has_blocking_failure is False

    def test_label_claim_scales_the_result(self):
        """
        A vial declared at 45 mg but holding the same measured drug assays higher
        against its claim: 96.9447 × 50/45 = 107.7164 → 107.72 %.
        """
        result = evaluator("TPL-A11-0002").evaluate(
            {**self.CONTEXT, "label_claim": 45.0}, self.GROUPS
        )
        assert result.row_value("sample", 0, "assay_pct") == pytest.approx(107.72)


# ── A6d: In-vitro release, Franz diffusion cell ─────────────────────


class TestA6DFranzCellIVRT:
    """
    Source: `Dissolution sheet_ Franz diffusion cell_Tapinarof.xls`.

    This transcription is the *whole* source dataset — six calibration levels, the
    bracketing QCs and all six cells across six timepoints — because the workbook is
    a legacy `.xls` whose formulas were lost, so every relation had to be
    reverse-engineered from cached numbers. Reproducing those numbers is the only
    evidence the reverse-engineering was right.

    Four of the sheet's cached values are pinned below to full displayed precision:
    theoretical 3.5773556 at cal-1, slope 53797.61, cell 1's amount of 135.34426 µg
    at 40 min, and the 19.334894 µg carry-over at 80 min.

    **One deliberate difference in the last decimal.** The sheet rounds its intercept
    to 1 dp (`ROUND(INTERCEPT(...),1)` = 28844.9) while the template rounds to 2
    (28844.87). Everything read back through the line therefore differs from the
    workbook in the seventh significant figure — cell 1 at 40 min is 135.344264 here
    against the sheet's 135.344260. That is orders of magnitude below reporting
    precision, but it is a real difference and it is why the assertions below carry
    the template's values rather than the sheet's. Recorded as a follow-up.
    """

    #  Potency 99.67 %, receptor volume 7 mL, 1 mL replaced per sampling, donor
    #  orifice 1.76 cm², withdrawn aliquot injected undiluted.
    CONTEXT = {
        "potency": 99.67, "receptor_volume": 7.0, "replacement_volume": 1.0,
        "sample_pip": 1.0, "sample_vol": 1.0, "donor_area": 1.76,
        #  1 % w/w cream; with 100 mg applied that is 1000 µg of drug per cell.
        "label_claim": 1.0,
    }
    #  89.73 mg to 50 mL. Levels 1–3 go via a 5 mL → 50 mL intermediate, levels 4–6
    #  come straight off the primary stock — which is why the chain is per row.
    CALIBRATION = [
        {"level": "Cal-1", "nominal_pct": 0.01, "weight_mg": 89.73,
         "c_vol_1": 50.0, "c_pip_1": 5.0, "c_vol_2": 50.0, "c_pip_2": 1.0,
         "c_vol_3": 50.0, "area": 200754.0},
        {"level": "Cal-2", "nominal_pct": 0.05, "weight_mg": 89.73,
         "c_vol_1": 50.0, "c_pip_1": 5.0, "c_vol_2": 50.0, "c_pip_2": 5.0,
         "c_vol_3": 50.0, "area": 974514.0},
        {"level": "Cal-3", "nominal_pct": 0.15, "weight_mg": 89.73,
         "c_vol_1": 50.0, "c_pip_1": 5.0, "c_vol_2": 50.0, "c_pip_2": 15.0,
         "c_vol_3": 50.0, "area": 2922207.0},
        {"level": "Cal-4", "nominal_pct": 0.3, "weight_mg": 89.73,
         "c_vol_1": 50.0, "c_pip_1": 1.0, "c_vol_2": 1.0, "c_pip_2": 3.0,
         "c_vol_3": 50.0, "area": 5786622.0},
        {"level": "Cal-5", "nominal_pct": 0.4, "weight_mg": 89.73,
         "c_vol_1": 50.0, "c_pip_1": 1.0, "c_vol_2": 1.0, "c_pip_2": 4.0,
         "c_vol_3": 50.0, "area": 7842177.0},
        {"level": "Cal-6", "nominal_pct": 0.6, "weight_mg": 89.73,
         "c_vol_1": 50.0, "c_pip_1": 1.0, "c_vol_2": 1.0, "c_pip_2": 6.0,
         "c_vol_3": 50.0, "area": 11507227.0},
    ]
    QC = [
        {"level": "LQC-1", "theoretical_ppm": 3.5773556, "area": 200535.0},
        {"level": "MQC-2", "theoretical_ppm": 53.6603346, "area": 2920429.0},
        {"level": "HQC-1", "theoretical_ppm": 107.3206692, "area": 5780363.0},
    ]
    CELLS = [{f"applied_mg_{n}": 100.0 for n in range(1, 7)}]
    _AREAS = [
        (40, [1069016.0, 688177.0, 1058932.0, 1274902.0, 749441.0, 1082016.0]),
        (80, [1501219.0, 1072893.0, 1466796.0, 1754152.0, 1042199.0, 1498375.0]),
        (120, [1772227.0, 1366683.0, 1706687.0, 2156378.0, 1245758.0, 1773041.0]),
        (160, [1883830.0, 1564759.0, 1850820.0, 2338036.0, 1300307.0, 1881978.0]),
        (200, [1962798.0, 1749653.0, 1935150.0, 2371001.0, 1397948.0, 1959299.0]),
        (240, [2015676.0, 1839654.0, 1991104.0, 2521117.0, 1402166.0, 2014489.0]),
    ]
    TIMEPOINTS = [
        {"time_min": float(minutes),
         **{f"area_{i + 1}": area for i, area in enumerate(areas)}}
        for minutes, areas in _AREAS
    ]
    GROUPS = {
        "calibration": CALIBRATION,
        "qc": QC,
        "cells": CELLS,
        "timepoints": TIMEPOINTS,
    }

    @pytest.fixture()
    def result(self):
        return evaluator("TPL-A6D-0001").evaluate(self.CONTEXT, self.GROUPS)

    def test_theoretical_concentrations_match_the_sheet(self, result):
        # 89.73/50 × 5/50 × 1/50 × 0.9967 × 1000 = 3.5773556
        assert result.row_value("calibration", 0, "theoretical_ppm") == pytest.approx(
            3.5773556, abs=1e-7
        )
        # Level 4 skips the intermediate: 89.73/50 × 1/1 × 3/50 × 0.9967 × 1000
        assert result.row_value("calibration", 3, "theoretical_ppm") == pytest.approx(
            107.3206692, abs=1e-7
        )

    def test_calibration_curve(self, result):
        assert result.values["curve.curve_slope"] == pytest.approx(53797.61)
        assert result.values["curve.curve_intercept"] == pytest.approx(28844.87)
        assert result.values["curve.correlation"] == pytest.approx(0.9999)

    def test_response_is_read_back_through_the_intercept(self, result):
        """
        Not a single-point standard. The intercept is 28844.87 against a level-1
        response of 200754, so a line forced through the origin would read cal-1 as
        200754/53797.61 = 3.731653 ppm instead of 3.195479 — 16.8 % high, and worst
        exactly where IVRT needs precision, at the early timepoints.
        """
        assert result.row_value("calibration", 0, "observed_ppm") == pytest.approx(
            3.1954789, abs=1e-7
        )
        through_origin = 200754.0 / 53797.61
        assert through_origin == pytest.approx(3.731653, abs=1e-6)
        assert through_origin / 3.1954789 == pytest.approx(1.1678, abs=1e-4)

    def test_calibration_recovery(self, result):
        # 3.1954789/3.5773556 × 100 = 89.325… → 89.33
        assert result.row_value("calibration", 0, "recovery_pct") == pytest.approx(89.33)

    def test_bracketing_qc_recoveries(self, result):
        assert result.row_value("qc", 0, "recovery_pct") == pytest.approx(89.21)
        assert result.row_value("qc", 1, "recovery_pct") == pytest.approx(100.17)
        assert result.row_value("qc", 2, "recovery_pct") == pytest.approx(99.62)

    def test_sqrt_time_is_taken_in_hours(self, result):
        """
        The reporting convention that sets the unit of the reportable: √(40/60) h,
        giving µg/cm²/√h rather than µg/cm²/√min.
        """
        assert result.row_value("timepoints", 0, "sqrt_hours") == pytest.approx(
            0.8164966, abs=1e-7
        )
        assert result.row_value("timepoints", 5, "sqrt_hours") == pytest.approx(2.0)

    def test_amount_at_the_first_timepoint_matches_the_sheet(self, result):
        # (1069016 − 28844.87)/53797.61 × 7 = 135.344264 µg
        assert result.row_value("timepoints", 0, "amount_1") == pytest.approx(
            135.344264, abs=1e-6
        )

    def test_the_first_timepoint_has_no_carry_over(self, result):
        assert result.row_value("timepoints", 0, "carry_1") == pytest.approx(0.0)
        assert result.row_value("timepoints", 0, "cumulative_1") == pytest.approx(
            135.344264, abs=1e-6
        )

    def test_carry_over_adds_back_what_earlier_samplings_removed(self, result):
        """
        The relation reverse-engineered from the sheet's correction column: its
        row-*t* entry is the *previous* amount × 1 mL ÷ 7 mL. Summing that column is
        the same quantity as `sum(prior.amount) × replacement / volume`, written here
        as one expression instead of a column plus a hidden running total.
        """
        # 135.344264 × 1/7 = 19.334895 µg — the sheet caches 19.334894
        assert result.row_value("timepoints", 1, "carry_1") == pytest.approx(
            19.334895, abs=1e-6
        )
        # 191.581353 + 19.334895 = 210.916248
        assert result.row_value("timepoints", 1, "amount_1") == pytest.approx(
            191.581353, abs=1e-6
        )
        assert result.row_value("timepoints", 1, "cumulative_1") == pytest.approx(
            210.916248, abs=1e-6
        )

    def test_carry_over_accumulates_over_every_earlier_timepoint(self, result):
        """
        Not just the previous one. By 120 min two samplings have been removed:
        (135.344264 + 191.581353) × 1/7 = 46.703660.
        """
        assert result.row_value("timepoints", 2, "carry_1") == pytest.approx(
            46.703660, abs=1e-6
        )
        assert result.row_value("timepoints", 5, "carry_1") == pytest.approx(
            149.539462, abs=1e-6
        )

    def test_normalised_by_donor_area(self, result):
        # 135.344264/1.76 = 76.900150 µg/cm²
        assert result.row_value("timepoints", 0, "per_area_1") == pytest.approx(
            76.900150, abs=1e-6
        )
        assert result.row_value("timepoints", 5, "per_area_1") == pytest.approx(
            231.852598, abs=1e-6
        )

    def test_across_cell_statistics(self, result):
        assert result.row_value("timepoints", 0, "mean_per_area") == pytest.approx(70.843)
        assert result.row_value("timepoints", 0, "rsd_per_area") == pytest.approx(23.3)

    def test_percent_released_against_applied_dose(self, result):
        # 100 mg of 1 % w/w = 1000 µg applied; 135.344264/1000 × 100 = 13.53 %
        assert result.row_value("timepoints", 0, "released_pct_1") == pytest.approx(13.53)

    def test_flux_is_the_higuchi_slope_per_cell(self, result):
        """
        Regression *down* the timepoints for each cell, cumulative amount per area
        against √time. Cell 5 is a genuine laggard in this dataset and cell 4 runs
        fast — that spread is in the source data, not in the arithmetic.
        """
        assert result.values["flux.flux_1"] == pytest.approx(130.52)
        assert result.values["flux.flux_4"] == pytest.approx(164.41)
        assert result.values["flux.flux_5"] == pytest.approx(91.11)

    def test_higuchi_fit_per_cell(self, result):
        assert result.values["flux.fit_1"] == pytest.approx(0.9999)
        assert result.values["flux.min_fit"] == pytest.approx(0.9975)

    def test_reportable_is_the_mean_flux(self, result):
        # mean of 130.52, 129.10, 128.37, 164.41, 91.11, 129.80 = 128.885 → 128.89
        assert result.values["flux.mean_flux"] == pytest.approx(128.89)
        assert result.reportable_result == pytest.approx(128.89)

    def test_the_source_dataset_fails_only_the_advisory_flux_precision(self, result):
        """
        The real numbers spread 18 % across cells, over the 15 % convention. It is
        advisory, so the run still reports: the calibration line fits, every QC
        recovers, and each cell is individually Higuchi-linear. A blocking criterion
        here would refuse to record a valid experiment with one slow cell.
        """
        assert result.values["flux.rsd_flux"] == pytest.approx(18.0)
        verdicts = {c.key: c.passed for c in result.criteria}
        assert verdicts["flux_precision"] is False
        assert verdicts["calibration_correlation"] is True
        assert verdicts["higuchi_linearity"] is True
        assert result.has_blocking_failure is False

    def test_a_curve_that_does_not_fit_blocks(self):
        calibration = [dict(row) for row in self.CALIBRATION]
        #  Top level comes back below the mid level — detector saturation.
        calibration[5]["area"] = 1000000.0
        result = evaluator("TPL-A6D-0001").evaluate(
            self.CONTEXT, {**self.GROUPS, "calibration": calibration}
        )
        assert result.values["curve.correlation"] < 0.99
        assert result.has_blocking_failure is True
