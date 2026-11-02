# Verification — Column-aligned worksheet table footers

Frontend-only change. No template definition, DB, or calculation-engine edits.

## What changed

1. `models/testTemplate.types.ts` — `GroupFooterItem.label` made optional
   (`label?: string`). Backward-compatible: every existing flat footer still
   supplies a label.
2. `models/groupFooter.ts` (new) — shared shape helper:
   - `isColumnAlignedFooter(footer)` → true iff the footer contains at least one
     UNLABELED item (`label` null/undefined/'').
   - `groupFooterRows(footer)` → groups a footer into `FooterRow[]`: a new row
     starts at each labeled item and absorbs the following unlabeled items until
     the next label/end. Leading unlabeled items form a `label:''` row so nothing
     is dropped.
   - Detection is by DATA SHAPE only — no template code or field name is ever
     referenced.
3. `components/WorksheetForm.tsx` — `renderGroupFooter` now branches on shape and
   receives `visibleFields`, `canAddRows`, `cellPad` from the group render so the
   footer grid mirrors the data table 1:1. Value formatting extracted to
   `footerValueText` and reused verbatim (rounding → toFixed, else
   toPrecision(12), unit suffix, em-dash for blank, `preview.stale` styling).
4. `pages/WorksheetPreviewPage.tsx` — the `<tfoot>` branches on the same shape;
   column-aligned footers render one `<tr>` per labeled group with placeholder
   cells under each compound column.
5. `pages/PrintWorksheetPage.tsx` — NOT changed. It renders no `<tfoot>` for
   multi-row groups (confirmed by grep: no `tfoot`/`footer`/`renderGroupFooter`),
   so footers never print today and column alignment there is moot / out of scope.

## Column-index mapping (the crux)

### Live form (`WorksheetForm.tsx`)
The data `<tbody>` builds columns as, left to right:
- index 0: leading `#` row-number column (always present),
- indices 1..N: one column per `visibleFields` entry (definition order, after
  `hidden` + per-worksheet `hiddenColumns` filtering),
- trailing action column, present only when `canAddRows` is true.

For A2-0004 `std_areas`/`bkt_areas`, `visibleFields` = `[inj_label, tri_area,
dppg_area, chol_area, depc_area]` (5 columns), and `canAddRows` is true for an
editable worksheet (`min:1, max:12`). The column-aligned footer row emits, in the
same order:

| rendered column | footer cell |
|---|---|
| `#` (index 0) | empty `<td>` |
| `visibleFields[0]` = `inj_label` | the ROW LABEL ("Mean"/"SD"/"% RSD") |
| `visibleFields[1]` = `tri_area` | `row.cells[0]` (the labeled item's value) |
| `visibleFields[2]` = `dppg_area` | `row.cells[1]` |
| `visibleFields[3]` = `chol_area` | `row.cells[2]` |
| `visibleFields[4]` = `depc_area` | `row.cells[3]` |
| trailing action col (canAddRows) | empty `<td>` |

So each footer row renders `1 (#) + 1 (label) + valueColumns.length (= visibleFields.slice(1) = 4) + 1 (action) = 7` cells, exactly matching the 7-cell data rows. Values map onto `visibleFields.slice(1)` by index; a cell missing a value renders an em-dash; extra values beyond the available compound columns are clamped (not rendered), per the definition-shape contract.

### Preview page (`WorksheetPreviewPage.tsx`)
Columns are `#` + `fields` (no trailing action column), colSpan today = `fields.length + 1`. The column-aligned footer row emits:
- `#` empty cell,
- label under `fields[0]`,
- one `<Placeholder />` per `fields.slice(1)` column that has a cell.

Cell count per row = `1 (#) + 1 (label) + fields.slice(1).length` = `fields.length + 1` = the old colSpan. No trailing action column (preview has none).

## Reasoned rendered output for BOTH shapes

### (1) A2-0004 `std_areas` footer — COLUMN-ALIGNED
`isColumnAlignedFooter` is true (the footer has unlabeled items). `groupFooterRows`
produces THREE rows from the 12-item footer:
- Row 0: label `"Mean"`, cells = [mean_std_tri, mean_std_dppg, mean_std_chol, mean_std_depc]
- Row 1: label `"SD"`, cells = [sd_std_tri, sd_std_dppg, sd_std_chol, sd_std_depc]
- Row 2: label `"% RSD"`, cells = [rsd_std_tri (unit %), rsd_std_dppg (%), rsd_std_chol (%), rsd_std_depc (%)]

Each renders as a `<tr>` in the live form with: empty `#` cell, the label in the
`inj_label` column position, then four value cells one under each of `tri_area`,
`dppg_area`, `chol_area`, `depc_area`, then an empty action cell. `bkt_areas` is
identical in shape using `*_pool_*` refs.

### (2) Simple 3-item all-labeled footer — FLAT STRIP (UNCHANGED)
A footer like `[{label:"Mean",ref}, {label:"SD",ref}, {label:"% RSD",ref}]` has no
unlabeled item, so `isColumnAlignedFooter` is false and the ORIGINAL flat-strip
renderer runs verbatim: the narrow `maxWidth: min(28rem,100%)` label/value box in
the live form, and the single-`colSpan` flex-wrap strip in the preview. Markup and
styling are byte-for-byte the previous behavior. ~15 other templates are
unaffected.

## Build

- Command run (from `d:\RD-instance\GIT\frontend-react`): `npm run build`
  (`tsc -b && vite build`).
- Result: **exit code 0**, zero TypeScript errors. Vite built 334 modules
  successfully. (The only warning is the pre-existing "chunk larger than 500 kB"
  size notice, unrelated to this change.)

## Tests

No unit-test framework is configured (`package.json` has no vitest/jest; ESLint is
not installed). Per the plan, NO test runner was added. Verification relies on the
TypeScript compile + Vite build gate and the explicit DOM-structure reasoning
above. Functional confirmation is a manual UI review by the user.

## Scope confirmation

`git status` shows only these footer-renderer files changed by this task:
- `frontend-react/src/features/test-templates/models/testTemplate.types.ts`
- `frontend-react/src/features/test-templates/models/groupFooter.ts` (new)
- `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
- `frontend-react/src/features/test-templates/pages/WorksheetPreviewPage.tsx`

No template definition, DB, or calculation-engine files were touched by this task.
(The working tree also shows a pre-existing, unrelated modification to
`backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` from the
earlier "remove (µV·s)" task — it was NOT made by this step and is deliberately
left unstaged and out of this commit.)

## Commit

- Commit hash: `6116222c1b694c6bf675ecbf9aacd149c89ab8e2`
  (local only — not pushed; caller handles release).
- 4 files changed, 222 insertions(+), 52 deletions(-).
