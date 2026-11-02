# Review — A6D calibration/linearity merge + title singleton (id=43)

Verdict: **APPROVED** (no blocking findings).

## Scope and evidence read
- Approved `design.md` (Revision 2) and `plan.md` in this task folder.
- Coder's `verification-note.md` (recorded commands + results) and the author
  script `backend-v2/_apply_a6d_calib_merge.py`.
- Engine change `src/domain/services/calculation/expression.py` (`_f_where` +
  `_FUNCTIONS` entry) and `tests/calculation/test_a6d_linearity_seed.py`.
- Narrow spot-checks run directly against the LIVE stored `lims.db` (not a
  suite re-run) to confirm the stored artifact, numeric acceptance, and id=26.

## Gate-by-gate result

### Gate 1 — merged single `linearity`, old groups gone, curve re-pointed — PASS
Stored id=43 group order: `['curve','linearity_title','linearity','cells','sampling_details','timepoints','flux']`.
`linearity` columns (stored): `calibration_curve, concentration_pct, std_weight_mg,
diluted_to_ml_1, ml_a, ml_b, ml_taken, diluted_to_ml_2, theoretical_ppm, area,
observed_ppm, recovery_pct` (exact 12 in required order) + two hidden masks
`is_standard, is_qc` appended after. `calibration` and `qc` groups absent from
the stored definition. `curve.curve_slope/curve_intercept/correlation` all read
`slope|intercept|correl(where(linearity.area, linearity.is_standard),
where(linearity.theoretical_ppm, linearity.is_standard))` — re-pointed to the
masked `linearity` series. `qc` handled per design: group removed, the two
advisory QC criteria re-pointed to `min|max(where(linearity.recovery_pct,
linearity.is_qc))`.

### Gate 2 — title singleton immediately before linearity, informational — PASS
Stored `linearity_title` = `{"key":"linearity_title","kind":"singleton",
"label":"Calibration Standards","fields":[{"key":"title","kind":"input",
"type":"text","label":"Title","default":"Calibration Standards"}]}` — exactly one
editable free-text input, following the `sri1_header` precedent. It sits
immediately before `linearity` in group order. A substring scan of the full
stored definition JSON for `linearity_title.title` returns False — it is
referenced by no expression, criterion, limit, or resultRef. Being a singleton
text input, it cannot enter any numeric computation or affect regression scoping.

### Gate 3 — numeric acceptance — PASS
Re-derived directly against the STORED id=43 definition (narrow spot-check):
- theoretical_ppm = [3.577356, 17.886778, 53.660335, 107.320669, 143.094226,
  214.641338] → matches [3.57735564, 17.8867782, 53.6603346, 107.3206692,
  143.0942256, 214.6413384] within 1e-3.
- observed_ppm = [3.195479, 17.578274, 53.782354, 107.026634, 145.235674,
  213.362306] → matches [3.195478386, 17.57827346, 53.7823539, 107.0266337,
  145.2356731, 213.3623055] within 1e-3.
- recovery_pct (round 2) = [89.33, 98.28, 100.23, 99.73, 101.5, 99.4] → matches
  raw targets [89.32515266 … 99.40410691].
- curve fit over the SIX standard rows only: slope 53797.61, intercept 28844.87,
  correl 0.9999. The hidden `is_standard`/`is_qc` masks exclude LQC/MQC/HQC;
  the coder's recorded mask-robustness check (QC given skewing dilutions+areas →
  fit byte-identical) further confirms exclusion by construction.

### Gate 4 — flux chain intact; defaults + sampling_details preserved — PASS
Stored `timepoints.conc_1..6` = `(area_k - curve.curve_intercept) /
curve.curve_slope` (unchanged, still fed by the re-pointed curve). `flux` chain
intact through `flux.mean_flux = mean([flux_1..6])`; `resultRef` = `flux.mean_flux`
(preserved). `sampling_details` group present. The script touches only
`linearity`, `curve`, `linearity_title`, the removed `calibration`/`qc` groups,
and the two QC criteria; `context` (23 entries, incl. the Additional-Info
defaults) and `cells`/`timepoints`/`flux` are never modified.

### Gate 5 — id=26 untouched and Active; no new parity failures — PASS
Stored id=26 (TPL-A6D-0001) status = Active; definition SHA-256 =
`955687326efea0f79515b585d76ee22d6c1c9b9d5f9e1ebf3ddf8d566839d010`, identical to
the baseline recorded in the verification note. Recorded parity evidence: all 22
A6D cases pass; the 3 A6B + 2 worksheet-workflow failures were confirmed
pre-existing (reproduced with the engine change stashed out) — no new failures.

### Gate 6 — parse+evaluate pass; minimal backward-compatible engine change; one coherent write; nothing committed — PASS
`TemplateDefinition.parse` + `WorksheetEvaluator.evaluate` succeed (recorded
`has_blocking_failure is False`, no circular-reference error; re-confirmed by the
spot-check evaluate above). Engine change is a single pure additive built-in
`_f_where` (len<2→[], flatten both, zip positionally, keep where mask
truthy-and-not-blank) + one `_FUNCTIONS` entry — no parser/scope/schema change,
no existing signature altered; registry contains a single `"where"` entry.
The author script performs ONE coherent transform and a single `UPDATE` setting
`definition` + `status='Active'`, re-reading byte-equal. `git status` shows the
engine source, tests, author script, and `lims.db` all uncommitted; recent
commits are unrelated template work. No lims.db or source committed.

## Notes (non-blocking, already accepted in design)
- QC `theoretical_ppm` is computed by the same per-row dilution formula and is
  EMPTY until QC dilutions are entered, keeping the two advisory QC criteria
  not-assessable — an accepted, design-documented consequence.
- The label-equality mask drops a standard row if relabelled; documented as a
  known contract, with a `count == 6` self-check guarding accidental relabels.

## Conclusion
All six gates pass against the live stored artifact and the recorded verification
evidence. No blocking findings.
