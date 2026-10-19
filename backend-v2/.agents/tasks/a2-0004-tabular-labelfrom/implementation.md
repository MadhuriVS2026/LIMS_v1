# Implementation evidence — TPL-A2-0004 tabular transpose + generic `labelFrom`

First iteration (no `review.json` present). Implemented exactly per `plan.md`.

## Files changed (tracked)
- `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
  - `std_areas` and `bkt_areas` transposed to **compounds-as-ROWS**: a
    `compound` cell (`mirrorFrom: "standard.name"`, read-only), six `inj_1..inj_6`
    area columns, and per-row `mean`/`sd`/`rsd`.
    - `std_areas` stats: `mean([inj_1..inj_6])`, `sd(...)`, `rsd(...)`.
    - `bkt_areas` stats: POOLED with the matching std row by `rowno - 1`, e.g.
      `mean(pool([std_areas.inj_1[rowno - 1], ...], [inj_1, ...]))`.
    - `rows`: `{min:1, max:10, default:4, labelFrom:"compound"}` for both.
  - `stats` singleton rewired to read the row tables by compound index
    (`std_areas.mean[idx]` / `bkt_areas.rsd[idx]`, etc.). Every `stats.*` KEY is
    unchanged, so `lipid_samples` %Assay and the 8 SST criteria are untouched.
  - `labelFrom: "standard.name[idx]"` applied to `lipid_samples` per-compound
    columns (`<c>_area1/area2/assay1/assay2/mean`, tri=0/dppg=1/chol=2/depc=3)
    and to `drug_lipid` `<c>_mgml` columns.
- `frontend-react/src/features/test-templates/models/testTemplate.types.ts`
  - Added `labelFrom?: string` to `FieldDef` (doc comment: UI-only dynamic header
    text, counterpart to `mirrorFrom`).
- `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
  - Added generic `resolveLabelFrom(spec, rowIndex)` + `headerText(field, rowIndex)`
    helpers. Parses `"<group>.<field>"` with optional `[idx]`; reads
    `computed.rows[group][idx][field]` (fallback to editable `values`), trims,
    returns `null` when blank. Applied at the three header render sites (table
    `<th>`, singleton editable `<label>`, singleton calculated `<label>`), each
    falling back to `field.label ?? field.key`. Fully generic — only consulted
    when `field.labelFrom` is set, so templates without it render unchanged.
- `backend-v2/tests/calculation/test_a2_0004_tabular_parity.py` (new)
  - Hand-derived GxP parity test from the workbook dump; 7 cases, all pass.

## DB sync (step 9)
- Fresh backup made: `backend-v2/lims.db.bak-a2areas-20261019201840`.
- Row `code='TPL-A2-0004'` (id 35, v1, Active) `definition` UPDATEd to
  `json.dumps(LIPID_RATIO_DEFINITION)` (SQLAlchemy JSON default serialization).
- Verified: `json.loads(stored) == LIPID_RATIO_DEFINITION` (structural) AND
  `stored == json.dumps(LIPID_RATIO_DEFINITION)` (byte-for-byte) → `True`.
- Re-parsed the DB row, dry-ran, and re-asserted the gold targets from the DB
  definition (not just the module): all pass.
- Throwaway sync/dry-run scripts deleted.

## Verification run (so the reviewer need not re-run)
- Backend validate (parse + empty dry-run, all 24 templates):
  `python -m scripts.seed_test_templates --validate-only` → exit 0;
  `TPL-A2-0004 [A2] 6 groups, 24 inputs, 20 area fields, 50 calculated, 8 criteria`.
- New parity test: `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q`
  → `7 passed`.
- Full suite: `python -m pytest tests/calculation -q` → `5 failed, 760 passed`.
  The 5 failures are PRE-EXISTING and unrelated to this task:
  `TestA6BDissolutionWithReplacement::{test_unit1_release_carryover,
  test_per_timepoint_summary, test_amount_remaining}` (TPL-A6B-0001) and
  `test_worksheet_service::{test_a_different_analyst_cannot_enter_results_on_an_assigned_trf,
  test_a_qa_correction_reopens_and_republishes_the_result}`. Confirmed by
  `git stash`-ing the A2-0004 module edit and re-running the same 5 tests — they
  fail identically with the edit removed (none reference TPL-A2-0004).
- Frontend TS build (authoritative static check; eslint not installed):
  `cd frontend-react && npm run build` (`tsc -b && vite build`) → exit 0, zero TS
  errors. The ">500 kB chunk" note is a pre-existing advisory, not a failure.

## Gold values reproduced (dry-run + parity test)
- `standard.conc_ppm`: 118.92 / 54.03 / 285.1 / 489.25
- `std_areas.mean`: 8691453.5 / 4461370.5 / 32403414.83 / 44013385.5
- `bkt_areas.mean[0]` 8699733.9, `bkt_areas.rsd[0]` ≈ 0.2383
- `stats.mean_std_tri == std_areas.mean[0]`; `stats.rsd_pool_tri` ≈ 0.2383
- Batch EP20_117-299-B %Assay inj1: tri 99.979 / dppg 86.200 / chol 101.772 / depc 100.390
- drug_lipid: `tri_mgml` 1.99958, `sum_lipid` 15.790645, `mgml_bupi` 13.2867, `ratio` 0.841429

## Scope
Only TPL-A2-0004 (module + DB row id 35) and the three frontend files changed.
No other template/Test touched. Not committed — the finalize step commits.
