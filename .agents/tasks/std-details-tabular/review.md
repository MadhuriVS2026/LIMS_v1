# Review — TPL-A2-0002 Standard Details → tabular

Verdict: APPROVED

## Scope reviewed
Branch `std-details-tabular`, diff `MadhuriWorktree...HEAD` in worktree
`d:\RD-instance\GIT\.worktrees\std-details-tabular`. Five files changed:
`expression.py`, `evaluator.py`, `test_evaluator.py`, `a2_lyso_content.py`, and new
`scripts/update_a2_0002_definition.py`.

## Blocking checks — all satisfied

1. Collapse site is scalar coercion, not the resolver — CONFIRMED.
   - `expression.py` `_as_number` (worktree lines ~397–404): `if isinstance(value, ColumnSeries): value = value[0] if len(value) else EMPTY` before blank/number handling. Same collapse added to `_loose_equal` for the `=`/`<>` path.
   - `_resolve` (worktree lines 433–453) is unchanged: it returns `current` as-is, so a bare `group.field` yields the full `ColumnSeries`. The index branch uses `isinstance(current, (list, tuple))`, which matches `ColumnSeries` (subclass of `list`), so `std.weight[1]` still selects row 1.
   - `_numeric`/`_flatten` (lines 372–394) iterate a `ColumnSeries` as an ordinary list, so aggregates see every row.
   - New test `TestMultiRowScalarCollapse::test_aggregate_over_multi_row_group_sees_every_row` asserts `mean(std.weight)` over rows (100, 200) == 150.0 and `sd` == 70.710678. Present in the diff; coder recorded the class as 5 passed.

2. Formula / acceptance-criterion preservation — CONFIRMED per recorded evidence.
   - Before/after parity reported: pc_mgml 0.722738, pg_mgml 0.446133, rsd_std_pc 2.211413, blocking True — all identical old (singleton) vs new (one-row table). No calculated field or criterion changed; the 16 standard input fields are byte-for-byte unchanged in the diff.

3. Scope — CONFIRMED.
   - Only the `standard` group flipped `singleton → table` in `a2_lyso_content.py`. No shared `standard_group()` helper and no `standard_2` exist in this template (grep: no matches); the standard literal is inline, so no out-of-scope singleton flip is possible. Catalogue fingerprint (TOTAL=57/ACTIVE=48) and the SHA over all rows excluding TPL-A2-0002 reported identical before/after — no other template drifted.

4. Source of truth — CONFIRMED.
   - Change lives in the version-controlled module `a2_lyso_content.py` (`kind:"table"`, `rows {min:1,max:10,default:1}`, `rowLabel {format:"STD - {n}"}`). The DB was re-seeded via new `update_a2_0002_definition.py`, which asserts identity (id, code, name, archetype, version=1, status=Active, test_id, result_unit) is preserved and refuses to write on mismatch — not a hand-edited row. No version bump; row stays Active/v1. Read-back reported stored def == module def.

5. Verification recorded — CONFIRMED (not re-run per instructions).
   - `seed_test_templates --validate-only`: exit 0.
   - `pytest -q`: 917 passed, 5 failed; the 5 are pre-existing on base (confirmed by git stash + re-run) — 3× TestA6BDissolutionWithReplacement, 2× test_worksheet_service — unrelated to this change. No new failures.
   - `TestMultiRowScalarCollapse`: 5 passed.
   - Frontend `npm run build` (tsc -b && vite build): zero TS errors. No FE source change needed; the generic renderer drives add/delete off `canAddRows = editable && group.kind !== 'singleton' && max > min` (WorksheetForm.tsx line 1747), and TPL-A2-0002's standard group now satisfies that (table, max 10 > min 1). Verified the `canAddRows` path exists in the worktree frontend.

## Notes (non-blocking)
- `rowLabel` is a frontend-only presentation hint; backend schema parser ignores it. Consistent across module comment, implementation note, and diff.

No material blockers found.
