"""Roll the tabular "Standard Details" layout out to the template catalogue.

Part 1 is the pure, database-free harness shared by the module-layer tests and the
live-catalogue sync tool (part 2, at the end of the file):

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

import argparse
import copy
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from scripts.template_definitions._common import (
    STANDARD_ROW_LABEL,
    STANDARD_ROWS,
    as_standard_table,
)
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


# ══ Part 2: live catalogue sync ══════════════════════════════════════
#
#  Raw sqlite3, in the style of scripts/update_a2_0002_definition.py. The tool never
#  copies a module over a row: it applies ``convert_definition`` to the stored
#  definition, so edits made to the live row since it was seeded are kept.
#
#      python -m scripts.standard_tabular_rollout --db <abs path to lims.db> \
#          (--dry-run | --apply | --verify) [--report-dir <dir>]
#
#  --dry-run and --verify open the database read-only (``mode=ro``). --apply takes
#  a backup first, then writes in one ``BEGIN IMMEDIATE`` transaction.

EXPECTED_ROWS = 57
EXPECTED_STATUSES: dict[str, int] = {"Active": 48, "Draft": 4, "Inactive": 3, "Superseded": 2}
ACTOR = "std-details-rollout"
BACKUP_INFIX = ".bak-std-rollout-"
LOCK_TIMEOUT_S = 30
#  Rows whose ``standard_2`` must be a table after the sync (user's last request).
STANDARD_2_CODES: frozenset[str] = frozenset({"TPL-A4-0001", "TPL-H1-0001", "TPL-H1-0002"})
#  Converted in an earlier commit; the sync only re-verifies it.
REFERENCE_CODE = "TPL-A2-0002"
_TS_FORMAT = "%Y-%m-%d %H:%M:%S.%f"  # what SQLAlchemy stores for DateTime columns


class RolloutError(Exception):
    """A pre-condition or post-condition failed; nothing was (or stays) written."""


def _open_ro(path: str | Path) -> sqlite3.Connection:
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)


def _digest(rows: Iterable[Iterable[Any]]) -> str:
    h = hashlib.sha256()
    for row in rows:
        h.update(repr(tuple(row)).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _group(defn: dict | None, key: str) -> dict | None:
    for g in (defn or {}).get("groups") or []:
        if g.get("key") == key:
            return g
    return None


def _json(text: Any) -> Any:
    if text is None:
        return None
    return json.loads(text) if isinstance(text, (str, bytes)) else text


# ── Fingerprint ──────────────────────────────────────────────────────


def fingerprint(
    con: sqlite3.Connection,
    expected_rows: int = EXPECTED_ROWS,
    expected_statuses: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Confirm this is the catalogue the roster was built against.

    Row count, per-status counts and ``PRAGMA integrity_check`` must all match,
    otherwise ``RolloutError`` is raised before anything is written. The expected
    values are arguments so tests can use a small database.
    """
    expected_statuses = EXPECTED_STATUSES if expected_statuses is None else expected_statuses
    rows = con.execute("select count(*) from test_templates").fetchone()[0]
    statuses = {s: n for s, n in con.execute("select status, count(*) from test_templates group by status")}
    integrity = [r[0] for r in con.execute("pragma integrity_check")]
    problems = []
    if rows != expected_rows:
        problems.append(f"{rows} template rows, expected {expected_rows}")
    if statuses != expected_statuses:
        problems.append(f"status counts {dict(sorted(statuses.items()))}, expected {dict(sorted(expected_statuses.items()))}")
    if integrity != ["ok"]:
        problems.append(f"integrity_check: {integrity[:3]}")
    if problems:
        raise RolloutError("fingerprint mismatch: " + "; ".join(problems))
    return {"rows": rows, "statuses": statuses, "integrity": "ok"}


# ── Plan ─────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _modules() -> dict[str, Any]:
    from scripts.template_definitions import SEED_TEMPLATES

    return {t.code: t for t in SEED_TEMPLATES}


@dataclass
class RowPlan:
    entry: RosterEntry
    row_id: int | None = None
    status: str | None = None
    #  "convert": the stored definition changes. "skip": every group is already a
    #  table. "error": the row cannot be planned.
    action: str = "error"
    old_def: dict | None = None
    new_def: dict | None = None
    #  Group keys whose stored shape changes.
    converted: tuple[str, ...] = ()
    audit: list[str] = field(default_factory=list)
    equivalence: EquivalenceReport | None = None
    worksheets: int = 0
    drift: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


@dataclass
class Plan:
    rows: list[RowPlan]

    @property
    def problems(self) -> list[str]:
        return [f"{r.entry.code} v{r.entry.version}: {p}" for r in self.rows for p in r.problems]

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def to_convert(self) -> list[RowPlan]:
        return [r for r in self.rows if r.action == "convert"]

    @property
    def group_count(self) -> int:
        return sum(len(r.converted) for r in self.rows)

    @property
    def audit_violations(self) -> int:
        return sum(len(r.audit) for r in self.rows)

    @property
    def equivalence_diffs(self) -> int:
        return sum(len(r.equivalence.diffs) for r in self.rows if r.equivalence)


def structural_problems(old: dict, new: dict, keys: Iterable[str]) -> list[str]:
    """
    The structural-diff guard: only the target groups may differ, and only by
    ``kind``, ``rows``, ``rowLabel`` and the removal of ``renderAsTable``.
    """
    keys = tuple(keys)
    problems: list[str] = []
    for k in sorted(set(old) | set(new)):
        if k != "groups" and old.get(k, _MISSING) != new.get(k, _MISSING):
            problems.append(f"top-level key {k!r} changed")
    og, ng = old.get("groups") or [], new.get("groups") or []
    if [g.get("key") for g in og] != [g.get("key") for g in ng]:
        return problems + ["group list or order changed"]
    for o, n in zip(og, ng):
        key = o.get("key")
        if key not in keys:
            if o != n:
                problems.append(f"group {key!r} is not a target but changed")
            continue
        if o.get("kind") == "table":
            if o != n:
                problems.append(f"group {key!r} is already a table but changed")
            continue
        if n.get("kind") != "table":
            problems.append(f"group {key!r} did not become a table")
        if n.get("rows") != STANDARD_ROWS or n.get("rowLabel") != STANDARD_ROW_LABEL:
            problems.append(f"group {key!r} has the wrong rows / rowLabel")
        drop_old, drop_new = {"kind", "renderAsTable", "rows", "rowLabel"}, {"kind", "rows", "rowLabel"}
        if {k: v for k, v in o.items() if k not in drop_old} != {k: v for k, v in n.items() if k not in drop_new}:
            problems.append(f"group {key!r} changed beyond kind/rows/rowLabel/renderAsTable")
    return problems


def _drift(live: dict, module: dict) -> list[str]:
    """Where the live definition differs from its module (informational)."""
    out = [
        k
        for k in sorted(set(live) | set(module))
        if k != "groups" and live.get(k, _MISSING) != module.get(k, _MISSING)
    ]
    lg = {g.get("key"): g for g in live.get("groups") or []}
    mg = {g.get("key"): g for g in module.get("groups") or []}
    for key in list(lg) + [k for k in mg if k not in lg]:
        if lg.get(key) != mg.get(key):
            out.append(f"groups.{key}")
    if not out and [g.get("key") for g in live.get("groups") or []] != list(mg):
        out.append("groups.order")
    return out


def module_check(entry: RosterEntry, new_def: dict) -> tuple[list[str], list[str]]:
    """
    Compare the converted definition with the module, as the roster declares.

    ``equal`` rows must equal the module exactly; ``drifted`` rows must match it on
    ``kind``/``rows``/``rowLabel`` of the converted groups (the drift is listed);
    ``none`` rows must have no module. Returns ``(drift, problems)``.
    """
    module = _modules().get(entry.code)
    if entry.module == "none":
        return [], ([f"roster says DB-only but a module exists for {entry.code}"] if module else [])
    if module is None:
        return [], [f"roster says {entry.module} but no module has code {entry.code}"]
    mdef = module.definition
    drift = _drift(new_def, mdef)
    if entry.module == "equal":
        return drift, ([f"converted definition differs from its module: {drift}"] if new_def != mdef else [])
    problems = []
    for key in entry.keys:
        live_g, mod_g = _group(new_def, key), _group(mdef, key)
        if mod_g is None:
            problems.append(f"module has no group {key!r}")
            continue
        for attr in ("kind", "rows", "rowLabel"):
            if (live_g or {}).get(attr) != mod_g.get(attr):
                problems.append(f"group {key!r} {attr} differs from the module")
    return drift, problems


def _load_worksheets(con: sqlite3.Connection) -> dict[int, list[tuple[dict, dict]]]:
    out: dict[int, list[tuple[dict, dict]]] = {}
    for tid, ctx, groups in con.execute(
        "select template_id, context_values, group_values from test_worksheets order by rowid"
    ):
        out.setdefault(tid, []).append((_json(ctx) or {}, _json(groups) or {}))
    return out


def plan_changes(con: sqlite3.Connection, roster: Iterable[RosterEntry] = ROSTER) -> Plan:
    """
    Plan the sync without writing. Every problem is recorded on its row; the caller
    must refuse to apply a plan that is not ``ok`` (one bad row aborts the run).
    """
    worksheets = _load_worksheets(con)
    rows: list[RowPlan] = []
    for entry in roster:
        rp = RowPlan(entry=entry)
        rows.append(rp)
        found = con.execute(
            "select id, status, definition from test_templates where code=? and version=?",
            (entry.code, entry.version),
        ).fetchall()
        if len(found) != 1:
            rp.problems.append(f"expected 1 row for code+version, found {len(found)}")
            continue
        rp.row_id, rp.status, text = found[0]
        if rp.row_id != entry.template_id:
            rp.problems.append(f"id is {rp.row_id}, roster says {entry.template_id}")
        if rp.status != entry.status:
            rp.problems.append(f"status is {rp.status!r}, expected {entry.status!r}")
        try:
            rp.old_def = _json(text)
        except ValueError as exc:
            rp.problems.append(f"stored definition is not valid JSON: {exc}")
            continue
        if not isinstance(rp.old_def, dict):
            rp.problems.append("stored definition is not an object")
            continue
        try:
            rp.new_def = convert_definition(rp.old_def, entry.keys)
        except ValueError as exc:
            rp.problems.append(str(exc))
            continue
        rp.converted = tuple(
            k for k in entry.keys if _group(rp.old_def, k) != _group(rp.new_def, k)
        )
        rp.action = "convert" if rp.new_def != rp.old_def else "skip"
        rp.problems += structural_problems(rp.old_def, rp.new_def, entry.keys)
        rp.audit = audit_references(rp.old_def, entry.keys)
        rp.problems += [f"reference audit: {v}" for v in rp.audit]
        rp.worksheets = len(worksheets.get(rp.row_id, []))
        try:
            TemplateDefinition.parse(rp.new_def)
        except Exception as exc:  # noqa: BLE001
            rp.problems.append(f"converted definition does not parse: {str(exc)[:200]}")
            continue
        if rp.action == "convert":
            try:
                rp.equivalence = check_equivalence(
                    rp.old_def, rp.new_def, entry.keys, worksheets.get(rp.row_id, [])
                )
            except Exception as exc:  # noqa: BLE001
                rp.problems.append(f"equivalence check failed to run: {type(exc).__name__}: {str(exc)[:200]}")
            else:
                for variant, cell, old, new in rp.equivalence.diffs[:5]:
                    rp.problems.append(f"equivalence diff [{variant}] {cell}: {old!r} -> {new!r}")
                if len(rp.equivalence.diffs) > 5:
                    rp.problems.append(f"... {len(rp.equivalence.diffs)} equivalence diffs in total")
                if not rp.equivalence.coverage_ok:
                    rp.problems.append("equivalence run had no non-blank calculated cell (vacuous)")
        rp.drift, module_problems = module_check(entry, rp.new_def)
        rp.problems += [f"module check: {p}" for p in module_problems]
    return Plan(rows)


# ── Snapshot and verify ──────────────────────────────────────────────


@dataclass(frozen=True)
class TemplateState:
    code: str
    version: int
    status: str
    ident_hash: str  # every column except definition, modified_by, modified_date
    full_hash: str  # every column
    definition: dict
    modified_by: str | None


@dataclass
class Snapshot:
    row_count: int
    statuses: dict[str, int]
    templates: dict[int, TemplateState]
    worksheets_count: int
    worksheets_hash: str


def snapshot(con: sqlite3.Connection) -> Snapshot:
    """Capture the state ``verify`` compares against."""
    cols = [r[1] for r in con.execute("pragma table_info(test_templates)")]
    skip = {"definition", "modified_by", "modified_date"}
    ident_idx = [i for i, c in enumerate(cols) if c not in skip]
    pos = {c: i for i, c in enumerate(cols)}
    templates: dict[int, TemplateState] = {}
    for row in con.execute("select * from test_templates order by id"):
        templates[row[pos["id"]]] = TemplateState(
            code=row[pos["code"]],
            version=row[pos["version"]],
            status=row[pos["status"]],
            ident_hash=_digest([[row[i] for i in ident_idx]]),
            full_hash=_digest([row]),
            definition=_json(row[pos["definition"]]),
            modified_by=row[pos["modified_by"]],
        )
    statuses = {s: n for s, n in con.execute("select status, count(*) from test_templates group by status")}
    ws_rows = con.execute("select * from test_worksheets order by rowid").fetchall()
    return Snapshot(len(templates), statuses, templates, len(ws_rows), _digest(ws_rows))


def verify(
    con: sqlite3.Connection,
    pre: Snapshot,
    roster: Iterable[RosterEntry] = ROSTER,
    *,
    replay: bool = True,
) -> list[str]:
    """
    Post-state checks against the pre-state snapshot. Returns the failures (an
    empty list means the sync is correct). Safe to call inside the write
    transaction or on a read-only connection.
    """
    roster = tuple(roster)
    failures: list[str] = []
    cur = snapshot(con)
    integrity = [r[0] for r in con.execute("pragma integrity_check")]
    if integrity != ["ok"]:
        failures.append(f"integrity_check: {integrity[:3]}")
    if cur.row_count != pre.row_count:
        failures.append(f"row count {cur.row_count}, was {pre.row_count}")
    if cur.statuses != pre.statuses:
        failures.append(f"status counts {cur.statuses}, were {pre.statuses}")
    if set(cur.templates) != set(pre.templates):
        failures.append("the set of template ids changed")
    if cur.worksheets_count != pre.worksheets_count or cur.worksheets_hash != pre.worksheets_hash:
        failures.append("test_worksheets content changed")

    by_key = {(s.code, s.version): i for i, s in pre.templates.items()}
    roster_ids: set[int] = set()
    worksheets = _load_worksheets(con) if replay else {}
    for entry in roster:
        label = f"{entry.code} v{entry.version}"
        tid = by_key.get((entry.code, entry.version))
        if tid is None or tid not in cur.templates:
            failures.append(f"{label}: not found")
            continue
        roster_ids.add(tid)
        before, after = pre.templates[tid], cur.templates[tid]
        if after.ident_hash != before.ident_hash:
            failures.append(f"{label}: an identity column changed")
        try:
            expected = convert_definition(before.definition, entry.keys)
        except ValueError as exc:
            failures.append(f"{label}: {exc}")
            continue
        if after.definition != expected:
            failures.append(f"{label}: definition is not convert(pre-state definition)")
        if after.definition == before.definition:
            if after.full_hash != before.full_hash:
                failures.append(f"{label}: unchanged definition but the row changed")
        elif after.modified_by != ACTOR:
            failures.append(f"{label}: modified_by is {after.modified_by!r}")
        for key in entry.keys:
            g, g_before = _group(after.definition, key), _group(before.definition, key)
            if g is None or g.get("kind") != "table":
                failures.append(f"{label}: {key} is not a table")
                continue
            if "renderAsTable" in g:
                failures.append(f"{label}: {key} still has renderAsTable")
            if (g_before or {}).get("kind") == "singleton" and (
                g.get("rows") != STANDARD_ROWS or g.get("rowLabel") != STANDARD_ROW_LABEL
            ):
                failures.append(f"{label}: {key} has the wrong rows / rowLabel")
        if entry.code in STANDARD_2_CODES and (_group(after.definition, "standard_2") or {}).get("kind") != "table":
            failures.append(f"{label}: standard_2 is not a table")
        _, module_problems = module_check(entry, after.definition)
        failures += [f"{label}: module check: {p}" for p in module_problems]
        if replay and after.definition != before.definition:
            rep = check_equivalence(before.definition, after.definition, entry.keys, worksheets.get(tid, []))
            if rep.diffs:
                failures.append(f"{label}: {len(rep.diffs)} equivalence diffs, first {rep.diffs[0]!r}")
            if not rep.coverage_ok:
                failures.append(f"{label}: equivalence run was vacuous")

    for tid, before in pre.templates.items():
        if tid in roster_ids or tid not in cur.templates:
            continue
        if cur.templates[tid].full_hash != before.full_hash:
            failures.append(f"{before.code} v{before.version}: not on the roster but changed")
        if before.code == REFERENCE_CODE:
            g = _group(cur.templates[tid].definition, "standard")
            if not g or g.get("kind") != "table" or g.get("rows") != STANDARD_ROWS:
                failures.append(f"{REFERENCE_CODE}: Standard Details is not the reference table")
    return failures


# ── Apply ────────────────────────────────────────────────────────────


@dataclass
class ApplyResult:
    plan: Plan
    backup: Path | None
    updated: list[str]


def _backup(con: sqlite3.Connection, db_path: Path, now: datetime) -> Path:
    dest = db_path.with_name(db_path.name + BACKUP_INFIX + now.strftime("%Y%m%d-%H%M%S"))
    if dest.exists():
        raise RolloutError(f"backup file already exists: {dest}")
    dst = sqlite3.connect(str(dest))
    try:
        con.backup(dst)
    finally:
        dst.close()
    check = _open_ro(dest)
    try:
        want = con.execute("select count(*) from test_templates").fetchone()[0]
        got = check.execute("select count(*) from test_templates").fetchone()[0]
        integrity = [r[0] for r in check.execute("pragma integrity_check")]
    finally:
        check.close()
    if got != want or integrity != ["ok"]:
        raise RolloutError(f"backup {dest} failed its check ({got} rows, expected {want}; integrity {integrity[:3]})")
    return dest


def apply_changes(
    db_path: str | Path,
    roster: Iterable[RosterEntry] = ROSTER,
    *,
    expected_rows: int = EXPECTED_ROWS,
    expected_statuses: dict[str, int] | None = None,
    now: datetime | None = None,
    replay: bool = True,
) -> ApplyResult:
    """
    Write the converted definitions: fingerprint, plan, backup, then one
    ``BEGIN IMMEDIATE`` transaction that updates only ``definition``,
    ``modified_by`` and ``modified_date``, verifies inside the transaction and
    commits. Any failure raises ``RolloutError`` after a rollback. When every row
    is already converted nothing is written and no backup is taken.
    """
    roster = tuple(roster)
    db_path = Path(db_path)
    now = now or datetime.now(timezone.utc)
    con = sqlite3.connect(str(db_path), timeout=LOCK_TIMEOUT_S, isolation_level=None)
    try:
        fingerprint(con, expected_rows, expected_statuses)
        plan = plan_changes(con, roster)
        if not plan.ok:
            raise RolloutError("plan has problems, nothing written:\n  " + "\n  ".join(plan.problems))
        todo = plan.to_convert
        if not todo:
            return ApplyResult(plan, None, [])
        backup = _backup(con, db_path, now)
        con.execute("BEGIN IMMEDIATE")
        try:
            pre = snapshot(con)
            for rp in todo:
                stored = con.execute("select definition from test_templates where id=?", (rp.row_id,)).fetchone()
                if stored is None or _json(stored[0]) != rp.old_def:
                    raise RolloutError(f"{rp.entry.code}: definition changed since it was planned")
            stamp = now.strftime(_TS_FORMAT)
            for rp in todo:
                cur = con.execute(
                    "UPDATE test_templates SET definition=?, modified_by=?, modified_date=? WHERE id=?",
                    (json.dumps(rp.new_def), ACTOR, stamp, rp.row_id),
                )
                if cur.rowcount != 1:
                    raise RolloutError(f"{rp.entry.code}: expected one updated row, got {cur.rowcount}")
            failures = verify(con, pre, roster, replay=replay)
            if failures:
                raise RolloutError("verification failed inside the transaction:\n  " + "\n  ".join(failures))
            con.execute("COMMIT")
        except BaseException:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        return ApplyResult(plan, backup, [f"{rp.entry.code} v{rp.entry.version}" for rp in todo])
    finally:
        con.close()


# ── Report ───────────────────────────────────────────────────────────


def write_roster(plan: Plan, path: Path, header: Iterable[str] = ()) -> None:
    """Write the per-row roster table (``roster.md``)."""
    lines = ["# Standard Details to tabular: roster", ""]
    lines += list(header)
    lines += [
        "",
        f"Rows to convert: {len(plan.to_convert)} of {len(plan.rows)}; groups converted: {plan.group_count}; "
        f"reference-audit violations: {plan.audit_violations}; equivalence diffs: {plan.equivalence_diffs}; "
        f"problems: {len(plan.problems)}.",
        "",
        "| Code | Id | Ver | Status | Groups | Source | Module | Action | Drift | Equivalence variants | Non-blank calculated |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in plan.rows:
        e = r.entry
        variants = (
            ", ".join(f"{k} {n}" for k, n in Counter(r.equivalence.variants).items()) if r.equivalence else "-"
        )
        coverage = str(r.equivalence.nonblank_calculated) if r.equivalence else "-"
        lines.append(
            f"| {e.code} | {r.row_id if r.row_id is not None else '-'} | {e.version} | {r.status or '-'} "
            f"| {', '.join(e.keys)} | {e.source} | {e.module} | {r.action} "
            f"| {', '.join(r.drift) or '-'} | {variants} | {coverage} |"
        )
    if plan.problems:
        lines += ["", "## Problems", ""] + [f"- {p}" for p in plan.problems]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary(plan: Plan) -> str:
    skipped = sum(1 for r in plan.rows if r.action == "skip")
    drifted = sum(1 for r in plan.rows if r.entry.module == "drifted")
    return (
        f"rows to convert: {len(plan.to_convert)} (already tabular: {skipped}), groups: {plan.group_count}\n"
        f"reference-audit violations: {plan.audit_violations}\n"
        f"equivalence diffs: {plan.equivalence_diffs}\n"
        f"module drift: {drifted} rows drifted, "
        f"{sum(1 for r in plan.rows if r.entry.module == 'none')} DB-only, "
        f"{sum(1 for r in plan.rows if r.entry.module == 'equal')} equal to their module\n"
        f"problems: {len(plan.problems)}"
    )


def _latest_backup(db_path: Path) -> Path | None:
    found = sorted(db_path.parent.glob(db_path.name + BACKUP_INFIX + "*"))
    return found[-1] if found else None


# ── CLI ──────────────────────────────────────────────────────────────


def main(
    argv: list[str] | None = None,
    *,
    roster: Iterable[RosterEntry] = ROSTER,
    expected_rows: int = EXPECTED_ROWS,
    expected_statuses: dict[str, int] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="standard_tabular_rollout", description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True, help="absolute path to lims.db")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="plan and prove equivalence, read-only")
    mode.add_argument("--apply", action="store_true", help="back up, then write the converted definitions")
    mode.add_argument("--verify", action="store_true", help="check the live state against the latest backup, read-only")
    parser.add_argument("--report-dir", default=".", help="where roster.md is written")
    parser.add_argument("--backup", help="pre-state backup for --verify (default: newest beside the database)")
    args = parser.parse_args(argv)
    roster = tuple(roster)
    db_path = Path(args.db)
    roster_path = Path(args.report_dir) / "roster.md"
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        if args.dry_run:
            con = _open_ro(db_path)
            try:
                fp = fingerprint(con, expected_rows, expected_statuses)
                plan = plan_changes(con, roster)
            finally:
                con.close()
            write_roster(plan, roster_path, [f"Mode: dry-run, {when}. Database: `{db_path}`. Fingerprint: {fp}."])
            print(_summary(plan))
            for p in plan.problems:
                print("PROBLEM:", p)
            print(f"roster: {roster_path}")
            return 0 if plan.ok else 1

        if args.apply:
            result = apply_changes(
                db_path, roster, expected_rows=expected_rows, expected_statuses=expected_statuses
            )
            print(_summary(result.plan))
            if not result.updated:
                print("no changes: every roster group is already tabular; nothing written")
                return 0
            write_roster(
                result.plan,
                roster_path,
                [f"Mode: apply, {when}. Database: `{db_path}`. Backup: `{result.backup}`."],
            )
            print(f"updated {len(result.updated)} rows; backup: {result.backup}")
            print(f"roster: {roster_path}")
            return 0

        backup = Path(args.backup) if args.backup else _latest_backup(db_path)
        if backup is None or not backup.exists():
            raise RolloutError("no pre-state backup found; pass --backup")
        pre_con = _open_ro(backup)
        try:
            pre = snapshot(pre_con)
            plan = plan_changes(pre_con, roster)
        finally:
            pre_con.close()
        con = _open_ro(db_path)
        try:
            fingerprint(con, expected_rows, expected_statuses)
            failures = verify(con, pre, roster)
        finally:
            con.close()
        write_roster(
            plan,
            roster_path,
            [f"Mode: verify, {when}. Database: `{db_path}`. Pre-state backup: `{backup}`."]
            + ([f"VERIFY FAILED: {len(failures)} failures"] if failures else ["Verify: all checks passed."]),
        )
        print(_summary(plan))
        for f in failures:
            print("FAIL:", f)
        print("verify:", "FAILED" if failures else "OK", f"(pre-state backup {backup})")
        print(f"roster: {roster_path}")
        return 1 if failures or not plan.ok else 0
    except RolloutError as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
