# Vertical "Cumulative % Release" rendering for TPL-A6A-0005

This change adds a display-only alternative layout for TPL-A6A-0005's `timepoints_release` sequence group in the worksheet form. Instead of one timepoint per horizontal row with Unit-1..6 as columns, each timepoint now renders as its own block: an editable Timepoint header, a two-column "Sample Area → Cumulative %Release" table stacking the six units vertically, and a per-timepoint Mean/Min/Max/%RSD footer. The data model is untouched — timepoints remain rows, the cumulative math is unchanged — only each row's unit columns are transposed on screen. Editing and computed-value display both reuse the existing `renderInput`, `computedCell`, and `displayValue` helpers, so bound values and displayed numbers are identical to the horizontal layout.

**Watch for:** the working tree bundles unrelated changes outside this task — a `.py` edit (`template_definitions/__init__.py` registering `a9_sodium_metabisulfite`), `TRFListPage.tsx`, and a worklog/verification doc. These belong to other tasks and are not part of the A6A-0005 render (confirmed). The A6A-0005 change itself touches only `WorksheetForm.tsx` and is frontend display-only (confirmed).

**Verdict**: APPROVED

## High-level view

The new path is reached by a short-circuit at the top of the `groups.map(...)` loop, gated on both `allowCumulativeVertical` (`template_code === 'TPL-A6A-0005'`) and `group.key === 'timepoints_release'`. Every other template and every other group falls through to the unchanged generic renderer, and no shared helper was modified, so there is no behavioral diff anywhere else (confirmed).

Editable cells (`time_hr`, `area_1..6`) go through the same `renderInput` helper the rest of the form uses, inheriting its `setCell` onChange, autosave, and `disabled = !isGroupEditing(...)` edit-lock. Computed cells (`unit_1..6`, `mean`/`min_val`/`max_val`/`rsd`) go through `computedCell`, which reads `computed.rows[...]` and formats via `displayValue`. Nothing is recomputed, re-rounded, or hard-coded in the UI (confirmed).

Add/Remove Timepoint reuses the existing `addRow`/`removeRow` with the same `min`/`max`/`editingThisGroup` guards as the generic sequence renderer. Table markup uses `th scope="col"` headers and the editable Timepoint field carries a `label`/`htmlFor` pair; aria labelling is consistent with the rest of the file.

The recorded build evidence shows `npm run build` (`tsc -b && vite build`) passing with zero TypeScript errors; ESLint absence is a known pre-existing gap, not a regression.

<details>
<summary>Issues (1)</summary>

1. **Unrelated changes bundled in working tree** — `template_definitions/__init__.py`, `TRFListPage.tsx`, and a worklog/verification doc are modified in the same working tree but belong to other tasks, not the A6A-0005 render. Non-blocking for this review; keep them out of this task's commit so the display-only change stays isolated.

</details>

<details>
<summary>Details</summary>

### Strict gating on template + group

The gate is tight on both required conditions. A new flag mirrors the existing per-template pattern:

```ts
const allowCumulativeVertical = detail.worksheet.template_code === 'TPL-A6A-0005';
```

and the dispatch at the top of the groups loop requires both the flag and the exact group key before diverging:

```ts
if (allowCumulativeVertical && group.key === 'timepoints_release') {
  return renderCumulativeVertical(group);
}
```

Any other template, or TPL-A6A-0005's other groups, skip this branch and hit the generic renderer exactly as before. No shared helper (`renderInput`, `computedCell`, `displayValue`, `addRow`, `removeRow`, `isGroupEditing`, `renderGroupToolbar`, `renderGroupHeaderContext`, `renderGroupFooter`) was modified — all are consumed read-only — so there is no path by which another template's output changes (confirmed).

### No recomputation in the UI

Both computed surfaces route through the existing `computedCell`, which pulls from the precomputed source and defers formatting to the shared helper:

```ts
const value = computed.rows?.[group.key]?.[rowIndex]?.[field.key];
...
{displayValue(value, field)}
```

The six Cumulative %Release cells (`unit_1..6`) and the four stat cells (`mean`, `min_val`, `max_val`, `rsd`) all use `computedCell(group, rowIndex, field)`. No arithmetic, rounding, or literal numbers appear in the new renderer, so shown values are byte-identical to the horizontal layout. The stat labels are remapped for display only (`min_val → "Min"`, `max_val → "Max"`, `rsd → "%RSD"`); the underlying field keys and values are unchanged.

### Editable wiring reused, not forked

`time_hr` and `area_1..6` render through the same `renderInput(group, rowIndex, field)` the generic table uses. That helper owns value binding (`values[group.key]?.[rowIndex]?.[field.key]`), the `setCell` onChange that feeds autosave, and the per-section edit-lock (`disabled = !isGroupEditing(group.key) || isMirrorField(field)`). Because the new layout calls it rather than duplicating an input, disabled/read-only behaviour, mirror-field handling, and autosave carry over with no forked path (confirmed).

Field lookups are defensive: `fieldByKey` returns `undefined` when a key is absent, and each cell renders an em-dash fallback rather than throwing, so a definition that lacks one of the expected keys degrades gracefully instead of crashing.

### Add/Remove Timepoint affordance preserved

The block reuses `addRow`/`removeRow` with the same guards as the generic sequence renderer:

```ts
const canAddRows = editable && max > min;
...
disabled={rows.length >= max}   // Add
disabled={rows.length <= min}   // Remove (per-row trash)
```

Controls are shown only when `canAddRows && editingThisGroup`, matching the existing behaviour, and the count strip (`{rows.length} of {max} timepoint(s)`) mirrors the generic renderer.

### Accessibility

Both tables use `<th scope="col">` headers. The editable Timepoint field is paired with a `<label htmlFor={`${group.key}-time_hr-${rowIndex}`}>` and the per-row delete button carries `aria-label={`Remove timepoint ${rowIndex + 1}`}`. The number/text inputs inherit the aria-label built inside `renderInput`. This is consistent with the aria conventions used elsewhere in the file.

### Build evidence

`verification.md` records `npm run build` (`tsc -b && vite build`) exiting 0 with zero TypeScript errors (`✓ 336 modules transformed`), with only the pre-existing vite chunk-size advisory. ESLint is documented as not installed project-wide — a known pre-existing gap, not introduced here. Per the task constraints the build was not re-run.

### Unrelated changes bundled in the diff

The working tree also carries edits that are not part of this task: `backend-v2/scripts/template_definitions/__init__.py` (registers an unrelated `a9_sodium_metabisulfite` module), `frontend-react/src/features/trf/pages/TRFListPage.tsx` (TRF list test-names column), and two worklog/verification docs. The worklog itself attributes these to separate tasks. They do not touch the A6A-0005 render and do not affect this verdict, but they should be kept out of this task's commit so the display-only change lands in isolation.

</details>

<details>
<summary>File map</summary>

- `src/features/test-templates/components/WorksheetForm.tsx` — adds `allowCumulativeVertical` gate flag, the `renderCumulativeVertical(group)` presentational renderer, and the groups-loop short-circuit for `timepoints_release`. The only file in scope for this task.

Out-of-scope working-tree changes (other tasks, not reviewed here): `backend-v2/scripts/template_definitions/__init__.py`, `frontend-react/src/features/trf/pages/TRFListPage.tsx`, `frontend-react/.agents/tasks/worksheet-column-merge/verification.md`, `worklog/2026-10-24-template-tasks.md`.

Full diff: `git diff` in `d:\RD-instance\GIT`.

</details>
