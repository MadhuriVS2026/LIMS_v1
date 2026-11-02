# Verification — Cumulative % Release vertical rendering (TPL-A6A-0005)

First iteration (no `review.json` existed). Implemented from scratch per the
task brief. DISPLAY-ONLY change, frontend only.

## Scope of change

- **MODIFIED** `src/features/test-templates/components/WorksheetForm.tsx`
  - Added gate flag `allowCumulativeVertical = detail.worksheet.template_code === 'TPL-A6A-0005'`
    (next to the existing `allowClearColumn` TPL-A6A-0004 gate).
  - Added a `renderCumulativeVertical(group)` presentational method that renders
    each timepoint row of the `timepoints_release` sequence as its own block:
    editable Timepoint header (`time_hr` via `renderInput`), a two-column
    "Sample Area → Cumulative %Release" table stacking `area_1..6` (via
    `renderInput`) against `unit_1..6` (via `computedCell`), and a per-timepoint
    Mean/Min/Max/%RSD footer (`mean`/`min_val`/`max_val`/`rsd` via `computedCell`).
    Add/Remove timepoint controls reuse the existing `addRow`/`removeRow`.
  - Added a short-circuit at the top of the `groups.map(...)` loop:
    `if (allowCumulativeVertical && group.key === 'timepoints_release') return renderCumulativeVertical(group);`

No other files changed. No template definition / backend / engine / formula /
`.py` change was made.

## Build / type-check — PASS

Command (run from `d:\RD-instance\GIT\frontend-react`):

```
npm run build
```

Runs `tsc -b && vite build`. Result: **EXIT 0**, zero TypeScript errors.
`✓ 336 modules transformed. ✓ built in 4.18s`. The only non-error output is the
pre-existing vite advisory that a chunk exceeds 500 kB (bundle-size hint, not a
compile error, unrelated to this change).

## Lint

`npm run lint` was NOT run: ESLint is not installed in this project. This is a
known pre-existing gap, not a failure introduced by this change.

## Dev server

No dev server / watch process was started. The orchestrator runs the frontend
dev server separately at http://localhost:5174; visual confirmation is at /trf/39
(a worksheet on TPL-A6A-0005).
