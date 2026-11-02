# Design — "STD Area in Media" dynamic media columns (TPL-A3-0001 v1 only)

## Overview

This design makes the media columns of **one** table — the "STD Area in Media"
table on template **TPL-A3-0001 v1, "Saturation Solubility by HPLC"** (archetype
A3, test TST-SOLB) — into a per-column wide table with **up to ten** media columns
(`media_1 … media_10`), each column's heading editable per-worksheet,
add/edit/delete column controls, and a Mean/SD/%RSD footer per media column.
Nothing else in this template or any other template changes.

The work is a **template-definition edit** (the single-`area` `std_areas` table
becomes a multi-column media table with a per-column statistics group and a
one-row "Media Name" heading group), plus a small, **template-scoped** frontend
enablement to turn on the existing add/delete-column control for this template
(scoped so **only the trailing media column** can be deleted — see Decision 3),
and one **in-definition blocking criterion** that keeps the reference medium
(`media_1`) from being left blank (see Decision 4). The per-worksheet media-name
heading text rides on top of the definition purely for display via the existing
`labelFrom` mechanism; renames are never written back into the template
definition.

**Column count (user scope, this iteration).** The provisioned set is **ten**
media columns. The screenshot showed six populated media, so **six columns
(`media_1 … media_6`) are visible by default** and the remaining four
(`media_7 … media_10`) are **provisioned-but-hidden**, reachable through "Add
Column" up to the tenth. Only the media **column** count grows to ten; the
standard-injection **rows** are unchanged (`Standard - 1 … 6`).

The chosen heading approach is **Option 1** (confirmed, not re-litigated): a
per-worksheet "Media Name" input whose per-media cells drive each column header
through `labelFrom`, falling back to the static label ("Media 1" … "Media 10")
when a cell is blank. Note (see Decision 1, Finding 2) that this heading input
renders as its own "Media Name" card with ten boxes (the six default-visible ones
plus the four restored by Add Column), not as an in-table heading strip aligned
to the columns; the column-renaming behaviour is identical either way.

---

## GROUND TRUTH — what the DB actually contains (read, not assumed)

I queried the SQLite `test_templates.definition` JSON for `TPL-A3-0001` in both
the worktree DB (`d:\RD-instance\GIT\.worktrees\satsol-media-columns\backend-v2\lims.db`)
and the user's live DB (`d:\RD-instance\GIT\backend-v2\lims.db`). **Both DBs' TPL-A3-0001
definition JSON is byte-identical (length 4177) and both still hold the original
seed shape.** (The two DBs' *worksheet 53* data differs — see Key facts below.) There is
**no** "STD Area in Media" table, no Media 1..6 columns, no "Media Name" row, no
Standard-1..6 media rows, no Mean/SD/RSD media footer, and **no `labelFrom`** on
this template today.

Verification performed:
- `SELECT ... WHERE definition LIKE '%STD Area in Media%'` → **zero rows** across
  the whole catalogue.
- `... LIKE '%Media Name%'` → **zero rows**.
- `... LIKE '%labelFrom%'` → 32 templates, **TPL-A3-0001 is NOT among them**.
- Direct marker check on TPL-A3-0001: `has_labelFrom=0`, `has_media=0`,
  `has_"Standard Replicate Injections"=1`.

> **Correction to the task premise.** The task states the LIVE DB's TPL-A3-0001
> already has the "STD Area in Media" table with Media 1..6, a Media Name row,
> Standard-1..6 rows and Mean/SD/RSD footers, and that only the *generification*
> remains. That is **not** what either DB contains. The live DB TPL-A3-0001 is
> still the plain seed: a single `std_areas` table with one `area` column labelled
> "Standard Replicate Injections". This design therefore **builds the media table
> from scratch** (matching the user's screenshot in messages 1–3) and generifies
> it in the same edit, rather than refactoring an existing media table. Every
> downstream decision below is made against the *observed* shape, as required.

### Exact observed TPL-A3-0001 definition (abridged to the relevant group)

```jsonc
{
  "resultRef": "samples.mean_solubility",
  "context": [ /* generic_name, batch_no, medium, temperature_c, method_no,
                  instrument_id, analysed_by, date_of_analysis */ ],
  "groups": [
    { "key": "standard", "kind": "singleton", "label": "Standard Details",
      "fields": [ /* name, weight_mg, vol_1..vol_3, pip_1..pip_2, mw_base,
                     mw_salt, potency, conc_ppm(calculated, ppm) */ ] },

    // ── THE TABLE IN SCOPE, as it exists today ──
    { "key": "std_areas", "kind": "table", "label": "Standard Replicate Injections",
      "rows": { "min": 1, "max": 6, "default": 5 },
      "fields": [ { "key": "area", "kind": "area", "label": "STD Area" } ],
      "footer": [
        { "label": "Mean",  "ref": "stats.mean_std" },
        { "label": "SD",    "ref": "stats.sd_std" },
        { "label": "% RSD", "ref": "stats.rsd_std", "unit": "%" }
      ] },

    { "key": "stats", "kind": "singleton", "label": "Standard Statistics",
      "fields": [
        { "key": "mean_std", "kind": "calculated", "label": "Mean STD Area",
          "expression": "mean(std_areas.area)" },
        { "key": "sd_std",   "kind": "calculated", "label": "SD",
          "expression": "sd(std_areas.area)" },
        { "key": "rsd_std",  "kind": "calculated", "label": "%RSD", "unit": "%",
          "expression": "rsd(std_areas.area)" }
      ] },

    { "key": "samples", "kind": "table", "label": "Saturated Solution Preparations",
      "rows": { "min": 1, "max": 12, "default": 3 },
      "fields": [ /* prep_ref, time_point, aliquot_ml, diluted_to_ml,
                     area, solubility(calculated), mean_solubility(calculated) */ ] }
  ],
  "criteria": [
    { "key": "sst_std_rsd", "target": "stats.rsd_std", "operator": "lte",
      "limit": 2.0, "severity": "blocking", "limitText": "NMT 2.0 %" },
    { "key": "prep_agreement", "target": "rsd(samples.solubility)",
      "operator": "lte", "limit": 5.0, "severity": "advisory", "limitText": "NMT 5.0 %" }
  ]
}
```

Key facts that constrain the design:
- **Group key of the table in scope:** `std_areas`.
- **Field key today:** a single `area` (kind `area`).
- `stats` (singleton) owns the Mean/SD/%RSD, computed over `mean/sd/rsd(std_areas.area)`.
- The table footer references `stats.mean_std` / `stats.sd_std` / `stats.rsd_std`.
- The downstream `samples.solubility` expression divides by `stats.mean_std`.
- **One worksheet exists** on this template: id **53**, status **InProgress**.
  Its stored `group_values` **differs between the two DBs** (re-queried this
  iteration — see the correction below):
  - **Live DB (`backend-v2\lims.db`, the one that is edited):** `group_values` is
    **NOT empty**. It holds real `standard` data (one row: Semaglutide API,
    weight 32.17 mg, the vol/pip/mw/potency fields), a `std_areas` array of
    **five rows each `{"area": null}`** (the OLD single-`area` shape, all blanks),
    a `stats` array `[{}]`, and a `samples` array of three rows with partial
    prep data (all `area` null). **No numeric STD-area data is stored anywhere**
    — the only `std_areas` cells are `area: null`.
  - **Worktree DB (`.worktrees\satsol-media-columns\backend-v2\lims.db`):**
    `group_values = '{}'` (empty).
  Consequence for migration: the shape change touches **only** `std_areas`
  (single `area` field → `std_label` + `media_1..10`). Its five stored rows carry
  **no value** (`area: null`), so rewriting them to the new shape orphans nothing
  of substance; `standard`, `stats` and `samples` keep their keys and fields and
  are left byte-for-byte intact. This is why the edit is safe despite the live
  worksheet being non-empty — see Decision 5 for the exact, data-preserving write.

### The pattern to reuse — TPL-A2-0004 (the project's canonical multi-column wide table)

TPL-A2-0004's `std_areas` table is exactly the shape this design mirrors — a
wide table with **one explicit field key per column**, each carrying a
`labelFrom`, a **column-aligned** footer, and a per-column `stats` singleton:

```jsonc
{ "key": "std_areas", "kind": "table", "label": "Standard Replicate Injections",
  "rows": { "min": 1, "max": 12, "default": 6, "labelFrom": "inj_label" },
  "fields": [
    { "key": "inj_label", "kind": "input", "type": "text", "label": "Injection" },
    { "key": "tri_area",  "kind": "area", "label": "Tricaprylin Area", "labelFrom": "standard.name[0]" },
    { "key": "dppg_area", "kind": "area", "label": "DPPG Na Area",     "labelFrom": "standard.name[1]" },
    { "key": "chol_area", "kind": "area", "label": "Cholesterol Area", "labelFrom": "standard.name[2]" },
    { "key": "depc_area", "kind": "area", "label": "DEPC Area",        "labelFrom": "standard.name[3]" }
  ],
  "footer": [
    { "label": "Mean",  "ref": "stats.mean_std_tri" }, { "ref": "stats.mean_std_dppg" }, { "ref": "stats.mean_std_chol" }, { "ref": "stats.mean_std_depc" },
    { "label": "SD",    "ref": "stats.sd_std_tri" },   { "ref": "stats.sd_std_dppg" },   { "ref": "stats.sd_std_chol" },   { "ref": "stats.sd_std_depc" },
    { "label": "% RSD", "ref": "stats.rsd_std_tri", "unit": "%" }, { "ref": "stats.rsd_std_dppg", "unit": "%" }, { "ref": "stats.rsd_std_chol", "unit": "%" }, { "ref": "stats.rsd_std_depc", "unit": "%" }
  ] }
```

with a `stats` singleton carrying `mean_std_tri = mean(std_areas.tri_area)`,
`sd_std_tri = sd(std_areas.tri_area)`, etc., one trio per column. **This design
copies that structure precisely**, substituting media columns for compound
columns and sourcing the `labelFrom` from the Media Name heading row instead of
`standard.name[i]`.

---

### Verification performed THIS iteration (independent re-check — iteration 4)

New load-bearing checks made this iteration, against the worktree source, for the
three scope/finding changes folded in (10 columns, trailing-only delete, and the
in-definition `media_1` criterion):

- **Column-aligned footer IS positional (confirms the review's HIGH finding).**
  `renderGroupFooter` in `WorksheetForm.tsx` builds `const valueColumns =
  visibleFields.slice(1)` and renders `valueColumns.map((field, c) => { const cell
  = row.cells[c]; … })`. The footer value for column `c` is `row.cells[c]` — a
  **positional** index into the footer refs, not a field-keyed lookup. Deleting a
  **middle** column removes it from `visibleFields` (which collapses the gap)
  while `row.cells` (the six/ten `stats.mean_mN` refs) is unchanged, so every
  later column would read the wrong column's stat. This is exactly why the chosen
  fix is **delete-trailing-only** (Decision 3): end-slicing stays aligned because
  dropping the last visible column drops the last footer cell position too.
- **`count` function (`expression.py`).** The registry maps `"count" → _f_count`,
  and `_f_count(args) = float(len(_numeric(args)))` — it counts the **numeric
  (non-blank)** values in the range and **always returns a number** (0.0 for an
  all-blank column), never `EMPTY`. So a criterion `count(std_areas.media_1)` is
  always assessable (see Decision 4).
- **Blocking-criteria path (`template_schema.py` + `evaluator.py`).**
  `CriterionDef` has `target` (an **expression**, exactly like the existing
  `prep_agreement` target `rsd(samples.solubility)`), `operator`, `limit`,
  `severity` (default `blocking`), `limitText`. `Operator.GTE = "gte"` exists.
  `_evaluate_criteria` computes `observed = evaluate(criterion.target, scope)` and
  `_assess` returns `value >= limit[0]` for `GTE`; `is_blocking_failure =
  severity is BLOCKING and passed is False`. So a **blocking** criterion
  `count(std_areas.media_1) gte 1` fails (blocks) whenever zero `media_1` cells
  are numeric and passes once ≥1 is entered — the in-definition enforcement that
  replaces the previously-mandated completion-time seam (Decision 4).
- **`FieldDef.parse` accepts `required` and ignores `labelFrom`.** `required=
  bool(raw.get("required", False))`; unknown keys (`labelFrom`) are not read, so
  the engine parses the field-level `labelFrom` cleanly. Confirmed.
- **`RowSpec` has only `min/max/default/label_from`** (re-confirmed) — no
  `rows.seed`; captions are still seeded via `group_values` (unchanged from the
  approved iteration-3 decision).
- **Trash-icon render site.** The per-column delete icon is rendered **inside**
  `visibleFields.map((field) => …)` in the table `<thead>`, so the guard has
  `visibleFields` (definition-ordered) in scope and can compare `field.key`
  against the highest-numbered visible `media_N` to expose the icon on the
  trailing column only (Decision 3).
- **Empirical end-to-end check of the full 10-column definition (run this
  iteration, not asserted).** I built the complete generified definition exactly
  as specified in Decisions 1/2/4 (ten `media_names` cells, ten `std_areas` area
  fields with field-level `labelFrom`, ten `stats` trios, the thirty-ref
  column-aligned footer, `samples.solubility` divided by `stats.mean_m1`,
  `sst_std_rsd` on `stats.rsd_m1`, and the new `media1_present` criterion), then
  ran it through the **worktree** `TemplateDefinition.parse` and
  `WorksheetEvaluator`. Results, all green:
  1. **Parses** — 5 groups, 3 criteria, `resultRef = samples.mean_solubility`.
  2. **`area_field_refs`** returns exactly the ten `('std_areas','media_1..10')`
     pairs plus `('samples','area')`.
  3. **Per-column independence + blank tolerance** — with `media_1..5` populated
     with distinct values and `media_6..10` blank, each `stats.mean_mN` equals its
     own column's mean and `stats.mean_m6..m10` are `EMPTY`. This is the
     trailing-delete scenario: blanking the trailing columns leaves the remaining
     columns' stats untouched.
  4. **Reportable repoint** — `samples.solubility` and `mean_solubility` compute
     off `stats.mean_m1`.
  5. **`media1_present` blocking criterion** — with `media_1` all-blank,
     `count(std_areas.media_1) == 0`, `passed is False`, `is_blocking_failure is
     True`, and `reportable_result is EMPTY`; with one `media_1` cell numeric,
     `count == 1`, `passed is True`, not blocking.
  6. **Screenshot parity** — feeding the user's five Media-1 standard areas
     (1264265 / 1266600 / 1267571 / 1267739 / 1266671) reproduces **Mean 1266569,
     SD 1386.78, %RSD 0.11** exactly. (Temporary verification scripts were removed
     after the run.)

Every load-bearing claim below was re-confirmed by reading the live code/DB in a
prior iteration and still holds:

1. **DB shape (both DBs).** Live `backend-v2/lims.db` and worktree
   `.worktrees/satsol-media-columns/backend-v2/lims.db` are byte-identical for
   TPL-A3-0001 (id 3, v1, definition length **4177**). Markers: `labelFrom`=absent,
   `Media Name`=absent, `STD Area in Media`=absent, `Standard Replicate
   Injections`=present, `media_`=absent. `std_areas` has a single `area` field;
   `stats` holds `mean_std/sd_std/rsd_std` over `std_areas.area`;
   `samples.solubility` divides by `stats.mean_std`; criteria target
   `stats.rsd_std` and `rsd(samples.solubility)`. **Confirms the task premise is
   wrong and the table is built from scratch.**
2. **Worksheet (CORRECTED this iteration).** The table is `test_worksheets`
   (joined via `template_id`). The one A3 worksheet is **id 53, InProgress**, but
   its `group_values` is **not** the empty `'{}'` the prior draft and the review
   both assumed. Re-queried directly this iteration: the **live** DB worksheet 53
   stores real `standard` and `samples` data plus a five-row `std_areas` array of
   `{"area": null}` (old shape, all blank) and `stats: [{}]`; the **worktree** DB
   worksheet 53 is `'{}'`. Because the shape change touches only `std_areas` and
   its five stored cells are all `area: null`, the migration is a targeted,
   value-preserving rewrite of `std_areas` only (Decision 5), not a no-op — this
   correction is the root of this iteration's revisions to Decisions 1 and 5.
3. **Pattern (A2-0004).** `std_areas` is a wide area table with field-level
   `labelFrom` (`standard.name[0..3]`) and `rows.labelFrom: "inj_label"`. Its
   stored singleton `standard` is a **multi-row** array — the shape contrast that
   motivates the explicit one-row `media_names` note in Decision 1.
4. **Engine functions.** `expression.py`: `mean` → EMPTY on empty; `sd`/`rsd` →
   EMPTY when `len(nums) < 2`; `rsd` → EMPTY when mean==0. Engine is blank-tolerant.
5. **Schema parse.** `template_schema.py`: `ValueType.TEXT` and `FieldKind.AREA`
   exist; `FieldDef.parse` ignores unknown keys (field-level `labelFrom` is safe);
   `GroupDef.parse` requires table `rows.labelFrom` to be one of the group's
   fields (`std_label` qualifies); `area_field_refs` returns every AREA
   `(group,field)` pair → the six `std_areas.media_N` post-edit.
6. **Frontend.** `allowClearColumn = … === 'TPL-A6A-0004'` (single gate, as
   quoted). `EDITABLE_KINDS = {'input','area'}`, so both `area` and `input`
   columns show the delete icon — hence the `std_label` guard is required.
   `deleteColumn` blanks+hides with the "template field is untouched; per-worksheet
   UI action" comment; `addColumn`/`deletableColumns`/`hiddenCountFor` behave as
   described; `resolveLabelFrom` reads `[groupKey][idx][fieldKey]`;
   `isColumnAlignedFooter`/`groupFooterRows` exist in `models/groupFooter.ts`.
7. **Parity.** `TestA3SaturationSolubility` in
   `tests/calculation/test_seeded_template_parity.py` exists and feeds
   `std_areas:[{area:50000},{area:50000}]`, asserting `conc_ppm==1000`,
   `solubility==5.0`, reportable `==5.0`, sourced from `SEED_TEMPLATES` (not the
   DB) — so the DB-only edit leaves it green, as Decisions 4/5 state.

## Technology stack (locked)

- **Backend / template store:** Python 3, SQLAlchemy over SQLite (`test_templates.definition`
  is a JSON column). Calc engine in `backend-v2/src/domain/services/calculation/`
  (`template_schema.py`, `evaluator.py`, `expression.py`). Functions available in
  expressions include `mean`, `sd`, `rsd` (confirmed in use).
- **Frontend:** React + TypeScript, PrimeReact, in `frontend-react`. The generic
  worksheet renderer is `src/features/test-templates/components/WorksheetForm.tsx`;
  types in `src/features/test-templates/models/testTemplate.types.ts`.
- **No new technology, library, component, or mechanism is introduced.** The
  column dynamics reuse the `labelFrom`/`headerText` path and the
  `hiddenColumns` add/delete-column path that already ship in commit `c436559`.

---

## Decision 1 — How a "dynamic set of media columns" is represented

**Decision:** Represent the media columns as a **fixed provisioned set of ten
explicit per-media field keys** (`media_1 … media_10`) inside a single table
group, exactly as TPL-A2-0004 provisions its compound columns. There is no
variable-length column array in the schema or the engine — the engine's
`mean/sd/rsd` each take **one** concrete column reference, so a column must be a
declared field key. "Dynamic" is delivered at the worksheet level by
**showing/hiding** columns within that provisioned set (Decision 3), not by
mutating the stored column list at runtime. **Six columns are visible by default**
(matching the screenshot); `media_7 … media_10` are provisioned-but-hidden and
restored one at a time via "Add Column".

### Target generified definition (the edit to apply)

Rename the in-scope table and give it ten media columns plus a leading
`std_label` text column for the "Standard - N" row labels. Add a dedicated
one-row **`media_names`** singleton that holds the editable per-column heading
cells; its ten cells drive the column headers via `labelFrom`.

```jsonc
// ── NEW one-row heading group (Option 1: the "Media Name" row) ──
{ "key": "media_names", "kind": "singleton", "label": "Media Name",
  "fields": [
    { "key": "media_1",  "kind": "input", "type": "text", "label": "Media 1" },
    { "key": "media_2",  "kind": "input", "type": "text", "label": "Media 2" },
    { "key": "media_3",  "kind": "input", "type": "text", "label": "Media 3" },
    { "key": "media_4",  "kind": "input", "type": "text", "label": "Media 4" },
    { "key": "media_5",  "kind": "input", "type": "text", "label": "Media 5" },
    { "key": "media_6",  "kind": "input", "type": "text", "label": "Media 6" },
    { "key": "media_7",  "kind": "input", "type": "text", "label": "Media 7" },
    { "key": "media_8",  "kind": "input", "type": "text", "label": "Media 8" },
    { "key": "media_9",  "kind": "input", "type": "text", "label": "Media 9" },
    { "key": "media_10", "kind": "input", "type": "text", "label": "Media 10" }
  ] },

// ── The in-scope table, generified and renamed ──
// NOTE: there is NO `rows.seed` key — RowSpec supports only min/max/default/
// labelFrom (verified, see "Row captions" below). The "Standard - N" captions
// are seeded into worksheet 53's group_values by the DB edit, not by the schema.
{ "key": "std_areas", "kind": "table", "label": "STD Area in Media",
  "rows": { "min": 1, "max": 6, "default": 6 },
  "fields": [
    { "key": "std_label", "kind": "input", "type": "text", "label": "Standard" },
    { "key": "media_1",  "kind": "area", "label": "Media 1",  "required": true, "labelFrom": "media_names.media_1[0]" },
    { "key": "media_2",  "kind": "area", "label": "Media 2",  "labelFrom": "media_names.media_2[0]" },
    { "key": "media_3",  "kind": "area", "label": "Media 3",  "labelFrom": "media_names.media_3[0]" },
    { "key": "media_4",  "kind": "area", "label": "Media 4",  "labelFrom": "media_names.media_4[0]" },
    { "key": "media_5",  "kind": "area", "label": "Media 5",  "labelFrom": "media_names.media_5[0]" },
    { "key": "media_6",  "kind": "area", "label": "Media 6",  "labelFrom": "media_names.media_6[0]" },
    { "key": "media_7",  "kind": "area", "label": "Media 7",  "labelFrom": "media_names.media_7[0]" },
    { "key": "media_8",  "kind": "area", "label": "Media 8",  "labelFrom": "media_names.media_8[0]" },
    { "key": "media_9",  "kind": "area", "label": "Media 9",  "labelFrom": "media_names.media_9[0]" },
    { "key": "media_10", "kind": "area", "label": "Media 10", "labelFrom": "media_names.media_10[0]" }
  ],
  "footer": [
    { "label": "Mean",  "ref": "stats.mean_m1" }, { "ref": "stats.mean_m2" }, { "ref": "stats.mean_m3" }, { "ref": "stats.mean_m4" }, { "ref": "stats.mean_m5" }, { "ref": "stats.mean_m6" }, { "ref": "stats.mean_m7" }, { "ref": "stats.mean_m8" }, { "ref": "stats.mean_m9" }, { "ref": "stats.mean_m10" },
    { "label": "SD",    "ref": "stats.sd_m1" },   { "ref": "stats.sd_m2" },   { "ref": "stats.sd_m3" },   { "ref": "stats.sd_m4" },   { "ref": "stats.sd_m5" },   { "ref": "stats.sd_m6" },   { "ref": "stats.sd_m7" },   { "ref": "stats.sd_m8" },   { "ref": "stats.sd_m9" },   { "ref": "stats.sd_m10" },
    { "label": "% RSD", "ref": "stats.rsd_m1", "unit": "%" }, { "ref": "stats.rsd_m2", "unit": "%" }, { "ref": "stats.rsd_m3", "unit": "%" }, { "ref": "stats.rsd_m4", "unit": "%" }, { "ref": "stats.rsd_m5", "unit": "%" }, { "ref": "stats.rsd_m6", "unit": "%" }, { "ref": "stats.rsd_m7", "unit": "%" }, { "ref": "stats.rsd_m8", "unit": "%" }, { "ref": "stats.rsd_m9", "unit": "%" }, { "ref": "stats.rsd_m10", "unit": "%" }
  ] }
```

**Default-visible set via an initial `hiddenColumns` seed, NOT the definition
`hidden` flag.** The obvious shortcut — marking `media_7 … media_10` with
`"hidden": true` in the definition — does **not** work with the existing add/
delete machinery and is rejected after reading the code: `deletableColumns`
filters `(f) => !f.hidden && isEditableField(f)`, so a definition-`hidden` field
is **excluded** from the restore set, and `hiddenCountFor`/`addColumn` only ever
operate over `deletableColumns`. A definition-`hidden` media column could
therefore never be brought back via "Add Column" — the exact opposite of the
requirement. (`f.hidden` in this codebase means "intermediate, never rendered",
per the renderer comment at the `editableFields`/`calculatedFields` filters.)

Instead, all ten media columns are provisioned as **ordinary (non-`hidden`)
fields**, and the **default-six view is produced by seeding the per-worksheet
`hiddenColumns` runtime state** with `std_areas.media_7 … std_areas.media_10` when
a TPL-A3-0001 worksheet opens. `hiddenColumns` is the same UI-only
`Set<"group.field">` that `deleteColumn` writes and `addColumn` clears; seeding it
on mount puts the four trailing columns in the identical state as if the analyst
had deleted them, so: `visibleFields` drops them (default six render), they count
toward `hiddenCountFor` (so "Add Column" is enabled, "4 hidden"), and `addColumn`
restores `media_7`, then `media_8`, … in definition order. This is a small,
**template-scoped** frontend addition (a lazy initial value for the
`hiddenColumns` state, gated to TPL-A3-0001) and is folded into this task's
frontend scope alongside the `allowClearColumn` gate and the trailing-delete
guard (Decision 3). It writes no definition and no new persisted state; a
worksheet the analyst later grows to ten columns simply carries fewer entries in
`hiddenColumns`, exactly like the existing feature.

> **Why this is acceptable as "in scope".** The prior iterations scoped the
> frontend to "one-line gate + field guard". This iteration's 6→10 + default-six
> requirement makes a seeded initial `hiddenColumns` the only correct way to get
> "visible-by-default six, the rest reachable via Add Column" without a definition
> mechanism the renderer does not honour. It is still a small, template-scoped,
> UI-only change (no new component, no new hook, no definition write), so it stays
> within the spirit of the minimal-frontend constraint. The alternative —
> rendering all ten by default and asking the analyst to delete the unused four —
> was considered and rejected because it contradicts the user's explicit
> "default six, rest via Add Column" instruction.

The column-aligned **footer carries all ten `stats.*_mN` refs in column order**;
because the footer renderer is positional (`row.cells[c]` for `valueColumns[c]`),
the footer cells line up 1:1 with the visible media columns **only when the
hidden columns form a trailing suffix** — which is exactly what the seeded-hidden
trailing four and the trailing-only delete guard (Decision 3) guarantee. A hidden
trailing column drops both its `visibleFields` entry and (being last) its
footer-cell position together, so alignment is preserved; only a *middle* hide
would break it, and the delete guard makes a middle hide impossible. See
Decision 2/3 for the full correctness argument.

The `std_label` column has **no `default`** and the `rows` block carries **no
`seed` and no `labelFrom`** — both were removed in a prior iteration because
neither is a real mechanism (see "Row captions" below). The six "Standard - N"
captions are seeded by writing them into worksheet 53's stored `group_values` as
part of the same DB edit (Decision 5), which is the only seeding path the renderer
and evaluator actually honour.

Notes:
- **Six rows default** (`min:1, max:6, default:6`) so Standard-1 … Standard-6
  render, matching the screenshot (Standard-6 may be left blank, as in the data).
  This is the **row** count (standard injections); it is independent of the media
  **column** count (ten provisioned, six visible by default).
- **Row captions ("Standard - 1 … 6") are SEEDED INTO `group_values`, not via any
  schema key** (resolves review Findings 1, 2, 3). The screenshot's "Standard - N"
  captions are fixed structure, but there is **no `rows.seed` / `RowSpec.seed`
  schema mechanism** — I verified this iteration that `RowSpec` in
  `template_schema.py` is a frozen dataclass with only `min/max/default/
  label_from`, that `RowSpec.parse` reads only those keys (a `seed` key is
  silently dropped), and that a workspace search for `seed` in the calculation
  package finds only the evaluator's unrelated `_seed_rows`/"Seed context"
  comments. The frontend `RowSpec` (`testTemplate.types.ts`) likewise has only
  `min/max/default/labelFrom`. The prior draft's claim that `RowSpec.seed` exists
  and was "verified" was **wrong and is retracted**.

  The only seeding paths that actually run are: the evaluator's `_seed_rows`,
  which fills each cell from the stored `group_values[group][i][field]`, else the
  field's scalar `default`, else `EMPTY`; and the frontend `seedValues`, which
  fills from `source[field.key] ?? field.default`. A single scalar `default`
  cannot carry six distinct per-row captions. **Therefore the captions are seeded
  by writing them into worksheet 53's stored `group_values["std_areas"]` as part
  of the DB edit** (the exact write is in Decision 5): six rows, each
  `{ "std_label": "Standard - N", "media_1": null, … "media_6": null }`. Because
  the renderer and evaluator both read stored `group_values` first, worksheet 53
  then opens with the `std_label` column pre-filled "Standard - 1 … Standard - 6".

  Scope note: this seeds **only the one existing worksheet (53)**. Any *future*
  TPL-A3-0001 worksheet would open with a blank `std_label` column (there is no
  template-level default for it), and the analyst would type the captions — which
  is acceptable because `std_label` is an ordinary editable input column and the
  captions are display-only (they never enter an expression). Implementing
  template-level per-row caption defaults for all future worksheets would require
  real `RowSpec.seed` support in both the Python schema and the TS types plus
  `seedValues`/`_seed_rows` — a schema+renderer change **outside** this task's
  frontend scope (the gate, the trailing-delete guard, and the default-six
  `hiddenColumns` seed — see Decision 3), and explicitly **not** undertaken here. It is called out as a follow-up should the lab ever create additional A3
  worksheets.

  Finally, I verified in `WorksheetForm.tsx` that the table body renders its
  left-most column as a **hard-coded numeric `#` (`localIndex + 1`)** and that
  **`rows.labelFrom` / `label_from` is never read by the renderer** — only
  field-level `labelFrom` (column headers / singleton labels) is consumed by
  `headerText`/`resolveLabelFrom`. The captions therefore appear purely because
  `std_label` is an ordinary first data column whose seeded `group_values` the
  renderer shows (alongside, not replacing, the numeric `#`). Accordingly
  **`rows.labelFrom` has been removed from the definition** (resolves Finding 3):
  it is behaviourally inert, and `GroupDef.parse` would otherwise force
  `std_label` to be a declared field solely to satisfy a key nothing reads. The
  analyst may still edit a seeded caption per worksheet; edits persist in
  `group_values` only, never to the definition.
- Each `media_N` column is **kind `area`** (chromatographic STD areas), which is
  what feeds `mean/sd/rsd`. Area kind is also what the Waters CDS import discovery
  (`area_field_refs`) expects — keeping these as `area` preserves that contract.
- **Waters CDS import now discovers ten media area targets** (resolves review
  Finding 4). Because each `media_N` is `kind: area`, `area_field_refs` returns
  ten `('std_areas','media_1..10')` pairs plus `('samples','area')` where it
  previously returned one `('std_areas','area')` pair (all ten are declared area
  fields regardless of which are visible per worksheet). This is intended — the
  media columns are genuine STD-area targets — and wiring any further CDS
  auto-mapping of those six targets is explicitly **out of scope** for this task
  (manual area entry is the current contract, per the "manual entry pending the
  Waters integration" hint in the renderer). Noted so the import-side team is not
  surprised by ten discoverable targets.
- `std_areas.media_1` carries `required: true` (the mandatory reference medium —
  see Decision 4). `required` is advisory to the engine (a blank area cell still
  aggregates to `EMPTY`); the enforcement is the trailing-only deletion guard
  (the column can never be deleted) plus the in-definition blocking criterion
  `media1_present` described in Decision 4.
- Field-level `labelFrom` is **UI-only**: `FieldDef.parse` in
  `template_schema.py` reads only known keys and silently ignores `labelFrom`, so
  the engine parses this definition cleanly (same as TPL-A2-0004 does in the
  parity suite).

### How `labelFrom` resolves `media_names.media_N[0]` (verified this iteration)

`resolveLabelFrom` in `WorksheetForm.tsx` (read this iteration) parses the spec
with `/^([A-Za-z_]\w*)\.([A-Za-z_]\w*)(?:\[(\d+)\])?$/` and then reads
`computed.rows?.[groupKey]?.[idx]?.[fieldKey]` (falling back to
`values[groupKey]?.[idx]?.[fieldKey]`), trims it, and returns `null` when blank.
So `media_names.media_1[0]` resolves to
`values['media_names'][0]['media_1']` — **row 0, field `media_1`**.

This is a deliberately different shape from A2-0004's `standard.name[0..3]`: there
the singleton stores a **multi-row array** (one row per compound, same field key
`name` indexed `[0]..[3]`), confirmed by reading worksheet 30's stored
`group_values` where `standard` is a 4-element array. Here `media_names` stores a
**single row with ten distinct field keys** (`media_1..media_10`), each read at
`[0]`. The resolver's row-indexed lookup supports **both** shapes identically; the
only implementation requirement this imposes is that `media_names` must seed and
persist as a **one-row array** (`group_values["media_names"] = [ { media_1: …,
… } ]`), which is exactly how the renderer already materialises any group's row 0.
A design note for the implementer: do **not** store `media_names` as a bare object
(`{media_1: …}`) — it must be the one-element array so `[0]` resolves. The chosen
one-row-six-keys shape is preferred over the A2-0004 multi-row shape because the
"Media Name" entries are conceptually one heading **per column** (a single row of
six cells); a multi-row encoding would be an unnatural fit and would complicate
add/delete-column (which operates on field keys, not rows).

### How the heading row actually renders (corrected — resolves review Finding 2)

**Correction to the prior layout claim.** The earlier draft stated the
`media_names` singleton "renders directly above the table as the Media Name row"
as a "faithful Option 1 layout". Having read the `group.kind === 'singleton'`
branch of `WorksheetForm.tsx` this iteration, that visual description is **wrong**
and is corrected here. A singleton renders inside its **own `<Card>`** with an
`<h3>` section header showing `group.label` ("Media Name") followed by a
**responsive field grid** — here ten separately-labelled text inputs ("Media 1" …
"Media 10"). It is NOT a single horizontal row of cells aligned under the table's
media columns, and it is a distinct card from the `std_areas` table card. Group
order in the definition controls only the vertical order of cards, not column
alignment.

What IS correct and verified is the **mechanism**: each `media_N` input value in
that card drives the matching `std_areas.media_N` **column header** via field-level
`labelFrom` (`resolveLabelFrom` reads `media_names.media_N[0]`, confirmed), so
typing "PBS pH 6.8" in the Media 3 box renames the Media 3 column header. So the
Option 1 intent — *an editable per-worksheet Media Name that sets each column's
heading* — is fully delivered; only the pixel layout differs from an in-table
heading strip.

**This is accepted for Option 1** rather than scoped as a renderer change,
because (a) a true in-table aligned heading row would require new renderer code
(a special header-row-from-singleton path) that is outside the agreed
one-line-gate-plus-field-guard frontend scope, and (b) the "Media Name" card +
six inputs reads naturally, matches how the project's existing `labelFrom`
templates (TPL-A2-0004) already present their heading source, and loses no
functionality. If stakeholders later require the literal in-table strip, that is a
separate renderer enhancement, called out here and not undertaken now.

### Why a separate `media_names` singleton rather than a cell in `std_areas`

The alternative — modelling the heading as the first data row of `std_areas` (a
`std_label="Media Name"` row whose media cells are text) — is rejected because
those media columns are `kind: area` (numeric) and feed the stats aggregates, so a
text heading value in row 0 would corrupt `mean(std_areas.media_1)`. A dedicated
one-row singleton keeps the heading text physically out of the numeric aggregates
and gives `labelFrom` a stable `[0]` index to read (identical to how TPL-A2-0004
reads `standard.name[0..3]`). That is why the heading is its own group even though,
per the correction above, it renders as a separate card rather than an in-table
row.

---

## Decision 2 — Mean/SD/RSD footer formulas per media column

**Decision:** Add a per-column trio to the `stats` singleton, one `mean/sd/rsd`
per media column, each aggregating exactly its own column — **ten trios**,
`media_1 … media_10`:

```jsonc
{ "key": "stats", "kind": "singleton", "label": "Standard Statistics",
  "fields": [
    { "key": "mean_m1", "kind": "calculated", "label": "Media 1 Mean", "expression": "mean(std_areas.media_1)" },
    { "key": "sd_m1",   "kind": "calculated", "label": "Media 1 SD",   "expression": "sd(std_areas.media_1)" },
    { "key": "rsd_m1",  "kind": "calculated", "label": "Media 1 %RSD", "unit": "%", "expression": "rsd(std_areas.media_1)" },
    /* …identical trios for media_2 … media_10 (mean_m2/sd_m2/rsd_m2 … mean_m10/sd_m10/rsd_m10)… */
    { "key": "mean_m10", "kind": "calculated", "label": "Media 10 Mean", "expression": "mean(std_areas.media_10)" },
    { "key": "sd_m10",   "kind": "calculated", "label": "Media 10 SD",   "expression": "sd(std_areas.media_10)" },
    { "key": "rsd_m10",  "kind": "calculated", "label": "Media 10 %RSD", "unit": "%", "expression": "rsd(std_areas.media_10)" }
  ] }
```

The table's **column-aligned footer** (shown in Decision 1) maps one Mean row,
one SD row and one %RSD row across the ten columns, referencing
`stats.mean_m1..m10`, `stats.sd_m1..m10`, `stats.rsd_m1..m10`. This is detected by
the renderer's `isColumnAlignedFooter` heuristic (unlabeled items following a
labeled one) and drawn as real rows under each column — exactly the A2-0004
behaviour.

**Keeping footer stats correct when a column is added/deleted (the HIGH-finding
fix — see Decision 3 for the guard).** The footer renderer is **positional**:
`valueColumns = visibleFields.slice(1)` and each data column `c` shows
`row.cells[c]`. So the footer stays aligned **only if the set of visible media
columns is a prefix** `media_1 … media_k` of the provisioned order — i.e. hidden
columns must always be a trailing suffix. This design guarantees that invariant
two ways: (1) the default-six view is produced by seeding the trailing four
(`media_7 … media_10`) into `hiddenColumns` (Decision 1), and (2) deletion is
**restricted to the trailing visible column only** (Decision 3), so a middle
column can never be hidden. Under that invariant, hiding the trailing column
drops its `visibleFields` entry **and** its last footer-cell position together,
and the remaining `media_1 … media_(k-1)` footer cells stay matched to their own
columns. The ten stats trios and ten footer refs are **always present in the
definition**; a hidden/deleted column's cells are blanked and `mean/sd/rsd` over
an all-blank column yields blank (engine blank-tolerance, confirmed by
`test_every_template_parses_and_runs_empty`), so a trailing hidden column's
footer slot never renders at all and the visible columns read their own correct,
independent stats. No footer formula is rewritten when columns change.

> **Why not fix the renderer to be field-keyed (review option a) or pad with a
> placeholder column (option b)?** Both are genuine fixes but require surgery to
> the shared `renderGroupFooter`, which is **outside** this task's frontend scope
> and would change behaviour for every column-aligned-footer template
> (TPL-A2-0004). The user explicitly chose **option (c), delete-trailing-only**,
> which keeps the positional renderer untouched and is enforced entirely by the
> delete-affordance guard (Decision 3). That is the option this design implements.

**Verified engine semantics for the footer (`backend-v2/.../expression.py`,
read this iteration):** `_f_mean` returns `EMPTY` for an empty numeric range;
`_f_sd` and `_f_rsd` return `EMPTY` for **fewer than two** numeric values
(`len(nums) < 2`), and `_f_rsd` additionally returns `EMPTY` when the mean is 0.
Consequences, all desirable and matching the source workbook:
- A populated column with ≥2 standards (the screenshot has five) yields real
  Mean/SD/%RSD — e.g. the Media-1 column reproduces Mean 1266569, SD 1386.78,
  %RSD 0.11 (checked in Testability).
- A column with exactly **one** area shows a Mean but blank SD/%RSD (sample SD is
  undefined for n=1). This is correct Excel-STDEV parity, not a defect.
- A hidden/deleted (all-blank) column shows "—" for all three. No error, no NaN.
`%RSD` is a percentage (`sd/mean*100`); the footer `unit: "%"` is display-only and
does not re-scale the value.

---

## Decision 3 — Where the media-column SET is persisted (definition vs per-worksheet)

**Decision: per-worksheet (UI state), NOT the template definition** — consistent
with how commit `c436559`'s add/delete-column feature already behaves.

Evidence from the code (`WorksheetForm.tsx`):
- Add/delete column is driven entirely by React state `hiddenColumns`
  (`Set<"group.field">`). `deleteColumn` **blanks the column's values and hides
  it**; `addColumn` restores the first hidden provisioned column. Neither touches
  the template definition — the comment is explicit: *"The (shared, versioned)
  template field is untouched; this is a per-worksheet UI action."*
- The provisioned maximum set lives in the **definition** (the ten `media_N`
  fields); the **active subset** is per-worksheet. This is exactly the model this
  design adopts: ten media columns provisioned once in the definition, six visible
  by default (the trailing four seeded into `hiddenColumns`, Decision 1), with the
  analyst growing/shrinking the visible set per worksheet.

Therefore **renames and add/delete never mutate the stored template definition**,
satisfying the explicit requirement that renames be per-worksheet only. A rename
is a `media_names.media_N` cell value saved in the worksheet's `group_values`; a
delete is a per-worksheet hidden column; the definition's ten columns and their
static labels are immutable until a formal versioned template edit.

### Enabling the control for this template, and the trailing-only delete guard (the scoped frontend change)

The add/delete-column UI is currently gated to a single template:

```ts
const allowClearColumn = detail.worksheet.template_code === 'TPL-A6A-0004';
```

Change this to also enable TPL-A3-0001:

```ts
const allowClearColumn =
  detail.worksheet.template_code === 'TPL-A6A-0004' ||
  detail.worksheet.template_code === 'TPL-A3-0001';
```

The per-column trash icon's exact render condition (verified in `WorksheetForm.tsx`)
is, inside `visibleFields.map((field) => …)` in the table `<thead>`:

```tsx
{allowClearColumn && !calc && isEditableField(field) && editingThisGroup && (
  <i className="pi pi-trash …" onClick={() => deleteColumn(group, field.key)} />
)}
```

with `isEditableField` true for `EDITABLE_KINDS = {'input','area'}` (verified).
Because `std_label` is `kind: input` and each `media_N` is `kind: area`, **every**
visible column of the generified `std_areas` would show the delete icon by
default. For this task the icon must be exposed on **exactly one** column: the
**highest-numbered currently-visible `media_N`** (the trailing media column). That
single guard simultaneously satisfies three requirements:

1. **Trailing-only delete (the HIGH-finding fix, option c).** Only the last visible
   media column is deletable, so hidden columns always form a trailing suffix and
   the positional column-aligned footer (Decision 2) never misaligns.
2. **`std_label` is never deletable** — it is the caption column, not a `media_N`,
   so it is never the trailing media column.
3. **`media_1` is never deletable while any other media column is visible** — with
   the default six visible, `media_6` is trailing; `media_1` only becomes trailing
   if the analyst deletes down to a single media column, and that case is blocked
   explicitly (see the guard) because `media_1` is the mandatory reference medium
   (Decision 4).

**The guard — computed once per group, used in the icon condition.** Inside the
group's render, derive the trailing media key from `visibleFields` (which is in
definition order, so the last `media_N` in it is the trailing visible one):

```tsx
// media columns currently visible, in definition order:
const visibleMediaKeys = visibleFields
  .filter((f) => /^media_\d+$/.test(f.key))
  .map((f) => f.key);
// the only deletable media column: the trailing (last) visible one,
// but never media_1 (the pinned reference medium).
const trailingMediaKey =
  visibleMediaKeys.length > 1 ? visibleMediaKeys[visibleMediaKeys.length - 1] : undefined;
```

and the icon condition becomes:

```tsx
{allowClearColumn && !calc && isEditableField(field) && editingThisGroup &&
  (group.key !== 'std_areas' || field.key === trailingMediaKey) && (
  <i className="pi pi-trash …" … />
)}
```

Reading of this guard, against the verified helpers:
- For `std_areas`, the icon shows **only** when `field.key === trailingMediaKey`.
  `trailingMediaKey` is the last visible `media_N` **unless only one media column
  remains** (`visibleMediaKeys.length > 1` guard), in which case it is `undefined`
  and no media delete icon shows — so the analyst can never delete the last
  remaining media column, which protects `media_1` (and the reportable divisor
  `stats.mean_m1` / SST `stats.rsd_m1`) exactly as required. `std_label` never
  matches `trailingMediaKey` (it is not a `media_N`), so it is never deletable.
- For other groups/templates the `group.key !== 'std_areas'` branch leaves the
  existing TPL-A6A-0004 behaviour untouched.

**Interaction with `deleteColumn` / `addColumn` / `deletableColumns` (verified).**
`deleteColumn(group, field.key)` blanks the column and adds `std_areas.media_N` to
`hiddenColumns`; because only the trailing column ever has an icon, the hidden set
stays a contiguous trailing suffix (`media_(k+1) … media_10`). `deletableColumns`
= `group.fields.filter(f => !f.hidden && isEditableField(f))` lists `std_label`,
`media_1 … media_10` (none carry the definition `hidden` flag now). `addColumn`
restores the **first still-hidden** deletable field in definition order — which,
given the trailing-suffix invariant, is always the lowest-numbered hidden
`media_N` (e.g. `media_7` first), re-growing the visible set from the end. The
initial `hiddenColumns` seed (`media_7 … media_10`, Decision 1) makes `media_6`
the trailing column on open, so the default-visible set is exactly `media_1 …
media_6`. `hiddenCountFor` therefore reports 4 on a fresh worksheet and "Add
Column" is enabled.

Note that `std_label` and `media_1` remain in `deletableColumns`, but since
neither ever shows a trash icon, neither can ever be hidden, so neither can ever
become an "Add Column" restore target. The reachable add/delete targets are
`media_7 … media_10` (restore) and the current trailing visible `media_N`
(delete), bounded below at a single remaining media column.

> **Components/hooks reused (named):** `WorksheetForm` component — its
> `deleteColumn`, `addColumn`, `hiddenColumns` state, `deletableColumns`,
> `hiddenCountFor`; the `headerText`/`resolveLabelFrom` helpers; the
> `renderGroupFooter` column-aligned path with `isColumnAlignedFooter` /
> `groupFooterRows` from `models/groupFooter.ts`; the `usePreview` hook from
> `hooks/useWorksheet`. **No new component or hook is created.**

---

## Decision 4 — Calc engine correctness for a variable column set, and parity

**Decision:** The engine needs **no change**. Each media column is a fixed field
key, and each stat is a single-column aggregate (`mean/sd/rsd(std_areas.media_N)`),
which the engine already evaluates for A2-0004's four columns. "Variable column
set" is a UI-layer show/hide; a hidden column's blanked cells aggregate to blank,
and the engine's documented blank-tolerance (`EMPTY` propagation) keeps every
other column's result correct and independent.

**Downstream `samples.solubility` dependency — the one substantive formula
decision.** Today `samples.solubility` divides by `stats.mean_std`
(`area / stats.mean_std * standard.conc_ppm * diluted_to_ml / aliquot_ml / 1000`).
The old scalar `stats.mean_std` is **removed** when `std_areas` becomes
multi-column, so this reference must be repointed. The media table has ten means
(`stats.mean_m1..m10`), and solubility is a single reportable concentration, so we
must pick the standard-mean that the sample areas were quantified against.

- **Chosen:** repoint `samples.solubility` to **`stats.mean_m1`** (Media 1 as the
  reference/standard medium), preserving a single scalar divisor and the existing
  formula shape. This matches the screenshot, where every media column shares the
  same standard areas (all columns show identical values) so Media 1's mean is a
  valid, stable standard reference, and it keeps `resultRef = samples.mean_solubility`
  and the `samples` table **completely untouched** (out of scope per the task).
- **Rejected:** making solubility itself per-media (ten solubility columns). That
  would expand the `samples` table, which is explicitly **out of scope** (only the
  STD Area in Media table may change). If the lab later wants per-media solubility,
  that is a separate, larger template change.

**SST criterion repoint.** The blocking `sst_std_rsd` criterion currently targets
`stats.rsd_std` (removed). Repoint it to **`stats.rsd_m1`** (the reference medium's
%RSD), keeping a single blocking SST consistent with the single-standard model.
The advisory `prep_agreement` criterion targets `rsd(samples.solubility)` and is
unchanged.

### Media 1 is the mandatory reference column — it MUST NOT be deletable (resolves review Finding 1, HIGH)

Making Media 1 the single standard reference (solubility divides by
`stats.mean_m1`; the blocking `sst_std_rsd` targets `stats.rsd_m1`) creates a
correctness hazard that the add/delete-column feature of *this* task would
otherwise open: every `media_N` column is per-worksheet deletable (Decision 3),
and a deleted or all-blank column aggregates to `EMPTY` (verified in `_f_mean`).
So if an analyst deleted or blanked **Media 1**, `stats.mean_m1` would become
`EMPTY`, `samples.solubility` would divide by `EMPTY` and the reportable
`mean_solubility` would collapse to blank, and the blocking `sst_std_rsd`
criterion would read `EMPTY` and silently stop blocking. That is a silent
failure of the primary reportable reachable through the very feature being added.

**Decision — guard `media_1` from deletion exactly as `std_label` is guarded,
and treat it as the mandatory reference medium.** Option (a) from the review is
chosen over (b) a separate non-deletable standard group and (c) a "first
populated `mean_mN`" fallback, because:

- (b) would add a new area group **outside** the in-scope `std_areas` table,
  which the task forbids (only the STD Area in Media table may change), and would
  also diverge from the screenshot (which has no separate standard-area table —
  the standard areas live in the media columns themselves).
- (c) is implementable with the engine's existing `coalesce` (verified: `_f_mean`
  / `coalesce` — "first non-blank argument, or EMPTY"), e.g.
  `samples.solubility` dividing by `coalesce(stats.mean_m1, stats.mean_m2, …)`.
  But it makes the reportable's standard reference **silently jump** from one
  medium to another when Media 1 is cleared — a GxP-unfriendly implicit change of
  the quantitation standard, and it does not fix the SST, whose single `target`
  cannot `coalesce` across ten refs without a schema change. Rejected.

Option (a) keeps a single stable scalar divisor and a single SST target, changes
nothing outside the in-scope table plus the already-planned frontend guard, and
matches the lab semantics in the screenshot (Media 1 is the reference medium).

**Two enforcement points, by layer:**

1. **Deletion guard (UI layer, frontend).** The trailing-only delete guard
   specified in Decision 3 already makes `media_1` non-deletable: the trash icon
   shows only on the highest-numbered **currently-visible** `media_N`, and the
   `visibleMediaKeys.length > 1` condition suppresses it entirely when a single
   media column remains, so the analyst can never delete down to zero media
   columns and can never delete `media_1` while it is the only one left. Combined
   with Decision 3's prohibition on deleting a non-trailing column, `media_1` can
   never be hidden (it is never the trailing column until it is the only one, at
   which point the icon is suppressed). `std_label` is likewise never deletable
   (it is not a `media_N`). No extra per-field guard beyond Decision 3's is needed.

2. **Populated-reference enforcement (template-definition BLOCKING CRITERION —
   resolves the MEDIUM finding, reviewer option (i)).** A UI delete guard alone
   does not stop an analyst leaving every `media_1` cell blank, which would blank
   `stats.mean_m1`, divide the reportable by `EMPTY`, and read the SST `rsd_m1` as
   `EMPTY` (silently non-blocking). `required: true` on the field is **not
   sufficient** — the engine treats a blank area cell as `EMPTY` regardless. The
   earlier draft mandated a worksheet-completion validation seam that was never
   verified to exist; that approach is **dropped**. Instead this design adds an
   **in-scope, in-definition blocking criterion** that reuses the engine's
   existing, verified blocking-criteria path and the verified `count` function:

   ```jsonc
   { "key": "media1_present", "label": "Media 1 reference required",
     "target": "count(std_areas.media_1)", "operator": "gte", "limit": 1,
     "severity": "blocking", "limitText": "At least one Media 1 standard area required" }
   ```

   Verified semantics (this iteration): `count(std_areas.media_1)` = `_f_count` =
   `float(len(_numeric(...)))` — the number of **numeric** `media_1` cells, and it
   **always returns a number** (0.0 when the column is all-blank), never `EMPTY`.
   `_evaluate_criteria` computes `observed = evaluate(target, scope)` and `_assess`
   returns `observed >= limit[0]` for `operator = gte`; `is_blocking_failure =
   severity is BLOCKING and passed is False`. So the criterion **fails (blocks)**
   whenever zero `media_1` cells are numeric and **passes** the moment at least one
   is entered. This closes the blank-`media_1` hole with no new seam and no engine
   change — it lives entirely inside the in-scope `std_areas`/criteria edit and
   fires through the same path as the existing `sst_std_rsd` blocking criterion.
   The target is an expression exactly like the existing `prep_agreement` target
   `rsd(samples.solubility)`, so the shape is proven in this very definition.

   `std_areas.media_1` is still marked `required: true` in the definition as
   declarative intent, but the **criterion** is the load-bearing enforcement.
   Because `count` is always assessable (never `EMPTY`), the criterion does not
   suffer the "blank observed ⇒ passed=None ⇒ not blocking" escape that an
   `rsd`/`mean`-based target would; an empty worksheet reads `count = 0` and
   blocks. During in-progress editing the criterion simply shows as a not-yet-met
   blocking item (the worksheet is not completable until satisfied), which is the
   correct GxP behaviour and does not interfere with blank-tolerant previews of
   the other fields.

> **No reliance on an unverified seam.** The previous "mandated-but-deferred
> completion-time validation" prose is removed. Enforcement is now a concrete
> blocking criterion in the definition, evaluated by the engine's existing
> criteria path (`_evaluate_criteria` / `_assess` / `is_blocking_failure`,
> verified), so it needs no new frontend or backend validation hook. The three
> existing criteria shapes in this template (`sst_std_rsd` blocking on
> `stats.rsd_std`, `prep_agreement` advisory on an expression target) confirm both
> a scalar-field target and an expression target are accepted.

**Test (committed deliverable of this task, see Testability):** add an engine/
schema test that (i) with `media_1` blank/absent, asserts the reportable and SST
`stats.rsd_m1` go `EMPTY` **and** the `media1_present` criterion evaluates to a
**blocking failure** (`passed is False`, `is_blocking_failure is True`) so the
worksheet cannot be completed; and (ii) with `media_1` populated, asserts the
reportable and SST compute and `media1_present` passes. This pins both the hazard
and the in-definition enforcement, and fails loudly if a future change silently
repoints the divisor or drops the criterion.

**What keeps the TPL-A3-0001 parity test passing.** The parity class
`TestA3SaturationSolubility` in
`backend-v2/tests/calculation/test_seeded_template_parity.py` feeds
`std_areas: [{"area": 50000.0}, {"area": 50000.0}]` and asserts
`standard.conc_ppm == 1000`, `samples[0].solubility == 5.0`, reportable `== 5.0`.
Because the seed modules are an **earlier state and the seed A3 still has the
single-`area` table** (the seed is NOT where this edit lands — see Decision 5),
the parity test continues to exercise the seed definition and **passes unchanged**.
The DB edit does not touch the seed, so parity is unaffected.

- **New-shape coverage IS delivered this task.** The new media behaviour
  (per-column stats, blank tolerance, the Media 1 reference guard, six-pair
  `area_field_refs`) is covered by the three committed unit tests in Testability,
  which build the media definition **object directly** and do not touch the seed.
  So the DB-only edit is not left uncovered.
- **Only the seed-parity-class rewrite is backlogged (not the coverage):** the
  worklog's standing caveat is that DB template edits are *"not yet captured as
  declarative seed modules."* When this media-table edit is eventually folded into
  the seed (`a2_a3_content.py`), the existing `TestA3SaturationSolubility` parity
  class must be rewritten to the media shape: feed `std_areas` rows with
  `media_1..media_10`, assert `stats.mean_m1 == 50000`, and keep `solubility == 5.0`
  via the repointed `stats.mean_m1` divisor (5 dp:
  `25000/50000 * 1000 * 10/1 / 1000 = 5.0`). That rewrite is deferred purely
  because it is coupled to the separate seed-capture work; the committed unit tests
  above already validate the live behaviour in the meantime, mirroring how the
  15 Oct and 29 Oct worklog entries validated their DB-only edits.

---

## Decision 5 — Which DB to edit, and the mandatory backup

**Decision: edit the user's LIVE DB, `d:\RD-instance\GIT\backend-v2\lims.db`,
directly** — because that is the DB the running backend opens.

Rationale:
- `backend-v2/.env` sets `DATABASE_URL=sqlite+aiosqlite:///./lims.db`, i.e. the DB
  is resolved **relative to the backend's working directory**. The app the user
  runs is `backend-v2`, so `backend-v2/lims.db` is the live, user-visible DB. The
  worktree copy at `.worktrees/satsol-media-columns/backend-v2/lims.db` is only
  live if the server is started from inside the worktree, which is not the user's
  normal run. Editing the worktree copy would leave the user's actual worksheet
  (id 53) and UI unchanged, so the change would appear to "not work."
- Both DBs are currently identical **for this template definition** (length 4177).
  Their worksheets 53 differ: the live DB's worksheet 53 has **populated**
  `group_values` (real `standard`/`samples` data, `std_areas` = five `{"area":
  null}` rows), the worktree's is `'{}'` (re-queried this iteration — correcting
  the prior "both empty" claim). This divergence does not change the decision: the
  live DB is still the one the running app opens, and the stored `std_areas` cells
  are all blank, so the migration is a safe, targeted rewrite (see Data/worksheet
  impact below), not a hazard.

**Mandatory, non-negotiable backup before any write.** Before the first write to
the chosen DB, create a timestamped copy alongside it:

```
d:\RD-instance\GIT\backend-v2\lims.db.bak-satsol-media-<yyyyMMdd-HHmmss>
```

This matches the project's established practice (every worklog entry records a
`lims.db.bak-*` taken before each change). If, instead, the decision is reversed
and the worktree DB is edited, the **same** timestamped-backup rule applies to
`.worktrees\satsol-media-columns\backend-v2\lims.db` before writing. The write is **two statements in one transaction**:

1. `UPDATE test_templates SET definition = :json, modified_by = …,
   modified_date = … WHERE code='TPL-A3-0001' AND version=1` (id 3), with the new
   JSON validated by `TemplateDefinition.parse(...)` **before** the UPDATE so a
   malformed definition can never reach the DB.
2. `UPDATE test_worksheets SET group_values = :gv WHERE id = 53`, where `:gv` is
   the existing stored object with **only its `std_areas` key replaced** by the
   six seeded caption rows (the caption-seeding mechanism for the retracted-seed
   findings). The `standard`, `stats` and `samples` keys are **copied through
   unchanged** so the real data already entered on worksheet 53 is preserved. Each
   seeded row carries all ten `media_N` keys null (the full provisioned set), so
   the stored shape matches the ten-column definition:

   ```jsonc
   "std_areas": [
     { "std_label": "Standard - 1", "media_1": null, "media_2": null, "media_3": null, "media_4": null, "media_5": null, "media_6": null, "media_7": null, "media_8": null, "media_9": null, "media_10": null },
     { "std_label": "Standard - 2", "media_1": null, "media_2": null, "media_3": null, "media_4": null, "media_5": null, "media_6": null, "media_7": null, "media_8": null, "media_9": null, "media_10": null },
     { "std_label": "Standard - 3", "media_1": null, "media_2": null, "media_3": null, "media_4": null, "media_5": null, "media_6": null, "media_7": null, "media_8": null, "media_9": null, "media_10": null },
     { "std_label": "Standard - 4", "media_1": null, "media_2": null, "media_3": null, "media_4": null, "media_5": null, "media_6": null, "media_7": null, "media_8": null, "media_9": null, "media_10": null },
     { "std_label": "Standard - 5", "media_1": null, "media_2": null, "media_3": null, "media_4": null, "media_5": null, "media_6": null, "media_7": null, "media_8": null, "media_9": null, "media_10": null },
     { "std_label": "Standard - 6", "media_1": null, "media_2": null, "media_3": null, "media_4": null, "media_5": null, "media_6": null, "media_7": null, "media_8": null, "media_9": null, "media_10": null }
   ]
   ```

   This replaces the old five `{"area": null}` rows (which carry no value and
   have no home in the new shape). Seeding all ten `media_N` keys (even though
   `media_7 … media_10` are not visible by default) keeps the stored rows
   consistent with the definition and is harmless — the evaluator fills any
   missing cell from `default`/`EMPTY` anyway, so partial rows would also work;
   the full keys are written for clarity. `media_names` is not written here — the
   renderer materialises a singleton's one row from `field.default`/blank on open,
   and `labelFrom` falls back to the static "Media N" label until the analyst
   types a heading. The default-visible-six view is produced by the frontend
   `hiddenColumns` seed (Decision 1), **not** by what is stored here. Both
   statements must assert `rowcount == 1` and roll back together on any failure.

### Data / worksheet impact (CORRECTED — live worksheet 53 is NOT empty)

Re-queried this iteration, the **live** worksheet 53 (InProgress) stores:
`standard` (one row of real values), `std_areas` (five `{"area": null}` rows),
`stats` (`[{}]`), and `samples` (three rows of partial prep data). The shape
change renames the in-scope table's fields (`std_areas` keeps its group key;
`area` → `std_label` + `media_1..10`) and adds the `media_names` group, the
per-media `stats` fields, and the `media1_present` blocking criterion. The impact,
key by key:

- **`std_areas`** — the only group whose shape changes. Its five stored cells are
  all `area: null` (**no value**). The migration **replaces** this key with the
  six seeded caption rows shown in the write above, losing nothing of substance
  (the orphaned cells were blank). This replacement is also the caption-seeding
  mechanism.
- **`standard`, `samples`** — unchanged keys and fields; **copied through
  verbatim** so the analyst's entered data survives. (Only the template-level
  `samples.solubility` divisor and the `sst_std_rsd` target are repointed off the
  removed scalar `stats.mean_std`; the stored `samples` row *values* are untouched.)
- **`stats`** — a singleton whose fields change from `mean_std/sd_std/rsd_std` to
  the ten `mean_mN/sd_mN/rsd_mN` trios. All are `calculated`, so nothing is stored
  for them (`[{}]` carries no input); the stored value is copied through as-is and
  the evaluator recomputes from the new fields on open.
- **`media_names`** — new singleton; nothing stored, materialises blank on open.

So the write preserves all real data and orphans only all-null cells. A dedicated
migration script is not required beyond the two-statement transaction above.

**Exact re-query to run immediately before writing (verified table/column names
this iteration):** the worksheet table is `test_worksheets` (NOT `worksheets`),
keyed to the template by `template_id`:

```sql
SELECT w.id, w.status, w.group_values
FROM   test_worksheets w
JOIN   test_templates t ON w.template_id = t.id
WHERE  t.code = 'TPL-A3-0001';
```

This returned `(53, 'InProgress', <non-empty object>)` against the **live** DB
this iteration, with `std_areas` holding only `{"area": null}` rows.
**Abort-and-reconcile trigger (refined):** inspect the stored `std_areas` rows
before writing — if **any** `area` cell is **non-null** (an analyst entered real
STD areas against the old single-`area` table), abort and reconcile, because that
value has no home in the ten-`media_N` shape and would be silently orphaned. If
all `std_areas.area` cells are null (as now), proceed with the replacement.
Real values under `standard`/`samples` are **not** an abort trigger — those keys
are preserved unchanged. (The prior draft's blanket "abort if group_values
non-empty" was based on the mistaken belief that worksheet 53 was empty; it is
refined here to key off the one field that actually changes shape.)

---

## Validation rules for external inputs

- **`media_names.media_N` (heading cells):** optional free text. Behaviour on
  blank: the column header falls back to the static `label` ("Media N") via
  `headerText` → `resolveLabelFrom` returning `null` on empty/whitespace. No type
  coercion, no length limit enforced beyond the existing text input. These values
  are display-only; they never enter an expression.
- **`std_areas.media_N` (area cells):** numeric (kind `area`), full instrument
  precision (the renderer allows up to 6 fraction digits for area fields).
  Non-numeric entry is prevented by the numeric `InputNumber` control. For
  `media_2 … media_10`: blank is valid and drops the cell out of that column's
  `mean/sd/rsd`. For **`media_1`** (`required: true`, the reference medium): at
  least one of the `media_1` cells must be numeric for the worksheet to be
  completed/approved — enforced by the trailing-only deletion guard (the column
  can never be deleted, Decision 3) **plus** the in-definition blocking criterion
  `media1_present` (`count(std_areas.media_1) gte 1`, Decision 4), which blocks
  completion while the column is all-blank. During in-progress editing the engine
  still tolerates a blank `media_1` (preview shows a blank reportable, no error);
  the blocking criterion is what prevents an all-blank `media_1` worksheet from
  being signed off, with no reliance on any unverified completion seam.
- **`std_areas.std_label` (row caption):** free text. On worksheet 53 it is
  **seeded with "Standard - 1 … Standard - 6" by the DB edit writing those values
  into `group_values["std_areas"]`** (Decision 1 / Decision 5) — there is no
  `rows.seed` schema key and no field-level scalar default that could carry six
  distinct captions. Any future worksheet would open with this column blank until
  the analyst types a caption. The analyst may overwrite a seeded caption; if a
  cell is cleared it simply renders empty (the renderer shows its own separate
  numeric `#` column regardless — `rows.labelFrom` is not consumed and has been
  removed from the definition, see Decision 1). Captions are display-only data and
  never enter an expression.
- **Invariant — heading text never persists to the definition:** owned by the
  **UI/worksheet layer**. `media_names` values live only in the worksheet's
  `group_values`; the template `UPDATE` writes the definition once at
  implementation time and is never rewritten by a rename. This layer owns it
  because the definition is shared and e-signed/versioned, so per-worksheet renames
  must not mutate it.
- **Invariant — numeric purity of media columns:** owned by the **schema/engine
  layer** (media columns are `kind: area`, so heading text is physically in a
  different group and cannot reach the numeric aggregates).

---

## Edge cases

- **Default view:** six media columns (`media_1 … media_6`) render; `media_7 …
  media_10` are seeded-hidden and reachable via "Add Column" up to ten
  (Decision 1). "Add Column" restores `media_7`, then `media_8`, … in order.
- **All media cells blank in a column:** footer Mean/SD/%RSD show "—"; no error.
- **Deleting an unused trailing media column:** only the **highest-numbered
  currently-visible `media_N`** shows the trash icon (Decision 3). Deleting it
  blanks its cells, hides it, and drops its (trailing) footer cell, so the
  remaining columns keep their own correct, column-aligned stats. The next-lower
  media column becomes the new trailing deletable one. "Add Column" re-grows from
  the end.
- **Attempt to delete a MIDDLE media column:** not possible — a non-trailing
  media column never shows a trash icon, so the positional column-aligned footer
  can never be misaligned (the HIGH-finding fix, option c).
- **Attempt to delete Media 1 / the last remaining media column:** not possible —
  the trash icon is suppressed whenever only one media column remains
  (`visibleMediaKeys.length > 1`), so the reportable divisor (`stats.mean_m1`) and
  the SST target (`stats.rsd_m1`) can never be removed via the UI. Leaving all
  `media_1` cells blank is caught by the **blocking `media1_present` criterion**
  (`count(std_areas.media_1) gte 1`, Decision 4) — the worksheet cannot be
  completed with an all-blank `media_1`, so the reportable is never silently blank.
- **Standard-6 row left blank (as in the screenshot):** a blank area row simply
  does not contribute to that column's mean — matches `mean()` over present
  values. (This is a standard-injection **row**, unaffected by the media **column**
  count.)
- **Only one area entered in a column:** Mean shows that value; SD and %RSD show
  "—" because `_f_sd`/`_f_rsd` require `len(nums) >= 2` (verified in
  `expression.py`). This is correct sample-statistics / Excel-STDEV behaviour, not
  a bug, and the implementer/reviewer should expect it rather than treat the blank
  SD as a failure.
- **A column whose mean is exactly 0:** `_f_rsd` returns `EMPTY` (guards division
  by zero); Mean shows 0, %RSD shows "—". Not reachable with real STD areas but
  defined.
- **Heading typed then cleared:** header reverts to the static "Media N" label on
  the next preview (labelFrom resolves blank → fallback).
- **Worksheet 53 after the edit:** the DB edit seeds six `std_areas` rows into
  worksheet 53's `group_values` with `std_label` = "Standard - 1 … Standard - 6"
  and all ten `media_N` = null, so on open the `std_label` column shows the
  captions, six media columns render (the trailing four hidden by the frontend
  `hiddenColumns` seed), and the media cells start blank; column headers show the
  static "Media N" until renamed. There is no `rows.seed` mechanism — the captions
  come from stored `group_values`, which is what the renderer/evaluator actually
  read.
- **A future (second) TPL-A3-0001 worksheet:** opens with the `std_label` column
  **blank** (no template-level per-row default exists) and six visible blank media
  cells; the analyst types the "Standard - N" captions and media areas. This is
  accepted for this task; template-level caption defaults for all future
  worksheets are an out-of-scope `RowSpec.seed` follow-up (Decision 1). The
  default-six-visible seed applies to every TPL-A3-0001 worksheet (it is keyed by
  template code, not worksheet id).
- **Reopening a saved worksheet:** `seedValues` seeds `media_names` (singleton, 1
  row) and `std_areas` (its stored rows) from `group_values`; `labelFrom` reads
  the seeded heading cells, so headings survive reload. (Confirmed by the seeding
  logic for singletons and tables.)
- **Preview staleness:** headers derive from `computed`/entered values; during a
  stale preview the header still shows the last entered heading (the resolver
  prefers computed then entered values), so headings do not flicker to fallback.

---

## Error handling (per operation that can fail)

- **Template JSON parse before write** — `TemplateDefinition.parse(new_def)`.
  Failure condition: schema violation (bad key, reserved identifier, calculated
  field without expression, etc.). **Fatal to the write** — abort the `UPDATE`,
  leave the DB untouched, surface the `TemplateSchemaError` message to the
  operator. Logged at error level in the migration/edit script output. Not
  recoverable automatically.
- **DB backup copy** — fatal precondition: if the timestamped `lims.db.bak-*`
  cannot be created (disk/permissions), **abort before any write**. The caller
  receives the OS error; nothing is modified.
- **The `UPDATE` statement** — if zero rows match (`code/version` wrong), treat as
  **fatal**: the edit silently targeting nothing is worse than failing, so assert
  `rowcount == 1` and roll back otherwise. Logged at error level.
- **Worksheet preview at runtime** (`usePreview`) — the engine is blank-tolerant;
  missing inputs yield blanks, not 400s (per the in-code comment and
  `test_every_template_parses_and_runs_empty`). A genuine preview error is already
  handled by the form: `preview.error` renders "Could not recalculate — the
  entered values may be incomplete." Recoverable; no change needed.
- **`labelFrom` resolution** — cannot fail: a malformed spec or missing source
  yields `null` and falls back to the static label (pure UI, no throw).

---

## Testability

> The unit tests below are **committed deliverables of THIS task**, not follow-ups.
> They are written against the new definition **object** (built in the test, or
> parsed from the edited DB definition), so they give the new media shape real
> automated coverage even though the seed-based parity suite stays on the old
> shape until the backlogged seed rewrite lands. Target file: a new
> `TestA3MediaColumns` class in
> `backend-v2/tests/calculation/test_seeded_template_parity.py` (or a sibling
> `test_media_columns.py` in the same package), built from the design's definition
> JSON — it does **not** depend on `SEED_TEMPLATES`.

- **Unit (schema — the full 10-column definition parses):** assert
  `TemplateDefinition.parse(new_def)` succeeds for the complete ten-`media_N`
  definition (ten `media_names` cells, ten `std_areas` area fields with
  field-level `labelFrom`, ten `stats` trios, the thirty-ref column-aligned
  footer, the repointed `samples.solubility`/`sst_std_rsd`, and the new
  `media1_present` criterion). Pins that the whole generified shape is valid.
  **Committed this task.**
- **Unit (engine — per-column independence + blank tolerance across 10 columns):**
  evaluate the media definition with a few media columns populated and assert each
  `stats.mean_mN == mean(colN)`, that populated columns are independent of blank
  ones, and that an all-blank column yields `EMPTY` for its mean/sd/rsd — proving
  per-column independence and blank tolerance over the full ten-column set. Pure
  engine test, no DB needed. **Committed this task.**
- **Unit (engine — trailing delete keeps footer stats aligned):** evaluate with,
  say, `media_1..media_6` populated with distinct values, then simulate the
  trailing-delete by blanking `media_6`'s cells, and assert that `media_1..media_5`
  still each report their **own** `stats.mean_mN` (i.e. deleting the trailing
  column does not shift any remaining column's stat). This is the engine-side
  pin for the HIGH-finding fix; the UI-side assertion (middle column offers no
  delete affordance, trailing does) is the frontend test below. **Committed this
  task.**
- **Unit (engine — Media 1 reference guard + blocking criterion):** (i) with
  `media_1` blank/absent, assert `samples.solubility` and `stats.rsd_m1` resolve
  to `EMPTY` **and** the `media1_present` criterion is a blocking failure
  (`observed == 0`, `passed is False`, `is_blocking_failure is True`); (ii) with
  one `media_1` cell populated, assert the reportable and SST compute and
  `media1_present` passes. Pins both the hazard and the in-definition enforcement.
  **Committed this task.**
- **Unit (schema — Waters discovery):** assert `area_field_refs` now contains the
  ten `('std_areas','media_1..10')` pairs plus `('samples','area')` (the
  Waters-import discovery invariant). **Committed this task.**
- **Integration (manual, documented):** read the edited definition back from the
  **live DB** (`SELECT definition FROM test_templates WHERE code='TPL-A3-0001'
  AND version=1`), instantiate `WorksheetEvaluator(TemplateDefinition.parse(db_def))`,
  and run the screenshot values (Standard-1..5 =
  1264265/1266600/1267571/1267739/1266671 in `media_1`) to reproduce Mean 1266569,
  SD 1386.78, %RSD 0.11 for that column — mirroring the end-to-end checks the
  worklog used for prior DB-only edits. (SD/%RSD are real here because five values
  satisfy the n≥2 rule.)
- **Frontend (add this task):** the add/delete-column and `labelFrom` paths are
  already shipped and exercised by TPL-A6A-0004 / TPL-A2-0004, but the
  trailing-only guard and the default-six `hiddenColumns` seed are new, so add a
  component test on TPL-A3-0001 asserting: (a) six media columns render on open
  (`media_7..media_10` hidden), (b) a typed Media Name updates the matching column
  header and clearing it reverts to "Media N", (c) **only the trailing visible
  media column (`media_6` by default) shows a delete icon; a middle column
  (`media_3`) shows none**, (d) after deleting the trailing column, the remaining
  columns' footer cells still read their own `stats.mean_mN` (the HIGH-finding
  regression test), and (e) "Add Column" restores `media_7`, growing the visible
  set from the end.

A design note on testability: because the live edit lands in the DB (not the
seed), the existing seed-based parity class (`TestA3SaturationSolubility`, built
from `SEED_TEMPLATES`) continues to exercise the OLD single-`area` shape and stays
green — so it cannot, by itself, cover the new media shape. That is precisely why
the three unit tests above are written against the **new definition object**
directly and are committed with this task: they are the automated coverage for the
new shape. Only the *rewrite of the seed parity class to the media shape* remains
backlogged (Decision 4), and it is backlogged solely because it is coupled to the
separate, standing "capture DB edits as seed modules" work — not because the new
behaviour would otherwise go untested.

---

## Summary of files touched

- **DB (data, not source):** `d:\RD-instance\GIT\backend-v2\lims.db` — a single
  transaction with **two** `UPDATE`s (Decision 5): (1) `test_templates.definition`
  for `code='TPL-A3-0001', version=1` (id 3); (2) `test_worksheets.group_values`
  for worksheet id 53, replacing only the all-null `std_areas` key with six
  caption-seeded rows while copying `standard`/`stats`/`samples` through unchanged.
  Timestamped `lims.db.bak-satsol-media-<ts>` taken first.
- **Frontend (source):**
  `frontend-react/src/features/test-templates/components/WorksheetForm.tsx` —
  three template-scoped, UI-only changes (no new component, no new hook, no type
  change; `labelFrom` already exists in `testTemplate.types.ts`): (1) extend the
  `allowClearColumn` gate to include `TPL-A3-0001`; (2) add the **trailing-only
  delete guard** so the per-column trash icon on `std_areas` shows **only** on the
  highest-numbered currently-visible `media_N`, and never when a single media
  column remains (which pins `media_1`); (3) **seed the initial `hiddenColumns`
  state** with `std_areas.media_7 … media_10` for TPL-A3-0001 so six columns are
  visible by default and the rest are reachable via "Add Column". (Decisions 1
  and 3.)
- **Tests (source, committed this task):** a new `TestA3MediaColumns` class (in
  `backend-v2/tests/calculation/test_seeded_template_parity.py` or a sibling
  `test_media_columns.py`) with the engine/schema unit tests in Testability — full
  10-column parse, per-column independence + blank tolerance, trailing-delete
  footer alignment, the Media 1 reference guard **plus** `media1_present` blocking
  criterion, and the ten-pair `area_field_refs` discovery. Plus the frontend
  component test (trailing-only delete affordance, default-six render, Add Column
  re-grow, footer alignment after trailing delete). Built from the new definition
  object, independent of `SEED_TEMPLATES`.
- **Tests (source, backlogged):** rewrite of the seed-based `TestA3SaturationSolubility`
  parity class to the media shape — deferred only until the DB edit is captured in
  the seed modules, consistent with the project's standing "seed not yet updated"
  caveat. The new-shape coverage above does not depend on this.

Out of scope and untouched: every other template; the `samples`,
`standard`, and context sections (only `samples.solubility`'s divisor and the
`sst_std_rsd` criterion target are repointed, as a forced consequence of removing
the scalar `stats.mean_std`, plus the new `media1_present` blocking criterion
added to the criteria list); all other tables.

---

## Responses to design-review findings (iteration 4 — current)

Review: `design-review.md` / `design-review.json`, verdict **CHANGES_REQUESTED**
(1 HIGH, 1 MEDIUM). This iteration also folds in a **user scope change** (6 → 10
media columns) delivered alongside the two fixes. Every review finding is
**addressed** via the user-chosen option; choices stay within the locked scope
(TPL-A3-0001 only, STD Area in Media table only, Option 1 per-worksheet headings
never written to the template). All previously-approved decisions are intact:
DB-built-from-scratch, per-worksheet `labelFrom` headings via the `media_names`
singleton, caption seeding via `group_values` (not `rows.seed`), `media_1` pinned
as the mandatory reference, edit-the-live-DB with a timestamped backup.

- **USER SCOPE — media columns 6 → 10. ADDED.** `std_areas` now provisions ten
  area fields `media_1 … media_10`; `media_names` has ten heading cells; `stats`
  has ten `mean/sd/rsd` trios; the column-aligned footer carries all thirty refs.
  **Six columns are visible by default** (matching the screenshot) and
  `media_7 … media_10` are reachable via "Add Column". Rejected the shortcut of
  marking the trailing four `hidden: true` in the definition after verifying
  `deletableColumns` filters `!f.hidden`, which would make them un-restorable;
  instead the default-six view is produced by **seeding the per-worksheet
  `hiddenColumns` UI state** for TPL-A3-0001 (Decision 1). Standard-injection rows
  are unchanged. Re-verified `TemplateDefinition.parse` accepts the field keys,
  `required`, and field-level `labelFrom`, and that the engine evaluates
  single-column `mean/sd/rsd(std_areas.media_N)` per column (A2-0004 pattern).
- **Finding 1 (HIGH) — middle-delete misaligns the positional column-aligned
  footer. ADDRESSED via the user-chosen option (c): DELETE TRAILING ONLY.**
  Verified the defect in `renderGroupFooter` (`valueColumns = visibleFields.slice(1)`,
  `cell = row.cells[c]` — positional). The fix exposes the per-column trash icon
  **only on the highest-numbered currently-visible `media_N`** (a `trailingMediaKey`
  derived from `visibleFields`, which is definition-ordered), and suppresses it
  entirely when a single media column remains. Hidden columns therefore always form
  a trailing suffix, so the positional footer never misaligns — no footer-renderer
  surgery, matching the user's explicit choice. Options (a) field-keyed renderer
  and (b) placeholder column were rejected as out-of-scope shared-renderer changes.
  Added an engine test (trailing delete keeps remaining `stats.mean_mN` aligned)
  and a frontend test (middle column has no delete affordance; trailing does;
  footer stays aligned after a trailing delete). Decisions 2 and 3.
- **Finding 2 (MEDIUM) — reportable silently blankable; completion-time seam
  presumed. ADDRESSED via the reviewer's preferred option (i): an IN-DEFINITION
  BLOCKING CRITERION.** Removed the mandated-but-deferred completion-time
  validation prose entirely. Added a blocking criterion
  `media1_present: count(std_areas.media_1) gte 1` to the definition's criteria
  list. Verified against source: `count` = `_f_count` = `float(len(_numeric(...)))`
  always returns a number (0.0 when all-blank, never `EMPTY`); `_evaluate_criteria`
  + `_assess` return `passed = observed >= 1` for `gte`, and `is_blocking_failure`
  is true for a blocking criterion with `passed is False`. So an all-blank
  `media_1` worksheet is blocked from completion through the engine's **existing**
  criteria path — no new seam, no engine change, entirely inside the in-scope
  criteria edit. The target is an expression exactly like the pre-existing
  `prep_agreement` target. Decision 4.

---

## Responses to design-review findings (iteration 3 — historical)

Review: `design-review.md` / `design-review.json`, verdict **CHANGES_REQUESTED**
(1 HIGH, 1 MEDIUM, 1 NIT). All three findings concern the retracted `rows.seed`
mechanism and its fallout. Every finding is **addressed** (none backlogged or
ignored); choices stay within the locked scope (TPL-A3-0001 only, STD Area in
Media table only, Option 1 per-worksheet headings never written to the template).
A fourth, undiscovered fact surfaced while fixing these and is incorporated:
live worksheet 53's `group_values` is NOT empty.

- **Finding 1 (HIGH) — `rows.seed` / `RowSpec.seed` is not a supported schema key;
  captions would not render. ADDRESSED.** Verified independently this iteration:
  `RowSpec` (both Python `template_schema.py` and TS `testTemplate.types.ts`)
  carries only `min/max/default/labelFrom`; `RowSpec.parse` drops a `seed` key
  silently; the only seeding paths (`evaluator._seed_rows`, frontend `seedValues`)
  fill from stored `group_values` then scalar `field.default`. Adopted review
  option (a): **removed `rows.seed` from the definition entirely** and seed the six
  "Standard - N" captions by writing them into **worksheet 53's stored
  `group_values["std_areas"]`** as the second statement of the DB-edit transaction
  (Decision 5). Every claim that `RowSpec.seed` exists / was "verified" is
  retracted (Decision 1 "Row captions"). Scope caveat added: this seeds only
  worksheet 53; template-level caption defaults for future worksheets are an
  out-of-scope `RowSpec.seed` follow-up.
- **Finding 2 (MEDIUM) — `std_label default:null` + no seed contradicts the
  "seeded captions" prose. ADDRESSED.** Removed `std_label`'s `default` and aligned
  all three sections (Decision 1 field notes, Edge cases, Validation rules) to the
  single mechanism: captions live in worksheet 53's `group_values`, seeded by the
  DB edit; a future worksheet opens with the column blank and the analyst types
  the caption. The "out of the box via `rows.seed`" promise is gone.
- **Finding 3 (NIT) — `rows.labelFrom: "std_label"` is inert dead config.
  ADDRESSED.** **Removed `rows.labelFrom` from the definition.** It was
  behaviourally inert (the renderer hard-codes the numeric `#` column and never
  reads `rows.labelFrom`) and only forced `std_label` to exist to satisfy
  `GroupDef.parse`. `std_label` remains a declared field on its own merits (it is
  the caption column); nothing now depends on `rows.labelFrom`.
- **Additional correction (not a review finding) — live worksheet 53 is NOT
  empty.** The prior draft and the review both stated worksheet 53's
  `group_values = '{}'`. Re-queried this iteration, that is true only of the
  worktree DB; the **live** DB (the one edited) stores real `standard`/`samples`
  data plus five all-null `std_areas` rows. Decisions 1 and 5, the GROUND TRUTH
  section, the Data/worksheet-impact section and the abort trigger are corrected
  to preserve `standard`/`stats`/`samples` verbatim, replace only the all-null
  `std_areas` key, and abort only if a `std_areas.area` cell holds a real value.

---

## Responses to design-review findings (iteration 2 — historical)

Review: `design-review.md` / `design-review.json`, verdict CHANGES_REQUESTED
(1 HIGH, 2 MEDIUM, 2 NIT). Every finding is **addressed** (none backlogged or
ignored); all choices stay within the locked scope (TPL-A3-0001 only, STD Area in
Media table only, Option 1 per-worksheet headings never written to the template).

> Note: iteration-2's Finding 3 response below claimed `rows.seed`/`RowSpec.seed`
> support — that claim was **false** and is retracted by iteration-3 Finding 1
> above. Retained here only as history.

- **Finding 1 (HIGH) — deleting/blanking Media 1 silently breaks the reportable
  and SST. ADDRESSED.** Chose review option (a): `std_areas.media_1` is the
  mandatory reference medium and is guarded from deletion exactly like `std_label`
  (its trash icon is suppressed, so it can never be hidden and never becomes an
  "Add Column" target), and it is marked `required: true` with a completion-time
  validation that at least one `media_1` cell is numeric. Options (b) a separate
  standard group and (c) a `coalesce` fallback were considered and rejected with
  reasons (b violates the table-only scope and diverges from the screenshot;
  c silently changes the quantitation standard and cannot fix the single-target
  SST). A committed engine test pins both directions (blank media_1 ⇒ reportable
  and SST `EMPTY`; populated ⇒ they compute). See new subsection in Decision 4 and
  the combined guard in Decision 3.
- **Finding 2 (MEDIUM) — `media_names` does not render as an in-table row.
  ADDRESSED.** Corrected Decision 1 (new subsection "How the heading row actually
  renders") and the overview to describe the actual rendering: a separate "Media
  Name" `<Card>` with six labelled inputs whose values drive the column headers via
  `labelFrom` (verified in the renderer this iteration). Confirmed this is accepted
  for Option 1 — the column-renaming behaviour is identical; a literal in-table
  heading strip would need out-of-scope renderer work and is explicitly not
  undertaken.
- **Finding 3 (MEDIUM) — "Standard - N" captions not seeded; `rows.labelFrom`
  effect unverified. ADDRESSED.** (3a) Added `rows.seed` with the six "Standard -
  1 … 6" captions to the `std_areas` definition so a fresh worksheet 53 shows them
  out of the box (`RowSpec.seed` support verified in `template_schema.py`). (3b)
  Verified in `WorksheetForm.tsx` that the renderer renders a hard-coded numeric
  `#` column and **never consumes `rows.labelFrom`**; corrected the design to say
  the captions appear because `std_label` is an ordinary seeded data column, and
  retained `rows.labelFrom: "std_label"` only as a harmless, non-relied-upon
  forward-compatible key (the claim that it replaces the row number is dropped).
- **Finding 4 (NIT) — Waters CDS import now discovers six area targets.
  ADDRESSED.** Added a Decision 1 note acknowledging `area_field_refs` now returns
  six `('std_areas','media_1..6')` pairs where it returned one, confirming this is
  intended and that wiring further CDS auto-mapping is out of scope (manual area
  entry remains the contract).
- **Finding 5 (NIT) — new media behaviour uncovered until the seed is updated.
  ADDRESSED.** Promoted the engine/schema unit tests from "follow-up" to
  **committed deliverables of this task** (new `TestA3MediaColumns`, built from the
  definition object, independent of `SEED_TEMPLATES`): per-column independence +
  blank tolerance, the Media 1 reference guard, and the six-pair `area_field_refs`
  discovery. Only the seed-parity-class *rewrite* remains backlogged, coupled to
  the separate standing seed-capture work; it no longer gates the new-shape
  coverage. Updated Testability, Decision 4, and the files-touched summary
  accordingly.
