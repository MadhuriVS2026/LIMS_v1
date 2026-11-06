# Implementation note — TPL-A2-0002 Standard Details → tabular

Reference-implementation phase. Scope: **only TPL-A2-0002** ("Content of Lyso PC /
Lyso PG (mg/mL)"). No other template was touched.

## What changed

### 1. Calculation engine — the engine-wide collapse rule (design-review HIGH #1)
`backend-v2/src/domain/services/calculation/expression.py`
- Added `class ColumnSeries(list)` — a multi-row group's field projected down the
  rows. Being a `list`, aggregates (`mean`/`sd`/`rsd`/`pool`/`slope`/…), `_flatten`,
  `_numeric` and the `_resolve` index branch all see the **full series** unchanged.
- First-row collapse applied **only at scalar numeric coercion**, never in
  `_resolve`:
  - `_as_number`: a non-empty `ColumnSeries` coerces to `series[0]`; empty → `EMPTY`.
    Covers every arithmetic/unary/rounding operand.
  - `_loose_equal`: same collapse for the `=`/`<>` equality path.
- `_resolve` is unchanged — it still returns the whole `ColumnSeries`, so aggregate
  arguments keep seeing the whole series (the rejected `_resolve` collapse would
  have corrupted 800+ aggregate references catalogue-wide).

`backend-v2/src/domain/services/calculation/evaluator.py`
- `_build_scope`, `_sheet_scope` and the sequence `prior` projection now wrap each
  multi-row field's per-row list in `ColumnSeries(...)` instead of a bare list.
- Imported `ColumnSeries` from `expression`.

### 2. New engine tests (design-review HIGH #1: the distinguishing test)
`backend-v2/tests/calculation/test_evaluator.py` → `TestMultiRowScalarCollapse`:
- bare arithmetic `group.field` over a two-row table collapses to row 0;
- **`mean(group.field)` / `sd(group.field)` over a two-row group return the mean /
  SD of BOTH rows** — the test that fails under a `_resolve` collapse and passes
  under the `_as_number` collapse;
- explicit `group.field[1]` still selects the second row;
- bare `group.field = <scalar>` equality collapses to row 0;
- empty series coerces to `EMPTY` (blank propagation preserved).

### 3. Template module (source of truth)
`backend-v2/scripts/template_definitions/a2_lyso_content.py`
- `standard` group: `kind "singleton" → "table"`, added `rows {min:1, max:10,
  default:1}` and `rowLabel {format:"STD - {n}"}`. Fields unchanged (16 inputs).
  `rowLabel` is a frontend-only presentation hint; the backend schema parser
  ignores it (design-review NIT #4).
- No other group touched. This module defines an **inline** standard literal (not
  the shared `standard_group()` helper), so the helper key-awareness issue
  (design-review MEDIUM #2) does not arise in this run; `standard_2` does not
  exist in this template.

### 4. DB re-seed (in-place, v1, authoritative main-repo DB)
`backend-v2/scripts/update_a2_0002_definition.py` (new) — models the established
`update_a2_0006_definition.py` in-place-sync precedent. Copies the module
definition into the existing Active v1 row, preserving identity (id, code, name,
archetype, version, status, test_id, result_unit). Idempotent; aborts on any
identity mismatch. Accepts an optional DB path so it can run from the worktree
(converted module) while writing the main-repo catalogue. Does NOT bump the
version — matches the worklog convention and the task's "still Active/v1" gate.

## Authoritative DB
`d:\RD-instance\GIT\backend-v2\lims.db` (main checkout; the worktree has no
lims.db). Fresh timestamped backup taken before the write:
`lims.db.bak-a2-0002-stdtab-20261105-180049` (2,592,768 bytes).
