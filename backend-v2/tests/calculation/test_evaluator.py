"""
Tests for the worksheet evaluator: template-definition parsing, dependency
ordering, row scoping, criteria assessment, and a full end-to-end run of the
real `Assay by HPLC` sheet expressed as a template definition.
"""
import pytest

from src.domain.services.calculation import (
    EMPTY,
    EvaluationError,
    Operator,
    Severity,
    TemplateDefinition,
    TemplateSchemaError,
    WorksheetEvaluator,
)


def _def(**overrides) -> dict:
    base = {"context": [], "groups": [], "criteria": []}
    base.update(overrides)
    return base


class TestSchemaParsing:
    def test_empty_definition_is_valid(self):
        parsed = TemplateDefinition.parse(None)
        assert parsed.groups == ()

    def test_calculated_field_requires_an_expression(self):
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [{"key": "x", "kind": "calculated"}],
                }
            ]
        )
        with pytest.raises(TemplateSchemaError, match="needs an 'expression'"):
            TemplateDefinition.parse(raw)

    def test_non_calculated_field_may_not_declare_an_expression(self):
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [{"key": "x", "kind": "input", "expression": "1+1"}],
                }
            ]
        )
        with pytest.raises(TemplateSchemaError, match="declares an expression"):
            TemplateDefinition.parse(raw)

    def test_duplicate_group_key_rejected(self):
        raw = _def(
            groups=[
                {"key": "g", "kind": "singleton", "fields": [{"key": "a", "kind": "input"}]},
                {"key": "g", "kind": "singleton", "fields": [{"key": "b", "kind": "input"}]},
            ]
        )
        with pytest.raises(TemplateSchemaError, match="duplicate group key"):
            TemplateDefinition.parse(raw)

    def test_duplicate_field_key_within_group_rejected(self):
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [
                        {"key": "a", "kind": "input"},
                        {"key": "a", "kind": "input"},
                    ],
                }
            ]
        )
        with pytest.raises(TemplateSchemaError, match="duplicate field"):
            TemplateDefinition.parse(raw)

    def test_invalid_identifier_rejected(self):
        raw = _def(
            groups=[
                {"key": "g", "kind": "singleton", "fields": [{"key": "not a name", "kind": "input"}]}
            ]
        )
        with pytest.raises(TemplateSchemaError, match="valid identifier"):
            TemplateDefinition.parse(raw)

    def test_reserved_field_key_rejected(self):
        raw = _def(
            groups=[{"key": "g", "kind": "singleton", "fields": [{"key": "row", "kind": "input"}]}]
        )
        with pytest.raises(TemplateSchemaError, match="reserved"):
            TemplateDefinition.parse(raw)

    def test_unknown_group_kind_rejected(self):
        raw = _def(
            groups=[{"key": "g", "kind": "bogus", "fields": [{"key": "a", "kind": "input"}]}]
        )
        with pytest.raises(TemplateSchemaError, match="not a valid GroupKind"):
            TemplateDefinition.parse(raw)

    def test_row_spec_bounds_validated(self):
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "table",
                    "rows": {"min": 5, "max": 2},
                    "fields": [{"key": "a", "kind": "input"}],
                }
            ]
        )
        with pytest.raises(TemplateSchemaError, match="less than min"):
            TemplateDefinition.parse(raw)

    def test_between_criterion_needs_two_limits(self):
        raw = _def(
            criteria=[{"key": "c", "target": "1", "operator": "between", "limit": [1.0]}]
        )
        with pytest.raises(TemplateSchemaError, match="needs two limits"):
            TemplateDefinition.parse(raw)

    def test_result_ref_must_resolve(self):
        raw = _def(
            groups=[{"key": "g", "kind": "singleton", "fields": [{"key": "a", "kind": "input"}]}],
            resultRef="g.missing",
        )
        with pytest.raises(TemplateSchemaError, match="does not resolve"):
            TemplateDefinition.parse(raw)

    def test_area_field_refs_exposed_for_future_cds_import(self):
        raw = _def(
            groups=[
                {
                    "key": "std",
                    "kind": "table",
                    "fields": [
                        {"key": "area", "kind": "area"},
                        {"key": "weight", "kind": "input"},
                    ],
                }
            ]
        )
        parsed = TemplateDefinition.parse(raw)
        assert parsed.area_field_refs == (("std", "area"),)


class TestDependencyOrdering:
    def test_fields_evaluate_in_dependency_order_regardless_of_declaration_order(self):
        # `c` is declared before its dependencies but must resolve correctly.
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [
                        {"key": "c", "kind": "calculated", "expression": "b * 2"},
                        {"key": "b", "kind": "calculated", "expression": "a + 1"},
                        {"key": "a", "kind": "input"},
                    ],
                }
            ]
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        result = evaluator.evaluate(group_values={"g": [{"a": 4.0}]})
        assert result.values["g.b"] == 5.0
        assert result.values["g.c"] == 10.0

    def test_circular_reference_raises(self):
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [
                        {"key": "a", "kind": "calculated", "expression": "b + 1"},
                        {"key": "b", "kind": "calculated", "expression": "a + 1"},
                    ],
                }
            ]
        )
        with pytest.raises(EvaluationError, match="Circular reference"):
            WorksheetEvaluator(TemplateDefinition.parse(raw)).evaluate()

    def test_cross_group_dependency_resolves(self):
        raw = _def(
            groups=[
                {
                    "key": "sample",
                    "kind": "table",
                    "rows": {"min": 1, "max": 5, "default": 2},
                    "fields": [
                        {"key": "area", "kind": "area"},
                        {
                            "key": "pct",
                            "kind": "calculated",
                            "expression": "area / mean(std.area) * 100",
                        },
                    ],
                },
                {
                    "key": "std",
                    "kind": "table",
                    "rows": {"min": 1, "max": 6, "default": 3},
                    "fields": [{"key": "area", "kind": "area"}],
                },
            ]
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        result = evaluator.evaluate(
            group_values={
                "std": [{"area": 100.0}, {"area": 100.0}, {"area": 100.0}],
                "sample": [{"area": 110.0}, {"area": 90.0}],
            }
        )
        assert result.row_value("sample", 0, "pct") == pytest.approx(110.0)
        assert result.row_value("sample", 1, "pct") == pytest.approx(90.0)

    def test_invalid_expression_surfaces_with_field_location(self):
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [{"key": "bad", "kind": "calculated", "expression": "1 +"}],
                }
            ]
        )
        with pytest.raises(EvaluationError, match="g.bad"):
            WorksheetEvaluator(TemplateDefinition.parse(raw)).evaluate()


class TestRowScoping:
    def test_column_series_available_for_aggregation(self):
        raw = _def(
            groups=[
                {
                    "key": "std",
                    "kind": "table",
                    "rows": {"min": 1, "max": 6, "default": 6},
                    "fields": [{"key": "area", "kind": "area"}],
                },
                {
                    "key": "stats",
                    "kind": "singleton",
                    "fields": [
                        {"key": "mean_area", "kind": "calculated", "expression": "mean(std.area)"},
                        {"key": "rsd_area", "kind": "calculated", "expression": "rsd(std.area)"},
                    ],
                },
            ]
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        result = evaluator.evaluate(
            group_values={"std": [{"area": v} for v in (100.0, 102.0, 98.0, None, None, None)]}
        )
        assert result.values["stats.mean_area"] == pytest.approx(100.0)
        assert result.values["stats.rsd_area"] == pytest.approx(2.0)

    def test_row_fields_are_in_scope_unqualified_and_via_row(self):
        raw = _def(
            groups=[
                {
                    "key": "t",
                    "kind": "table",
                    "rows": {"min": 1, "max": 3, "default": 2},
                    "fields": [
                        {"key": "a", "kind": "input"},
                        {"key": "bare", "kind": "calculated", "expression": "a * 2"},
                        {"key": "viarow", "kind": "calculated", "expression": "row.a * 3"},
                    ],
                }
            ]
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        result = evaluator.evaluate(group_values={"t": [{"a": 5.0}, {"a": 7.0}]})
        assert result.row_value("t", 0, "bare") == 10.0
        assert result.row_value("t", 0, "viarow") == 15.0
        assert result.row_value("t", 1, "bare") == 14.0

    def test_rowno_is_one_based(self):
        raw = _def(
            groups=[
                {
                    "key": "t",
                    "kind": "table",
                    "rows": {"min": 1, "max": 3, "default": 3},
                    "fields": [{"key": "n", "kind": "calculated", "expression": "rowno"}],
                }
            ]
        )
        result = WorksheetEvaluator(TemplateDefinition.parse(raw)).evaluate()
        assert [result.row_value("t", i, "n") for i in range(3)] == [1.0, 2.0, 3.0]

    def test_row_count_clamped_to_declared_bounds(self):
        raw = _def(
            groups=[
                {
                    "key": "t",
                    "kind": "table",
                    "rows": {"min": 1, "max": 2, "default": 1},
                    "fields": [{"key": "a", "kind": "input"}],
                }
            ]
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        result = evaluator.evaluate(group_values={"t": [{"a": 1.0}] * 10})
        assert len(result.rows["t"]) == 2

    def test_context_values_in_scope(self):
        raw = _def(
            context=[{"key": "label_claim", "kind": "context", "source": "product.labelClaim"}],
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [
                        {"key": "pct", "kind": "calculated", "expression": "50 / label_claim * 100"}
                    ],
                }
            ],
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        result = evaluator.evaluate(context_values={"label_claim": 50.0})
        assert result.values["g.pct"] == pytest.approx(100.0)


class TestSequenceGroup:
    """Dissolution-style sequential rows with access to earlier rows."""

    RAW = _def(
        context=[{"key": "media_volume", "kind": "context"}, {"key": "withdrawal", "kind": "context"}],
        groups=[
            {
                "key": "tp",
                "kind": "sequence",
                "rows": {"min": 1, "max": 8, "default": 3},
                "fields": [
                    {"key": "uncorrected", "kind": "input"},
                    {
                        "key": "correction",
                        "kind": "calculated",
                        "expression": "withdrawal / media_volume * uncorrected",
                        "rounding": {"mode": "trunc", "digits": 3},
                    },
                    {
                        "key": "release",
                        "kind": "calculated",
                        "expression": "uncorrected + sum(prior.correction)",
                    },
                ],
            }
        ],
    )

    def test_cumulative_release_accumulates_prior_corrections(self):
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(self.RAW))
        result = evaluator.evaluate(
            context_values={"media_volume": 500.0, "withdrawal": 5.0},
            group_values={"tp": [{"uncorrected": 20.0}, {"uncorrected": 40.0}, {"uncorrected": 60.0}]},
        )
        # corrections: 0.2, 0.4, 0.6
        assert result.row_value("tp", 0, "correction") == pytest.approx(0.2)
        # release: 20, 40+0.2, 60+0.2+0.4
        assert result.row_value("tp", 0, "release") == pytest.approx(20.0)
        assert result.row_value("tp", 1, "release") == pytest.approx(40.2)
        assert result.row_value("tp", 2, "release") == pytest.approx(60.6)

    def test_prev_row_reference(self):
        raw = _def(
            groups=[
                {
                    "key": "tp",
                    "kind": "sequence",
                    "rows": {"min": 1, "max": 4, "default": 3},
                    "fields": [
                        {"key": "v", "kind": "input"},
                        {"key": "delta", "kind": "calculated", "expression": "v - prev.v"},
                    ],
                }
            ]
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        result = evaluator.evaluate(
            group_values={"tp": [{"v": 10.0}, {"v": 25.0}, {"v": 45.0}]}
        )
        # First row has no predecessor → blank, not an error.
        assert result.row_value("tp", 0, "delta") is EMPTY
        assert result.row_value("tp", 1, "delta") == pytest.approx(15.0)
        assert result.row_value("tp", 2, "delta") == pytest.approx(20.0)

    def test_shrinking_media_volume_series(self):
        """Without replacement, V[t] = V[t-1] - withdrawal — generated, not hard-coded."""
        raw = _def(
            context=[
                {"key": "initial", "kind": "context"},
                {"key": "withdrawal", "kind": "context"},
            ],
            groups=[
                {
                    "key": "tp",
                    "kind": "sequence",
                    "rows": {"min": 1, "max": 8, "default": 4},
                    "fields": [
                        {
                            "key": "volume",
                            "kind": "calculated",
                            "expression": "initial - (rowno - 1) * withdrawal",
                        }
                    ],
                }
            ],
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        result = evaluator.evaluate(context_values={"initial": 500.0, "withdrawal": 5.0})
        volumes = [result.row_value("tp", i, "volume") for i in range(4)]
        assert volumes == [500.0, 495.0, 490.0, 485.0]


class TestRounding:
    def test_round_applied_to_field_result(self):
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [
                        {
                            "key": "v",
                            "kind": "calculated",
                            "expression": "10 / 3",
                            "rounding": {"mode": "round", "digits": 2},
                        }
                    ],
                }
            ]
        )
        result = WorksheetEvaluator(TemplateDefinition.parse(raw)).evaluate()
        assert result.values["g.v"] == pytest.approx(3.33)

    def test_trunc_applied_to_field_result(self):
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [
                        {
                            "key": "v",
                            "kind": "calculated",
                            "expression": "1.9999",
                            "rounding": {"mode": "trunc", "digits": 2},
                        }
                    ],
                }
            ]
        )
        result = WorksheetEvaluator(TemplateDefinition.parse(raw)).evaluate()
        assert result.values["g.v"] == pytest.approx(1.99)

    def test_rounded_value_propagates_downstream(self):
        # Rounding is load-bearing: downstream fields must see the rounded value.
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [
                        {
                            "key": "a",
                            "kind": "calculated",
                            "expression": "10 / 3",
                            "rounding": {"mode": "round", "digits": 1},
                        },
                        {"key": "b", "kind": "calculated", "expression": "a * 3"},
                    ],
                }
            ]
        )
        result = WorksheetEvaluator(TemplateDefinition.parse(raw)).evaluate()
        assert result.values["g.a"] == pytest.approx(3.3)
        assert result.values["g.b"] == pytest.approx(9.9)  # not 10.0

    def test_digits_from_input_field(self):
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [
                        {"key": "digits", "kind": "input"},
                        {
                            "key": "v",
                            "kind": "calculated",
                            "expression": "10 / 3",
                            "rounding": {"mode": "round", "digitsFrom": "digits"},
                        },
                    ],
                }
            ]
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        assert evaluator.evaluate(group_values={"g": [{"digits": 3}]}).values["g.v"] == pytest.approx(3.333)
        assert evaluator.evaluate(group_values={"g": [{"digits": 1}]}).values["g.v"] == pytest.approx(3.3)


class TestCriteria:
    def _build(self, target: str, operator: str, limit, severity: str = "blocking"):
        raw = _def(
            groups=[
                {"key": "g", "kind": "singleton", "fields": [{"key": "v", "kind": "input"}]}
            ],
            criteria=[
                {
                    "key": "c",
                    "label": "Test criterion",
                    "target": target,
                    "operator": operator,
                    "limit": limit,
                    "severity": severity,
                    "limitText": "NMT 2.0 %",
                }
            ],
        )
        return WorksheetEvaluator(TemplateDefinition.parse(raw))

    def test_lte_pass_and_fail(self):
        ev = self._build("g.v", "lte", 2.0)
        assert ev.evaluate(group_values={"g": [{"v": 1.5}]}).criteria[0].passed is True
        assert ev.evaluate(group_values={"g": [{"v": 2.5}]}).criteria[0].passed is False

    def test_boundary_is_inclusive(self):
        ev = self._build("g.v", "lte", 2.0)
        assert ev.evaluate(group_values={"g": [{"v": 2.0}]}).criteria[0].passed is True

    def test_gte(self):
        ev = self._build("g.v", "gte", 0.99)
        assert ev.evaluate(group_values={"g": [{"v": 0.999}]}).criteria[0].passed is True
        assert ev.evaluate(group_values={"g": [{"v": 0.98}]}).criteria[0].passed is False

    def test_between(self):
        ev = self._build("g.v", "between", [0.7, 1.3])
        assert ev.evaluate(group_values={"g": [{"v": 1.0}]}).criteria[0].passed is True
        assert ev.evaluate(group_values={"g": [{"v": 1.4}]}).criteria[0].passed is False

    def test_blank_observed_is_not_yet_assessable(self):
        ev = self._build("g.v", "lte", 2.0)
        result = ev.evaluate()
        assert result.criteria[0].passed is None
        assert result.has_blocking_failure is False

    def test_blocking_failure_flagged(self):
        ev = self._build("g.v", "lte", 2.0)
        result = ev.evaluate(group_values={"g": [{"v": 5.0}]})
        assert result.has_blocking_failure is True
        assert result.blocking_failures[0].key == "c"

    def test_advisory_failure_does_not_block(self):
        ev = self._build("g.v", "lte", 2.0, severity="advisory")
        result = ev.evaluate(group_values={"g": [{"v": 5.0}]})
        assert result.criteria[0].passed is False
        assert result.has_blocking_failure is False

    def test_limit_text_preserved_for_display(self):
        ev = self._build("g.v", "lte", 2.0)
        assert ev.evaluate(group_values={"g": [{"v": 1.0}]}).criteria[0].limit_text == "NMT 2.0 %"


class TestReportableResult:
    def test_singleton_result_ref(self):
        raw = _def(
            groups=[
                {
                    "key": "g",
                    "kind": "singleton",
                    "fields": [
                        {"key": "a", "kind": "input"},
                        {"key": "out", "kind": "calculated", "expression": "a * 2"},
                    ],
                }
            ],
            resultRef="g.out",
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        assert evaluator.evaluate(group_values={"g": [{"a": 21.0}]}).reportable_result == 42.0

    def test_multi_row_result_takes_first_non_blank(self):
        raw = _def(
            groups=[
                {
                    "key": "t",
                    "kind": "table",
                    "rows": {"min": 1, "max": 4, "default": 2},
                    "fields": [
                        {"key": "a", "kind": "input"},
                        {"key": "out", "kind": "calculated", "expression": "a * 2"},
                    ],
                }
            ],
            resultRef="t.out",
        )
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(raw))
        result = evaluator.evaluate(group_values={"t": [{"a": None}, {"a": 5.0}]})
        assert result.reportable_result == 10.0

    def test_no_result_ref_yields_blank(self):
        assert WorksheetEvaluator(TemplateDefinition.parse(_def())).evaluate().reportable_result is EMPTY


class TestDeterminismAndIsolation:
    RAW = _def(
        groups=[
            {
                "key": "std",
                "kind": "table",
                "rows": {"min": 1, "max": 6, "default": 3},
                "fields": [{"key": "area", "kind": "area"}],
            },
            {
                "key": "calc",
                "kind": "singleton",
                "fields": [{"key": "m", "kind": "calculated", "expression": "mean(std.area)"}],
            },
        ]
    )

    def test_repeated_evaluation_is_stable(self):
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(self.RAW))
        values = {"std": [{"area": 100.0}, {"area": 101.0}, {"area": 102.0}]}
        results = {evaluator.evaluate(group_values=values).values["calc.m"] for _ in range(20)}
        assert len(results) == 1

    def test_input_dicts_are_not_mutated(self):
        evaluator = WorksheetEvaluator(TemplateDefinition.parse(self.RAW))
        values = {"std": [{"area": 100.0}]}
        snapshot = [dict(r) for r in values["std"]]
        evaluator.evaluate(group_values=values)
        assert values["std"] == snapshot
