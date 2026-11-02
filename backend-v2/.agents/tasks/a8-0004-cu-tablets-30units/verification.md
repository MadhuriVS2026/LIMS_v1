# Verification — A8-0004 Content Uniformity by HPLC, 30 units ("CU-tablets-30units")

First iteration (no `review.json` present). Implemented from the plan and task.

## Identity / chosen code
- Template code: **TPL-A8-0004** (confirmed free in live DB; existing A8 rows were
  TPL-A8-0001 Inactive v1 + Active v2, TPL-A8-0002 Active, TPL-A8-0003 Draft).
- Archetype: A8. result_unit: AV.
- Test: **TST-CU-30U**, name EXACTLY **CU-tablets-30units**, type Quantitative
  (created via `ensure_test`; TST-CU / TST-CUWV NOT reused).
- New module: `backend-v2/scripts/template_definitions/a8_cu_tablets_30units.py`,
  registered in `__init__.py` as `*_A8_CU30` immediately after `*_A8`.

## Reuse (verbatim logic)
- AV arithmetic: `_ACCEPTANCE_VALUE` imported UNCHANGED from
  `a8_content_uniformity` (upper bound outermost, lower bound inside) via the
  reused `_summary_group("units")`; `_cu_criteria("units")` imported too. The
  parity test asserts the summary AV field's expression `is` the imported
  `_ACCEPTANCE_VALUE` object.
- Standard + replicate + statistics: `_common` helpers (`standard_group`,
  `replicate_area_group(default_rows=5)`, `standard_statistics_group`,
  `sst_rsd_criterion`, `context_header`, `standard_chain_terms`,
  `dilution_fields`) exactly as A8_HPLC uses them.
- Bracketing + pooled %RSD: A12-0001 pattern — `bkt_1`/`bkt_2` tables
  (rows {min:0,max:6,default:0}, single area field) + `stats.rsd_bkt =
  rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))` + blocking SST criterion
  NMT 2.0 %.
- Differences from A8_HPLC (only these): `units` rows {min:1,max:30,default:30};
  `k_value` default 2.0 (USP <905> k for n=30). per-unit `pct_lc` expression
  identical to A8_HPLC.

## MANDATORY DB backup
- Backup filename: **lims.db.bak-cu30-20261024-144055**
- Size match: orig 1363968 bytes == backup 1363968 bytes (match=True).

## seed --validate-only
- Command: `python -m scripts.seed_test_templates --validate-only`
- Exit code: **0**. Output includes:
  `ok   TPL-A8-0004 [A8] 7 groups, 17 inputs, 4 area fields, 13 calculated, 4 criteria`

## Parity test
- File: `backend-v2/tests/calculation/test_a8_0004_cu30_parity.py`
- `python -m pytest tests/calculation/test_a8_0004_cu30_parity.py -q` → **9 passed**.
- Covers: units rows default==30 and max==30; k_value default==2.0; identity
  (code/archetype/result_unit/test_code/test_name); AV nesting with two
  hand-derived cases evaluated through `summary.acceptance_value`:
  - CENTRED (mean 100.0 in [98.5,101.5]): AV == k·s == 2.0·0.8305 → **1.7**.
  - OFF-CENTRE LOW (mean 97.0 < 98.5): AV == (98.5−97.0)+2.0·0.8305 → **3.2**
    (reversed nesting would drop the 1.5 gap — this guards the order).
  - AV expression identity (`is` the imported `_ACCEPTANCE_VALUE`).
  - pooled bracketing %RSD == hand-derived `rsd(pool(...))`.
  - criteria present with correct limits: `sst_std_rsd` (stats.rsd_std, lte 2.0,
    blocking), `sst_bkt_rsd` (stats.rsd_bkt, lte 2.0, blocking),
    `acceptance_value` (summary.acceptance_value, lte 15.0, blocking),
    `unit_count` (count(units.pct_lc), gte 10, advisory).
  - empty-evaluate: no blocking failure, blank reportable.

## Seed into live DB
- `python -m scripts.seed_test_templates` exit 0; logged `ok TPL-A8-0004 ...`
  then `add` on first run with `+ Test Master: TST-CU-30U — CU-tablets-30units`.
- Post-seed verification (throwaway script, since deleted):
  - Exactly ONE `TPL-A8-0004` row, status **Active**, version 1, archetype A8,
    result_unit AV.
  - Bound test: `TST-CU-30U` / name `CU-tablets-30units` (exact).
  - Stored definition **byte-equal** to the module: `dict == dict` True AND
    canonical-JSON (`sort_keys=True, separators=(',',':')`) equal True.
  - Counts: templates 37→38, tests 34→35 — only TPL-A8-0004 and TST-CU-30U
    added, no other row disturbed.

## Full calculation suite
- `python -m pytest tests/calculation -q` → **5 failed, 811 passed in 43.41s**.
- The 5 failures are EXACTLY the known pre-existing/unrelated ones, unchanged:
  - `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_unit1_release_carryover`
  - `::test_per_timepoint_summary`
  - `::test_amount_remaining`
  - `test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`
  - `test_worksheet_service.py::test_a_qa_correction_reopens_and_republishes_the_result`
- The new parity module passes; no OTHER new failures (passed count rose with the
  new cases).

## Cleanup
- Throwaway scripts (`_tmp_check.py`, `_tmp_derive.py`, `_tmp_verify.py`) deleted.
- Staged for commit: the new module, the `__init__.py` edit, the new parity test
  only. `lims.db` and the backup remain gitignored / unstaged.

## Commit
- Commit hash: **9ee1fed57232b06fcdf5c128eaf0a4654a6162da** (local only; NOT pushed).
- `git log -1 --stat` shows exactly 3 files: `__init__.py` (+2),
  `a8_cu_tablets_30units.py` (new, 178), `test_a8_0004_cu30_parity.py` (new, 189).
