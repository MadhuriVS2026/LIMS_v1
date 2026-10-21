# Implementation Plan — Opt-in "visual merge" for a worksheet table column (SET column of TPL-A2-0004)

## Goal (verbatim scope)

Add a generic, **opt-in**, **frontend-only** "visual merge" (Excel merged-cell
style) for a worksheet table COLUMN, and enable it for the **SET** column
(`set_no`) of TPL-A2-0004's **Sample Details** (group key `lipid_samples`).
When consecutive rows share the same non-empty rendered value in a merge-enabled
column, render that value ONCE in the first row of the run and leave the cells
beneath it blank. Pure DISPLAY transform: no row reorder/hide, other columns stay
editable, blanks never merge. Do NOT touch any template definition, the DB, or
the calculation engine.

## Findings from exploration (grounding)

- **Data already correct.** The backend (`backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`,
  group `lipid_samples`) auto-labels `set_no` as a **calculated** field
  (`expression: "trunc((rowno - 1) / 4, 0) + 1"`), producing 1,1,1,1,2,2,2,2 over
  8 rows. The group also carries a **hidden calculated `cidx`** field
  (`expression: "rowno - 1 - trunc((rowno - 1) / 4, 0) * 4"`, `hidden: true`) —
  the per-row compound index 0..3. Both facts are stable identifiers we can key a
  frontend rule on WITHOUT any backend/DB change. This file is read-only context;
  **no edits to backend or DB.**

- **Chosen opt-in rule (least magical, no backend change):** a frontend
  predicate `shouldMergeColumn(group, field)` returns true when **the field key is
  `set_no`** AND **the group's fields include a field whose key is `cidx`**. This
  is the "group/field shape" heuristic the task suggested: it targets exactly
  TPL-A2-0004's lipid_samples SET column and cannot match plain tables (no other
  group has both a `set_no` and a `cidx` field). It is a pure frontend rule that
  needs no definition flag, so DB row 35 / the backend module stay byte-equal.
  The rule lives in one shared util so all three render sites agree.

- **Render sites (all under `src/features/test-templates`):**
  - `components/WorksheetForm.tsx` — LIVE table. `set_no` is `kind: 'calculated'`,
    so each cell is produced by `computedCell(group, rowIndex, field)` inside the
    `tbody` `rows.map(...)` → `visibleFields.map(...)` loop. Value source:
    `computed.rows[group.key][rowIndex][field.key]`. PRIMARY surface.
  - `pages/WorksheetPreviewPage.tsx` — PREVIEW skeleton. It has **no worksheet
    instance and no computed values**; every data cell is a blank `<Placeholder/>`
    (em-dash). There is therefore nothing to merge (no non-empty repeated values).
    The generic merge util will be wired in but is a no-op here because all values
    are blank, which is the correct behavior (blanks never merge). Documented so
    the implementer does not try to synthesize fake SET values.
  - `pages/PrintWorksheetPage.tsx` — PRINT/PDF. Confirmed it **does render the data
    table** (`groups.map` → multi-row branch renders `rows = rowsOf(group.key)`
    from `computed.rows`, one `<td>` per visible field via `displayValue`). So the
    merge DOES apply here and must be wired in.

- **Shared-util precedent:** `models/groupFooter.ts` is the small shared util the
  footer work added (pure functions, shape-detection, no per-template branching).
  The new merge util follows the same style and lives beside it.

- **Build/verify:** `npm run build` (= `tsc -b && vite build`) from
  `frontend-react`. **No test runner** in package.json (do not add one). ESLint is
  not installed (`lint` script exists but is not used here). Verification =
  TypeScript build passes + DOM reasoning.

## Merge semantics (exact)

Operate per visible column, over the ordered list of rendered rows for a group:
1. Compute each row's **rendered string** for the column (same formatting the site
   already uses: `displayValue`/`computedCell` output). Treat `null`/`undefined`/
   `''`/`'—'` as EMPTY.
2. A row **starts a run** if it is the first row, OR its value is EMPTY, OR its
   value differs from the previous row's value. Otherwise it **continues** the run
   above it.
3. Render: run-start rows render the value normally (optionally with `rowSpan`);
   continuation rows render an **empty cell** (nothing). Empty values always start
   their own single-row run (so blanks never visually merge).
4. Nothing else changes: row count, ordering, other columns, and editability are
   untouched.

Two viable rendering strategies — **chosen: option A (blank continuation cells)**,
because it is the least invasive to the existing per-row `<tr>`/`<td>` loops (no
restructuring of the map to pre-group rows) and keeps every other column's cell in
its normal position/editable state. Option B (`rowSpan` on the first cell +
omitting the `<td>` entirely on continuation rows) would require emitting a
different number of `<td>`s per row and is riskier across three differently
structured tables; we therefore render a visually blank `<td>` on continuation
rows instead of a real `rowSpan`. (If the user later wants a true spanning
border/vertical-center, that is a follow-up; option A already reads as a merged
cell.)

---

# Implementation Plan

- [ ] 1. Add the shared, generic column-merge util.
      Create `columnMerge.ts` with: `shouldMergeColumn(group: GroupDef, field: FieldDef): boolean`
      — returns true only when `field.key === 'set_no'` AND `(group.fields ?? []).some(f => f.key === 'cidx')`
      (the TPL-A2-0004 lipid_samples shape; documented in a file header comment
      mirroring `groupFooter.ts`); and a pure display helper
      `isMergedContinuation(renderedValues: string[], rowIndex: number): boolean`
      — given the column's rendered strings in row order, returns true when the
      row should render BLANK (i.e. `rowIndex > 0`, the value is non-empty, and it
      equals the previous row's value). Also export a small
      `normalizeMergeValue(v: unknown): string` that maps `null`/`undefined`/`''`
      and the em-dash placeholder to `''`, else `String(v).trim()`, so all three
      sites classify "empty" identically.
      Files: `frontend-react/src/features/test-templates/models/columnMerge.ts`
      Verify: `npm run build` from `frontend-react` compiles with no new TS errors
      (the file is pure TS, imported in step 2).

- [ ] 2. Wire the merge into the LIVE form (primary surface).
      In `WorksheetForm.tsx`, inside each table group's render (the non-singleton
      branch), for every mergeable visible column precompute the column's rendered
      values in row order once per render (use the same value the cell shows: for
      `set_no` that is `computed.rows[group.key][rowIndex].set_no`, formatted via
      the existing `displayValue`). In the `tbody` `rows.map` → `visibleFields.map`
      cell render, when `shouldMergeColumn(group, field)` is true and
      `isMergedContinuation(renderedCol, rowIndex)` is true, render an empty `<td>`
      (same `cellPad`/classes, no inner content) instead of calling
      `computedCell`. For run-start rows and all non-merge columns, render exactly
      as today. Do not change editable (`renderInput`) columns' behavior.
      Files: `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
      Verify: `npm run build` passes. DOM reasoning: for lipid_samples with 8 rows
      (`set_no` = 1,1,1,1,2,2,2,2) the SET `<td>` shows "1" on row 0 and blank on
      rows 1–3, "2" on row 4 and blank on rows 5–7; all other `<td>`s (Compound
      Name, LC, Area, % Assay, inputs) render unchanged and inputs stay editable.

- [ ] 3. Wire the merge into the PRINT/PDF table.
      In `PrintWorksheetPage.tsx` multi-row branch, precompute each mergeable
      column's rendered values (via the existing `displayValue(row[f.key], f)`)
      for `rows = rowsOf(group.key)`, and in the `rows.map` → `fields.map` cell
      loop render an empty `<td className="num">` for continuation rows of a
      mergeable column (using `shouldMergeColumn` + `isMergedContinuation`),
      otherwise render `displayValue(...)` as today.
      Files: `frontend-react/src/features/test-templates/pages/PrintWorksheetPage.tsx`
      Verify: `npm run build` passes. DOM reasoning: a printed TPL-A2-0004
      worksheet shows the SET column value once per 4-row block, blank beneath;
      every other template's print table is unaffected because `shouldMergeColumn`
      only matches the lipid_samples/`set_no`+`cidx` shape.

- [ ] 4. Wire the merge into the PREVIEW skeleton (consistency, expected no-op).
      In `WorksheetPreviewPage.tsx` table branch, call `shouldMergeColumn`/
      `isMergedContinuation` in the same cell loop for parity. Because the preview
      has no computed values (every cell is a blank `<Placeholder/>`), all values
      normalize to empty and NO merge occurs — the rule's "blanks never merge"
      branch makes this a safe no-op. Wiring it here keeps the three sites using
      one code path and future-proofs the page if it ever gains sample values.
      Files: `frontend-react/src/features/test-templates/pages/WorksheetPreviewPage.tsx`
      Verify: `npm run build` passes. DOM reasoning: preview renders identically to
      today (all em-dash placeholders, no cell blanked), confirming no regression.

- [ ] 5. Confirm a plain table is unaffected and the whole app builds.
      No code change. Reason about at least one plain-table template (e.g. the
      `standard` group "Standard Details", or a dissolution timepoints table):
      none has a field named both `set_no` and a sibling `cidx`, so
      `shouldMergeColumn` returns false for every column and rendering is byte-for
      -byte identical to today.
      Files: none (verification step).
      Verify: `npm run build` from `frontend-react` completes successfully
      (`tsc -b && vite build`), confirming all four touched files typecheck and
      the production bundle builds. No test runner exists, so verification is the
      build plus the DOM reasoning recorded in steps 2–4.

---

## Backend/DB tradeoff note (for the user)

A `mergeEqual`-style flag on the `set_no` field definition would be the "cleanest"
declarative approach, but it would require editing the backend module
`backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` and DB
row 35, which is **OUT OF SCOPE** for this frontend-only task. The plan therefore
uses the frontend shape-heuristic (`set_no` + sibling `cidx`) which needs **no**
backend/DB change and does not merge columns in other templates. If the user later
prefers the declarative flag, the implementer must PAUSE (via `send_message`,
severity "warning") and get approval before touching backend/DB — never edit them
unilaterally.

## Assumptions

- "Sample Details" in the task maps to the `lipid_samples` group (its label in the
  definition is the per-SET sample block; the group is the only one with
  `set_no`). If the deployed DB labels it differently, the rule still matches by
  field shape, not by group label.
- Visual merge = blank continuation cells (option A). A true `rowSpan` with a
  centered value is a possible later enhancement; blank-beneath already reads as a
  merged cell and is the safest across the three differently-structured tables.
