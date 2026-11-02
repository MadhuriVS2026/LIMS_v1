# Implementation notes — TPL-A7-0003 "Dissolution F1-F2-calculations"

First iteration (no `review.json` present). Implemented per `plan.md`, including
the §7 f1/f2 recommendation (wired).

## What changed (source, committed)

1. **New seed module** —
   `backend-v2/scripts/template_definitions/a7_f1f2_calculations.py`
   - `TPL-A7-0003`, archetype `A7`, `TST-F1F2CALC`, "Dissolution F1-F2-calculations",
     Quantitative, `result_unit=None`, `resultRef="comparison.f2"`.
   - FIVE groups: `test_product` (singleton, 6 inputs), `reference_product`
     (singleton, same 6 inputs), `test_timepoints` (table), `reference_timepoints`
     (table), `comparison` (singleton, f1/f2).
   - Four distinct data groups (no shared-row reuse of TPL-A7-0001). Header fields
     are `input` (not `context`) so both blocks are independently editable;
     `definition["context"]` is empty.
   - Six header fields: Product Name (text), Batch No. (text), Date of Analysis
     (date), Media (text), RPM (number), Volume (number, mL).
   - Timepoint tables: `time` (text, row label via `labelFrom`), `unit` (text,
     default "Hr"), `mean` (number %), `rsd` (number %). `rows: min 1 / max 20 /
     default 6`.
   - f1/f2 built from the two tables by ROW INDEX using the proven A6B
     cross-table pattern: `test_timepoints` carries calculated columns
     `ref_mean = reference_timepoints.mean[rowno - 1]`, then `abs_diff`,
     `sq_diff`, `ref_in_scope` (all blank-guarded). The `comparison` singleton
     sums those columns and computes f1 = Σ|R−T|/ΣR×100 and
     f2 = 50·log10(100/√(1 + Σ(R−T)²/n)), both rounded to 1 dp. `n_points` is the
     MIN of the two row counts so a length mismatch cannot overrun the shorter
     table. Two advisory criteria (f2 ≥ 50, f1 ≤ 15).

2. **Registration** — `backend-v2/scripts/template_definitions/__init__.py`
   - Added `from ... a7_f1f2_calculations import TEMPLATES as _A7C` next to the
     existing A7 import, and spliced `*_A7C,` into `SEED_TEMPLATES` after `*_A7,`.

3. **Frontend** —
   `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
   - Added `allowSideBySideHeaders = template_code === 'TPL-A7-0003'` beside the
     existing `allowClearColumn` / `allowCumulativeVertical` flags.
   - Extracted the inline singleton field-grid into `renderSingletonCard(group)`
     (byte-identical markup) and had the generic non-chart singleton branch call
     it, so every other template is unchanged.
   - Added a scoped branch at the top of `groups.map`: on `test_product` render
     both product headers in one `flex flex-wrap gap-3` wrapper, each child
     `style={{ flex: '1 1 22rem', minWidth: 'min(22rem, 100%)' }}`, reusing
     `renderSingletonCard`; return `null` for `reference_product` so it is not
     drawn twice. Sections 3/4 and the comparison singleton fall through to the
     generic renderer unchanged.

4. **Backend test** —
   `backend-v2/tests/calculation/test_a7_0003_f1f2_calculations.py`
   - Structure assertions (five groups/kinds, the twelve header input fields and
     their types, `resultRef`) and hand-derived parity for the plan §9 example
     profiles (R = 9,23,41,58,89; T = 7,21,39,56,84 → f1 = 5.9, f2 = 75.9), plus
     the row-indexed cross-table `ref_mean`/`abs_diff` and an empty-sheet check
     that f2 stays blank (EMPTY).

## Verification (commands + results)

Backend (cwd `backend-v2`):

- `python -m scripts.seed_test_templates --validate-only` → exit 0,
  `ok   TPL-A7-0003 [A7] 5 groups, 20 inputs, 0 area fields, 11 calculated, 2 criteria`
  and "All definitions valid."
- lims.db was ABSENT in this fresh worktree — nothing to back up.
- `python -m scripts.seed_test_templates` → `add  TPL-A7-0003 [A7] Dissolution
  F1-F2-calculations -> TST-F1F2CALC` and `+ Test Master: TST-F1F2CALC`. (Fresh
  DB, so all 33 added; others would skip on a populated DB.)
- Re-ran the seeder → `skip TPL-A7-0003 — already present (v1, Active)`
  (idempotent).
- `python -m pytest tests/calculation/test_a7_0003_f1f2_calculations.py
  tests/calculation/test_seeded_template_parity.py -q` → **3 failed, 289 passed**.
  The ONLY failures are the three `TestA6BDissolutionWithReplacement` parity
  tests (`test_unit1_release_carryover`, `test_per_timepoint_summary`,
  `test_amount_remaining`) — the PRE-EXISTING, known-failing A6B tests on this
  branch (groups `release`/`amount`, unrelated to A7). The new A7-0003 test and
  every catalogue-wide invariant covering TPL-A7-0003 passed.

Frontend (cwd `frontend-react`):

- `npm ci` (node_modules was absent) → 123 packages installed.
- `npm run build` (`tsc -b && vite build`) → success, no TypeScript errors.
- Lint: the `lint` script is `eslint .`, but **eslint is NOT a declared/installed
  dependency** (absent from package.json and from node_modules after `npm ci`).
  Per instructions I did not install an unpinned tool; `npx eslint` only tried to
  fetch it from the network (and timed out). The `tsc -b` type-check in the build
  is the available static gate and it passed.

## Runtime layout check — NOT performed here

The side-by-side responsive layout (share width on wide screens; wrap/stack on
narrow with no overlap/clipping) is NOT verified by this agent — a true check
needs a running browser, which is not drivable in this environment. The code
follows the exact responsive pattern the brief/plan specify (PrimeFlex
`flex flex-wrap gap-3` + `flex: 1 1 22rem` / `minWidth: min(22rem, 100%)`), but a
reviewer/finalizer must do the browser check (plan §10 item 6).

## Pre-existing repo issue encountered (NOT my change, NOT committed)

The worktree's committed `__init__.py` imports
`scripts.template_definitions.a9_sodium_metabisulfite`, but that module file was
never committed to any ref (it exists only as an UNTRACKED file in the main repo
and the lenacapavir worktree). Without it the seeder cannot even import, so to run
verification I copied the untracked module into this worktree. It is untracked and
was NOT committed — it is outside this task's scope. Flagging it so the
reviewer/finalizer is aware the shared branch has an imported-but-uncommitted
dependency.

## Not committed

`lims.db` and any backups (gitignored), `node_modules/`, `dist/`, and the copied
`a9_sodium_metabisulfite.py`. Only the four source files above are committed.
