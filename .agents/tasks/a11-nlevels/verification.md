# A11 N-levels — verification note

Task: make the A11 microbial-bioassay Standard Stock Solution tables (and the
dose-level tables coupled to them) support a variable number of rows with
add/delete controls, raising the fixed 5 to max N=10, while keeping every
existing 5-level worksheet's computed results bit-for-bit identical.

## What changed (A11 archetype only)

File `backend-v2/scripts/template_definitions/a11_microbial_bioassay.py`:

- Added `_MAX_DOSE_LEVELS = 10` and a helper `_s_label_expr()` that builds the
  dose-name `if`-nest S1..S10 from `rowno` (the engine has no string
  concatenation). Rows 1..5 still evaluate to exactly S1..S5, so default-5
  worksheets are unchanged textually and numerically.
- Row bounds changed from `{min:5,max:5,default:5}` to `{min:3,max:10,default:5}`
  on every dose-level-coupled table:
  * shared `_STANDARD_GROUP` (standard) — used by TPL-A11-0001 and TPL-A11-0002
  * `_API_STOCK_TABLE` (std_stock) — TPL-A11-0001
  * `_AMPHO_API_STOCK_TABLE` (std_stock) — TPL-A11-0003
  * `_AMPHO_API_STANDARD_READINGS` (standard) — TPL-A11-0003
- NOT changed (not coupled to the dose-level count, per task): the sample /
  sample_prep tables in A11-0001 (`sample` min1/max6/default3), A11-0002
  (`sample` min1/max6/default2), A11-0003 (`sample_prep` + `sample` fixed 3).
- Reference-row guard (A11-0001/FP) — `corrected_mean` now compares `rowno`
  against `min(reference_row, count(standard.pip_dose))`:
  * A11-0001 reference_row lives in the `std_meta` singleton:
    `if(rowno = min(std_meta.reference_row, count(standard.pip_dose)), ...)`.
  * FP reference_row lives in the `std_stock` singleton:
    `if(rowno = min(std_stock.reference_row, count(standard.pip_dose)), ...)`.
  With the default 5 filled rows and reference_row 3 the clamp is min(3,5)=3, so
  the corrected mean is bit-for-bit identical to the fixed-5 design. If the
  analyst deletes levels below the declared reference row, the clamp keeps the
  reference on the last real row instead of pointing past the table — it never
  invents a data point.
- A11-0003 keeps its hardcoded `rowno = 3` reference (valid for any N in [3,10]).
  See AMBIGUITY FLAG below.

## Why the regression math is N-safe without any engine change

Investigated `backend-v2/src/domain/services/calculation/expression.py` and
`evaluator.py`:

- `evaluator._build_scope` / `_sheet_scope` project every multi-row group as a
  column series `{field: [v for each row]}` of exactly the stored row count, so
  aggregates see N values automatically. `_seed_rows` clamps the row count to
  `[min,max]` and uses `len(stored)` when rows are present, so N is driven by the
  worksheet, not the default.
- `mean(...)` → `_numeric` skips blanks (EMPTY / None / empty string).
- `slope`/`intercept`/`correl` → `_xy_pairs` zips the two column series
  positionally and DROPS any pair where either side is blank, then requires >= 2
  pairs (else EMPTY). So blank/unfilled trailing rows in a padded table are
  silently excluded from the fit — a partially-filled dose table does NOT corrupt
  the regression. A blank reference row's log_conc is EMPTY, so even that pair is
  dropped.
- Per-row index refs use `[rowno - 1]` (self-scaling) and `[0]` (A11-0003 stock,
  always valid for N>=3). No hardcoded `[4]`/`[5-1]` index assuming exactly 5.

EMPTY-handling semantics are therefore safe for a partially-filled dose table;
no `where(...)`/filter was needed. This is confirmed by the new N=3 / N=6 tests.

## Commands run and results

### 1. Seed validation — `python -m scripts.seed_test_templates --validate-only`
PASS ("All definitions valid"). A11 counts printed:
- TPL-A11-0001 [A11]: 6 groups, 54 inputs, 0 area fields, 26 calculated, 4 criteria
- TPL-A11-0002 [A11]: 5 groups, 54 inputs, 0 area fields, 23 calculated, 4 criteria
- TPL-A11-0003 [A11]: 1 groups, 9 inputs, 0 area fields, 6 calculated, 0 criteria

### 2. A11 parity + new tests — `pytest ...test_seeded_template_parity.py -k A11 -v`
34 passed, 278 deselected. All 29 existing A11 assertions pass UNCHANGED.
New tests added in class `TestA11VariableDoseLevels`:
- `test_six_dose_levels_fit_a_line` — 6 doubling doses; independently-derived
  slope 1.9167, intercept 14.1953, R² 0.9987.
- `test_three_dose_levels_fit_a_line` — floor of 3 levels; slope 1.1542,
  intercept 14.6667, R² 0.9796.
- `test_reference_row_in_bounds_points_at_the_declared_row` — default 5 rows,
  reference_row 3 → row 3 is the reference (unchanged).
- `test_reference_row_past_the_table_is_clamped_to_the_last_row` — reference_row 5
  with only 3 rows → clamped to row 3; no point lost, no invented data.
- `test_ampho_api_stock_table_labels_up_to_ten_levels` — S1..S5 unchanged, S6/S7
  produced for the raised ceiling.

All new expected regression coefficients were computed independently of the
engine (plain least squares over the log_conc / corrected_mean pairs).

### 3. Pre-existing unrelated failures — `pytest backend-v2/tests/calculation -q`
5 failed, 897 passed. The 5 failures are the known pre-existing set, NOT caused
by this change:
- TestA6BDissolutionWithReplacement::test_unit1_release_carryover
- TestA6BDissolutionWithReplacement::test_per_timepoint_summary
- TestA6BDissolutionWithReplacement::test_amount_remaining
- test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf
- test_worksheet_service.py::test_a_qa_correction_reopens_and_republishes_the_result

### 4. Frontend
No frontend file was touched. The generic table renderer already shows
add/delete-row controls when `max > min` (WorksheetForm.tsx `canAddRows = editable
&& group.kind !== 'singleton' && max > min`), which the A11 sample tables already
exercise. Moving these A11 tables to {min:3,max:10} activates the same existing
controls. `npm run build` therefore NOT run (gate only applies if a frontend file
is changed).

## Live-DB driver script (authored, NOT run here)

`backend-v2/scripts/update_a11_nlevels.py` — one idempotent driver for all three
codes. It:
- backs up `backend-v2/lims.db` to `lims.db.bak-a11nlevels-<UTC timestamp>` before
  any write,
- logs in to the local API (admin/admin123) at http://127.0.0.1:8443/api/v1,
- TPL-A11-0001: reuses the existing unapproved v2 Draft (id 55) and PUTs the new
  definition onto it (does NOT branch a v3 on top of a Draft),
- TPL-A11-0002 / TPL-A11-0003: resolves the live Active row by code and
  reuses-or-branches a fresh Draft each,
- PUTs each module definition (server re-validates), reads back and verifies
  std_stock/standard rows == {min:3,max:10,default:5} as applicable, resultRef and
  criteria unchanged vs the live Active definition, and the curve aggregates
  present,
- leaves every Draft UNAPPROVED (never calls /submit or /approve),
- prints per-code Draft version/id and OVERALL PASS/FAIL.

### To run it (apply-live step — do NOT run in this step)
Backend must be started first. Either run `d:\RD-instance\GIT\start-lims.bat`
(backend on 127.0.0.1:8443, frontend on 5174) or just the backend:
```
cd /d d:\RD-instance\GIT\backend-v2
python -m uvicorn src.main:app --host 127.0.0.1 --port 8443
```
Then:
```
cd /d d:\RD-instance\GIT\backend-v2
python -m scripts.update_a11_nlevels
```
Exit 0 = all PASS. Draft version ids/numbers are resolved at runtime and printed
per code; the only hardcoded id is the known TPL-A11-0001 v2 Draft (id 55) reuse.
The concrete version numbers depend on the live DB state at apply time and will
be reported by the script then.

## AMBIGUITY FLAG — A11-0003 reference row

TPL-A11-0003 hardcodes dose row 3 as the plate reference (`if(rowno = 3, ...)`).
Per the task this stays unchanged: row 3 remains a valid in-range reference for
any N in [3,10], so raising the ceiling is safe. If the user's variable-level
intent is that the reference should track the MIDDLE dose (e.g. row 5 when N=10)
rather than a fixed row 3, that is a product decision and was NOT made here; it
is flagged for the user/reviewer to confirm. The safe default (keep hardcoded 3)
preserves today's behavior.
