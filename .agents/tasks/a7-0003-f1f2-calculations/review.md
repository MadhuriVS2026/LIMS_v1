# Review — TPL-A7-0003 "Dissolution F1-F2-calculations"

Verdict: APPROVED

## Scope reviewed
Diff `MadhuriWorktree...f1f2-calculations`: one new backend seed module, its
registration in `__init__.py`, one new backend test, and the scoped frontend
render in `WorksheetForm.tsx`. Checked against plan.md and the verbatim user
request.

## Requirements check

1. Fresh template identifiers — PASS.
   `a7_f1f2_calculations.py`: `code="TPL-A7-0003"`, `name="Dissolution
   F1-F2-calculations"`, `test_code="TST-F1F2CALC"`, `archetype="A7"`,
   `test_name="Dissolution F1-F2-calculations"`, `test_type="Quantitative"`,
   `result_unit=None`.

2. Four distinct groups — PASS.
   - §1 `test_product` singleton "Test Product" with the six input fields.
   - §2 `reference_product` singleton "Reference Product" with the SAME six
     fields (shared `_product_header_fields()` helper).
   - §3 `test_timepoints` table "Timepoints for Test Product".
   - §4 `reference_timepoints` table "Timepoints for Reference Product".
   Each product owns its own header and own timepoint table — not A7-0001's
   single-shared-row model. The structure test
   `test_four_data_entry_sections_plus_comparison` and
   `test_both_product_blocks_carry_the_same_six_input_fields` pin this.

3. Six fields per header — PASS.
   Product Name (text), Batch No. (text), Date of Analysis (date), Media (text),
   RPM (number), Volume (number, unit mL). All `kind="input"`. Matches the brief.

4. f1/f2 wired — PASS.
   Fifth `comparison` singleton. Per-point difference built as calculated
   columns on `test_timepoints` reading `reference_timepoints.mean[rowno - 1]`
   (the proven A6/A6B `[rowno - 1]` cross-table pattern; confirmed present in
   those sibling modules and that `rowno` is a 1-based reserved identifier set
   in evaluator.py).
   - f1 expression: `sum_abs_diff / sum_ref * 100` where `sum_abs_diff =
     Σ|R−T|` and `sum_ref = Σ R` over in-scope points. = Σ|R−T|/ΣR×100. ✓
   - f2 expression: `50 * log10(100 / sqrt(1 + mean_sq_diff))` where
     `mean_sq_diff = Σ(R−T)²/n`. = 50·log10(100/√(1+(1/n)Σ(R−T)²)). ✓
   - `resultRef = "comparison.f2"`. ✓
   Independently recomputed the test's example (R=9,23,41,58,89; T=7,21,39,56,84):
   f1 = 13/220×100 = 5.9 (1 dp); f2 = 50·log10(100/√9.2) = 75.9 (1 dp). Both
   match the template output and the parity test assertions.
   All functions used (`abs`, `sqrt`, `log10`, `sum`, `count`, `min`, `if`,
   `isblank`, `blank`, `^`) are present in expression.py's function table.
   Blank-propagation guards (`n_points` blanks an empty sheet; abs_diff masks the
   ref denominator) are sound and prevent a spurious "identical profiles" 0.

5. Registration — PASS.
   `__init__.py` imports `_A7C` next to the existing A7 import and splices
   `*_A7C,` after `*_A7,` in `SEED_TEMPLATES`.

6. Frontend scoped flag + side-by-side render — PASS.
   - `allowSideBySideHeaders = detail.worksheet.template_code === 'TPL-A7-0003'`
     declared beside the existing scoped flags.
   - Dispatch renders `test_product` and `reference_product` in ONE
     `flex flex-wrap gap-3` row, each child `style={{ flex: '1 1 22rem',
     minWidth: 'min(22rem, 100%)' }}`. `reference_product` returns `null` on its
     own pass, so neither is drawn twice.
   - Reuses an extracted `renderSingletonCard` helper; the diff shows the former
     inline non-chart singleton branch removed and replaced by
     `return renderSingletonCard(group);`, so the generic path is byte-identical
     markup. The chart-singleton sub-case is preserved before the call.
   - No new UI libraries (PrimeFlex classes + inline styles only). No change to
     the generic render path for any other template; both other scoped flags
     (`allowClearColumn`, `allowCumulativeVertical`) left intact.

## Verification evidence (recorded by coder, per policy)
- `seed_test_templates --validate-only` -> exit 0, `ok TPL-A7-0003 [A7]`,
  "All definitions valid."
- Seed run adds TPL-A7-0003 + Test Master TST-F1F2CALC; re-run skips
  (idempotent). lims.db absent in fresh worktree (nothing to back up).
- pytest: new test file + catalogue parity -> 3 failed, 289 passed; the 3 are
  the pre-existing `TestA6BDissolutionWithReplacement` failures.
- Frontend `npm run build` (tsc -b && vite build) succeeded, no TS errors.
  eslint not a declared dependency; coder correctly declined to install an
  unpinned tool — tsc in the build covers type checking.

Narrow spot-checks (specific doubt: is the new test green and are the 3
failures truly unrelated?):
- `pytest tests/calculation/test_a7_0003_f1f2_calculations.py` -> 8 passed.
- `pytest tests/calculation/test_seeded_template_parity.py` -> 3 failed
  (all `TestA6BDissolutionWithReplacement`), 281 passed. The A6B replacement
  model is unrelated to TPL-A7-0003; the catalogue-wide invariants covering the
  new template (unique codes, parses/runs empty, resolvable reportable result,
  no unfillable context) all pass.

## Runtime layout check
Not drivable here (needs a running browser). Coder left a clear reviewer/
finalizer instruction in the commit message and plan §10 item 6 describes the
exact checks. Its absence is not a code defect.

## Findings
None. No reachable correctness, security, or data-integrity defect introduced
by the change.
