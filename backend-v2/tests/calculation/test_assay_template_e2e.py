"""
End-to-end test: the real `Assay by HPLC.xlsx` sheet expressed as a template
definition and driven through the evaluator with that sheet's own input values.

This is the proof that the generic schema + engine can actually replace a
production calculation workbook. The definition here is the reference
implementation for archetype A1 (assay against an external standard) and is what
the seeded template will be built from.

Source: `rd-lab-instance/Test types/Assay by HPLC.xlsx`
Product: Amphotericin B Liposome for injection 50 mg/vial
"""
import pytest

from src.domain.services.calculation import (
    EMPTY,
    TemplateDefinition,
    WorksheetEvaluator,
)

ASSAY_HPLC_DEFINITION = {
    "resultRef": "samples.pct_mean_assay",
    "context": [
        {"key": "generic_name", "kind": "context", "type": "text", "source": "product.name"},
        {"key": "label_claim", "kind": "context", "source": "product.labelClaim", "unit": "mg"},
        {"key": "avg_weight", "kind": "context", "source": "sample.avgWeight", "overridable": True},
        {"key": "method_no", "kind": "context", "type": "text", "source": "test.methodNo"},
        {"key": "instrument_id", "kind": "context", "type": "text"},
        {"key": "analysed_by", "kind": "context", "type": "text", "source": "session.user"},
        {"key": "date_of_analysis", "kind": "context", "type": "date", "source": "session.date"},
    ],
    "groups": [
        # ── Standard preparation (sheet row 14) ──
        {
            "key": "standard",
            "kind": "singleton",
            "label": "Standard Details",
            "fields": [
                {"key": "name", "kind": "input", "type": "text", "label": "Standard Name"},
                {"key": "weight_mg", "kind": "input", "label": "Weight in mg", "required": True},
                {"key": "vol_1", "kind": "input", "label": "Vol", "required": True},
                {"key": "pip_1", "kind": "input", "label": "Pip", "default": 1},
                {"key": "vol_2", "kind": "input", "label": "Vol", "default": 1},
                {"key": "pip_2", "kind": "input", "label": "Pip", "default": 1},
                {"key": "vol_3", "kind": "input", "label": "Vol", "default": 1},
                {"key": "mw_base", "kind": "input", "label": "MW - Base", "default": 1},
                {"key": "mw_salt", "kind": "input", "label": "MW - Salt", "default": 1},
                {"key": "potency", "kind": "input", "label": "Potency", "default": 100},
                {
                    "key": "conc_ppm",
                    "kind": "calculated",
                    "label": "PPM",
                    "unit": "ppm",
                    "expression": (
                        "weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 "
                        "* mw_base / mw_salt * potency / 100 * 1000"
                    ),
                },
            ],
        },
        # ── Standard replicate injections (B18:B23) ──
        {
            "key": "std_areas",
            "kind": "table",
            "label": "STD Area",
            "rows": {"min": 1, "max": 6, "default": 6},
            "fields": [{"key": "area", "kind": "area", "label": "STD Area"}],
        },
        # ── Bracketing standard blocks ──
        {
            "key": "bkt_1",
            "kind": "table",
            "label": "BKT STD (block 1)",
            "rows": {"min": 0, "max": 6, "default": 6},
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
        },
        {
            "key": "bkt_2",
            "kind": "table",
            "label": "BKT STD (block 2)",
            "rows": {"min": 0, "max": 6, "default": 6},
            "fields": [{"key": "area", "kind": "area", "label": "BKT STD Area"}],
        },
        # ── Second standard, for the co-relation check ──
        {
            "key": "std_2",
            "kind": "singleton",
            "label": "STD-2",
            "fields": [
                {"key": "weight_mg", "kind": "input", "label": "STD-2 Weight"},
                {"key": "area_1", "kind": "area"},
                {"key": "area_2", "kind": "area"},
                {
                    "key": "mean_area",
                    "kind": "calculated",
                    "expression": "mean([area_1, area_2])",
                },
            ],
        },
        # ── Derived standard statistics ──
        {
            "key": "stats",
            "kind": "singleton",
            "label": "Standard Statistics",
            "fields": [
                {"key": "mean_std", "kind": "calculated", "expression": "mean(std_areas.area)"},
                {"key": "sd_std", "kind": "calculated", "expression": "sd(std_areas.area)"},
                {"key": "rsd_std", "kind": "calculated", "expression": "rsd(std_areas.area)"},
                # Bracketing statistics pool cumulatively with the standard.
                {
                    "key": "mean_bkt_1",
                    "kind": "calculated",
                    "expression": "mean(pool(std_areas.area, bkt_1.area))",
                },
                {
                    "key": "rsd_bkt_1",
                    "kind": "calculated",
                    "expression": "rsd(pool(std_areas.area, bkt_1.area))",
                },
                {
                    "key": "mean_bkt_2",
                    "kind": "calculated",
                    "expression": "mean(pool(std_areas.area, bkt_1.area, bkt_2.area))",
                },
                {
                    "key": "rsd_bkt_2",
                    "kind": "calculated",
                    "expression": "rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))",
                },
                {
                    "key": "std_corelation",
                    "kind": "calculated",
                    "expression": (
                        "trunc(stats.mean_std / std_2.mean_area "
                        "* std_2.weight_mg / standard.weight_mg, 3) * 100"
                    ),
                },
            ],
        },
        # ── Sample preparations (sheet rows 31+) ──
        {
            "key": "samples",
            "kind": "table",
            "label": "Sample Details",
            "rows": {"min": 1, "max": 32, "default": 2},
            "fields": [
                {"key": "batch_no", "kind": "input", "type": "text"},
                {"key": "stability_condition", "kind": "input", "type": "text"},
                {"key": "packing_detail", "kind": "input", "type": "text"},
                {"key": "sample_weight", "kind": "input", "label": "Sample Weight", "required": True},
                {"key": "s_vol_1", "kind": "input", "label": "Vol", "required": True},
                {"key": "s_pip_1", "kind": "input", "label": "Pip", "default": 1},
                {"key": "s_vol_2", "kind": "input", "label": "Vol", "default": 1},
                {"key": "s_pip_2", "kind": "input", "label": "Pip", "default": 1},
                {"key": "s_vol_3", "kind": "input", "label": "Vol", "default": 1},
                {"key": "area_1", "kind": "area", "label": "Area-1"},
                {"key": "area_2", "kind": "area", "label": "Area-2"},
                {
                    "key": "avg_area",
                    "kind": "calculated",
                    "label": "Avg. Area",
                    "expression": "mean([area_1, area_2])",
                },
                {
                    "key": "pct_assay",
                    "kind": "calculated",
                    "label": "% Assay",
                    "unit": "%",
                    "expression": (
                        "avg_area / stats.mean_std "
                        "* standard.weight_mg / standard.vol_1 "
                        "* standard.pip_1 / standard.vol_2 "
                        "* standard.pip_2 / standard.vol_3 "
                        "* s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 "
                        "* s_vol_1 / sample_weight "
                        "* avg_weight / label_claim "
                        "* standard.potency * standard.mw_base / standard.mw_salt"
                    ),
                },
                {
                    "key": "pct_mean_assay",
                    "kind": "calculated",
                    "label": "% Mean Assay",
                    "unit": "%",
                    "expression": "mean(samples.pct_assay)",
                },
            ],
        },
    ],
    "criteria": [
        {
            "key": "sst_std_rsd",
            "label": "%RSD of standard replicate injections",
            "target": "stats.rsd_std",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        {
            "key": "sst_bkt_rsd",
            "label": "%RSD of pooled bracketing standards",
            "target": "stats.rsd_bkt_2",
            "operator": "lte",
            "limit": 2.0,
            "severity": "blocking",
            "limitText": "NMT 2.0 %",
        },
        {
            "key": "std_corelation",
            "label": "Standard co-relation",
            "target": "stats.std_corelation",
            "operator": "between",
            "limit": [98.0, 102.0],
            "severity": "advisory",
            "limitText": "98.0 % to 102.0 %",
        },
    ],
}


#  Values transcribed from the source sheet.
CONTEXT = {
    "generic_name": "Amphotericin B Liposome for injection 50 mg/vial",
    "label_claim": 50.0,
    "avg_weight": 1.0,
    "method_no": "QC-DP-MOA-066-06",
    "instrument_id": "AD/HPLC/048",
    "analysed_by": "Sundaram Patel",
}

GROUPS = {
    "standard": [
        {
            "name": "Amphotericin B",
            "weight_mg": 5.054,
            "vol_1": 50.0,
            "pip_1": 5.0,
            "vol_2": 100.0,
            "pip_2": 1.0,
            "vol_3": 1.0,
            "mw_base": 1.0,
            "mw_salt": 1.0,
            "potency": 99.4,
        }
    ],
    "std_areas": [
        {"area": 253287.0},
        {"area": 253024.0},
        {"area": 252584.0},
        {"area": 252811.0},
        {"area": 251367.0},
        {"area": None},
    ],
    "bkt_1": [{"area": 251635.0}, {"area": 251658.0}],
    "bkt_2": [{"area": 260938.0}],
    "std_2": [{"weight_mg": 5.054, "area_1": 253000.0, "area_2": 253100.0}],
    "samples": [
        {
            "batch_no": "PTF_142HIN-392A",
            "stability_condition": "Initial_1",
            "packing_detail": "Glass Vial",
            "sample_weight": 1.0,
            "s_vol_1": 500.0,
            "s_pip_1": 5.0,
            "s_vol_2": 100.0,
            "s_pip_2": 1.0,
            "s_vol_3": 1.0,
            "area_1": 273537.0,
            "area_2": None,
        },
        {
            "batch_no": "PTF_142HIN-392A",
            "stability_condition": "Initial_2",
            "packing_detail": "Glass Vial",
            "sample_weight": 1.0,
            "s_vol_1": 500.0,
            "s_pip_1": 5.0,
            "s_vol_2": 100.0,
            "s_pip_2": 1.0,
            "s_vol_3": 1.0,
            "area_1": 273755.0,
            "area_2": None,
        },
    ],
}


@pytest.fixture(scope="module")
def definition() -> TemplateDefinition:
    return TemplateDefinition.parse(ASSAY_HPLC_DEFINITION)


@pytest.fixture()
def result(definition):
    return WorksheetEvaluator(definition).evaluate(
        context_values=CONTEXT, group_values=GROUPS
    )


class TestDefinitionIsValid:
    def test_parses(self, definition):
        # standard, std_areas, bkt_1, bkt_2, std_2, stats, samples
        assert len(definition.groups) == 7
        assert len(definition.criteria) == 3
        assert definition.result_ref == "samples.pct_mean_assay"

    def test_area_fields_discoverable_for_waters_import(self, definition):
        refs = dict()
        for group_key, field_key in definition.area_field_refs:
            refs.setdefault(group_key, []).append(field_key)
        assert refs["std_areas"] == ["area"]
        assert refs["bkt_1"] == ["area"]
        assert set(refs["samples"]) == {"area_1", "area_2"}
        assert set(refs["std_2"]) == {"area_1", "area_2"}


class TestStandardBlock:
    def test_standard_concentration(self, result):
        assert result.values["standard.conc_ppm"] == pytest.approx(5.023676, abs=1e-6)

    def test_mean_std_area_skips_blank_sixth_injection(self, result):
        assert result.values["stats.mean_std"] == pytest.approx(252614.6)

    def test_sd_and_rsd(self, result):
        assert result.values["stats.sd_std"] == pytest.approx(744.26897, abs=1e-4)
        assert result.values["stats.rsd_std"] == pytest.approx(0.294626, abs=1e-6)


class TestBracketingPooling:
    def test_block_1_pools_with_standard(self, result):
        expected = (253287 + 253024 + 252584 + 252811 + 251367 + 251635 + 251658) / 7
        assert result.values["stats.mean_bkt_1"] == pytest.approx(expected)

    def test_block_2_pools_cumulatively(self, result):
        expected = (
            253287 + 253024 + 252584 + 252811 + 251367 + 251635 + 251658 + 260938
        ) / 8
        assert result.values["stats.mean_bkt_2"] == pytest.approx(expected)

    def test_drifting_bracket_raises_pooled_rsd(self, result):
        assert result.values["stats.rsd_bkt_2"] > result.values["stats.rsd_bkt_1"]


class TestSampleResults:
    def test_first_preparation_percent_assay(self, result):
        assert result.row_value("samples", 0, "pct_assay") == pytest.approx(
            108.795079, abs=1e-6
        )

    def test_second_preparation_percent_assay(self, result):
        # 273755 vs 273537 — slightly higher area, so slightly higher assay.
        second = result.row_value("samples", 1, "pct_assay")
        first = result.row_value("samples", 0, "pct_assay")
        assert second > first
        assert second == pytest.approx(108.881785, abs=1e-5)

    def test_avg_area_uses_only_the_filled_injection(self, result):
        assert result.row_value("samples", 0, "avg_area") == pytest.approx(273537.0)

    def test_mean_assay_averages_the_two_preparations(self, result):
        first = result.row_value("samples", 0, "pct_assay")
        second = result.row_value("samples", 1, "pct_assay")
        assert result.row_value("samples", 0, "pct_mean_assay") == pytest.approx(
            (first + second) / 2
        )

    def test_reportable_result_is_the_mean_assay(self, result):
        assert result.reportable_result == pytest.approx(108.838432, abs=1e-5)

    def test_reportable_result_is_in_a_plausible_range(self, result):
        assert 90.0 < result.reportable_result < 120.0


class TestSystemSuitability:
    def test_standard_rsd_criterion_passes(self, result):
        criterion = next(c for c in result.criteria if c.key == "sst_std_rsd")
        assert criterion.passed is True
        assert criterion.limit_text == "NMT 2.0 %"

    def test_bracketing_rsd_criterion_passes(self, result):
        assert next(c for c in result.criteria if c.key == "sst_bkt_rsd").passed is True

    def test_no_blocking_failures_on_good_data(self, result):
        assert result.has_blocking_failure is False

    def test_drifting_standard_trips_the_blocking_criteria(self, definition):
        """
        A standard series with real drift must fail SST and block reporting.

        Both RSD criteria fail here, and that is correct: the bracketing
        statistics pool the standard replicates in, so drift in the standard
        necessarily shows up in the pooled %RSD too.
        """
        bad = {**GROUPS, "std_areas": [{"area": v} for v in
                                       (253287.0, 240000.0, 262000.0, 251000.0, 238000.0, None)]}
        result = WorksheetEvaluator(definition).evaluate(
            context_values=CONTEXT, group_values=bad
        )
        assert result.values["stats.rsd_std"] > 2.0
        assert result.has_blocking_failure is True
        assert {c.key for c in result.blocking_failures} == {"sst_std_rsd", "sst_bkt_rsd"}

    def test_drift_confined_to_a_bracket_trips_only_the_pooled_criterion(self, definition):
        """
        The converse: a clean standard with a wildly off bracketing injection
        fails only the pooled criterion, proving the two are independent.
        """
        bad = {**GROUPS, "bkt_2": [{"area": 400000.0}]}
        result = WorksheetEvaluator(definition).evaluate(
            context_values=CONTEXT, group_values=bad
        )
        assert result.values["stats.rsd_std"] <= 2.0
        assert {c.key for c in result.blocking_failures} == {"sst_bkt_rsd"}

    def test_advisory_corelation_failure_does_not_block(self, definition):
        # A second standard whose response is well off yields a bad co-relation,
        # but that criterion is advisory so it must not block reporting.
        bad = {**GROUPS, "std_2": [{"weight_mg": 5.054, "area_1": 200000.0, "area_2": 200000.0}]}
        result = WorksheetEvaluator(definition).evaluate(
            context_values=CONTEXT, group_values=bad
        )
        corelation = next(c for c in result.criteria if c.key == "std_corelation")
        assert corelation.passed is False
        assert result.has_blocking_failure is False


class TestPartiallyFilledWorksheet:
    """An analyst mid-entry must see blanks, never errors."""

    def test_empty_worksheet_produces_blanks_not_errors(self, definition):
        result = WorksheetEvaluator(definition).evaluate()
        assert result.values["stats.mean_std"] is EMPTY
        assert result.reportable_result is EMPTY
        assert result.has_blocking_failure is False

    def test_standard_entered_but_no_sample_areas(self, definition):
        partial = {"standard": GROUPS["standard"], "std_areas": GROUPS["std_areas"]}
        result = WorksheetEvaluator(definition).evaluate(
            context_values=CONTEXT, group_values=partial
        )
        assert result.values["stats.mean_std"] == pytest.approx(252614.6)
        assert result.row_value("samples", 0, "pct_assay") is EMPTY
        assert result.reportable_result is EMPTY

    def test_criteria_assessable_before_samples_are_entered(self, definition):
        partial = {"standard": GROUPS["standard"], "std_areas": GROUPS["std_areas"]}
        result = WorksheetEvaluator(definition).evaluate(
            context_values=CONTEXT, group_values=partial
        )
        # SST depends only on the standard, so it can be judged already.
        assert next(c for c in result.criteria if c.key == "sst_std_rsd").passed is True

    def test_missing_context_leaves_result_blank_without_raising(self, definition):
        result = WorksheetEvaluator(definition).evaluate(group_values=GROUPS)
        # label_claim/avg_weight absent → assay cannot be computed.
        assert result.row_value("samples", 0, "pct_assay") is EMPTY


class TestUnitBasisAndOverrides:
    def test_overriding_average_weight_scales_the_result(self, definition):
        doubled = {**CONTEXT, "avg_weight": 2.0}
        result = WorksheetEvaluator(definition).evaluate(
            context_values=doubled, group_values=GROUPS
        )
        assert result.reportable_result == pytest.approx(108.838432 * 2, abs=1e-4)

    def test_mw_ratio_applied(self, definition):
        salt = {
            **GROUPS,
            "standard": [{**GROUPS["standard"][0], "mw_base": 171.24, "mw_salt": 267.35}],
        }
        result = WorksheetEvaluator(definition).evaluate(
            context_values=CONTEXT, group_values=salt
        )
        ratio = 171.24 / 267.35
        # Applied on both the concentration and the assay chain.
        assert result.values["standard.conc_ppm"] == pytest.approx(
            5.023676 * ratio, abs=1e-6
        )
        assert result.reportable_result == pytest.approx(108.838432 * ratio, abs=1e-4)
