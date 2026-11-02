# Design Review — TPL-A6D-0002 "Standard Tapinarof for Linearity" + Additional-Info fields

Reviewed document: `backend-v2/.agents/tasks/a6d-linearity-addlinfo/design.md`
Review mode: fresh / standalone (no authoring context assumed). All load-bearing
claims were re-verified against live source and the live `lims.db`; no files were
edited and `lims.db` was not written.

**Verdict: APPROVED** — zero HIGH and zero MEDIUM findings. Three NITs recorded
below; none blocks.

---

## Evidence gathered (what I actually ran / read)

- Read `src/domain/services/calculation/template_schema.py` in full —
  `FieldDef`, `RowSpec`, `GroupDef`, `TemplateDefinition`.
- Read `src/application/services/worksheet_service.py` — `_seed_context`
  `available` map (~lines 628–662) and `create_worksheet` (~line 150).
- Read `scripts/template_definitions/_common.py` — the "source-or-overridable or
  permanently-blank read-only box" invariant (lines 50–53).
- Read `_apply_a6d_sampling_details.py` header — the FR7 author-script precedent.
- Queried live `lims.db` `test_templates` for TPL-A6D-0001 (id=26) and
  TPL-A6D-0002 (id=43): full `context[]`, `groups[]` order + rows specs, resultRef.
- Built the proposed edited definition (linearity group + 6 context fields) in
  memory and ran the service two-pass gate
  `TemplateDefinition.parse(...)` + `WorksheetEvaluator(...).evaluate({}, {})`.

---

## Gating criteria (from the task) — outcome

1. **Shared/merged cell representation cites a real precedent OR documents the
   blank-on-non-first-row fallback as deliberate** — **MET.** The design proves
   (and I re-verified) that `template_schema.py` has no span/merge/rowspan
   attribute on `FieldDef`/`RowSpec`/`GroupDef`, and documents the
   blank-on-non-first-row convention as the deliberate, schema-honest fallback
   (decision 1, Out-of-scope, Resolved decisions §1).

2. **All 11 Additional-Info items enumerated with a final kind; every auto-fetch
   names a context key that exists in the real wiring** — **MET.** All 11 are
   enumerated with a final decision. The only two auto-fetch keys introduced,
   `trf.trf_number` and `trf.ar_number`, are present verbatim in
   `WorksheetService._seed_context`'s `available` map. No invented key is used as
   a `source`. Items without a real key (`working_std_no`, `use_before_date`,
   `time_points_min`, `avg_weight_mg`) are correctly made overridable manual
   inputs, not fabricated sources.

3. **Calibration/linearity rows spec follows the timepoints sequence precedent,
   sized ≥ 9 rows, labelFrom at the "Calibration curve" label field** — **MET.**
   `rows = {min:9, max:15, default:9, labelFrom:"calibration_curve"}` on a
   `sequence` group; `labelFrom` names the group's own col-1 text field. Verified
   it parses and `RowSpec.parse` accepts it (`0 ≤ min ≤ default ≤ max`,
   `labelFrom` ∈ fields).

4. **Group JSON matches live schema patterns (kind/fields/units), not invented
   structure** — **MET.** Verified by parsing the full proposed definition
   against the live DB row and running `evaluate({}, {})` →
   `has_blocking_failure == False`, groups order
   `[calibration, curve, qc, linearity, cells, sampling_details, timepoints,
   flux]`, `resultRef` still `flux.mean_flux`.

---

## Findings

1. **NIT — AC12 wording overstates what is tested.**
   AC12 says "A freshly instantiated worksheet for TPL-A6D-0002 opens the
   `linearity` group with exactly nine rows…". A literal "freshly instantiated
   worksheet" goes through `WorksheetService.create_worksheet`, which rejects any
   template that is not Active (`if not template.is_selectable: raise …`,
   `worksheet_service.py` ~line 139; `is_selectable` returns `status == ACTIVE`,
   `test_template.py` line 133). TPL-A6D-0002 is `Draft`, so a real
   `create_worksheet` call would raise before opening any group. The design's own
   Testability section already resolves this correctly — AC12 is actually an
   `evaluate({}, {})` blank-sheet assertion, not a `create_worksheet` call — but
   the AC12 prose does not say so and could mislead the coder into calling
   `create_worksheet` on a Draft row.
   **Fix:** reword AC12 to "Parsing the edited definition and running
   `WorksheetEvaluator.evaluate({}, {})` yields `has_blocking_failure == False`
   and the `linearity` group reports `rows.default == 9` with every field blank
   (no `default`)," matching the Testability section. (Row count at render is a
   frontend concern driven by `rows.default`; the evaluator does not instantiate
   nine rows, so assert on the spec, not on nine materialised rows.)

2. **NIT — "nine rows at open" is a frontend behavior, stated as if backend.**
   FR3/AC12 describe the worksheet "opening with nine blank rows." The design
   correctly attributes this to `WorksheetForm.tsx` (`rowCount = rows.default ??
   rows.min ?? 1`) in the Resolved note, but FR3 reads as a backend guarantee.
   Backend `evaluate({}, {})` and `create_worksheet` (`group_values={}`) store no
   rows; the nine-row open is purely the frontend row builder reading
   `rows.default`. This is consistent with the design's other statements, just
   phrased ambiguously in FR3.
   **Fix:** add a half-sentence to FR3: "(the nine-row open is produced by the
   frontend row builder reading `rows.default`; the stored definition and the
   backend evaluator hold no rows)."

3. **NIT — unit on a `date`/`text` manual field has no effect; harmless but
   note it.** `time_points_min` is `type:text` with `unit:"min"`. `FieldDef`
   accepts a `unit` on any type, and it parses fine (verified), but a unit on a
   free-text "15,30,60…" field is display-only and may render oddly next to a
   text box. Not a correctness issue.
   **Fix (optional):** drop `unit:"min"` from `time_points_min` and fold the unit
   into the label ("Time Points (min)"), or leave as-is — either is acceptable.

---

## Verified Assumptions

- **No merge/rowspan primitive in the schema.** Confirmed: `FieldDef` fields are
  exactly `key, kind, label, type, unit, expression, rounding, required, default,
  options, source, overridable, area_source` — no span/merge/rowspan/colspan.
  `RowSpec` is only `min/max/default/label_from`. `GroupDef` is
  `key/kind/label/rows/fields`. The blank-on-non-first-row fallback is therefore
  the honest representation.
- **`RowSpec.parse` constraints.** Confirmed `0 ≤ min ≤ default ≤ max`,
  `max ≥ min`, and `labelFrom` must be one of the group's fields. The proposed
  `{min:9, max:15, default:9, labelFrom:"calibration_curve"}` satisfies all.
- **`GroupDef.parse` rejects duplicate field keys.** Confirmed — justifies the
  `ml_a`/`ml_b` and `diluted_to_ml_1`/`diluted_to_ml_2` disambiguation.
- **`FieldDef.default` is a single value applied to all rows.** Confirmed — a
  definition cannot bake nine *distinct* per-row labels/Concentrations. The
  design's "analyst-entered, not stored" conclusion is correct.
- **`create_worksheet` seeds `group_values={}`.** Confirmed at
  `worksheet_service.py` ~line 150 — no per-row content at creation.
- **`_seed_context` `available` map contains `trf.trf_number` and
  `trf.ar_number` verbatim.** Confirmed (lines ~634–635). The source→value→default
  fallback (`available.get(cf.source)` then `cf.default`) is as described.
- **`trf.mfg_date` / `trf.expiry_or_retest_date` are NOT in the `available`
  map.** Confirmed — justifies `use_before_date` being a manual input rather than
  an invented source.
- **`_common.py` invariant.** Confirmed verbatim: "Every field here either
  resolves from a source or is `overridable` — a context field with neither, and
  no default, would render as a permanently blank read-only box." Justifies
  `overridable:true` on the four manual fields.
- **Live TPL-A6D-0002 (id=43) shape.** Confirmed: Draft, archetype A6d,
  test_id=25, result_unit `µg/cm²/√h`, resultRef `flux.mean_flux`; top-level keys
  `[resultRef, context, groups, criteria]`; 17 context fields exactly as the
  design's table (keys/labels/sources/defaults match); groups order
  `calibration, curve, qc, cells, sampling_details, timepoints, flux`;
  **no `additional_info` group** (header renders from `context[]`).
- **Already-present context fields (must not duplicate).** Confirmed present:
  `date_of_analysis` (source `session.date`), `potency` (unit %, default 100,
  overridable), `temperature_c` (unit °C, default 32, overridable), `donor_area`
  (unit cm², default 1.76, overridable), `batch_no` (source `trf.batch_number`).
- **`timepoints` precedent.** Confirmed `sequence`,
  `{min:2, max:12, default:6, labelFrom:"time_min"}`. `calibration` and `qc` use
  `labelFrom:"level"` over analyst-entered label fields — matches the design's
  claim about named multi-row groups.
- **Full proposed edit parses and evaluates clean.** Confirmed:
  `TemplateDefinition.parse` succeeds, groups order
  `[calibration, curve, qc, linearity, cells, sampling_details, timepoints,
  flux]`, context count 23 (17+6), `evaluate({}, {})` →
  `has_blocking_failure == False`, `resultRef` preserved.
- **FR7 author-script precedent exists** (`_apply_a6d_sampling_details.py`) and
  does read-live → deep-copy → two-pass validate → write-back → byte-equality
  assert, as the design states.

## Unverified / Wrong Assumptions

- None material. Every load-bearing claim in the design was independently
  reproduced. The only gaps are the NIT-level phrasing issues above (AC12's
  "freshly instantiated worksheet" and FR3's "opens with nine rows" describe
  frontend render behavior as if it were a backend guarantee), which the design's
  own Testability section already clarifies — so they are inaccuracies of
  emphasis, not wrong facts.
