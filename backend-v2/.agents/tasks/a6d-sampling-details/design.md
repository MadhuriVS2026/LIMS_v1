# TPL-A6D duplicate + "Sampling details" per-cell Sample-weight sub-section

Requirements and technical design. This is an investigation-and-design artifact:
no code or DB was modified while producing it (two throwaway read-only inspection
scripts were created under `scripts/` and deleted again).

---

## Summary

Duplicate the Active template **TPL-A6D-0001 "In-Vitro Release (Franz Diffusion
Cell)" v1** into a new, independent template and, in the duplicate only, add a
new sub-section **"Sampling details"** inside the existing **Sampling Timepoints**
section (group key `timepoints`). The sub-section is a per-cell table:

- a header row labelled **"Cell no"** with columns **Cell-1 … Cell-6**;
- a row **"Sample weight (mg)"** that is a per-cell **blank input** (no pre-filled
  numbers — the user's 257.0 / 229.4 / … are examples only).

The Sample-weight row must (1) support **add-column** the same way the other
per-cell tables in this template do, so the lab can extend to Cell-7, Cell-8, …,
and (2) stay in sync ("mirror") with the per-cell tables below it so every
per-cell section carries the same number of cells.

The investigation below pins down three mechanisms that materially change how
this must be built. The most consequential finding: **there is no runtime
"grow the schema" add-column feature, and the existing hide/restore "Add column"
control is hard-wired to a single template (TPL-A6A-0004), not to A6D.** The
number of cells is fixed by the template definition. "Add column" and
"mirror to the tables below" are therefore **authoring-time decisions baked into
the duplicate's definition**, implemented by keeping every per-cell group over a
single shared cell range. The design makes that range explicit and consistent so
the requirement is satisfiable and future cell-count changes are a one-line edit.

---

## Investigation — evidence

### The live definition (source of truth = `backend-v2/lims.db`)

Read directly from `lims.db`, table `test_templates`. There is exactly one A6D
row:

```
id=26  code=TPL-A6D-0001  name="In-Vitro Release (Franz Diffusion Cell)"
version=1  status=Active  archetype=A6d  result_unit=µg/cm²/√h  test_id=25
```

(Re-verified by reading `lims.db` directly for this pass: `id=26`, `test_id=25`,
and `TPL-A6D-0001` is the **only** `TPL-A6D-%` row, so `TPL-A6D-0002` is in fact
the next free code. The authoring script copies `test_id` from the source row
rather than hard-coding 25, so it stays correct if the Test Master id ever
differs across environments; `test_id=25` is the entry whose test code is
`TST-IVRT`.)

Its stored `definition` JSON is structurally identical to the seed module
`scripts/template_definitions/a6d_franz_ivrt.py` (6 cells, same groups/fields,
same group order `calibration, curve, qc, cells, timepoints, flux`,
`resultRef = flux.mean_flux`; the only `labelFrom` keys present are the three
`rows.labelFrom` on `calibration`/`qc`/`timepoints`; verified absent from the
stored JSON: `hidden`, `mirrorFrom`, `footer`, `headerContext`, `chart`).
Note that `hidden` and `mirrorFrom` are **frontend-only** field flags consumed
by `WorksheetForm.tsx` — the backend `FieldDef.parse` in `template_schema.py`
does not model either, so they are not part of the authoring contract here and
the new group must not rely on them. Groups and per-cell fields in the live row
(field counts re-confirmed: `applied_mg_{n}`=6 in `cells`, `area_{n}`=6 in
`timepoints`, `flux_{n}`=6 in `flux`):

| group | kind | label | rows | per-cell fields |
|---|---|---|---|---|
| `calibration` | table | Calibration Standards | min2/max10/def6 | — |
| `curve` | singleton | Regression | — | — |
| `qc` | table | Bracketing QC Standards | min0/max24/def6 | — |
| `cells` | singleton | Cell Loading | — | `applied_mg_{n}` |
| `timepoints` | sequence | **Sampling Timepoints** | min2/max12/def6 | `area_{n}`, `conc_{n}`, `amount_{n}`, `carry_{n}`, `cumulative_{n}`, `per_area_{n}`, `released_pct_{n}` |
| `flux` | singleton | Release Rate | — | `flux_{n}`, `fit_{n}` |

So **four groups carry per-cell columns**: `cells`, `timepoints`, `flux`, and
(implicitly, by the cross-cell aggregates `mean_per_area`/`rsd_per_area` in
`timepoints` and `mean_flux`/`rsd_flux`/`min_fit` in `flux`) the series lists
built by `_series(prefix)` in the seed module. The "tables below" the new
Sampling-details row are `timepoints`' own calculated per-cell columns and the
`flux` group.

### 1. Duplication / versioning

`src/application/services/test_template_service.py` owns template lifecycle. The
relevant facts:

- **`new_version(template_id, actor)`** branches an *approved* template into a
  new **Draft** that shares the **same `code`**, deep-copies the definition,
  bumps `version` to `max(existing)+1`, and leaves the source untouched. It
  enforces "only one unapproved version per code at a time". This is NOT what we
  want: the task asks for a *distinct* template (its own code), a true duplicate,
  not a v2 of the same code.
- **`create_template(name, archetype, test_id, definition, result_unit, actor)`**
  creates a brand-new **Draft** with a **generated** code via
  `TemplateCodeGenerator.generate(archetype, existing)` — i.e. the code is
  machine-assigned from the archetype prefix and the count of existing codes with
  that prefix; the caller cannot choose it. For archetype `A6d` the generator
  would produce the next `TPL-A6D-00NN`. There is **no service method that clones
  one template into another code with a caller-supplied code.**
- Both `create_template` and `update_definition` run
  `validate_definition()` → `TemplateDefinition.parse` **and** a dry-run
  `WorksheetEvaluator(parsed).evaluate({}, {})`. A definition that cannot compute
  on blank inputs is rejected at authoring time (Property 9).
- The API surface (`src/api/v1/endpoints/test_template_endpoints.py`) mirrors the
  service: `POST /test-templates` (create, Admin only), `PUT
  /test-templates/{id}/definition` (replace a Draft's definition), `POST
  /{id}/submit`, `POST /{id}/approve` (e-signed), `POST /{id}/new-version`,
  `POST /{id}/deactivate`.

**Decision — how to duplicate.** There is no first-class "duplicate into a new
code" helper, so use the established **script fallback** that prior template work
in this repo already used. The precedent is `backend-v2/_apply_cu30_kedit.py`: it
builds the definition dict, runs `TemplateDefinition.parse` + a dry-run
`WorksheetEvaluator(...).evaluate({}, {})`, then writes the row through
`async_session_factory()` and re-reads to assert byte-equality. The same seeding
shape lives in `scripts/seed_test_templates.py` (validate, then insert a
`TestTemplateModel`). The duplicate will be created by a one-off script under
`backend-v2/scripts/` (or `backend-v2/` alongside `_apply_cu30_kedit.py`) that:

1. reads the **live** `TPL-A6D-0001` definition from `lims.db` (not only the seed
   file, because the DB is the source of truth and may have diverged — here it
   happens to match, but the script must read the DB row);
2. `copy.deepcopy`s it and applies the Sampling-details edit (section 3);
3. inserts a new `TestTemplateModel` row with a **new code and name**, `version=1`,
   reusing the **same `test_id`** as TPL-A6D-0001 (test `TST-IVRT`), `archetype`
   `A6d`, `result_unit` `µg/cm²/√h`, `created_by/modified_by="seed"` (or the
   operator), copying `definition`;
4. validates before commit (`parse` + dry-run `evaluate`), and re-reads to assert
   byte-equality, exactly like `_apply_cu30_kedit.py`.

Seed **as `Draft`** (no `approved_by`) and route it through the normal
submit/approve e-sign gate, matching `seed_test_templates.py --draft` guidance —
do **not** stamp it Active/`seed` in a validated flow. If it must be immediately
usable for a demo, Active with `approved_by="seed"` is the documented shortcut,
but flag it.

**Why a script, not the API/`create_template`:** `create_template` refuses a
caller-chosen code (it auto-generates one), and the task requires a specific,
sensible code. The script path lets us set the code explicitly, is the pattern
every prior template change in this repo used against `lims.db`, and keeps the
new row's definition byte-verifiable. If instead an auto-generated code is
acceptable, `create_template` via `POST /test-templates` is viable and would
yield the next free `TPL-A6D-00NN` — but then the name must still be set and the
Sampling-details edit applied via `PUT /{id}/definition` before submit.

**Decision — new code and name.**

- **Code: `TPL-A6D-0002`.** It is the next free number in the A6d archetype
  series (only `-0001` exists), is exactly what `TemplateCodeGenerator.generate`
  would also pick for a new A6d template, and reads unambiguously as "another A6d
  template" rather than a new version of `-0001` (versions share a code; this is
  a distinct template).
- **Name: `In-Vitro Release (Franz Diffusion Cell) — with Sampling Details`.**
  Keeps the recognisable base name and states what distinguishes it, so the
  catalogue list (`GET /test-templates`) is self-explanatory. Bind it to the same
  Test Master entry (`TST-IVRT`, "In-Vitro Release Rate (IVRT)") so it is
  selectable on the same TRF test lines.

### 2. Add-column + cross-section cell mirroring

**How per-cell columns are represented.** There is no "cell range" object in the
stored schema. Each cell is a **separate field** whose key ends in `_{n}`, and the
seed module generates them with `_CELL_RANGE = range(1, 7)`:

- `scripts/template_definitions/a6d_franz_ivrt.py`:
  - `_CELLS = 6`, `_CELL_RANGE = range(1, _CELLS + 1)`.
  - `cells` group: `applied_mg_{n}` for n in range.
  - `timepoints` group: `area_{n}` (`_cell_area_fields`) and the calculated chain
    `conc_{n}`, `amount_{n}`, `carry_{n}`, `cumulative_{n}`, `per_area_{n}`,
    `released_pct_{n}` (`_cell_calculated_fields`).
  - `flux` group: `flux_{n}`, `fit_{n}`.
  - Cross-cell aggregates use `_series(prefix)` → literal list
    `[per_area_1, …, per_area_6]`, `[flux_1, …, flux_6]`, `[fit_1, …, fit_6]`.
  - Per-cell expressions reference the matching index across groups, e.g.
    `released_pct_{n}` reads `cells.applied_mg_{n}`; `flux_{n}` reads
    `timepoints.per_area_{n}`. **The cell-count contract is therefore the set of
    `_{n}` suffixes, and every per-cell group plus every `_series(...)` aggregate
    must use the SAME range** or the engine silently drops or mis-pairs cells.
- `template_schema.py` has no notion of "columns" beyond fields; `GroupDef.fields`
  is a flat tuple and field keys must be valid identifiers and unique within a
  group. Adding Cell-7 = adding fields `*_7` across every per-cell group.

**How the frontend "add column" actually works — the decisive finding.**
`frontend-react/src/features/test-templates/components/WorksheetForm.tsx`:

```ts
// line ~181
const allowClearColumn = detail.worksheet.template_code === 'TPL-A6A-0004';
```

- The **Add column / delete column** controls are **gated to one template code,
  `TPL-A6A-0004`**. For every other template (A6D included) the trash icon and the
  "Add Column" button are not rendered at all (lines ~1258, ~1344).
- Even where enabled, the behaviour is NOT a schema change. `deleteColumn`
  (line ~459) *hides* an input column and blanks its stored values;
  `addColumn` (line ~480) is its exact inverse — it **restores the first
  previously-hidden input column**, bounded by the columns the template already
  provisions. The code comment is explicit: *"There is no runtime schema change —
  only previously-deleted columns can come back."* The list of restorable columns
  is `deletableColumns(group)` = the group's non-hidden **input** fields.
- `mirrorFrom` (the only thing literally called "mirror" in the code) is a
  **row-aligned value echo** between tables *by row index* (e.g. echoing the Time
  column into the %Release table). It is NOT a cross-section cell-count mechanism
  and does not create or remove columns. Do not conflate it with the user's
  "mirror to below tables".
- There is no per-cell table component shared across A6D sections; A6D renders
  through the **generic table/singleton renderer**. (The only bespoke per-cell
  layout, `renderCumulativeVertical`, is hard-gated to `TPL-A6A-0005` and hard-codes
  6 units.)

**Consequence for this task.** "Add column to reach Cell-7/Cell-8" and "mirror to
the tables below" cannot be delivered as a live, user-triggered runtime action for
A6D today — that machinery does not exist for this template. What *is* real and
consistent is the **authoring-time** contract: cell count is whatever set of
`_{n}` fields the definition carries across all per-cell groups. So the
requirement is met by making the new Sample-weight row a **first-class per-cell
field set keyed `sample_weight_mg_{n}` over the same shared range as every other
per-cell group**, so that:

- adding a cell later is a single-point change (extend the range and re-run the
  authoring script), and it automatically adds the matching column to Sampling
  details AND to `cells`, `timepoints` (`area`/calc chain), and `flux` — i.e. it
  mirrors across every per-cell section by construction; and
- if/when the hide/restore "Add column" UI is extended to this template, the
  Sample-weight columns are ordinary input columns and participate automatically
  (they are exactly the `deletableColumns` the control restores).

This is the representation that "matches existing patterns rather than inventing a
new structure": per-cell = `_{n}`-suffixed fields over one range, driven in the
seed/author script by a single `_CELL_RANGE`.

**Every per-cell group that must stay in sync (the mirror set):** `cells`
(`applied_mg_{n}`), `timepoints` (`area_{n}` + `conc/amount/carry/cumulative/
per_area/released_pct_{n}` + the `_series('per_area')` aggregates), `flux`
(`flux_{n}`, `fit_{n}` + the `_series('flux')`/`_series('fit')` aggregates), and
now the new Sampling-details row (`sample_weight_mg_{n}`). The authoring script
must generate all of them from the **same** range constant.

### 3. Sub-section modeling

The schema (`template_schema.py`) and the frontend types
(`frontend-react/.../models/testTemplate.types.ts`) have **no first-class
sub-section / sub-group concept.** A "section" is a `GroupDef`. Within a group the
only sub-structuring that exists is:

- `footer` (computed summary rows under a table),
- `headerContext` (read-only context row above a table),
- `chart` (singleton-only line chart),
- the frontend **shape-heuristic "Set N" blocks** (`models/setBlocks.ts`), which
  split one table's rows into visual blocks — a UI-only read of row data, carrying
  no flag in the definition and naming a template only by heuristic. (See the
  frontend comments and `.agents/tasks/a2-0004-set-blocks/plan.md`.)

The user's "Sampling details" is a *header row + a per-cell input row* — i.e. a
small fixed grid of per-cell values, not repeating rows and not a chart/footer.
Two candidate representations:

- **(A) A new `singleton` group** `sampling_details` placed in the `groups` array
  immediately before `timepoints`, carrying one `sample_weight_mg_{n}` input per
  cell. The generic singleton renderer draws each field as a labelled box, header
  from each field's `label` ("Cell 1" … "Cell 6"); the group `label` is the
  sub-section heading "Sampling details". Blank by default (no `default`).
- **(B) Extra per-cell input fields inside the `timepoints` group.** Rejected:
  `timepoints` is a `sequence` (per-timepoint rows). A sample weight is **per cell,
  once**, not per timepoint — putting it on the sequence would duplicate it on
  every timepoint row and change its meaning. It would also collide with the
  Higuchi math semantics of that group.

**Decision — representation (A): a new `singleton` group `sampling_details`.**
Reasoning:

- It matches the **exact existing pattern** for a per-cell, once-only block: the
  `cells` group ("Cell Loading") is already a `singleton` holding `applied_mg_{n}`.
  Sampling-details is the same shape (per-cell, one value each), so it should be
  the same kind of group. This is the "don't invent a new structure" choice.
- `singleton` renders through the generic grid renderer with per-cell labels as
  column/field headers, giving the "Cell no → Cell-1..Cell-6" header and the
  "Sample weight (mg)" values beneath, consistent with how `cells`/`flux` render.
- It keeps the add-column/mirror keying trivially correct: the fields are plain
  `_{n}` inputs over the shared range, so they join the per-cell mirror set
  (section 2) with no special casing.
- The task says the sub-section is "under" / "inside" the Sampling Timepoints
  section. Schema has no nesting, so model it as its own group positioned
  **adjacent to** `timepoints` (immediately before it) and give it a label that
  reads as a sub-section of sampling. If stricter visual nesting is later
  required, that is a frontend-only concern (a heading style), not a schema change.

Note on the user's wording ("Cell no" header with Cell-1..Cell-6, then a "Sample
weight (mg)" row): in representation (A) the per-cell **field labels** carry the
cell identity ("Cell 1" … "Cell 6") and the **group label** carries "Sampling
details"; the literal "Cell no" / "Sample weight (mg)" row labels are a rendering
detail. The group label will be `Sampling details` and each field label `Cell {n}
Sample Weight` with unit `mg`, matching how `cells` labels `Cell {n} Applied
Dose`. This preserves the per-cell table reading without a bespoke two-row widget.

---

## Functional requirements

- **FR1.** Produce a new template, distinct from TPL-A6D-0001, with code
  **`TPL-A6D-0002`** and name **"In-Vitro Release (Franz Diffusion Cell) — with
  Sampling Details"**, archetype `A6d`, result unit `µg/cm²/√h`, bound to the same
  Test (`TST-IVRT`), `version=1`, created as **Draft**.
- **FR2.** The new template's definition is a deep copy of the **live**
  TPL-A6D-0001 definition (read from `lims.db`), with exactly one addition
  (FR3); nothing else changes.
- **FR3.** Add a new **`singleton` group `sampling_details`**, label "Sampling
  details", positioned in `groups` immediately **before** `timepoints`. It holds
  one **blank** input field per cell: key `sample_weight_mg_{n}`, kind `input`,
  type `number`, unit `mg`, label `Cell {n} Sample Weight`, `required: false`, **no
  `default`** (blank reusable input — the example figures must not be stored).
- **FR4.** The `sample_weight_mg_{n}` fields are generated over the **same single
  cell range** used for every other per-cell group in this template, so cell
  counts stay identical across `sampling_details`, `cells`, `timepoints`, and
  `flux`.
- **FR5.** Extending the cell count (add Cell-7, Cell-8, …) is a single change to
  that one range constant in the authoring script, which simultaneously adds the
  matching `*_{n}` columns to Sampling details and to all per-cell sections below
  (the "mirror"), re-validated and re-written to the DB.
- **FR6.** The duplicate is created via a one-off authoring script under
  `backend-v2/` (pattern: `_apply_cu30_kedit.py` / `seed_test_templates.py`): read
  live definition → deep-copy → add group → `TemplateDefinition.parse` + dry-run
  `WorksheetEvaluator.evaluate({}, {})` → insert new `TestTemplateModel` →
  re-read and assert byte-equality.

## Non-functional requirements

- **NFR1 (safety).** Before any write to `lims.db`, make a timestamped backup
  `lims.db.bak-<slug>-<yyyymmdd-HHMMSS>` following the existing naming (e.g.
  `lims.db.bak-a6dsampling-20261016-HHMMSS`). The DB is gitignored and the source
  of truth; the backup is mandatory and must precede the first change.
- **NFR2 (GxP).** Seed as **Draft** and route through the real submit/approve
  e-sign gate for a validated environment. Only use Active/`approved_by="seed"` as
  a flagged demo shortcut.
- **NFR3 (no regression).** TPL-A6D-0001 (id=26) must be left byte-unchanged; the
  duplicate is a new row with a new code.
- **NFR4.** No frontend code change is required or in scope. The new group renders
  through the existing generic renderer. (The runtime hide/restore "Add column"
  control remains A6A-0004-only; delivering a live per-cell add-column UX for A6D
  would be a separate, larger frontend change and is out of scope — see Out of
  scope.)

## Acceptance criteria

1. `lims.db` contains a row `code='TPL-A6D-0002'`, `version=1`, `status='Draft'`,
   `archetype='A6d'`, `result_unit='µg/cm²/√h'`, `test_id` equal to
   TPL-A6D-0001's `test_id`.
2. Row `id=26` (`TPL-A6D-0001`) is unchanged: same `status='Active'`, same
   `definition` bytes as before the change.
3. `TPL-A6D-0002`'s definition `groups` contains a `singleton` group with
   `key='sampling_details'`, `label='Sampling details'`, positioned immediately
   before the `timepoints` group.
4. That group has exactly `_CELLS` fields `sample_weight_mg_1 … sample_weight_mg_6`
   (for the default 6 cells), each `kind='input'`, `type='number'`, `unit='mg'`,
   and **no `default` key** (verified: a fresh worksheet shows every Sample-weight
   cell blank, not 257.0/229.4/…).
5. The example numbers (257.0, 229.4, 227.0, 218.2, 254.3, 257.2) appear **nowhere**
   in the stored definition.
6. `TemplateDefinition.parse(definition)` succeeds and
   `WorksheetEvaluator(parsed).evaluate({}, {})` returns with
   `has_blocking_failure == False` and `reportable_result` empty, for the new
   definition (same two-pass validation the service applies).
7. Cell-count parity: the count of `sample_weight_mg_{n}` fields equals the count
   of `applied_mg_{n}` in `cells`, of `area_{n}` in `timepoints`, and of `flux_{n}`
   in `flux`. (Test asserts all four ranges are identical.)
8. Incrementing the range constant to 7 and re-running the authoring script yields
   `sample_weight_mg_7` AND `applied_mg_7`, `area_7` (+ calc chain `_7`),
   `flux_7`/`fit_7`, with the `_series(...)` aggregates including the new index —
   demonstrating the mirror. (May be shown in a throwaway dry-run, not committed.)
9. A mandatory `lims.db.bak-a6dsampling-<ts>` backup exists, created before the
   write.
10. `pytest tests/calculation/test_seeded_template_parity.py` still passes
    unchanged (it reads the seed modules, which this task does not alter for the
    existing A6D; if the duplicate is also captured as a seed module, its new
    `sample_weight_mg_{n}` inputs must not break the catalogue-wide invariants —
    they are plain inputs, so they do not).

## Out of scope

- A live, user-triggered **runtime** add-column/mirror UX for A6D. The existing
  control is a hide/restore of pre-provisioned columns gated to TPL-A6A-0004; a
  generic dynamic-cell feature across sections is a separate design.
- Any change to TPL-A6D-0001 itself, to the calculation engine, to
  `template_schema.py`, or to the frontend components.
- Capturing the duplicate as a permanent declarative seed module (optional
  follow-up; the worklog notes DB template edits are not yet all mirrored into
  seed source).
- Wiring the Sample weight into any calculation (flux, release %). The user asked
  for a blank reusable input only; no formula references it. If a formula is later
  wanted (e.g. per-cell applied-dose cross-check), that is a new requirement.

---

## Implementation notes for the implementer (concrete)

1. **Backup first.** Copy `backend-v2/lims.db` to
   `backend-v2/lims.db.bak-a6dsampling-<yyyymmdd-HHMMSS>` before opening a write
   session. (`Copy-Item lims.db lims.db.bak-a6dsampling-<ts>`.)
2. **Author script** (place next to `_apply_cu30_kedit.py`, async, uses
   `async_session_factory`):
   - `SELECT` the live `TPL-A6D-0001` row; `definition = copy.deepcopy(row.definition)`.
   - Define `CELL_RANGE = range(1, 7)` once. Build the new group:
     ```python
     sampling_details = {
         "key": "sampling_details",
         "kind": "singleton",
         "label": "Sampling details",
         "fields": [
             {
                 "key": f"sample_weight_mg_{n}",
                 "kind": "input",
                 "type": "number",
                 "label": f"Cell {n} Sample Weight",
                 "unit": "mg",
                 # no "default" → blank reusable input
             }
             for n in CELL_RANGE
         ],
     }
     ```
   - Insert it into `definition["groups"]` immediately before the `timepoints`
     group (find its index by `key == "timepoints"`).
   - Validate: `parsed = TemplateDefinition.parse(definition)` then
     `WorksheetEvaluator(parsed).evaluate({}, {})` — abort on any exception.
   - Insert a new `TestTemplateModel(code="TPL-A6D-0002", name="In-Vitro Release
     (Franz Diffusion Cell) — with Sampling Details", archetype="A6d",
     test_id=<same as -0001>, version=1, status="Draft", result_unit="µg/cm²/√h",
     definition=definition, approved_by=None, created_by="seed",
     modified_by="seed")`. Do NOT touch row id=26.
   - Commit, re-read the new row, assert `json.dumps(new.definition, sort_keys=True)
     == json.dumps(definition, sort_keys=True)` (byte-equality, per the
     `_apply_cu30_kedit.py` precedent).
3. **Verify.**
   - Re-run the backup-diff mentally: id=26 untouched.
   - `python -m scripts.seed_test_templates --validate-only` (if the duplicate is
     also added as a seed module) and/or a small script calling
     `TemplateDefinition.parse` + `evaluate` on the new row.
   - `pytest tests/calculation/test_seeded_template_parity.py`.
   - Launch via `start-lims.bat`, open the new template's worksheet, confirm the
     "Sampling details" section shows Cell-1..Cell-6 Sample-weight inputs, all
     blank, and that the existing IVRT math is unchanged.
4. **Edge cases / validation rules for the new input.**
   - `sample_weight_mg_{n}`: optional (`required: false`), numeric, no default →
     renders blank. Non-numeric entry is prevented by the numeric input control;
     blank → stays blank and feeds nothing (no formula depends on it), so an empty
     Sampling-details section never blocks the result or raises an evaluation
     error. This is confirmed safe by AC6 (dry-run on empty values passes).
   - Range mismatch is the one real failure mode: if a future edit adds
     `sample_weight_mg_7` but not `applied_mg_7`/`area_7`/`flux_7`, the sections
     fall out of sync. The invariant (AC7) and the single-`CELL_RANGE` rule in the
     script are what prevent it; keep the range as one constant used by every
     per-cell group.

## Testability

- **Unit-level (no DB):** build the edited definition dict in-memory and assert
  `TemplateDefinition.parse` + `WorksheetEvaluator.evaluate({}, {})` succeed, and
  that the four per-cell ranges match (AC6, AC7). This mirrors
  `test_seeded_template_parity.py`'s style and needs no database.
- **DB-level:** after the script, re-read both rows and assert id=26 unchanged and
  TPL-A6D-0002 present with the new group (AC1–AC5, AC9). Byte-equality check as in
  `_apply_cu30_kedit.py`.
- **Mirror demonstration:** a throwaway run with `CELL_RANGE = range(1, 8)` showing
  `_7` fields appear across all per-cell groups (AC8) — do not commit that row.
- Hard-to-test: the live frontend rendering (manual check via `start-lims.bat`).
  Everything else is deterministic and scriptable.
