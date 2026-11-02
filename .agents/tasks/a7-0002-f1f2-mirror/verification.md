# Verification — TPL-A7-0002 "Dissolution Profile Comparison (f1 / f2) — Mirrored"

Worktree: `d:\RD-instance\GIT\.worktrees\f1f2-mirror-template`
Iteration: first (no `review.json` present when this step ran).

## What was built

1. New seed module `backend-v2/scripts/template_definitions/a7_profile_comparison_mirrored.py`
   — TPL-A7-0002, test TST-F1F2M, archetype A7, `resultRef = comparison.f2`. It imports and
   deep-copies the A7 (TPL-A7-0001) timepoint fields, comparison group, context and criteria so the
   f1/f2 arithmetic and the five validity criteria are byte-for-byte identical. The only additive
   field is a per-row `unit` text input (default "Hr"), inserted right after `time`; it is display
   metadata only and is referenced by no expression.
2. Registered in `backend-v2/scripts/template_definitions/__init__.py` (import `_A7M` + `*_A7M,`
   right after `*_A7,`).
3. Frontend custom render in
   `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`, gated on
   `template_code === 'TPL-A7-0002'` + `group.key === 'timepoints'`, following the
   `renderCumulativeVertical` (TPL-A6A-0005) pattern and reusing the shared helpers
   (`renderInput`, `renderGroupToolbar`, `addRow`, `removeRow`, `setCell`, `isGroupEditing`,
   `renderGroupHeaderContext`). Two tables side by side (Reference | Test) in a `flex flex-wrap`
   row, each `flex: 1 1 22rem; minWidth: min(22rem, 100%)`, `w-full` + `tableLayout: fixed`, cells
   wrap (`break-word` / `overflow-wrap: anywhere`). Timepoint label + unit are edited on the Test
   table and shown read-only on the Reference table (same backing row ⇒ mirroring is inherent);
   mean %/%RSD are independently editable per product.

## Backend

### `python -m scripts.seed_test_templates --validate-only` — PASS (exit 0)

All 30 definitions valid. The new template reports:

```
ok   TPL-A7-0002 [A7] 2 groups, 7 inputs, 0 area fields, 18 calculated, 5 criteria
```

(vs TPL-A7-0001: `2 groups, 6 inputs, 0 area fields, 18 calculated, 5 criteria` — i.e. identical
except the one new `unit` input). Line ends: "All definitions valid. --validate-only, so nothing
was written."

### DB backup before seeding

The worktree had **no pre-existing `backend-v2/lims.db`** (checked: `Get-ChildItem lims.db*` returned
nothing; no `.env`; `.env.example` points `DATABASE_URL` at `sqlite:///./lims.db`). There was
therefore no existing database state to protect, so the `lims.db.bak-f1f2mirror-<timestamp>` backup
was not applicable — the seed run below created a fresh `lims.db`. (Had a DB existed, it would have
been copied to `lims.db.bak-f1f2mirror-$(Get-Date -Format 'yyyyMMdd-HHmmss')` first.) `lims.db` and
its backups are gitignored and are not committed.

### `python -m scripts.seed_test_templates` — PASS (exit 0), TPL-A7-0002 ADDED

First run reported the new template added (not skipped):

```
add  TPL-A7-0002 [A7] Dissolution Profile Comparison (f1 / f2) — Mirrored -> TST-F1F2M
     + Test Master: TST-F1F2M — Dissolution Profile Comparison (f1 / f2) — Mirrored
```

A direct sqlite check of the resulting `lims.db` confirmed it holds both the template and the test:

```
test_templates.code: ['TPL-A7-0001', 'TPL-A7-0002']
tests.code:          ['TST-F1F2', 'TST-F1F2M']
```

Re-running the seeder is idempotent — it then reports `skip TPL-A7-0002 — already present (v1, Active)`.

### pytest — catalogue parity + new parity test

`python -m pytest tests/calculation/test_a7_0002_mirrored_parity.py tests/calculation/test_seeded_template_parity.py -q`
→ **272 passed, 3 failed**.

- The new `tests/calculation/test_a7_0002_mirrored_parity.py` **passes**. It feeds the A7 docstring's
  own 5-timepoint example (reference means 9, 23, 41, 58, 89; test means 7, 21, 39, 56, 84) through
  the engine and asserts:
  - `comparison.f1 == 5.9` (the A7 docstring's documented value) and `comparison.f2 == 75.9`
    (the engine's value for the same inputs, derived not copied), `n_points == 5`;
  - full parity with TPL-A7-0001 on identical inputs across `n_points`, `sum_abs_diff`, `sum_ref`,
    `sum_sq_diff`, `mean_sq_diff`, `f1`, `f2`, `points_over_85`, `rsd_breaches` — i.e. the new `unit`
    field perturbs no computed value;
  - the five criteria keys are present (reused verbatim).
- The catalogue-wide parity invariants in `test_seeded_template_parity.py` (unique codes, every
  template parses/runs empty, resolvable reportable result, no unfillable context, area-field
  discovery, every-archetype-seeded) **pass**, now covering TPL-A7-0002.
- The **3 failures are pre-existing and unrelated to this change** — all in
  `TestA6BDissolutionWithReplacement` (the A6B template):
  `test_unit1_release_carryover`, `test_per_timepoint_summary`, `test_amount_remaining`.
  Confirmed by `git stash`-ing the working-tree changes and re-running
  `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement` on the clean HEAD (713c82f):
  the same 3 tests fail there too (3 failed, 1 passed). They are not touched by the A7 work.

The sheet-cited f1 ≈ 5.9 (and f2 = 75.9 for the AmBisome-vs-test profile example) therefore still
computes correctly for the mirrored template.

## Frontend

### `npm run build` (`tsc -b && vite build`) — PASS (exit 0)

`npm ci` first (123 packages; node_modules was absent in the worktree). Build: "336 modules
transformed", "built in 3.96s", exit 0. No TypeScript errors — full type-check clean, including the
new `renderMirroredProfile` and the `CSSProperties` import added for its inline styles. (The usual
non-blocking "chunks larger than 500 kB" advisory is unrelated to this change.)

### eslint — NOT RUNNABLE in this environment (explained)

`npx eslint src/.../WorksheetForm.tsx` and `npm run lint` (`eslint .`) could **not** be run:
eslint is **not a declared dependency** of `frontend-react` (no `eslint` in devDependencies), there
is **no eslint config** (`.eslintrc*` / `eslint.config.*` absent), and **no local
`node_modules/.bin/eslint`**. `npx eslint` therefore tries to fetch an unpinned `eslint@10` from the
network and blocks on an interactive "Ok to proceed?" prompt. I did not install an unrelated,
unpinned tool just to satisfy the lint step. The TypeScript build (above) type-checked the file
cleanly, and the new code reuses the file's existing patterns/helpers (no new lint surface such as
unused vars, floating promises, or `any`).

## Runtime browser check (layout + mirroring) — NOT DRIVEN in this environment

The layout and mirroring behaviour must be confirmed at runtime in a browser, and **this environment
has no browser-automation capability and no interactive desktop to drive a dev server + browser**, so
I could not click through a live worksheet or capture screenshots. What I was able to verify instead:

- the production build compiles the render with full type-checking (above);
- by code review, the layout uses only existing in-repo conventions (PrimeFlex `flex flex-wrap gap-3`,
  inline `flex: 1 1 22rem` / `minWidth: min(22rem, 100%)`, `w-full` + `tableLayout: fixed`, and
  per-cell `wordBreak: break-word` / `overflowWrap: anywhere`), which is the same responsive,
  non-overlapping recipe already relied on elsewhere in this file;
- mirroring needs no runtime state: both tables read/write the SAME backing row for `time`/`unit`
  (Test editable, Reference read-only), so the values cannot diverge by construction.

**Action for the reviewer / finalize step:** start the stack (`start-lims.bat`, or
`uvicorn` + `vite dev`), open a worksheet on a TRF test line bound to TST-F1F2M (template
TPL-A7-0002), and confirm: (a) the two tables sit side by side and share the window; (b) resizing
wide→narrow auto-fits then stacks them vertically with no cell clipping/overlap at a couple of
widths; (c) typing a timepoint label + unit in a Test-table row mirrors into the matching
Reference-table row while mean %/%RSD stay per-product; (d) entering the example profiles yields
f1 ≈ 5.9 / f2 = 75.9 in the `comparison` section. Capture a screenshot of the resized layout.

## Files changed

- `backend-v2/scripts/template_definitions/a7_profile_comparison_mirrored.py` (new)
- `backend-v2/scripts/template_definitions/__init__.py` (import + `*_A7M,`)
- `backend-v2/tests/calculation/test_a7_0002_mirrored_parity.py` (new)
- `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
  (gating flag, `renderMirroredProfile`, dispatch branch, `CSSProperties` import)
