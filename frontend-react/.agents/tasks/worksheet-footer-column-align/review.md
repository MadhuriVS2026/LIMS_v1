# Column-aligned worksheet footers for TPL-A2-0004

This change teaches the two worksheet footer renderers (the live `WorksheetForm` and the read-only `WorksheetPreviewPage`) to render a footer as real table rows whose Mean/SD/%RSD values land directly under each compound column, instead of the flat label/value strip. It targets TPL-A2-0004's `std_areas` and `bkt_areas` groups, which are laid out injections-as-rows × compounds-as-columns. Selection is driven purely by footer data shape — a footer that contains an unlabeled item following a labeled one is treated as column-aligned — so no template code or field name is hardcoded in the frontend. A new `groupFooter.ts` helper carries the shape detection and row grouping; `GroupFooterItem.label` becomes optional to model the unlabeled per-compound cells.

Watch for: the column-aligned footer in the live form is rendered as a *separate* standalone `<table>` with `tableLayout: 'fixed'`, not a `<tfoot>` appended to the data table, so the footer's column widths are divided evenly and will not pixel-match the data table's column widths — cell count and order are correct but widths can drift visually (confirmed). Everything else checks out.

**Verdict**: APPROVED

## High-level view

The problem is solved one level up from the template: rather than adding an A2-specific renderer, the footer array's own shape decides the layout. `isColumnAlignedFooter` returns true only when at least one footer item has no label, and `groupFooterRows` folds the flat footer array into logical rows (each labeled item starts a row and absorbs the unlabeled items that follow). This generalizes to any future footer with the same shape without per-template branching.

The column mapping is the crux and it is correct. Both sites compute the value-column list from the same field array they used to build the data rows — the live form uses `visibleFields.slice(1)`, the preview uses `fields.slice(1)` — so the footer grid mirrors the data table one cell at a time: an empty `#` cell, the row label under the first field column (`inj_label`), then one value cell per subsequent compound column, plus a trailing action cell in the live form when rows are addable. Verified against the actual A2-0004 definition: the footer is Mean/SD/%RSD × four compound refs (tri/dppg/chol/depc) and `visibleFields` for these groups is `[inj_label, tri_area, dppg_area, chol_area, depc_area]`, giving an exact 4-values-into-4-columns match.

Backward compatibility is solid. A sweep of every template definition confirms only `a2_bupivacaine_lipid_ratio.py`'s two groups carry unlabeled footer items; the other ~15 footers label every item, so `isColumnAlignedFooter` is false for them and the original flat-strip branch runs verbatim. The flat-strip markup was preserved byte-for-byte (only lifted into an early-return branch) and the value-formatting logic was extracted into a `footerValueText` helper reused by both branches, so formatting cannot diverge between the two shapes.

The print path is untouched and correctly declared out of scope — `PrintWorksheetPage.tsx` renders no `<tfoot>`, so footers never print today and column alignment there is moot. The build evidence records `npm run build` (`tsc -b && vite build`) exiting 0 with zero TypeScript errors; the diff is small and type-consistent, so that evidence is credible and was not re-run. Scope is clean: exactly the four footer-renderer files in one local, unpushed commit.

<details>
<summary>Issues (1)</summary>

1. **Live-form footer width drift (non-blocking)** — the column-aligned footer in `WorksheetForm.tsx` is a standalone `<table tableLayout:fixed>` separate from the data table, so its even-split column widths won't exactly match the data table's widths; cell count/order are correct, only pixel alignment can drift. Acceptable for this pass; could be tightened later by appending a real `<tfoot>` to the data table or sharing explicit column widths. Confirm during the manual UI review.

</details>

<details>
<summary>Details</summary>

## Shape-based detection, not template matching

`groupFooter.ts` makes the whole feature hinge on one predicate: `isColumnAlignedFooter(footer)` is true iff some item has no non-empty label. `groupFooterRows` then walks the flat array and starts a new `FooterRow` at each labeled item (or at the very first item if it is unlabeled, via the `current === null` guard), pushing following unlabeled items into the current row's `cells`. A leading run of unlabeled items becomes a `label: ''` row so nothing is silently dropped. No template code, group key, or field key appears anywhere in the helper or its two callers' branch conditions — the selection is entirely data-driven, satisfying the shape-detection requirement.

This was checked against reality rather than assumed. The A2-0004 definition's `std_areas` footer is:

```
{label:"Mean", ref:tri} {ref:dppg} {ref:chol} {ref:depc}
{label:"SD",   ref:tri} {ref:dppg} {ref:chol} {ref:depc}
{label:"% RSD",ref:tri,unit:%} {ref:dppg,unit:%} {ref:chol,unit:%} {ref:depc,unit:%}
```

so `groupFooterRows` yields exactly three rows of four cells. A grep across all `template_definitions/*.py` confirms every other footer (a1_assay, a2_a3_content, a2_lyso_content*, a6_dissolution, _common.py) labels every item, so those stay on the flat branch.

## Column-index mapping mirrors the data table

The data `<tbody>` row in the live form renders `#` + one `<td>` per `visibleFields` entry + an optional action `<td>` when `canAddRows`. The footer row emits the same sequence:

```
 #     inj_label   tri    dppg   chol   depc   [action]
┌────┬───────────┬──────┬──────┬──────┬──────┬────────┐
│    │  "Mean"   │  v0  │  v1  │  v2  │  v3  │        │   row.cells → visibleFields.slice(1)
└────┴───────────┴──────┴──────┴──────┴──────┴────────┘
```

`valueColumns = visibleFields.slice(1)` and `row.cells[c]` are indexed together, so the labeled item's value sits under the first compound column and each trailing unlabeled value under the next. Missing cells render an em-dash; extra values beyond the available columns are clamped by the `valueColumns.map` bound. The preview page does the same with `fields.slice(1)` and no action column, and its row cell count equals `fields.length + 1`, matching the existing `colSpan`. Because each site derives its column list from the identical array used to build its data rows, alignment cannot drift between header, body, and footer.

## Formatting extracted, not duplicated

The per-value formatting (honor `rounding` → `toFixed`, else `toPrecision(12)`, append `unit`, em-dash for blanks, `preview.stale` styling) was pulled out of the old inline flat-strip loop into `footerValueText` and is now called from both the flat branch and the column-aligned branch. This removes the risk of the two shapes formatting the same value differently, and the flat-strip branch is otherwise the original markup unchanged.

## Live-form footer is a separate table

The one caveat worth a reviewer's eye: in the live form the column-aligned footer is its own `<table className="w-full" style={{borderCollapse:'collapse', tableLayout:'fixed'}}>` rendered after the data table closes, not a `<tfoot>` inside it. `tableLayout: fixed` divides width evenly across its cells, so the footer's columns won't necessarily line up pixel-for-pixel with the data table's columns (which use the data table's own fixed/auto layout and per-column widths). The logical mapping — which value is under which compound — is correct; only visual width alignment can differ. The preview page avoids this because its footer rows live inside the same `<table>` as the data rows. This is non-blocking and flagged for the manual UI pass.

## Print path out of scope

`PrintWorksheetPage.tsx` was not modified and renders no footer for multi-row groups, so footers never print and column alignment there does not apply. The plan and verification both record this, matching the requirement that Print either behave consistently or be explicitly noted as not rendering footers.

## Build and scope

The recorded evidence shows `npm run build` (`tsc -b && vite build`) exiting 0 with zero TypeScript errors and the only warning being the pre-existing chunk-size notice. The diff is small, and the single type change (`label?: string`) is backward compatible, so the evidence is credible; the full build was not re-run per instruction. The commit `6116222` contains exactly the four footer-renderer files (`testTemplate.types.ts`, new `groupFooter.ts`, `WorksheetForm.tsx`, `WorksheetPreviewPage.tsx`), is local only (not in `origin/MadhuriWorktree`), and the one unrelated modified file in the tree — `a2_bupivacaine_lipid_ratio.py` from the earlier µV·s task — is correctly left unstaged and out of this commit. No template/DB/engine changes, no stray source files.

## File map

- `models/testTemplate.types.ts` — `GroupFooterItem.label` made optional to model unlabeled per-compound cells.
- `models/groupFooter.ts` (new) — `isColumnAlignedFooter` shape test + `groupFooterRows` row grouping; data-shape only.
- `components/WorksheetForm.tsx` — `renderGroupFooter` branches on shape; column-aligned path renders a standalone footer table mirroring the data columns; `footerValueText` extracted and shared.
- `pages/WorksheetPreviewPage.tsx` — `<tfoot>` branches on the same shape; column-aligned footers render one `<tr>` per labeled group with placeholder cells per compound column.

Full diff: `git -C d:\RD-instance\GIT show 6116222c1b694c6bf675ecbf9aacd149c89ab8e2`

</details>
