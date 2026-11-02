# Implementation Plan — TPL-A6D-0002 linearity table + Additional-Info fields

Edits the LIVE Draft template **TPL-A6D-0002 (id=43)** in
`d:\RD-instance\GIT\backend-v2\lims.db` to apply the two additions from the
APPROVED design (`.agents/tasks/a6d-linearity-addlinfo/design.md`, reviewed
APPROVED in `design-review.md`). The work is one cohesive in-place edit delivered
by a single one-off author script, following the precedents
`_apply_a6d_sampling_details.py` and `_apply_cu30_kedit.py`.

Source of truth is the design doc. Where this plan abbreviates (field lists, rows
spec, which fields are already present), the design's Addition 1 / Addition 2
sections and Acceptance Criteria are authoritative.

## Decisions carried from the APPROVED design (do not re-decide)

- **Addition 1** is ONE `sequence` group `key="linearity"`,
  `label="Standard Tapinarof for Linearity"`, inserted **immediately after `qc`
  and before `cells`**, with 8 input fields and
  `rows = {min:9, max:15, default:9, labelFrom:"calibration_curve"}`. One
  continuous table (the user chose "use 1" — not two set-blocks).
- **No per-row content is baked in.** The nine row labels (Calibration
  standard-1..6, LQC, MQC, HQC) and their Concentrations are analyst-entered; the
  schema has no per-row seed mechanism, and no field carries a `default`. The
  pasted figures (89.73, 50.0, …) are examples only and are NOT stored.
- **Columns 3–4 (`std_weight_mg`, `diluted_to_ml_1`) are ordinary blank per-row
  inputs**, filled once per block by convention — the schema has no merge/rowspan
  primitive (verified in `template_schema.py`).
- **Addition 2** appends exactly **six** `context[]` fields: `trf_number`
  (source `trf.trf_number`) and `ar_number` (source `trf.ar_number`) as
  non-overridable auto-fetch; `working_std_no`, `use_before_date`,
  `time_points_min`, `avg_weight_mg` as `overridable:true` manual inputs (no
  source). The five already-present fields (`date_of_analysis`, `potency`,
  `temperature_c`, `donor_area`, `batch_no`) are NOT duplicated.
- Both additions are purely additive; `resultRef` stays `flux.mean_flux`; no
  existing group/expression is touched; no frontend change; no status change
  (stays Draft).

## Baseline facts verified during planning (for the implementer)

- Python 3.13 with sqlalchemy/sqlite available; run commands from
  `d:\RD-instance\GIT\backend-v2`.
- Live DB confirmed: id=26 `TPL-A6D-0001` **Active**, id=43 `TPL-A6D-0002`
  **Draft**, both archetype `A6d`, test_id=25. id=43 top-level keys
  `[resultRef, context, groups, criteria]`, resultRef `flux.mean_flux`, groups
  order `calibration, curve, qc, cells, sampling_details, timepoints, flux`, 17
  context fields.
- Test baseline for `tests/calculation/test_seeded_template_parity.py`:
  **3 failed, 269 passed**. The 3 failures are all pre-existing and unrelated to
  A6D: `TestA6BDissolutionWithReplacement::test_unit1_release_carryover`,
  `::test_per_timepoint_summary`, `::test_amount_remaining`. This exact tally is
  the pass/fail gate — the edit must not change it.
- Backup naming convention in `backend-v2\`: `lims.db.bak-<slug>-<timestamp>`
  (e.g. `lims.db.bak-a6a0004bkt-20261014-101509`). Use slug `a6dlinearity`.

---

# Implementation Plan

- [ ] 1. MANDATORY backup of lims.db before any write.
      Copy `d:\RD-instance\GIT\backend-v2\lims.db` to
      `d:\RD-instance\GIT\backend-v2\lims.db.bak-a6dlinearity-<yyyymmdd-HHMMSS>`
      using the current timestamp, matching the existing `lims.db.bak-*` naming.
      Do this as the first action; no DB write may precede it.
      Files: creates `backend-v2\lims.db.bak-a6dlinearity-<yyyymmdd-HHMMSS>` (new backup, not committed — lims.db is gitignored).
      Verify: `Get-ChildItem backend-v2\lims.db.bak-a6dlinearity-*` lists the new file and `(Get-Item backend-v2\lims.db.bak-a6dlinearity-*).Length` equals `(Get-Item backend-v2\lims.db).Length` (backup is a full byte copy of the current DB).

- [ ] 2. Write the one-off author script that applies both additions to the live TPL-A6D-0002 (id=43).
      Create `backend-v2\_apply_a6d_linearity_addinfo.py` modeled on
      `_apply_a6d_sampling_details.py` / `_apply_cu30_kedit.py`. It must:
      (a) read the LIVE definition for `code="TPL-A6D-0002"` from `lims.db` via
      `TestTemplateModel` + `async_session_factory` and `copy.deepcopy` it;
      (b) build the `linearity` sequence group exactly per design Addition 1
      (8 input fields in order `calibration_curve` text, `concentration_pct`
      number %, `std_weight_mg` number mg, `diluted_to_ml_1` number mL, `ml_a`
      number mL, `ml_b` number mL, `ml_taken` number mL, `diluted_to_ml_2` number
      mL; all `kind:"input"`; NO `default` on any field; `rows={min:9,max:15,
      default:9,labelFrom:"calibration_curve"}`) and insert it immediately after
      the `qc` group and before `cells`;
      (c) append the six context fields per design Addition 2 (do NOT add the five
      already-present keys);
      (d) validate with the two-pass gate `TemplateDefinition.parse(definition)`
      then `WorksheetEvaluator(parsed).evaluate({}, {})` asserting
      `has_blocking_failure is False`;
      (e) assert the edit is additive: groups differ from the live source ONLY by
      the inserted `linearity` group and context differs ONLY by the six appended
      fields (deep-compare every other group and the five retained context keys
      byte-for-byte);
      (f) write `definition` back to the SAME row id=43 (do not change
      code/name/version/status/test_id/archetype/result_unit), commit, then
      re-read and assert the stored `definition` is byte-equal
      (`json.dumps(..., sort_keys=True)`) to what was written.
      Provide a `--validate-only` flag (build + validate + additive-check, NO DB
      write) like the precedent, so step 3 can dry-run before the real write.
      Files: `backend-v2\_apply_a6d_linearity_addinfo.py`
      Verify: `python _apply_a6d_linearity_addinfo.py --validate-only` prints the validation-OK and additive-check lines and exits 0 WITHOUT writing (confirm by re-checking that the id=43 groups still number 7 via a quick read).

- [ ] 3. Dry-run the script to prove parse + blank-evaluate pass before touching the DB.
      Run the script in validate-only mode; confirm `TemplateDefinition.parse`
      succeeds, `evaluate({}, {})` reports `has_blocking_failure == False`, the
      additive-check passes, and no write occurred. If it fails, fix step 2 and
      re-run — do not proceed to step 4 until this is clean.
      Files: none (read-only run of `backend-v2\_apply_a6d_linearity_addinfo.py`)
      Verify: `python _apply_a6d_linearity_addinfo.py --validate-only` exits 0 with the OK output; a read of id=43 still shows groups `[calibration, curve, qc, cells, sampling_details, timepoints, flux]` (7 groups, unchanged) and 17 context fields.

- [ ] 4. Execute the author script to apply the edit to id=43.
      Depends on step 1 (backup exists) and step 3 (dry-run clean). Run the script
      without `--validate-only`. It performs the write and the byte-equal re-read
      assertion internally.
      Files: modifies `backend-v2\lims.db` (row id=43 `definition` only)
      Verify: `python _apply_a6d_linearity_addinfo.py` exits 0 and prints the write + re-read-byte-equal confirmation line.

- [ ] 5. Confirm both additions in the stored definition (AC1–AC8 checks).
      Read id=43's definition from `lims.db` and assert: groups order is now
      `[calibration, curve, qc, linearity, cells, sampling_details, timepoints,
      flux]`; `linearity.kind == "sequence"`,
      `label == "Standard Tapinarof for Linearity"`,
      `rows == {min:9,max:15,default:9,labelFrom:"calibration_curve"}`; the 8
      field keys/types/units are exactly as designed and NO `linearity` field has
      a `default` key; none of the example figures (89.73, 50.0, 5.0, 1.0, 15.0,
      3.0, 4.0, 6.0) appear anywhere in the `linearity` group JSON; context now
      has 23 fields with the six new keys present (two with the expected sources,
      four with `overridable:true` and no source) and the five already-present
      keys each still appearing exactly once; `resultRef` still `flux.mean_flux`.
      Do this as assertions in a short throwaway read (inline `python -c` or a
      temp script deleted after); grep is NOT acceptable as the verification.
      Files: none (read-only); delete any temp script created.
      Verify: the read script prints all assertions passed and exits 0.

- [ ] 6. Confirm TPL-A6D-0001 (id=26) is byte-unchanged and still Active, and id=43 is the only edited row.
      Compare id=26's current `definition` to the copy in the step-1 backup DB
      (`lims.db.bak-a6dlinearity-<ts>`) and assert byte-equality, and assert its
      `status == "Active"`. Also assert id=43 still has unchanged
      code/name/version/status(=Draft)/test_id/archetype/result_unit.
      Files: none (read-only comparison against the backup); delete any temp script.
      Verify: the comparison script reports id=26 definition identical between live DB and backup, id=26 status Active, id=43 metadata unchanged, and exits 0.

- [ ] 7. Run the seeded-template parity suite and compare to the baseline.
      Depends on step 4. Run the parity tests; the result must be exactly
      **3 failed, 269 passed** with the three failures being the pre-existing
      `TestA6BDissolutionWithReplacement` cases (`test_unit1_release_carryover`,
      `test_per_timepoint_summary`, `test_amount_remaining`). Any other failure,
      or a different count, means the edit regressed something and must be fixed
      before closing.
      Files: none (runs `tests/calculation/test_seeded_template_parity.py`)
      Verify: `python -m pytest tests/calculation/test_seeded_template_parity.py -q` ends with `3 failed, 269 passed` and the three failing node ids are the pre-existing A6B ones.

- [ ] 8. Optional running-app render check; fall back to API/DB inspection if the app is not launched.
      If a running instance is convenient, start via
      `d:\RD-instance\GIT\start-lims.bat` (backend on 127.0.0.1:8443, frontend on
      5174) and visually confirm TPL-A6D-0002 shows the "Standard Tapinarof for
      Linearity" table (9 blank rows, add/delete-row control) and the new
      Additional-Info header fields. If not launching the app, the step-5
      stored-definition assertions plus the step-7 parity pass stand in for the
      render check (TPL-A6D-0002 is Draft, so `create_worksheet` would reject it —
      do NOT call `create_worksheet`; the blank-sheet behavior is already covered
      by `evaluate({}, {})`). Do not restart any already-running dev server on
      8443/5174 unnecessarily.
      Files: none
      Verify: either the app renders the new table + fields correctly, or record in the task notes that steps 5 and 7 serve as the verification in lieu of a live render.

## Notes and assumptions

- `lims.db` is gitignored (confirmed in the worklog); the DB edit and the backup
  are not committed. The author script IS a source file under `backend-v2\` and
  follows the `_apply_*.py` precedent of living in the repo root of the backend.
- AC12 from the design is satisfied at the evaluator level (`evaluate({}, {})` →
  no blocking failure, `rows.default == 9`, all `linearity` fields blank), per the
  design-review NIT: do not attempt a `create_worksheet` call on the Draft row.
- The design flags an optional follow-up (relabeling the five already-present
  context fields to the user's exact right-column wording). It is explicitly OUT
  of scope here and must not be done.
