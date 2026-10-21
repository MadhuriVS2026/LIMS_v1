# Frontend verification — TPL-A2-0004 "Set 1 / Set 2" fixed blocks

## What changed

New generic, opt-in helper `src/features/test-templates/models/setBlocks.ts`:
- `isSetBlockGroup(group)` — true when a table group has a HIDDEN field keyed
  `cidx` AND has NO `set_no` field. This is exactly the shape left after the SET
  column was removed from `lipid_samples`: `cidx` survives (it drives the per-row
  compound selection and resets to 0 at each new SET) and the SET column is gone.
  It names NO template code and carries NO definition/DB flag.
- `setBlockSize(group, computedRows?)` — the block size is the detected `cidx`
  0-reset CYCLE LENGTH: the smallest row index > 0 at which computed `cidx`
  returns to 0 (only trusted when row 0's `cidx` is 0). When computed values are
  unavailable (the preview skeleton has none) or the cycle cannot be derived, it
  falls back to the documented fixed design value **4**.
- `setBlocksFor(rowCount, blockSize)` — consecutive blocks titled
  `Set {1-based index}` covering `[0, rowCount)`.

Applied consistently in all three render sites so live / preview / print match:
- `components/WorksheetForm.tsx` (live/editable form)
- `pages/PrintWorksheetPage.tsx` (print)
- `pages/WorksheetPreviewPage.tsx` (blank preview skeleton)

Each site: when `isSetBlockGroup(group)` is true, the group renders as one
sub-table per block, each preceded by a `Set N` sub-heading (`<h4>`) and carrying
its OWN repeated column header. Chosen layout: **column headers once PER BLOCK**
(each block is a self-contained small table). Rationale: a single shared header
above two visually separated blocks reads ambiguously, and per-block headers keep
each block intact for print pagination (print wraps each block in its own
`.ws-section`, which already has `break-inside: avoid`). The `#` row-number
column **restarts at 1 within each block** (1–4 per block) while cell lookups use
the ABSOLUTE row index, so values, calculated cells and editability are identical
to before — only the visual grouping changes.

The previously-added SET-column visual-merge code path is now dead for this
template (the column it keyed on, `set_no`, no longer exists). A repo-wide search
confirmed `models/columnMerge.ts` had no importers other than the three render
sites, so after rewiring those sites the file became globally unused and was
DELETED. No other template defined a `set_no` field, so nothing else referenced
it.

Block detection is driven PURELY by definition shape, never by template code.

## DOM reasoning — `lipid_samples` (TPL-A2-0004)

The `lipid_samples` group now has `rows {min:8,max:8}` and fields: hidden `cidx`,
`compound_name`, `lc`, `avg_weight`, `sample_weight`, `vol_j`, `pip_k`, `vol_l`,
`area`, `pct_assay`, `pct_mean` — and NO `set_no`. So `isSetBlockGroup` returns
true (hidden `cidx` present, `set_no` absent).

- Live form (`WorksheetForm`): `computed.rows.lipid_samples` carries evaluated
  `cidx` = 0,1,2,3,0,1,2,3 across the 8 rows, so `setBlockSize` detects the first
  return-to-0 at index 4 → block size 4 → `setBlocksFor(8,4)` yields
  `[{Set 1, 0..4}, {Set 2, 4..8}]`. The DOM is: a card titled "Sample Details",
  then `<h4>Set 1</h4>` + a `<table>` with the column header row (`#`, Compound
  Name, LC, Avg Weight, Sample Weight, Vol, Pip, Vol, Area, % Assay (%),
  % Mean (%)) and rows `#`=1..4; then `<h4>Set 2</h4>` + an identical `<table>`
  with rows `#`=1..4 bound to absolute rows 4..7. NO "SET" column header appears
  in either block. Because `max === min` (8), `canAddRows` is false → no Add/Remove
  Row controls and no trailing action column, exactly as intended for the pinned
  table. Inputs (avg_weight, sample_weight, vol_j, pip_k, vol_l, area) remain
  editable `renderInput` cells; compound_name/lc/pct_assay/pct_mean remain
  read-only `computedCell` cells — unchanged from before minus the dropped column.
- Preview page (`WorksheetPreviewPage`): no computed values, so `setBlockSize`
  falls back to 4 → 2 blocks of 4 blank placeholder rows, each with its own
  "Set N" caption and header; the (absent) footer renders once after the last
  block.
- Print page (`PrintWorksheetPage`): `rowsOf('lipid_samples')` returns the
  computed rows (with `cidx`), so block size detects 4 → two `.ws-section`
  tables, "Set 1" and "Set 2", header repeated per block, `#` restarting per
  block. The group label "Sample Details" prints once above the blocks.

Column alignment: every block renders the SAME `visibleFields` in the same order
through the SAME header/cell markup, so the two blocks' columns line up and match
the single-table layout used everywhere else.

## DOM reasoning — an unaffected plain-table template

`std_areas` / `bkt_areas` (also in TPL-A2-0004) and e.g. TPL-A6A/A6B dissolution
timepoint tables have NO hidden `cidx` field, so `isSetBlockGroup` returns false.
The `blocks` array is the single `[{title:'', 0..rows.length}]` fallback and the
title is empty, so no "Set N" `<h4>` is emitted and the group renders as ONE
table with one header and continuous `#` numbering — byte-identical markup to
before this change (the extracted `tableHead` / `renderRows` / `renderTable`
helpers produce the same nodes the inline JSX did). I confirmed by shape that
only `lipid_samples` carries a hidden `cidx`; every `standard` / `std_areas` /
`bkt_areas` and all other templates' tables lack it, so none opt in.

## Build

`npm run build` (`tsc -b && vite build`) from `frontend-react` → **exit 0**,
no TypeScript errors, no unresolved imports (the deleted `columnMerge.ts` has no
remaining importers). ESLint is not installed, per the plan it was not run. No
dev server was started.
