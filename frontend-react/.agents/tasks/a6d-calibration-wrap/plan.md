# Implementation Plan — Wide worksheet table wrapping / best-fit (A6D linearity & calibration)

## Context from investigation (read this first)

- **One file owns the fix:** `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`. All worksheet
  tables are plain `<table>` elements built by this component — they are **not** PrimeReact `DataTable`s, so the
  `.p-datatable` rules in `src/shared/styles/theme-overrides.css` do **not** apply to them. Styling is PrimeFlex utility
  classes (`w-full`, `text-sm`, `text-xs`, `p-1`, `p-2`) plus inline `style` objects. Reuse that approach; do not add a new
  CSS module or global rule.

- **The overflowing table the user sees** ("Standard Tapinarof for Linearity", shown under the "Calibration Standards"
  area) is the template group `linearity` on the Active template `TPL-A6D-0002`. Confirmed from `backend-v2/lims.db`:
  it is a `sequence` group, `rows.min = 9`, `rows.max = 15`, with 8 visible `input` fields, none hidden, none calculated:
  `calibration_curve` (label "Calibration curve"), `concentration_pct` ("Concentration", unit %), `std_weight_mg`
  ("Standard Weight", unit mg), `diluted_to_ml_1` ("Diluted to", mL), `ml_a` ("mL", mL), `ml_b` ("mL", mL), `ml_taken`
  ("mL taken", mL), `diluted_to_ml_2` ("Diluted to", mL). Headers render as label + ` (unit)` so e.g. "Standard Weight
  (mg)", "Calibration curve".

- **Why it clips.** The generic table renderer (the `groups.map(...)` block, roughly lines 1345–1560 of
  `WorksheetForm.tsx`) classifies table width by column count:
  - `tableColCount = 1 (# col) + editableFields + calculatedFields − hiddenInGroup + (canAddRows ? 1 : 0)`
  - `wideTable = tableColCount > 8`, `veryWideTable = tableColCount > 12`.
  For `linearity`: `tableColCount = 1 + 8 + 0 − 0 + 1 = 10` → `wideTable = true`, `veryWideTable = false`.
  That path sets `tableStyle = { tableLayout:'auto', minWidth: tableColCount*colMinRem rem }` (here `10 * 4.5 = 45rem`)
  and wraps the table in `<div style={{ overflowX:'auto' }}>`. With `tableLayout:'auto'` and a 45rem floor the columns
  grow to fit their longest content on a single line; inside the worksheet panel's constrained column the table is wider
  than the Card, so the right-hand columns/headers sit under the scroll and read as "cut off". The header `<th>` already
  has `wordBreak:'break-word'`, but `tableLayout:'auto'` lets columns widen instead of wrapping, so wrapping never kicks
  in; cell `<td>`s and their inputs have no wrap/min-size guidance at all.

- **The "Calibration Standards" table itself** is a *different* group, `calibration` (a `table`, `rows.min=2 max=10`,
  12 visible fields = 8 input + 1 area + 3 calculated) → `tableColCount = 1 + 9 + 3 − 0 + 1 = 14` → `veryWideTable = true`.
  That path already uses `tableLayout:'fixed'; width:100%` with compact `text-xs`/`p-1`, so it fits width-wise but its
  fixed equal columns can still truncate the long header labels because there is no explicit wrap on the cell text. The
  fix below is applied at the shared renderer level so BOTH the `wideTable` and `veryWideTable` branches wrap their
  content; it is not keyed to any group name.

- **Must NOT regress:** the per-cell area/timepoints/flux tables and the TPL-A6A-0005 vertical render
  (`renderCumulativeVertical`, ~lines 880–1210) and the `renderGroupFooter` flat/column-aligned tables each use their own
  local `tableLayout:'fixed'` styles — leave those untouched. Narrow tables (`tableColCount <= 8`) take the final
  `else` branch (`tableLayout:'fixed'`, no scroll wrapper) and must look exactly as today. Singleton sections (field grid
  via `fieldColClass`) and the Context / `renderGroupHeaderContext` sections are not `<table>`s and are out of scope.

- **Build/verify tooling:** `frontend-react/package.json` → `npm run build` = `tsc -b && vite build`; `npm run lint` =
  `eslint .`. There is **no** unit-test framework in `frontend-react` (no vitest/jest). Verification is therefore: a clean
  typecheck + production build, a lint pass, and visual/DOM evidence from the dev server (`npm run dev`).

## Chosen approach (and why)

Scope the fix to the shared generic table renderer so any wide group benefits, in two coordinated parts:

1. **Make wide tables wrap instead of grow.** For the `wideTable && !veryWideTable` branch, switch the table from
   `tableLayout:'auto'` to `tableLayout:'fixed'` with `width:'100%'` and a sensible `minWidth` floor, and give header and
   body cells `white-space:normal; word-break:break-word; overflow-wrap:anywhere`. A fixed layout divides the available
   width evenly, so long headers like "Standard Weight (mg)" wrap onto 2–3 lines inside their column rather than forcing
   the table past the Card edge. The `overflowX:'auto'` wrapper stays as a fallback only when the `minWidth` floor is
   larger than the container (very narrow screens), so content is reachable either way. Rationale: wrapping is exactly what
   the user asked for ("wrap text to view all entered details"), and reusing `tableLayout:'fixed'` matches what the
   `veryWideTable` and footer tables already do — no new styling system.

2. **Guarantee cell text wraps everywhere wide.** Add a shared cell-wrap style/class applied to the `#`, data `<th>`,
   and data `<td>` of wide tables (both `wideTable` and `veryWideTable`) so header labels and entered text can break.
   Inputs already carry `w-full`, so they shrink with their fixed column; only the text (headers, computed cells, the
   row-label-like first column values such as "Calibration standard-1") needs explicit wrap guidance.

This keeps every narrow table (`tableColCount <= 8`) on its current fixed-layout path unchanged, and leaves the
area/timepoints/flux/footer/vertical tables (which build their own `<table>` locally) untouched.

---

## Steps

- [ ] 1. Add a shared wrap style constant for wide-table cells near the top of the `WorksheetForm` component body (e.g.
      just before `renderInput`, alongside the other inline-style helpers). Define, as a typed const:
      `const WRAP_CELL = { whiteSpace: 'normal', wordBreak: 'break-word', overflowWrap: 'anywhere' } as const;`
      This is the single source of truth reused by the header and body cells so the rule stays consistent and easy to
      remove later.
      Files: `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
      Verify: `cd frontend-react; npm run build` — `tsc -b` compiles with no new type errors (the `as const` keeps the
      object assignable to React `CSSProperties`).

- [ ] 2. Change the wide-table `tableStyle` so wide tables wrap rather than expand. In the generic table renderer, locate
      the `const tableStyle = veryWideTable ? ... : wideTable ? ({ borderCollapse:'collapse', tableLayout:'auto',
      minWidth: `${tableColCount * colMinRem}rem` }) : (...)` expression (around lines 1480–1489). For the `wideTable`
      (middle) branch, change `tableLayout:'auto'` to `tableLayout:'fixed'` and add `width:'100%'`, keeping the existing
      `minWidth:`${tableColCount * colMinRem}rem`` as the lower bound. Leave the `veryWideTable` branch
      (`tableLayout:'fixed', width:'100%'`) and the final narrow `else` branch (`tableLayout:'fixed'`) exactly as they are.
      Result: a 10-column linearity table lays out as fixed, full-width columns that wrap their contents, only scrolling
      when the container is narrower than the `minWidth` floor.
      Files: `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
      Verify: `cd frontend-react; npm run build` passes; then `npm run dev`, open the TPL-A6D-0002 worksheet, and confirm
      in DevTools that the `linearity` table element has `table-layout: fixed` and no longer overflows its Card
      horizontally at a standard 1440px viewport.

- [ ] 3. Apply `WRAP_CELL` to the shared `tableHead` cells so long header labels wrap. In the `tableHead` JSX (around
      lines 1402–1455), merge `WRAP_CELL` into the `#` `<th>`'s inline `style` and into each data `<th>`'s inline `style`
      (that data `<th>` currently has `style={{ wordBreak:'break-word' }}` — replace it with `style={WRAP_CELL}` so it
      also gets `whiteSpace:'normal'` and `overflowWrap:'anywhere'`). Do not remove the existing `title`, `className`, or
      per-column delete-icon logic. Because `tableHead` is shared by the narrow, `wideTable`, and `veryWideTable` branches,
      guard the wrap so it only applies when `wideTable || veryWideTable` is true — e.g. compute
      `const headWrap = wideTable || veryWideTable ? WRAP_CELL : undefined;` and spread it: for the data `<th>` use
      `style={{ ...(calc ? {} : {}), ...headWrap, wordBreak: 'break-word' }}` (keep `wordBreak:'break-word'` as the
      baseline for ALL widths so narrow tables are byte-identical to today, and only add `whiteSpace/overflowWrap` for
      wide tables). Keep the `#` `<th>` width style (`veryWideTable ? '1.6rem' : '3rem'`) and merge `headWrap` into it.
      Files: `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
      Verify: `cd frontend-react; npm run build` passes; in the dev server, confirm the linearity headers
      "Standard Weight (mg)" and "Calibration curve" wrap to multiple lines and are fully readable, and that a narrow
      table elsewhere (e.g. a `tableColCount <= 8` group) is visually unchanged.

- [ ] 4. Apply `WRAP_CELL` to the body cells of wide tables so entered text and the first-column labels wrap. In
      `renderRows` (around lines 1457–1500), for wide tables only, add the wrap style to the `#` `<td>` and to each data
      `<td>`. Use the same `const bodyWrap = wideTable || veryWideTable ? WRAP_CELL : undefined;` guard and spread it into
      the `<td>` `style` (these `<td>`s currently have no inline `style`, only `className={cellPad}`/`inputCellPad`), e.g.
      `<td className={cellPad} style={bodyWrap} key={field.key}>`. This lets long entered strings (e.g.
      "Calibration standard-1") and computed cell text wrap within their fixed column. Do not alter the inputs themselves
      (they keep `w-full` and shrink with the column) and do not touch the trailing action `<td>` beyond leaving it as is.
      Files: `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
      Verify: `cd frontend-react; npm run build` passes; in the dev server, enter a long value in the first linearity
      column and confirm it wraps within the cell instead of widening the column / clipping; confirm the
      `veryWideTable` "Calibration Standards" (`calibration`) table's long headers/cells also wrap and nothing overlaps.

- [ ] 5. Regression check the untouched tables and sections. Confirm by reading the diff that NO change was made inside
      `renderCumulativeVertical`, `renderGroupFooter`, the singleton field-grid branch, `renderGroupHeaderContext`, or the
      Context section, and that the three local `tableLayout:'fixed'` tables at lines ~655/1021/1150 are unmodified. The
      only edits are: the new `WRAP_CELL` const, the `wideTable` `tableStyle` branch, the shared `tableHead` `<th>`s
      (wrap added, gated on wide), and the `renderRows` `<td>`s (wrap added, gated on wide).
      Files: `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
      Verify: `cd frontend-react; npm run build` (clean `tsc -b` + `vite build`) and `npm run lint` (no new warnings);
      in the dev server, spot-check the TPL-A6D-0002 worksheet end to end — the Context block, "Sampling details"
      singleton, the per-cell area/timepoints/flux tables, and the Additional Info header-context values (eleven
      pre-filled values) all render exactly as before, while the linearity and calibration tables now show all content
      with wrapped headers/cells.

## Verification summary (commands)

Run from `frontend-react/`:

1. `npm run build` — must complete `tsc -b` with zero errors and produce a successful `vite build`.
2. `npm run lint` — no new lint errors introduced by the change.
3. `npm run dev`, open the TPL-A6D-0002 worksheet (via a TRF test line → worksheet panel), and capture visual/DOM
   evidence: (a) the `linearity` table element reports `table-layout: fixed` and does not overflow its Card at 1440px;
   (b) headers "Standard Weight (mg)" / "Calibration curve" and any long entered first-column value wrap onto multiple
   lines and are fully visible; (c) narrow tables and the singleton/context/footer sections are visually unchanged.

## Notes / assumptions

- The user's phrase "Calibration Standards" names the on-screen area; the actual clipped 8-column table is the
  `linearity` sequence ("Standard Tapinarof for Linearity"). The fix is applied at the shared wide-table level so both the
  `linearity` (`wideTable`) and the `calibration` (`veryWideTable`) tables benefit without hardcoding either group key.
- No change to the template definition, `backend-v2/lims.db`, or any seed/backend data — this is a pure frontend display
  fix, as required.
- If, in the dev server, a particular viewport still shows the linearity table exceeding its Card because the
  `minWidth` floor (≈45rem) is wider than the available column, the retained `overflowX:'auto'` wrapper provides a
  horizontal-scroll fallback so content is never unreachable; wrapping remains the primary mechanism.
