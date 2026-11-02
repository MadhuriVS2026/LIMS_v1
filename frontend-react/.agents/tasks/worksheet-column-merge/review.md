# Opt-in visual column merge for the TPL-A2-0004 SET column

A frontend-only "visual merge" (Excel merged-cell style) was added so that consecutive rows sharing the same non-empty value in a merge-enabled column render the value once at the top of the run with blank cells beneath. It is enabled for the SET column (`set_no`) of TPL-A2-0004's Sample Details (`lipid_samples`) via a shape heuristic, keeps the stored per-row value and all other columns untouched, and is wired identically into the live form, the print page, and the preview page. No template definition, DB row, or calculation-engine file was changed — the backend already auto-labels `set_no` as 1,1,1,1,2,2,2,2 and even documents that the frontend should visually merge it. Watch for: nothing blocking — the heuristic is uniquely scoped and every render site classifies "empty" through one shared helper (confirmed).

**Verdict**: APPROVED

## High-level view

The merge is a pure display transform implemented in one shared util (`columnMerge.ts`) and consumed at all three render sites. `shouldMergeColumn` opts a column in only when its key is `set_no` and the same group carries a sibling `cidx` field; that pair exists in exactly one template definition and nowhere else in the frontend, so no plain table can accidentally merge.

Each site precomputes the column's rendered strings in row order and blanks a cell when `isMergedContinuation` reports the value equals the previous non-empty value. Row count, ordering, other columns, and editable inputs are all left in place; a continuation row still emits a `<td>`, so column alignment and the per-`<tr>` cell count are unchanged.

Empty values never merge: `normalizeMergeValue` folds `null`/`undefined`/`''` and the em-dash placeholder to `''`, and an empty value always starts its own single-row run. The preview page has no computed values so every cell normalizes to empty and the wiring is a confirmed no-op, kept only for parity. The build was recorded green (tsc + vite, exit 0, zero TS errors).

<details>
<summary>Issues (0)</summary>

No blocking or non-blocking findings.

</details>

<details>
<summary>Details</summary>

## Heuristic scope — uniquely targets lipid_samples (point 3)

`shouldMergeColumn(group, field)` returns true only when `field.key === 'set_no'` and `(group.fields ?? []).some(f => f.key === 'cidx')`. The backend definition confirms both fields live in the `lipid_samples` group: `set_no` is a calculated SET label and `cidx` is a hidden calculated compound index 0..3. A grep of every template definition shows `set_no` appears in exactly one module (`a2_bupivacaine_lipid_ratio.py`), and `set_no`/`cidx` appear nowhere else in the frontend source. No other group can satisfy both conditions, so the rule is genuinely opt-in and cannot merge a plain table (confirmed).

Keying on `group.fields` rather than visible fields is correct here: `cidx` is `hidden: true`, so it would be absent from a visible-field list, but it is present in the group definition — the heuristic still fires (confirmed).

## Merge semantics and blank handling (points 1 and 2)

`isMergedContinuation(renderedValues, rowIndex)` returns true only when `rowIndex > 0`, the current normalized value is non-empty, and it equals the previous normalized value. For the 8-row A2-0004 default the `set_no` column renders `["1","1","1","1","2","2","2","2"]`, so row 0 shows "1", rows 1–3 blank, row 4 shows "2", rows 5–7 blank — two merged SET blocks, matching the task's expectation exactly (confirmed).

Blanks never merge: `normalizeMergeValue` maps `null`/`undefined`/`''` and the em-dash placeholder to `''`, and a current value of `''` returns false, so an empty cell always starts its own single-row run (confirmed). The two `displayValue` implementations differ in their empty sentinel — WorksheetForm returns `'—'`, PrintWorksheetPage returns `''` — but `normalizeMergeValue` folds both to `''`, so the two sites classify "empty" identically (confirmed).

## Render-site consistency (point 4)

All three sites import the same util and follow the same pattern: precompute `mergeColumnValues[field.key]` once per group via the site's own `displayValue`, then blank the `<td>` when `isMergedContinuation` is true, otherwise render as before.

- `WorksheetForm.tsx` (live): precomputes from `computed.rows[group.key][rowIndex][field.key]`; continuation rows render an empty `<td className={cellPad}>`. The calculated/editable branch is preserved for run-start and non-merge columns, so inputs stay editable (confirmed).
- `PrintWorksheetPage.tsx` (print): precomputes from `rowsOf(group)` via `displayValue(row[f.key], f)`; continuation rows render an empty `<td className="num">`, preserving column class and alignment (confirmed).
- `WorksheetPreviewPage.tsx` (preview): wired for parity. The preview has no worksheet instance, so every cell is a blank placeholder; the merge input is an array of normalized `EMPTY` values, which makes `isMergedContinuation` always false. Confirmed no-op — the page renders identically to before (confirmed).

A continuation cell still emits a `<td>` (empty) rather than omitting it or using a real `rowSpan`, so every `<tr>` keeps the same number of cells and columns stay aligned. The stored per-row value is never mutated; this is display-only (confirmed).

## Build evidence (point 5)

The implementer recorded `npm run build` (`tsc -b && vite build`) exiting 0 with "335 modules transformed", zero TypeScript errors, and only the pre-existing Vite chunk-size warning. Evidence is specific and present; per instructions the suites were not re-run. The new util is pure TS imported by all three sites, and `displayValue` and `EMPTY` were confirmed in scope at each consuming site, so the type-check claim is consistent with the code (confirmed).

## Scope (point 6)

`git show --stat d73918a` lists only the new `columnMerge.ts`, the three tsx render sites, and the two task-doc files. No `backend-v2` source, DB, or calculation-engine file is in the commit; `git status` shows only the task's own files. The backend module `a2_bupivacaine_lipid_ratio.py` and DB row 35 remain byte-equal. Scope respected, no stray application files (confirmed).

</details>

<details>
<summary>File map</summary>

- `models/columnMerge.ts` (new) — `shouldMergeColumn` shape heuristic, `normalizeMergeValue`, `isMergedContinuation`.
- `components/WorksheetForm.tsx` — precompute mergeable column values; blank continuation cells in the live table.
- `pages/PrintWorksheetPage.tsx` — same precompute/blank for the print table.
- `pages/WorksheetPreviewPage.tsx` — parity wiring; no-op because preview cells are all placeholders.
- `.agents/tasks/worksheet-column-merge/plan.md`, `verification.md` — task tracking docs.

Full diff: `git diff HEAD~1` from `frontend-react` (commit `d73918a`).

</details>
