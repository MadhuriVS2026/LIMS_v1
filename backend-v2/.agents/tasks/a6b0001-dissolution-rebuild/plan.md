# Implementation Plan — Rebuild TPL-A6B-0001 (Doxorubicin, with replacement, whole vial, 12 units)

Backend/data only. No frontend changes. No worktree.

## Goal

Replace the stored definition of template row `TPL-A6B-0001` (version 1, status
Active, archetype A6b, DB id=7, test_id=12) so it reproduces the Excel sheet
`Test types/Dissolution sheet_with replacement_whole vial_ QC release_12 units_Doxo.xlsx`
exactly. Keep the declarative source module `scripts/template_definitions/a6_dissolution.py`
in sync and directly UPDATE the stored JSON in `lims.db` (the seeder skips existing
codes). Then prove every numeric gold value through the real engine.

The code, archetype (A6b), Test binding (test_id=12), status (Active) and version
(1) are preserved. Do NOT create a new template or a new version.

---

## Findings grounded in the code and the sheet (read these first)

### Engine facts (from the three engine files — already read)

- `src/domain/services/calculation/template_schema.py`: a definition has `context[]`,
  `groups[]` (kind `singleton` | `table` | `sequence`), `criteria[]`, `resultRef`.
  `FieldDef.parse` and `GroupDef.parse` only read known keys and **silently ignore
  unknown keys** — so `hidden: true`, `footer`, `mirrorFrom`, and a group-level
  `chart` object pass validation untouched (confirmed: TPL-A6A-0004 stores all of
  these). Field `key` must be a valid Python identifier and must not be one of the
  reserved names `row, prev, prior, index, rowno`.
- `src/domain/services/calculation/evaluator.py`: a multi-row group exposes each
  field as a **column series** `group.field` (a list down the rows). A row-scoped
  formula additionally sees its own row's fields unqualified and via `row.`, plus
  `rowno` (1-based). A **sequence** group additionally exposes `prev.field` (the
  immediately preceding row) and `prior.field` (all preceding rows, as a list).
  Calculated fields are evaluated in topological dependency order; all rows of one
  field are computed before the next field, so a sequence self-reference via `prev`
  resolves against the already-computed earlier row.
- `src/domain/services/calculation/expression.py`: `+ - * /` propagate `EMPTY`
  (blank) — `anything + EMPTY == EMPTY`. `sum([])` returns `0`; `mean([])` returns
  `EMPTY`. `coalesce(a, b)` returns the first non-blank. `trunc`/`round` take a
  digits arg. `pool(...)` flattens ranges dropping blanks. `number(x)` parses a
  wholly-numeric string to float else `EMPTY`. Rounding declared on a field is
  applied to that field's own result and the rounded value is what downstream
  fields see.

### THE carry-over decision (resolved early and verified in-engine)

The sheet's `% Content` table computes release cumulatively **with replacement**:

- First timepoint (sheet B59):
  `area / H16 * C13/E13 * G13/I13 * K13/M13 * F35/net_wt * J35/H35 * P13/100 / B4 * F10 * 100`
- Every later timepoint (sheet B60..B63) adds the PREVIOUS timepoint's release times
  the replacement ratio:
  `base_at_row + (previous_release * M35/F35)`

where `M35` = Withdrawal Volume (10), `F35` = Total Volume (610). This is the exact
sheet formula (transcribed verbatim below), **not** the `sum(prior.correction)` +
TRUNC shape that TPL-A6A-0004 uses. There is no TRUNC and no rounding on the
content/release values — they are full precision on the sheet.

In the sequence engine, model each unit column `n` as:

```
base_n     (hidden) = sample_area.unit_n[rowno - 1] / stats.mean_std
                      * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2
                      * standard.pip_2 / standard.vol_3
                      * test_prep.total_volume / gravimetric.net_n
                      * test_prep.dilution_volume / test_prep.aliquot_volume
                      * standard.potency / 100 / number(label_claim) * wt_per_ml * 100
content_n  (shown)  = base_n + coalesce(prev.content_n, 0) * test_prep.withdrawal_volume / test_prep.total_volume
```

**CRITICAL:** the carry-over term MUST be `coalesce(prev.content_n, 0)`, never a
bare `prev.content_n`. On the first row `prev` is empty, `prev.content_n` is
`EMPTY`, and `base_n + EMPTY * ratio` would propagate to `EMPTY` and blank the whole
column. `coalesce(..., 0)` makes the first row equal `base_n`, matching the sheet.
This was proven in the engine against all gold values before writing this plan.

### Exact sheet transcription (authoritative)

Cell -> meaning -> value / formula:

- `B4` LABEL CLAIM (mg/mL) = `2`
- `B10` % Assay = `99.6`
- `F10` Wt./mL = `1.0313`
- Standard prep: `C13`=30.11 mg; `E13`=100 (ml Water); `G13`=5; `I13`=50 (ml Media);
  `K13`=5; `M13`=10 (ml MeOH); `P13`=100 %Potency.
- `R13` Std Conc (ppm) `= ROUND(C13/E13*G13/I13*K13/M13*P13/100*1000, 3)` = **15.055**
- Replicate areas `C16..G16` = 1299388, 1284245, 1289430, 1289886, 1287196.
  `H16` Mean `= AVERAGE(C16:G16)` = **1290029**.
  `I16` %RSD `= TRUNC(STDEV(C16:G16)/H16*100, 5)` = **0.44098**.
- Bracketing: only `B19`=1289948, `C19`=1317112 populated (BKT-1, BKT-2).
  Pooled mean `H19 = TRUNC(AVERAGE(C16:G16, B19:G19, B21:G21, B23:G23, B25:G25), 1)`.
  Pooled %RSD `I19 = TRUNC(STDEV(same pool)/H19*100, 5)` = **0.86913**. The pool is
  the 5 replicate areas + the 2 bracket values.
- STD-1/STD-2 co-relation: `L19`=30.11 (`=C13`), `L20`=30.02.
  STD-1 areas `O19..O21` = 1299388, 1284245, 1289430 (mirror first 3 replicates),
  `O24 = AVERAGE(O19:O21)` = 1291021.
  STD-2 areas `P19,P20` = 1281451, 1286859, `P24 = AVERAGE(P19:P20)` = 1284155.
  `P25 STD Co-Relation = O24/P24 * L20/L19` = **1.0023416848823155** (≈1.00234).
- System Suitability: items 1-3 text ("Complies"); item 4 `O31 = I16` (0.44098);
  item 5 `O32 = I19` (0.86913).
- Test Preparation: `B35` Sample Volume = 1; `D35` Medium Volume = 600;
  `F35` Total Volume = 610; `H35` Aliquot Volume = 3; `J35` Dilution Volume = 6;
  `M35` Withdrawal Volume = 10; `O35` Replenishment Volume = 10.
- Gravimetric (units-as-columns, Unite-1..Unite-12): Filled Wt row41, Empty Wt row42,
  Net Wt row43 `= Filled - Empty`. Summary over the 12 nets: `N43 = AVERAGE(B43:G43)`,
  `O43 = MIN(B43:G43)`, `P43 = MAX(B43:G43)`.
  NOTE: the sheet's Net summary N/O/P use `B43:G43` (units 1-6 only).
- Sample areas (rows 47-51, times 0.5/3/7/24/48). **Unit-1 raw areas read from the
  sheet (col B)**: `B47`=1227280, `B48`=1136967, `B49`=940328, `B50`=447679,
  `B51`=143975.
- `% Content` table rows 59-63 (sheet title A57 "% Content of Doxorubicin
  Hydrochloride"): B59 is the first-timepoint formula, B60..B63 add `prev * M35/F35`.
  Per-timepoint summary cols N..R: `N = AVERAGE(B:M)`, `O = STDEV(B:M)`,
  `P = O/N*100`, and on this sheet `Q = MIN(B:G)`, `R = MAX(B:G)` for the content
  rows (row 59), while later content rows and the amount table use the full B:M
  span for min/max. (The sheet is internally inconsistent on the Min/Max span;
  reproduce the stored gold numbers — see the verification gate.)
- `% Release` table rows 67-71 (sheet title A65 "% Release of Doxorubicin
  Hydrochloride") = **% Assay − % Content** per unit per timepoint:
  `B67 = $B$10 - B59`, etc. Summary `N/O/P` as above; `Q67 = MIN(B67:G67)`,
  `R67 = MAX(B67:M67)`.

**Naming reconciliation (important):** the user brief calls rows 59-63 the
"%RELEASE TABLE" and rows 67-71 the "AMOUNT-REMAINING TABLE". The sheet's own titles
are the reverse ("% Content" for 59-63, "% Release" for 67-71). The gold values
disambiguate: Unit-1 0.5hr = 83.2069 is the row-59 value (brief "%release"), and
16.3931 = 99.6 − 83.2069 is the row-67 value (brief "amount remaining"). Use the
brief's semantics for group keys/labels (first table = the computed release,
83.2069…; second table = assay minus release, 16.3931…). Document this mapping in a
comment in the source module so a future reader is not misled by the sheet titles.

### Reference templates (read for modeling style)

- TPL-A6A-0004 (DB id=34) — units-as-columns, timepoints-as-rows, hidden helper
  columns, a `sequence` group, per-timepoint Mean/SD/%RSD/Min/Max, and a group-level
  `chart` on a "Graphical data" singleton. Mirror this structure. Its carry-over
  uses `uncorrected + sum(prior.correction)` (A6a shape) — do NOT copy that; A6B uses
  the `prev * M35/F35` recurrence above.
- TPL-A6A-0004 / TPL-A6A-0002 chart config shape to mirror (group-level `chart`
  object):
  ```json
  "chart": {
    "title": "% Release vs Time",
    "sourceGroup": "<release group key>",
    "xField": "time_hr", "xLabel": "Time Interval (Hours)", "yLabel": "% Release",
    "series": [ {"key": "unit_1","label":"Unit 1"}, ... , {"key":"mean","label":"Mean"} ],
    "defaultSeries": ["mean"]
  }
  ```

### Existing tests that will break and must be updated

- `tests/calculation/test_seeded_template_parity.py` -> class
  `TestA6BDissolutionWithReplacement` (approx lines 564-594) pins the OLD 6-unit
  structure (`initial_volume`, `withdrawal_volume` context, `timepoints` group,
  fields `uncorrected_1`, `correction_1`, `released_1`, `mean_released`). This class
  MUST be rewritten to the new 12-unit Doxorubicin structure and gold values.
- The four catalogue-wide invariants in that file still apply to the new definition
  and must pass unchanged: `test_every_template_parses_and_runs_empty`,
  `test_every_template_has_a_resolvable_reportable_result`,
  `test_no_context_field_is_unfillable`,
  `test_area_fields_are_discoverable_for_the_waters_import`. In particular:
  - resultRef must resolve (point it at the release group's `mean`).
  - every context field must have `source`, `overridable`, or a `default`.
  - every chromatographic-area field must be `kind: "area"` (sample unit areas and
    the standard replicate areas), so `area_field_refs` matches.
- `tests/calculation/test_dissolution_a6a_release.py` pins TPL-A6A-0004 and is
  independent of A6B — it must keep passing untouched (regression guard).

---

## Design decisions (one or two sentences each)

1. **Full-precision release, no rounding.** The sheet's B59..B63 and B67..B71 carry
   full precision (no ROUND/TRUNC on content/release), so the `content_n`,
   `remain_n`, and all per-timepoint Mean/SD/%RSD/Min/Max fields declare NO rounding.
   Rounding only appears where the sheet uses it: Std Conc (ROUND 3), replicate %RSD
   / pooled %RSD (TRUNC 5), pooled mean (TRUNC 1), co-relation (match 1.00234).
2. **Carry-over via `coalesce(prev.content_n, 0)`** inside one `sequence` group (the
   release group). Verified to reproduce every gold value. Hidden `base_n` columns
   hold the uncorrected term; visible `content_n` columns hold the cumulative value.
3. **Two output tables as two sequence-style groups.** First group `release`
   (sequence) holds `base_n`(hidden) + `content_n`(visible) + summary. Second group
   `amount` (table — no carry-over, so it needs no `prev`) computes
   `number(pct_assay) - release.content_n[rowno - 1]` per unit + summary. Modeling
   `amount` as a `table` referencing the release column series by row index keeps it
   simple and matches the sheet's `$B$10 - B59` cross-reference.
4. **Units are 12 fixed columns** `unit_1..unit_12` (gravimetric `net_1..net_12`,
   sample-area `unit_1..unit_12`, release `content_1..12`, amount `remain_1..12`),
   built by a Python loop in the source module (same idiom as TPL-A6A-0004). Labels
   `Unite-1`..`Unite-12` to match the sheet.
5. **Timepoints are rows**, default 5 (0.5, 3, 7, 24, 48), max e.g. 20, min 1. The
   first sample-area table carries the raw areas; `release` and `amount` sequence/
   table rows mirror the timepoints.
6. **Context vs input.** `batch_no`, `product`, `trf_no`, `ar_no`, `date_of_analysis`
   come from context (`trf.*` / `product.*` / `session.*`, overridable). `label_claim`
   (B4), `pct_assay` (B10), `wt_per_ml` (F10) are addressable fields used in math —
   keep them as context with numeric defaults AND `overridable: true` (and
   `label_claim` sourced from `trf.label_claim_numeric`, matching A6A-0004) so the
   arithmetic always has a number. `number(label_claim)` guards the free-text case.
7. **Bracketing as a flexible table** (`bkt`, min 0, max 24, default 2) pooled with the
   5 replicate areas via `pool(std_areas.area, bkt.area)`; co-relation modeled with
   two small tables (`corel_std1` default 3 rows, `corel_std2` default 2 rows) plus a
   `corel` singleton for the weights and the co-relation result.
8. **Chart** mirrors TPL-A6A-0004: a "Graphical data" singleton group carrying a
   group-level `chart` object, `sourceGroup` = the release group, series = 12 units +
   mean, `defaultSeries: ["mean"]`.
9. **Min/Max span.** Reproduce the sheet's stored gold numbers. The release-table
   0.5hr gold Min=82.9124 / Max=87.6712 fall within units 1-6, consistent with the
   sheet's `MIN(B59:G59)/MAX(B59:G59)`. Implement Min/Max over the full 12-unit list
   (`min([content_1..12])`, `max([content_1..12])`) as the defensible general
   behaviour, and in the verification script assert the full set of per-timepoint
   gold means (and the 0.5hr SD/%RSD) which are unambiguous; for Min/Max assert the
   0.5hr values which match under both spans for this data (82.9124 / 87.6712 are the
   overall min/max of the 12 at 0.5hr too — confirm during verification and, if a
   later timepoint's gold Min/Max diverges between spans, pin it to the full-12 value
   the engine produces and note it, since the sheet span is internally inconsistent).

---

## Ordered implementation steps

- [ ] 1. Rewrite the A6B definition in the declarative source module to the full
      Doxorubicin 12-unit structure.
      Build `A6B_DEFINITION` (and keep the `A6B = SeedTemplate(... code="TPL-A6B-0001",
      archetype="A6b", test_code="TST-DISSR" ...)` wrapper unchanged) with: context
      (`product`, `batch_no`, `label_claim` [source `trf.label_claim_numeric`,
      overridable, numeric], `pct_assay` [default 99.6, overridable], `wt_per_ml`
      [default 1.0313, overridable], `trf_no`, `ar_no`, `date_of_analysis`, plus
      text header fields for strength/test-performed/media/apparatus/rpm/temp/LNB/
      DISSO ID/HPLC ID/Column ID as context or a header singleton); groups in order:
      `standard` (singleton, chain 100/5/50/5/10, potency 100, `conc_ppm` = ROUND 3),
      `std_areas` (table area, default 5), `bkt` (table input, min 0/max 24/default 2),
      `corel`/`corel_std1`/`corel_std2` (co-relation), `stats` (singleton:
      `mean_std`=mean, `rsd_std`=TRUNC5, `mean_bkt`=TRUNC1 of pooled, `rsd_bkt`=TRUNC5
      of pooled), `sst` (singleton: items 1-3 text inputs default "Complies", item 4
      = `stats.rsd_std`, item 5 = `stats.rsd_bkt`), `test_prep` (singleton: the 7
      volumes with the sheet defaults 1/600/610/3/6/10/10), `gravimetric` (singleton:
      `filled_n`,`empty_n` inputs + `net_n` calculated `filled_n - empty_n` for 12
      units, + `net_mean`/`net_min`/`net_max`), `sample_area` (table: `time_hr` input
      + `unit_1..12` **area** fields, default 5 rows), `release` (sequence: hidden
      `base_n` + visible `content_n` using `coalesce(prev.content_n,0)` + `mean`/`sd`/
      `rsd`/`min_val`/`max_val` over `[content_1..12]`), `amount` (table: `remain_n` =
      `number(pct_assay) - release.content_n[rowno-1]` + the same summary set), and a
      `graph` singleton carrying the `chart` object. Set
      `resultRef: "release.mean"`. Keep `criteria` = the SST %RSD blocking criterion
      (`stats.rsd_std` lte 2.0). Build the per-unit field lists with a loop.
      Files: `scripts/template_definitions/a6_dissolution.py`
      Verify: `cd d:/RD-instance/GIT/backend-v2; python -m scripts.seed_test_templates --validate-only`
      prints `ok   TPL-A6B-0001 [A6b] ...` and exits 0 (parses + dry-run evaluate with
      empty inputs, no blocking failure). The A6A/A6C siblings in the same module must
      still validate.

- [ ] 2. Add a throwaway verification script that asserts every gold value through the
      real engine, driving the exact source-module definition.
      The script imports `A6B` from `scripts.template_definitions.a6_dissolution`,
      parses `A6B.definition` with `TemplateDefinition.parse`, runs
      `WorksheetEvaluator(...).evaluate(context, group_values)` with the sheet inputs
      (standard chain 100/5/50/5/10 potency 100; replicate areas 1299388/1284245/
      1289430/1289886/1287196; bkt 1289948,1317112; corel_std1 1299388/1284245/1289430,
      corel_std2 1281451/1286859, std2_weight 30.02; test_prep 1/600/610/3/6/10/10;
      the 12 filled/empty weights from sheet rows 41/42; sample areas rows 47-51 across
      12 units; context label_claim "2", pct_assay 99.6, wt_per_ml 1.0313), and asserts
      the gold gate (see below). Unit-1 raw areas to feed (sheet col B rows 47-51):
      **0.5hr=1227280, 3hr=1136967, 7hr=940328, 24hr=447679, 48hr=143975**; Unit-1 net
      wt = 21.9327 − 11.1039 = **10.8288**. It must print PASS/FAIL per assertion and
      exit non-zero on any failure. This file is throwaway (prefix `_` under `scripts/`)
      and is deleted in step 6.
      Files: `scripts/_verify_a6b_gold.py` (new, throwaway)
      Verify: `cd d:/RD-instance/GIT/backend-v2; python scripts/_verify_a6b_gold.py`
      exits 0 and prints ALL PASS. Gold values that MUST pass: Std Conc=15.055;
      replicate Mean=1290029; replicate %RSD=0.44098; pooled bkt %RSD=0.86913;
      STD Co-Relation=1.00234; Unit-1 content 0.5/3/7/24/48 = 83.2069/78.4479/65.0382/
      31.4179/10.2762; 0.5hr Mean=85.4977 SD=1.4558 %RSD=1.7027 Min=82.9124 Max=87.6712;
      3hr Mean=77.4944; 7hr Mean=64.8847; 24hr Mean=34.3579; 48hr Mean=10.1428;
      amount-remaining 0.5hr Unit-1=16.3931, 0.5hr Mean=14.1023.

- [ ] 3. Directly UPDATE the stored definition JSON of the TPL-A6B-0001 row in lims.db.
      The `definition` column is JSON-as-TEXT and the seeder skips existing codes, so
      write a small idempotent update script that imports `A6B.definition` from the
      source module, `json.dumps` it, and runs
      `UPDATE test_templates SET definition=?, modified_by='a6b-rebuild',
      modified_date=<utcnow> WHERE code='TPL-A6B-0001'` against
      `d:/RD-instance/GIT/backend-v2/lims.db` (plain `sqlite3`, parameterized). The
      script must confirm exactly one row updated and must NOT change code, archetype,
      test_id, status, version, or approved_by. Source-module and stored JSON are then
      identical by construction (the script serialises the same dict).
      Files: `scripts/update_a6b_definition.py` (new; keep — it is the documented sync
      mechanism), plus it reads `scripts/template_definitions/a6_dissolution.py`.
      Verify: `cd d:/RD-instance/GIT/backend-v2; python scripts/update_a6b_definition.py`
      reports "1 row updated"; then a read-back
      (`python -c "import sqlite3,json;d=json.loads(sqlite3.connect('lims.db').execute(\"select definition from test_templates where code='TPL-A6B-0001'\").fetchone()[0]);print(d['resultRef'], len(d['groups']))"`)
      shows `release.mean` and the expected group count, and `code/archetype/version/
      status/test_id` are unchanged (confirm with a second query).

- [ ] 4. Rewrite the `TestA6BDissolutionWithReplacement` parity class to the new
      structure and gold values.
      Replace the old 6-unit class body (context `initial_volume`/`withdrawal_volume`,
      `timepoints` group, `released_1`/`correction_1`/`mean_released` assertions) with
      the Doxorubicin 12-unit inputs and a hand-derived subset of the gold gate
      (Std Conc, replicate mean/%RSD, pooled %RSD, co-relation, Unit-1 content at the
      five timepoints, 0.5hr Mean/SD/%RSD/Min/Max, and amount-remaining 0.5hr Unit-1 /
      Mean). Keep the class importing the SEEDED definition via `evaluator("TPL-A6B-0001")`
      so it pins the source module, consistent with the file's other parity classes.
      Files: `tests/calculation/test_seeded_template_parity.py`
      Verify: `cd d:/RD-instance/GIT/backend-v2; python -m pytest tests/calculation/test_seeded_template_parity.py -q`
      passes (including the four catalogue-wide invariants against the new A6B).

- [ ] 5. Run the full calculation test suite to confirm no regressions.
      Confirm the A6A-0004 release pins and every other archetype parity still pass.
      Files: none (verification only).
      Verify: `cd d:/RD-instance/GIT/backend-v2; python -m pytest tests/calculation -q`
      exits 0 with all tests passing.

- [ ] 6. Clean up the throwaway verification script and confirm the final state.
      Delete `scripts/_verify_a6b_gold.py`. Leave `scripts/update_a6b_definition.py`
      in place (documented DB-sync mechanism). Re-confirm the suite is green.
      Files: remove `scripts/_verify_a6b_gold.py`.
      Verify: `cd d:/RD-instance/GIT/backend-v2; python -m pytest tests/calculation -q`
      exits 0; `scripts/_verify_a6b_gold.py` no longer exists.

---

## Acceptance gate (all must hold)

- `python -m scripts.seed_test_templates --validate-only` exits 0 with TPL-A6B-0001 ok.
- `python -m pytest tests/calculation -q` exits 0 (new A6B parity + unchanged A6A-0004
  + all other archetypes).
- The stored `definition` of row `code='TPL-A6B-0001'` in `lims.db` equals
  `A6B.definition` from the source module; `code`, `archetype='A6b'`, `version=1`,
  `status='Active'`, `test_id=12` unchanged.
- Numeric gold values reproduced exactly (see step 2 list). These were already proven
  reproducible in the engine during planning, including the `coalesce(prev,0)`
  carry-over and the TRUNC/ROUND placements.

## Notes / assumptions

- No AGENTS.md / CONTRIBUTING / steering files exist in the repo; build/test is plain
  `python -m pytest` (config in `backend-v2/pyproject.toml`, `testpaths=["tests"]`,
  asyncio auto). Run all commands with cwd `d:/RD-instance/GIT/backend-v2`.
- The header text fields (strength, media, apparatus, rpm, temp, LNB, DISSO/HPLC/
  Column ID) are display-only and not in any formula; model them as context
  (overridable) or a header singleton — either passes `test_no_context_field_is_unfillable`
  as long as context fields are overridable or defaulted.
- The sheet's Min/Max column span is internally inconsistent (content row uses B:G,
  amount row uses B:M). Implement the general full-12 span and pin the unambiguous
  gold means/SD/%RSD plus the 0.5hr Min/Max (which coincide under both spans for this
  data). See Decision 9.
