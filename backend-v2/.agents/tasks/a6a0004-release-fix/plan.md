# Implementation Plan — Fix % Release calculation in TPL-A6A-0004 (Dissolution_12units)

Backend/data only. Correct the stored template definition JSON for `test_templates.id = 34`
(code `TPL-A6A-0004`, version 1, status Active, name `Dissolution_12units`) so the
`timepoints_release` sequence group reproduces the Bupivacaine dissolution sheet EXACTLY.
No frontend changes.

## Context discovered during exploration (read before implementing)

- Engine files (already correct, DO NOT modify): `src/domain/services/calculation/template_schema.py`,
  `evaluator.py`, `expression.py`. Relevant facts:
  - A `sequence` group row sees: its own fields unqualified, `prev.<field>` (immediately
    preceding row), `prior.<field>` (list of all preceding rows), `rowno` (1-based), and
    column series `group.field` for every group.
  - `sum([])` returns `0` (not blank) — so `sum(prior.correction_N)` on row 1 yields 0.
  - `trunc(x, d)` and `round(x, d)` match Excel TRUNC/ROUND. Field-level `rounding`
    (`{"mode":"round"|"trunc","digits":n}`) is applied to the field's result and the
    rounded value is what downstream fields see.
  - `mean/sd/rsd/min/max` already drop blanks; `sd`/`rsd` need ≥2 numbers or return blank.
  - Calculated fields topo-sort by exact `group.field` references, so `unit_N` depending on
    `uncorrected_N`, `correction_N`, `carry`→`media` is fine (no cycle).
- Target is DB-only. `TPL-A6A-0004` is NOT produced by any seed module. The only dissolution
  seed module, `scripts/template_definitions/a6_dissolution.py`, defines `TPL-A6A-0001/-A6B/-A6C`
  with a DIFFERENT 6-unit structure and different field names (`area_n`, `uncorrected_n`,
  `released_n`, group key `timepoints`). It is NOT the source of `-0004`. Therefore the fix
  is a direct UPDATE of `test_templates.definition` for id 34; see item 6 for the
  source-sync decision.
- Worksheet instance for end-to-end verification: `test_worksheets.id = 27`, `template_id = 34`,
  status InProgress, already populated with 12-unit area data in group `time_intervals`.
- Reference dumps written during exploration (keep as read-only aids, delete-optional):
  `.agents/tpl34_definition.json`, `.agents/ws_27.json`, `.agents/bupivacaine_cells.txt`.

## Root-cause findings (verified by running the real evaluator against ws 27)

1. **Media bug (primary).** Current `media = test_prep.medium_volume - (rowno-1)*test_prep.withdrawal_volume`.
   In ws 27, `test_prep.medium_volume = 1` (wrong field). So media = 1, -4, -9, … → negative
   release after the first timepoint. The real dissolution bath/media volume is **750**, held
   in `test_prep.dilution_volume` (= 750 in ws 27; `additional_info.media_volume` and
   `additional_info.wt_per_ml` also hold 750). Sheet T56=`F18`=750 (first row);
   T57=`T56-E23+G23`=`750-5+5`=750; withdrawal (`E23`)=5 and replacement (`G23`)=5 are equal,
   so **media stays 750 for every row**. CONFIRMED against the workbook.
2. **Combined unit formula is wrong.** Current `unit_N` folds uncorrected+carry in one
   expression with no TRUNC and a wrong divisor chain (`test_prep.dilution_volume / 1 * media /
   test_prep.aliquot_volume`), and `carry_N` accumulates `prev.unit_N` (the already-cumulative
   value) instead of a separate truncated correction factor. The sheet uses three distinct
   stages with TRUNC/ROUND at specific points (C57 → C73 → C88).
3. **Summary has no rounding.** Current `mean/sd/rsd/min/max` lack the sheet's ROUND
   (mean→0 dp, sd→1 dp, rsd→1 dp).

## Exact sheet formulas being reproduced (Bupivacaine, confirmed from xl/worksheets/sheet1.xml)

Let `area` = unit area at timepoint t; `STD1 = stats.mean_std` (=1680981.2); standard chain =
`weight_mg/vol_1 * pip_1/vol_2 * pip_2/vol_3` = `22.2/25 * 2/100 * 1/1`; `potency` = 99.9;
`final_LC` = `label_claim_mgml * taken_mL` = `13.3 * 1` = 13.3; media_at_t = 750; MW = 1/1.

- **C57 (uncorrected):** `TRUNC( C41/H27 * D17/F17 * G17/H17 * I17/J17 * F18/1 * H18/G18 * E16/J12 * P26/P27, 3 )`.
  Map: C41→area; H27→STD1; D17/F17/G17/H17/I17/J17→standard chain; F18→media_at_t (750);
  H18/G18→SPL pipette chain (`1/1`); E16→potency; J12→final_LC (13.3); P26/P27→MW (1/1).
- **C73 (correction factor):** `TRUNC( E23/F18 * C57, 3 )` = `TRUNC( withdrawal / media_at_t * uncorrected, 3 )`.
- **C88 ff (corrected, cumulative):** `ROUND(C57,0)`, `ROUND(D57+C73,0)`, `ROUND(E57+C73+D73,0)`, …
  i.e. in the sequence model: `ROUND( uncorrected_at_this_row + sum(prior.correction), 0 )`.
- **Summary:** `mean = ROUND(AVERAGE(units),0)`, `sd = ROUND(STDEV(units),1)`,
  `rsd = ROUND(sd*100/mean,1)` (use `rsd()` rounded to 1 dp), `min = MIN`, `max = MAX`.

Note the sheet is transposed vs. the schema (sheet columns = timepoints, rows = units). In the
sequence group, timepoints are ROWS and the carry accumulates DOWN rows via `sum(prior.correction_N)`.

## Gold values (proven reproduced by the prototype run)

- STD1 mean = 1680981.2.
- U-1 uncorrected: 30min 19.91, 1h 43.19, 2h 63.337, 3h 73.067, 4h 76.916, 6h 81.422, 8h 84.244.
- U-1 correction: 30min 0.132, 1h 0.287, 2h 0.422.
- U-1 corrected: 30min 20, 1h 43, 2h 64, 3h 74, 4h 78, 6h 83, 8h 87.
- Cross-unit summary (corrected): 1h Mean=41, Max=43.
- **DATA CAVEAT (important for verification):** ws 27's stored `time_intervals` row 0 (30 min)
  has corrupted areas for units 2–4 (725659 / 1064162 / 1292301 — these are U-1's 1h/2h/3h
  values, mis-entered). The sheet's true 30-min areas are
  `[334519, 324554, 277744, 298191, 331527, 305277, 304483, 313534, 279703, 336125, 303006, 326627]`.
  So the 30-min cross-unit summary from ws 27 as-stored will NOT match the sheet's
  Mean=19/SD=1.1/%RSD=5.8/Max=20; it matches only after substituting the clean 30-min vector.
  The verification harness (item 7) must therefore assert the 30-min summary against a
  CLEAN input vector, not against the stored ws-27 row. The release-formula correctness is
  fully pinned by U-1's whole series + the 1h summary, which use clean data.

---

## Ordered implementation items

- [ ] 1. Load and snapshot the current stored definition for the fix script.
      Read `test_templates.definition` for id 34 from `backend-v2/lims.db` into a Python dict;
      keep an untouched copy in memory (and optionally write a backup to
      `.agents/tasks/a6a0004-release-fix/tpl34_before.json`) so the change is auditable and
      reversible.
      Files: none yet (a throwaway script under `.agents/tasks/a6a0004-release-fix/` reads the DB).
      Verify: `python -c "..."` prints the current `timepoints_release` field keys (12 `carry_*`,
      12 `unit_*`, media, mean/sd/rsd/min_val/max_val) — confirms you loaded the right row.

- [ ] 2. Rebuild the `timepoints_release` group's field list in that dict (in memory), replacing
      the buggy `media`, `carry_N`, combined `unit_N`, and unrounded summary fields with the
      corrected structure below. Keep `time_hr` (input, `mirrorFrom: time_intervals.time_hr`)
      as the first field unchanged. Preserve `rows: {min:1, max:20, default:12}`. This is ONE
      item (one coherent group rewrite), built with a 1..12 loop.

      Field definitions (expression-engine syntax):
      - `media` (calculated, `hidden: true`):
        `if(rowno = 1, test_prep.dilution_volume, prev.media - test_prep.withdrawal_volume + test_prep.replenishment_volume)`
      - For each unit N in 1..12, `uncorrected_N` (calculated, `hidden: true`,
        `rounding` omitted — TRUNC is in the expression):
        `trunc( time_intervals.unit_N[rowno - 1] / stats.mean_std`
        ` * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3`
        ` * media / 1`
        ` * test_prep.aliquot_volume / test_prep.pippette_2`
        ` * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume)`
        ` * 1 / 1, 3 )`
        (Mapping: `media/1`←F18/1; `aliquot_volume/pippette_2`←H18/G18 SPL pipette chain, =1/1;
        `potency / (label_claim_mgml * sample_volume)`←E16/J12, =99.9/13.3; trailing `1/1`←P26/P27 MW.)
      - For each unit N, `correction_N` (calculated, `hidden: true`):
        `trunc( test_prep.withdrawal_volume / media * uncorrected_N, 3 )`
      - For each unit N, `unit_N` (calculated, VISIBLE — no `hidden` key, keep `label: "N"`):
        `round( uncorrected_N + sum(prior.correction_N), 0 )`
      - `mean` (calculated, visible, `label: "Mean"`): `mean([unit_1, …, unit_12])`,
        `rounding: {"mode":"round","digits":0}`
      - `sd` (visible, `label: "SD"`): `sd([unit_1, …, unit_12])`, `rounding: {"mode":"round","digits":1}`
      - `rsd` (visible, `label: "%RSD"`): `rsd([unit_1, …, unit_12])`, `rounding: {"mode":"round","digits":1}`
      - `min_val` (visible, `label: "Min."`): `min([unit_1, …, unit_12])`
      - `max_val` (visible, `label: "Max."`): `max([unit_1, …, unit_12])`

      Field ORDER in the list: `time_hr`, `media`, then interleave is NOT required —
      place all `uncorrected_1..12`, then all `correction_1..12`, then all `unit_1..12`, then
      `mean, sd, rsd, min_val, max_val`. (Order does not affect evaluation; the topo-sort
      handles dependencies. Grouping by stage keeps the JSON readable.)
      Visible set must remain exactly: `time_hr` + `unit_1..unit_12` + `mean/sd/rsd/min_val/max_val`.
      Hidden set: `media` + `uncorrected_1..12` + `correction_1..12`.
      Files: none persisted yet (same throwaway script).
      Verify: `TemplateDefinition.parse(defn)` succeeds (no `TemplateSchemaError`); assert the
      visible-field count is 18 and hidden-field count is 25 (1 media + 24 helpers).

- [ ] 3. Parse-validate and dry-run evaluate the rebuilt definition against ws 27 BEFORE writing
      to the DB. Construct `WorksheetEvaluator(TemplateDefinition.parse(defn))`, call
      `.evaluate(context_values, group_values)` with ws 27's `context_values` and `group_values`,
      and confirm no exception and that `rows["timepoints_release"][*]["media"]` is 750 for all rows.
      Files: none persisted (throwaway script).
      Verify: prints `media == 750.0` for all 12 rows and `U-1 corrected == [20,43,64,74,78,83,87, …]`.

- [ ] 4. Persist the corrected definition to the DB. `UPDATE test_templates SET definition = ?,
      modified_by = 'release-fix', modified_date = <now> WHERE id = 34` with
      `json.dumps(defn)`. Do this inside a transaction; commit only after the parse+evaluate in
      item 3 passed. This is the only mutating DB write; it is reversible via the backup from item 1.
      Files: `backend-v2/lims.db` (row id 34 of `test_templates`).
      Verify: re-read the row, `json.loads` it, and assert the `timepoints_release` `media`
      expression now starts with `if(rowno = 1, test_prep.dilution_volume`.

- [ ] 5. Clear the stale `computed_snapshot` on ws 27 so the UI/service recomputes with the fixed
      definition (it is currently `null`, so this is a no-op guard — set to `NULL` explicitly if
      non-null). Confirm no other worksheets reference template_id 34 (query returns only id 27).
      Files: `backend-v2/lims.db` (row id 27 of `test_worksheets`, only if `computed_snapshot` is non-null).
      Verify: `SELECT computed_snapshot FROM test_worksheets WHERE id=27` returns NULL.

- [ ] 6. Source-sync decision (document, minimal code). `TPL-A6A-0004` has no declarative source
      module and the existing `a6_dissolution.py` uses an incompatible 6-unit structure, so there
      is nothing to "keep in sync" for this exact template. Record this explicitly: add a short
      comment block in `scripts/template_definitions/a6_dissolution.py` (or a note in this plan's
      directory) stating that the active 12-unit `TPL-A6A-0004` lives DB-only, its corrected
      `timepoints_release` formulas are the authoritative reference, and that regenerating the
      `-0001` variants will NOT touch `-0004`. Do NOT retrofit `-0004` into the seed module in
      this task (that would be a new template version and risks overwriting the live row on reseed).
      Files: `backend-v2/scripts/template_definitions/a6_dissolution.py` (comment only), or
      `.agents/tasks/a6a0004-release-fix/SOURCE_SYNC_NOTE.md`.
      Verify: `python -m pytest tests/calculation/test_seeded_template_parity.py -q` still passes
      (comment-only change does not alter seeded output).

- [ ] 7. Add a permanent parity test reproducing the Bupivacaine release chain through the engine,
      following the pattern in `tests/calculation/test_workbook_parity.py`. Build the
      `timepoints_release` group (or load the fixed definition for id 34) and feed the sheet's
      clean inputs; assert: U-1 uncorrected (30min 19.91 … 8h 84.244), U-1 correction
      (30min 0.132, 1h 0.287, 2h 0.422), U-1 corrected (`[20,43,64,74,78,83,87]`), media == 750
      for all rows, and the cross-unit summary at 30 min (Mean 19, SD 1.1, %RSD 5.8, Min 17,
      Max 20) and 1 h (Mean 41, Max 43) USING the clean 30-min vector
      `[334519,324554,277744,298191,331527,305277,304483,313534,279703,336125,303006,326627]`
      (NOT ws 27's corrupted row). Use `pytest.approx(..., abs=...)` at the sheet's rounding.
      Files: `backend-v2/tests/calculation/test_dissolution_a6a_release.py` (new).
      Verify: `python -m pytest tests/calculation/test_dissolution_a6a_release.py -q` — all new
      tests pass.

- [ ] 8. End-to-end regression + cleanup. Run the full calculation suite to confirm nothing else
      regressed, then delete any throwaway scripts created in items 1–4 (keep the new test from
      item 7 and the reference dumps if desired).
      Files: remove `.agents/tasks/a6a0004-release-fix/*.py` throwaways.
      Verify: `python -m pytest tests/calculation -q` — all pass (including the new test and the
      existing `test_workbook_parity.py` / `test_seeded_template_parity.py`).

## Verification approach summary

- Correctness is pinned by the engine itself (not grep): parse the fixed definition with
  `TemplateDefinition.parse`, run `WorksheetEvaluator.evaluate`, and assert computed values equal
  the sheet's gold numbers at the sheet's rounding. A prototype of exactly this already PASSED for
  U-1's full uncorrected/correction/corrected series, media==750, and the 1h summary during planning.
- The 30-min cross-unit summary must be verified against the clean 30-min area vector (above),
  because ws 27's stored 30-min row is corrupted for units 2–4. If the intent is also to repair the
  stored worksheet data, that is a SEPARATE data-entry correction, out of scope for this
  calculation fix unless requested — flag it, do not silently rewrite analyst-entered areas.
- Run `python -m pytest tests/calculation -q` from `backend-v2/` as the final gate.
