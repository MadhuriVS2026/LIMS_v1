# Implementation Plan — TPL-A2-0004 "Set 1 / Set 2" fixed blocks

Change ONLY the "Sample Details" section (`lipid_samples` group) of template
**TPL-A2-0004** so that:

1. the in-table **SET column (`set_no`) is REMOVED**, and
2. the frontend renders `lipid_samples` as **two fixed labeled blocks** — a
   "Set 1" heading above compound rows 1–4 and a "Set 2" heading above rows 5–8
   — each block an identical 4-compound table.

Fixed **2 sets, fixed 4 compounds per set**. Every other group, formula, the 8
SST criteria, `standard`, `std_areas`, `bkt_areas`, `stats`, context, and the
`drug_lipid` math stay byte-identical. Gold values MUST reproduce exactly and
the live DB row (test_templates id 35) MUST end byte-for-byte equal to the
source module.

---

## Decisions made in this plan (grounded in the code read)

- **D-A. Remove `set_no` outright (not hide it).** The task says remove the
  column entirely. `set_no` feeds no formula (confirmed: it is referenced
  nowhere except its own definition and the frontend merge heuristic). Removing
  it is safe for the calculation chain. `drug_lipid` indexes
  `lipid_samples.pct_mean[(rowno-1)*4 + idx]`, which is positional and unaffected
  by dropping `set_no`.
- **D-B. Keep `cidx` (hidden).** `cidx = (rowno-1) mod 4` still selects each
  row's compound via `_compound_select` for `compound_name`, `lc`, `pct_assay`.
  It is already `hidden: true`, so it never renders as a column. It becomes the
  **block-boundary signal** for the frontend (a new block starts when `cidx`
  resets to 0). This is why we keep it rather than deleting it.
- **D-C. Pin to exactly 2 sets.** `lipid_samples.rows` → `{min:8, max:8,
  default:8}` (8 rows = 2 SETs × 4 compounds). `drug_lipid.rows` → `{min:2,
  max:2, default:2}` (one row per SET). Add Row / Remove Row controls disappear
  automatically in `WorksheetForm` because `canAddRows = max > min` becomes
  false for both groups.
- **D-D. Block detection is a generic, opt-in frontend rule — NOT keyed to the
  template code.** A new `models/setBlocks.ts` helper decides, purely from the
  definition shape, whether a table group renders as labeled "Set N" blocks:
  the group has a **hidden `cidx` field** AND does **not** have a `set_no` field.
  When it applies, block size is the detected `cidx` cycle length (the row count
  where `cidx` first returns to 0; here 4), and each block is titled
  `Set {1-based blockIndex}`. If `cidx`'s computed values are unavailable to the
  renderer (e.g. preview page, which has no computed values), fall back to row
  index modulo the detected cycle length, defaulting the cycle to 4 when it
  cannot be derived. This generalises to any future "N sets of M compounds"
  table without naming the template.
- **D-E. Column headers render ONCE PER BLOCK.** Each "Set N" block is its own
  small 4-row table with its own header row. This is the cleaner aligned layout:
  a single shared header above two visually separated blocks reads ambiguously
  on paper, and per-block headers keep each block self-contained for print
  pagination (`break-inside: avoid` already wraps each `.ws-section`). The
  "Set N" caption sits as a sub-heading directly above each block's header row.
- **D-F. Retire the `set_no` visual-merge path for this template, keep the util
  for safety.** With `set_no` gone, `shouldMergeColumn` (keys on `set_no` +
  sibling `cidx`) can no longer match TPL-A2-0004 — its merge branch becomes
  dead for this template. The util `columnMerge.ts` is referenced by all three
  render sites and keys on a field literally named `set_no`; no other template
  defines a `set_no` field (verified by grep — only TPL-A2-0004's module used
  it), so the branch is now globally unreachable. We will **remove the
  `columnMerge` wiring from the three render sites and delete `columnMerge.ts`**
  because it is now entirely unused (see item 9's verification: a repo-wide
  search must return no remaining importers before deletion). If any importer
  outside these three sites is found, we instead leave `columnMerge.ts` intact
  and only stop the `lipid_samples` column from reaching it (which it already
  can't, since the column is gone). Scope boundary below reasons about other
  templates.

### Scope boundary (what must NOT change)

- **Backend:** no change to `standard`, `std_areas`, `bkt_areas`, `stats`,
  `context`, the 8 SST `criteria`, `resultRef`, `SeedTemplate` header, or any
  formula string. Only: delete the `set_no` field dict; change two `rows`
  specs; update docstrings/comments; the frontend render.
- **Frontend:** the new set-block rendering is **opt-in by shape** and must not
  change any plain-table template. Reason about **TPL-A6A-0004 Dissolution
  "Timepoints For Sample"** (a plain multi-row table with no `cidx` field): the
  new helper's gate (`has hidden cidx AND no set_no`) is false for it, so it
  renders exactly as today — one header, numbered rows, no "Set" sub-headings.
  The same is true for every `std_areas`/`bkt_areas` table (they have
  `inj_label` + area columns, no `cidx`) and the `standard` table. Only
  `lipid_samples` carries a hidden `cidx`, so only it opts in.

---

## Ordered implementation items

> Base branch is green; each item leaves the tree buildable. Backend items 1–4
> are independent of the frontend items 5–9 except that the parity test (item 3)
> and the DB sync (item 4) must run against the edited module (item 1–2).

- [ ] **1. Remove `set_no` and pin `lipid_samples` to 2 SETs in the source module.**
      In `_lipid_sample_fields()` delete the entire `set_no` field dict (the
      first entry, `"key": "set_no"` … `"expression": "trunc((rowno - 1) / 4, 0) + 1"`)
      and its preceding comment block. Keep `cidx` (hidden) and every other
      field byte-identical. In `LIPID_RATIO_DEFINITION`, change the
      `lipid_samples` group `rows` from `{"min": 4, "max": 16, "default": 8}` to
      `{"min": 8, "max": 8, "default": 8}`.
      Files: `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
      Verify: deferred to item 3 (parity test) + item 4b (seed validate).

- [ ] **2. Pin `drug_lipid` to 2 SETs and refresh docstrings/comments.**
      Change the `drug_lipid` group `rows` from `{"min": 1, "max": 8,
      "default": 2}` to `{"min": 2, "max": 2, "default": 2}`. Update the
      `_lipid_sample_fields()` docstring and the `lipid_samples` group comment to
      describe the **fixed 2-SET layout with SET rendered as a heading (no
      `set_no` column)**: the SET is now a frontend heading over each 4-row
      block keyed off the hidden `cidx`, columns are Compound Name, LC, Avg
      Weight, Sample Weight, Vol, Pip, Vol, Area, % Assay, % Mean. Leave the
      `(rowno-1)*4 + idx` indexing note intact (rows 1–4 = SET 1, 5–8 = SET 2).
      Do NOT alter any `expression` string.
      Files: `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
      Verify: deferred to item 3.

- [ ] **3. Update the parity test for the removed SET column and run it.**
      In `test_a2_0004_tabular_parity.py`: remove `"set_no"` from the `_PREP`
      dict and remove `"set_no": "1"` from the `DRUG_LIPID` row (these keys are
      now undefined input fields; the evaluator ignores unknown keys, but drop
      them to keep the fixture honest). Keep `test_set1_row_compound_selection`
      asserting `cidx`/`compound_name`/`lc` (unchanged — `cidx` survives). All
      gold assertions stay as-is.
      Files: `backend-v2/tests/calculation/test_a2_0004_tabular_parity.py`
      Verify (from `d:\RD-instance\GIT\backend-v2`):
      `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q`
      — all 8 tests pass, reproducing the gold values in the checklist below.

- [ ] **4. Validate the whole catalogue still parses + runs, then confirm the
      module evaluates empty.**
      No file change — this is the backend gate before touching the DB.
      Files: none.
      Verify (from `d:\RD-instance\GIT\backend-v2`):
      (a) `python -m scripts.seed_test_templates --validate-only` — exit 0,
          "All definitions valid."
      (b) `python -c "import json; from scripts.template_definitions.a2_bupivacaine_lipid_ratio import LIPID_RATIO_DEFINITION as D; from src.domain.services.calculation.template_schema import TemplateDefinition; from src.domain.services.calculation.evaluator import WorksheetEvaluator; WorksheetEvaluator(TemplateDefinition.parse(json.loads(json.dumps(D)))).evaluate({}, {}); print('ok')"`
          — prints `ok` (parses from canonical JSON and evaluates blank with no error).

- [ ] **5. Sync the edited module into live DB row 35 (byte-for-byte), via the
      existing sync script.**
      Reuse `scripts/update_a2_0004_definition.py` as-is (it loads
      `BUPI_LIPID_RATIO.definition`, UPDATEs the `definition` JSON of the
      `TPL-A2-0004` row, asserts id/code/archetype/version/status/test_id
      unchanged). It writes via sqlite directly to `lims.db`. If a reviewer
      requires the ORM path specified in the task, the equivalent is: load
      `BUPI_LIPID_RATIO.definition`, set `TestTemplateModel` row id 35
      `.definition = json.dumps(module_def)`, commit. Either way the stored
      string must equal `json.dumps(BUPI_LIPID_RATIO.definition)`. Delete any
      throwaway script created; do NOT leave scratch files.
      Files: run `backend-v2/scripts/update_a2_0004_definition.py` (no edit
      expected); DB `backend-v2/lims.db` row id 35.
      Verify (from `d:\RD-instance\GIT\backend-v2`):
      (a) `python -m scripts.update_a2_0004_definition` — prints
          "1 row updated" and "identity preserved: id=35 …".
      (b) Canonical-JSON equality re-read:
          `python -c "import json,sqlite3; from scripts.template_definitions.a2_bupivacaine_lipid_ratio import BUPI_LIPID_RATIO as T; c=sqlite3.connect('lims.db'); row=c.execute('select id,definition from test_templates where code=?',('TPL-A2-0004',)).fetchone(); assert row[0]==35; got=json.loads(row[1]); assert got==T.definition, 'DB != module'; assert 'set_no' not in json.dumps(got); print('db==module, set_no gone')"`
          — prints `db==module, set_no gone`.
      (A `lims.db.bak-a2setblocks-*` backup already exists from the setup step.)

- [ ] **6. Add the generic, opt-in set-block detection helper.**
      Create `models/setBlocks.ts` exporting:
      - `isSetBlockGroup(group: GroupDef): boolean` — true when the group has a
        field with `key === 'cidx' && hidden` AND no field with `key === 'set_no'`.
        (Documented: this is the shape left behind after the SET column was
        removed; `cidx` is the per-row compound index that resets to 0 at each
        new SET.)
      - `setBlockSize(group, computedRows?): number` — the cycle length: the
        smallest row index > 0 where `cidx` returns to 0 using
        `computedRows[i].cidx`; when computed rows are unavailable (preview) or
        the cycle can't be derived, return **4** (the fixed design value) as the
        documented fallback.
      - `setBlocksFor(rowCount, blockSize): {title, startRow, endRow}[]` —
        consecutive blocks titled `Set {1-based index}` covering `[0, rowCount)`.
      Pattern-match the style of `models/columnMerge.ts` and `models/groupFooter.ts`
      (frontend-only shape heuristic, no DB/definition flag, JSDoc explaining
      why it cannot match a plain table). Block detection documented in the file
      header exactly as D-D above.
      Files: `frontend-react/src/features/test-templates/models/setBlocks.ts`
      Verify: compiles as part of item 9's `npm run build`.

- [ ] **7. Render `lipid_samples` as "Set 1"/"Set 2" blocks in `WorksheetForm.tsx`.**
      In the table-group branch, when `isSetBlockGroup(group)` is true, instead
      of one `<tbody>` of all rows, emit one sub-section per block from
      `setBlocksFor(rows.length, setBlockSize(group, computed.rows?.[group.key]))`:
      a small `Set N` sub-heading (e.g. an `<h4>`/caption styled like the card
      sub-labels) followed by a table carrying the **same `<thead>`
      (visibleFields, minus the removed SET column — which no longer exists) and
      only that block's rows** (slice `startRow..endRow`). Keep per-row inputs,
      calculated cells, editability gating, and `renderGroupFooter` exactly as
      today (footer renders once after the last block, or is absent here since
      `lipid_samples` has no footer). Preserve the `#` row-number column
      numbering within each block (1–4 per block reads cleaner; document the
      choice — restart per block). Remove the `columnMerge` precompute/continuation
      code from this group's render.
      Files: `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
      Verify: item 9 build + manual reasoning; the group with `max==min` shows no
      Add/Remove Row controls (expected for the pinned 2-set table).

- [ ] **8. Mirror the block rendering in the print and preview pages.**
      Apply the same `isSetBlockGroup` branch in:
      - `pages/PrintWorksheetPage.tsx` — for a set-block group, render one
        `<h4>Set N</h4>` + `<table class="ws-table">` per block (header repeated
        per block), slicing `rowsOf(group.key)` by block. Keep `.ws-section`
        wrapping so each block stays together on the page.
      - `pages/WorksheetPreviewPage.tsx` — same, using `rowCount(group)` for the
        blank skeleton: emit `ceil(rows / blockSize)` blocks (2 blocks of 4 blank
        rows) each with its own header and `Set N` caption. Preview has no
        computed values, so `setBlockSize` falls back to 4 (documented).
      Remove the now-dead `columnMerge` wiring (the `shouldMergeColumn` precompute
      and `isMergedContinuation` branch) from both files for the `lipid_samples`
      path. All three sites must render the two blocks identically (same columns,
      same per-block headers, same "Set N" captions).
      Files: `frontend-react/src/features/test-templates/pages/PrintWorksheetPage.tsx`,
      `frontend-react/src/features/test-templates/pages/WorksheetPreviewPage.tsx`
      Verify: item 9 build.

- [ ] **9. Remove the now-unused `columnMerge.ts` (only if globally unused) and build.**
      Search the repo for any remaining importer of `columnMerge`
      (`shouldMergeColumn`, `isMergedContinuation`, `normalizeMergeValue`). After
      items 7–8 the only importers were the three render sites. If the search
      returns no importers, delete `models/columnMerge.ts`. If any other importer
      exists, leave the file and its imports in those other sites untouched
      (the `lipid_samples` column is gone regardless, so no template merges it).
      Files: `frontend-react/src/features/test-templates/models/columnMerge.ts`
      (delete if unused); the three render-site imports.
      Verify (from `d:\RD-instance\GIT\frontend-react`):
      (a) `npm run build` (`tsc -b && vite build`) — exits 0, no TS errors, no
          unresolved imports. (ESLint is not installed; do not run `npm run lint`.)
      (b) Confirm no dangling imports:
          grep the three render sites show no `columnMerge` imports remain for the
          `lipid_samples` path (and none at all if the file was deleted).

---

## Gold-value verification checklist (must reproduce exactly)

Run via item 3's parity test (`CONTEXT` = lc_tri 2 / lc_dppg 0.9 / lc_chol 4.7 /
lc_depc 8.2 / lc_bupi 13.3). Expected:

- **Standard conc (ppm), rounded 2 dp:** Tricaprylin **118.92**, DPPG **54.03**,
  Cholesterol **285.1**, DEPC **489.25**.
- **Pooled Tricaprylin mean** `stats.mean_pool_tri` = **8699733.9**;
  `stats.rsd_pool_tri` = **0.2383** (%RSD).
- **SET 1 % Assay** per compound row (rounds to): Tricaprylin **99.98**,
  DPPG **86.20**, Cholesterol **101.77**, DEPC **100.39**.
- **% Mean == % Assay** for each of the 4 SET-1 rows (single injection).
- **Drug/Lipid ratio** `drug_lipid.ratio` row 0 = **0.841429**; and
  `reportable_result == 0.841429`.
- No blocking SST failure on this data (`has_blocking_failure is False`).

## DB-update procedure (summary)

1. Backup already present (`lims.db.bak-a2setblocks-*`).
2. `python -m scripts.update_a2_0004_definition` (writes module→row 35, asserts
   identity columns unchanged).
3. Re-read row 35 and assert `json.loads(definition) == BUPI_LIPID_RATIO.definition`
   and that `"set_no"` no longer appears in the stored JSON.

## Generic block-detection rule (summary)

A table group renders as "Set N" blocks iff it has a **hidden `cidx` field** and
**no `set_no` field**. Block size = the `cidx` 0-reset cycle length from computed
rows, falling back to **4** when computed values are absent (preview) or the
cycle cannot be derived. Blocks are consecutive, titled `Set {1-based index}`,
each with its own repeated column header. No template code appears in the rule;
plain tables (no `cidx`) never opt in.

## Build / test commands (confirmed during exploration)

- Backend parity: `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q`
  (cwd `backend-v2`).
- Backend validate: `python -m scripts.seed_test_templates --validate-only`
  (cwd `backend-v2`) — exit 0.
- Backend evaluate-empty + DB equality: the one-liners in items 4 and 5.
- Frontend: `npm run build` (cwd `frontend-react`) = `tsc -b && vite build`.
  ESLint is NOT installed (no local eslint despite the `lint` script); do not run
  it. No dev servers are to be started.
