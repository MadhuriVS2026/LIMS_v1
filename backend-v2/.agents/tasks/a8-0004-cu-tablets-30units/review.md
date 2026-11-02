# 30-unit Content Uniformity (by HPLC) seed template — TPL-A8-0004 / "CU-tablets-30units"

A new fresh module, `a8_cu_tablets_30units.py`, adds a USP <905> stage-2 (30-unit) content-uniformity-by-HPLC template bound to a brand-new Test Master entry `TST-CU-30U` / `CU-tablets-30units`. The approach is "build fresh, reuse logic verbatim": the Acceptance-Value arithmetic, summary group and CU criteria are imported from the existing `a8_content_uniformity` module (the literal same objects), the standard/replicate/statistics scaffolding comes from `_common`, and the bracketing + pooled-%RSD suitability block is lifted from the A12-0001 pattern. The only deliberate deviations from A8_HPLC are the two the task demanded: `units` defaults to 30 rows and `k_value` defaults to 2.0 (the n=30 acceptability constant). A parity test hand-derives the gold AV for a centred and an off-centre-low batch plus the pooled bracketing %RSD, and the template was seeded Active with its stored definition byte-equal to the module.

Watch for: nothing blocking. The AV nesting is reused by import (byte-identical by construction) — **confirmed**. The commit is local-only on branch `MadhuriWorktree` and contains exactly the three in-scope files — **confirmed**.

**Verdict**: APPROVED

## High-level view

The Acceptance Value is the one place a mistake would be catastrophic, and it is handled the safest possible way: `_ACCEPTANCE_VALUE`, `_summary_group` and `_cu_criteria` are imported unchanged from `a8_content_uniformity`, so the nested `IF` (upper bound outermost, lower bound inside) is the same string object A8_HPLC uses. The parity test asserts object identity (`is _ACCEPTANCE_VALUE`) and independently proves the nesting with an off-centre-low case where a reversed order would drop the `(98.5 − mean)` gap.

The standard block, five-replicate injection table (with its `stats.mean_std`/`sd_std`/`rsd_std` footer) and the statistics singleton are the `_common` helpers used exactly as A8_HPLC uses them, so `stats.mean_std` — the divisor in every per-unit `pct_lc` — keeps its key and meaning. The bracketing suitability is the A12-0001 shape reproduced faithfully: `bkt_1`/`bkt_2` tables with `{min:0,max:6,default:0}` and a single area field each, a pooled `rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))` field, and a blocking NMT 2.0 % criterion on it.

The identifiers are clean: TPL-A8-0004 is the next free A8 code, archetype A8, result_unit AV, and the test is created fresh as `CU-tablets-30units` rather than reusing TST-CU or TST-CUWV. The template was seeded Active, the DB backed up first, and only TPL-A8-0004 and TST-CU-30U were added. The commit holds exactly the module, its `__init__` registration and the parity test, and is not pushed.

<details>
<summary>Issues (0)</summary>

No blocking or actionable concerns. All criteria in the review brief were confirmed.

</details>

<details>
<summary>Details</summary>

### AV nesting reused by import, not re-typed

The single most important check passes by construction. `a8_cu_tablets_30units` imports `_ACCEPTANCE_VALUE`, `_cu_criteria` and `_summary_group` from `a8_content_uniformity` and builds the summary via `_summary_group("units")`, so the AV expression in the stored definition is the literal same object as A8_HPLC's — **confirmed** by reading both modules. The source string is unchanged:

```
if(mean_pct < 101.5,
   if(mean_pct < 98.5, (98.5 - mean_pct) + k_value * sd_pct, k_value * sd_pct),
   (mean_pct - 101.5) + k_value * sd_pct)
```

The parity test guards this two ways: `test_av_expression_is_the_a8_hplc_object` asserts the summary field's expression `is _ACCEPTANCE_VALUE`, and `test_off_centre_low_case_adds_lower_bound_gap` evaluates a mean of 97.0 through the template and asserts AV == `(98.5 − 97.0) + 2.0·s` == 3.2, which a reversed (upper-inner) nesting would compute wrongly by dropping the 1.5 gap. The centred case (mean 100.0) asserts AV == `2.0·s` == 1.7. Both expected values are derived from the rounded `mean_pct` (1 dp) and `sd_pct` (4 dp) the summary feeds the chain, matching `_summary_group` — **confirmed**.

### Reused standard / replicate / bracketing blocks match their sources

The standard block is `standard_group(conc_label="Standard Concentration")` and the replicate table is `replicate_area_group(default_rows=5)` — the same calls A8_HPLC makes. The statistics singleton is produced by `_stats_group_30()`, which takes `standard_statistics_group()` (keys `mean_std`, `sd_std`, `rsd_std` over `std_areas.area`) and appends the pooled bracketing field. Keeping `mean_std` unchanged matters because the per-unit `pct_lc` divides by `stats.mean_std`; the key is preserved — **confirmed**.

The two bracketing blocks are byte-identical in shape to A12-0001's: `_BKT_ROWS = {"min": 0, "max": 6, "default": 0}`, each a `kind: table` with a single `area` field labelled "BKT STD Area". The pooled field expression `rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))` matches the A12 source string exactly (confirmed against `a12_derived_rollups.py:172`) — **confirmed**.

### Per-unit pct_lc preserved; 30 units; k = 2.0

The `units` table carries the same fields as `A8_HPLC_DEFINITION` (`unit_ref`, `unit_weight` required, `*dilution_fields("s_")`, `area`, `pct_lc`) and the `pct_lc` expression is copied verbatim — it still divides `area` by `stats.mean_std` and applies the standard chain, potency, MW correction, sample chain and label-claim scaling, rounded to 1 dp. The two intended differences are present: `units.rows == {"min": 1, "max": 30, "default": 30}` and `k_value` default `2.0` via the local `_cu_context_30()` (same label and shape as `_cu_context`, only the default changed) — **confirmed** by reading the module.

### Criteria and limits

Criteria are `[sst_rsd_criterion(), sst_bkt_rsd, *_cu_criteria("units")]`. `sst_rsd_criterion()` targets `stats.rsd_std`, lte 2.0, blocking (key `sst_std_rsd`). The bracketing criterion `sst_bkt_rsd` targets `stats.rsd_bkt`, lte 2.0, blocking. `_cu_criteria("units")` supplies the AV criterion (`summary.acceptance_value`, lte 15.0, blocking) and the unit-count advisory (`count(units.pct_lc)`, gte 10, advisory). The parity test `test_criteria_present_with_correct_limits` asserts all four with those exact targets, operators, limits and severities — **confirmed**.

### Identity and registration

Code TPL-A8-0004 is the next free A8 code per the plan's DB survey (0001 v1+v2, 0002, 0003 draft all taken), archetype A8, result_unit AV. The test is created via `ensure_test` as `TST-CU-30U` / `CU-tablets-30units` — not reusing TST-CU (id 14) or TST-CUWV (id 15). `__init__.py` imports `_A8_CU30` next to the other A8 import and splices `*_A8_CU30` immediately after `*_A8` and before `*_A9_A10_A13`, preserving archetype order — **confirmed** from the committed `__init__.py` diff.

### Seeding, DB integrity and scope

Per the verification notes: DB backed up first to `lims.db.bak-cu30-20261024-144055` (size match 1363968 == 1363968); `--validate-only` exit 0 with `ok TPL-A8-0004 [A8] 7 groups, 17 inputs, 4 area fields, 13 calculated, 4 criteria`; seeder run added one Active TPL-A8-0004 row and the `TST-CU-30U — CU-tablets-30units` Test; stored definition byte-equal to the module (dict==dict and canonical-JSON equal); counts moved templates 37→38 and tests 34→35 with no other row disturbed. I did not re-run the seeder per instruction; the evidence is specific and complete. The commit (9ee1fed) contains exactly `__init__.py` (M), `a8_cu_tablets_30units.py` (A) and `test_a8_0004_cu30_parity.py` (A), confirmed via `git show --name-status`. The unrelated `worksheet-column-merge/verification.md` and `worklog` edits that appear in a working-tree diff are unstaged and NOT part of this commit — scope is clean. No remote contains HEAD, so the commit is local-only — **confirmed**.

### Test coverage

The parity test module reports 9 passing cases covering: units default/max == 30, k_value default == 2.0, identity (code/archetype/result_unit/test_code/test_name), the two hand-derived AV cases plus AV object identity, pooled bracketing %RSD against a hand-derived `rsd(pool(...))`, the four criteria with their limits, and an empty-evaluate invariant (no blocking failure, blank reportable). The full calculation suite reports 5 failed / 811 passed, the 5 being exactly the known pre-existing A6B (3) and worksheet_service (2) failures, unchanged, with no new failures beyond the added parity cases. Per instruction I relied on the recorded results rather than re-running.

Not tested: there is no end-to-end seeded-DB parity assertion in the committed test suite (the byte-equal check was a throwaway script, now deleted) — acceptable, since the catalogue-wide parity tests cover the seeding invariants and the verification notes record the one-off byte-equal confirmation.

</details>

<details>
<summary>File map</summary>

- `backend-v2/scripts/template_definitions/a8_cu_tablets_30units.py` — new 30-unit CU-by-HPLC template; imports AV/summary/criteria from A8_HPLC, bracketing from A12 pattern, k=2.0, 30 units.
- `backend-v2/scripts/template_definitions/__init__.py` — registers `_A8_CU30` and splices it after `*_A8`.
- `backend-v2/tests/calculation/test_a8_0004_cu30_parity.py` — new parity test (9 cases): structure, AV nesting, pooled %RSD, criteria, invariants.

Full diff: `git show 9ee1fed57232b06fcdf5c128eaf0a4654a6162da`.

</details>
