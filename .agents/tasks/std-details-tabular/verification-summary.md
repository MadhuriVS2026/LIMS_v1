# Verification summary — TPL-A2-0002 Standard Details → tabular

All commands run from `d:\RD-instance\GIT\.worktrees\std-details-tabular\backend-v2`
(so the converted worktree modules are used) unless noted.

## 1. Seed validation gate — PASS (exit 0)
`python -m scripts.seed_test_templates --validate-only`
→ "All definitions valid." Exit 0. TPL-A2-0002 parses with the tabular standard
group (6 groups, 20 inputs, 21 area fields, 26 calculated, 4 criteria).

## 2. Backend test suite — no NEW failures
`python -m pytest -q` → **917 passed, 5 failed** in ~80s.
The 5 failures are **pre-existing on the base commit** (confirmed by `git stash`
+ re-run): identical failures with and without my change.
- `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement` ×3
  (`test_unit1_release_carryover`, `test_per_timepoint_summary`, `test_amount_remaining`)
- `test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`
- `test_worksheet_service.py::test_a_qa_correction_reopens_and_republishes_the_result`
No new failures introduced. All A2 parity tests and the full expression/evaluator
suites pass.

## 3. New distinguishing test — PASS
`pytest tests/calculation/test_evaluator.py::TestMultiRowScalarCollapse -v` → 5 passed.
Includes `test_aggregate_over_multi_row_group_sees_every_row`: `mean` of a two-row
group = mean of both rows (150.0), `sd` = 70.710678 — the assertion that fails
under the rejected `_resolve` collapse and passes under the `_as_number` collapse.

## 4. Before/after parity (formula preservation HARD constraint) — PASS
Evaluated a representative Lyso mg/mL worksheet through the OLD (singleton) and
NEW (one-row table) definition and compared every result cell by logical
(group, field) identity (reconciling the expected `values["standard.*"]` →
`rows["standard"][0]` migration). Result: **every cell identical.**
- reportable pc_mgml = 0.722738 (old == new)
- pg_mgml = 0.446133, stats.rsd_std_pc = 2.211413 (unchanged)
- blocking criteria outcome unchanged (True == True)

## 5. Frontend build — PASS
`npm install` then `npm run build` (`tsc -b && vite build`) in
`frontend-react` → built in 7.56s, **zero TS errors**. No frontend source change
was needed; the generic table renderer drives add/delete off `group.kind` and
`rows` (`canAddRows = editable && kind !== 'singleton' && max > min`), and
`rowLabel` renders the "STD - {n}" caption column. (A chunk-size warning is
informational, not an error.)

## 6. DB re-seed (authoritative main-repo lims.db) — PASS
- Fresh backup before write: `backend-v2/lims.db.bak-a2-0002-stdtab-20261105-180049`.
- `python -m scripts.update_a2_0002_definition <authoritative lims.db>` →
  "TPL-A2-0002 updated; identity preserved (id=25, version=1, status=Active)".
- Read-back: stored definition **== module definition** (byte-consistent);
  version 1, status Active; `standard.kind == "table"`,
  `rows == {min:1,max:10,default:1}`, `rowLabel == {format:"STD - {n}"}`,
  16 fields.
- Catalogue fingerprint before/after: TOTAL=57, ACTIVE=48 unchanged; the
  SHA-256 over all rows **excluding TPL-A2-0002** is identical before and after
  (`e86c12aa...dbdda96eb`) — no out-of-scope drift. Only the full-catalogue SHA
  moved, driven solely by the intended TPL-A2-0002 definition change.

## 7. Worksheet UI
The converted group is `kind:'table'`, min=1/max=10, so the existing generic
renderer shows an editable one-row Standard Details table with working add-row
(up to 10) and delete-row controls and the STD-{n} caption — verified by reading
the `canAddRows` path in `WorksheetForm.tsx` and by the successful production build.
