# Design Review — TPL-A6D duplicate + "Sampling details" per-cell Sample-weight row

Reviewed document: `backend-v2/.agents/tasks/a6d-sampling-details/design.md`
Review stance: fresh, no prior context. Every load-bearing claim was checked
against source and the live DB.

## Verdict

**APPROVED.** Zero HIGH and zero MEDIUM findings. All findings below are NITs.

The design's three gated mechanisms (duplication, add-column/mirror, sub-section
modeling) are each named with concrete file/line evidence that I independently
reproduced, a concrete new code/name is chosen, and the safety + verification
mandates (timestamped backup, `test_seeded_template_parity.py`,
`TemplateDefinition.parse` + dry-run `evaluate`, running app) are all present and
correct.

---

## Verified Assumptions

Each of these was a claim in the design that I confirmed against source or the
live database.

1. **Live DB row.** `lims.db.test_templates` has exactly one `TPL-A6D-%` row:
   `id=26, code=TPL-A6D-0001, version=1, status=Active, archetype=A6d,
   result_unit=µg/cm²/√h, test_id=25`. `TPL-A6D-0002` is therefore the next free
   code. Confirmed by direct query. ✔
2. **`test_id=25` is `TST-IVRT`.** Row 25 in `tests` is `TST-IVRT /
   "In-Vitro Release Rate (IVRT)" / Quantitative`. The design's plan to copy
   `test_id` from the source row rather than hard-code it is correct and matches
   this. ✔
3. **Stored definition shape.** Group order in the live JSON is exactly
   `calibration, curve, qc, cells, timepoints, flux`; `resultRef=flux.mean_flux`.
   Per-cell field counts: `applied_mg_{1..6}` in `cells`, `area_{1..6}` in
   `timepoints`, `flux_{1..6}` in `flux`. ✔
4. **Absent flags.** `hidden`, `mirrorFrom`, `footer`, `headerContext`, `chart`
   do not appear anywhere in the stored A6D definition JSON. ✔
5. **`cells` is a `singleton` holding per-cell `applied_mg_{n}`.** Confirmed in
   `scripts/template_definitions/a6d_franz_ivrt.py` (`_CELLS_GROUP`). The design's
   representation (A) — model `sampling_details` as a `singleton` mirroring the
   `cells` shape — is the genuine existing pattern. ✔
6. **Single `_CELL_RANGE` drives every per-cell group + `_series(...)`
   aggregates.** `a6d_franz_ivrt.py` defines `_CELLS=6`,
   `_CELL_RANGE=range(1,_CELLS+1)`, and uses it for `cells`, `timepoints`
   (`_cell_area_fields`, `_cell_calculated_fields`), `flux` (`_flux_fields`) and
   `_series('per_area'|'flux'|'fit')`. The "mirror by construction = one range
   constant" argument is accurate. ✔
7. **Service lifecycle.** `TestTemplateService.new_version` branches a Draft
   sharing the **same code** (not a distinct one); `create_template` auto-generates
   the code via `TemplateCodeGenerator.generate(archetype, existing)` and the
   caller cannot choose it. There is no clone-into-a-chosen-code method. The
   design's rejection of both for a caller-chosen code is correct. ✔
8. **Two-pass validation.** `validate_definition` runs `TemplateDefinition.parse`
   then `WorksheetEvaluator(parsed).evaluate({}, {})`, raising on either. Both
   `create_template` and `update_definition` call it, and `submit_for_approval`
   re-validates. The design's AC6 mirrors this exactly. ✔
9. **Script precedent.** `_apply_cu30_kedit.py` does precisely what the design
   prescribes: `TemplateDefinition.parse` + `evaluate({}, {})`, write via
   `async_session_factory()`, re-read and assert `json.dumps(..., sort_keys=True)`
   byte-equality. The design's authoring-script steps match this pattern. ✔
10. **Add-column UI is gated to one template.** `WorksheetForm.tsx` line 181:
    `allowClearColumn = detail.worksheet.template_code === 'TPL-A6A-0004'`. The
    trash/`Add Column` controls (lines ~1258, ~1344) are guarded by it. ✔
11. **"Add column" is hide/restore, not schema growth.** `deleteColumn` hides and
    blanks a column; `addColumn` restores the first hidden input column; the
    explicit comment says "There is no runtime schema change — only previously
    deleted columns can come back." `deletableColumns` = non-hidden input fields.
    The design's "not a runtime grow-the-schema feature" claim is correct. ✔
12. **`mirrorFrom` is a row-aligned echo, not a cross-section cell mechanism.**
    `WorksheetForm.tsx` (~line 371–410) echoes one column into another by row
    index; it is display-only (`isMirrorField`). The design correctly refuses to
    conflate it with the user's "mirror to below tables." ✔
13. **Backend schema does not model `hidden`/`mirrorFrom`.** `FieldDef.parse` in
    `template_schema.py` reads only `key, kind, label, type, unit, expression,
    rounding, required, default, options, source, overridable, areaSource` — no
    `hidden` or `mirrorFrom`. They are frontend-only, as the design states. ✔
14. **Field-key and enum constraints are satisfiable.** Field keys must pass
    `.isidentifier()` and must not be in `_IDENT_RESERVED={row,prev,prior,index,
    rowno}`; `sample_weight_mg_{n}` passes both. `kind="input"` and
    `type="number"` are valid `FieldKind`/`ValueType` enum members, and a
    `singleton` group needs a non-empty `fields` list (6 fields satisfies it). The
    FR3 field spec will parse. ✔
15. **Parity test reads seed modules, not the DB.** `test_seeded_template_parity.py`
    builds `BY_CODE` from `SEED_TEMPLATES` (the `scripts/template_definitions`
    modules). A DB-only duplicate is invisible to it, so AC10's claim that the
    existing suite "still passes unchanged" because the task doesn't alter the A6D
    seed module is correct. ✔
16. **Backup naming convention.** The repo's `lims.db.bak-<slug>-<yyyymmdd-HHMMSS>`
    pattern is well established (dozens of existing `lims.db.bak-*` files, e.g.
    `lims.db.bak-cu30-...`, `lims.db.bak-a6bmirror-...`). NFR1's mandated
    `lims.db.bak-a6dsampling-<ts>` matches it. ✔
17. **Draft-vs-Active seeding guidance.** `seed_test_templates.py` documents
    `--draft` (route through approval) vs default Active with `approved_by="seed"`,
    and `--validate-only`. NFR2 reflects this accurately. ✔

## Unverified / Wrong Assumptions

None. Every factual claim I checked held. No claim in the design was left
unverifiable by me, and none was contradicted by source.

---

## Findings

1. **NIT — "inside/under Sampling Timepoints" rendered as an adjacent group is a
   presentation compromise, not a literal satisfaction of the request.** Sections
   3 and FR3 place `sampling_details` *immediately before* `timepoints` because
   the schema has no nesting. That is the right call given the schema, and the
   design is transparent about it. It remains a deviation from the user's literal
   "sub section ... inside" wording.
   *Concrete note for implementer:* keep the group `label` as `Sampling details`
   (reads as a sampling sub-heading) and position it directly adjacent to
   `timepoints`; if a stakeholder later insists on visual nesting, that is a
   frontend heading-style change only, as the design already states under Out of
   scope / NFR4. No action required to proceed.

2. **NIT — the literal "Cell no" header row and "Sample weight (mg)" row label are
   not reproduced; cell identity moves into per-field labels.** The design
   (section 3 closing note) renders each cell as a field labelled
   `Cell {n} Sample Weight` with unit `mg`, so the rendered grid reads per-cell
   boxes rather than a two-row "Cell no / Sample weight (mg)" table. This matches
   how `cells` ("Cell {n} Applied Dose") already renders, so it is consistent —
   but a reviewer comparing against the user's verbatim table should know the
   two-row layout is intentionally not built.
   *Concrete note:* acceptable as designed; if the exact two-row label layout is
   required, it is a bespoke frontend widget and a new scope item.

3. **NIT — `_apply_cu30_kedit.py` byte-equality check reads the seed module `d`,
   whereas this task must read the live DB row.** The precedent script asserts
   byte-equality against the in-memory module definition. The design correctly
   requires reading the **live** `TPL-A6D-0001` definition from `lims.db`
   (FR2/FR6 step 1), deep-copying it, then asserting byte-equality of the
   newly-written row against that deep-copied-and-edited dict — not against a seed
   module. The implementer should not copy `_apply_cu30_kedit.py`'s
   `seed.definition` source verbatim; use the DB row as the base. The design says
   this, but the one-line precedent invites a copy-paste slip.
   *Concrete fix:* in the author script, base `definition` on
   `copy.deepcopy(db_row.definition)` and assert the re-read row equals
   `json.dumps(definition, sort_keys=True)` where `definition` is that edited
   copy.

---

## Notes on the three gated areas (summary)

- **DUPLICATION:** mechanism named with evidence (no first-class clone method;
  `create_template` auto-codes; script fallback via `_apply_cu30_kedit.py` /
  `seed_test_templates.py` precedent), concrete code `TPL-A6D-0002` and name
  chosen, `test_id` reused from the source row. Solid.
- **ADD-COLUMN + MIRROR:** correctly diagnosed that no runtime add-column exists
  for A6D (gated to TPL-A6A-0004, hide/restore only), and that `mirrorFrom` is a
  row echo, not a cross-section mechanism. The real contract — per-cell `_{n}`
  fields over one shared range, with `sample_weight_mg_{n}` joining it — is keyed
  consistently (`area_{n}`-style) and mirrors across `cells`/`timepoints`/`flux`
  by construction. Evidence precise (file/line). Solid.
- **SUB-SECTION MODELING:** representation (A) `singleton` group justified against
  the existing `cells` singleton pattern and consistent with the `_{n}` keying;
  alternative (B) rejected with a correct semantic reason (per-cell once, not
  per-timepoint). Solid.
- **SAFETY/VERIFICATION:** NFR1 mandates the timestamped `lims.db` backup before
  any write (naming matches repo convention); verification path names
  `test_seeded_template_parity.py`, `TemplateDefinition.parse` + dry-run
  `evaluate`, byte-equality re-read, and a `start-lims.bat` manual render check.
  All present and correct.
