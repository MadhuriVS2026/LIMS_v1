# Implementation Plan — Column-aligned worksheet table footers

## Goal

Render Mean / SD / % RSD footers for TPL-A2-0004's `std_areas` ("Standard
Replicate Injections") and `bkt_areas` ("BKT Standard Injections") tables as real
footer ROWS whose values sit directly beneath each compound COLUMN, instead of
the current flat label/value strip. Frontend rendering change ONLY — no template
definition, DB, or calculation-engine edits.

## Root cause (verified)

- The `std_areas` / `bkt_areas` groups are laid out injections-as-rows ×
  compounds-as-columns. Visible fields in definition order are:
  `inj_label` (text input) → `tri_area` → `dppg_area` → `chol_area` → `depc_area`
  (confirmed in `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`,
  `_std_area_fields()` / `_bkt_area_fields()`).
- Each group's `footer` array is three logical rows of column-aligned cells. Each
  LABELED item (`label: "Mean"/"SD"/"% RSD"`) starts a row; the UNLABELED items
  that immediately follow are the per-compound column values in column order
  (tri → dppg → chol → depc). Verified verbatim in the same module (footer arrays
  for `std_areas` using `stats.*_std_*` refs and `bkt_areas` using `stats.*_pool_*`
  refs).
- `renderGroupFooter` in `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
  renders every footer item as a label-left / value-right line inside a narrow
  `maxWidth: min(28rem,100%)` box — no column concept, so all 12 entries pile up.
- The preview `<tfoot>` in `frontend-react/src/features/test-templates/pages/WorksheetPreviewPage.tsx`
  (single `colSpan` cell with a `flex-wrap` strip) has the same flat behavior.
- `frontend-react/src/features/test-templates/pages/PrintWorksheetPage.tsx` renders
  NO footer at all (its multi-row `<table>` closes `<tbody>` with no `<tfoot>`), so
  it is OUT OF SCOPE. See "Print path" below.

## Column-index mapping (the crux)

The footer row must mirror the data `<tbody>`'s column set EXACTLY.

**Live form (`WorksheetForm.tsx`)** — the data table columns are built as:
1. a leading `#` row-number column (always present),
2. one column per entry in `visibleFields` (definition order, after `hidden` and
   per-worksheet `hiddenColumns` filtering),
3. a trailing action column, present only when `canAddRows` is true
   (`editable && kind !== 'singleton' && max > min`). For A2's tables
   (`min:1, max:12`) this column IS present whenever the worksheet is editable.

A column-aligned footer row therefore emits, left to right:
- `#` column → empty `<td>`.
- First data field (`visibleFields[0]`, i.e. `inj_label`) column → the ROW LABEL
  ("Mean" / "SD" / "% RSD").
- Remaining data-field columns (`visibleFields[1..]`, i.e. `tri_area`,
  `dppg_area`, `chol_area`, `depc_area`) → the group's values in order: the
  LABELED item's value under the FIRST remaining column (tri), then each UNLABELED
  item under the next columns (dppg, chol, depc).
- Trailing action column (only if `canAddRows`) → empty `<td>`.

So a footer "row group" holds `1 + (number of trailing unlabeled items)` values,
and they map onto `visibleFields.slice(1)` by position. For A2 that is exactly 4
values into 4 compound columns. If a row group has fewer values than available
compound columns, fill left-to-right and leave the rest as em-dash blanks; if it
has more, render the overflow in the last column's cell is NOT expected — clamp to
the available columns (log nothing; this is a definition-shape contract).

**Preview page (`WorksheetPreviewPage.tsx`)** — same, except there is NO trailing
action column. Columns are `#` + `fields` (its `visibleFields(group)`), so the
footer row is: `#` empty, label under `fields[0]`, values under `fields[1..]`.

Both sites must compute the value column list from the SAME field array they used
to build the data rows (live form: the `visibleFields` const inside the group map;
preview: `fields` from `visibleFields(group)`), so alignment can never drift.

## Shape-detection rule (backward-compatible)

A footer is "column-aligned" iff it contains at least one UNLABELED item that
follows a labeled one — i.e. `footer.some((item) => !hasLabel(item))` where
`hasLabel(item)` is `item.label != null && item.label !== ''`. Decision is purely
by DATA SHAPE; never by template code or field name.

- Column-aligned footer → render as `<tfoot>` rows beneath the table grid (new
  behavior).
- Footer where EVERY item has its own label (the ~15 other templates' simple
  `[{label:"Mean",...},{label:"SD",...},{label:"% RSD",...}]`) → render the
  EXISTING flat strip UNCHANGED (live form: the narrow box; preview: the single
  `colSpan` strip). Do not alter its markup or styling.

## Shared helper

Location: `frontend-react/src/features/test-templates/models/groupFooter.ts`
(a new small util beside `describeDefinition.ts` and `testTemplate.types.ts`).

Signature and return shape:

```ts
import type { GroupFooterItem } from './testTemplate.types';

/** One rendered footer row: a label plus its column-aligned values. */
export interface FooterRow {
  /** Row label ("Mean"/"SD"/"% RSD"); may be '' if the leading item had none. */
  label: string;
  /** Values in compound-column order: the labeled item first, then the
   *  unlabeled items that followed it, each still carrying its ref/unit/rounding
   *  so the caller formats exactly as today. */
  cells: GroupFooterItem[];
}

/** True when the footer is column-aligned (>=1 unlabeled item). */
export function isColumnAlignedFooter(footer: GroupFooterItem[] | undefined): boolean;

/** Group a column-aligned footer into rows: a new row starts at each LABELED
 *  item and absorbs the following UNLABELED items until the next label/end.
 *  Returns [] for an empty/undefined footer. Leading unlabeled items (before any
 *  label) start their own label-'' row so nothing is dropped. */
export function groupFooterRows(footer: GroupFooterItem[] | undefined): FooterRow[];
```

`hasLabel` is the single source of truth for "labeled": `item.label != null &&
item.label !== ''`. Keep it internal to the module (not exported) unless a caller
needs it.

All three value-formatting rules stay in the CALLERS (they differ: live form uses
`computed.values[ref]` + `preview.stale` styling; preview uses em-dash
placeholders). The helper only decides shape and groups cells; it does not format.

## Type change

`GroupFooterItem.label` in
`frontend-react/src/features/test-templates/models/testTemplate.types.ts` is
currently `label: string` (required). The A2 footers omit `label` on unlabeled
items, so make it optional: `label?: string`. This is backward-compatible — every
existing simple footer still supplies a label. No other type change is needed
(`ref`, `unit?`, `rounding?` already fit). `GroupDef.footer?: GroupFooterItem[]`
is unchanged.

## Backward-compatible flat-strip path

Keep both existing flat-strip renderers exactly as-is and gate them behind
`!isColumnAlignedFooter(group.footer)`. Only when `isColumnAlignedFooter` is true
do the sites switch to the new column-aligned rows. This guarantees the single-
column STD-area footers on the other templates are untouched.

## Ordered implementation steps

- [ ] 1. Make `GroupFooterItem.label` optional.
      What: change `label: string` to `label?: string` on `GroupFooterItem`.
      Files: `frontend-react/src/features/test-templates/models/testTemplate.types.ts`
      Verify: `npm run build` (from `frontend-react`) — `tsc -b && vite build`
      completes with no new type errors.

- [ ] 2. Add the shared footer-shape helper.
      What: create `groupFooter.ts` exporting `FooterRow`, `isColumnAlignedFooter`,
      and `groupFooterRows` exactly as specified above. Internal `hasLabel`
      treats `null`/`undefined`/`''` as unlabeled. `groupFooterRows` starts a new
      row at each labeled item and absorbs following unlabeled items; a run of
      unlabeled items before any label forms a `label: ''` row so nothing drops.
      Files: `frontend-react/src/features/test-templates/models/groupFooter.ts`
      Verify: `npm run build` from `frontend-react` succeeds (the module compiles
      and is tree-shaken until imported in step 3/4).

- [ ] 3. Rewrite `renderGroupFooter` in the live worksheet form to branch on shape.
      What: when `isColumnAlignedFooter(group.footer)` is false, render the
      EXISTING narrow label/value box UNCHANGED. When true, render a `<table>`
      (or `<tfoot>` appended to the existing data table) whose rows mirror the
      data columns: empty `#` cell, the row label under the first `visibleFields`
      column (`inj_label`), then one value cell per subsequent `visibleFields`
      column built from `groupFooterRows(...)[r].cells` in order, and an empty
      trailing cell when `canAddRows`. Reuse the current value formatting verbatim
      (`item.rounding` → `toFixed`, else `toPrecision(12)`, `item.unit` suffix,
      em-dash for blank, `preview.stale` ? `text-400` : `text-900 font-semibold`).
      Because `renderGroupFooter` is currently called AFTER the data `<table>`
      closes, the cleanest approach is a standalone `<table className="w-full"
      style={{ borderCollapse:'collapse', tableLayout: same-as-data }}>` that
      repeats the SAME column widths/count as the data table (compute the column
      list from the same `visibleFields` and `canAddRows` the group's render used
      — pass them into `renderGroupFooter`, or inline the footer render inside the
      group map where those consts are in scope). Prefer inlining into the group
      map so `visibleFields`, `canAddRows`, `veryWideTable`/`cellPad`, and
      `computed`/`preview.stale` are all in scope and the grid matches 1:1.
      Files: `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
      Verify: `npm run build` from `frontend-react` succeeds. Then manual UI check
      (deferred to the user per the workflow): open a TPL-A2-0004 worksheet and
      confirm Mean/SD/% RSD appear as three rows with each value under its compound
      column, label under the Injection column; confirm a single-column-footer
      template (e.g. an A2 assay STD-area table) still shows the old flat strip.

- [ ] 4. Update the preview `<tfoot>` to branch on the same shape.
      What: in the groups `.map` of `WorksheetPreviewPage.tsx`, when
      `isColumnAlignedFooter(footer)` is false keep the EXISTING single-`colSpan`
      flat strip UNCHANGED. When true, render one `<tr>` per `groupFooterRows`
      entry inside the `<tfoot>`: an empty/`#`-aligned cell, the label under
      `fields[0]`, then `<Placeholder />` cells (preview has no real values) under
      `fields[1..]`, one per row cell — the preview shows em-dash placeholders, so
      the value text is a `Placeholder`, but the LABEL and the per-column
      alignment are real so the skeleton reflects the true layout. Column count
      must equal `fields.length + 1` (its `colSpan` today), with NO trailing action
      column (preview has none).
      Files: `frontend-react/src/features/test-templates/pages/WorksheetPreviewPage.tsx`
      Verify: `npm run build` from `frontend-react` succeeds. Manual: open the
      TPL-A2-0004 template preview; the footer shows three labeled rows with
      placeholder cells aligned under each compound column header.

- [ ] 5. Confirm the print path needs no change and record it.
      What: no code change. `PrintWorksheetPage.tsx` renders no `<tfoot>` for
      multi-row groups, so footers never print today; column alignment there is
      moot. Add a one-line note in the task report (and optionally a code comment
      near the print table) stating the print path intentionally omits footers and
      is therefore out of scope for this change.
      Files: none (report note only; optional comment in
      `frontend-react/src/features/test-templates/pages/PrintWorksheetPage.tsx`).
      Verify: `grep`-free confirmation already done during planning —
      `PrintWorksheetPage` has no `<tfoot>`; re-confirm by reading the multi-row
      branch if a code comment is added, then `npm run build` succeeds.

## Verification summary

- Build command (only automated check available): from `d:\RD-instance\GIT\frontend-react`
  run `npm run build` (`tsc -b && vite build`). There is NO unit-test framework
  (no vitest/jest in `package.json`) and ESLint is not installed — do not rely on
  `npm run lint`. The TypeScript compile + Vite build is the pass/fail gate.
- Functional confirmation is a manual UI review by the user (per the original
  request "wait for me to review on UI"): TPL-A2-0004 `std_areas` and `bkt_areas`
  footers render as column-aligned rows; other templates' simple footers are
  visually unchanged.

## Scope guardrails

- Edit only: `testTemplate.types.ts`, new `groupFooter.ts`, `WorksheetForm.tsx`,
  `WorksheetPreviewPage.tsx` (and an optional comment in `PrintWorksheetPage.tsx`).
- Do NOT touch any template definition module, the DB, the calculation engine, or
  unrelated components. Detection is by footer data shape only — never by template
  code or field name.
