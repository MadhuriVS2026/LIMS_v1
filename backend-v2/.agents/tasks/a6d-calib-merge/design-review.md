# Design Review — Merge calibration/linearity tables of LIMS template id=43 (TPL-A6D-0002)

Reviewer: design-review subagent (fresh context). Reviewing `design.md` (Revision 2).
Method: every load-bearing claim was checked against the actual source — the engine
(`expression.py`, `evaluator.py`), the schema (`template_schema.py`), the cited precedent
(`a4_a5_related_substances.py`), the stored definition (`_id43_dump.json`), and the existing
test (`test_a6d_linearity_seed.py`). The numeric targets were re-derived by running the real
engine, not taken on the design's word.

**Verdict: APPROVED** (0 HIGH, 0 MEDIUM, 3 NIT).

The design stands on its own, specifies the regression row-scoping mechanism concretely, grounds
the title singleton in a verified precedent, and proves the flux-chain preservation. The three
remaining findings are NITs that do not block implementation; they are improvements the implementer
should fold in.

---

## Must-have gate (all six satisfied)

1. **Complete reference trace** — satisfied. §1 traces every `calibration.*`, `curve.*`, `qc.*`
   use, cross-checked against `_id43_dump.json`. Confirmed accurate: `curve.{curve_slope,
   curve_intercept,correlation}` read `calibration.*` (re-point); `calibration.observed_ppm`,
   `qc.observed_ppm`, and `timepoints.conc_1..6` read `curve.*`; criteria `qc_recovery_low/high`
   read `qc.recovery_pct`; `calibration_correlation` reads `curve.correlation`. The dump also
   carries `higuchi_linearity` (reads `flux.min_fit`) and `flux_precision` (reads `flux.rsd_flux`)
   — both untouched by this change, correctly out of the trace's re-point scope. No `footer`,
   `charts`, or `flags` block exists in the definition (verified). The conc→amount→carry→
   cumulative→per_area→flux chain keeps feeding from `curve.*` by key.

2. **Engine aggregate row-selection capability** — satisfied with evidence. Verified in
   `expression.py`: `slope`/`intercept`/`correl` all call `_xy_pairs`, which positionally zips
   two flattened series and drops blank pairs; there is **no** row-filtering predicate, and a
   grep for `where` finds no such function. The design's least-invasive addition (`_f_where` +
   one `_FUNCTIONS` entry) is correct, pure, and backward-compatible. `_loose_equal` does the
   case-insensitive string equality the `is_standard` mask relies on; `_build_scope`/`_sheet_scope`
   both expose multi-row groups as parallel column series, so `where(linearity.area,
   linearity.is_standard)` resolves to two aligned lists exactly as `_f_where` expects.

3. **Merged 12-column `linearity` spec** — satisfied. §3 gives the exact column order, the three
   formulas, and the re-pointed regression written out. The per-row `theoretical_ppm` formula was
   run against the real engine and reproduces all six §7 targets to full precision with
   `potency=99.67`.

4. **Title singleton grounded in precedent** — satisfied. The `sri1_header` precedent in
   `a4_a5_related_substances.py` is verbatim as cited (`{"key":"title","kind":"input",
   "type":"text","label":"Title"}` inside a singleton). The design adds only `default`, drops
   `overridable` — correct, since `is_editable` in `template_schema.py` shows `overridable` is a
   no-op on `INPUT` (it only matters for `CONTEXT`). Field-key uniqueness is enforced only within a
   group (`GroupDef.parse` `seen` set), so `linearity_title.title` cannot collide with `linearity`.

5. **Delete `calibration`, handle `qc`** — satisfied. A grep of `backend-v2/src/**/*.py` finds
   **no** source that hardcodes the `"calibration"`/`"qc"` group keys or `qc.recovery`, so removal
   is safe once `curve` and the two QC criteria are re-pointed. `resultRef=flux.mean_flux` and the
   flux chain are structurally untouched.

6. **Numeric acceptance targets restated** — satisfied. §7 is complete and was independently
   reproduced (below).

### Independent numeric reproduction (real engine)

Running the engine with `potency=99.67` and the §3 formula/seed:

| row | theoretical_ppm (design & reproduced) |
|---|---|
| 1 | 3.57735564 |
| 2 | 17.8867782 |
| 3 | 53.6603346 |
| 4 | 107.3206692 |
| 5 | 143.0942256 |
| 6 | 214.6413384 |

Regression over the six standards: slope **53797.61**, intercept **28844.87**, correl **0.9999** —
identical to §7. `observed_ppm` and `recovery_pct` reproduce §7 at the stated precision/rounding.
The `where`-masked fit over the same six rows is numerically identical by construction, so the
mask provably excludes QC without perturbing the curve.

---

## Findings

### NIT 1 — QC `theoretical_ppm` fate is left as an open confirmation, not a decision
**Where:** §3 "Open confirmation for the user (non-blocking)" and the §3 QC note.
**Problem:** The design leaves whether QC `theoretical_ppm` is computed-by-formula vs. a manual
input as an open question deferred to the user, while defaulting to computed-by-formula. Because
the six QC seed rows carry no dilution inputs, computed QC `theoretical_ppm` → EMPTY, so
`recovery_pct` → EMPTY and the `qc_recovery_low/high` criteria stay permanently `passed=None`
(not assessable) until an analyst hand-enters QC dilution columns. The old `qc` group had
`theoretical_ppm` as a direct **input**, which made QC recovery assessable from just a theoretical
value + area. The merge silently raises the data-entry bar for QC recovery to be evaluated at all.
This is a behavior change, not merely a style choice, so it deserves a stated decision rather than
an open question. It does not block because the design does specify a concrete default and the
criteria are advisory (non-blocking severity confirmed in the dump).
**Concrete fix:** State the decision explicitly. Recommended: keep the task's "computed by the
same per-row formula" for consistency with the single-table intent, and add one sentence to the
QC-recovery edge case noting these criteria remain not-assessable until QC dilution inputs are
entered — so an implementer and reviewer do not read the permanent `passed=None` as a defect.
If instead parity with the old behavior is wanted, add a separate editable QC-theoretical path;
but do not leave it as an unresolved open question in an otherwise implementation-ready design.

### NIT 2 — `concentration_pct` type/semantics vs. the seed values
**Where:** §3 column table (row 2) and the seed table.
**Problem:** The original user data expresses the level as `1%`, `5%`, … but the seed stores
`concentration_pct` as the bare numbers `1,5,15,30,40,60` (matching the stored dump and the
existing seed test). The design calls the column "display/label-only" and correctly keeps it out
of every formula, but does not state the display convention (is the `%` unit suffix rendered by the
UI from `unit:"%"`, so the stored `1` shows as `1 %`?). An implementer could misread the user's
`1%` as `0.01`. Low impact because the column feeds no math, but worth nailing down to avoid a
confusing worksheet.
**Concrete fix:** Add a one-line note: "`concentration_pct` stores the nominal integer level
(1/5/15/30/40/60); the `%` is a display unit rendered by the UI, not a stored 0.01-scale fraction;
the column is informational and enters no formula."

### NIT 3 — label-equality mask is brittle to analyst row edits and added rows; make the contract louder
**Where:** §2c `is_standard` six-way `or`, and the Edge cases "Analyst renames a standard row" /
"Rows beyond the seed".
**Problem:** The mask binds row membership to six exact label strings. The design does document
(correctly) that a renamed standard row silently drops out of the fit and that analyst-added rows
(up to max 15) are neither standard nor QC. Verified against the engine this is the true behavior.
But for a GxP curve this is a real foot-gun: a typo in "Calibration standard-3" silently refits the
curve over five points and changes every downstream `observed_ppm`/flux with no error surfaced.
The design weighed and rejected a dedicated hidden point-type input (reasonable, to stay within the
twelve mandated columns), so the equality mask is acceptable — but the safety contract should be
elevated from an edge-case bullet to an explicit stated limitation, and the self-check should pin
`count(where(linearity.area, linearity.is_standard)) == 6` so an accidental relabel is caught by a
failing assertion rather than a silently-wrong curve.
**Concrete fix:** In §6 add an assertion `count of masked standard rows == 6` to the self-check,
and promote the rename/added-row behavior to a named "Known limitation" so it is a conscious
accepted risk rather than buried in edge cases.

---

## Verified Assumptions (checked against source, all TRUE)

- `slope`/`intercept`/`correl` use `_xy_pairs` (positional zip + blank-pair drop) and have **no**
  row-filtering — `expression.py`. ✔
- No `where` function exists today; grep in `expression.py` finds only prose. ✔
- `_loose_equal` performs case-insensitive trimmed string equality, enabling the label mask. ✔
- `_build_scope` and `_sheet_scope` expose every multi-row group as `{field: [column series]}`,
  so `where(group.field, group.mask)` resolves to aligned lists in both row formulas and criteria
  — `evaluator.py`. ✔
- `_evaluation_order`: a qualified `group.field` edge is created **only** when the referenced field
  is calculated; inputs/areas create no ordering edge. Confirms the no-cycle argument
  (`theoretical_ppm, is_standard → curve.* → observed_ppm → recovery_pct`). ✔
- `is_editable` makes `overridable` a no-op on `INPUT`/`AREA`; it matters only for `CONTEXT`.
  Dropping `overridable` from the title field is correct. ✔
- Field-key uniqueness is enforced per-group only (`GroupDef.parse`), so `linearity_title.title`
  cannot collide with fields in `linearity`. ✔
- `rows.seed` is validated against declared field keys (`bad = set(seed_row) - seen` raises), so
  the 6-row dilution seed keys must — and do — all exist as fields. ✔
- `sri1_header` precedent in `a4_a5_related_substances.py` matches the cited shape verbatim. ✔
- Stored id=43 definition: group order `[calibration, curve, qc, linearity, cells,
  sampling_details, timepoints, flux]`; top-level keys `resultRef, context, groups, criteria`;
  **no** `footer`/`charts`/`flags`. `potency` is `kind=context, default=99.67, overridable=true`.
  `resultRef=flux.mean_flux`. All as the design states — `_id43_dump.json`. ✔
- Criteria set is exactly `calibration_correlation` (blocking), `qc_recovery_low/high` (advisory),
  `higuchi_linearity`, `flux_precision` (advisory) — matches the trace. ✔
- No source under `backend-v2/src/**/*.py` hardcodes `"calibration"`/`"qc"` group keys or
  `qc.recovery` — deletion is safe for consumers. ✔
- `test_a6d_linearity_seed.py` pins `set(row) == {"calibration_curve","concentration_pct"}` and a
  blank `UNSEEDED_COLUMNS` set — the design's §6 "expected churn" flag is accurate; this test
  **will** fail and must be updated to the 12-column + 2-mask shape. ✔
- Numeric targets (§7): theoretical_ppm, slope 53797.61, intercept 28844.87, correl 0.9999,
  observed_ppm, recovery_pct all reproduced on the real engine with `potency=99.67`. ✔

## Unverified / Wrong Assumptions

- **`_proto_check.py` skew table (§2b)** — the specific "naive all-9-row, QC filled" intercept
  124336.70 was not independently re-run (the harness was not re-executed here). The *claim* it
  supports — that QC rows sharing the group skew a naive fit and that the mask removes them — is
  sound on inspection of `_xy_pairs` (it would include any non-blank QC pair) and the six-standard
  fit was reproduced exactly. So the conclusion is verified even though the exact skewed intercept
  value was not. No finding; noted for transparency.
- **Author-script `UPDATE ... SET status='Active'` and `approved_by`/`approved_at` preservation** —
  described in §6 but the script does not yet exist, so this is a design intent, not verified
  behavior. Correctly scoped as an implementation deliverable; the live row is `Draft` as the
  design states. No finding (implementation step concern).
- **Flux chain resolving to a finite `mean_flux` end-to-end after the re-point** — argued
  structurally (keys preserved) and the dependency graph supports it, but a full
  `WorksheetEvaluator.evaluate` over the merged definition with representative timepoint areas was
  not executed here (the merged definition is not yet built). The design makes this an explicit
  self-check in §6, which is the right place for it. No finding.
