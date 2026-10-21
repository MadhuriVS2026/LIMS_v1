# Verification — TPL-A2-0004 "Sample Details" tall per-SET restructure

## Backup (mandatory first action)
- Command: `Copy-Item lims.db lims.db.bak-a2sampletall-<ts>` then size compare.
- Backup filename: **lims.db.bak-a2sampletall-20261021-122215**
- Byte size match: orig 1298432 == bak 1298432 -> equal=True

## DB row 35 identity (before any change)
- `select id,code,archetype,version,status,test_id from test_templates where id=35`
  -> `(35, 'TPL-A2-0004', 'A2', 1, 'Active', 32)`
- Current stored definition byte-equal to OLD module def: True

---

## Commands run and results

### 1. Module parse + run empty worksheet
`python -c "... TemplateDefinition.parse(d); WorksheetEvaluator(p).evaluate({},{}) ..."`
-> `parses+runs empty OK`

### 2. A2-0004 parity test (rewritten for tall layout)
`python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q`
-> `8 passed in 0.20s`

### 3. GOLD %Assay — SET 1 (abs=1e-2 confirms 2-dp sheet gold)
Inputs: Avg Weight 1.0050, Sample Weight 1.5008, Vol(vol_j) 25, Pip(pip_k) 1,
Vol(vol_l) 1; areas Tri 8729574 / DPPG 3826195 / Chol 32474189 / DEPC 44235393.
Reproduced per-row `pct_assay`:
- row 0 Tricaprylin: 99.979 -> **99.98** ✓
- row 1 DPPG Na:     86.200 -> **86.20** ✓
- row 2 Cholesterol: 101.772 -> **101.77** ✓
- row 3 DEPC:        100.390 -> **100.39** ✓
cidx = 0/1/2/3, compound_name = Tricaprylin/DPPG Na/Cholesterol/DEPC,
lc = 2 / 0.9 / 4.7 / 8.2 (mirrored from lc_<c>).

### 4. Unchanged gold still holds
- Std conc: Tri 118.92 / DPPG 54.03 / Chol 285.1 / DEPC 489.25 ✓
- std_areas means: Tri 8691453.5 (and dppg/chol/depc) ✓
- pooled Tri mean 8699733.9, %RSD 0.2383 ✓
- drug_lipid chain from SET-1 fixture: tri_mgml 1.99958, sum_lipid 15.790645,
  mgml_bupi 13.2867, ratio 0.841429, reportable 0.841429; has_blocking_failure
  False ✓ (flows from repointed index into unrounded pct_assay)

### 5. Full calculation suite
`python -m pytest tests/calculation -q`
-> `5 failed, 761 passed in 28.75s`
The 5 failures are the SAME known pre-existing unrelated failures, NO new ones:
- test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_unit1_release_carryover
- test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_per_timepoint_summary
- test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_amount_remaining
- test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf
- test_worksheet_service.py::test_a_qa_correction_reopens_and_republishes_the_result

### 6. Seeder validate-only
`python -m scripts.seed_test_templates --validate-only`
-> exit 0; `ok TPL-A2-0004 [A2] 6 groups, 20 inputs, 9 area fields, 36 calculated, 8 criteria`
`All definitions valid.`  (EXITCODE=0)

### 7. DB sync script created + import-check
`python -c "... import scripts.update_a2_0004_definition as m ..."` -> `import OK True`

### 8. DB sync + byte-equality
`python -m scripts.update_a2_0004_definition`
-> `1 row updated` / `identity preserved: id=35 archetype=A2 version=1 status=Active test_id=32`
Byte-equality (exact `stored == json.dumps(module_def)`): **byte-equal: True**

### 9. Live-DB end-to-end gold re-check (reads stored row 35 JSON)
`python -c "... parse row-35 definition, evaluate SET-1 fixture ..."`
-> `live-DB pct_assay (2dp): [99.98, 86.2, 101.77, 100.39]`
-> `live-DB ratio: 0.841429 blocking: False`
-> `LIVE DB GOLD RE-CHECK PASS`

## Identity (after)
- id=35, code=TPL-A2-0004, archetype=A2, version=1, status=Active, test_id=32 — UNCHANGED.

## Files changed (scope)
- `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` — `_lipid_sample_fields`
  full rewrite to tall per-SET; `lipid_samples` group rows -> {min 4, max 16, default 8};
  `_drug_lipid_fields` `<c>_mgml` repointed to `lipid_samples.pct_assay[(rowno-1)*4+idx]`,
  drug_lipid rows -> {min 1, max 8, default 2}; docstrings updated. `standard`, `std_areas`,
  `bkt_areas`, `stats`, context header and the 8 SST criteria untouched.
- `tests/calculation/test_a2_0004_tabular_parity.py` — fixture + asserts updated for tall.
- `scripts/update_a2_0004_definition.py` — new DB sync script (modelled on A6B).
- `lims.db` row 35 definition (gitignored; local only).

## Commit
- Commit hash: (recorded below)

