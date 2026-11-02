# Verification — A6D calibration/linearity wide-table wrapping

Iteration: 1 (first implementation; no prior `review.json`).

## What changed

Single file, scoped to the shared generic sequence/table renderer in
`frontend-react/src/features/test-templates/components/WorksheetForm.tsx`.
No template definition, `lims.db`, backend, or seed data touched. Pure frontend display fix.

Four coordinated edits, all gated on the existing `wideTable`/`veryWideTable` width classification so
narrow tables (`tableColCount <= 8`) are byte-identical to before:

1. **New shared const `WRAP_CELL`** (added just before `renderInput`):
   `{ whiteSpace: 'normal', wordBreak: 'break-word', overflowWrap: 'anywhere' } as const`.
   Single source of truth for the wrap rule; typed `as const` so it is assignable to React `CSSProperties`.

2. **Wide-table `tableStyle` branch** changed from `tableLayout: 'auto'` to
   `tableLayout: 'fixed', width: '100%'`, keeping the existing `minWidth: ${tableColCount * colMinRem}rem`
   floor. A fixed full-width layout divides the Card width evenly so long headers/values wrap within their
   column instead of the columns growing and pushing content under the scroll. The retained `overflowX: 'auto'`
   wrapper (unchanged) remains only as a scroll fallback when the `minWidth` floor exceeds the container.
   The `veryWideTable` branch (already `fixed`/`100%`) and the narrow `else` branch (`fixed`) are unchanged.

3. **Header cells (`tableHead`)**: a `cellWrap = (wideTable || veryWideTable) ? WRAP_CELL : undefined` guard is
   spread into the `#` `<th>` style and the data `<th>` style. The data `<th>` keeps its baseline
   `wordBreak: 'break-word'` for all widths, and only adds `whiteSpace: 'normal'` + `overflowWrap: 'anywhere'`
   for wide tables. `title`, `className`, unit/calc icons, and the per-column delete icon are untouched.

4. **Body cells (`renderRows`)**: the same `cellWrap` guard is spread into the `#` `<td>`, the calculated `<td>`,
   and the input `<td>`. Inputs keep `w-full` and shrink with their fixed column; the trailing action `<td>` is
   unchanged.

## Resulting DOM / CSS evidence (from source, confirmed by `git diff`)

For the A6D `linearity` group (`tableColCount = 1 + 8 + 0 - 0 + 1 = 10` → `wideTable = true`,
`veryWideTable = false`):
- `<table>` now resolves to `table-layout: fixed; width: 100%; min-width: 45rem` (10 × 4.5rem floor),
  `border-collapse: collapse`, inside the retained `<div style="overflow-x: auto">` fallback wrapper.
- Every header `<th>` resolves to `white-space: normal; word-break: break-word; overflow-wrap: anywhere`, so
  "Standard Weight (mg)" and "Calibration curve" wrap onto multiple lines inside their fixed-width columns
  rather than clipping.
- Every body `<td>` (including the `#` column and the first data column that holds values like
  "Calibration standard-1") resolves to the same wrap rule, so entered text wraps within the column.

For the `calibration` group (`tableColCount = 14` → `veryWideTable = true`): already `fixed`/`100%`; the new
`cellWrap` now also makes its long headers/cells wrap instead of truncating.

Narrow tables (`tableColCount <= 8`): `cellWrap` is `undefined`, so no inline wrap style is added; the data
`<th>` keeps exactly its prior `{ wordBreak: 'break-word' }`. Rendering is unchanged.

Untouched by this change (confirmed via diff): `renderCumulativeVertical`, `renderGroupFooter`, the singleton
field-grid branch, `renderGroupHeaderContext`/Context sections, and the three local `tableLayout: 'fixed'`
area/timepoints/flux tables.

## Commands run and results

From `frontend-react/`:

- `npm run build` (= `tsc -b && vite build`) → PASS. Zero TypeScript errors; `vite build` completed
  ("✓ 336 modules transformed", "✓ built in ~4.3s"). The only output warning is the pre-existing
  >500 kB chunk-size advisory, unrelated to this change.
- Lint: `eslint` is NOT installed in `node_modules` in this environment, and `npm run lint` / `npx eslint`
  would require an interactive network install, so lint was not run. The authoritative gate (`tsc -b`) passed.

## Visual confirmation

Direct in-browser visual confirmation was NOT possible in this headless environment: `start-lims.bat` spawns a
Python/uvicorn backend plus a Vite dev server in separate Windows console windows and opens a browser, none of
which can be driven or observed here. Verification is therefore: (a) clean `tsc -b` + `vite build`, and (b) the
DOM/CSS evidence above proving the wide-table cells now resolve to wrapping (`white-space: normal`,
`word-break: break-word`, `overflow-wrap: anywhere`) with `table-layout: fixed; width: 100%`, rather than the
prior `table-layout: auto` growth-and-clip behavior. A reviewer with the app running should confirm the
TPL-A6D-0002 (TST-IVRT) worksheet shows all 8 linearity headers wrapped and all entered values visible, with the
other tables unchanged.
