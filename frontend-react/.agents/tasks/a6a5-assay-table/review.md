# Display-only % Assay / C1 / C2 columns for TPL-A6A-0005 timepoints

This change extends the existing TPL-A6A-0005 vertical "Cumulative % Release" renderer in `WorksheetForm.tsx` with three read-only columns per timepoint: `% Assay` (from `jassay_N`), `C1` (from `kfrac_N`), and `C2` (a display-only `unit_N − jassay_N` carry-over). Rather than a standalone second table, the three columns were appended onto the already-approved two-column "Sample Area → Cumulative %Release" table, producing one five-column per-timepoint table plus the unchanged Mean/Min/Max/%RSD footer. All three new columns read straight from `computed.rows` and format through the existing 2dp `displayValue` path — no assay math is recomputed in the UI except the single `C2` subtraction, which is blank-guarded. The change is frontend-only and strictly gated to `template_code === 'TPL-A6A-0005'` and `group.key === 'timepoints_release'`.

**Watch for:** the delegation brief for this task asked for a *separate* 3-column `% Assay` table beneath the existing one, but the implementation *merged* the three columns into the existing table (per a mid-task clarification recorded in `verification.md`) — the layout decision should be confirmed against the latest intent, though the columns, sources, and math all match the brief (confirmed). The working tree also carries unrelated, pre-existing changes (`__init__.py`, `TRFListPage.tsx`, another task's verification doc, worklog) that are out of scope for this review and were not introduced by this task (confirmed).

**Verdict**: APPROVED

## High-level view

The new columns live inside `renderCumulativeVertical`, reached only through the existing short-circuit `if (allowCumulativeVertical && group.key === 'timepoints_release')` at the top of the groups loop. No other template and no other group can reach this code, and no shared helper was modified, so output everywhere else is unchanged (confirmed).

`% Assay` and `C1` are rendered directly from `computed.rows[group.key][rowIndex][jassay_N]` and `[kfrac_N]` — the hidden computed values the engine already produced — and are never recalculated in the UI. They are formatted to 2dp by `assay2dp`, a thin wrapper over the existing `displayValue` using a synthetic 2dp `FieldDef`, so blanks still fall through to the em-dash the rest of the form uses (confirmed).

`C2` is the only UI-side arithmetic: `unit_N − jassay_N`, and only when both operands are present numbers; otherwise it is `null` and renders blank. That matches the brief's blank-guard and the no-prior-carry-over first timepoint reading blank (confirmed).

The pre-existing Sample Area input, the Cumulative %Release computed cell, the Mean/Min/Max/%RSD footer, and the Add/Remove Timepoint controls are untouched by this change — the new columns are purely additive table cells (confirmed).

Build evidence in `verification.md` records `npm run build` (`tsc -b && vite build`) passing with zero TypeScript errors; the ESLint-not-installed gap is pre-existing and documented, not a regression.

<details>
<summary>Issues (2)</summary>

1. **Separate vs merged layout** — the delegation brief asked for a *separate* `% Assay` table beneath the existing one; the implementation merged the three columns into the existing table per a recorded mid-task clarification. Non-blocking; confirm the merged layout is the intended final form before shipping.
2. **Unrelated working-tree changes bundled** — `backend-v2/scripts/template_definitions/__init__.py`, `frontend-react/src/features/trf/pages/TRFListPage.tsx`, and other-task docs sit in the same working tree. Non-blocking for this review; keep them out of this task's commit so the display-only change lands isolated.

</details>

<details>
<summary>Details</summary>

### Strict gating is unchanged and still tight

The new columns add no new entry point. The only dispatch into the custom renderer remains the existing double-guarded short-circuit:

```ts
if (allowCumulativeVertical && group.key === 'timepoints_release') {
  return renderCumulativeVertical(group);
}
```

`allowCumulativeVertical` is `detail.worksheet.template_code === 'TPL-A6A-0005'`. Any other template, or any other group on A6A-0005, falls through to the generic renderer. The three new `<td>`/`<th>` cells live entirely inside the body of `renderCumulativeVertical`, so they cannot render for anything outside that gate (confirmed).

### % Assay and C1 read computed values, nothing recomputed

Both columns pull the hidden computed values straight from the preview payload for the current unit:

```ts
const computedRow = computed.rows?.[group.key]?.[rowIndex];
const jassayVal = computedRow?.[`jassay_${u + 1}`];
const kfracVal  = computedRow?.[`kfrac_${u + 1}`];
const unitVal   = computedRow?.[`unit_${u + 1}`];
```

`% Assay` renders `assay2dp(jassayVal)` and `C1` renders `assay2dp(kfracVal)`. There is no arithmetic on these two values in the UI — they are formatted and displayed as-is. The engine's `jassay_N`/`kfrac_N` are the single source of truth (confirmed).

### C2 is the only UI arithmetic, and it is blank-guarded

```ts
const carryOver =
  typeof unitVal === 'number' && typeof jassayVal === 'number'
    ? unitVal - jassayVal
    : null;
...
{assay2dp(carryOver)}
```

The subtraction happens only when both `unit_N` and `jassay_N` are present numbers; otherwise `carryOver` is `null`. A `null` (or any non-number / blank) routes into `displayValue`, which returns the em-dash:

```ts
function displayValue(value, field) {
  if (value === null || value === undefined || value === '') return '—';
  ...
}
```

So a timepoint with no prior carry-over (first timepoint) reads blank in C2, matching the brief's expected visual (1 Hr C2 blank; 24 Hr C2 0.30/0.33/0.25). This is display-only — nothing is written back to the data model (confirmed).

### 2dp formatting reuses displayValue via a synthetic FieldDef

The hidden `jassay_N`/`kfrac_N` fields carry no rounding of their own, so the renderer defines a throwaway 2dp field and funnels the three columns through the same `displayValue` the rest of the form uses:

```ts
const ASSAY_2DP_FIELD: FieldDef = {
  key: '__assay_display',
  kind: 'calculated',
  rounding: { mode: 'round', digits: 2 },
};
const assay2dp = (value: unknown): string => displayValue(value, ASSAY_2DP_FIELD);
```

`FieldDef` requires `key` and `kind` and takes an optional `rounding`; `'calculated'` is a valid `FieldKind`, so this literal type-checks. With `mode: 'round'` and `digits: 2`, `displayValue` returns `value.toFixed(2)` for numbers and the em-dash for blanks — identical precision and blank handling to the engine-reported cells, which is exactly what the brief asks for (confirmed).

### Existing table, stats, inputs, and add/remove preserved

The three columns are appended to the existing table's header and body rows; the Sample Area cell still renders through `renderInput(group, rowIndex, areaField)` (editable, autosave, edit-lock intact) and the Cumulative %Release cell still renders through `computedCell(group, rowIndex, unitField)`. The Mean/Min/Max/%RSD footer table and the `addRow`/`removeRow` Timepoint controls are unchanged by this diff. The new cells are read-only `<span>`s and add no editable surface or writeback (confirmed).

### Accessibility and styling consistent with the file

The three new headers use `<th scope="col" className="text-right p-2 text-500 font-medium">`, matching the two existing headers in the same table and the stat-footer headers. The new cells reuse the same `font-mono text-right block` span styling and the `preview.stale ? 'text-400' : 'text-900 font-medium'` staleness treatment that `computedCell` applies, so the % Assay/C1/C2 cells dim in lockstep with the computed cells during recalculation (confirmed).

### Build evidence

`verification.md` records `npm run build` (`tsc -b && vite build`) run from `d:\RD-instance\GIT\frontend-react` exiting 0 with zero TypeScript errors (`✓ 336 modules transformed`, `✓ built in 4.36s`), with only the pre-existing vite chunk-size advisory. ESLint is documented as not installed project-wide — a known pre-existing gap, not introduced here. Per the task constraints the build was not re-run; the recorded evidence is sufficient and consistent with the diff (type-safe synthetic `FieldDef`, no new imports), so no spot-check was warranted.

### Separate vs merged layout — a decision to confirm, not a defect

The delegation brief described this change as a *separate* read-only `% Assay` 3-column table rendered *beneath* the existing table. The implementation instead appended the three columns onto the existing table as a single five-column table, which `verification.md` attributes to a mid-task user clarification. The columns, their data sources (`jassay_N` / `kfrac_N` / `unit_N − jassay_N`), the 2dp formatting, and the blank-guard all match the brief; only the container layout differs. Because the deviation is a documented deliberate decision and does not change the data shown, it is not treated as a blocking finding — but the merged layout should be confirmed as the intended final form, since the brief's wording and the implementation disagree.

### Unrelated changes bundled in the working tree

The working tree also carries edits outside this task: `backend-v2/scripts/template_definitions/__init__.py` (registers an unrelated `a9_sodium_metabisulfite` module), `frontend-react/src/features/trf/pages/TRFListPage.tsx` (TRF list test-names column), and another task's verification doc plus the worklog. The worklog attributes these to separate tasks; they do not touch the A6A-0005 render and are out of scope here. They should be kept out of this task's commit so the display-only change lands in isolation.

</details>

<details>
<summary>File map</summary>

- `src/features/test-templates/components/WorksheetForm.tsx` — adds the `ASSAY_2DP_FIELD` / `assay2dp` display helper and the three `% Assay` / `C1` / `C2` columns (headers + cells, with the `C2 = unit_N − jassay_N` blank-guarded carry-over) inside the existing `renderCumulativeVertical` table. The only file in scope for this task.

Out-of-scope working-tree changes (other tasks, not reviewed here): `backend-v2/scripts/template_definitions/__init__.py`, `frontend-react/src/features/trf/pages/TRFListPage.tsx`, `frontend-react/.agents/tasks/worksheet-column-merge/verification.md`, `worklog/2026-10-24-template-tasks.md`.

Full diff: `git diff` in `d:\RD-instance\GIT`.

</details>
