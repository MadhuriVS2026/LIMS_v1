"""Roll the tabular "Standard Details" layout out to the template catalogue.

Part 1 (this section) is the pure, database-free harness shared by the module-layer
tests and the live-catalogue sync tool:

* ``ROSTER``              the 25 live rows whose ``standard`` / ``standard_2``
                          singleton becomes a one-row ``table`` (min 1, max 10,
                          default 1).
* ``convert_definition``  the one transform applied to a stored definition. It
                          reuses ``_common.as_standard_table`` and never copies a
                          whole module over a row: some live definitions have been
                          edited since they were seeded.
* ``audit_references``    the static gate. Once a group is a table, a bare
                          ``standard.field`` evaluates to a column series, which the
                          engine collapses to row 1 only in a few contexts. Every
                          reference from outside the group must be in one of them.
* ``synthesize_inputs`` / ``compare_results`` / ``check_equivalence``
                          replay the old and the converted definition on the same
                          inputs and compare every logical cell, every acceptance
                          criterion and the reportable result.

Formula preservation is the hard constraint: no calculated value and no acceptance
criterion may change. ``check_equivalence`` is the proof of that.

Run from ``backend-v2``.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from scripts.template_definitions._common import as_standard_table
from src.domain.services.calculation import expression as ex
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import (
    FieldKind,
    TemplateDefinition,
)

#  The two group keys that count as "standard sections".
STANDARD_KEYS: tuple[str, ...] = ("standard", "standard_2")


# ── Roster ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RosterEntry:
    code: str
    template_id: int
    version: int
    status: str
    #  Group keys to convert on this row.
    keys: tuple[str, ...]
    #  How the source builds the group: "helper" (standard_group()), "inline"
    #  (a literal in the module) or "db" (the row has no module).
    source: str
    #  Module relationship after the sync: "equal" (live definition must equal the
    #  module), "drifted" (module differs elsewhere; only the converted groups are
    #  compared) or "none" (no module).
    module: str


def _r(code, template_id, version, status, keys, source, module) -> RosterEntry:
    return RosterEntry(code, template_id, version, status, tuple(keys), source, module)


_S = ("standard",)
_S2 = ("standard", "standard_2")

ROSTER: tuple[RosterEntry, ...] = (
    _r("TPL-A1-0001", 1, 1, "Active", _S, "helper", "equal"),
    _r("TPL-A1-0002", 15, 1, "Active", _S, "db", "none"),
    _r("TPL-A1-0003", 39, 1, "Active", _S, "inline", "equal"),
    _r("TPL-A2-0001", 2, 1, "Active", _S, "helper", "drifted"),
    _r("TPL-A2-0003", 33, 1, "Active", _S, "inline", "drifted"),
    _r("TPL-A2-0006", 54, 1, "Active", _S, "inline", "equal"),
    _r("TPL-A3-0001", 3, 1, "Active", _S, "helper", "drifted"),
    _r("TPL-A4-0001", 4, 1, "Active", _S2, "helper", "equal"),
    _r("TPL-A4-0004", 52, 1, "Active", _S, "helper", "drifted"),
    _r("TPL-A6A-0001", 6, 1, "Active", _S, "helper", "drifted"),
    _r("TPL-A6A-0002", 22, 1, "Active", _S, "db", "none"),
    _r("TPL-A6A-0003", 23, 1, "Active", _S, "db", "none"),
    _r("TPL-A6A-0004", 34, 1, "Active", _S, "db", "none"),
    _r("TPL-A6A-0005", 44, 3, "Active", _S, "inline", "equal"),
    _r("TPL-A6B-0001", 7, 1, "Active", _S, "inline", "equal"),
    _r("TPL-A6B-0002", 37, 1, "Active", _S, "inline", "equal"),
    _r("TPL-A6C-0001", 8, 1, "Active", _S, "helper", "drifted"),
    _r("TPL-A8-0001", 24, 2, "Active", _S, "helper", "drifted"),
    _r("TPL-A8-0003", 21, 1, "Draft", _S, "db", "none"),
    _r("TPL-A8-0004", 38, 1, "Active", _S, "helper", "equal"),
    _r("TPL-A12-0001", 30, 1, "Active", _S, "helper", "drifted"),
    _r("TPL-A13-0001", 14, 1, "Active", _S, "helper", "drifted"),
    _r("TPL-H1-0001", 16, 1, "Active", _S2, "db", "none"),
    _r("TPL-H1-0002", 20, 1, "Active", _S2, "db", "none"),
    _r("TPL-NITRO-0001", 51, 1, "Active", _S, "inline", "equal"),
)


# ── Transform ────────────────────────────────────────────────────────


def convert_definition(defn: dict, keys: Iterable[str]) -> dict:
    """
    Return a copy of ``defn`` with each group in ``keys`` in tabular form.

    A singleton becomes a one-row ``table``; a group that is already a table is
    left as it is (so the call is idempotent). A key that is missing, or a group
    that is neither singleton nor table, raises ``ValueError``. Nothing but the
    named groups changes, and the input is never mutated.
    """
    out = copy.deepcopy(defn)
    groups = out.get("groups") or []
    for key in keys:
        for i, group in enumerate(groups):
            if group.get("key") != key:
                continue
            if group.get("kind") not in ("singleton", "table"):
                raise ValueError(
                    f"group {key!r} has kind {group.get('kind')!r}; only singleton or table can be converted"
                )
            groups[i] = as_standard_table(group)
            break
        else:
            raise ValueError(f"group {key!r} not found in definition")
    return out


# ── Static reference audit ───────────────────────────────────────────

#  Functions that coerce each argument to a number, so a bare multi-row reference
#  collapses to row 1 inside them (`_as_number`).
_COERCING_FUNCTIONS = frozenset({"round", "trunc", "abs", "sqrt", "ln", "log10", "exp"})

#  Strings under these keys are display text or identifiers, never expressions.
_NON_EXPRESSION_KEYS = frozenset({"label", "limitText", "help", "description", "key", "unit"})

#  The only calculated field allowed to be nothing but a bare reference to a
#  converted group. The evaluator collapses it at the calculated-field sink.
BARE_ALIAS_ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {("groups.corel_weights.fields.std1_weight.expression", "standard.weight_mg")}
)


def _classify(node: Any, parent: Any, index: int, keys: frozenset[str], out: list[tuple[str, str]]) -> None:
    if isinstance(node, ex._Ref):
        head = node.parts[0] if node.parts else None
        if head in keys:
            text = ".".join(str(p) for p in node.parts if isinstance(p, str))
            if len(node.parts) == 1:
                kind = "whole-group"
            elif any(not isinstance(p, str) for p in node.parts[1:]):
                kind = "ok:explicit-index"
            elif parent is None:
                kind = "bare"
            elif isinstance(parent, ex._Binary):
                kind = "logic-operator" if parent.op in ("and", "or") else "ok:operator"
            elif isinstance(parent, ex._Unary):
                kind = "logic-operator" if parent.op == "not" else "ok:operator"
            elif isinstance(parent, ex._Call):
                if parent.name in _COERCING_FUNCTIONS:
                    kind = f"ok:{parent.name}"
                else:
                    kind = f"argument-of-{parent.name}"
            else:
                kind = f"inside-{type(parent).__name__}"
            out.append((kind, text))
        return
    if isinstance(node, ex._Unary):
        _classify(node.operand, node, 0, keys, out)
    elif isinstance(node, ex._Binary):
        _classify(node.left, node, 0, keys, out)
        _classify(node.right, node, 1, keys, out)
    elif isinstance(node, ex._Call):
        for i, arg in enumerate(node.args):
            _classify(arg, node, i, keys, out)
    elif isinstance(node, ex._ListNode):
        for i, item in enumerate(node.items):
            _classify(item, node, i, keys, out)


def _walk_strings(obj: Any, path: tuple[str, ...]) -> Iterable[tuple[tuple[str, ...], str]]:
    """Yield (path, string) for every string that could hold an expression."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(v, path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            label = v["key"] if isinstance(v, dict) and isinstance(v.get("key"), str) else str(i)
            yield from _walk_strings(v, path + (label,))
    elif isinstance(obj, str):
        if path and path[-1] in _NON_EXPRESSION_KEYS:
            return
        yield path, obj


def audit_references(defn: dict, keys: Iterable[str]) -> list[str]:
    """
    List every reference to a converted group that could change a value.

    A reference is accepted when it is an operand of an arithmetic or comparison
    operator, the argument of ``round/trunc/abs/sqrt/ln/log10/exp``, or explicitly
    indexed. Anything else is reported: an argument of ``if/coalesce/number/min/max/
    sum/count/mean/...``, ``and/or/not``, a whole-group reference, a bare reference
    that is the entire expression (except the allow-listed ``corel_weights``
    alias), a criterion target, ``resultRef``, or a string that mentions a
    converted key but does not parse. Returns an empty list when the definition is
    safe to convert.
    """
    keyset = frozenset(keys)
    pattern = re.compile(r"\b(?:%s)\b" % "|".join(sorted(map(re.escape, keyset), key=len, reverse=True)))
    violations: list[str] = []
    for path, text in _walk_strings(defn, ()):
        if not pattern.search(text):
            continue
        where = ".".join(path)
        try:
            node = ex._parse(text)
        except Exception:  # noqa: BLE001 - any parse failure is reported, not raised
            violations.append(f"{where}: unparseable expression mentions a converted group: {text[:80]!r}")
            continue
        found: list[tuple[str, str]] = []
        _classify(node, None, 0, keyset, found)
        for kind, ref in found:
            if kind.startswith("ok:"):
                continue
            if kind == "bare":
                if (where, text.strip()) in BARE_ALIAS_ALLOWLIST and where.endswith(".expression"):
                    continue
                if where.startswith("criteria."):
                    kind = "criterion-target"
                elif where == "resultRef":
                    kind = "result-ref"
            violations.append(f"{where}: {kind} ({ref}) in {text[:80]!r}")
    result_ref = defn.get("resultRef")
    if isinstance(result_ref, str) and result_ref.split(".")[0] in keyset:
        violations.append(f"resultRef: points at a converted group ({result_ref})")
    return violations


# ── Input synthesis ──────────────────────────────────────────────────

#  Extra standard rows in the padded variant are scaled copies of row 1.
PAD_FACTORS: tuple[float, ...] = (1.37, 1.91)


def synthesize_inputs(
    defn: dict, pad_keys: Iterable[str] | None = None
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """
    Deterministic, fully filled ``(context_values, group_values)`` for ``defn``.

    Numbers come from a counter, so the same definition always yields the same
    sheet; text, date and select fields are filled by type; declared defaults are
    honoured on every third field. Singleton groups get one row, tables their
    default row count. For each group in ``pad_keys`` the first row is the same as
    in the unpadded sheet and two more rows follow, each a scaled copy of it, so a
    padded run differs from the plain one only by the extra rows.
    """
    n = [0]

    def val(f: dict) -> Any:
        n[0] += 1
        t = f.get("type")
        if t == "text":
            return "S"
        if t == "date":
            return "2026-01-01"
        options = f.get("options")
        if options:
            first = options[0]
            return first.get("value") if isinstance(first, dict) else first
        if f.get("default") is not None and n[0] % 3 == 0:
            return f["default"]
        return round(1.5 + ((n[0] * 7919) % 5000) / 100.0, 3)

    context: dict[str, Any] = {}
    for c in defn.get("context") or []:
        if c.get("default") is not None:
            context[c["key"]] = c["default"]
        else:
            context[c["key"]] = "T" if c.get("type") == "text" else val(c)

    groups: dict[str, list[dict[str, Any]]] = {}
    for g in defn.get("groups") or []:
        count = 1 if g.get("kind") == "singleton" else (g.get("rows") or {}).get("default", 1)
        inputs = [f for f in g["fields"] if f.get("kind") in ("input", "area")]
        groups[g["key"]] = [{f["key"]: val(f) for f in inputs} for _ in range(count)]

    for key in pad_keys or ():
        base = groups[key][0]
        for factor in PAD_FACTORS:
            #  A different factor per field, so ratios between fields change too
            #  (equal factors would leave a weight/volume concentration unchanged).
            groups[key].append(
                {
                    k: (
                        v * (factor + 0.07 * j)
                        if isinstance(v, (int, float)) and not isinstance(v, bool)
                        else v
                    )
                    for j, (k, v) in enumerate(base.items())
                }
            )
    return context, groups


# ── Comparison ───────────────────────────────────────────────────────

_MISSING = object()


def _is_blank(v: Any) -> bool:
    return v is ex.EMPTY or v is None or v == ""


def _same(a: Any, b: Any) -> bool:
    if a is b:
        return True
    if isinstance(a, float) and isinstance(b, float) and a != a and b != b:
        return True
    try:
        return bool(a == b)
    except Exception:  # noqa: BLE001
        return False


def _cells(result: Any, converted: frozenset[str], skip_rows_of: frozenset[str] = frozenset()) -> dict[str, Any]:
    """
    Flatten a ``WorksheetResult`` into logical cells.

    The flat ``group.field`` mirror of a converted group is dropped: a singleton
    emits it, a table does not, and its logical cell is ``rows[group][0][field]``
    which is compared anyway. Rows of ``skip_rows_of`` groups are left out.
    """
    cells: dict[str, Any] = {}
    for k, v in result.values.items():
        if "." in k and k.split(".", 1)[0] in converted:
            continue
        cells[f"v:{k}"] = v
    for gk, rows in result.rows.items():
        if gk in skip_rows_of:
            continue
        for i, row in enumerate(rows):
            for fk, v in row.items():
                cells[f"r:{gk}[{i}].{fk}"] = v
    for c in result.criteria:
        cells[f"c:{c.key}"] = (c.observed, c.passed, tuple(c.limit), c.severity)
    cells["reportable"] = result.reportable_result
    return cells


def compare_results(old: Any, new: Any, converted_keys: Iterable[str]) -> list[tuple[str, Any, Any]]:
    """
    Compare two ``WorksheetResult`` objects cell by cell.

    Returns ``(cell, old_value, new_value)`` for each difference; an empty list
    means identical. Comparison is exact (``==``; blank equals blank). A list or
    column series in ``new`` where ``old`` held a scalar is a difference.
    """
    converted = frozenset(converted_keys)
    a, b = _cells(old, converted), _cells(new, converted)
    diffs: list[tuple[str, Any, Any]] = []
    for cell in sorted(set(a) | set(b)):
        x, y = a.get(cell, _MISSING), b.get(cell, _MISSING)
        if not _same(x, y):
            diffs.append((cell, "<missing>" if x is _MISSING else x, "<missing>" if y is _MISSING else y))
    return diffs


@dataclass
class EquivalenceReport:
    """Outcome of replaying an old and a converted definition on the same inputs."""

    #  (variant, cell, old_value, new_value); a cell starting "!" is an error message.
    diffs: list[tuple[str, str, Any, Any]] = field(default_factory=list)
    variants: list[str] = field(default_factory=list)
    #  Calculated cells with a value in the old synthetic run. Zero means the
    #  comparison could pass vacuously (blank == blank).
    nonblank_calculated: int = 0
    reportable: Any = None

    @property
    def ok(self) -> bool:
        return not self.diffs

    @property
    def coverage_ok(self) -> bool:
        return self.nonblank_calculated > 0


def _evaluate(evaluator: WorksheetEvaluator, ctx: dict, groups: dict) -> tuple[Any, str | None]:
    try:
        return evaluator.evaluate(ctx, groups), None
    except Exception as exc:  # noqa: BLE001 - recorded as data
        return None, f"{type(exc).__name__}: {exc}"[:200]


def check_equivalence(
    old_def: dict,
    new_def: dict,
    converted_keys: Iterable[str],
    worksheets: Iterable[tuple[dict, dict]] = (),
) -> EquivalenceReport:
    """
    Prove that converting ``converted_keys`` changed no value and no criterion.

    Variants, each evaluated with both definitions and compared by
    ``compare_results``: ``empty`` (no input); ``synth`` (a fully filled sheet);
    one ``ws`` per stored ``(context_values, group_values)`` pair; and ``pad3``,
    where each converted group carries three rows. For ``pad3``, row 1 is still
    authoritative, so every cell outside the converted groups must equal the old
    one-row result, and each extra row's cells must equal what the old definition
    computes when that row's inputs are its single row.
    """
    keys = tuple(converted_keys)
    converted = frozenset(keys)
    report = EquivalenceReport()
    old_eval = WorksheetEvaluator(TemplateDefinition.parse(old_def))
    new_eval = WorksheetEvaluator(TemplateDefinition.parse(new_def))

    synth_ctx, synth_groups = synthesize_inputs(old_def)
    variants: list[tuple[str, dict, dict]] = [("empty", {}, {}), ("synth", synth_ctx, synth_groups)]
    for ctx, groups in worksheets:
        variants.append(("ws", ctx or {}, groups or {}))

    for name, ctx, groups in variants:
        report.variants.append(name)
        old_res, old_err = _evaluate(old_eval, ctx, groups)
        new_res, new_err = _evaluate(new_eval, ctx, groups)
        if old_err or new_err:
            if old_err != new_err:
                report.diffs.append((name, "!error", old_err, new_err))
            continue
        if name == "synth":
            calculated = {
                (g.key, f.key)
                for g in old_eval._def.groups
                for f in g.fields
                if f.kind is FieldKind.CALCULATED
            }
            report.nonblank_calculated = sum(
                1
                for gk, rows in old_res.rows.items()
                for row in rows
                for fk, v in row.items()
                if (gk, fk) in calculated and not _is_blank(v)
            )
            report.reportable = old_res.reportable_result
        for cell, x, y in compare_results(old_res, new_res, converted):
            report.diffs.append((name, cell, x, y))

    #  pad3: extra rows must not disturb row 1 or anything outside the group.
    report.variants.append("pad3")
    base_res, base_err = _evaluate(old_eval, synth_ctx, synth_groups)
    pad_ctx, pad_groups = synthesize_inputs(old_def, pad_keys=keys)
    pad_res, pad_err = _evaluate(new_eval, pad_ctx, pad_groups)
    if base_err or pad_err:
        if base_err != pad_err:
            report.diffs.append(("pad3", "!error", base_err, pad_err))
        return report

    base_cells = _cells(base_res, converted, skip_rows_of=converted)
    pad_cells = _cells(pad_res, converted, skip_rows_of=converted)
    for cell in sorted(set(base_cells) | set(pad_cells)):
        x, y = base_cells.get(cell, _MISSING), pad_cells.get(cell, _MISSING)
        if not _same(x, y):
            report.diffs.append(("pad3", cell, "<missing>" if x is _MISSING else x, "<missing>" if y is _MISSING else y))
    for key in keys:
        if len(pad_res.rows.get(key, [])) != 1 + len(PAD_FACTORS):
            report.diffs.append(("pad3", f"rows:{key}", 1 + len(PAD_FACTORS), len(pad_res.rows.get(key, []))))

    #  Row i of the padded run must equal the old definition fed that row alone.
    for i in range(1 + len(PAD_FACTORS)):
        single = {k: list(v) for k, v in pad_groups.items()}
        for key in keys:
            single[key] = [pad_groups[key][i]]
        single_res, single_err = _evaluate(old_eval, pad_ctx, single)
        if single_err:
            report.diffs.append(("pad3", f"!row{i + 1}", single_err, None))
            continue
        for key in keys:
            old_row = single_res.rows[key][0]
            new_row = pad_res.rows[key][i]
            for fk in sorted(set(old_row) | set(new_row)):
                x, y = old_row.get(fk, _MISSING), new_row.get(fk, _MISSING)
                if not _same(x, y):
                    report.diffs.append(
                        ("pad3", f"r:{key}[{i}].{fk}", "<missing>" if x is _MISSING else x, "<missing>" if y is _MISSING else y)
                    )
    return report
