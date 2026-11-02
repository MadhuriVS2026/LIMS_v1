# Verification — TPL-A2-0004 transpose std_areas / bkt_areas to injection-rows × compound-columns

First iteration (no `review.json` present). Implemented from scratch per `plan.md`.

## Backup (mandatory first action)

```
Copy-Item lims.db -> lims.db.bak-a2areas-transpose-20261019-224718
Source size: 1290240   Backup size: 1290240   Match: True
```

Backup file: `backend-v2/lims.db.bak-a2areas-transpose-20261019-224718`.

## What changed

- `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
  - Removed `_INJ_COLUMNS` / `_injection_columns()` / `_inj_list()`; added
    `_MAX_INJ_ROWS=12`, `_DEFAULT_INJ_ROWS=6`, and `_area_columns()` (four
    compound AREA columns `tri_area/dppg_area/chol_area/depc_area`, each with
    `labelFrom="standard.name[<idx>]"`).
  - `_std_area_fields()` / `_bkt_area_fields()` now return
    `[inj_label, *_area_columns()]` (injections-as-rows / compounds-as-columns,
    no per-row compound/inj_1..6/mean/sd/rsd).
  - `_stats_fields()` SOURCE expressions moved to per-column aggregates —
    `mean(std_areas.<c>_area)` etc., and `mean(pool(std_areas.<c>_area,
    bkt_areas.<c>_area))` for the pooled BKT stats. KEYS / labels / units
    UNCHANGED.
  - `std_areas` / `bkt_areas` group dicts: `rows {min:1, max:12, default:6,
    labelFrom:"inj_label"}`; footer has one `ref` per compound column for
    Mean / SD / % RSD (std → `stats.*_std_*`, bkt → `stats.*_pool_*`).
  - Module docstring + inline group comments corrected to describe the new
    orientation, footer-per-column aggregates, pooling, and decisions D1–D8.
- `backend-v2/tests/calculation/test_a2_0004_tabular_parity.py`
  - `STD_AREAS` / `BKT_AREAS` fixtures transposed to injection-row dicts
    (STD 6 rows, BKT 4 rows). Same gold numbers.
  - `test_std_area_column_means` / `test_bkt_pooled_tricaprylin` /
    `test_stats_indirection_still_resolves` now read `result.values["stats.*"]`
    (the per-row `mean`/`rsd` fields no longer exist). Gold values unchanged.
- `backend-v2/lims.db` row id 35 `definition` column only (direct ORM UPDATE,
  not the approve/e-sign flow, not a re-seed).

## Commands run and results

### seed --validate-only (exit 0)
```
python -m scripts.seed_test_templates --validate-only
...
All definitions valid. --validate-only, so nothing was written.
exit=0
```

### Direct evaluate of an empty worksheet (builds clean)
```
WorksheetEvaluator(TemplateDefinition.parse(json.loads(json.dumps(D)))).evaluate({}, {})
-> evaluate ok; reportable= EMPTY blocking= False
```

### Parity test — all gold values reproduce (7/7)
```
python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q
7 passed in 0.15s
```
Gold values asserted and reproduced to the sheet's rounding:
- Std Conc (ppm): Tri 118.92, DPPG 54.03, Chol 285.1, DEPC 489.25
- std_areas per-compound Mean (column aggregate): Tri 8691453.5, DPPG 4461370.5,
  Chol 32403414.83, DEPC 44013385.5
- pooled (bkt) Tri Mean 8699733.9, %RSD 0.2383
- Batch EP20_117-299-B %Assay: 99.979, 86.200, 101.772, 100.390
- Drug/Lipid batch: mg/mL Tri 1.99958, Sum of Lipid 15.790645,
  mg/mL Bupivacaine 13.2867, Ratio 0.841429
- has_blocking_failure = False

### Full calculation suite — 5 known pre-existing failures unchanged
```
python -m pytest tests/calculation -q
5 failed, 760 passed in 35.35s
```
The 5 failures are the SAME pre-existing, unrelated ones (A6B dissolution +
worksheet_service), not caused by this change:
- test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_unit1_release_carryover
- test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_per_timepoint_summary
- test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_amount_remaining
- test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf
- test_worksheet_service.py::test_a_qa_correction_reopens_and_republishes_the_result

### DB row 35 byte-for-byte parity + identity
```
python -c "import sqlite3,json; from scripts.template_definitions.a2_bupivacaine_lipid_ratio import LIPID_RATIO_DEFINITION as D; ..."
exact True
normalized True
identity (35, 'TPL-A2-0004', 1, 'Active')
```

## Scope (git status)

Tracked changes limited to the two intended source files:
```
 M backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py
 M backend-v2/tests/calculation/test_a2_0004_tabular_parity.py
```
`backend-v2/lims.db` is gitignored (binary artifact; row 35 updated in place,
same as prior edits in this project). Throwaway update script removed. No
frontend, engine, `_common.py`, or other-template changes.

## Commit

Local commit (not pushed): `7e3e270053634fde066b83df3f00476a8df6837f`
