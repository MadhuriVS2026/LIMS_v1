# Verification — TPL-A2-0004 cross-set `% Mean`

## Iteration

First iteration (no `review.json` present at start).

## Authoritative scope note

`plan.md` describes an ADD-A-NEW-COLUMN approach (keep `pct_mean`, add
`pct_mean_compound`). The authoritative task instruction overrides the plan:
**change ONLY the `pct_mean` field expression in place** to the cross-set mean,
`drug_lipid` keeps reading `pct_mean`. No new field added. This verification
records the in-place change per the authoritative instruction.

## DB backup (MANDATORY FIRST ACTION)

- Original: `backend-v2/lims.db` — 1306624 bytes.
- Backup: `backend-v2/lims.db.bak-a2xsetmean-20261022-102317` — 1306624 bytes.
- Byte size match: **True**.

## The change

`scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`,
`_lipid_sample_fields()`, `pct_mean` field only:

- Expression changed from `mean([pct_assay])` to
  `mean([ lipid_samples.pct_assay[cidx], lipid_samples.pct_assay[cidx + 4] ])`
  (engine-proven self-group cross-row reference; blank-skipping mean).
- Field docstring bullet and inline comment updated to describe the cross-set
  per-compound mean shown identically on both the Set-1 row (`cidx`) and the
  Set-2 row (`cidx + 4`).
- `pct_assay`, `cidx`, `compound_name`, `lc`, prep inputs, `area`,
  `standard`/`std_areas`/`bkt_areas`/`stats`, context, the 8 SST criteria and
  `drug_lipid` (still reads `pct_mean`) are UNCHANGED.

## Self-verify results

### 1. No self-referential / circular-dependency error
`TemplateDefinition.parse(LIPID_RATIO_DEFINITION)` → `parses OK`. Evaluator
resolves `pct_mean` from `pct_assay` deterministically (referenced paths are
only `cidx` and `lipid_samples.pct_assay`; `pct_assay` does not depend on any
mean field). Confirmed by every parity test evaluating without error.

### 2. Set-1-only fixture (gold preserved)
Areas Tri 8729574 / DPPG 3826195 / Chol 32474189 / DEPC 44235393; shared prep
Avg Weight 1.0050, Sample Weight 1.5008, vol_j 25, pip_k 1, vol_l 1; Set 2 blank.

- `pct_assay` Set-1 rows: 99.979001 / 86.200388 / 101.772429 / 100.389722
  (2-dp gold 99.98 / 86.20 / 101.77 / 100.39). ✔
- `pct_assay` Set-2 rows (4..7): `EMPTY`. ✔
- `pct_mean` on BOTH the Set-1 row (`cidx`) and the blank Set-2 row (`cidx+4`)
  of each compound = the Set-1 `pct_assay` (blank Set-2 skipped). ✔
- `drug_lipid` row 0 ratio = 0.8414285851744482 → 0.841429 (GOLD PRESERVED). ✔

### 3. Both-sets fixture (cross-set mean)
Set 1 = gold areas; Set 2 = Set1×1.02 truncated = [8904165, 3902718, 33123672,
45120100].

Engine `pct_assay`:
- Set 1: 99.979001 / 86.200388 / 101.772429 / 100.389722
- Set 2: 101.978576 / 87.924375 / 103.807876 / 102.397514

Hand-derived per-compound cross-set mean = (Set1 + Set2) / 2:
- Tri : (99.979001 + 101.978576)/2 = 100.978789
- DPPG: (86.200388 + 87.924375)/2 = 87.062382
- Chol: (101.772429 + 103.807876)/2 = 102.790153
- DEPC: (100.389722 + 102.397514)/2 = 101.393618

Engine `pct_mean` (both the Set-1 row `cidx` and the Set-2 row `cidx+4`, SAME
value): 100.978789 / 87.062382 / 102.790153 / 101.393618. ✔ Matches hand-derived.

Ratio chain from the cross-set means:
- sum_lipid = 100.978789·2/100 + 87.062382·0.9/100 + 102.790153·4.7/100
  + 101.393618·8.2/100
- mgml_bupi = 99.9·13.3/100
- expected ratio = mgml_bupi / sum_lipid = 0.833098 (engine row0 and row1 both
  = 0.8330976239022022). ✔ Both `drug_lipid` rows equal the chain from the
  cross-set means; `reportable_result` matches.

### 4. DB row id 35 byte-for-byte equal to module
- Identity: (35, TPL-A2-0004, v1, Active) — unchanged.
- `exact_equal` (json.dumps): **True** (14226 chars each).
- `canonical_equal` (json.loads == module dict): **True**.
- Sync script printed `1 row updated` and
  `identity preserved: id=35 archetype=A2 version=1 status=Active test_id=32`.

### 5. Parity test updated
`tests/calculation/test_a2_0004_tabular_parity.py`:
- `test_set1_only_cross_set_mean_equals_set1` — Set-1-only; cross-set mean =
  Set-1 value on both rows, Set-2 `pct_assay` EMPTY, gold 2-dp values.
- `TestA2_0004CrossSetMean` class — both-sets oracle: same mean on both rows,
  hand-derived (set1+set2)/2, and ratio chain on both `drug_lipid` rows.
- `test_db_definition_matches_module` — DB row 35 byte-for-byte + canonical +
  identity.

### 6. `pytest tests/calculation`
`5 failed, 765 passed in 71.25s`. The 5 failures are the KNOWN pre-existing
unrelated ones (same as baseline):
- `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement` ×3
- `test_worksheet_service.py` ×2

No new failures. A2-0004 parity file: 12 passed (was 9 at baseline; +3 net).

### 7. TemplateDefinition.parse + WorksheetEvaluator.evaluate + seed validate-only
- parse + evaluate: exercised green by all 12 A2-0004 parity tests.
- `python -m scripts.seed_test_templates --validate-only` → "All definitions
  valid." exit code **0**.

## Cleanup

Throwaway scripts deleted: `_tmp_xset_probe.py`, `_tmp_db_check.py`,
`_tmp_calc_run.txt`. Only the module, the parity test, and DB row 35 changed. No
frontend change.

## Commit

NOT committed (per instruction: do not commit before review verdict APPROVED).
