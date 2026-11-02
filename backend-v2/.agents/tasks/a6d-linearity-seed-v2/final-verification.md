# Final End-to-End Verification — TPL-A6D-0002 per-row linearity seeding + eleven Additional-Info defaults

Fresh independent confirmation run from `d:\RD-instance\GIT\backend-v2`. Each check
below was re-proven from scratch (DB read directly, source code read, real service
paths exercised, tests re-run) rather than relying on the prior `verification.md`.

**Overall result: ALL 8 CHECKS PASS.**

Direct UI render (a human-observed browser page) was **NOT** confirmed — this is a
headless agent environment with no observable browser. The UI render was instead
verified via (a) the frontend render code path in `WorksheetForm.tsx`, (b) a clean
`tsc + vite` production build, and (c) the real backend **service/create+preview
path** (the exact code the worksheet-create API endpoint runs) returning the nine
rows and eleven values. See Check 5 for the explicit scope statement.

---

## Check 1 — Stored TPL-A6D-0002 (id=43) definition in lims.db — **PASS**

Read directly from `lims.db` table `test_templates`, row id=43 (code `TPL-A6D-0002`,
status `Draft`, version 1, name "In-Vitro Release (Franz Diffusion Cell) — with
Sampling Details").

Linearity group (`key="linearity"`, kind `sequence`, label "Standard Tapinarof for
Linearity"):
- **8 columns in the required order**: `calibration_curve`, `concentration_pct`,
  `std_weight_mg`, `diluted_to_ml_1`, `ml_a`, `ml_b`, `ml_taken`, `diluted_to_ml_2`.
- **Add-row rows spec**: `{min:9, max:15, default:9, labelFrom:"calibration_curve", seed:[…9…]}`.
- Sits immediately after `qc` and before `cells` (group order index qc=2, linearity=3, cells=4).
- **Nine seeded Calibration-curve labels + concentrations (%)**:
  `(Calibration standard-1, 1) (…-2, 5) (…-3, 15) (…-4, 30) (…-5, 40) (…-6, 60)
  (LQC, 1) (MQC, 15) (HQC, 30)` → exactly `1,5,15,30,40,60,1,15,30 %`.
- Each seed row carries ONLY the two seeded columns; the other six open blank.
- No example weight/volume figures (89.73 / 50.0 / 5.0 / 1.0 / 15.0 / 3.0 / 4.0 / 6.0)
  leaked into the linearity group. (A naive full-definition substring scan flagged
  "5.0"/"15.0" — traced to unrelated acceptance limits `85.0`/`115.0` in the criteria
  block, NOT the linearity group. Confirmed false positive.)

All **eleven** Additional-Info `context[]` defaults present with EXACT values and
`source=None` (no competing source to override the baked default):

| Field | Stored default | Expected |
|---|---|---|
| date_of_analysis | `06 April 2026` | `06 April 2026` ✅ |
| working_std_no | `WS/25/079` | `WS/25/079` ✅ |
| use_before_date | `26-May` | `26-May` ✅ |
| potency | `99.67` | `99.67` ✅ |
| temperature_c | `32` | `32` ✅ |
| time_points_min | `40, 80, 120, 160, 200, 240` | `40, 80, 120, 160, 200, 240` ✅ |
| avg_weight_mg | `100` | `100` ✅ |
| batch_no | `LE6001` | `LE6001` ✅ |
| trf_number | `TRF-021-26-053` | `TRF-021-26-053` ✅ |
| ar_number | `AD/048/26/0121` | `AD/048/26/0121` ✅ |
| donor_area | `1.76` | `1.76` ✅ |

## Check 2 — parse + evaluate({}, {}) on the stored definition — **PASS**

`TemplateDefinition.parse(<stored id=43 def>)` succeeded; parsed group order
`['calibration','curve','qc','linearity','cells','sampling_details','timepoints','flux']`.
`WorksheetEvaluator(parsed).evaluate({}, {})` → `has_blocking_failure = False`.

(Note: `python _apply_a6d_linearity.py --validate-only` now RAISES
`RuntimeError: definition already has a 'linearity' group`. That is the author
script's intended idempotence guard — it refuses to re-apply to an already-edited
definition — NOT a defect. The parse+evaluate gate was therefore re-proven directly
against the live stored definition, which is the stronger check.)

## Check 3 — Worksheet runtime, OPTION (ii) — **PASS**

Exercised the real production code the create path uses, on the actual stored id=43
definition:
- `WorksheetService._seed_group_rows(parsed)` → `group_values["linearity"]` = nine
  rows with the exact labels + concentrations above; each row carries only the two
  seeded columns (other six blank).
- `WorksheetService._seed_context(parsed, trf, line, product, actor)` →
  `context_values` returned all eleven Additional-Info values pre-filled with the
  exact baked defaults (all eleven have `source=None`, so the baked default is
  applied directly).

Additionally proven end-to-end through the FULL service path (see Check 5).

## Check 4 — Tests: no new failures vs accepted baseline, and targeted seed test passes — **PASS**

- `tests/calculation/test_a6d_linearity_seed.py` → **3 passed**
  (`test_rows_seed_round_trips_through_parse`, `test_unknown_seed_field_is_rejected`,
  `test_seeded_rows_land_in_a_created_worksheet`).
- `tests/calculation/test_seeded_template_parity.py` → **3 failed, 284 passed**.
  The 3 failures are exactly the accepted baseline `TestA6BDissolutionWithReplacement`
  A6B failures (`test_unit1_release_carryover`, `test_per_timepoint_summary`,
  `test_amount_remaining`). **No NEW failure** introduced by `rows.seed`. Pass count
  is 284 (not the baseline note's 269) because additional unrelated seed templates
  were added to the suite since the baseline note; the three A6B failures that matter
  are unchanged.

## Check 5 — Visual UI render — **direct UI render NOT confirmed; verified via service/API path + render-code path + build instead**

**Direct browser render could not be observed**: this is a headless agent
environment. `start-lims.bat` launches two GUI console windows (backend on
127.0.0.1:8443, frontend on localhost:5174) and opens a browser — none of which is
observable here, so I did not start it (nothing to shut down). This is stated
explicitly as required by the task.

Fallback verification performed (all PASS):

1. **Real service create+preview path** (the exact code
   `POST /trf/test-lines/{id}/worksheet` runs — `Container.get_worksheet_service(...)
   .create_worksheet()` then `.preview()`), against a **disposable copy** of
   `lims.db` (never the shipped file) with a promoted-Active clone of TPL-A6D-0002 on
   a dedicated test/TRF/line:
   - `worksheet.group_values["linearity"]` = **nine** pre-filled rows with the exact
     labels + concentrations; each row only the two seeded columns.
   - `worksheet.context_values` = **all eleven** Additional-Info values pre-filled
     with the exact baked defaults.
   - `preview` → `has_blocking_failure = False`.
   The disposable DB (and its -wal/-shm) was deleted afterward.
2. **Frontend render code path** (read `frontend-react/.../WorksheetForm.tsx`, no
   change made): `seedValues` reads `detail.worksheet.group_values?.[group.key]` as
   `stored`; `rowCount` returns `stored.length` when stored rows exist → nine rows
   render with the seeded cell values winning over `field.default`. The context grid
   maps `definition.context`, each field's
   `current = contextValues[field.key] ?? detail.worksheet.context_values?.[field.key]`,
   rendered through the same `<span>`/input components as the existing left-column
   Additional-Info values; all eleven are `overridable:true` so they pre-fill and are
   editable, identical to the existing values' rendering.
3. **Frontend production build**: `npm run build` (from `frontend-react`) →
   `✓ built in 7.00s` (tsc + vite clean).

**Conclusion for Check 5: the pre-filled linearity table (nine rows, labels +
concentrations) and the eleven Additional-Info values are confirmed present in the
API/service response the UI consumes, and the render code surfaces them the same way
as existing left-column values; direct human-observed browser render was NOT
confirmed in this environment.**

## Check 6 — id=26 byte-unchanged & Active; id=43 the only edited template row — **PASS (within this task's scope)**

- **id=26 (TPL-A6D-0001): byte-unchanged and Active.** Every column (code, name,
  archetype, test_id, version, status, result_unit, definition) is identical to the
  pre-write backups; definition JSON byte-equal; status `Active`; groups still
  `['calibration','curve','qc','cells','timepoints','flux']`.
- **id=43 (TPL-A6D-0002): the only template row this task edited** (definition only;
  code/name/version/status=Draft/test_id/archetype/result_unit unchanged).

Diffing the current DB against this task's own pre-write backup
(`lims.db.bak-a6dlinearity2-20261027-144357`) showed id=43 (definition) plus two
UNRELATED rows — id=27 (TPL-A7-0001 Active→Inactive) and id=49 (TPL-A7-0002 added).
Those belong to a SEPARATE later A7 workflow, proven by its own backup
`lims.db.bak-a7inactivate-20261027-150532` (15:05) and `lims.db.bak-f1f2mirror-20261027-145556`
(14:55), both timestamped AFTER this task's write backup (14:43). They are not this
task's doing; within the A6D scope, id=43 is the sole edited row and id=26 is
untouched.

## Check 7 — Mandatory timestamped backup exists — **PASS**

Two `lims.db.bak-a6dlinearity2-<ts>` backups present:
- `lims.db.bak-a6dlinearity2-20261027-122834` (setup-step backup)
- `lims.db.bak-a6dlinearity2-20261027-144357` (fresh backup taken immediately before
  this task's DB write)

## Check 8 — Cleanup; nothing committed — **PASS**

- All temporary verification scripts I created (`_verify_a6d_final.py`,
  `_verify_leak.py`, `_verify_runtime_a6d.py`, `_verify_diff_a6d.py`,
  `_verify_service_e2e_a6d.py`) were deleted. No `lims.e2eproof*` / `lims.runtimeproof*`
  temp DBs remain.
- **No git commit made.** `lims.db` is gitignored (`git check-ignore` confirms) and
  was never staged. The source edits (`template_schema.py`, `worksheet_service.py`),
  the new test, and the author script remain uncommitted/untracked, per instructions.

---

## Summary table

| # | Check | Result |
|---|---|---|
| 1 | Stored id=43 def: 8 cols, add-row rows spec, 9 seeded labels+conc, 11 Additional-Info defaults exact | **PASS** |
| 2 | parse + evaluate({}, {}) no blocking failure | **PASS** |
| 3 | Worksheet runtime OPTION (ii): 9 rows + 11 values | **PASS** |
| 4 | Targeted seed test passes; parity 3 baseline A6B fails / 284 passed, no new failures | **PASS** |
| 5 | Visual UI render | Direct browser render **NOT confirmed** (headless env). Verified via service/create+preview response + render-code path + clean build. |
| 6 | id=26 byte-unchanged & Active; id=43 only edited A6D row | **PASS** |
| 7 | Backup `lims.db.bak-a6dlinearity2-<ts>` exists | **PASS** |
| 8 | Temp files cleaned; lims.db + source changes NOT committed | **PASS** |
