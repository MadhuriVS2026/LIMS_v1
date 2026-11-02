# Verification note — A6D calibration/linearity merge + title singleton (id=43)

This records exactly what was run and the results, so the reviewer can read the
evidence without re-running the suites. First iteration (no `review.json`
present); implemented from the approved `plan.md` / `design.md`.

## What changed
1. **Engine (backend source, NOT committed):**
   `src/domain/services/calculation/expression.py` — added the additive pure
   built-in `where(series, mask) -> list` (flatten both, zip positionally, keep
   `series[i]` where `mask[i]` is truthy-and-not-blank) and registered it in
   `_FUNCTIONS`. No parser/scope/schema change; no existing signature changed.
2. **Engine unit tests (NOT committed):**
   `tests/calculation/test_expression.py` — added `TestWhereMask` (mask drops
   unmasked positions; blank/whitespace mask entries false; `<2` args → `[]`;
   length-mismatch truncates to shorter; composition
   `slope/intercept/correl(where(area,m), where(theo,m))` over the six acceptance
   rows → slope 53797.61 / intercept 28844.87 / correl 0.9999).
3. **Author script (kept, not committed):**
   `_apply_a6d_calib_merge.py` — one coherent transform of the LIVE id=43 def:
   extend `linearity` to the 12 user-visible columns (+2 hidden boolean masks
   `is_standard`/`is_qc`), new 6-standard + 3-QC dilution seed, re-point `curve`
   to the masked fit, insert `linearity_title` singleton immediately before
   `linearity`, remove old `calibration` and `qc` groups, re-point the two
   advisory QC-recovery criteria at the QC rows inside `linearity`. Single
   `UPDATE` sets `definition` + `status='Active'`; re-reads byte-equal.
4. **Seed test (NOT committed):**
   `tests/calculation/test_a6d_linearity_seed.py` — rewritten to the merged
   12-col + 2-mask shape with the 6-standard dilution seed; added a regression
   assertion over the six seeded standards.

Per the task + design, lims.db and engine/source changes are **not** committed.

## Backups confirmed before the write
- Setup backup `lims.db.bak-a6dmerge-*` already present (confirmed via directory
  listing). A second belt-and-braces copy `lims.db.bak-a6dmerge2-<ts>` was taken
  immediately before the write.

## Commands run and results

### Numeric acceptance gate — `python _apply_a6d_calib_merge.py --validate-only`
PASS. Output:
```
validation OK: parse + evaluate pass; theoretical/observed/recovery match §7;
curve slope=53797.61 intercept=28844.87 correl=0.9999 over 6 standards;
mask excludes QC (n=6); title singleton informational; flux.mean_flux=15.64 finite (chain intact).
```
Acceptance numbers asserted inside the harness (potency=99.67, areas
200754, 974514, 2922207, 5786622, 7842177, 11507227):
- `theoretical_ppm` ≈ [3.57735564, 17.8867782, 53.6603346, 107.3206692, 143.0942256, 214.6413384] (tol 1e-3) — PASS
- regression over the SIX standards only: slope 53797.61, intercept 28844.87 (round 2), correl 0.9999 (round 4) — PASS
- `observed_ppm` ≈ [3.195478386, 17.57827346, 53.7823539, 107.0266337, 145.2356731, 213.3623055] (tol 1e-3) — PASS
- `recovery_pct` (round 2) == [89.33, 98.28, 100.23, 99.73, 101.50, 99.40] (raw targets 89.32515266 … 99.40410691) — PASS
- `count(where(area, is_standard)) == 6` (NIT 3) — PASS
- mask robustness: QC rows given skewing dilutions AND areas → curve slope/intercept/correl byte-identical to standards-only fit — PASS
- flux chain: `flux.mean_flux` finite (15.64) with representative timepoint areas, no circular-reference error — PASS

### Real write — `python _apply_a6d_calib_merge.py`
PASS. Output:
```
wrote/updated id=43 (TPL-A6D-0002) status=Active … re-read byte-equal OK
```

### Stored-state confirmation (direct DB read)
- id=43 `status` = **Active**
- id=43 group order = `['curve', 'linearity_title', 'linearity', 'cells', 'sampling_details', 'timepoints', 'flux']`
  → `linearity_title` sits immediately before `linearity`.
- id=43 `linearity` columns = `calibration_curve, concentration_pct, std_weight_mg, diluted_to_ml_1, ml_a, ml_b, ml_taken, diluted_to_ml_2, theoretical_ppm, area, observed_ppm, recovery_pct, is_standard, is_qc` (12 visible + 2 hidden masks, exact order).
- id=43 `resultRef` = `flux.mean_flux` (preserved).
- Title singleton: one editable free-text input field `title` (default "Calibration Standards"); the string `"linearity_title.title"` appears in no expression/criterion/limit/resultRef (asserted in `validate()`).
- **id=26 (TPL-A6D-0001)** `status` = **Active**, definition SHA-256 unchanged
  before and after the write (`955687326efea0f79515b585d76ee22d6c1c9b9d5f9e1ebf3ddf8d566839d010`) — byte-unchanged and Active.

### parse + evaluate
PASS — `TemplateDefinition.parse` + `WorksheetEvaluator.evaluate` run inside
`validate()`; blank-sheet evaluate reports `has_blocking_failure is False`; no
circular-reference error.

### `python -m pytest tests/calculation/test_expression.py -q`
`106 passed` (includes the 5 new `where` tests).

### `python -m pytest tests/calculation/test_a6d_linearity_seed.py -q`
`4 passed`.

### `python -m pytest tests/calculation/test_seeded_template_parity.py -q`
`3 failed, 293 passed`. The three failures are the KNOWN pre-existing
`TestA6BDissolutionWithReplacement` cases (`test_unit1_release_carryover`,
`test_per_timepoint_summary`, `test_amount_remaining`). Confirmed pre-existing:
re-run with the engine change stashed out and they still fail (3 failed, 1
passed, 292 deselected) — NOT caused by this task.
All **22 A6D** parity cases pass (`-k "A6D"` → 22 passed), so the
**TPL-A6D-0001 parity test still passes**.

### `python -m pytest tests/calculation -q` (full suite)
`5 failed, 881 passed`. The 5 failures are the 3 A6B parity cases above plus two
pre-existing worksheet-workflow cases in `test_worksheet_service.py`
(`test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`,
`test_a_qa_correction_reopens_and_republishes_the_result`). All five were
confirmed to fail with the engine change stashed out as well — they are the
accepted baseline, **no NEW failures** are introduced by this task.

## Net
One merged 12-column (+2 hidden mask) `linearity` table with a `linearity_title`
singleton immediately before it; regression fit over the six standards only via
`where`; old `calibration`/`qc` removed; QC criteria and the flux/resultRef chain
preserved; id=43 Active and byte-equal on re-read; id=26 untouched.
