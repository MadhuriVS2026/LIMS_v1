# Verification note — TPL-A6D-0002 (id=43) calibration-table merge + title box

Final end-to-end verification of the stored `lims.db` result for
**TPL-A6D-0002** (id=43), the In-Vitro Release (Franz Diffusion Cell) template.
All checks run against the **stored** definition (source of truth), not a
freshly re-derived one. No feature changes were made during verification; no
defect was found. Verdict: **PASS on every check.**

## Check 1 — merged `linearity` table / old groups / curve / flux — PASS

- Single merged `linearity` sequence group with exactly the twelve user-visible
  columns in order:
  `calibration_curve, concentration_pct, std_weight_mg, diluted_to_ml_1,
  ml_a, ml_b, ml_taken, diluted_to_ml_2, theoretical_ppm, area, observed_ppm,
  recovery_pct` (plus two hidden regression masks `is_standard`, `is_qc`
  appended after the twelve). `area` carries label "Area Response", kind `area`.
- Old `calibration` group **GONE**; old `qc` group **GONE** (handled per design:
  removed, QC-recovery criteria re-pointed into `linearity` via
  `where(..., linearity.is_qc)`).
- `curve` re-pointed to `linearity`:
  `curve_slope   = slope(where(linearity.area, linearity.is_standard), where(linearity.theoretical_ppm, linearity.is_standard))`
  `curve_intercept = intercept(...)`  `correlation = correl(...)`.
- All eleven Additional-Info context defaults still present.
- `sampling_details` group still present.
- IVRT flux chain intact: `timepoints.conc_{n}` feeds from
  `curve.curve_intercept` / `curve.curve_slope`; `amount_{n}` feeds from
  `conc_{n}`; `flux.flux_{n}` chains through `per_area`.
- `resultRef = flux.mean_flux` (unchanged).
- Current group order (after the orchestrator's QC-table addition):
  `curve, linearity_title, linearity, linearity_qc_title, linearity_qc, cells,
  sampling_details, timepoints, flux`.

### Re-verified after the QC-table addition (2026-10-31)

After this run's code review approved, the orchestrator deliberately added two
groups directly after `linearity` (at the user's request; backup
`lims.db.bak-a6dqctable-20261031-203709`). These are **expected** and were left
untouched; re-verification confirms they do not break any acceptance criterion:

- `linearity_qc_title` — editable title singleton, one free-text input field
  (`title`, kind `input`, type `text`, editable), default
  `"Calibration curve for LQC-MQC-HQC"`; referenced by nothing.
- `linearity_qc` — **input-only** sequence, eight columns
  (`calibration_curve, concentration_pct, std_weight_mg, diluted_to_ml_1,
  ml_a, ml_b, ml_taken, diluted_to_ml_2`), rows min 1 / max 15 / default 3,
  seeded `LQC, MQC, HQC`.
- Neither new group is referenced by the curve regression, flux chain, criteria
  or `resultRef`. The masked regression still fits over **only the six standard
  rows in `linearity`** (not `linearity_qc`): slope 53797.61, intercept
  28844.87, correl 0.9999 — unchanged. All six theoretical/observed/recovery
  numbers unchanged. `resultRef` still `flux.mean_flux`. id=43 still **Active**.

## Check 2 — title singleton — PASS

- Group `linearity_title` (kind `singleton`) sits **immediately before**
  `linearity` in group order.
- Exactly one editable free-text input field `title` (kind `input`, type `text`,
  `is_editable == True`).
- Referenced by nothing: `linearity_title.title` appears 0 times anywhere in the
  definition (no expression/aggregate/criterion/limit/footer/chart/resultRef).

## Check 3 — numeric acceptance via the real evaluate path — PASS

Fed the six calibration-standard rows + areas
`[200754, 974514, 2922207, 5786622, 7842177, 11507227]`, potency = 99.67:

| row | theoretical_ppm | observed_ppm | recovery_pct |
|-----|-----------------|--------------|--------------|
| 1 | 3.57735564 | 3.195478944 (exp 3.195478386) | 89.33 |
| 2 | 17.8867782 | 17.578274016 (exp 17.57827346) | 98.28 |
| 3 | 53.6603346 | 53.782354458 (exp 53.7823539) | 100.23 |
| 4 | 107.3206692 | 107.026634269 (exp 107.0266337) | 99.73 |
| 5 | 143.0942256 | 145.235673667 (exp 145.2356731) | 101.5 |
| 6 | 214.6413384 | 213.362306058 (exp 213.3623055) | 99.4 |

theoretical_ppm matches to <1e-6; observed_ppm matches within tol ~1e-3;
recovery_pct (round 2) matches the expected two-dp values exactly. Regression
fit over **only the six standard rows** (LQC/MQC/HQC excluded via `is_standard`
mask): **slope = 53797.61, intercept = 28844.87, correl = 0.9999**.

## Check 4 — parse/evaluate + parity suite — PASS (no new failures)

- `TemplateDefinition.parse(id=43)` + blank `WorksheetEvaluator.evaluate({}, {})`
  → no blocking failure.
- `tests/calculation/test_seeded_template_parity.py`: **3 failed, 293 passed** —
  identical to the accepted baseline (re-confirmed after the QC-table addition).
  The 3 failures are all the pre-existing A6B cases
  (`TestA6BDissolutionWithReplacement::test_unit1_release_carryover`,
  `::test_per_timepoint_summary`, `::test_amount_remaining`). The
  `TestA6DFranzCellIVRT` (TPL-A6D-0001) parity class still passes. No new
  failures introduced.
- `tests/calculation/test_a6d_linearity_seed.py`: **4 passed**.

## Check 5 — id=26 (TPL-A6D-0001) untouched — PASS

Compared id=26 in current `lims.db` against the pre-merge backup
`lims.db.bak-a6dmerge-20261027-173123`: definition is **RAW-bytes-equal** and
JSON-equal; status is **Active**.

## Check 6 — worksheet create + evaluate (service path, disposable copy) — PASS

Headless: the full app (`start-lims.bat`, uvicorn + Vite + browser) cannot be
driven here, so the documented fallback was used. A disposable copy of
`lims.db` was made (`lims-verify-ce0z0d5o.db`, created and removed in the run;
the real `lims.db` was never opened for writing). The engine was pointed at the
copy via `DATABASE_URL`; a product + TRF + one test line on `test_id=25`
(TST-IVRT) were seeded, then the **real** `WorksheetService.create_worksheet`
bound the stored Active id=43 (worksheet created, 9 linearity rows + 3
`linearity_qc` rows seeded) and `WorksheetService.preview` was run with the six
standards' dilution values + areas and edited titles. The single `linearity`
table returned the correct Theoretical / Observed / % Recovery (same numbers as
Check 3), curve slope/intercept/correl = 53797.61 / 28844.87 / 0.9999, group
order = `curve, linearity_title, linearity, linearity_qc_title, linearity_qc,
cells, sampling_details, timepoints, flux`, and both the `linearity_title.title`
and `linearity_qc_title.title` fields are editable with `linearity_title`
rendering immediately above the merged table.

**UI render was NOT directly confirmed** (headless environment) — verified via
the real worksheet create+evaluate **service path** on a disposable DB copy.
Post-run confirmation: the real `lims.db` has 0 verify-seeded TRFs; both id=43
and id=26 remain Active.

## Check 7 — cleanup — DONE

Temp verification scripts removed. Kept: the author script
`_apply_a6d_calib_merge.py`, the parity test
`tests/calculation/test_seeded_template_parity.py`, and this note. No `lims.db`
or source changes were committed.
