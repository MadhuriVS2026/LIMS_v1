# Implementation Plan — A8-0004 Content Uniformity (by HPLC), 30 units ("CU-tablets-30units")

Goal: Create a NEW Content Uniformity by HPLC seed template for 30 units (USP <905> stage 2),
bound to a NEW Test Master entry named EXACTLY `CU-tablets-30units`. Build it FRESH as its own
new module, but REUSE the existing standard + bracketing-standard suitability LOGIC verbatim.
Formula-exact GxP build: reproduce the CU Acceptance-Value arithmetic exactly, seed Active, keep
the stored DB definition byte-for-byte equal to the module.

## Grounding facts confirmed during exploration (do not re-derive)

- Next free A8 code: **TPL-A8-0004**. Live DB (`backend-v2/lims.db`) A8 rows are TPL-A8-0001
  (Inactive v1 + Active v2), TPL-A8-0002 (Active), TPL-A8-0003 (Draft "content uniformity for
  tablet" — NOT in the module `SEED_TEMPLATES`, so the seeder never touches it). TPL-A8-0004 is
  free. USE **TPL-A8-0004**.
- Test `TST-CU-30U` does NOT exist yet. `TST-CU` (id 14) and `TST-CUWV` (id 15) exist and must
  NOT be reused.
- Source module `backend-v2/scripts/template_definitions/a8_content_uniformity.py` defines
  `_ACCEPTANCE_VALUE`, `_cu_context`, `_summary_group`, `_cu_criteria`, `A8_HPLC_DEFINITION`
  (groups: `standard_group(conc_label="Standard Concentration")`, `replicate_area_group(default_rows=5)`,
  `standard_statistics_group()`, `units` table rows {min:1,max:30,default:10}, `_summary_group("units")`).
- Bracketing pattern source `a12_derived_rollups.py`: blocks `bkt_1`/`bkt_2` are `kind:"table"`,
  rows `{"min":0,"max":6,"default":0}`, each a single `area` field; the pooled stat field is
  `"expression": "rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))"`, with a blocking SST
  criterion on it (`operator:"lte"`, `limit:2.0`, `severity:"blocking"`, `limitText:"NMT 2.0 %"`).
- `_common.py` helpers to reuse: `standard_group`, `replicate_area_group`, `standard_statistics_group`,
  `sst_rsd_criterion`, `context_header`, `standard_chain_terms`, `dilution_fields`.
  `replicate_area_group(default_rows=5)` already attaches a footer referencing `stats.mean_std`,
  `stats.sd_std`, `stats.rsd_std` — the `stats` singleton MUST keep those three keys.
- Registration: `__init__.py` imports each module's `TEMPLATES` and splices them into
  `SEED_TEMPLATES`, ordered by archetype; `_A8` is `*_A8` between `*_A7` and `*_A9_A10_A13`.
- Seeder `scripts/seed_test_templates.py` is additive + idempotent: validates all, then for a
  new code calls `ensure_test` (creates the Test if absent) and inserts the template `Active`
  (`approved_by="seed"`). `--validate-only` parses + dry-run-evaluates every definition.
- Test framework: pytest (`pyproject.toml`, `asyncio_mode=auto`). Run from `backend-v2`.
  Parity-test pattern to copy: `tests/calculation/test_a12_0003_ampho_parity.py` (imports the
  definition dict directly, `TemplateDefinition.parse(...)`, `WorksheetEvaluator(...).evaluate(...)`,
  asserts `result.values[...]`, `result.row_value(group,i,field)`, and criteria via
  `TemplateDefinition.parse(...).criteria`).
- **Known pre-existing failures (baseline, must stay EXACTLY these 5):**
  `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_unit1_release_carryover`,
  `::test_per_timepoint_summary`, `::test_amount_remaining`;
  `test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`,
  `::test_a_qa_correction_reopens_and_republishes_the_result`. Baseline run: 5 failed, 798 passed.

## CRITICAL — AV nesting warning (verbatim, DO NOT reorder)

`_ACCEPTANCE_VALUE` is USP <905> AV = |M - X| + k·s with the **upper bound tested outermost and
the lower bound inside**. Reversing the two tests gives the WRONG answer for any mean below 98.5.
The new module MUST reuse `_ACCEPTANCE_VALUE` UNCHANGED (import it or reproduce byte-identically):

```
if(mean_pct < 101.5,
   if(mean_pct < 98.5, (98.5 - mean_pct) + k_value * sd_pct, k_value * sd_pct),
   (mean_pct - 101.5) + k_value * sd_pct)
```

Prefer IMPORTING `_ACCEPTANCE_VALUE`, `_summary_group`, `_cu_criteria` from
`a8_content_uniformity` so the AV string is literally the same object — this is the surest way to
keep it byte-identical and is what "reuse verbatim" means.

---

- [ ] 1. MANDATORY FIRST — fresh DB backup.
      Copy `backend-v2/lims.db` to `backend-v2/lims.db.bak-cu30-<yyyymmdd-HHMMSS>` (timestamp in
      that exact format). Verify the backup's byte size equals the original's. Record the exact
      backup filename in the commit message / task notes.
      Files: creates `backend-v2/lims.db.bak-cu30-<yyyymmdd-HHMMSS>` (gitignored).
      Verify: the copy exists and its file size equals `lims.db` size (compare byte counts and
      confirm they match); print the backup filename.

- [ ] 2. Create the new fresh module `a8_cu_tablets_30units.py` with the full template definition.
      Create `backend-v2/scripts/template_definitions/a8_cu_tablets_30units.py`. Import from
      `scripts.template_definitions._common`: `SeedTemplate`, `context_header`, `dilution_fields`,
      `replicate_area_group`, `standard_chain_terms`, `standard_group`, `standard_statistics_group`,
      `sst_rsd_criterion`. Import from `scripts.template_definitions.a8_content_uniformity`:
      `_ACCEPTANCE_VALUE`, `_summary_group`, `_cu_criteria` (reuse verbatim — AV nesting must be
      byte-identical to the source). Build the definition with these exact pieces:
        - `resultRef`: `"summary.acceptance_value"`.
        - context: reuse `_cu_context`'s shape and the k label, but **default k_value = 2.0** (USP
          <905> k for n=30 is 2.0, not 2.4). Since `_cu_context` hard-codes default 2.4, define a
          local `_cu_context_30()` that returns `context_header(extra=[{ "key":"k_value",
          "kind":"context", "label":"Acceptability Constant k (2.4 for n=10, 2.0 for n=30)",
          "default":2.0, "overridable":True }])` — same label, same shape, only the default changes.
        - groups, in order:
          1. `standard_group(conc_label="Standard Concentration")`.
          2. `replicate_area_group(default_rows=5)` → key `std_areas` (footer references
             `stats.mean_std` / `stats.sd_std` / `stats.rsd_std`, so keep those stat keys).
          3. Two bracketing blocks (A12-0001 shape): `bkt_1` and `bkt_2`, each
             `{"key":..., "kind":"table", "label":"Bracketing Standard — Block N",
             "rows":{"min":0,"max":6,"default":0}, "fields":[{"key":"area","kind":"area","label":"BKT STD Area"}]}`.
          4. `stats` singleton (`kind:"singleton"`, label "Standard Statistics") with the three
             standard-replicate fields from `standard_statistics_group()` (keys `mean_std`,
             `sd_std`, `rsd_std` over `std_areas.area`) PLUS a pooled bracketing field
             `{"key":"rsd_bkt","kind":"calculated","label":"%RSD (pooled with bracketing standards)",
             "unit":"%","expression":"rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))"}`.
             (Build by taking `standard_statistics_group()`'s fields and appending `rsd_bkt`, OR
             hand-write the singleton with all four fields — keep key `mean_std` unchanged because
             the per-unit `pct_lc` divides by `stats.mean_std`.)
          5. `units` table: SAME fields and SAME `pct_lc` expression as `A8_HPLC_DEFINITION`
             (`unit_ref` text, `unit_weight` mg required, `*dilution_fields("s_")`, `area` area
             field unit "µV·s", then `pct_lc` calculated with the A8_HPLC expression and
             `rounding {mode:"round", digits:1}`), but **rows = {"min":1,"max":30,"default":30}**
             (thirty units by default). Copy the `pct_lc` expression string verbatim from
             `a8_content_uniformity.py`.
          6. `_summary_group("units")` (reused verbatim — contains `_ACCEPTANCE_VALUE`).
        - criteria: `[sst_rsd_criterion(), <bracketing pooled-%RSD criterion>, *_cu_criteria("units")]`
          where the bracketing criterion is `{"key":"sst_bkt_rsd","label":"%RSD of pooled bracketing
          standards","target":"stats.rsd_bkt","operator":"lte","limit":2.0,"severity":"blocking",
          "limitText":"NMT 2.0 %"}`. `sst_rsd_criterion()` targets `stats.rsd_std` NMT 2.0;
          `_cu_criteria("units")` gives the AV criterion (target `summary.acceptance_value`,
          `lte`, limit **15.0**, blocking) and the unit-count advisory (`count(units.pct_lc)`,
          `gte`, limit **10**, advisory "NLT 10 units" — for 30 units this still holds).
        - Wrap in `SeedTemplate(code="TPL-A8-0004", name="Content Uniformity by HPLC — 30 Units
          (Stage 2)", archetype="A8", result_unit="AV", test_code="TST-CU-30U",
          test_name="CU-tablets-30units", test_type="Quantitative", definition=<the dict>)`.
          `test_name` MUST be EXACTLY `CU-tablets-30units`. Expose `TEMPLATES = [A8_CU_30U]`.
        - Module docstring MUST record: reuses A8_HPLC's AV logic + `_common` standard/replicate
          helpers + A12-0001's bracketing/pooled-%RSD pattern; and that k defaults to 2.0 for the
          30-unit stage.
      Files: `backend-v2/scripts/template_definitions/a8_cu_tablets_30units.py`.
      Verify: `python -c "from scripts.template_definitions.a8_cu_tablets_30units import TEMPLATES; print(len(TEMPLATES))"`
      run from `backend-v2` prints `1` with no import error.

- [ ] 3. Register the new module in `__init__.py` in A8 order.
      In `backend-v2/scripts/template_definitions/__init__.py` add
      `from scripts.template_definitions.a8_cu_tablets_30units import TEMPLATES as _A8_CU30`
      beside the other A8 import, and splice `*_A8_CU30` into `SEED_TEMPLATES` immediately after
      `*_A8` (keeping archetype order: after `*_A8`, before `*_A9_A10_A13`).
      Files: `backend-v2/scripts/template_definitions/__init__.py`.
      Verify: `python -c "from scripts.template_definitions import SEED_TEMPLATES; print([t.code for t in SEED_TEMPLATES if t.code=='TPL-A8-0004'])"`
      run from `backend-v2` prints `['TPL-A8-0004']`.

- [ ] 4. Validate the whole catalogue parses + dry-run-evaluates (seeder validate-only).
      No file change — this gates that the new definition is well-formed before writing tests/DB.
      Files: none.
      Verify: from `backend-v2`, `python -m scripts.seed_test_templates --validate-only`; exit
      code 0, and the output lists an `ok   TPL-A8-0004 [A8] ...` line.

- [ ] 5. Add the parity test `test_a8_0004_cu30_parity.py`.
      Create `backend-v2/tests/calculation/test_a8_0004_cu30_parity.py` following the pattern of
      `tests/calculation/test_a12_0003_ampho_parity.py` (import the definition, parse with
      `TemplateDefinition.parse`, evaluate with `WorksheetEvaluator`). Assert ALL of:
        1. Structure: `units` group rows `default == 30` and `max == 30`; `k_value` context field
           `default == 2.0`.
        2. AV nesting intact — two HAND-DERIVED cases evaluated through the template's
           `summary.acceptance_value`, choosing per-unit inputs that yield the target mean/sd:
           - a CENTRED case: mean in [98.5, 101.5] ⇒ AV == k·s == 2.0·s (first |M−X| term is 0).
           - an OFF-CENTRE LOW case: mean < 98.5 ⇒ AV == (98.5 − mean) + 2.0·s.
           Derive AV independently (not copied from a run) and assert equality to the summary AV
           for the same mean/sd, proving the upper-outer / lower-inner nesting is intact. (The AV
           uses `summary.mean_pct` rounded to 1 dp and `summary.sd_pct` rounded to 4 dp — derive
           the expected AV from those rounded values, matching `_summary_group`.)
        3. Pooled bracketing %RSD: feed `std_areas` areas plus `bkt_1`/`bkt_2` areas; assert
           `stats.rsd_bkt == rsd(pool(all those areas))`, hand-deriving the expected %RSD from the
           pooled set (mean, sample SD, SD/mean·100).
        4. Criteria present with correct limits via `TemplateDefinition.parse(...).criteria`:
           `sst_std_rsd` (target `stats.rsd_std`, lte 2.0, blocking), `sst_bkt_rsd` (target
           `stats.rsd_bkt`, lte 2.0, blocking), `acceptance_value` (target
           `summary.acceptance_value`, lte **15.0**, blocking), `unit_count` (target
           `count(units.pct_lc)`, gte **10**, advisory).
        5. (Recommended) An empty-evaluate returns no blocking failure and a blank reportable, to
           mirror the catalogue-wide invariant.
      Also add the new code to the catalogue parity coverage if required: note
      `test_seeded_template_parity.py::test_every_archetype_in_scope_is_seeded` asserts the
      archetype SET equals the existing fourteen names — adding another A8 template does NOT change
      the set, so that test still passes; `test_template_codes_are_unique` still passes because
      TPL-A8-0004 is new. No edit to `test_seeded_template_parity.py` is needed.
      Files: `backend-v2/tests/calculation/test_a8_0004_cu30_parity.py`.
      Verify: from `backend-v2`, `python -m pytest tests/calculation/test_a8_0004_cu30_parity.py -q`;
      all new tests pass.

- [ ] 6. Seed the template into the live DB and confirm byte-equal storage.
      Run the seeder against `lims.db` so TPL-A8-0004 is Active and TST-CU-30U "CU-tablets-30units"
      exists. Then confirm with a throwaway check script (deleted in step 8): exactly ONE new
      Active row with code TPL-A8-0004; its `test_id` points at a Test whose `name` is EXACTLY
      `CU-tablets-30units` and `code` is `TST-CU-30U`; the stored `definition` is canonical-JSON
      byte-equal to the module's `A8_CU_30U.definition` (compare `json.dumps(stored, sort_keys=True,
      separators=(',',':'))` against the same canonicalisation of the module dict — match the
      canonical form the codebase/engine uses; if the ORM stores dict==dict, assert equality of the
      parsed dicts too); and NO other template/test row changed (compare counts and the set of
      codes before vs after — only TPL-A8-0004 and test TST-CU-30U are added).
      Files: live `backend-v2/lims.db` only (gitignored); a throwaway verify script (removed in
      step 8).
      Verify: from `backend-v2`, `python -m scripts.seed_test_templates` exits 0 and logs
      `add  TPL-A8-0004 ...` plus `+ Test Master: TST-CU-30U — CU-tablets-30units`; the check
      script prints that the new row is Active, bound to the EXACT test name, definition byte-equal,
      and no other row disturbed.

- [ ] 7. Run the full calculation suite and confirm no NEW failures.
      Files: none.
      Verify: from `backend-v2`, `python -m pytest tests/calculation -q`; the SAME 5 pre-existing
      failures remain (3 A6B: `test_unit1_release_carryover`, `test_per_timepoint_summary`,
      `test_amount_remaining`; 2 worksheet_service: `test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`,
      `test_a_qa_correction_reopens_and_republishes_the_result`), the new parity test passes, and
      there are NO other new failures (expected summary: 5 failed, 799+ passed, the +1 being the
      new parity test module's cases).

- [ ] 8. Clean up throwaway artifacts.
      Delete any throwaway/verify scripts created during steps 6–7. Confirm the ONLY additions to
      source control are: the new module `a8_cu_tablets_30units.py`, the `__init__.py` edit, and
      the new parity test `test_a8_0004_cu30_parity.py`. The new DB rows (template + test) and the
      backup file live only in gitignored `lims.db` / backup and are not staged.
      Files: removes throwaway scripts (if any).
      Verify: `git status` from repo root `d:\RD-instance\GIT` shows only those three files changed
      under `backend-v2/scripts/template_definitions/` and `backend-v2/tests/calculation/`; `lims.db`
      and the backup are untracked/ignored and NOT staged.

- [ ] 9. Finalize: commit locally (do NOT push).
      Stage only `backend-v2/scripts/template_definitions/a8_cu_tablets_30units.py`,
      `backend-v2/scripts/template_definitions/__init__.py`, and
      `backend-v2/tests/calculation/test_a8_0004_cu30_parity.py`. Commit with a message describing
      the new 30-unit CU-by-HPLC template (reusing A8_HPLC AV logic + `_common` standard/replicate
      helpers + A12-0001 bracketing/pooled-%RSD pattern, k default 2.0), bound to Test
      "CU-tablets-30units", gold AV reproduced, seeded Active, DB definition byte-equal; and record
      the DB backup filename from step 1. Do NOT `git push`.
      Files: git commit (local only).
      Verify: `git log -1 --stat` from repo root shows the commit with exactly the three staged
      files; report the commit hash and the code used (**TPL-A8-0004**, test **TST-CU-30U** /
      "CU-tablets-30units"). `lims.db` stays gitignored and unstaged.

## Loop stop contract (for the reviewer that closes this task)

The implement/review loop stops ONLY when
`d:\RD-instance\GIT\backend-v2\.agents\tasks\a8-0004-cu-tablets-30units/review.json` has
jsonPath `verdict` == `APPROVED`, written by the semantic reviewer as the loop's last child.

## Assumptions / gaps noted

- `test_name` is fixed EXACTLY as `CU-tablets-30units` per the authoritative task; the human-facing
  template `name` is chosen as "Content Uniformity by HPLC — 30 Units (Stage 2)" (descriptive, not
  constrained by the task). If the reviewer prefers a different template `name`, it is cosmetic and
  does not affect any identifier, test binding, or arithmetic.
- "Byte-equal" is interpreted as canonical-JSON equality of the stored definition against the
  module definition using the same canonicalisation the engine/storage uses; the exact
  serializer must be matched when implementing step 6 (confirm how `TestTemplateModel.definition`
  is persisted — it is passed `item.definition` as a dict, so a dict-equality assertion plus a
  canonical-JSON string comparison both apply).
