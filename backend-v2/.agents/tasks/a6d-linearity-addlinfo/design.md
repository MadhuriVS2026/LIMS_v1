# TPL-A6D-0002 — "Standard Tapinarof for Linearity" table + Additional-Info right-column fields

Requirements and technical design. This is an investigation-and-design artifact
only: **no `lims.db` write and no author script were produced in this step.** One
read-only inspection script was created and deleted. Two further additions are
designed into the EXISTING Draft template **TPL-A6D-0002** (id=43, version 1,
archetype `A6d`, test_id=25 / `TST-IVRT`, status `Draft`), which already carries
the `sampling_details` sub-section from the prior task.

---

## Summary

Two additions to the live TPL-A6D-0002 definition, in place:

1. **Addition 1 — a new "Standard Tapinarof for Linearity" section.** One single
   add-ROW `sequence` group (the user chose "use 1" — one continuous table, not
   two set-blocks) with eight columns opening with nine blank rows (`default:9`,
   sized for the 6 calibration standards + LQC/MQC/HQC). The row label and the
   Concentration (%) are the fixed named content the analyst enters per row; the
   weight/volume/mL cells are blank reusable inputs. Nothing is baked into the
   stored definition — neither the pasted figures (89.73 / 50.0 / 5.0 / … are
   examples only) nor the row labels/Concentrations, because the engine has no
   per-row seed mechanism (resolved under Addition 1).

2. **Addition 2 — fill the Additional-Info right column.** The header renders
   from the definition's flat `context[]` list. Add the right-column items that
   have no field yet, auto-fetching from the TRF where a real backing source key
   exists and falling back to blank manual inputs where it does not. Several of
   the requested right-column labels already have a context field in the live
   definition (`potency`, `temperature_c`, `donor_area`, `date_of_analysis`,
   `batch_no`) and must NOT be duplicated.

The investigation below pins down the three decisions the task asked for, each
with evidence from the live DB and the actual code.

---

## Investigation — evidence

### Live TPL-A6D-0002 definition (source of truth = `backend-v2/lims.db`)

Read directly from `lims.db`, table `test_templates` (not the seed module — the
DB has diverged from the seed: the seed `a6d_franz_ivrt.py` defines only
TPL-A6D-0001 and has no `sampling_details` group). The live row:

```
id=43  code=TPL-A6D-0002  version=1  status=Draft  archetype=A6d
test_id=25  result_unit=µg/cm²/√h
name="In-Vitro Release (Franz Diffusion Cell) — with Sampling Details"
```

**There is no `additional_info` GROUP in this template.** The "Additional Info"
header the user refers to is the definition's flat **`context[]`** list rendered
as the worksheet header. (Contrast with A8 `TPL-A8-0004`, which *does* model an
`additional_info` singleton group — that is a different template's pattern. A6D's
header is `context`, so Addition 2 edits `context`, matching A6D's own pattern.)

Live `context[]` (17 fields), in order, with `source` where present:

| key | label | kind | type | unit | source | overridable | default |
|---|---|---|---|---|---|---|---|
| `generic_name` | Generic Name | context | text | — | `product.name` | — | — |
| `batch_no` | Batch No. | context | text | — | `trf.batch_number` | — | — |
| `label_claim` | Label Claim | context | number | — | `trf.label_claim_numeric` | yes | — |
| `potency` | Standard Potency | context | — | % | — | yes | 100 |
| `membrane` | Membrane Type / Make | context | text | — | — | yes | — |
| `membrane_lot` | Membrane B. No. | context | text | — | — | yes | — |
| `receptor_media` | Receptor Media | context | text | — | — | yes | — |
| `receptor_volume` | Total Receptor Volume | context | — | mL | — | yes | 7 |
| `replacement_volume` | Media Replacement Volume | context | — | mL | — | yes | 1 |
| `sample_pip` | Withdrawn Aliquot | context | — | mL | — | yes | 1 |
| `sample_vol` | Diluted to | context | — | mL | — | yes | 1 |
| `donor_area` | Donor Chamber Area | context | — | cm² | — | yes | 1.76 |
| `temperature_c` | Temperature | context | — | °C | — | yes | 32 |
| `method_no` | Method No. | context | text | — | — | yes | — |
| `instrument_id` | Instrument ID | context | text | — | — | yes | — |
| `analysed_by` | Analysed By | context | text | — | `session.analyst` | — | — |
| `date_of_analysis` | Date of Analysis | context | date | — | `session.date` | — | — |

Live `groups[]` order: `calibration, curve, qc, cells, sampling_details,
timepoints, flux`. The `timepoints` group is a `sequence` with
`rows = {min:2, max:12, default:6, labelFrom:"time_min"}` — the add-ROW precedent
Addition 1 follows. Per-cell parity is 6 everywhere (`applied_mg_*`,
`sample_weight_mg_*`, `area_*`, `flux_*`).

### Decision (1) — how a "shared / merged across rows of a block" cell is represented

**Finding: the schema has no merge / rowspan / "spans N rows" concept.** Evidence
from `src/domain/services/calculation/template_schema.py`:

- `GroupDef.fields` is a flat tuple of `FieldDef`; a group's rows come only from
  `RowSpec` (`min`/`max`/`default`/`labelFrom`). There is no per-cell "span",
  "merge", "rowspan", or "colspan" attribute anywhere in `FieldDef`, `RowSpec`,
  or `GroupDef`.
- `FieldDef` fields are: `key, kind, label, type, unit, expression, rounding,
  required, default, options, source, overridable, area_source`. None expresses
  a vertical merge.
- The only cross-row mechanism is in *expressions* (`prev`, `prior`, `sum(...)`),
  which is a calculation feature, not a display-merge of an input cell.
- `frontend-react/src/features/test-templates/models/setBlocks.ts` (read directly
  for this design) splits a table's rows into visual "Set N" blocks by a shape
  heuristic (`isSetBlockGroup`: a hidden `cidx` field and no `set_no` field). Its
  own docstring states it is "a PURE DISPLAY transform: rows, columns, values and
  editability are untouched — only their visual grouping changes" and that it
  "carries NO flag on the template definition / DB and names NO template code." So
  it is a UI-only read of the data, carries no definition flag, and does NOT merge
  cells. There is likewise no `mirrorFrom`-style merge for inputs within a group.

**Conclusion / chosen representation.** Because there is no merge primitive, the
pragmatic and schema-honest representation (explicitly confirmed by the task as
the fallback) is: **the two "entered once per block" columns — `Standard Weight
in mg` (col 3) and the first `Diluted to (mL)` (col 4) — are ordinary per-row
blank inputs; the analyst fills them only on the first row of each block
(Calibration-standard-1 and LQC) and leaves them blank on the other rows of that
block.** This is exactly how the example sheet reads (the value appears once per
block, blank beneath). No `default` is stored for these columns, so every cell
renders blank and the analyst decides where to enter. There is no engine
dependency on them (no expression references the linearity group — see
testability), so blank non-first-row cells are harmless.

This is documented here as the deliberate representation so a reviewer does not
mistake the blank non-first-row cells for missing data: **blank = "shared from the
first row of this block", by convention, because the schema cannot merge cells.**
If a true visual rowspan is ever wanted it is a frontend-only concern and a
separate change; it must not drive a schema invention here.

### Decision (2) — which Additional-Info right-column items have a real backing source

**The authoritative catalogue of resolvable `source` keys** is
`WorksheetService._seed_context` in
`src/application/services/worksheet_service.py` (read directly for this design,
lines ~617–670). A context field's `source` is looked up in this `available`
map; the loop is `value = available.get(cf.source) if cf.source else None`, then
`if value is None: value = cf.default` — so an unresolved source falls back to the
field's `default` (or nothing). The two keys this design introduces —
`trf.trf_number` and `trf.ar_number` — were **confirmed present verbatim** in the
`available` map (both map to `trf.trf_number` / `trf.ar_number` on the
`TestRequestForm`). The complete map (verbatim keys):

- `product.code`, `product.name`, `product.material_type`,
  `product.storage_condition`
- `trf.trf_number`, `trf.ar_number`, `trf.batch_number`, `trf.label_claim`,
  `trf.label_claim_numeric`, `trf.stage_of_sample`, `trf.group_name`,
  `trf.quantity`, `trf.storage_condition`, `trf.storage_period`,
  `trf.pack_details`, `trf.manufactured_by`, `trf.product_id`, `trf.remark`
- `line.test_code`, `line.test_name`, `line.specification`, `line.line_no`,
  `line.raw_data_reference`
- `session.username`, `session.analyst`, `session.date`

Note: the `TestRequestForm` entity *has* `mfg_date` and `expiry_or_retest_date`
fields, but **they are NOT in the `available` map**, so there is currently **no
resolvable source key** for a use-before / expiry date. Inventing
`trf.expiry_or_retest_date` as a `source` would silently resolve to nothing
(the A12 worklog's rule: "a context field with neither a resolvable source nor a
default renders as a permanently blank read-only box" — worse than a manual
input). So any item without a real key becomes a blank **manual input**, per the
task's instruction, rather than a fabricated context source.

**Enumeration of all 11 requested right-column items** with their final kind.
"Already present" means a context field already exists in the live definition and
must NOT be duplicated (only its presence is confirmed / optionally relabeled):

| # | Right-column item | Backing source key | Final decision |
|---|---|---|---|
| 1 | Date of Analysis | `session.date` (exists as `date_of_analysis`) | **Already present** (`date_of_analysis`, source `session.date`). The task also lists it among the "remaining per-run measurements → blank manual inputs"; since it already auto-fills from the session date and is the established pattern, keep the existing field. No new field. |
| 2 | Working/reference standard number | none | **Blank manual input** — add `working_std_no` (context, text, overridable, no source, no default). |
| 3 | Use before date | none (`trf.expiry_or_retest_date` not exposed) | **Blank manual input** — add `use_before_date` (context, date, overridable, no source). |
| 4 | Potency(%) | none | **Already present** (`potency`, unit %, default 100, overridable). No new field. |
| 5 | Temperature (°C) | none | **Already present** (`temperature_c`, unit °C, default 32, overridable). No new field. |
| 6 | Time points (Min) | none | **Blank manual input** — add `time_points_min` (context, text, overridable, no default; text because it is a descriptive list like "15,30,60,120,240,360 min", not a single divisor number). |
| 7 | Average weight (mg) | none | **Blank manual input** — add `avg_weight_mg` (context, number, unit mg, overridable, no default). |
| 8 | Batch No.: | `trf.batch_number` (exists as `batch_no`) | **Already present** (`batch_no`, source `trf.batch_number`). No new field. |
| 9 | TRF number | `trf.trf_number` | **Auto-fetch** — add `trf_number` (context, text, source `trf.trf_number`). |
| 10 | A R No. | `trf.ar_number` | **Auto-fetch** — add `ar_number` (context, text, source `trf.ar_number`). |
| 11 | Surface Area of Donor chamber (cm²) | none | **Already present** (`donor_area`, label "Donor Chamber Area", unit cm², default 1.76, overridable). No new field. |

**Net new context fields to add (6):** `trf_number` (auto-fetch),
`ar_number` (auto-fetch), `working_std_no` (manual), `use_before_date` (manual),
`time_points_min` (manual), `avg_weight_mg` (manual).

**Already-present (do NOT duplicate; 5):** `date_of_analysis`, `potency`,
`temperature_c`, `donor_area`, `batch_no`.

Rationale for only two auto-fetches: those are the only two of the eleven whose
datum has a real resolvable key in `_seed_context` AND is not already wired.
`batch_no` is auto-fetch already. Everything else (standard number, use-before,
time points, average weight) has no backing TRF/sample field, so per the task it
is a blank manual input — matching the worklog's explicit warning against context
fields with no source and no default.

> **Open point for review (does not block the design):** the task's framing
> assumes the right column is entirely empty. In the live definition five of the
> eleven labels already have fields. If the user's worksheet is not showing them,
> that is a *rendering/layout* question (left vs right column placement in the
> header), not a missing-field question — and the frontend header renderer is out
> of scope for a definition edit. This design adds the six genuinely-absent fields
> and documents the five that already exist; if the intent was instead to
> *relabel* the existing five to match the user's exact wording
> (e.g. `donor_area` label → "Surface Area of Donor chamber"), that is a one-line
> label change per field and is listed as an optional follow-up below.

### Decision (3) — the sequence-group rows spec for the linearity table

**Precedent:** the live `timepoints` sequence group uses
`rows = {min:2, max:12, default:6, labelFrom:"time_min"}`, and `calibration`
(a `table`) uses `{min:2, max:10, default:6, labelFrom:"level"}`. `RowSpec.parse`
enforces `0 ≤ min ≤ default ≤ max` and `max ≥ min`; `labelFrom` must name one of
the group's own fields.

The linearity table has **nine required rows** (6 calibration standards +
LQC/MQC/HQC) and the user asked for add-ROW capability sized "to hold at least the
9 listed rows." (The rows open blank and are analyst-filled — see the RESOLVED
note under Addition 1; the spec only governs the row *count*, not row content.)

**Chosen rows spec:** `{"min": 9, "max": 15, "default": 9, "labelFrom":
"calibration_curve"}`.

- `default = 9` so the worksheet opens with exactly nine rows ready for the nine
  named standards/QCs. Those rows open blank; the fixed labels/Concentrations are
  analyst-entered (see the RESOLVED note under Addition 1), not stored.
- `min = 9` so an analyst cannot delete below the nine mandated rows (the nine are
  a fixed, named set — unlike `timepoints`, where any count of times is valid).
- `max = 15` gives headroom (six extra rows) for additional QC/standards without
  being unbounded; it mirrors the bounded style of `timepoints` (max 12) and
  `calibration` (max 10) rather than inventing a large cap.
- `labelFrom = "calibration_curve"` points at the row-label text field (column 1),
  exactly as `calibration` uses `labelFrom:"level"` and `timepoints` uses
  `labelFrom:"time_min"`.

Note that `kind: sequence` (not `table`) is chosen deliberately: the task
explicitly says "a sequence group with a rows spec, like the existing
`timepoints` sequence group." Functionally for a non-calculated input table
`table` and `sequence` render the same add/delete-row control; `sequence` is used
to match the named precedent and because `sequence` also permits future `prev`/
`prior` expressions if a linearity regression is later added (it is not in scope
now).

---

## Addition 1 — exact JSON group structure

New group inserted into `definition["groups"]`. **Placement:** immediately after
`qc` and before `cells` (it is a standards/linearity block, companion to
`calibration`/`qc`, and logically precedes the per-cell sample sections). This
placement is a presentation choice; it has no effect on calculation because no
expression references the group.

```json
{
  "key": "linearity",
  "kind": "sequence",
  "label": "Standard Tapinarof for Linearity",
  "rows": { "min": 9, "max": 15, "default": 9, "labelFrom": "calibration_curve" },
  "fields": [
    { "key": "calibration_curve",  "kind": "input", "type": "text",   "label": "Calibration curve" },
    { "key": "concentration_pct",  "kind": "input", "type": "number", "label": "Concentration", "unit": "%" },
    { "key": "std_weight_mg",      "kind": "input", "type": "number", "label": "Standard Weight", "unit": "mg" },
    { "key": "diluted_to_ml_1",    "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL" },
    { "key": "ml_a",               "kind": "input", "type": "number", "label": "mL", "unit": "mL" },
    { "key": "ml_b",               "kind": "input", "type": "number", "label": "mL", "unit": "mL" },
    { "key": "ml_taken",           "kind": "input", "type": "number", "label": "mL taken", "unit": "mL" },
    { "key": "diluted_to_ml_2",    "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL" }
  ]
}
```

Column → field mapping (user's order preserved):

| # | User column header | field key | kind | type | unit | notes |
|---|---|---|---|---|---|---|
| 1 | Calibration curve | `calibration_curve` | input | text | — | row-label text; analyst-entered per row (fixed named set, not stored), `labelFrom` target |
| 2 | Concentration (%) | `concentration_pct` | input | number | % | analyst-entered per row (fixed value, not stored), see intended row content below |
| 3 | Standard Weight in mg | `std_weight_mg` | input | number | mg | blank reusable input; filled once per block (decision 1) |
| 4 | Diluted to (mL) | `diluted_to_ml_1` | input | number | mL | blank reusable input; filled once per block (decision 1) |
| 5 | mL | `ml_a` | input | number | mL | blank reusable input |
| 6 | mL | `ml_b` | input | number | mL | blank reusable input |
| 7 | mL taken | `ml_taken` | input | number | mL | blank reusable input |
| 8 | Diluted to (mL) | `diluted_to_ml_2` | input | number | mL | blank reusable input |

Two columns are literally headed "mL" (cols 5 and 6); keys are disambiguated
`ml_a` / `ml_b` (both labelled "mL" for display) because field keys must be
unique identifiers within a group (`GroupDef.parse` rejects duplicates). The two
"Diluted to (mL)" columns (cols 4 and 8) are likewise `diluted_to_ml_1` /
`diluted_to_ml_2`.

**Fixed row labels & Concentrations** (the nine opening rows). The row label
(`calibration_curve`) and `concentration_pct` are the FIXED, named set the task
lists; every other cell is blank. The nine labels/Concentrations below are the
intended content of the nine opening rows:

| row | `calibration_curve` | `concentration_pct` |
|---|---|---|
| 1 | Calibration standard-1 | 1 |
| 2 | Calibration standard-2 | 5 |
| 3 | Calibration standard-3 | 15 |
| 4 | Calibration standard-4 | 30 |
| 5 | Calibration standard-5 | 40 |
| 6 | Calibration standard-6 | 60 |
| 7 | LQC | 1 |
| 8 | MQC | 15 |
| 9 | HQC | 30 |

The example weight/volume figures (89.73, 50.0, 5.0, 50, 1.0, 50, 15.0, 3.0, 4.0,
6.0, …) are **examples only** and appear nowhere in the stored definition.

> **RESOLVED — where the nine fixed labels/Concentrations live (not the stored
> definition).** Verified by reading the actual creation and render paths:
>
> - **Backend never seeds per-row content.** `WorksheetService.create_worksheet`
>   (`worksheet_service.py` ~line 155) instantiates the worksheet with
>   `group_values={}`. No row content is written at creation; `_seed_context`
>   seeds only the flat `context` values, never group rows.
> - **`RowSpec` carries only counts.** `template_schema.py` `RowSpec` has
>   `min/max/default/label_from` and nothing else — no per-row payload.
> - **`FieldDef.default` is one value for all rows.** The frontend row builder
>   `WorksheetForm.tsx` (`rowCount(group)` = `rows.default ?? rows.min ?? 1`, then
>   for each of N rows `source[field.key] ?? (field.default ?? null)`) applies the
>   *same* `field.default` to every opening row. It cannot express nine distinct
>   labels or nine distinct Concentrations.
> - **`labelFrom` does not seed content.** In both schema and `WorksheetForm.tsx`
>   `labelFrom` only sources a column *header / label text* from an already-entered
>   worksheet value; it injects no row data.
>
> **Conclusion:** there is no mechanism — definition, `RowSpec`, `FieldDef.default`,
> or `labelFrom` — to bake nine *distinct* per-row values into the stored template.
> The template therefore opens with nine blank rows (`default:9`), and the fixed
> row labels (`Calibration standard-1..6`, `LQC`, `MQC`, `HQC`) and their
> Concentration values are entered by the analyst into `calibration_curve` and
> `concentration_pct` on those nine rows. This is schema-honest and matches how the
> live template already handles its other named multi-row groups (`calibration`,
> `qc`: both use `labelFrom` over analyst-entered label fields, with no baked
> per-row content). The table below is the *intended data*, not stored defaults.
> The author step must NOT attempt to persist these nine rows into the definition
> JSON (there is nowhere valid to put them) and the acceptance criteria (AC4/AC5)
> assert they are NOT baked in.

## Addition 2 — exact new `context[]` fields

Append these **six** fields to `definition["context"]` (placement within the list
only affects header ordering; append after `date_of_analysis` or group them with
the related existing fields — presentation only). Do **not** add the five
already-present ones.

```json
{ "key": "trf_number",       "kind": "context", "type": "text", "label": "TRF Number",                        "source": "trf.trf_number" },
{ "key": "ar_number",        "kind": "context", "type": "text", "label": "A.R. No.",                          "source": "trf.ar_number" },
{ "key": "working_std_no",   "kind": "context", "type": "text", "label": "Working / Reference Standard No.",  "overridable": true },
{ "key": "use_before_date",  "kind": "context", "type": "date", "label": "Use Before Date",                   "overridable": true },
{ "key": "time_points_min",  "kind": "context", "type": "text", "label": "Time Points", "unit": "min",        "overridable": true },
{ "key": "avg_weight_mg",    "kind": "context", "type": "number", "label": "Average Weight", "unit": "mg",    "overridable": true }
```

Per new field — key, label, kind, unit, source/manual:

| key | label | kind | type | unit | source / manual | overridable |
|---|---|---|---|---|---|---|
| `trf_number` | TRF Number | context | text | — | **auto-fetch** `trf.trf_number` | no (derived; not overridable, matching `batch_no`/`generic_name` which are source-backed and not overridable) |
| `ar_number` | A.R. No. | context | text | — | **auto-fetch** `trf.ar_number` | no |
| `working_std_no` | Working / Reference Standard No. | context | text | — | manual (no source) | yes (so the blank is editable; the `_common.py` rule requires a source **or** overridable, else a permanently blank read-only box) |
| `use_before_date` | Use Before Date | context | date | — | manual (no source) | yes |
| `time_points_min` | Time Points | context | text | min | manual (no source) | yes |
| `avg_weight_mg` | Average Weight | context | number | mg | manual (no source) | yes |

The source-backed fields in the live definition (`generic_name`, `batch_no`,
`analysed_by`, `date_of_analysis` are non-overridable; `label_claim` is the lone
source-backed-but-overridable field because it is a divisor that must be
correctable — all verified in the live context dump) show the pattern:
source-only context fields that are *not* meant to be edited are left
non-overridable (overridable only where a divisor like `label_claim` must be
correctable). The two new auto-fetch fields follow `batch_no` (not overridable).
The four manual fields MUST be `overridable: true` so they render as editable
blank inputs rather than permanently-blank read-only boxes (the documented
`_common.py` invariant).

---

## Functional requirements

- **FR1.** Edit the EXISTING TPL-A6D-0002 (id=43) definition in place; do not
  create a new template, do not change code/name/version/status/test_id/archetype
  /result_unit, and do not touch TPL-A6D-0001 (id=26).
- **FR2 (Addition 1).** Add one `sequence` group `linearity`, label "Standard
  Tapinarof for Linearity", with the eight fields above and
  `rows = {min:9, max:15, default:9, labelFrom:"calibration_curve"}`, placed
  between `qc` and `cells`. One single continuous table (not two set-blocks).
- **FR3.** The group opens with nine blank rows (`default:9`). The FIXED row
  labels (`Calibration standard-1..6`, `LQC`, `MQC`, `HQC`) and their
  Concentration (%) values are the intended analyst-entered content of those rows;
  they are NOT baked into the stored definition because no per-row seeding
  mechanism exists (see the RESOLVED note under Addition 1). No example weight/
  volume figures are stored either.
- **FR4.** Columns 3 and 4 (`std_weight_mg`, `diluted_to_ml_1`) are blank
  per-row inputs filled once per block by convention (no merge primitive exists);
  this is the documented representation of the user's "entered once" requirement.
- **FR5 (Addition 2).** Append the six new `context[]` fields above:
  `trf_number` + `ar_number` auto-fetch from `trf.trf_number` / `trf.ar_number`;
  `working_std_no`, `use_before_date`, `time_points_min`, `avg_weight_mg` as blank
  overridable manual inputs.
- **FR6.** Do NOT duplicate the five already-present fields (`date_of_analysis`,
  `potency`, `temperature_c`, `donor_area`, `batch_no`).
- **FR7.** The edit is applied by a one-off author script following
  `_apply_a6d_sampling_details.py` / `_apply_cu30_kedit.py`: read the LIVE
  definition from `lims.db`, deep-copy, apply the two additions, validate with the
  service's two-pass gate (`TemplateDefinition.parse` + `WorksheetEvaluator.
  evaluate({}, {})`), write back to the SAME row id=43, re-read and assert
  byte-equality. (The write is the next step; this document is design only.)

## Non-functional requirements

- **NFR1 (safety).** A timestamped backup `lims.db.bak-a6dlinearity-<ts>` must be
  made before the write, matching the established naming.
- **NFR2 (GxP).** The template stays `Draft`; it is routed through the normal
  submit/approve e-sign gate. No status change in the edit.
- **NFR3 (no regression).** The existing groups (`calibration`, `curve`, `qc`,
  `cells`, `sampling_details`, `timepoints`, `flux`), their per-cell parity (6),
  and `resultRef = flux.mean_flux` are unchanged. The two additions are purely
  additive and no existing expression references them.
- **NFR4 (no new source keys).** No `source` value is used that is absent from
  `WorksheetService._seed_context`'s `available` map; items without a key are
  overridable manual inputs.
- **NFR5.** No frontend code change. Both additions render through the existing
  generic sequence/singleton/header renderers.

## Acceptance criteria

1. TPL-A6D-0002 (id=43) `definition.groups` contains a `sequence` group
   `key="linearity"`, `label="Standard Tapinarof for Linearity"`, positioned
   immediately after `qc` and before `cells`.
2. `linearity.rows == {min:9, max:15, default:9, labelFrom:"calibration_curve"}`
   and `labelFrom` names an existing field of the group.
3. `linearity.fields` are exactly, in order: `calibration_curve` (text),
   `concentration_pct` (number, %), `std_weight_mg` (number, mg),
   `diluted_to_ml_1` (number, mL), `ml_a` (number, mL), `ml_b` (number, mL),
   `ml_taken` (number, mL), `diluted_to_ml_2` (number, mL); all `kind=input`.
4. The stored definition bakes in NO per-row content: neither the nine row labels
   (Calibration standard-1..6, LQC, MQC, HQC) nor their Concentrations (1, 5, 15,
   30, 40, 60, 1, 15, 30) nor any field `default` for the input columns appears in
   `linearity` (confirmed by asserting no `default` key on any `linearity` field
   and `rows.default == 9`). The labels/Concentrations are the intended
   analyst-entered content, verified at the integration level (AC12), not baked in.
5. None of the example figures (89.73, 50.0, 5.0, 50, 1.0, 15.0, 3.0, 4.0, 6.0,
   …) appear anywhere in the stored definition.
6. `definition.context` gains exactly six fields: `trf_number` (source
   `trf.trf_number`), `ar_number` (source `trf.ar_number`), `working_std_no`,
   `use_before_date`, `time_points_min`, `avg_weight_mg` (last four: no source,
   `overridable=true`).
7. No duplicate context keys: `date_of_analysis`, `potency`, `temperature_c`,
   `donor_area`, `batch_no` each still appear exactly once (unchanged).
8. Every `source` used resolves to a key in `WorksheetService._seed_context`'s
   `available` map (only `trf.trf_number`, `trf.ar_number` are introduced; both
   present).
9. `TemplateDefinition.parse(definition)` succeeds and
   `WorksheetEvaluator(parsed).evaluate({}, {})` returns
   `has_blocking_failure == False` with `resultRef` still `flux.mean_flux`.
10. Row id=26 (TPL-A6D-0001) is byte-unchanged; id=43 keeps code/name/version/
    status/test_id/archetype/result_unit; only `definition` changes.
11. A `lims.db.bak-a6dlinearity-<ts>` backup exists, created before the write.
12. A freshly instantiated worksheet for TPL-A6D-0002 opens the `linearity` group
    with exactly nine rows (`rows.default == 9`), every editable cell blank, and no
    blocking failure — matching the `test_seeded_template_parity.py` "blank sheet"
    expectation (`evaluate({}, {})` → `has_blocking_failure is False`). The nine
    fixed labels/Concentrations are analyst-entered on those rows, not pre-filled.

## Out of scope

- Any calculation on the linearity table (regression slope/intercept/correlation
  of the standards). The user asked for a data-entry table with reusable blank
  inputs; no formula references it. A linearity regression is a separate
  requirement if wanted later (the `sequence` kind leaves room for it).
- A true visual cell-merge / rowspan for columns 3–4. The schema has no merge
  primitive; the blank-non-first-row convention is the agreed representation. A
  rendered rowspan would be a frontend-only follow-up.
- Relabeling the five already-present context fields to the user's exact right-
  column wording (e.g. `donor_area` → "Surface Area of Donor chamber (cm²)",
  `temperature_c` → "Temperature (°C)"). Optional one-line follow-up; flagged
  under decision (2). Not done here to avoid changing fields the task said are
  reference-only / already populated.
- Header column layout (which fields land in the left vs right column). That is a
  frontend header-rendering concern, not a definition edit.
- Exposing `trf.expiry_or_retest_date` / a potency / a standard-number field as
  new context sources in `_seed_context`. That is a backend service change
  (new TRF→worksheet wiring) outside a template-definition edit; until it exists,
  those items are manual inputs (NFR4).

## Testability

- **Unit-level (no DB):** build the edited definition dict in memory and assert
  `TemplateDefinition.parse` + `WorksheetEvaluator.evaluate({}, {})` succeed
  (AC9); assert `linearity` group shape and rows spec (AC1–AC3); assert the six
  new context keys and no duplicates (AC6, AC7); assert every `source` is in the
  `_seed_context` `available` set (AC8). This mirrors
  `tests/calculation/test_a12_0003_ampho_parity.py`'s definition-shape style and
  needs no database.
- **Integration-level (DB):** after the author script, re-read id=43 and assert
  the two additions present and byte-equality of the written vs re-read
  definition; assert id=26 unchanged (AC10); assert the backup exists (AC11). This
  follows the `_apply_a6d_sampling_details.py` verification pattern.
- **Opening-row behaviour (AC12)** is integration-tested rather than pure-schema:
  a worksheet-creation / `evaluate({}, {})` test asserts the group opens with nine
  **blank** rows and no blocking failure (the `test_seeded_template_parity.py`
  blank-sheet pattern). It deliberately does NOT assert pre-filled labels/
  Concentrations, because the resolved finding is that no per-row seed mechanism
  exists — the nine labels/Concentrations are analyst-entered, so a parity test
  would supply them via `group_values` if it wanted to exercise a filled table.
- **Hard to test:** live header column placement (left vs right) — a manual check
  via `start-lims.bat`. Everything else is deterministic and scriptable. A design
  that needed a merge primitive would be hard to test; the blank-non-first-row
  convention keeps it trivially testable (plain inputs).

---

## Resolved decisions (summary)

1. **"Shared across rows of a block" cell:** the schema has NO merge/rowspan
   primitive (`template_schema.py`: `FieldDef`/`RowSpec`/`GroupDef` carry no span
   attribute; `setBlocks.ts` is a UI-only heuristic, not a merge). Chosen
   representation: `std_weight_mg` and `diluted_to_ml_1` are ordinary blank
   per-row inputs, entered only on the first row of each block by convention,
   blank beneath — the documented fallback.
2. **Additional-Info right column (all 11 enumerated):** only
   `trf_number` (`trf.trf_number`) and `ar_number` (`trf.ar_number`) are genuinely
   new auto-fetches with a real backing key in `WorksheetService._seed_context`.
   `batch_no` is already auto-fetch; `date_of_analysis`, `potency`,
   `temperature_c`, `donor_area` already exist. The remaining four —
   `working_std_no`, `use_before_date`, `time_points_min`, `avg_weight_mg` — have
   NO backing source key, so they are blank overridable manual inputs (not
   fabricated context sources). Six new fields added, five left as-is.
3. **Linearity rows spec:** `{min:9, max:15, default:9,
   labelFrom:"calibration_curve"}` on a `sequence` group, following the
   `timepoints` precedent, sized to open with the nine required rows (all blank),
   prevent deleting below nine, and allow up to six more. The nine row labels and
   Concentrations are analyst-entered, not baked into the definition — verified
   against the creation path (`create_worksheet` seeds `group_values={}`), the
   schema (`RowSpec` holds only counts), and the frontend row builder
   (`WorksheetForm.tsx` applies one `field.default` to all rows). No per-row seed
   mechanism exists, so the fixed values cannot and must not be stored.
