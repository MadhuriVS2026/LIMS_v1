"""
Tests for the "Standard Details to tabular" rollout harness (part 1).

Covers the shared transform (`as_standard_table`, `convert_definition`), the static
reference audit, the input synthesiser, and the before/after equivalence check that
backs the hard constraint: converting a `standard` section to a table must not
change any calculated value, acceptance criterion or the reportable result.
"""
import copy
from collections import Counter

import pytest

from scripts.standard_tabular_rollout import (
    ROSTER,
    audit_references,
    check_equivalence,
    convert_definition,
    synthesize_inputs,
)
from scripts.template_definitions._common import (
    STANDARD_ROW_LABEL,
    STANDARD_ROWS,
    as_standard_table,
)
from src.domain.services.calculation import evaluator as evaluator_module
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition


def _legacy_definition(**overrides) -> dict:
    """A small pre-conversion sheet: singleton `standard`, a bare alias, a result."""
    definition = {
        "context": [],
        "groups": [
            {
                "key": "standard",
                "kind": "singleton",
                "label": "Standard Details",
                "renderAsTable": True,
                "fields": [
                    {"key": "weight_mg", "kind": "input", "required": True},
                    {"key": "vol", "kind": "input"},
                    {"key": "conc", "kind": "calculated", "expression": "weight_mg / vol * 1000"},
                ],
            },
            {
                "key": "corel_weights",
                "kind": "singleton",
                "fields": [
                    {"key": "std1_weight", "kind": "calculated", "expression": "standard.weight_mg"},
                ],
            },
            {
                "key": "sample",
                "kind": "singleton",
                "fields": [
                    {"key": "area", "kind": "input"},
                    {"key": "assay", "kind": "calculated", "expression": "area / standard.conc * 100"},
                ],
            },
        ],
        "criteria": [
            {
                "key": "assay_limit",
                "label": "Assay",
                "target": "sample.assay",
                "operator": "between",
                "limit": [0, 1000000],
                "severity": "blocking",
                "limitText": "any",
            }
        ],
        "resultRef": "sample.assay",
    }
    definition.update(overrides)
    return definition


def _sample_field(expression: str) -> dict:
    return {"key": "probe", "kind": "calculated", "expression": expression}


def _with_probe(expression: str) -> dict:
    definition = _legacy_definition()
    definition["groups"][2]["fields"].append(_sample_field(expression))
    return definition


class TestAsStandardTable:
    def test_singleton_becomes_a_table_with_the_standard_row_spec(self):
        group = _legacy_definition()["groups"][0]
        out = as_standard_table(group)
        assert out["kind"] == "table"
        assert out["rows"] == STANDARD_ROWS == {"min": 1, "max": 10, "default": 1}
        assert out["rowLabel"] == STANDARD_ROW_LABEL == {"format": "STD - {n}"}
        assert out["fields"] == group["fields"]
        assert out["label"] == "Standard Details"

    def test_render_as_table_is_dropped(self):
        assert "renderAsTable" not in as_standard_table(_legacy_definition()["groups"][0])

    def test_does_not_mutate_its_input(self):
        group = _legacy_definition()["groups"][0]
        before = copy.deepcopy(group)
        as_standard_table(group)
        assert group == before

    def test_is_idempotent(self):
        once = as_standard_table(_legacy_definition()["groups"][0])
        assert as_standard_table(once) == once

    def test_an_existing_table_is_returned_unchanged(self):
        table = {
            "key": "standard",
            "kind": "table",
            "rows": {"min": 2, "max": 4, "default": 3},
            "fields": [{"key": "a", "kind": "input"}],
        }
        assert as_standard_table(table) == table

    def test_the_row_spec_dicts_are_not_shared_between_groups(self):
        a = as_standard_table(_legacy_definition()["groups"][0])
        b = as_standard_table(_legacy_definition()["groups"][0])
        a["rows"]["max"] = 99
        a["rowLabel"]["format"] = "x"
        assert b["rows"] == STANDARD_ROWS
        assert b["rowLabel"] == STANDARD_ROW_LABEL
        assert STANDARD_ROWS["max"] == 10


class TestConvertDefinition:
    def test_converts_only_the_named_group_and_passes_the_schema(self):
        old = _legacy_definition()
        new = convert_definition(old, ("standard",))
        TemplateDefinition.parse(new)
        assert [g["kind"] for g in new["groups"]] == ["table", "singleton", "singleton"]
        assert new["groups"][1:] == old["groups"][1:]
        assert new["criteria"] == old["criteria"]
        assert new["resultRef"] == old["resultRef"]

    def test_does_not_mutate_the_input(self):
        old = _legacy_definition()
        before = copy.deepcopy(old)
        convert_definition(old, ("standard",))
        assert old == before

    def test_is_idempotent(self):
        once = convert_definition(_legacy_definition(), ("standard",))
        assert convert_definition(once, ("standard",)) == once

    def test_converted_definition_evaluates_with_no_input(self):
        new = convert_definition(_legacy_definition(), ("standard",))
        result = WorksheetEvaluator(TemplateDefinition.parse(new)).evaluate({}, {})
        assert len(result.rows["standard"]) == 1

    def test_a_missing_group_is_an_error(self):
        with pytest.raises(ValueError, match="standard_2"):
            convert_definition(_legacy_definition(), ("standard", "standard_2"))

    def test_a_group_that_is_neither_singleton_nor_table_is_an_error(self):
        old = _legacy_definition()
        old["groups"][0]["kind"] = "sequence"
        with pytest.raises(ValueError, match="sequence"):
            convert_definition(old, ("standard",))


class TestAuditReferences:
    def test_arithmetic_rounding_and_indexing_are_accepted(self):
        for expression in (
            "area / standard.conc * 100",
            "round(standard.conc, 2)",
            "abs(standard.conc)",
            "standard.conc[0] + 1",
            "-standard.conc",
            "standard.conc > 1",
        ):
            assert audit_references(_with_probe(expression), ("standard",)) == [], expression

    def test_the_corel_weights_alias_is_the_one_allowed_bare_reference(self):
        assert audit_references(_legacy_definition(), ("standard",)) == []

    def test_a_bare_reference_anywhere_else_is_flagged(self):
        definition = _with_probe("standard.conc")
        violations = audit_references(definition, ("standard",))
        assert len(violations) == 1
        assert "sample.fields.probe.expression" in violations[0]
        assert "bare" in violations[0]

    def test_the_alias_allow_list_is_exact(self):
        definition = _legacy_definition()
        definition["groups"][1]["fields"][0]["expression"] = "standard.conc"
        assert len(audit_references(definition, ("standard",))) == 1

    def test_if_condition_and_branches_are_flagged(self):
        for expression in ("if(standard.conc, 1, 0)", "if(area > 0, standard.conc, 0)"):
            assert audit_references(_with_probe(expression), ("standard",)), expression

    def test_aggregates_are_flagged(self):
        for expression in ("mean(standard.conc)", "count(standard.conc)", "max(standard.conc, 1)", "sum(standard.conc)"):
            assert audit_references(_with_probe(expression), ("standard",)), expression

    def test_logical_operators_are_flagged(self):
        for expression in ("standard.conc and area", "not standard.conc"):
            assert audit_references(_with_probe(expression), ("standard",)), expression

    def test_a_whole_group_reference_is_flagged(self):
        violations = audit_references(_with_probe("count(standard)"), ("standard",))
        assert any("whole-group" in v for v in violations)

    def test_a_criterion_target_is_flagged(self):
        definition = _legacy_definition()
        definition["criteria"][0]["target"] = "standard.conc"
        violations = audit_references(definition, ("standard",))
        assert any("criterion-target" in v for v in violations)

    def test_a_result_ref_into_a_converted_group_is_flagged(self):
        definition = _legacy_definition(resultRef="standard.conc")
        violations = audit_references(definition, ("standard",))
        assert any(v.startswith("resultRef") for v in violations)

    def test_a_string_that_mentions_a_converted_group_but_does_not_parse_is_flagged(self):
        definition = _legacy_definition()
        definition["groups"][2]["fields"][0]["placeholder"] = "use the standard value ("
        violations = audit_references(definition, ("standard",))
        assert any("unparseable" in v for v in violations)

    def test_labels_and_keys_are_not_treated_as_expressions(self):
        definition = _legacy_definition()
        definition["groups"][2]["label"] = "Sample vs standard (n=1"
        definition["groups"][2]["fields"][0]["help"] = "standard ("
        assert audit_references(definition, ("standard",)) == []

    def test_only_the_named_groups_are_audited(self):
        assert audit_references(_with_probe("mean(standard.conc)"), ("standard_2",)) == []

    def test_standard_2_is_a_separate_key(self):
        definition = _with_probe("mean(standard_2.conc)")
        assert audit_references(definition, ("standard",)) == []
        assert audit_references(definition, ("standard", "standard_2"))


class TestSynthesizeInputs:
    def test_is_deterministic(self):
        definition = _legacy_definition()
        assert synthesize_inputs(definition) == synthesize_inputs(definition)

    def test_fills_every_input_and_skips_calculated_fields(self):
        _, groups = synthesize_inputs(_legacy_definition())
        assert set(groups["standard"][0]) == {"weight_mg", "vol"}
        assert all(v is not None for v in groups["standard"][0].values())

    def test_padding_keeps_row_one_and_adds_two_distinct_scaled_rows(self):
        definition = _legacy_definition()
        _, plain = synthesize_inputs(definition)
        _, padded = synthesize_inputs(definition, pad_keys=("standard",))
        assert len(plain["standard"]) == 1
        assert len(padded["standard"]) == 3
        assert padded["standard"][0] == plain["standard"][0]
        assert len({tuple(r.values()) for r in padded["standard"]}) == 3
        assert padded["sample"] == plain["sample"]


class TestCheckEquivalence:
    KEYS = ("standard",)

    def _report(self, old, worksheets=()):
        return check_equivalence(old, convert_definition(old, self.KEYS), self.KEYS, worksheets)

    def test_a_clean_conversion_has_no_differences_and_real_coverage(self):
        report = self._report(_legacy_definition())
        assert report.ok, report.diffs
        assert report.coverage_ok
        assert report.reportable not in (None,)
        assert report.variants == ["empty", "synth", "pad3"]

    def test_stored_worksheets_are_replayed(self):
        sheet = ({}, {"standard": [{"weight_mg": 25.0, "vol": 50.0}], "sample": [{"area": 3.5}]})
        report = self._report(_legacy_definition(), worksheets=[sheet, sheet])
        assert report.variants == ["empty", "synth", "ws", "ws", "pad3"]
        assert report.ok, report.diffs

    def test_the_bare_alias_is_clean_only_because_of_the_sink_collapse(self, monkeypatch):
        old = _legacy_definition()
        assert self._report(old).ok

        monkeypatch.setattr(evaluator_module, "collapse_series", lambda value: value)
        report = self._report(old)
        assert not report.ok
        cells = {d[1] for d in report.diffs}
        assert "r:corel_weights[0].std1_weight" in cells

    def test_a_reference_that_reads_every_row_is_reported(self):
        #  mean() over the converted group sees all three padded rows, so the
        #  padded run no longer matches the one-row baseline. This is the
        #  condition the static audit also rejects.
        old = _with_probe("mean(standard.conc)")
        report = self._report(old)
        assert any(d[0] == "pad3" and d[1] == "r:sample[0].probe" for d in report.diffs)
        assert audit_references(old, self.KEYS)

    def test_a_changed_formula_is_reported(self):
        old = _legacy_definition()
        new = convert_definition(old, self.KEYS)
        new["groups"][2]["fields"][1]["expression"] = "area / standard.conc * 101"
        report = check_equivalence(old, new, self.KEYS)
        assert not report.ok
        assert any(d[1] == "r:sample[0].assay" for d in report.diffs)
        assert any(d[1] == "reportable" for d in report.diffs)

    def test_a_changed_criterion_is_reported(self):
        old = _legacy_definition()
        new = convert_definition(old, self.KEYS)
        new["criteria"][0]["limit"] = [0, 1]
        report = check_equivalence(old, new, self.KEYS)
        assert any(d[1] == "c:assay_limit" for d in report.diffs)

    def test_extra_rows_compute_what_the_old_sheet_computes_for_that_row(self):
        report = self._report(_legacy_definition())
        assert not [d for d in report.diffs if d[0] == "pad3"]

    def test_an_evaluation_error_in_only_one_definition_is_a_difference(self):
        old = _legacy_definition()
        new = convert_definition(old, self.KEYS)
        #  conc -> sample.assay -> conc is a cycle, raised when the sheet is evaluated.
        new["groups"][0]["fields"][2]["expression"] = "sample.assay"
        report = check_equivalence(old, new, self.KEYS)
        assert not report.ok
        assert any(d[1] == "!error" and d[2] is None and "Circular" in d[3] for d in report.diffs)

    def test_the_same_evaluation_error_in_both_definitions_is_not_a_difference(self):
        old = _legacy_definition()
        old["groups"][0]["fields"][2]["expression"] = "sample.assay"
        report = self._report(old)
        assert report.ok, report.diffs

    def test_standard_2_is_converted_and_checked_alongside_standard(self):
        old = _legacy_definition()
        second = copy.deepcopy(old["groups"][0])
        second["key"] = "standard_2"
        second.pop("renderAsTable")
        old["groups"].insert(1, second)
        old["groups"][3]["fields"].append(
            {"key": "second_assay", "kind": "calculated", "expression": "area / standard_2.conc * 100"}
        )
        keys = ("standard", "standard_2")
        new = convert_definition(old, keys)
        assert [g["kind"] for g in new["groups"][:2]] == ["table", "table"]
        report = check_equivalence(old, new, keys)
        assert report.ok, report.diffs
        assert audit_references(old, keys) == []


class TestRoster:
    def test_has_25_rows_and_28_converted_groups(self):
        assert len(ROSTER) == 25
        assert len({e.code for e in ROSTER}) == 25
        assert len({e.template_id for e in ROSTER}) == 25
        assert sum(len(e.keys) for e in ROSTER) == 28
        assert Counter(k for e in ROSTER for k in e.keys) == {"standard": 25, "standard_2": 3}

    def test_standard_2_is_converted_in_exactly_the_three_named_templates(self):
        assert {e.code for e in ROSTER if "standard_2" in e.keys} == {
            "TPL-A4-0001",
            "TPL-H1-0001",
            "TPL-H1-0002",
        }

    def test_module_relationship_split_is_9_equal_9_drifted_7_none(self):
        assert Counter(e.module for e in ROSTER) == {"equal": 9, "drifted": 9, "none": 7}
        assert Counter(e.source for e in ROSTER)["db"] == 7
        assert {e.code for e in ROSTER if e.source == "db"} == {e.code for e in ROSTER if e.module == "none"}

    def test_only_a8_0003_is_a_draft(self):
        assert {e.code for e in ROSTER if e.status == "Draft"} == {"TPL-A8-0003"}
        assert all(e.status in ("Active", "Draft") for e in ROSTER)

# ── Module layer: the declarative modules in scripts/template_definitions ──

from scripts.standard_tabular_rollout import STANDARD_KEYS  # noqa: E402
from scripts.template_definitions import SEED_TEMPLATES  # noqa: E402
from scripts.template_definitions._common import standard_group  # noqa: E402

#  Sheets whose `standard` was already a table before the rollout, with their own row spec.
_ALREADY_TABULAR = {"TPL-A2-0004", "TPL-A2-0005", "TPL-A11-0001", "TPL-A11-0002"}


def _standard_groups(defn: dict) -> list[dict]:
    return [g for g in defn["groups"] if g["key"] in STANDARD_KEYS]


def _converted_keys(defn: dict) -> tuple[str, ...]:
    """Keys of the groups carrying the rollout's row spec (the converted ones)."""
    return tuple(
        g["key"]
        for g in _standard_groups(defn)
        if g["kind"] == "table" and g.get("rows") == STANDARD_ROWS
    )


def _revert(defn: dict, keys: tuple[str, ...]) -> dict:
    """Test-side inverse of the conversion: the pre-rollout singleton shape."""
    legacy = copy.deepcopy(defn)
    for group in legacy["groups"]:
        if group["key"] in keys:
            group["kind"] = "singleton"
            group.pop("rows", None)
            group.pop("rowLabel", None)
    return legacy


_CONVERTED = [t for t in SEED_TEMPLATES if _converted_keys(t.definition)]
_IDS = [t.code for t in _CONVERTED]


class TestModuleRoster:
    def test_no_standard_or_standard_2_group_is_a_singleton(self):
        offenders = [
            (t.code, g["key"])
            for t in SEED_TEMPLATES
            for g in _standard_groups(t.definition)
            if g["kind"] == "singleton"
        ]
        assert offenders == []

    def test_every_converted_group_has_the_standard_row_spec_and_label(self):
        for t in SEED_TEMPLATES:
            for g in _standard_groups(t.definition):
                if t.code in _ALREADY_TABULAR:
                    assert g["kind"] == "table", (t.code, g["key"])
                    continue
                if g["kind"] != "table" or "rows" not in g:
                    continue
                if g["rows"] == STANDARD_ROWS:
                    assert g["rowLabel"] == STANDARD_ROW_LABEL, (t.code, g["key"])
                    assert "renderAsTable" not in g, (t.code, g["key"])

    def test_every_non_exempt_standard_group_uses_the_standard_row_spec(self):
        bad = [
            (t.code, g["key"], g.get("rows"))
            for t in SEED_TEMPLATES
            if t.code not in _ALREADY_TABULAR
            for g in _standard_groups(t.definition)
            if g.get("rows") != STANDARD_ROWS or g.get("rowLabel") != STANDARD_ROW_LABEL
        ]
        #  Sheets that were tabular under their own key (A4-0002 `standards`,
        #  A4-0003 `std_preps`) have no `standard` group and so never appear here.
        assert bad == []

    def test_the_converted_templates_include_all_the_rollout_targets(self):
        codes = set(_IDS)
        assert "TPL-A2-0002" in codes
        for entry in ROSTER:
            if entry.module != "none":
                assert entry.code in codes, entry.code

    def test_standard_2_is_a_table_in_a4_0001(self):
        a4 = next(t for t in SEED_TEMPLATES if t.code == "TPL-A4-0001")
        assert _converted_keys(a4.definition) == ("standard", "standard_2")

    def test_a4_0004_no_longer_carries_render_as_table(self):
        a4 = next(t for t in SEED_TEMPLATES if t.code == "TPL-A4-0004")
        group = next(g for g in a4.definition["groups"] if g["key"] == "standard")
        assert group["kind"] == "table"
        assert "renderAsTable" not in group

    def test_the_reference_a2_0002_module_uses_the_shared_constants(self):
        a2 = next(t for t in SEED_TEMPLATES if t.code == "TPL-A2-0002")
        group = next(g for g in a2.definition["groups"] if g["key"] == "standard")
        assert group["kind"] == "table"
        assert group["rows"] == STANDARD_ROWS
        assert group["rowLabel"] == STANDARD_ROW_LABEL

    def test_there_are_19_converted_module_templates(self):
        #  18 module-backed rollout templates plus the A2-0002 reference conversion.
        assert len(_CONVERTED) == 19, _IDS


@pytest.mark.parametrize("template", _CONVERTED, ids=_IDS)
class TestModuleEquivalence:
    def test_converted_groups_match_the_legacy_shape_apart_from_the_row_spec(self, template):
        keys = _converted_keys(template.definition)
        legacy = _revert(template.definition, keys)
        assert convert_definition(legacy, keys) == template.definition

    def test_references_to_the_standard_are_all_row_one_safe(self, template):
        keys = _converted_keys(template.definition)
        assert audit_references(template.definition, keys) == []

    def test_no_calculated_value_criterion_or_reportable_result_changes(self, template):
        keys = _converted_keys(template.definition)
        legacy = _revert(template.definition, keys)
        report = check_equivalence(legacy, template.definition, keys, [])
        assert report.variants == ["empty", "synth", "pad3"]
        assert report.ok, report.diffs[:5]
        assert report.nonblank_calculated > 0


def _first_numeric_input(group: dict) -> str | None:
    for field in group["fields"]:
        if field["kind"] == "input" and field.get("type", "number") == "number":
            return field["key"]
    return None


@pytest.mark.parametrize("template", _CONVERTED, ids=_IDS)
def test_aggregates_over_a_three_row_standard_use_every_row(template):
    import statistics

    keys = _converted_keys(template.definition)
    ctx, groups = synthesize_inputs(template.definition, pad_keys=keys)
    for key in keys:
        group = next(g for g in template.definition["groups"] if g["key"] == key)
        field = _first_numeric_input(group)
        assert field, (template.code, key)
        defn = copy.deepcopy(template.definition)
        defn["groups"].append(
            {
                "key": "zz_probe",
                "kind": "singleton",
                "fields": [
                    {"key": "m", "kind": "calculated", "expression": f"mean({key}.{field})"},
                    {"key": "s", "kind": "calculated", "expression": f"sd({key}.{field})"},
                    {"key": "n", "kind": "calculated", "expression": f"count({key}.{field})"},
                ],
            }
        )
        result = WorksheetEvaluator(TemplateDefinition.parse(defn)).evaluate(ctx, groups)
        values = [float(row[field]) for row in groups[key]]
        assert len(values) == 3
        probe = result.rows["zz_probe"][0]
        assert probe["n"] == 3, (template.code, key)
        assert probe["m"] == pytest.approx(statistics.mean(values)), (template.code, key)
        assert probe["s"] == pytest.approx(statistics.stdev(values)), (template.code, key)


class TestStandardGroupHelper:
    def _evaluate(self, stored_rows: int):
        defn = {"context": [], "groups": [standard_group()]}
        rows = [{"weight_mg": 10.0 + i, "vol_1": 100.0} for i in range(stored_rows)]
        return WorksheetEvaluator(TemplateDefinition.parse(defn)).evaluate({}, {"standard": rows})

    def test_shape(self):
        group = standard_group()
        assert group["kind"] == "table"
        assert group["rows"] == STANDARD_ROWS
        assert group["rowLabel"] == STANDARD_ROW_LABEL
        assert "renderAsTable" not in group

    def test_fields_are_unchanged_by_the_conversion(self):
        with_mw = [f["key"] for f in standard_group()["fields"]]
        assert with_mw == [
            "name", "weight_mg", "vol_1", "pip_1", "vol_2", "pip_2", "vol_3",
            "mw_base", "mw_salt", "potency", "conc_ppm",
        ]
        without = [f["key"] for f in standard_group(with_mw=False)["fields"]]
        assert without == [k for k in with_mw if k not in ("mw_base", "mw_salt")]

    def test_twelve_stored_rows_evaluate_to_ten(self):
        assert len(self._evaluate(12).rows["standard"]) == 10

    def test_no_stored_rows_gives_the_default_single_row(self):
        assert len(self._evaluate(0).rows["standard"]) == 1