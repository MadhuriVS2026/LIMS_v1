# Design + Implementation Plan — TPL-A7-0002 "Dissolution Profile Comparison (f1 / f2) — Mirrored"

Task: add a NEW F1/F2 dissolution profile-comparison template whose two products' timepoints
render as two side-by-side mirrored tables (Reference | Test), responsive and non-overlapping,
while reusing the proven A7 (TPL-A7-0001) f1/f2 arithmetic and validity criteria verbatim.

All edits happen in the worktree: `d:\RD-instance\GIT\.worktrees\f1f2-mirror-template`.
Do NOT modify or overwrite `TPL-A7-0001` or its module `a7_profile_comparison.py`.

---

## 1. Chosen data-model approach (and why) — Requirement 2

### Decision: Approach B — ONE backing `sequence` group, rendered as TWO side-by-side tables in the frontend.

The new module keeps A7's single `timepoints` **sequence** group (one row per timepoint carrying
BOTH products' means/RSD), and the only change is a frontend custom render gated on
`template_code === 'TPL-A7-0002'` + `group.key === 'timepoints'` that paints that one group as two
visually separate tables side by side: a Reference table (timepoint label, unit, `ref_mean`,
`ref_rsd`) and a Test table (timepoint label, unit, `test_mean`, `test_rsd`). Both tables are two
views of the *same* row array.

### Why Approach B and not Approach A (two parallel `ref_timepoints` / `test_timepoints` groups)

- **The f1/f2 + validity arithmetic stays byte-for-byte identical.** A7's entire comparison math
  (`abs_diff`, `sq_diff`, `ref_in_scope`, `*_over_85`, `worst_rsd`, `has_rsd`, `rsd_limit`,
  `rsd_breach`, and the whole `comparison` singleton: `n_points`, `sum_abs_diff`, `sum_ref`,
  `sum_sq_diff`, `mean_sq_diff`, `f1`, `f2`, `points_over_85`, `rsd_breaches`) is expressed within a
  single row and aggregates over a single group. Approach A would require re-aligning two separate
  groups row-by-row by index inside expressions — the engine sees other groups only as whole columns,
  not row-aligned (confirmed by the `mirrorFrom` comment in `WorksheetForm.tsx`), so `ref_mean` and
  `test_mean` could no longer sit in the same row and `abs(ref_mean - test_mean)` would break. That
  is a rewrite of the exact arithmetic we were told to reuse verbatim. Rejected.

- **"Same timepoints for both products" stays structurally guaranteed.** A7's docstring makes this
  explicit: requirement 2 is enforced *because one row carries both products' means*, so there is no
  way to compare a 4 h reference value against a 6 h test value. Approach B inherits that guarantee
  for free — there is literally one `time`/unit per row. Approach A would reintroduce the very drift
  the requirement forbids and would need an extra cross-group equality criterion to compensate.

- **`prior.`-based RSD-limit logic survives untouched.** `rsd_limit` uses
  `if(has_rsd > 0 and sum(prior.has_rsd) = 0, 20, 10)` — `prior.` references earlier rows of the SAME
  sequence. One sequence => `prior.` keeps meaning "earlier timepoints", so the 20%-at-first /
  10%-thereafter rule is preserved exactly. Splitting into two groups would make `prior.` ambiguous
  per product and the worst-of-both `worst_rsd` could no longer be computed in-row. Rejected.

- **Mirroring is inherent, not bolted on.** With one backing row, the timepoint label + unit are a
  single shared cell; both tables render the same value, so the two profiles *cannot* drift onto
  different time axes — it is impossible by construction, which is strictly stronger than copying
  values between two groups. (See §3 for how editing is wired so the analyst types the label/unit in
  the Test table and the Reference table shows the same shared value.)

### Consequence for the "unit" requirement

A7 today carries the time **unit** once, as the `time_unit` context field ("Hr") for the whole
profile, and `time` is a free-text label ("1 Hr", "24 Hr"). The new template must let label AND unit
live per-timepoint-row and mirror together. So the new module adds a per-row `unit` input field to
the `timepoints` group (default sourced from the `time_unit` context default "Hr"). Because it is one
shared row, the unit is automatically identical for both products — mirroring of the unit is
inherent, exactly like the label. `time_unit` context stays as the profile-level default/label.

---

## 2. Backend module structure — `a7_profile_comparison_mirrored.py`

New file:
`d:\RD-instance\GIT\.worktrees\f1f2-mirror-template\backend-v2\scripts\template_definitions\a7_profile_comparison_mirrored.py`

It reuses A7's arithmetic verbatim. To guarantee "verbatim" and avoid drift, **import the building
blocks from the A7 module** rather than retyping the expressions:

- A7's `_timepoint_fields()`, `_MAX_TIMEPOINTS`, and the `comparison` group fields are module-level in
  `a7_profile_comparison.py`. Prefer importing `a7_profile_comparison` and deep-copying its pieces so
  the f1/f2 expressions are literally the same strings. Concretely:

  ```python
  import copy
  from scripts.template_definitions import a7_profile_comparison as a7
  from scripts.template_definitions._common import SeedTemplate, context_header
  ```

- Build `_timepoint_fields_mirrored()`:
  - Start from `copy.deepcopy(a7._timepoint_fields())` (all calculated fields —
    `abs_diff`, `sq_diff`, `ref_in_scope`, `ref_over_85`, `test_over_85`, `worst_rsd`, `has_rsd`,
    `rsd_limit`, `rsd_breach` — and the inputs `time`, `included`, `ref_mean`, `ref_rsd`,
    `test_mean`, `test_rsd` carry over unchanged).
  - Insert ONE new input field `unit` (kind `input`, type `text`, label "Unit", default `"Hr"`),
    positioned right after `time` so the two mirror-together inputs are adjacent. The unit is display
    metadata only; it is NOT referenced by any expression, so no calculated field changes.

- Build `_TIMEPOINTS_GROUP_MIRRORED` as a deepcopy of `a7._TIMEPOINTS_GROUP` with:
  - same `key: "timepoints"`, same `kind: "sequence"`, same `rows` spec
    (`min:1, max:_MAX_TIMEPOINTS(=20), default:9, labelFrom:"time"`),
  - `fields` replaced by `_timepoint_fields_mirrored()`,
  - label updated to e.g. "Mean % Dissolved by Time Point (Reference | Test)".

- Reuse `a7._COMPARISON_GROUP` by deepcopy — it is unchanged (it aggregates over `timepoints.*`).

- Build `A7M_DEFINITION` as a deepcopy of `a7.A7_DEFINITION` with:
  - `resultRef` stays `"comparison.f2"` (unchanged),
  - `context` = `copy.deepcopy(a7.A7_DEFINITION["context"])` (same context header incl.
    `reference_product`, `reference_batch`, `reference_trf`, `test_trf`, `time_unit` (default "Hr"),
    `media`, etc.),
  - `groups` = `[_TIMEPOINTS_GROUP_MIRRORED, <deepcopy of comparison group>]`,
  - `criteria` = `copy.deepcopy(a7.A7_DEFINITION["criteria"])` — the five criteria
    (`min_timepoints` NLT 3 blocking; `single_point_over_85` NMT 1 blocking;
    `profile_precision` RSD-breaches None blocking; `f2_similarity` NLT 50 advisory;
    `f1_difference` NMT 15 advisory) are reused verbatim.

- Define the SeedTemplate:

  ```python
  A7M = SeedTemplate(
      code="TPL-A7-0002",
      name="Dissolution Profile Comparison (f1 / f2) — Mirrored",
      archetype="A7",
      result_unit=None,
      test_code="TST-F1F2M",
      test_name="Dissolution Profile Comparison (f1 / f2) — Mirrored",
      test_type="Quantitative",
      definition=A7M_DEFINITION,
  )
  TEMPLATES = [A7M]
  ```

  Note: the step prompt says `name` and `test_name` are both
  "Dissolution Profile Comparison (f1 / f2) — Mirrored". Use that exact string for both.

### `__init__.py` registration (one line + one import)

In `d:\RD-instance\GIT\.worktrees\f1f2-mirror-template\backend-v2\scripts\template_definitions\__init__.py`:

- Add import next to the existing A7 import:
  ```python
  from scripts.template_definitions.a7_profile_comparison_mirrored import TEMPLATES as _A7M
  ```
- Add `*_A7M,` into the `SEED_TEMPLATES` list immediately after `*_A7,`.

### Catalogue-invariant impact (important)

`tests/calculation/test_seeded_template_parity.py::test_template_codes_are_unique` and the
"every template parses/runs empty", "resolvable reportable result", "no unfillable context",
"area fields discoverable" parametrized tests will automatically pick up `TPL-A7-0002`. Because the
new definition is a structural clone of A7 (which already passes all of these), it must pass them too.
`test_every_archetype_in_scope_is_seeded` asserts the SET of archetypes — adding another "A7" entry
does NOT change the set, so that invariant is unaffected. No edit to that test is required.

---

## 3. Frontend custom render, mirroring, and responsive side-by-side layout

File: `d:\RD-instance\GIT\.worktrees\f1f2-mirror-template\frontend-react\src\features\test-templates\components\WorksheetForm.tsx`

### Gating (mirror the existing TPL-A6A-0005 pattern)

- Add a flag next to `allowCumulativeVertical`:
  ```ts
  const allowMirroredProfile = detail.worksheet.template_code === 'TPL-A7-0002';
  ```
- In the `groups.map(...)` dispatch (where `allowCumulativeVertical && group.key === 'timepoints_release'`
  returns `renderCumulativeVertical(group)`), add a sibling branch BEFORE the generic renderer:
  ```ts
  if (allowMirroredProfile && group.key === 'timepoints') {
    return renderMirroredProfile(group);
  }
  ```
  The `comparison` singleton and the Context block fall through to the existing generic renderers
  unchanged (f1/f2 show exactly as they do for A7).

### `renderMirroredProfile(group)` structure

Build it as a new function alongside `renderCumulativeVertical`, reusing the SHARED helpers exactly
as that function does — `renderInput`, `computedCell`, `renderGroupToolbar`, `addRow`, `removeRow`,
`setCell`, `isGroupEditing`, `editable`. One backing row array: `const rows = values[group.key] ?? []`.

- Resolve field defs by key once: `time`, `unit`, `ref_mean`, `ref_rsd`, `test_mean`, `test_rsd`
  (via `(group.fields ?? []).find(f => f.key === ...)`).
- Render a `<Card>` with the group label + `renderGroupToolbar(group)` and the Add/Remove-timepoint
  controls gated on `canAddRows && isGroupEditing(group.key)` (same gating as renderCumulativeVertical).
- Inside, render TWO tables inside a responsive flex row (see layout below). Each table has a header
  row and one body row PER backing-row index `rowIndex`, both tables iterating the SAME `rows`:
  - **Reference table** columns: `Time Point` (shared `time` input), `Unit` (shared `unit` input),
    `Reference mean % (R(t))` (`ref_mean` input), `Reference %RSD` (`ref_rsd` input).
  - **Test table** columns: `Time Point` (shared `time` input), `Unit` (shared `unit` input),
    `Test mean % (T(t))` (`test_mean` input), `Test %RSD` (`test_rsd` input).
  - The `included` input and all calculated per-row fields (`abs_diff`, etc.) remain NON-rendered in
    these two tables (A7 shows them in its generic table; here keep them out of the mirrored view to
    stay readable). They still compute and store because `seedValues`/the evaluator iterate the full
    definition — identical to how `hidden`/omitted fields behave. Provide `included` either as a small
    toggle column on ONE of the tables (Reference) OR as a compact per-row control row; default value
    `1` is seeded so a row counts unless the analyst changes it. (Keep `included` visible so the
    ">85% exclusion" workflow A7 documents is still reachable; put it on the Reference table only, since
    it is shared.)

### Mirroring (label + unit only), typed in the Test table

Because there is ONE backing row, the `time` and `unit` cells are a single shared value. To satisfy
"analyst enters label+unit in the TEST table and they auto-populate the REFERENCE table":

- Make the `time` and `unit` inputs in the **Test** table the editable source (`renderInput` with the
  group in edit mode writes via `setCell(group.key, rowIndex, 'time'|'unit', value)`).
- In the **Reference** table, render the SAME `time`/`unit` as READ-ONLY cells (display the shared
  value via the row value / a disabled input), so they visibly reflect whatever was typed on the Test
  side and can never diverge.
- This needs NO new state and NO `mirrorFrom` wiring, because both tables read/write the same backing
  cell — the mirror is inherent to the single-row model (exactly the "single shared backing row" case
  the requirement calls out). `ref_mean`, `ref_rsd`, `test_mean`, `test_rsd` remain independently
  editable per product in their own table.

  (Optional simplification if the implementer prefers a declarative approach: NOT needed here. The
  generic `mirrorFrom` mechanism copies between DIFFERENT groups/columns by row index; with a single
  shared column there is nothing to copy. Do not use `mirrorFrom` for this template.)

### Responsive, non-overlapping side-by-side layout — Requirement 4 (verify visually)

Use the existing PrimeFlex/inline-style conventions already in this file (no new UI libraries):

- Outer wrapper: a flex row that wraps and auto-fits the window:
  ```tsx
  <div className="flex flex-wrap gap-3">
    <div style={{ flex: '1 1 22rem', minWidth: 'min(22rem, 100%)' }}> {/* Reference */} </div>
    <div style={{ flex: '1 1 22rem', minWidth: 'min(22rem, 100%)' }}> {/* Test */} </div>
  </div>
  ```
  `flex: 1 1 22rem` makes both tables share width and grow to fill; `flex-wrap` + `minWidth: min(22rem,100%)`
  makes them stack vertically on narrow windows instead of overflowing — this is the "auto-fit the
  window width / responsive" behaviour.
- Each table: `className="w-full text-sm"` with `style={{ borderCollapse:'collapse', tableLayout:'fixed' }}`
  (same as the existing tables). `tableLayout: fixed` + `w-full` makes columns divide the available
  width evenly regardless of content width.
- Prevent overlap/clipping: every data cell span uses `style={{ wordBreak:'break-word', overflowWrap:'anywhere' }}`
  and inputs use `className="w-full"` (as `renderInput` already does), so long values wrap inside the
  cell instead of spilling. Header cells use `whiteSpace:'normal'` so long headers wrap too. Follow the
  `cellPad` pattern (`p-1`/`p-2`) used by the generic renderer for compactness.
- Keep column count low (4 per table) so even on mid-width windows the fixed layout never crushes a
  column — this is why `included`/calculated columns are kept out of the mirrored view.

### Models/types

`FieldDef.mirrorFrom`/`labelFrom` already exist in
`frontend-react\src\features\test-templates\models\testTemplate.types.ts`. The new `unit` input is a
plain text field — no type change needed. No new type additions required.

---

## 4. Verification commands

Run from the worktree. Backend commands run from
`d:\RD-instance\GIT\.worktrees\f1f2-mirror-template\backend-v2`; frontend from
`d:\RD-instance\GIT\.worktrees\f1f2-mirror-template\frontend-react`.

### Backend

1. **Validate-only (parse + dry-run every definition, writes nothing):**
   ```
   python -m scripts.seed_test_templates --validate-only
   ```
   Expect: a line `ok   TPL-A7-0002 [A7] <groups/inputs/calculated/criteria>` and
   "All definitions valid. --validate-only, so nothing was written." (exit 0). This is the gate before
   any DB write — do it first.

2. **Backup lims.db BEFORE seeding (backup convention, see §5):**
   ```powershell
   Copy-Item lims.db "lims.db.bak-f1f2mirror-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
   ```
   (Run only if `lims.db` exists; it is gitignored.) Confirm the `.bak-f1f2mirror-*` file now exists.

3. **Seed (additive, idempotent):**
   ```
   python -m scripts.seed_test_templates
   ```
   Expect: `add  TPL-A7-0002 [A7] Dissolution Profile Comparison (f1 / f2) — Mirrored -> TST-F1F2M`
   and `+ Test Master: TST-F1F2M — ...`, with all other templates reported `skip ... already present`.
   Re-running must report `skip TPL-A7-0002 — already present` (idempotency check).

4. **Catalogue-wide parity invariants + A7 parity (pytest):**
   ```
   python -m pytest tests/calculation/test_seeded_template_parity.py -q
   ```
   Expect: all pass, including the parametrized invariants now covering `TPL-A7-0002`.

5. **New parity test for TPL-A7-0002** (add it — see the FEAT steps): create
   `tests/calculation/test_a7_0002_mirrored_parity.py` modelled on
   `test_a6a_0005_leuprolide_parity.py`: import `A7M_DEFINITION` directly, feed the A7 sheet's own
   5-timepoint example (ref means 9,23,41,58,89; test means 7,21,39,56,84 — from the A7 docstring's
   hand-typed comparison block) through `WorksheetEvaluator`, and assert the SAME f1/f2 the A7 math
   produces (f1 ≈ 5.9 per the docstring; assert `comparison.f1`/`comparison.f2` equal the values A7
   produces for the identical inputs — derive them, do not copy a run). Also assert the `unit` field
   does not perturb any computed value (parity with A7 on identical mean/RSD inputs). Run:
   ```
   python -m pytest tests/calculation/test_a7_0002_mirrored_parity.py -q
   ```
   Expect: all pass. Optionally run the whole calculation suite: `python -m pytest tests/calculation -q`.

### Frontend

6. **Type-check + build:**
   ```
   npm run build
   ```
   (`tsc -b && vite build`.) Expect: no TS errors, build succeeds.

7. **Lint:**
   ```
   npm run lint
   ```
   Expect: no new eslint errors in `WorksheetForm.tsx`.

8. **Runtime browser check (MANDATORY — layout + mirroring cannot be verified by reading code):**
   Start backend + frontend (e.g. the repo's `start-lims.bat`, or `uvicorn`/`vite dev` per the dev
   setup). In the browser, open/create a worksheet on a TRF test line bound to test `TST-F1F2M`
   (template `TPL-A7-0002`) and verify:
   - The two tables (Reference | Test) render SIDE BY SIDE and share the window width.
   - Typing a timepoint LABEL and UNIT into a row of the TEST table immediately shows the SAME label
     and unit in the corresponding REFERENCE row; mean %/%RSD remain independently editable per table.
   - Resize the window from wide to narrow: tables auto-fit, then stack vertically on narrow widths;
     at every width cell content WRAPS and is never clipped or overlapping.
   - Entering the §4.5 example profiles yields the same f1/f2 in the `comparison` section as A7.
   Capture a note/screenshot of the resized layout as the visual evidence.

---

## 5. lims.db backup convention

Before ANY seeding write to the database, make a timestamped copy in `backend-v2\`:

```
lims.db.bak-f1f2mirror-<yyyymmdd-HHMMSS>
```

PowerShell (run in `...\worktrees\f1f2-mirror-template\backend-v2`):
```powershell
Copy-Item lims.db "lims.db.bak-f1f2mirror-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

This matches the existing convention in the repo (`lims.db.bak-a2*-<timestamp>` files) and the worklog
note that a timestamped `lims.db.bak-*` is made before each DB change. `lims.db` and its backups are
gitignored — they are never committed; only source (the new seed module, the `__init__.py` line, the
frontend render, and the new parity test) is committed.

---

## 6. Gaps / assumptions

- **`included` placement:** assumed shared and shown on the Reference table only (it is one shared
  row). If the lab wants it per-product it would change the data model — out of scope; the single-row
  model is what keeps the arithmetic intact, so `included` stays shared.
- **f1/f2 expected values in the new parity test:** derived from A7's documented example (f1 ≈ 5.9).
  The implementer must compute the exact float the engine returns for the identical inputs and pin it,
  not copy a run — same discipline as the existing parity tests.
- **Rounding:** inherited from A7 (f1/f2 rounded to 1 dp). No change.
- **Runtime check environment:** assumes the standard dev stack starts cleanly; if a seeded
  `TST-F1F2M` TRF line is not readily available, create a TRF/test line selecting the new test, since
  the template is seeded Active and immediately selectable.
```