# Implementation Plan — Merge calibration/linearity tables of TPL-A6D-0002 (id=43)

Source of truth: the APPROVED `design.md` (Revision 2) and `design-review.md` (verdict APPROVED,
0 HIGH / 0 MEDIUM / 3 NIT) in this task folder. This plan sequences that design; it does not
re-decide the architecture. The three NITs are folded into the relevant items below.

## Context discovered during exploration (do not re-derive)

- **Live id=43** is `TPL-A6D-0002`, `test_id=25`, `version=1`, **`status=Draft`**, `result_unit=µg/cm²/√h`,
  `resultRef=flux.mean_flux`. Stored group order: `[calibration, curve, qc, linearity, cells,
  sampling_details, timepoints, flux]`. Top-level keys: `resultRef, context, groups, criteria`
  (no `footer`/`charts`/`flags`). The verbatim dump is `.agents/tasks/a6d-calib-merge/_id43_dump.json`.
  `context.potency` is `kind=context, unit=%, default=99.67, overridable=true`.
- **id=26** (`TPL-A6D-0001`, Active) must NOT be touched.
- **Engine** is `src/domain/services/calculation/expression.py` (tokenizer+parser+evaluator, no `eval`)
  and `evaluator.py`. `slope`/`intercept`/`correl` all go through `_xy_pairs` (positional zip + blank-pair
  drop); there is **no** row-filtering aggregate and **no** `where` function today (grep-confirmed).
  `_FUNCTIONS` is the built-in registry. `_flatten` and `_is_blank` are the helpers `_f_where` will reuse.
- **Scoping (evaluator.py `_build_scope`/`_sheet_scope`):** a multi-row group exposes each field as a
  parallel column series `group.field`; a singleton exposes `group.field` scalars (mirrored into
  `result.values["group.field"]`). So `where(linearity.area, linearity.is_standard)` resolves to two
  aligned lists, and a per-row `observed_ppm` can read `curve.curve_slope`/`curve.curve_intercept`.
  `_evaluation_order` creates a `group.field` ordering edge **only** when the referenced field is
  calculated — inputs/areas create none — so `theoretical_ppm, is_standard → curve.* → observed_ppm →
  recovery_pct` sorts with no cycle.
- **Schema (template_schema.py):** `ValueType.BOOLEAN` exists (so `type:"boolean"` is valid for the
  masks). `rows.seed` keys are validated against the group's declared field keys (`bad = set(seed_row) -
  seen` raises) — every seeded dilution column MUST be a declared field. `overridable` is a no-op on
  `INPUT` (only matters for `CONTEXT`). Field-key uniqueness is enforced **per group**, so
  `linearity_title.title` cannot collide with `linearity`.
- **Author-script precedent (edit id=43 in place):** `backend-v2/_apply_a6d_linearity.py` — reads the
  live def by `code`, `copy.deepcopy`, mutates, `validate()` = `TemplateDefinition.parse` +
  `WorksheetEvaluator.evaluate`, single `UPDATE` via async SQLAlchemy ORM (`async_session_factory`,
  `TestTemplateModel`), then re-reads byte-equal. NOTE: that precedent asserts `status == "Draft"`;
  this task’s script must instead **set `status='Active'`** on write (design §6, review Finding 4).
  Other precedents: `backend-v2/_apply_a6d_sampling_details.py` (deep-copy + two-pass validate +
  byte-equal re-read + group insertion), `backend-v2/_apply_cu30_kedit.py` (edit-by-code + evaluate proof).
  Author scripts live at the **backend-v2 root**, not under `scripts/template_definitions/`.
- **Title singleton precedent:** `scripts/template_definitions/a4_a5_related_substances.py` `sri1_header`
  — a `singleton` with one `{"key":"title","kind":"input","type":"text","label":"Title"}` field.
- **Existing test to update:** `tests/calculation/test_a6d_linearity_seed.py` pins the OLD 8-column
  input-only `linearity` (`set(row) == {"calibration_curve","concentration_pct"}`, `UNSEEDED_COLUMNS`
  all blank). It will fail after the merge and must be updated (design §6, expected churn).
- **DB backup:** the setup step already made `lims.db.bak-a6dmerge-*` (and `lims.db.bak-a6dactivate-*`).
  Do NOT re-backup unless adding a second safety copy; the author script may optionally write one more
  timestamped copy immediately before its `UPDATE` as belt-and-braces, but must not rely on it.

## Engine API decision (design §2c)

Add ONE pure, additive built-in `where(series, mask) -> list`: `_flatten` both, zip positionally, keep
`series[i]` where `mask[i]` is truthy-and-not-blank, return the kept values. Blanks that survive the mask
are left for the downstream aggregate's own blank-dropping, so `slope(where(area,m), where(theo,m))`
keeps today's semantics over the masked subset. Backward-compatible: no parser/scope/schema change, no
existing function signature changes, no template references `where` today. Chosen over "separate groups +
pool" (cannot *exclude* a same-group subset) and over a new `startswith` primitive (more surface than six
label equalities). This capability is REQUIRED because the one-table layout the user mandated puts QC rows
in the same group as the standards, and a naive all-row fit is skewed the moment QC dilutions+areas are
entered (design §2b).

## Ordering of DB backup vs source edit vs DB write

1. Setup step's `lims.db` backup is already done — reuse it; do not duplicate.
2. Make the engine source edit FIRST (item 1). The author script's self-check `evaluate` depends on
   `where` existing, so the engine change must be importable before the script runs.
3. Run the engine unit test (item 2) to confirm `where` is correct before trusting the self-check.
4. Run the author script's `--validate-only` dry run (item 4) — parse + evaluate + assert §7 numbers,
   NO DB write — to prove the merged definition before any write.
5. Only then run the author script for real: it performs the SINGLE `UPDATE` to id=43 (item 5).
6. Update and run the seed test (item 6) and the full calc suite (item 7) last.

---

# Implementation Plan

- [ ] 1. Add the `where(series, mask)` built-in to the expression engine.
      Define `_f_where(args)` beside `_f_pool` in `expression.py`: guard `len(args) < 2 → []`; `_flatten`
      both args; `zip` positionally; append `series[i]` when `not _is_blank(flag) and bool(flag)`; return
      the list. Register `"where": _f_where` in the `_FUNCTIONS` dict. No other engine change.
      Files: `src/domain/services/calculation/expression.py`
      Verify: `python -m pytest tests/calculation/test_expression.py -q` (run from `backend-v2`) still
      passes (no regression from the additive change); full assertion of `where` behavior is item 2.

- [ ] 2. Add `where()` unit tests to the expression test module.
      Cover: mask drops unmasked positions; blank/whitespace mask entries are treated as false; `< 2` args
      returns `[]`; length-mismatched series truncate to the shorter (zip semantics); and composition
      `slope(where(ys, m), where(xs, m))` fits only the masked pairs. Use the six acceptance areas and
      theoretical values from design §7 for one composition case asserting slope `53797.61`,
      intercept `28844.87` (round 2 via `round(...,2)`), correl `0.9999` (round 4).
      Files: `tests/calculation/test_expression.py`
      Verify: `python -m pytest tests/calculation/test_expression.py -q` — all new `where` tests pass.

- [ ] 3. Write the merged-definition builder as pure functions in the author script (no DB yet).
      Create `backend-v2/_apply_a6d_calib_merge.py` following `_apply_a6d_linearity.py`/`_apply_a6d_sampling_details.py`
      (module imports: `asyncio, copy, json, argparse`; `sqlalchemy.select`; `WorksheetEvaluator`,
      `TemplateDefinition`, `TestTemplateModel`, `async_session_factory`). Constants `CODE="TPL-A6D-0002"`,
      `EXPECTED_ID=43`. Implement `build_mutated(source_definition) -> dict` that deep-copies the live def and,
      in ONE coherent transform, produces the target definition. The transform must:
        (a) **Extend `linearity`** (keep `kind=sequence`) to the twelve user-visible columns in EXACT order —
            `calibration_curve`(input text), `concentration_pct`(input number, %), `std_weight_mg`(input number mg),
            `diluted_to_ml_1`(input number mL), `ml_a`(input number mL), `ml_b`(input number mL),
            `ml_taken`(input number mL), `diluted_to_ml_2`(input number mL),
            `theoretical_ppm`(calculated number ppm, expr
            `std_weight_mg / diluted_to_ml_1 * ml_a / ml_b * ml_taken / diluted_to_ml_2 * potency / 100 * 1000`),
            `area`(area number µV·s),
            `observed_ppm`(calculated number ppm, expr `(area - curve.curve_intercept) / curve.curve_slope`),
            `recovery_pct`(calculated number %, expr `observed_ppm / theoretical_ppm * 100`,
            rounding `{mode:round, digits:2}`) — then append TWO hidden `calculated` `type:"boolean"` mask
            columns AFTER the twelve (visible order unchanged): `is_standard` =
            `(calibration_curve = "Calibration standard-1") or … or (calibration_curve = "Calibration standard-6")`
            (six-way `or`, exact seeded labels), and `is_qc` = `not is_standard`.
            `concentration_pct` is display/label-only — it must NOT appear in any formula (design §3, NIT 2:
            it stores the integer level 1/5/15/30/40/60; the `%` is a display unit, not a 0.01 fraction).
        (b) **Replace the seed** so `rows` stays `{min:9, max:15, default:9, labelFrom:"calibration_curve", seed:[…]}`
            with the six standard rows carrying their dilution inputs and the three QC rows carrying label+pct only:
            std-1..6 `std_weight_mg=89.73, diluted_to_ml_1=50`; `ml_a/ml_b/ml_taken/diluted_to_ml_2` =
            (5,50,1,50),(5,50,5,50),(5,50,15,50),(1,1,3,50),(1,1,4,50),(1,1,6,50) with `concentration_pct`
            1/5/15/30/40/60; LQC/MQC/HQC carry only `calibration_curve`+`concentration_pct` (1/15/30).
        (c) **Insert the `linearity_title` singleton** IMMEDIATELY BEFORE `linearity`: `{"key":"linearity_title",
            "kind":"singleton","label":"Calibration Standards","fields":[{"key":"title","kind":"input",
            "type":"text","label":"Title","default":"Calibration Standards"}]}` (follow `sri1_header`; add only
            `default`, no `overridable` — it is a no-op on input per NIT 7).
        (d) **Re-point `curve`** (same keys/roundings): `curve_slope =
            slope(where(linearity.area, linearity.is_standard), where(linearity.theoretical_ppm, linearity.is_standard))`,
            `curve_intercept = intercept(where(...), where(...))`, `correlation = correl(where(...), where(...))`.
        (e) **Remove the `calibration` group** and **remove the `qc` group**; re-point the two advisory criteria:
            `qc_recovery_low.target = min(where(linearity.recovery_pct, linearity.is_qc))`,
            `qc_recovery_high.target = max(where(linearity.recovery_pct, linearity.is_qc))`
            (operators/limits/severity unchanged). Leave `calibration_correlation`, `higuchi_linearity`,
            `flux_precision` untouched. Final group order: `curve, linearity_title, linearity, cells,
            sampling_details, timepoints, flux`.
      Do not touch `context`, `cells`, `sampling_details`, `timepoints`, `flux`, or `resultRef`.
      Files: `backend-v2/_apply_a6d_calib_merge.py`
      Verify: `python -c "import _apply_a6d_calib_merge"` (from `backend-v2`) imports with no error — the
      numeric gate is item 4.

- [ ] 4. Add the self-check (`validate`) and numeric harness to the author script, runnable as `--validate-only`.
      In `_apply_a6d_calib_merge.py` add `validate(definition)`: (1) `TemplateDefinition.parse(definition)`;
      (2) assert `result_ref == "flux.mean_flux"`, the final group set is exactly
      `{curve, linearity_title, linearity, cells, sampling_details, timepoints, flux}`, and `linearity_title`
      is the group immediately before `linearity`; (3) assert `linearity_title.title` appears in NO
      expression, criterion target, or rounding `digitsFrom` across the whole definition (purely informational);
      (4) build the numeric harness — call `WorksheetEvaluator(parsed).evaluate` with `context={"potency":99.67,
      "label_claim": <any>}` and `group_values={"linearity":[ six standard rows with the §7 areas
      200754, 974514, 2922207, 5786622, 7842177, 11507227, then three QC rows ]}`, then assert:
        - each `linearity.theoretical_ppm` ≈ `[3.57735564, 17.8867782, 53.6603346, 107.3206692, 143.0942256,
          214.6413384]` (tol 1e-3),
        - each `linearity.observed_ppm` ≈ `[3.195478386, 17.57827346, 53.7823539, 107.0266337, 145.2356731,
          213.3623055]` (tol 1e-3),
        - each `linearity.recovery_pct` == `[89.32515266→89.33, …]` at round 2 (assert the round-2 values the
          engine produces; the raw targets are `[89.32515266, 98.27523583, 100.227392, 99.72602157, 101.4965296,
          99.40410691]`),
        - `curve.curve_slope == 53797.61`, `curve.curve_intercept == 28844.87` (round 2),
          `curve.correlation == 0.9999` (round 4),
        - **NIT 3:** assert `count(where(linearity.area, linearity.is_standard)) == 6` by evaluating that
          expression (or counting masked rows) so an accidental relabel fails loudly;
        - **mask-robustness:** re-run with the three QC rows given dummy areas AND dummy dilutions and assert
          the four `curve.*` values are byte-identical to the standards-only fit (proves the mask excludes QC);
        - **flux-chain non-break:** feed representative `timepoints` areas and assert `flux.mean_flux` is a
          finite number and `evaluate` raised no circular-reference error.
      Also assert the example weight `89.73` IS present only inside the seeded standard rows (it is now a seed,
      unlike `_apply_a6d_linearity.py` which forbade it), and that QC seed rows name only
      `calibration_curve`+`concentration_pct`. Wire `main(validate_only)` to call `validate` then return
      without writing when `--validate-only`.
      Files: `backend-v2/_apply_a6d_calib_merge.py`
      Verify: `python _apply_a6d_calib_merge.py --validate-only` (from `backend-v2`) prints the validation-OK
      line and exits 0 with every assertion passing. This is the numeric acceptance gate.

- [ ] 5. Add the single DB write (`main`) and run it against id=43.
      In `_apply_a6d_calib_merge.py` `main()`: load the live row by `CODE`, assert `row.id == EXPECTED_ID`;
      `build_mutated`; `validate`; optionally write one extra timestamped `lims.db` copy as a second safety
      net (the setup backup already exists); then in an `async_session_factory()` session set
      `row.definition = definition` AND `row.status = "Active"` (preserve `approved_by`/`approved_at`,
      never write `Draft`), `commit`; re-open a fresh session and assert the re-read `definition` is
      byte-equal (`json.dumps(..., sort_keys=True)`) and `status == "Active"`. The script must never query or
      modify id=26.
      Files: `backend-v2/_apply_a6d_calib_merge.py`, `backend-v2/lims.db` (data write, gitignored)
      Verify: `python _apply_a6d_calib_merge.py` (from `backend-v2`) prints the wrote/re-read-byte-equal line;
      then `python -c "import asyncio,json; from sqlalchemy import select; from src.infrastructure.database.session import async_session_factory; from src.infrastructure.database.models.test_template_model import TestTemplateModel; ..."`
      or a tiny inline check confirms id=43 `status=='Active'`, group keys are
      `[curve, linearity_title, linearity, cells, sampling_details, timepoints, flux]`, and id=26 is unchanged.

- [ ] 6. Update the existing linearity seed test to the merged shape.
      Rewrite `tests/calculation/test_a6d_linearity_seed.py`: replace the OLD 8-column `LINEARITY_GROUP` and
      `UNSEEDED_COLUMNS` with the merged 12-column + 2-mask definition and the new 6-standard dilution seed
      (QC rows still label+pct only). Keep `test_rows_seed_round_trips_through_parse` and
      `test_seeded_rows_land_in_a_created_worksheet` but update their expected per-row key sets (standard rows
      now carry dilution inputs; QC rows still `{calibration_curve, concentration_pct}`). Keep
      `test_unknown_seed_field_is_rejected`. Add one regression assertion that a fit over the six seeded
      standard rows with the §7 areas reproduces slope `53797.61` / intercept `28844.87` / correl `0.9999`.
      Files: `tests/calculation/test_a6d_linearity_seed.py`
      Verify: `python -m pytest tests/calculation/test_a6d_linearity_seed.py -q` — all tests pass.

- [ ] 7. Run the full calculation test suite to confirm no regression from the additive engine change.
      Files: (none)
      Verify: `python -m pytest tests/calculation -q` (from `backend-v2`) — all pass, confirming `where` and
      the merged template regress no other template.

## Notes / assumptions

- **Engine source is not committed unless the user later asks** (task + design §2c). The author script
  edits `lims.db` only, which is gitignored.
- **QC theoretical_ppm** is computed by the same per-row dilution formula (task-mandated). With QC dilution
  columns blank it yields EMPTY, so `recovery_pct` is EMPTY and `qc_recovery_low/high` stay `passed=None`
  (not-assessable) until an analyst enters QC dilutions — a stated, accepted consequence, not a defect
  (design §3 / review NIT 1). This is advisory (non-blocking) and does not affect the reportable flux result.
- **Label-equality mask is a known limitation** (review NIT 3): relabelling a standard row drops it from the
  fit. The `count == 6` self-check assertion (item 4) catches an accidental relabel of the seeded rows.
- The review verdict is **APPROVED**; proceed with implementation. The `design.md` preamble referring to a
  prior `CHANGES_REQUESTED` is the earlier revision — the current `design-review.md` is the APPROVED re-review.
