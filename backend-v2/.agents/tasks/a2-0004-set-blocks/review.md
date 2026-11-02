# TPL-A2-0004 Sample Details rendered as fixed Set 1 / Set 2 blocks

The change removes the in-table SET column from the GxP template TPL-A2-0004 and renders its `lipid_samples` "Sample Details" group as two fixed "Set N" labeled blocks (Set 1 over rows 1–4, Set 2 over rows 5–8), each an identical 4-compound table. Backend drops the `set_no` field outright, keeps the hidden `cidx` compound index, pins `lipid_samples` to 8 rows and `drug_lipid` to 2 rows, and repoints the `drug_lipid` mg/mL reads from the old `<c>_mean[rowno-1]` onto `lipid_samples.pct_mean[(rowno-1)*4 + idx]`. Frontend adds a generic, shape-driven `setBlocks.ts` helper (opt-in when a group has a hidden `cidx` and no `set_no`), wires it into all three render sites, and deletes the now-unused `columnMerge.ts`. Every gold value, formula, SST criterion, and untouched group is preserved, and the live DB row 35 was re-synced to equal the module.

Watch for: nothing blocking. The `update_a2_0004_definition.py` sync also writes `modified_by`/`modified_date` on row 35 (confirmed), which is expected book-keeping and does not touch the `definition` JSON the task pins — the coder's re-read asserts exact + normalized `definition` equality (confirmed via evidence). The untracked `.agents/` files in `git status` are artifacts of other tasks, not stray temp files from this one (confirmed).

**Verdict**: APPROVED

## High-level view

The backend edit is surgical and well-scoped: the module diff touches only the module docstring, the `_lipid_sample_fields`/`_drug_lipid_fields` builders, and the two `rows` specs inside `LIPID_RATIO_DEFINITION`. `_assay_expression`, `_stats_fields`, the `standard`/`std_areas`/`bkt_areas` groups, the `stats` singleton and the 8 SST criteria are all outside the diff hunks, so they are byte-identical. The `set_no` field dict is deleted entirely (not hidden), and no formula ever referenced it, so the calculation chain is inert to its removal. `cidx` survives as a hidden field and now also serves as the frontend's block-boundary signal.

The gold chain is preserved by construction. The only arithmetic-adjacent change is the `drug_lipid` index repoint from `lipid_samples.<c>_mean[rowno-1]` to `lipid_samples.pct_mean[(rowno-1)*4 + idx]`; because single-injection `pct_mean == pct_assay` (both unrounded) and the tall layout places tri/dppg/chol/depc at offsets 0..3 of each 4-row SET block, the row-0 reads reproduce the same values as the old wide layout. The parity test was updated to the tall fixture shape with every gold assertion unchanged, and the coder's run reports all of them reproducing (99.98/86.20/101.77/100.39; ratio 0.841429; std conc 118.92/54.03/285.1/489.25; pooled Tri mean 8699733.9, %RSD 0.2383).

Block detection is generic and opt-in. `isSetBlockGroup` keys purely on definition shape — a hidden `cidx` field present AND no `set_no` field — never on the template code, and `setBlockSize` derives the cycle length from the computed `cidx` 0-resets with a documented fallback to 4 when computed values are absent (preview). The same branch is applied identically across `WorksheetForm`, `PrintWorksheetPage`, and `WorksheetPreviewPage`, and plain tables fall through to a single unnamed block spanning all rows, so their markup is unchanged.

The dead SET-merge path was removed cleanly. With `set_no` gone, `columnMerge.ts` had no reachable match; a repo-wide search confirms zero remaining importers, so the file was deleted and all three render sites were rewired off it. Row pinning (`lipid_samples` 8/8/8, `drug_lipid` 2/2/2) makes `max == min`, which suppresses the Add/Remove Row controls as intended.

<details>
<summary>Issues (0)</summary>

No blocking or actionable concerns. All checklist items are satisfied.

</details>

<details>
<summary>Details</summary>

## SET column removal and the hidden `cidx` carry-over

`_lipid_sample_fields()` deletes the entire `set_no` field dict (the old `trunc((rowno-1)/4,0)+1` auto-label column) and its comment. A repo-wide `set_no` search returns only comment text and the `isSetBlockGroup` exclusion check — no field named `set_no` exists anywhere in the module or frontend. `cidx` remains as a hidden calculated field (`rowno - 1 - trunc((rowno - 1) / 4, 0) * 4`), which the parity test's `test_set1_row_compound_selection` asserts yields 0/1/2/3 across the first SET. Because `set_no` fed no formula, its removal is inert to the calculation chain — confirmed by the diff showing no expression string referencing it and by the gold values reproducing unchanged.

## Drug/Lipid index repoint

The one substantive formula edit is in `_drug_lipid_fields`:

```
- "expression": f"lipid_samples.{prefix}_mean[rowno - 1] * lc_{prefix} / 100",
+ "expression": (
+     f"lipid_samples.pct_mean[(rowno - 1) * 4 + {idx}] "
+     f"* lc_{prefix} / 100"
+ ),
```

The old wide layout stored one `<c>_mean` column per compound and read it at `[rowno-1]` (one batch per row). The tall layout stores a single `pct_mean` column where SET n occupies rows `(n-1)*4 .. (n-1)*4+3` and compound `idx` (tri 0, dppg 1, chol 2, depc 3) sits at offset `idx`. For `drug_lipid` row 0 (SET 1, `rowno==1`) the index is `0*4 + idx == idx`, reading rows 0..3 — the same four `%Mean` values the old layout produced. Single injection makes `pct_mean == mean([pct_assay]) == pct_assay`, both unrounded, so the gold ratio chain (tri_mgml 1.99958, sum_lipid 15.790645, mgml_bupi 13.2867, ratio 0.841429) is reproduced exactly. The parity test's `test_drug_lipid_ratio_chain` keeps these assertions verbatim.

## Generic opt-in block detection

`setBlocks.ts` gates on shape, not template code:

```
const hasHiddenCidx = fields.some((f) => f.key === 'cidx' && f.hidden === true);
const hasSetNo = fields.some((f) => f.key === 'set_no');
return hasHiddenCidx && !hasSetNo;
```

`setBlockSize` detects the cycle length from the computed `cidx` 0-resets (only trusted when row 0's `cidx` is 0) and falls back to the documented `DEFAULT_BLOCK_SIZE = 4` when computed rows are absent — the preview path, which has no evaluated values. `setBlocksFor` emits consecutive `Set {1-based}` blocks and keeps a trailing partial block so no row is dropped. No plain table defines a hidden `cidx`, so only `lipid_samples` opts in; the coder's reasoning that `std_areas`/`bkt_areas`/`standard` and other-template dissolution timepoint tables (no `cidx`) fall through to the single-block `[{title:'', 0..rows.length}]` path holds, and the empty title suppresses any "Set N" heading for them.

## Three render sites aligned

`WorksheetForm.tsx` factors the header into a shared `tableHead` and the body into `renderRows(start,end)`, then maps `blocks` to one captioned table each, with the footer rendered once after the last block. The `#` column restarts at 1 per block while cell lookups use the absolute `rowIndex = startRow + localIndex`, so values, calculated cells, and editability are unchanged — only the visual grouping changes. `PrintWorksheetPage.tsx` renders the group label once then one titled `.ws-section` table per block (keeping `break-inside: avoid` page behavior), and `WorksheetPreviewPage.tsx` produces 2 blocks of 4 blank rows via the fallback size with the footer gated to the last block. All three import the same helper and share the single-block fallback for plain tables, so non-SET groups render identically to before.

## Row pinning and control suppression

`lipid_samples.rows` moved from `{min:4,max:16,default:8}` (note: the live base was `{min:1,max:8,default:3}` in the diff's `-` line) to `{min:8,max:8,default:8}`, and `drug_lipid.rows` to `{min:2,max:2,default:2}`. With `max == min`, `canAddRows` is false in the form, so the Add/Remove Row controls and the trailing action column disappear — exactly the fixed-2-SET intent.

## columnMerge removal

With `set_no` gone, the `columnMerge` visual-merge path could no longer match. A repo-wide search for `columnMerge`/`shouldMergeColumn`/`isMergedContinuation`/`normalizeMergeValue` returns zero matches, and the file is deleted in commit `906b76f`. Removing a globally-unused util rather than leaving dead wiring is the right call and keeps the three render sites clean.

## Verification evidence (not re-run)

The coder's notes record: parity test 9 passed with every gold value reproduced; `seed_test_templates --validate-only` exit 0 ("All definitions valid", A2-0004 now 37 calculated fields, one fewer = removed `set_no`); evaluate-empty prints `ok`; DB sync re-reads row 35 asserting BOTH `raw == json.dumps(module.definition)` and `json.loads(raw) == module.definition` with `set_no` absent; full `pytest tests/calculation` = 5 failed / 762 passed, the 5 being the known pre-existing A6B dissolution (3) and worksheet_service (2) failures, none touching A2-0004; `npm run build` exit 0, no TS errors, no dangling `columnMerge` import. The diff and these records are internally consistent; no articulable doubt justified a spot-check.

</details>

<details>
<summary>File map</summary>

- `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` — removed `set_no`, kept hidden `cidx`, pinned `lipid_samples` 8/8/8 and `drug_lipid` 2/2/2, repointed `drug_lipid` mg/mL onto `pct_mean[(rowno-1)*4+idx]`, refreshed docstrings/comments.
- `backend-v2/tests/calculation/test_a2_0004_tabular_parity.py` — updated fixtures to the tall no-`set_no` shape; added `cidx`/`pct_mean` assertions; all gold assertions unchanged.
- `frontend-react/src/features/test-templates/models/setBlocks.ts` — new generic opt-in set-block helper (shape heuristic, cycle detection, fallback 4).
- `frontend-react/src/features/test-templates/components/WorksheetForm.tsx` — per-block rendering with shared header/row factories; plain tables unaffected.
- `frontend-react/src/features/test-templates/pages/PrintWorksheetPage.tsx` — per-block `.ws-section` tables under group label.
- `frontend-react/src/features/test-templates/pages/WorksheetPreviewPage.tsx` — per-block blank skeleton with footer on last block.
- `frontend-react/src/features/test-templates/models/columnMerge.ts` — deleted (globally unused after SET column removal).
- `backend-v2/scripts/update_a2_0004_definition.py` — reused as-is to sync module → DB row 35.

Full diff: `git diff 6fc824e..HEAD`

</details>
