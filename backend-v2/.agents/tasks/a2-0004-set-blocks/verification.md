# Verification — TPL-A2-0004 "Set 1 / Set 2" fixed blocks (first iteration)

Scope: ONLY the "Sample Details" (`lipid_samples`) section of TPL-A2-0004.
The in-table SET column (`set_no`) was removed; the frontend renders the group
as two fixed labeled blocks ("Set 1" over rows 1–4, "Set 2" over rows 5–8),
each an identical 4-compound table. No other section, formula, SST criterion,
`standard`/`std_areas`/`bkt_areas`/`stats`/context, or any gold value changed.

## Backend changes

Module `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`:
- Deleted the entire `set_no` field dict from `_lipid_sample_fields()` (the
  auto-label column). `set_no` fed no formula — it was referenced only by its own
  definition and the (now-removed) frontend merge heuristic — so removing it is
  inert to the calculation chain.
- Kept hidden `cidx` and everything else byte-identical (compound_name, lc,
  avg_weight/sample_weight/vol_j/pip_k/vol_l, area, pct_assay, pct_mean).
- Pinned `lipid_samples.rows` → `{min:8, max:8, default:8}` (fixed 2 SETs × 4).
- Pinned `drug_lipid.rows` → `{min:2, max:2, default:2}`.
- Updated the `_lipid_sample_fields()` docstring and the `lipid_samples` /
  `drug_lipid` group comments to describe the fixed 2-SET, SET-as-heading layout
  with no `set_no` column. No `expression` string changed. `drug_lipid` indexing
  `(rowno-1)*4 + idx` is unaffected (rows 1–4 = SET 1, 5–8 = SET 2).

Parity test `tests/calculation/test_a2_0004_tabular_parity.py`:
- Dropped `"set_no"` from `_PREP` and `DRUG_LIPID` (now-undefined input keys).
- Updated the module docstring to the fixed-8-row / no-`set_no` shape and the
  `drug_lipid` reads `lipid_samples.pct_mean[...]`. All gold assertions unchanged.

## Backend verification results

- `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q`
  → **9 passed**. Reproduces the gold values:
  - Standard conc (ppm): Tricaprylin 118.92, DPPG 54.03, Cholesterol 285.1, DEPC 489.25.
  - Pooled Tricaprylin mean 8699733.9, %RSD 0.2383.
  - SET 1 %Assay: 99.98 / 86.20 / 101.77 / 100.39 (unrounded, rounds to gold).
  - Each row's %Mean == its %Assay.
  - Drug/Lipid ratio chain: tri_mgml 1.99958, sum_lipid 15.790645,
    mgml_bupi 13.2867, ratio 0.841429; `reportable_result` 0.841429.
  - `has_blocking_failure is False`.
- `python -m scripts.seed_test_templates --validate-only` → **exit 0**,
  "All definitions valid." TPL-A2-0004 now reports 37 calculated fields
  (was 38; one fewer = the removed `set_no`).
- `TemplateDefinition.parse(json.loads(json.dumps(D)))` then
  `WorksheetEvaluator(...).evaluate({}, {})` on the module def → prints `ok`
  (parses from canonical JSON and evaluates blank with no error).
- DB sync: `python -m scripts.update_a2_0004_definition` → "1 row updated;
  identity preserved: id=35 archetype=A2 version=1 status=Active test_id=32".
  Re-read row 35 asserts BOTH exact-bytes (`raw == json.dumps(module.definition)`)
  AND normalized (`json.loads(raw) == module.definition`) equality, and that
  `"set_no"` no longer appears in the stored JSON → prints
  `db==module exact+normalized, set_no gone`.
- `python -m pytest tests/calculation -q` → **5 failed, 762 passed**. The 5
  failures are the SAME KNOWN pre-existing unrelated ones and NO new failures:
  - `TestA6BDissolutionWithReplacement::test_unit1_release_carryover`
  - `TestA6BDissolutionWithReplacement::test_per_timepoint_summary`
  - `TestA6BDissolutionWithReplacement::test_amount_remaining`
  - `test_worksheet_service::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`
  - `test_worksheet_service::test_a_qa_correction_reopens_and_republishes_the_result`
  (3× A6B dissolution + 2× worksheet_service; none touch A2-0004.)

The DB sync script `scripts/update_a2_0004_definition.py` is a pre-existing
committed tool and was reused as-is (no edit). No throwaway scripts were created
or left behind.

## Frontend

See `frontend-react/.agents/tasks/a2-0004-set-blocks/verification.md`.
