# Implementation Plan — TPL-A6D duplicate + "Sampling details" per-cell Sample-weight sub-section

Derived from the APPROVED design at `.agents/tasks/a6d-sampling-details/design.md`
(review: `design-review.md`). This plan sequences that design faithfully; it does
not re-decide the architecture. Decisions already fixed by the design and honored
here: duplicate via a one-off authoring script (no first-class clone method exists;
`create_template` auto-generates the code, so it cannot set `TPL-A6D-0002`); new
code `TPL-A6D-0002`, name `In-Vitro Release (Franz Diffusion Cell) — with Sampling
Details`, `version=1`, `status=Draft`, same `test_id` as `-0001`; the sub-section
is a new `singleton` group `sampling_details` placed immediately before
`timepoints`, holding blank `sample_weight_mg_{n}` inputs over the SAME single cell
range used by every other per-cell group (that shared range is the add-column +
cross-section "mirror" contract).

## Verified baseline (from exploration — treat as ground truth for this plan)

- `lims.db` `test_templates` has exactly one `TPL-A6D-%` row: `id=26`,
  `code=TPL-A6D-0001`, `version=1`, `status=Active`, `archetype=A6d`,
  `result_unit=µg/cm²/√h`, `test_id=25` (`test_id=25` is `TST-IVRT`). `TPL-A6D-0002`
  is the next free code. The live definition `groups` order is
  `calibration, curve, qc, cells, timepoints, flux`; per-cell counts are 6 in each
  of `cells` (`applied_mg_{n}`), `timepoints` (`area_{n}`), `flux` (`flux_{n}`); no
  `sampling_details` group exists yet. Verified by direct `sqlite3` read.
- Backup naming in use across the repo: `lims.db.bak-<slug>-<yyyymmdd-HHMMSS>`
  (e.g. `lims.db.bak-a12entrap-20261016-001656`). Use slug `a6dsampling`.
- Authoring-script precedent: `backend-v2/_apply_cu30_kedit.py` — `TemplateDefinition.parse`
  + `WorksheetEvaluator(parsed).evaluate({}, {})`, write via `async_session_factory()`,
  re-read and assert `json.dumps(..., sort_keys=True)` byte-equality. NOTE the
  review's finding #3: that precedent bases its definition on a SEED MODULE; this
  task must base it on the LIVE DB row (`copy.deepcopy(db_row.definition)`), not the
  seed module.
- `TestTemplateService.validate_definition` = `TemplateDefinition.parse` then
  `WorksheetEvaluator(parsed).evaluate({}, {})` — the two-pass gate (AC6).
- `TestTemplateModel` columns available: `code, name, archetype, test_id, version,
  status, result_unit, definition, approved_by, approved_at, created_by, modified_by,
  superseded_by_id`.
- Test runner: `python -m pytest` (config in `backend-v2/pyproject.toml`,
  `asyncio_mode=auto`). **Pre-existing baseline failures:** running
  `tests/calculation/test_seeded_template_parity.py` on the untouched repo yields
  `3 failed, 269 passed` — the 3 failures are all in `TestA6BDissolutionWithReplacement`
  (A6B, unrelated to this A6D task) and fail BEFORE any change here. The 140
  catalogue-wide + A6D-relevant selections pass. The verification gate for this task
  is therefore "no NEW failures beyond those 3 known A6B failures," not "0 failures."
- `lims.db` is gitignored and is the source of truth; it must NOT be committed.
  Supporting script/seed changes may be committed only if the user later asks.

## Scope / out of scope (from design)

- IN: new `TPL-A6D-0002` Draft row with one added `singleton` group of blank,
  add-column-capable, mirroring `sample_weight_mg_{n}` inputs.
- OUT: any change to `TPL-A6D-0001` (id=26 must stay byte-unchanged), to the
  calculation engine, to `template_schema.py`, or to the frontend. No live
  runtime add-column UX for A6D (the existing hide/restore control is gated to
  `TPL-A6A-0004` only). No formula references the new input. Capturing the
  duplicate as a permanent seed module is an optional follow-up, not required.

---

# Implementation Plan

- [ ] 1. Create the mandatory timestamped backup of `lims.db` BEFORE any DB change.
      Copy `backend-v2/lims.db` to `backend-v2/lims.db.bak-a6dsampling-<yyyymmdd-HHMMSS>`
      using the real current timestamp, following the existing `lims.db.bak-*`
      naming. Do this as the very first action; no write may precede it.
      Files: creates `backend-v2/lims.db.bak-a6dsampling-<ts>` (not committed —
      backups are gitignored like `lims.db`).
      Verify: run `Get-ChildItem -Name "lims.db.bak-a6dsampling-*"` in `backend-v2`
      and confirm exactly one new backup exists; confirm its byte size equals the
      current `lims.db` size (`(Get-Item lims.db).Length` equals the backup's
      Length) so it is a complete copy.

- [ ] 2. Write the one-off authoring script that reads the LIVE `TPL-A6D-0001`
      definition from `lims.db`, deep-copies it, inserts the new `sampling_details`
      group, validates, writes the new row, and asserts byte-equality — all in one
      file following the `_apply_cu30_kedit.py` pattern (async, `async_session_factory`).
      Concretely the script must:
      (a) `SELECT` the `TestTemplateModel` row where `code='TPL-A6D-0001'`; set
          `definition = copy.deepcopy(row.definition)` and capture `source_test_id = row.test_id`.
      (b) Define the cell range ONCE as a single module constant
          `CELL_RANGE = range(1, 7)` (this constant IS the add-column/mirror contract:
          changing only this one line extends every per-cell group together).
      (c) Build the new group exactly per design FR3:
          `{"key":"sampling_details","kind":"singleton","label":"Sampling details",
          "fields":[{"key":f"sample_weight_mg_{n}","kind":"input","type":"number",
          "label":f"Cell {n} Sample Weight","unit":"mg"} for n in CELL_RANGE]}` —
          with NO `default` key (blank reusable input) and `required` omitted/false.
          The example numbers 257.0/229.4/227.0/218.2/254.3/257.2 MUST NOT appear
          anywhere in the script or the definition.
      (d) Find the index of the group with `key=="timepoints"` in
          `definition["groups"]` and insert `sampling_details` immediately BEFORE it.
      (e) Guard against double-insert: if a `sampling_details` group already exists
          or a `TPL-A6D-0002` row already exists, abort without writing (idempotent /
          safe to re-run).
      Do NOT write to the DB yet in this item beyond what step 3 covers — but the
      script is authored complete here. Place the script at
      `backend-v2/_apply_a6d_sampling_details.py` (next to `_apply_cu30_kedit.py`).
      Files: `backend-v2/_apply_a6d_sampling_details.py`
      Verify: `python -c "import ast,sys; ast.parse(open('_apply_a6d_sampling_details.py',encoding='utf-8').read()); print('parse ok')"`
      run in `backend-v2` prints `parse ok` (syntactic check only; the real
      behavioral verification is steps 3–5).

- [ ] 3. In the same script, validate the edited definition with the service's
      exact two-pass gate BEFORE any insert: `parsed = TemplateDefinition.parse(definition)`
      then `WorksheetEvaluator(parsed).evaluate({}, {})`, aborting (no DB write) on
      any exception. This is AC6 and mirrors `TestTemplateService.validate_definition`.
      Files: `backend-v2/_apply_a6d_sampling_details.py` (same file as step 2)
      Verify: temporarily run the script up to the validation point (or add a
      `--validate-only` flag) and confirm it reports validation success and that
      `evaluate({}, {})` returns with `has_blocking_failure is False`; if adding a
      flag, `python _apply_a6d_sampling_details.py --validate-only` prints success
      and writes nothing.

- [ ] 4. In the same script, insert the new Draft row and assert byte-equality on
      re-read. Insert `TestTemplateModel(code="TPL-A6D-0002",
      name="In-Vitro Release (Franz Diffusion Cell) — with Sampling Details",
      archetype="A6d", test_id=source_test_id, version=1, status="Draft",
      result_unit="µg/cm²/√h", definition=definition, approved_by=None,
      approved_at=None, created_by="seed", modified_by="seed")`. Do NOT modify row
      id=26. Commit, then re-read the new row and assert
      `json.dumps(new.definition, sort_keys=True) == json.dumps(definition, sort_keys=True)`
      (byte-equality, per the precedent — against the edited deep-copy, not a seed
      module). Run the script to perform the write (backup from step 1 is already in place).
      Files: writes to `backend-v2/lims.db` (NOT committed); no new source files.
      Verify: `python _apply_a6d_sampling_details.py` in `backend-v2` exits 0 and
      prints the byte-equal confirmation.

- [ ] 5. Verify the DB post-conditions (AC1–AC5, AC7, AC9) with a short read-only
      inspection: `TPL-A6D-0002` exists with `version=1, status='Draft',
      archetype='A6d', result_unit='µg/cm²/√h', test_id` equal to `-0001`'s; its
      `groups` contains a `singleton` `sampling_details` labelled "Sampling details"
      positioned immediately before `timepoints` with exactly 6 fields
      `sample_weight_mg_1..6`, each `kind='input'`, `type='number'`, `unit='mg'`, and
      NO `default` key; the example numbers appear nowhere in the stored definition;
      the per-cell range parity holds (count of `sample_weight_mg_{n}` == count of
      `applied_mg_{n}` in `cells` == `area_{n}` in `timepoints` == `flux_{n}` in
      `flux`); and row id=26 (`TPL-A6D-0001`) is still `status='Active'` and
      byte-unchanged versus the step-1 backup. Use a temporary script
      `backend-v2/_tmp_verify_a6d.py` (delete it in step 8).
      Files: temporary `backend-v2/_tmp_verify_a6d.py`
      Verify: `python _tmp_verify_a6d.py` in `backend-v2` prints PASS for every
      assertion above (and specifically asserts id=26's definition bytes equal those
      read from `lims.db.bak-a6dsampling-<ts>`).

- [ ] 6. Demonstrate the add-column / cross-section mirror (AC8) WITHOUT committing
      a changed row. In a throwaway dry-run, set `CELL_RANGE = range(1, 8)`, rebuild
      the `sampling_details` group plus (in-memory, mirroring the seed module's
      per-cell generators from `scripts/template_definitions/a6d_franz_ivrt.py`) the
      per-cell fields of `cells`/`timepoints`/`flux` and the `_series(...)`
      aggregates, then assert that `sample_weight_mg_7` AND `applied_mg_7`, `area_7`
      (+ calc chain `_7`), `flux_7`/`fit_7` all appear and that
      `TemplateDefinition.parse` + `evaluate({}, {})` still succeed. This proves the
      single-range contract mirrors across sections. Do NOT write this 7-cell row to
      the DB. Use a temporary script `backend-v2/_tmp_mirror_demo_a6d.py`
      (delete it in step 8).
      Files: temporary `backend-v2/_tmp_mirror_demo_a6d.py`
      Verify: `python _tmp_mirror_demo_a6d.py` in `backend-v2` prints that all `_7`
      fields are present across the four per-cell groups and that parse + dry-run
      evaluate pass; confirm it made NO DB write (no new `TPL-A6D` row; re-run step
      5's row-count check and confirm still exactly two `TPL-A6D-%` rows).

- [ ] 7. Run the template/calculation test suite and confirm no NEW failures.
      Run `python -m pytest tests/calculation/test_seeded_template_parity.py -q` in
      `backend-v2`. Because this duplicate lives only in `lims.db` and is NOT added
      as a seed module, `SEED_TEMPLATES` is unchanged, so the result must be
      identical to the recorded baseline: `3 failed, 269 passed`, with the 3 failures
      being exactly `TestA6BDissolutionWithReplacement::{test_unit1_release_carryover,
      test_per_timepoint_summary, test_amount_remaining}` (pre-existing A6B issues,
      not caused by this task). Any OTHER failure, or a change in the passed count,
      is a regression to fix before proceeding.
      Files: none (test run only)
      Verify: the pytest summary shows `3 failed, 269 passed` with the three failing
      node ids all under `TestA6BDissolutionWithReplacement`; no A6D/catalogue-wide
      test fails.

- [ ] 8. App-level verification of the rendered worksheet (or documented fallback).
      Start the app via `d:\RD-instance\GIT\start-lims.bat` if it is not already
      running (backend on 127.0.0.1:8443, frontend on localhost:5174; the .bat frees
      those ports first). Confirm in the running app: (i) `TPL-A6D-0002` "… — with
      Sampling Details" appears in the template catalogue (API:
      `GET http://127.0.0.1:8443/api/v1/test-templates` — adjust prefix to the real
      route if different; it is a Draft, so include Draft in the listing filter if
      the UI hides drafts); (ii) a worksheet built on it renders the "Sampling
      details" section with the Cell-1..Cell-6 Sample-weight inputs ALL BLANK (no
      257.0/229.4/…); (iii) the existing IVRT sections (`cells`, `timepoints`,
      `flux`) still render with 6 cells and the math is unchanged. For the
      add-column + mirror requirement: because the live hide/restore "Add column" UI
      is gated to `TPL-A6A-0004` only (confirmed in `WorksheetForm.tsx`), the
      add-column-to-Cell-7 + mirror behavior for A6D is delivered at AUTHORING time
      via the single `CELL_RANGE` constant and is DEMONSTRATED by step 6, not by a
      live button for A6D — state this explicitly in the verification notes.
      If the app cannot be launched in this environment, state that explicitly and
      verify as far as possible via API calls (catalogue listing, fetch the
      definition for `TPL-A6D-0002`) and the DB inspection from step 5; record which
      checks were done live vs via API/DB.
      Files: none (manual/API verification)
      Verify: catalogue lists `TPL-A6D-0002`; the fetched definition for it contains
      the blank `sampling_details` group; a rendered (or API-simulated) worksheet
      shows blank Sample-weight cells for Cell-1..Cell-6; and the mirror/add-column
      mechanism is confirmed via the step-6 demonstration with the gating caveat
      documented.

- [ ] 9. Clean up temporary files and finalize. Delete the temporary verification/
      demo scripts (`backend-v2/_tmp_verify_a6d.py`, `backend-v2/_tmp_mirror_demo_a6d.py`)
      and any other throwaway `_tmp_*` files created during verification. Decide the
      fate of the authoring script `backend-v2/_apply_a6d_sampling_details.py`: keep
      it on disk (matching the `_apply_cu30_kedit.py` precedent) but do NOT commit
      anything — `lims.db` is gitignored and must not be committed, and per the task,
      supporting script/seed changes are committed only if the user later asks. Leave
      the `lims.db.bak-a6dsampling-<ts>` backup in place (it is the safety artifact).
      Files: deletes `backend-v2/_tmp_verify_a6d.py`, `backend-v2/_tmp_mirror_demo_a6d.py`
      Verify: `Get-ChildItem -Name "_tmp_*"` in `backend-v2` returns nothing; `git
      status` shows no staged `lims.db` and no unintended commits (working-tree-only
      changes are acceptable and expected).

## Acceptance (maps to design ACs)

- AC1–AC5, AC9: covered by steps 1, 4, 5.
- AC6 (two-pass validation on the new definition): step 3.
- AC7 (four per-cell ranges equal): step 5.
- AC8 (mirror demonstration at range 1..8, not committed): step 6.
- AC10 (`test_seeded_template_parity.py` unchanged — here "unchanged" = same
  3-failed/269-passed baseline, failures A6B-only): step 7.
- Rendered worksheet / catalogue presence: step 8 (with explicit fallback if the
  app cannot run here).

## Notes / assumptions

- Seeded as **Draft** per design NFR2 (GxP: route through the real submit/approve
  e-sign gate for a validated environment). If a demo requires it be immediately
  usable, Active with `approved_by="seed"` is the documented shortcut — but this
  plan does NOT take that shortcut; it leaves the row Draft and flags that choice.
- The literal two-row "Cell no / Sample weight (mg)" layout is intentionally not
  built as a bespoke widget; cell identity lives in each field's label
  (`Cell {n} Sample Weight`), matching how the existing `cells` group renders
  (`Cell {n} Applied Dose`). This is design review NIT #2 — acceptable as designed;
  a literal two-row widget would be a separate frontend scope item.
- The API route prefix in step 8 (`/api/v1/test-templates`) should be confirmed
  against `src/api/v1/endpoints/test_template_endpoints.py` / `src/main.py` at
  implementation time; adjust if the mounted prefix differs.
