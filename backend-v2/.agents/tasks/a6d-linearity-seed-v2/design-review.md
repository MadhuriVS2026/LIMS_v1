# Design Review — TPL-A6D-0002 per-row linearity seeding + eleven Additional-Info defaults

Reviewed document: `.agents/tasks/a6d-linearity-seed-v2/design.md`
Review performed fresh against live code at `d:\RD-instance\GIT\backend-v2` and
`d:\RD-instance\GIT\frontend-react`, plus the live `lims.db` row id=43. Every
engine/schema/frontend quote in the design was re-read firsthand, and the live
template definition was queried directly rather than trusting the design's Evidence
section.

**Verdict: APPROVED** (0 HIGH, 0 MEDIUM, 3 NIT).

The design's central mechanism — seed nine rows into `group_values["linearity"]` at
`create_worksheet`, return them verbatim through the API, and let the existing generic
`WorksheetForm` row builder render them — traces correctly and completely against
firsthand code. The user's core complaint ("still not viewing on the UI") is addressed
by a path I was able to verify end to end, including the exact render `<span>` and the
repository round-trip that the design itself only hedged as an assumption.

---

## End-to-end mechanism verification (the primary gate)

**Addition 1 — nine seeded linearity rows. VERIFIED end to end.**

1. **Definition JSON → parse.** `RowSpec` and `GroupDef.parse` in
   `src/domain/services/calculation/template_schema.py` were read firsthand. The
   design's proposed `seed` field, `RowSpec.parse` validation, and the `GroupDef.parse`
   seed-key check all slot into real code: `GroupDef.parse` does build a `seen` set of
   field keys and already validates `labelFrom ∈ seen`, so the design's
   `field_keys = seen` snippet is accurate and placeable. Absent `seed`, the frozen
   dataclass default `()` keeps every existing template parsing unchanged — correct.
2. **lims.db.** Confirmed firsthand: id=43 is `TPL-A6D-0002`, v1, `Draft`, archetype
   `A6d`, test_id 25, result_unit `µg/cm²/√h`, top keys exactly
   `resultRef, context, groups, criteria`, groups
   `calibration, curve, qc, cells, sampling_details, timepoints, flux`. "After `qc`,
   before `cells`" is a real, valid insertion point. The new key `linearity` does not
   collide with the existing `curve` group. `TemplateDefinition.parse` rejects
   duplicate group keys, so this is safe.
3. **create_worksheet seeding.** `src/application/services/worksheet_service.py`
   `create_worksheet` was read firsthand: it constructs `TestWorksheet(... group_values={} ...)`
   today, exactly as quoted. The proposed `_seed_group_rows(definition)` helper mirrors
   `_seed_context` and is the single functional seam. Verified correct.
4. **Persistence of creation-time group_values.** The design flags this as an
   unverified "stated assumption." **I verified it and it is TRUE.**
   `src/infrastructure/database/repositories/test_template_repository_impl.py`
   `create()` maps `group_values=worksheet.group_values` straight to the JSON column,
   and `tests/calculation/test_template_repository.py::test_worksheet_create_and_fetch_by_test_line`
   creates a worksheet with `group_values={"g": [{"a": 21.0}]}` and asserts the
   round-trip `by_line.group_values["g"][0]["a"] == 21.0`. The fallback the design
   describes is therefore unnecessary — but harmless. Not a defect; see NIT #2.
5. **API response.** `src/api/v1/endpoints/worksheet_endpoints.py::create_worksheet`
   calls the service then `service.preview(worksheet.id)` and returns
   `WorksheetResponse.model_validate(worksheet)`, which serializes `group_values`
   verbatim. Verified.
6. **Frontend render.** `frontend-react/.../WorksheetForm.tsx` was read in full.
   `rowCount` returns `stored.length` when stored rows exist; `seedValues` copies
   `source[field.key]` into form `values` for every editable field. `calibration_curve`
   (`kind:input,type:text`) and `concentration_pct` (`kind:input,type:number`) are
   editable, so both seed into `values`. The table/sequence renderer iterates
   `rows = values[group.key]` and calls `renderInput`, which reads
   `values[group.key]?.[rowIndex]?.[field.key]`. A disabled input still displays its
   bound value, so the nine seeded labels/concentrations are visible on open even
   before the analyst clicks Edit. No `WorksheetForm.tsx` change is required — verified,
   not assumed. The frontend `RowSpec` type lacks a `seed` field, but the frontend
   never reads `rows.seed`; an extra JSON key is ignored at runtime. Correct.

**Addition 2 — eleven Additional-Info defaults. VERIFIED end to end.**

- `_seed_context` was read firsthand and matches the design's quote exactly:
  `value = available.get(cf.source) if cf.source else None; if value is None: value = cf.default`.
  The design's "remove the source" rule is correct: `session.date` and
  `trf.batch_number` always resolve non-None in the live `available` map (confirmed
  present in the map firsthand), so the baked default is only reached when the source
  is dropped.
- The live `available` map contains `trf.trf_number`, `trf.ar_number`,
  `trf.batch_number`, `session.date`, and contains **no** working-standard, potency,
  use-before, time-points, or average-weight key. This confirms the design's claim that
  the five manual values can only come from fixed defaults, matching the user's option
  (a).
- The context render path in `WorksheetForm.tsx` is a single grid: every context field
  renders through `const current = contextValues[field.key] ?? stored;` then the
  `<span>{... String(current)}</span>` (or an editable input when overridable and in
  edit mode). There is no separate left/right-column code — confirmed firsthand. Giving
  each of the eleven a non-empty `default` makes `current` non-empty, so all eleven
  render identically to the existing populated fields. The user's "right column not
  viewing" is explained and fixed.

**Existing-precedent check (gate item).** The design explicitly searched for a per-row
seed precedent (`seed`, `seedRows`, `rowSeed`, `prefill`) and concluded none exists;
only `evaluator._seed_rows` (uniform `field.default`) and unrelated DB seeding. I
independently confirmed `RowSpec` carries only `min/max/default/label_from` and that
`field.default` is a single scalar applied uniformly in both `_seed_rows` and the
frontend `seedValues`. The design did **not** invent a key before checking — it checked,
found nothing, and introduced the task-supplied `rows.seed`. Gate satisfied.

---

## Findings

1. **NIT — Internal inconsistency in the new-context-key count ("5" vs "6").**
   In the "Net changes to `context[]`" section the design writes **"Add 5 new
   fields:"** and then lists **six** keys (`working_std_no`, `use_before_date`,
   `time_points_min`, `avg_weight_mg`, `trf_number`, `ar_number`), self-correcting in
   the same sentence to "that is **six** new keys." The Summary likewise says "five are
   new context fields." The canonical list, the exact JSON block, and acceptance
   criterion #7 all correctly say **six**. The arithmetic is right where it matters
   (six keys added; five of the eleven map to existing keys: `date_of_analysis`,
   `potency`, `temperature_c`, `donor_area`, `batch_no`), so no implementer following
   the JSON block or AC #7 will go wrong — but the stray "5"/"five" phrasings are a
   contradiction worth removing.
   **Fix:** change "Add 5 new fields:" to "Add 6 new fields:" and the Summary's "five
   are new context fields" to "six are new context fields." Keep the canonical six-key
   list and AC #7 as the source of truth.

2. **NIT — The "stated assumption" about creation-time `group_values` persistence is
   actually already proven by existing code and a test; presenting it as unverified
   overstates the risk.** The design's Decision A note and Stated Assumptions section
   hedge that `TestWorksheet.__init__`/the repo mapper may drop a creation-time
   `group_values` and propose a `set_values`/create-mapper fallback. The repo `create()`
   maps `group_values` to a JSON column and `test_template_repository.py` round-trips it
   at creation. The hedge is harmless (the mechanism works either way) but misleads on
   effort/risk.
   **Fix:** downgrade the assumption to a one-line confirmation citing
   `test_worksheet_create_and_fetch_by_test_line` and
   `test_template_repository_impl.create()`, and drop the fallback as dead weight (or
   keep it as a one-line "already proven; no fallback needed").

3. **NIT — Decision C ("entered once per block" for columns 3–4) leaves a convention
   unenforced, which is acceptable but should be called out as a known UI gap, not
   silently relied on.** The design correctly establishes there is no
   merge/rowspan/colspan primitive (`FieldDef`/`RowSpec` carry none — confirmed) and
   leaves `std_weight_mg` / `diluted_to_ml_1` as ordinary blank per-row inputs filled
   "by convention" only on the first row of each block. This is a reasonable scope call
   and is listed under Out of Scope, but an analyst can freely type into those cells on
   any row, so the "once per block" semantic is purely social. No schema or data defect
   results.
   **Fix (optional):** add one sentence to the Decision C paragraph noting these two
   columns are not visually merged and nothing prevents per-row entry, so downstream
   readers of the stored rows must not assume blanks mean "inherited from row 1."

---

## Verified Assumptions

- **Live id=43 metadata and definition shape** — queried `lims.db` directly: id=43,
  `TPL-A6D-0002`, v1, `Draft`, `A6d`, test_id 25, result_unit `µg/cm²/√h`, top keys
  `resultRef, context, groups, criteria`, groups
  `calibration, curve, qc, cells, sampling_details, timepoints, flux`, 17 context
  fields. Matches the design's Evidence exactly.
- **All 17 context keys with their sources/defaults/overridable/type** — match the
  design's table verbatim, including `potency` default 100, `temperature_c` default 32,
  `donor_area` default 1.76, `batch_no` src `trf.batch_number` (no default),
  `date_of_analysis` src `session.date` type `date` (no default).
- **Existing rows specs** — `calibration table {min2,max10,default6,labelFrom level}`,
  `qc table {min0,max24,default6,labelFrom level}`, `timepoints sequence
  {min2,max12,default6,labelFrom time_min}`. Match the design.
- **`RowSpec` / `FieldDef` source** — the design's quotes are accurate;
  `RowSpec` carries only `min/max/default/label_from`; `FieldDef.default` is a single
  scalar; `GroupDef.parse` builds a `seen` field-key set and validates `labelFrom`,
  making the proposed seed-key validation placeable.
- **`create_worksheet` passes `group_values={}`; `_seed_context` default-fallback
  logic** — read firsthand, matches the quotes.
- **`available` source map** — contains `trf.trf_number`, `trf.ar_number`,
  `trf.batch_number`, `session.date`; contains no working-standard / potency /
  use-before / time-points / average-weight key. Confirms the fixed-default approach is
  necessary for those values.
- **API serializes stored `group_values`/`context_values` verbatim** — `_detail` →
  `WorksheetResponse.model_validate(worksheet)` in `worksheet_endpoints.py`.
- **Frontend render path** — `rowCount`, `seedValues`, `renderInput`, and the context
  grid `<span>`/`InputText`/`InputNumber` all read as the design quotes; no
  per-template branch is needed for `linearity`.
- **Creation-time `group_values` persists** — repo `create()` mapping plus
  `test_worksheet_create_and_fetch_by_test_line` round-trip prove it (upgrades the
  design's "stated assumption" to verified).
- **Author-script precedent and backup exist** — `_apply_a6d_sampling_details.py` is
  present, and `lims.db.bak-a6dlinearity2-20261027-122834` exists as the design claims.
- **Eleven field mapping completeness** — all eleven user values (incl. the eleventh,
  Date of Analysis → "06 April 2026") are mapped with exact defaults; six new keys,
  five mapped to existing keys; `date_of_analysis`/`batch_no` sources dropped.
- **Nine seed rows** — labels `Calibration standard-1..6`, `LQC`, `MQC`, `HQC` with
  concentrations `1,5,15,30,40,60,1,15,30`; only `calibration_curve`/`concentration_pct`
  seeded, the six input columns blank. Matches the original user request (messages 2
  and the set-2 block).
- **Add-row spec** — `rows {min:9, max:15, default:9, labelFrom:"calibration_curve"}`,
  consistent with the `timepoints`/`calibration` bounded-sequence precedents.

## Unverified / Wrong Assumptions

- **None material.** The only item the design itself labeled "unverified" (creation-time
  `group_values` round-trip) is in fact verifiable and TRUE — see Verified Assumptions
  and NIT #2. No claim in the design was found to be wrong.
- **Not independently re-derived (low risk, flagged for honesty):** the prior reference
  design `a6d-linearity-addlinfo/design.md` exists and is cited for reused conclusions
  (the `_common.py` "source-or-overridable-or-blank-box" invariant and prior NIT #3).
  Those conclusions were re-grounded against live code here (context render path,
  `available` map, `_seed_context`), so the reuse does not rest on the prior design's
  word. The `_common.py` invariant text itself was not re-opened in this review; it is
  not load-bearing for the mechanism (every new field carries both a default and
  `overridable:true`, so it renders pre-filled and editable regardless).
- **Runtime proof is deferred by design** because `create_worksheet` rejects non-Active
  templates and id=43 is `Draft`. The design's split proof plan (schema unit test +
  `_seed_group_rows` unit test without a worksheet + a throwaway Active-copy e2e render
  proof + parity regression) is sound and does not require weakening the Active-only
  guard on the shipped Draft. This is a correct deferral, not a gap.
