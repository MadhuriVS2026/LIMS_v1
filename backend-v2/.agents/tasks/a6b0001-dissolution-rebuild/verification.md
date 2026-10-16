# Verification — TPL-A6B-0001 rebuild (Doxorubicin, with replacement, whole vial, 12 units)

Formula-exact rebuild of the stored definition of template row `TPL-A6B-0001`
(id=7, archetype A6b, version 1, status Active, test_id=12) to reproduce
`Test types/Dissolution sheet_with replacement_whole vial_ QC release_12 units_Doxo.xlsx`.

## What was done

1. Rebuilt `A6B_DEFINITION` in `scripts/template_definitions/a6_dissolution.py`
   to the 12-unit Doxorubicin structure: standard prep (chain 100/5/50/5/10,
   potency 100, Std Conc = ROUND(…,3)); 5-replicate standard table with
   Mean=AVERAGE and %RSD=TRUNC5; up-to-24 bracketing standards pooled via
   `pool(std_areas.area, bkt.area)` with pooled Mean=TRUNC1 and %RSD=TRUNC5;
   STD-1/STD-2 co-relation block (`std1_mean/std2_mean * std2_weight/std1_weight`);
   System Suitability singleton (items 1-3 text, item 4 = replicate %RSD, item 5 =
   pooled %RSD); test-preparation singleton (7 volumes); gravimetric weights with
   units-as-columns (Filled/Empty/Net per 12 units + Mean/Min/Max); `release`
   SEQUENCE group reproducing the sheet's `% Content` table with the cumulative
   WITH-replacement carry-over
   `content_n = base_n + coalesce(prev.content_n, 0) * withdrawal/total`, hidden
   `base_n` helper columns, and per-timepoint Mean/SD/%RSD/Min/Max over the 12
   visible unit columns; `amount` table reproducing the `% Release` table
   (`number(pct_assay) - release.content_n[rowno-1]`) with the same summary; and a
   "Graphical data" singleton carrying a group-level `chart` object mirroring
   TPL-A6A-0004 (sourceGroup `release`, x=time_hr, 12 unit series + Mean,
   defaultSeries `["mean"]`). `resultRef = "release.mean"`.
2. Directly updated the stored `definition` JSON of the `TPL-A6B-0001` row in
   `backend-v2/lims.db` via `python -m scripts.update_a6b_definition`
   (`1 row updated`, identity columns preserved). Stored JSON equals the source
   module dict by construction (confirmed equal).

## Safety

- Backup confirmed present before writing:
  `backend-v2/lims.db.bak-a6b0001-20261016-122436`.
- Only the `TPL-A6B-0001` row was changed. Confirmed the sole row with
  `modified_by='a6b-rebuild'` is `TPL-A6B-0001`; `id=7`, `archetype=A6b`,
  `version=1`, `status=Active`, `test_id=12` unchanged. No Test rows touched.
- Re-validated the stored JSON via `TemplateDefinition.parse` + dry-run evaluate:
  `python -m scripts.seed_test_templates --validate-only` →
  `ok TPL-A6B-0001 [A6b] 14 groups, 48 inputs, 16 area fields, 71 calculated, 1 criteria`,
  exit 0.

## Gold-value gate (loaded from the DB row, run through the real engine)

Command: `python -m scripts._verify_a6b_gold` (throwaway; deleted after). It loads
the stored TPL-A6B-0001 definition from `lims.db`, feeds the sheet inputs
(standard chain 100/5/50/5/10 potency 100; replicate areas 1299388/1284245/
1289430/1289886/1287196; bracketing 1289948, 1317112; corel STD-1 1299388/1284245/
1289430, STD-2 1281451/1286859, STD-2 weight 30.02; test_prep 1/600/610/3/6/10/10;
12 filled/empty weights from sheet rows 41/42; sample areas rows 47-51 across 12
units; context label_claim "2", pct_assay 99.6, wt_per_ml 1.0313), runs the
evaluator, and asserts each gold value.

Unit-1 raw areas fed (sheet col B, rows 47-51):
0.5hr=1227280, 3hr=1136967, 7hr=940328, 24hr=447679, 48hr=143975.
Unit-1 net weight = 21.9327 − 11.1039 = 10.8288 g.

Computed vs expected (all PASS):

| Check | Computed | Expected | Result |
|---|---:|---:|---|
| Std Conc (ppm) | 15.05500 | 15.055 | PASS |
| Replicate Mean | 1290029.00000 | 1290029 | PASS |
| Replicate %RSD | 0.44098 | 0.44098 | PASS |
| Pooled bracketing %RSD | 0.86913 | 0.86913 | PASS |
| STD Co-Relation | 1.00234 | 1.00234 | PASS |
| Unit-1 %release 0.5hr | 83.20692 | 83.2069 | PASS |
| Unit-1 %release 3hr | 78.44795 | 78.4479 | PASS |
| Unit-1 %release 7hr | 65.03823 | 65.0382 | PASS |
| Unit-1 %release 24hr | 31.41787 | 31.4179 | PASS |
| Unit-1 %release 48hr | 10.27624 | 10.2762 | PASS |
| 0.5hr Mean | 85.49774 | 85.4977 | PASS |
| 0.5hr SD | 1.45576 | 1.4558 | PASS |
| 0.5hr %RSD | 1.70269 | 1.7027 | PASS |
| 0.5hr Min | 82.91242 | 82.9124 | PASS |
| 0.5hr Max | 87.67125 | 87.6712 | PASS |
| 3hr Mean | 77.49444 | 77.4944 | PASS |
| 7hr Mean | 64.88466 | 64.8847 | PASS |
| 24hr Mean | 34.35786 | 34.3579 | PASS |
| 48hr Mean | 10.14276 | 10.1428 | PASS |
| Amount 0.5hr Unit-1 | 16.39308 | 16.3931 | PASS |
| Amount 0.5hr Mean | 14.10226 | 14.1023 | PASS |

`21/21 passed — RESULT: ALL PASS` (exit 0).

## Regression tests

- `python -m pytest tests/calculation/test_seeded_template_parity.py -q` →
  244 passed (includes the rewritten `TestA6BDissolutionWithReplacement` class and
  the four catalogue-wide invariants against the new A6B definition).
- `python -m pytest tests/calculation -q` → 752 passed, 2 failed.
  The two failures are
  `test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`
  and `::test_a_qa_correction_reopens_and_republishes_the_result`. These are
  PRE-EXISTING and unrelated to this change: they use an in-memory A1 stand-in
  template (not the DB file, not A6B) and fail identically on the baseline with
  this task's two tracked edits stashed (verified: `2 failed` with stash applied).
  The failures are a worksheet-lifecycle locking assertion, not a calculation
  regression. `test_dissolution_a6a_release.py` (TPL-A6A-0004 guard) passed
  untouched.

## Notes

- Sheet/brief naming: the sheet titles rows 59-63 "% Content" and rows 67-71
  "% Release"; the user brief calls them "%RELEASE" and "AMOUNT-REMAINING"
  respectively. Group keys follow the brief: `release` = the computed content
  (Unit-1 0.5hr = 83.2069), `amount` = %Assay − release (16.3931). Documented in a
  comment in the source module.
- Min/Max span: implemented over the full 12 visible unit columns. For the 0.5hr
  row this coincides with the sheet's `MIN(B59:G59)/MAX(B59:G59)` (82.9124 /
  87.6712 are the overall 12-unit extremes at 0.5hr), which is what the gate pins.
- Release/content fields carry no rounding (full precision on the sheet). Rounding
  appears only where the sheet uses it: Std Conc (ROUND 3), replicate/pooled %RSD
  (TRUNC 5), pooled mean (TRUNC 1).
