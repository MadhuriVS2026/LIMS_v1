# Implementation Plan — TPL-A6D-0002 per-row linearity seeding + eleven Additional-Info defaults

Derived from the APPROVED design (`design.md`) and its APPROVED review (`design-review.md`,
0 HIGH / 0 MEDIUM / 3 NIT). The design's architecture is accepted as-is; this plan only
sequences the work. The review upgraded the design's one "stated assumption"
(creation-time `group_values` persistence) to **verified** — it is proven by
`test_worksheet_create_and_fetch_by_test_line` and the repo `create()` mapper, so no
`set_values` fallback is needed.

Grounding (all read firsthand during planning):
- `src/domain/services/calculation/template_schema.py` — `RowSpec` carries only
  `min/max/default/label_from`; `GroupDef.parse` builds a `seen` field-key set and already
  validates `labelFrom ∈ seen`; `FieldDef.default` is a single scalar; `FieldDef.parse`
  already reads `default`, `overridable`, `source`, `type`.
- `src/application/services/worksheet_service.py` — `create_worksheet` constructs
  `TestWorksheet(... group_values={} ...)`; `_seed_context` applies `cf.default` only when
  `available.get(cf.source)` is `None` (so a competing source must be removed for a baked
  default to win). The `available` map contains `trf.batch_number` and `session.date`
  (always non-None), and contains no working-standard/potency/use-before/time-points/
  average-weight key.
- `tests/calculation/` — pytest 9.1.1 on Python 3.13; `python -m pytest` from `backend-v2`;
  `conftest.py` provides `seed_trf_with_line`, `seed_test`, `user`;
  `test_worksheet_service.py` shows the `_service(session)` + `_seed_active_template`
  pattern; `test_template_repository.py::test_worksheet_create_and_fetch_by_test_line`
  proves creation-time `group_values` round-trips through the JSON column.
- Author-script precedents: `_apply_a6d_sampling_details.py` (read-live → deepcopy →
  two-pass validate via `TemplateDefinition.parse` + `WorksheetEvaluator.evaluate({}, {})`
  → write → byte-equal re-read) and `_apply_cu30_kedit.py` (edit-in-place of an existing
  row: fetch by `code`, set `.definition`, commit, re-read byte-equal).
- `rows.seed` does not exist anywhere in `src/**/*.py` today — this is a genuinely new,
  additive capability, confirming the design's Decision A.
- Frontend `frontend-react` build is `tsc -b && vite build`; the row builder already
  prefers stored `group_values` rows over `field.default`, so no `WorksheetForm.tsx`
  change is required (verify-only).

Hard constraints carried into every DB step:
- A timestamped backup `lims.db.bak-a6dlinearity2-<yyyymmdd-HHMMSS>` MUST exist before ANY
  write to `lims.db`. (Setup already created `lims.db.bak-a6dlinearity2-20261027-122834`;
  item 5 re-takes a fresh one immediately before the write so the backup reflects the
  state right before this run's mutation.)
- Do NOT touch TPL-A6D-0001 (id=26, Active) — it must stay byte-unchanged and Active.
- Only `definition` on id=43 changes; its code/name/version/status(Draft)/test_id/
  archetype/result_unit stay exactly as they are.
- Do NOT commit the source edits or `lims.db` unless the user later explicitly asks.

Order rationale: the schema change (1) is the foundation both the service change (2) and
the author script (4) depend on — the script's two-pass validation parses `rows.seed`, and
the service seeds from the parsed definition. The test (3) proves 1+2 before any DB write.
The backup+write (5) and runtime verification (6) come last because they depend on a
promoted Active copy, which only exists once the definition is correct and validated.

---

- [ ] 1. Add the additive `rows.seed` per-row seed capability to the template schema.
      In `template_schema.py`, add a frozen-dataclass field `seed: tuple[dict[str, Any], ...] = ()`
      to `RowSpec`; in `RowSpec.parse`, read `raw.get("seed") or []`, require it to be a list
      of dict objects, require `len(seed) <= max_`, and store it as `tuple(dict(r) for r in raw_seed)`
      (raise `TemplateSchemaError` with a `{where}.rows.seed…` message on any violation). In
      `GroupDef.parse`, after the existing `labelFrom ∈ seen` check, validate that every key in
      every seed row is a real field key (`set(seed_row) - seen`) and raise `TemplateSchemaError`
      naming the unknown field(s). The `()` default keeps every existing template parsing
      unchanged.
      Files: src/domain/services/calculation/template_schema.py
      Verify: `python -m pytest tests/calculation/test_template_entities.py tests/calculation/test_evaluator.py tests/calculation/test_seeded_template_parity.py` — all pass with no new failures (parity may show only the three pre-existing A6B failures as its recorded baseline; no additional failure is introduced).

- [ ] 2. Seed group rows at worksheet creation from any group whose rows spec declares a seed.
      In `worksheet_service.py`, add a `@staticmethod _seed_group_rows(definition: TemplateDefinition) -> dict[str, list[dict[str, Any]]]`
      that iterates `definition.groups` and, for each group with a non-empty `group.rows.seed`,
      emits `{group.key: [dict(r) for r in group.rows.seed]}` (groups without a seed are omitted
      entirely, preserving today's empty-rows behavior). In `create_worksheet`, replace
      `group_values={}` in the `TestWorksheet(...)` construction with
      `group_values=self._seed_group_rows(definition)` (computed right after the existing
      `context_values = self._seed_context(...)` line). No other call site changes — downstream
      `save_values`/`preview`/`_evaluate`/`_filter_groups` already handle a populated
      `group_values`. Depends on item 1 (reads `RowSpec.seed`).
      Files: src/application/services/worksheet_service.py
      Verify: `python -m pytest tests/calculation/test_worksheet_service.py tests/calculation/test_template_repository.py` — all pass (confirms creation still works and creation-time group_values round-trips).

- [ ] 3. Add a targeted test proving per-row seed round-trips through parse AND lands in a created worksheet's group_values.
      Create `tests/calculation/test_a6d_linearity_seed.py` with two tests. (a) A pure-parse test:
      build a minimal definition containing a `sequence` group with eight fields
      (`calibration_curve` text, `concentration_pct` number, plus the six blank input columns)
      and `rows={min:9,max:15,default:9,labelFrom:"calibration_curve",seed:[…9…]}`; call
      `TemplateDefinition.parse(...)`, assert the parsed group's `rows.seed` has nine entries
      with exactly the nine `calibration_curve`/`concentration_pct` pairs (Calibration standard-1..6,
      LQC, MQC, HQC → 1,5,15,30,40,60,1,15,30) and that the six unseeded columns are absent from
      each seed dict; also assert `WorksheetEvaluator(parsed).evaluate({}, {}).has_blocking_failure is False`.
      (b) A creation test following the `test_worksheet_service.py` pattern (`_seed_active_template`
      with that definition as an Active template + `seed_trf_with_line` + `WorksheetService.create_worksheet`),
      asserting the returned worksheet's `group_values[<group key>]` contains the nine seeded rows
      with the seeded cells filled. Depends on items 1 and 2.
      Files: tests/calculation/test_a6d_linearity_seed.py
      Verify: `python -m pytest tests/calculation/test_a6d_linearity_seed.py` — both new tests pass.

- [ ] 4. Write the one-off author script that mutates the live TPL-A6D-0002 (id=43) definition.
      Create `_apply_a6d_linearity.py` at `backend-v2/` root following `_apply_cu30_kedit.py`
      (edit-in-place of an existing row by `code`) and `_apply_a6d_sampling_details.py` (deepcopy
      + two-pass validate + byte-equal re-read). The script: fetches the live row by
      `code="TPL-A6D-0002"` (assert id==43, status=="Draft"), `copy.deepcopy`s its `definition`,
      then (i) inserts the `linearity` `sequence` group — label "Standard Tapinarof for Linearity",
      the eight fields in the design's exact order, `rows={min:9,max:15,default:9,labelFrom:"calibration_curve",seed:[…9…]}`
      — into `definition["groups"]` immediately after `qc` and before `cells`; (ii) edits the
      eleven Additional-Info `context[]` fields per the design's canonical mapping — modify in
      place `date_of_analysis` (drop `source`, `type:text`, default "06 April 2026", overridable),
      `batch_no` (drop `source`, default "LE6001", overridable), `potency` (default 100→99.67);
      assert `temperature_c`==32 and `donor_area`==1.76 unchanged; add the six new context keys
      `working_std_no`, `use_before_date`, `time_points_min`, `avg_weight_mg`, `trf_number`,
      `ar_number` with the design's defaults, all `overridable:true`, none carrying a `source`.
      The script asserts no example weight/volume figures (89.73/50.0/5.0/50/1.0/15.0/3.0/4.0/6.0)
      appear in the stored definition, validates via the two-pass gate
      (`TemplateDefinition.parse` + `WorksheetEvaluator.evaluate({}, {})` → no blocking failure,
      `resultRef` still `flux.mean_flux`), supports a `--validate-only` / dry-run that makes NO DB
      write, and on a real run writes id=43's `.definition` and re-reads it byte-equal. The real
      DB write MUST NOT run until item 5's backup is confirmed. Depends on item 1 (parse must
      accept `rows.seed`).
      Files: _apply_a6d_linearity.py
      Verify: `python _apply_a6d_linearity.py --validate-only` from `backend-v2` — prints the two-pass validation success (parse + evaluate, no blocking failure) and performs NO DB write.

- [ ] 5. Take a fresh timestamped backup, then apply the author script to lims.db and confirm the round-trip.
      Copy `lims.db` to `lims.db.bak-a6dlinearity2-<yyyymmdd-HHMMSS>` (new timestamp at run time)
      BEFORE the write. Then run the author script for real to mutate id=43. The script's own
      byte-equal re-read is the primary gate; additionally confirm independently that id=43's
      definition now contains the `linearity` group (after `qc`, before `cells`) with nine seed
      rows and that `context[]` has all eleven Additional-Info values as defaults with no competing
      source, AND that id=26 (TPL-A6D-0001) is byte-unchanged and still Active. Do NOT commit
      `lims.db`. Depends on item 4.
      Files: lims.db (data edit, gitignored — not committed); new lims.db.bak-a6dlinearity2-<timestamp>
      Verify: `python _apply_a6d_linearity.py` from `backend-v2` — prints "wrote/updated id=43 … re-read byte-equal OK"; a follow-up read of id=43 shows the linearity group + eleven defaults and id=26 unchanged & Active.

- [ ] 6. Runtime verification end to end (requires an Active copy; never flip the shipped Draft).
      Because `create_worksheet` rejects non-Active templates and id=43 is Draft, in a DISPOSABLE
      copy of `lims.db` (never the shipped file) promote a copy of TPL-A6D-0002 to Active, create
      a worksheet for a `TST-IVRT` test line, and assert the API/worksheet
      `group_values["linearity"]` returns the nine seeded rows (col 1: Calibration standard-1..6 /
      LQC / MQC / HQC; col 2: 1,5,15,30,40,60,1,15,30; the other six columns blank) and
      `context_values` returns all eleven Additional-Info values. Then run the app
      (`start-lims.bat`; backend 127.0.0.1:8443, frontend 5174) against a DB holding the Active
      copy and visually confirm the "Standard Tapinarof for Linearity" table opens with the nine
      pre-filled rows (add/remove bounded 9–15) and the Additional-Info header shows all eleven
      values pre-filled, rendered identically to the existing left-column values. No
      `WorksheetForm.tsx` change is expected; if a seeded cell fails to surface, the fix stays in
      the generic row builder (never a `template_code ===` special case) and the frontend build is
      `tsc -b && vite build` (run from `frontend-react`). Depends on item 5.
      Files: none committed (runtime check only; any Active flip happens in a throwaway DB copy)
      Verify: on the created worksheet, `group_values["linearity"]` has nine rows with seeded cells and `context_values` has all eleven baked values; the UI renders both the nine linearity rows and the eleven Additional-Info values pre-filled.

---

## Notes / assumptions (stated per instructions)

- **Date of Analysis is stored as `type:text` literal "06 April 2026"** (not an ISO `date`),
  so it renders verbatim through the context `<span>`; the `session.date` source is dropped so
  today's date never overrides the baked default.
- **Columns 3–4 (`std_weight_mg`, `diluted_to_ml_1`) are ordinary blank per-row inputs**, not
  seeded and not visually merged — the "entered once per block" semantic is convention only
  (no rowspan/colspan primitive exists in the schema). Downstream readers must not treat a blank
  cell as "inherited from row 1". A true visual merge is out of scope (frontend-only follow-up).
- **Review NIT #1** (a stray "5"/"five new fields" phrasing in the design vs the canonical SIX
  new keys) does not affect this plan: the canonical six new keys are
  `working_std_no`, `use_before_date`, `time_points_min`, `avg_weight_mg`, `trf_number`,
  `ar_number`, with five of the eleven mapping to existing keys
  (`date_of_analysis`, `potency`, `temperature_c`, `donor_area`, `batch_no`).
- **No frontend source change** is required for either addition; item 6 is a verify-the-render
  step. If review later finds a gap, the fix stays in the generic `WorksheetForm.tsx` row builder.
- The source edits (items 1–3) are committable but MUST NOT be committed, and neither must
  `lims.db`, unless the user later asks.
