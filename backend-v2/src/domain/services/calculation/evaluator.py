"""
Worksheet evaluator: walks a parsed template definition and computes every
calculated field in dependency order.

Scoping model — the part worth understanding before changing anything here:

  * Context fields and singleton-group fields are addressed as `key` and
    `group.field`.
  * A multi-row group exposes each of its fields as a **column series**:
    `group.field` is the list of that field's values down the rows. This is what
    makes `mean(standard.area)` and `rsd(pool(std.area, bkt.area))` work.
  * While evaluating a row-scoped field, that row's own fields are additionally
    in scope unqualified (`weight_mg`) and via `row.weight_mg`. Column series for
    every group stay visible, so a row formula can reference a sheet-level
    aggregate such as `mean(std_areas.area)`.
  * `sequence` groups additionally expose `prev.field` (the immediately
    preceding row) and `prior.field` (all preceding rows, as a list). The
    dissolution carry-over chains are expressed with `sum(prior.correction)`
    rather than the source sheets' hard-coded `C73+D73+E73+...`.

Evaluation order is a topological sort over calculated fields; a circular
reference raises rather than silently producing a blank.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.services.calculation.expression import (
    EMPTY,
    ExpressionError,
    evaluate,
    referenced_paths,
)
from src.domain.services.calculation.template_schema import (
    CriterionDef,
    FieldDef,
    FieldKind,
    GroupDef,
    GroupKind,
    Operator,
    RoundMode,
    Severity,
    TemplateDefinition,
)


class EvaluationError(ValueError):
    """Raised for circular references or otherwise unevaluable templates."""


@dataclass(frozen=True)
class CriterionResult:
    key: str
    label: str
    observed: Any
    operator: Operator
    limit: tuple[float, ...]
    severity: Severity
    limit_text: str
    passed: bool | None  # None when the observed value is blank (not yet assessable)

    @property
    def is_blocking_failure(self) -> bool:
        return self.severity is Severity.BLOCKING and self.passed is False


@dataclass
class WorksheetResult:
    """Computed state of a worksheet."""

    #  Singleton/context scalars: {"group.field": value} and {"context_key": value}
    values: dict[str, Any] = field(default_factory=dict)
    #  Multi-row groups: {group_key: [{field_key: value}, ...]}
    rows: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    criteria: list[CriterionResult] = field(default_factory=list)
    reportable_result: Any = EMPTY

    @property
    def has_blocking_failure(self) -> bool:
        return any(c.is_blocking_failure for c in self.criteria)

    @property
    def blocking_failures(self) -> list[CriterionResult]:
        return [c for c in self.criteria if c.is_blocking_failure]

    def row_value(self, group_key: str, row_index: int, field_key: str) -> Any:
        try:
            return self.rows[group_key][row_index].get(field_key, EMPTY)
        except (KeyError, IndexError):
            return EMPTY


def _apply_rounding(value: Any, field_def: FieldDef, scope: dict[str, Any]) -> Any:
    """Apply a calculated field's declared rounding.

    Rounding position is load-bearing in these sheets — several formulas round
    mid-chain and the totals sum already-rounded values — so this is applied to
    the field's own result and the rounded value is what downstream fields see.
    """
    rounding = field_def.rounding
    if rounding.mode is RoundMode.NONE or value is EMPTY:
        return value
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return value

    digits = rounding.digits
    if rounding.digits_from:
        raw = scope.get(rounding.digits_from, EMPTY)
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            digits = int(raw)

    fn = "round" if rounding.mode is RoundMode.ROUND else "trunc"
    return evaluate(f"{fn}(v, d)", {"v": float(value), "d": digits})


class WorksheetEvaluator:
    """
    Stateless evaluator. Construct with a parsed definition, then call
    `evaluate()` with the worksheet's stored values as many times as needed —
    the same inputs always give the same outputs.
    """

    def __init__(self, definition: TemplateDefinition) -> None:
        self._def = definition

    # ─────────────── public API ───────────────

    def evaluate(
        self,
        context_values: dict[str, Any] | None = None,
        group_values: dict[str, list[dict[str, Any]]] | None = None,
    ) -> WorksheetResult:
        """
        Compute the worksheet.

        `context_values` supplies context-field values by key.
        `group_values` supplies stored input/area values per group as a list of
        row dicts (a singleton group is a one-element list).
        """
        context_values = dict(context_values or {})
        group_values = {k: [dict(r) for r in v] for k, v in (group_values or {}).items()}

        result = WorksheetResult()

        # Seed context.
        for cf in self._def.context:
            result.values[cf.key] = context_values.get(cf.key, cf.default if cf.default is not None else EMPTY)

        # Seed group rows with their stored non-calculated values.
        for group in self._def.groups:
            rows = self._seed_rows(group, group_values.get(group.key))
            result.rows[group.key] = rows

        # Resolve calculated fields in dependency order.
        for group_key, field_key in self._evaluation_order():
            group = self._def.group(group_key)
            if group is None:
                continue
            field_def = group.field(field_key)
            if field_def is None or field_def.kind is not FieldKind.CALCULATED:
                continue
            self._evaluate_field(group, field_def, result)

        # Mirror singleton groups into flat `group.field` scalars for convenience.
        for group in self._def.groups:
            if not group.is_multi_row and result.rows.get(group.key):
                for key, value in result.rows[group.key][0].items():
                    result.values[f"{group.key}.{key}"] = value

        result.criteria = self._evaluate_criteria(result)
        result.reportable_result = self._extract_result(result)
        return result

    # ─────────────── seeding ───────────────

    def _seed_rows(
        self, group: GroupDef, stored: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]]:
        stored = stored or []
        count = len(stored) if stored else group.rows.default
        if group.is_multi_row:
            count = max(group.rows.min, min(count, group.rows.max))
        else:
            count = 1

        rows: list[dict[str, Any]] = []
        for i in range(count):
            source = stored[i] if i < len(stored) else {}
            row: dict[str, Any] = {}
            for f in group.fields:
                if f.kind is FieldKind.CALCULATED:
                    row[f.key] = EMPTY
                    continue
                if f.key in source and source[f.key] is not None:
                    row[f.key] = source[f.key]
                elif f.default is not None:
                    row[f.key] = f.default
                else:
                    row[f.key] = EMPTY
            rows.append(row)
        return rows

    # ─────────────── dependency ordering ───────────────

    def _evaluation_order(self) -> list[tuple[str, str]]:
        """
        Topologically sort calculated fields.

        Dependencies are resolved to the exact field wherever the expression names
        one: `stats.mean_std` depends on that field alone, and `peaks.area` — an
        input column — creates no dependency at all. Only a *bare* group reference
        (`mean(standard)`) falls back to depending on everything calculated in that
        group, because then the expression really could be reading any of it.

        The precision matters for more than speed. Depending on a whole group
        reports circular references that do not exist: a total summing an input
        column would appear to depend on the per-row percentages that divide by
        that total, which is a legitimate and common sheet shape.
        """
        nodes: list[tuple[str, str]] = []
        deps: dict[tuple[str, str], set[tuple[str, str]]] = {}

        calculated_by_group: dict[str, list[str]] = {}
        for group in self._def.groups:
            for f in group.fields:
                if f.kind is FieldKind.CALCULATED:
                    nodes.append((group.key, f.key))
                    calculated_by_group.setdefault(group.key, []).append(f.key)

        for group in self._def.groups:
            for f in group.fields:
                if f.kind is not FieldKind.CALCULATED or not f.expression:
                    continue
                node = (group.key, f.key)
                node_deps: set[tuple[str, str]] = set()
                try:
                    paths = referenced_paths(f.expression)
                except ExpressionError as exc:
                    raise EvaluationError(
                        f"{group.key}.{f.key}: invalid expression — {exc}"
                    ) from exc

                for path in paths:
                    root = path[0]
                    if root in ("row", "prev", "prior"):
                        continue

                    if len(path) >= 2:
                        #  Qualified: `group.field`. Depend on it only if that
                        #  field is itself calculated; an input needs no ordering.
                        if path[1] in calculated_by_group.get(root, []):
                            dep = (root, path[1])
                            if dep != node:
                                node_deps.add(dep)
                        continue

                    #  Same-group sibling reference (bare field name).
                    if root in calculated_by_group.get(group.key, []) and root != f.key:
                        node_deps.add((group.key, root))
                        continue

                    #  Bare group reference — the expression could read anything
                    #  calculated in it, so depend on all of it.
                    for dep_field in calculated_by_group.get(root, []):
                        if (root, dep_field) != node:
                            node_deps.add((root, dep_field))

                deps[node] = node_deps

        return self._toposort(nodes, deps)

    @staticmethod
    def _toposort(
        nodes: list[tuple[str, str]], deps: dict[tuple[str, str], set[tuple[str, str]]]
    ) -> list[tuple[str, str]]:
        ordered: list[tuple[str, str]] = []
        state: dict[tuple[str, str], int] = {}  # 0 = visiting, 1 = done

        def visit(node: tuple[str, str], trail: list[tuple[str, str]]) -> None:
            mark = state.get(node)
            if mark == 1:
                return
            if mark == 0:
                cycle = " -> ".join(f"{g}.{f}" for g, f in [*trail, node])
                raise EvaluationError(f"Circular reference in template: {cycle}")
            state[node] = 0
            for dep in sorted(deps.get(node, set())):
                if dep in deps or dep in nodes:
                    visit(dep, [*trail, node])
            state[node] = 1
            ordered.append(node)

        for node in nodes:
            visit(node, [])
        return ordered

    # ─────────────── field evaluation ───────────────

    def _evaluate_field(
        self, group: GroupDef, field_def: FieldDef, result: WorksheetResult
    ) -> None:
        rows = result.rows.get(group.key) or []
        for index in range(len(rows)):
            scope = self._build_scope(result, group, index)
            try:
                value = evaluate(field_def.expression or "", scope)
            except ExpressionError as exc:
                raise EvaluationError(
                    f"{group.key}.{field_def.key} (row {index + 1}): {exc}"
                ) from exc
            rows[index][field_def.key] = _apply_rounding(value, field_def, scope)

    def _build_scope(
        self, result: WorksheetResult, group: GroupDef, row_index: int
    ) -> dict[str, Any]:
        scope: dict[str, Any] = dict(result.values)

        # Column series for every group, so any formula can aggregate any group.
        for other in self._def.groups:
            other_rows = result.rows.get(other.key) or []
            if other.is_multi_row:
                scope[other.key] = {
                    f.key: [r.get(f.key, EMPTY) for r in other_rows] for f in other.fields
                }
            else:
                scope[other.key] = dict(other_rows[0]) if other_rows else {}

        # The current row: unqualified and via `row.`
        rows = result.rows.get(group.key) or []
        current = dict(rows[row_index]) if row_index < len(rows) else {}
        scope.update(current)
        scope["row"] = current
        scope["rowno"] = float(row_index + 1)

        # Sequence groups get access to earlier rows.
        if group.kind is GroupKind.SEQUENCE:
            preceding = rows[:row_index]
            scope["prev"] = dict(preceding[-1]) if preceding else {}
            scope["prior"] = {
                f.key: [r.get(f.key, EMPTY) for r in preceding] for f in group.fields
            }

        return scope

    # ─────────────── criteria & result ───────────────

    def _evaluate_criteria(self, result: WorksheetResult) -> list[CriterionResult]:
        scope = self._sheet_scope(result)
        out: list[CriterionResult] = []
        for criterion in self._def.criteria:
            try:
                observed = evaluate(criterion.target, scope)
            except ExpressionError as exc:
                raise EvaluationError(
                    f"criterion {criterion.key!r}: invalid target expression — {exc}"
                ) from exc
            out.append(
                CriterionResult(
                    key=criterion.key,
                    label=criterion.label,
                    observed=observed,
                    operator=criterion.operator,
                    limit=criterion.limit,
                    severity=criterion.severity,
                    limit_text=criterion.limit_text,
                    passed=self._assess(observed, criterion),
                )
            )
        return out

    @staticmethod
    def _assess(observed: Any, criterion: CriterionDef) -> bool | None:
        if observed is EMPTY or observed is None:
            return None
        if not isinstance(observed, (int, float)) or isinstance(observed, bool):
            return None
        value = float(observed)
        if criterion.operator is Operator.LTE:
            return value <= criterion.limit[0]
        if criterion.operator is Operator.GTE:
            return value >= criterion.limit[0]
        if criterion.operator is Operator.BETWEEN:
            low, high = criterion.limit[0], criterion.limit[1]
            return low <= value <= high
        if criterion.operator is Operator.EQ:
            return value == criterion.limit[0]
        return None

    def _sheet_scope(self, result: WorksheetResult) -> dict[str, Any]:
        scope: dict[str, Any] = dict(result.values)
        for group in self._def.groups:
            rows = result.rows.get(group.key) or []
            if group.is_multi_row:
                scope[group.key] = {
                    f.key: [r.get(f.key, EMPTY) for r in rows] for f in group.fields
                }
            else:
                scope[group.key] = dict(rows[0]) if rows else {}
        return scope

    def _extract_result(self, result: WorksheetResult) -> Any:
        ref = self._def.result_ref
        if not ref:
            return EMPTY
        group_key, _, field_key = ref.partition(".")
        group = self._def.group(group_key)
        if group is None:
            return EMPTY
        rows = result.rows.get(group_key) or []
        if not rows:
            return EMPTY
        if not group.is_multi_row:
            return rows[0].get(field_key, EMPTY)
        # For a multi-row group the reportable result is the last non-blank value
        # (matches the sheets, where the group mean sits on the first row of a
        # preparation pair and later rows repeat or leave it blank).
        for row in rows:
            value = row.get(field_key, EMPTY)
            if value is not EMPTY and value is not None:
                return value
        return EMPTY
