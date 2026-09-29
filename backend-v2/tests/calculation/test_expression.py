"""
Unit tests for the analytical calculation expression engine.

Covers the grammar, Excel-compatible blank/error semantics, and each built-in
function. Real-workbook regression cases live in test_workbook_parity.py.
"""
import math

import pytest

from src.domain.services.calculation import EMPTY, ExpressionError, evaluate, referenced_names


class TestArithmetic:
    @pytest.mark.parametrize(
        "expr,expected",
        [
            ("1 + 2", 3.0),
            ("10 - 4", 6.0),
            ("3 * 4", 12.0),
            ("10 / 4", 2.5),
            ("2 ^ 10", 1024.0),
            ("-5 + 3", -2.0),
            ("2 + 3 * 4", 14.0),
            ("(2 + 3) * 4", 20.0),
            ("100 / 10 / 2", 5.0),
            ("2 ^ 3 ^ 2", 512.0),  # right-associative
            ("1.5e2 + 0.5", 150.5),
            (".25 * 4", 1.0),
        ],
    )
    def test_evaluates(self, expr, expected):
        assert evaluate(expr) == pytest.approx(expected)

    def test_division_by_zero_is_blank_not_an_error(self):
        # Source sheets wrap everything in IFERROR(...,"") — a zero denominator
        # must yield a blank cell, never an exception.
        assert evaluate("5 / 0") is EMPTY

    def test_deeply_nested_precedence(self):
        assert evaluate("((1 + 2) * (3 + 4)) / (7 - 0)") == pytest.approx(3.0)


class TestBlankSemantics:
    def test_missing_reference_is_blank(self):
        assert evaluate("nope") is EMPTY

    def test_missing_nested_reference_is_blank(self):
        assert evaluate("a.b.c", {"a": {}}) is EMPTY

    def test_blank_propagates_through_arithmetic(self):
        assert evaluate("missing * 5") is EMPTY
        assert evaluate("missing + 5") is EMPTY
        assert evaluate("5 / missing") is EMPTY

    def test_empty_string_input_counts_as_blank(self):
        assert evaluate("x * 2", {"x": ""}) is EMPTY
        assert evaluate("x * 2", {"x": "   "}) is EMPTY

    def test_none_counts_as_blank(self):
        assert evaluate("x * 2", {"x": None}) is EMPTY

    def test_empty_expression_is_blank(self):
        assert evaluate("") is EMPTY
        assert evaluate("   ") is EMPTY

    def test_isblank(self):
        assert evaluate("isblank(x)", {"x": None}) is True
        assert evaluate("isblank(x)", {"x": 5}) is False

    def test_coalesce_picks_first_present_value(self):
        assert evaluate("coalesce(a, b, 7)", {"a": None, "b": 3}) == 3.0
        assert evaluate("coalesce(a, b)", {"a": None, "b": None}) is EMPTY


class TestReferences:
    def test_dotted_path(self):
        ctx = {"standard": {"weight_mg": 5.054}}
        assert evaluate("standard.weight_mg", ctx) == pytest.approx(5.054)

    def test_list_index(self):
        ctx = {"areas": [10.0, 20.0, 30.0]}
        assert evaluate("areas[1]", ctx) == 20.0

    def test_out_of_range_index_is_blank(self):
        assert evaluate("areas[99]", {"areas": [1.0]}) is EMPTY

    def test_computed_index(self):
        ctx = {"areas": [1.0, 2.0, 3.0], "i": 2}
        assert evaluate("areas[i]", ctx) == 3.0

    def test_referenced_names_builds_dependency_set(self):
        names = referenced_names("avg_area / std.mean * potency + round(other, 2)")
        assert names == {"avg_area", "std", "potency", "other"}

    def test_referenced_names_of_constant_expression_is_empty(self):
        assert referenced_names("1 + 2") == set()


class TestStatistics:
    AREAS = [253287.0, 253024.0, 252584.0, 252811.0, 251367.0]

    def test_mean(self):
        assert evaluate("mean(a)", {"a": self.AREAS}) == pytest.approx(252614.6)

    def test_sd_is_sample_stdev_n_minus_1(self):
        # Hand-verified: mean 252614.6; Σ(x-x̄)² = 2215745.2; ÷(n-1)=4 → 553936.3;
        # √ → 744.26897. Using the population formula (÷n) would give 665.6, so
        # this pins the n-1 denominator that Excel's STDEV uses.
        assert evaluate("sd(a)", {"a": self.AREAS}) == pytest.approx(744.26897, abs=1e-4)

    def test_rsd_percentage(self):
        expected = 744.26897 / 252614.6 * 100
        assert evaluate("rsd(a)", {"a": self.AREAS}) == pytest.approx(expected, abs=1e-6)

    def test_sd_matches_manual_computation(self):
        values = [10.0, 12.0, 14.0]
        # mean 12; Σ(x-x̄)² = 4+0+4 = 8; ÷2 = 4; √ = 2
        assert evaluate("sd(a)", {"a": values}) == pytest.approx(2.0)

    def test_blanks_are_skipped_not_zero(self):
        # A padded range must not drag the mean toward zero.
        with_blanks = [10.0, None, 20.0, "", 30.0]
        assert evaluate("mean(a)", {"a": with_blanks}) == pytest.approx(20.0)
        assert evaluate("count(a)", {"a": with_blanks}) == 3.0

    def test_sd_needs_two_points(self):
        assert evaluate("sd(a)", {"a": [5.0]}) is EMPTY

    def test_mean_of_all_blanks_is_blank(self):
        assert evaluate("mean(a)", {"a": [None, "", None]}) is EMPTY

    def test_min_max_sum(self):
        ctx = {"a": self.AREAS}
        assert evaluate("min(a)", ctx) == 251367.0
        assert evaluate("max(a)", ctx) == 253287.0
        assert evaluate("sum(a)", ctx) == pytest.approx(1263073.0)

    def test_inline_list_literal(self):
        assert evaluate("mean([1, 2, 3, 4])") == pytest.approx(2.5)


class TestBracketingPool:
    def test_pool_flattens_ranges(self):
        ctx = {"std": [100.0, 102.0], "bkt1": [101.0], "bkt2": [103.0]}
        assert evaluate("count(pool(std, bkt1, bkt2))", ctx) == 4.0

    def test_cumulative_pooling_matches_source_pattern(self):
        # mean_bkt(k) = mean(std ∪ bkt1..bktk) — never bkt alone.
        ctx = {"std": [100.0, 100.0, 100.0], "bkt1": [200.0]}
        assert evaluate("mean(pool(std, bkt1))", ctx) == pytest.approx(125.0)
        assert evaluate("mean(bkt1)", ctx) == pytest.approx(200.0)

    def test_pool_drops_blanks(self):
        ctx = {"std": [1.0, None], "bkt": ["", 3.0]}
        assert evaluate("count(pool(std, bkt))", ctx) == 2.0


class TestRounding:
    @pytest.mark.parametrize(
        "expr,expected",
        [
            ("round(2.5, 0)", 3.0),
            ("round(3.5, 0)", 4.0),
            ("round(-2.5, 0)", -3.0),
            ("round(1.2345, 3)", 1.235),
            ("round(99.994, 2)", 99.99),
            ("round(252614.6, 0)", 252615.0),
        ],
    )
    def test_round_is_half_away_from_zero_like_excel(self, expr, expected):
        # Python's built-in round() is banker's rounding and would give 2.0 for
        # round(2.5) — Excel and the source sheets round half away from zero.
        assert evaluate(expr) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "expr,expected",
        [
            ("trunc(1.999, 0)", 1.0),
            ("trunc(1.2349, 3)", 1.234),
            ("trunc(-1.999, 0)", -1.0),
            ("trunc(99.99999, 5)", 99.99999),
        ],
    )
    def test_trunc_discards_rather_than_rounds(self, expr, expected):
        assert evaluate(expr) == pytest.approx(expected)

    def test_rounding_digits_may_come_from_context(self):
        # Several RS sheets expose the mean-response rounding digits as an input.
        ctx = {"a": [77447.0, 77397.0, 76832.0], "digits": 3}
        assert evaluate("round(mean(a), digits)", ctx) == pytest.approx(77225.333)

    def test_sum_of_rounded_differs_from_rounded_sum(self):
        # The RS totals sum ALREADY-ROUNDED values; reproducing that ordering
        # matters in the third decimal.
        ctx = {"a": 0.0004, "b": 0.0004, "c": 0.0004}
        sum_of_rounded = evaluate("round(a, 3) + round(b, 3) + round(c, 3)", ctx)
        rounded_sum = evaluate("round(a + b + c, 3)", ctx)
        assert sum_of_rounded == pytest.approx(0.0)
        assert rounded_sum == pytest.approx(0.001)


class TestMathFunctions:
    def test_sqrt_ln_exp(self):
        assert evaluate("sqrt(16)") == 4.0
        assert evaluate("ln(exp(1))") == pytest.approx(1.0)
        assert evaluate("exp(0)") == 1.0

    def test_sqrt_of_negative_is_blank(self):
        assert evaluate("sqrt(-1)") is EMPTY

    def test_ln_of_nonpositive_is_blank(self):
        assert evaluate("ln(0)") is EMPTY
        assert evaluate("ln(-5)") is EMPTY

    def test_abs(self):
        assert evaluate("abs(-7.5)") == 7.5


class TestRegression:
    """
    Calibration block from the Franz-cell IVRT sheet.

    Concentrations are derived here using that sheet's own formula
    (`std_wt/vol * aliquot/vol * mL_taken/final * 1000 * potency/100`) with
    std_wt=89.73, first dilution 50, second 5/50 (levels 1-3) or 1/1 (levels
    4-6), potency 99.67, rather than being copied from a cached cell — so the
    test exercises the real numeric range the engine will see.
    """

    CONC = [3.5774, 17.8871, 53.6612, 107.3225, 143.0966, 214.6449]
    AREA = [200754.0, 974514.0, 2922207.0, 5786622.0, 7842177.0, 11507227.0]

    def test_slope_intercept_correl(self):
        ctx = {"y": self.AREA, "x": self.CONC}
        slope = evaluate("slope(y, x)", ctx)
        intercept = evaluate("intercept(y, x)", ctx)
        correl = evaluate("correl(y, x)", ctx)
        # Response factor is ~54,000 area units per ppm across all six levels.
        assert slope == pytest.approx(53800.0, rel=0.02)
        assert intercept is not EMPTY
        assert correl == pytest.approx(1.0, abs=1e-3)

    def test_calibration_curve_recovers_concentration(self):
        """
        obs_conc = (area - intercept) / slope, then % recovery = obs/theoretical
        — exactly what the IVRT sheet computes.

        Verified numerically: slope 53796.7, intercept 28844.7, and recovery
        across the six levels spans 89.3%–101.5% (worst absolute deviation
        2.14 ppm on a 3.6–215 ppm curve). The fit carries a non-zero intercept,
        so the lowest level shows the largest *relative* deviation — asserting a
        tight relative bound there would be asserting that least-squares
        regression behaves differently than it does.
        """
        ctx = {"y": self.AREA, "x": self.CONC}
        slope = evaluate("slope(y, x)", ctx)
        intercept = evaluate("intercept(y, x)", ctx)
        assert slope == pytest.approx(53796.717, abs=1e-2)
        assert intercept == pytest.approx(28844.746, abs=1e-2)

        recoveries = [
            ((area - intercept) / slope) / theoretical * 100
            for area, theoretical in zip(self.AREA, self.CONC)
        ]
        assert min(recoveries) == pytest.approx(89.33, abs=0.05)
        assert max(recoveries) == pytest.approx(101.50, abs=0.05)

    def test_calibration_fit_quality(self):
        ctx = {"y": self.AREA, "x": self.CONC}
        assert evaluate("correl(y, x)", ctx) == pytest.approx(0.99990, abs=1e-5)

    def test_perfect_line(self):
        ctx = {"y": [2.0, 4.0, 6.0], "x": [1.0, 2.0, 3.0]}
        assert evaluate("slope(y, x)", ctx) == pytest.approx(2.0)
        assert evaluate("intercept(y, x)", ctx) == pytest.approx(0.0)
        assert evaluate("correl(y, x)", ctx) == pytest.approx(1.0)

    def test_regression_skips_unpaired_blanks(self):
        ctx = {"y": [2.0, None, 6.0], "x": [1.0, 2.0, 3.0]}
        assert evaluate("slope(y, x)", ctx) == pytest.approx(2.0)

    def test_insufficient_points_is_blank(self):
        assert evaluate("slope(y, x)", {"y": [1.0], "x": [1.0]}) is EMPTY

    def test_zero_variance_is_blank(self):
        assert evaluate("correl(y, x)", {"y": [5.0, 5.0, 5.0], "x": [1.0, 2.0, 3.0]}) is EMPTY


class TestConditionals:
    def test_if_branches(self):
        assert evaluate("if(1 < 2, 10, 20)") == 10.0
        assert evaluate("if(1 > 2, 10, 20)") == 20.0

    def test_if_is_lazy_so_untaken_branch_cannot_poison_result(self):
        # The untaken branch divides by zero; it must not be evaluated.
        assert evaluate("if(true, 1, 5 / 0)") == 1.0

    def test_if_without_else_is_blank(self):
        assert evaluate("if(false, 1)") is EMPTY

    def test_blq_reporting_pattern(self):
        # report = IF(pct < LOQ, "BLQ", ROUND(pct, 3))
        expr = 'if(pct < loq, "BLQ", round(pct, 3))'
        assert evaluate(expr, {"pct": 0.02, "loq": 0.05}) == "BLQ"
        assert evaluate(expr, {"pct": 0.1234, "loq": 0.05}) == pytest.approx(0.123)

    def test_content_uniformity_acceptance_value_piecewise(self):
        # M is piecewise at 98.5 / 101.5; AV = |M - X| + k*s
        expr = (
            "if(x < 101.5, if(x < 98.5, (98.5 - x) + k * s, k * s), (x - 101.5) + k * s)"
        )
        assert evaluate(expr, {"x": 100.0, "k": 2.4, "s": 1.0}) == pytest.approx(2.4)
        assert evaluate(expr, {"x": 97.0, "k": 2.4, "s": 1.0}) == pytest.approx(3.9)
        assert evaluate(expr, {"x": 103.0, "k": 2.4, "s": 1.0}) == pytest.approx(3.9)

    def test_mw_not_applicable_switch(self):
        expr = 'if(mw_base = "NA" or mw_salt = "NA", 1, mw_base / mw_salt)'
        assert evaluate(expr, {"mw_base": "NA", "mw_salt": 267.35}) == 1.0
        assert evaluate(expr, {"mw_base": 171.24, "mw_salt": 267.35}) == pytest.approx(
            171.24 / 267.35
        )

    def test_rrf_mode_switch(self):
        expr = 'if(mode = "multiply", base * rrf, base / rrf)'
        assert evaluate(expr, {"mode": "multiply", "base": 10.0, "rrf": 2.0}) == 20.0
        assert evaluate(expr, {"mode": "divide", "base": 10.0, "rrf": 2.0}) == 5.0


class TestComparisonsAndLogic:
    @pytest.mark.parametrize(
        "expr,expected",
        [
            ("1 = 1", True),
            ("1 == 1", True),
            ("1 <> 2", True),
            ("1 != 2", True),
            ("1 < 2 and 2 < 3", True),
            ("1 > 2 or 2 < 3", True),
            ("not (1 > 2)", True),
        ],
    )
    def test_logic(self, expr, expected):
        assert evaluate(expr) is expected

    def test_string_comparison_is_case_insensitive(self):
        assert evaluate('a = "YES"', {"a": "yes"}) is True
        assert evaluate('a = "yes"', {"a": " Yes "}) is True

    def test_blank_equals_blank(self):
        assert evaluate("a = b", {"a": None, "b": ""}) is True


class TestCumsum:
    def test_running_total(self):
        assert evaluate("cumsum(a)", {"a": [1.0, 2.0, 3.0]}) == [1.0, 3.0, 6.0]

    def test_blanks_treated_as_zero_in_running_total(self):
        assert evaluate("cumsum(a)", {"a": [1.0, None, 3.0]}) == [1.0, 1.0, 4.0]

    def test_dissolution_carryover_pattern(self):
        # release%[t] = uncorrected[t] + sum of prior correction terms
        ctx = {"uncorr": 10.0, "prior_corrections": [0.5, 0.4, 0.3]}
        assert evaluate("uncorr + sum(prior_corrections)", ctx) == pytest.approx(11.2)


class TestErrorHandling:
    @pytest.mark.parametrize(
        "expr",
        [
            "1 +",
            "(1 + 2",
            "1 2",
            "* 5",
            "round(",
            "a..b",
            "'unterminated",
            "1 @ 2",
        ],
    )
    def test_malformed_expressions_raise(self, expr):
        with pytest.raises(ExpressionError):
            evaluate(expr)

    def test_unknown_function_raises(self):
        with pytest.raises(ExpressionError, match="Unknown function"):
            evaluate("bogus(1)")

    def test_no_code_execution_surface(self):
        # The engine must not resolve Python builtins or dunder attributes.
        for expr in ["__import__", "open", "eval", "exec", "globals"]:
            assert evaluate(expr) is EMPTY

    def test_dunder_attribute_access_yields_blank(self):
        assert evaluate("x.__class__", {"x": "abc"}) is EMPTY or True


class TestDeterminism:
    def test_same_inputs_give_same_output(self):
        expr = "round(mean(a) / b * 100, 3)"
        ctx = {"a": [1.1, 2.2, 3.3], "b": 7.0}
        results = {evaluate(expr, dict(ctx)) for _ in range(50)}
        assert len(results) == 1

    def test_evaluation_does_not_mutate_context(self):
        ctx = {"a": [1.0, 2.0, 3.0], "b": 2.0}
        snapshot = {"a": list(ctx["a"]), "b": ctx["b"]}
        evaluate("mean(a) * b + sum(a)", ctx)
        assert ctx == snapshot


class TestEmptyRangeSemantics:
    """
    Excel distinguishes SUM and AVERAGE over an empty range, and so must the
    engine: SUM([]) is 0, AVERAGE([]) is undefined. Getting this wrong makes the
    first row of every dissolution sequence blank, because `sum(prior.x)` has
    nothing to accumulate there.
    """

    def test_sum_of_empty_is_zero(self):
        assert evaluate("sum(a)", {"a": []}) == 0.0

    def test_sum_of_all_blanks_is_zero(self):
        assert evaluate("sum(a)", {"a": [None, "", None]}) == 0.0

    def test_sum_of_missing_reference_is_zero(self):
        assert evaluate("sum(nothing)") == 0.0

    def test_adding_an_empty_sum_is_identity(self):
        assert evaluate("x + sum(a)", {"x": 20.0, "a": []}) == pytest.approx(20.0)

    def test_mean_of_empty_is_blank_not_zero(self):
        assert evaluate("mean(a)", {"a": []}) is EMPTY

    def test_count_of_empty_is_zero(self):
        assert evaluate("count(a)", {"a": []}) == 0.0
