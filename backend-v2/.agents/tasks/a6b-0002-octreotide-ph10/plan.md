# Implementation Plan — TPL-A6B-0002, Dissolution (Octreotide Acetate, pH-10, with replacement)

Source of truth: the APPROVED design at `.agents/tasks/a6b-0002-octreotide-ph10/design.md`
and the formula dump `_dumps/Dissolution sheet_Octreotide_PH 10.txt`. This plan
sequences that design faithfully; it does not re-decide the architecture.

All commands run from `d:\RD-instance\GIT\backend-v2` (run Python from there).

## Decisions taken in this plan (where the brief and design diverge, the brief wins)

- **New module, not an append to `a6_dissolution.py`.** The design's "Files to
  touch" says add the builders into `a6_dissolution.py`, but the authoritative
  user brief mandates a NEW module
  `scripts/template_definitions/a6b_octreotide_ph10.py` registered via
  `__init__.py`. The brief is authoritative, so the template lives in its own
  module. Everything else in the design (group map, expressions, gold values,
  single `sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)`,
  deliberately-omitted dead blocks) is followed verbatim.
- **Dedicated parity test file.** The brief mandates a new parity test at
  `tests/calculation/test_a6b_0002_octreotide_parity.py` (not an added class in
  the existing `test_seeded_template_parity.py`). Follow the brief.
- **`std_stats` group + explicit criterion target.** The standard-statistics
  group is named `std_stats` (per the group map), so the acceptance criterion
  MUST be written `sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)` — a
  bare `sst_rsd_criterion()` defaults to `stats.rsd_std` and would never
  evaluate. Likewise, if the `std_areas` table is given a footer, its `ref`s must
  point at `std_stats.*`, not the helper default `stats.*`; simplest is to build
  `std_areas` inline without the `stats`-defaulted footer, or pass the footer
  refs explicitly.

## Verified facts from exploration (so the implementer need not re-derive them)

- Expression engine (`src/domain/services/calculation/expression.py`) provides
  `mean`, `sd` (sample STDEV n-1, == Excel STDEV), `min`, `max`, `pool`,
  `number`, `coalesce`; supports list literals containing references
  (`sd(pool(weights.w_1hr, [mean_1hr]))`) and indexed refs
  (`weights.w_1hr[rowno - 1]`).
- `rowno` is 1-based (`evaluator.py`: `scope["rowno"] = float(row_index + 1)`),
  so per-unit weight lookup uses `[rowno - 1]`.
- Current test baseline for `tests/calculation`: **5 pre-existing failures** —
  `TestA6BDissolutionWithReplacement::{test_unit1_release_carryover,
  test_per_timepoint_summary, test_amount_remaining}` (A6B-0001) and
  `test_worksheet_service::{test_a_different_analyst_cannot_enter_results_on_an_assigned_trf,
  test_a_qa_correction_reopens_and_republishes_the_result}` — 780 passed.
- `TPL-A6B-0002` is free in `lims.db`; `TST-DISS-OCT-PH10` does not exist.
- `lims.db` is gitignored (`backend-v2/*.db`), so the seeded DB rows are not
  committed.
- Seeder `scripts/seed_test_templates.py` is additive/idempotent: validates all
  defs, `ensure_test` creates the Test if absent, inserts the template Active
  with `approved_by="seed"`, skips any code already present.

---

- [ ] 1. Create the new template module `scripts/template_definitions/a6b_octreotide_ph10.py`,
      mirroring `a6_dissolution.py`'s A6B-0001 structure and reusing `_common`
      helpers where they fit (`context_header` not required — see the design's
      context section; import `SeedTemplate` and `sst_rsd_criterion`). Model the
      design's units-as-rows / timepoints-as-separate-groups shape exactly:
      - Context fields (rows 2-15) per the design: `generic_name` (source
        `product.name`), `product_name`, `trf_no` (`trf.trf_number`), `ar_no`
        (`trf.ar_number`), `batch_no` (`trf.batch_number`), `stability_condition`,
        `test_performed`, `analysis_as_per`, `analysed_by` (`session.analyst`),
        `instrument_id`, `date_of_analysis` (`session.date`) — every one sourced
        OR `overridable` (no unfillable context box).
      - `standard` singleton: `potency`, `mw_base`, `mw_salt`, `weight_mg`,
        `dilution_1`, `volume_1`, `dilution_2`, and `conc_ppm` =
        `weight_mg / dilution_1 * volume_1 / dilution_2 * mw_base / mw_salt * potency / 100 * 1000`
        (gold J19 = 91.73466).
      - `std_areas` table (default 5) and `bkt` table (min 0, max 5, default 2).
      - `std_stats` singleton with `mean_std`, `sd_std`, `rsd_std` (= `sd_std*100/mean_std`),
        `mean_bkt`/`sd_bkt`/`rsd_bkt` over `pool(std_areas.area, bkt.area)` per the
        design's exact expressions.
      - `params` singleton (Volume mL/Apparatus/RPM/Temp/Media) — context/inputs,
        not in any formula.
      - `weights` table (6 rows) with `w_1hr`, `w_4hr`, `w_24hr`; `weight_stats`
        singleton with per-column Mean = `mean(weights.w_1hr)`, SD =
        `sd(pool(weights.w_1hr, [mean_1hr]))` (deliberately includes the mean
        cell, reproducing the sheet's `STDEV(F22:F28)`), %RSD = `sd_1hr*100/mean_1hr`;
        identical for `_4hr`/`_24hr`.
      - `prep` context/singleton: `pct_assay` (A32, default 4.12, number-guarded),
        `media_vol` (A35, default 10), `pipette_vol` (B35, default 1), `vf_vol`
        (C35, default 1), `withdraw_replace` (A37, default 1).
      - Three %Residue timepoint tables (`residue_1hr`, `residue_4hr`,
        `residue_24hr`, 6 rows each) with `area`, `residue` (the design's K-column
        chain, each reading its own weight column `weights.w_1hr[rowno-1]` /
        `w_4hr` / `w_24hr`), and `mean`/`min_v`/`max_v`/`rsd` aggregates
        (`rsd = sd(...)*100/mean`).
      - Three %Release-from-assay tables (`release_1hr`, `release_4hr`,
        `release_24hr`, 6 rows each) with input `residue_in`, `rel =
        (number(pct_assay) - residue_in) / number(pct_assay) * 100`, and the four
        aggregates.
      - Do NOT model the rows 58-69 `#VALUE!` block or the L/M carry-over columns
        (design "Deliberately NOT reproduced").
      - `resultRef = "residue_24hr.mean"`; `criteria =
        [sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)]`.
      - Define `A6B_OCT = SeedTemplate(code="TPL-A6B-0002", name="Dissolution
        (Octreotide Acetate, pH 10)", archetype="A6b", result_unit="%",
        test_code="TST-DISS-OCT-PH10", test_name="Dissolution-Octreolide-pH-10"
        (EXACT, keep the "Octreolide" spelling), test_type="Quantitative",
        definition=...)` and `TEMPLATES = [A6B_OCT]`.
      Files: `scripts/template_definitions/a6b_octreotide_ph10.py`
      Verify: `python -c "from scripts.template_definitions.a6b_octreotide_ph10 import TEMPLATES; from src.domain.services.calculation.template_schema import TemplateDefinition; from src.domain.services.calculation.evaluator import WorksheetEvaluator; d=TemplateDefinition.parse(TEMPLATES[0].definition); WorksheetEvaluator(d).evaluate({}, {}); print('parsed+empty-eval ok', TEMPLATES[0].code)"` exits 0 and prints the ok line.

- [ ] 2. Register the new module in `scripts/template_definitions/__init__.py`:
      add `from scripts.template_definitions.a6b_octreotide_ph10 import TEMPLATES as _A6B_OCT`
      near the other A6 imports, and splice `*_A6B_OCT` into `SEED_TEMPLATES` in
      A6 order (immediately after `*_A6` / the A6b family, before `*_A6D`).
      Files: `scripts/template_definitions/__init__.py`
      Verify: `python -c "from scripts.template_definitions import SEED_TEMPLATES; codes=[t.code for t in SEED_TEMPLATES]; assert 'TPL-A6B-0002' in codes; assert codes.count('TPL-A6B-0002')==1; print('registered once at index', codes.index('TPL-A6B-0002'))"` exits 0.

- [ ] 3. Add the parity test `tests/calculation/test_a6b_0002_octreotide_parity.py`.
      Build the definition via `TemplateDefinition.parse(TEMPLATES[0].definition)`
      and a `WorksheetEvaluator`, following the fixture/assertion style of
      `TestA6BDissolutionWithReplacement` in
      `tests/calculation/test_seeded_template_parity.py` (use `result.values[...]`
      for singletons and `result.row_value(group, idx, field)` for table rows).
      Load the gold fixture = the dump's entered values: standard inputs
      (potency 89.41, mw 1/1, weight 25.65, dilution_1 25, volume_1 5,
      dilution_2 50); `std_areas` [3025190, 3032957, 3039697, 3038818, 3038602];
      `bkt` [3037074, 3035247]; weights w_1hr [23.59, 23.9], w_4hr [25.13, 24.84],
      w_24hr [25.34, 23.61] (units 1-2 only, rest blank); prep pct_assay 4.12,
      media_vol 10, pipette_vol 1, vf_vol 1, withdraw_replace 1; residue areas
      1hr [3152088, 3270742], 4hr [2351327, 2326691], 24hr [1622756, 1437001];
      release residue_in 1hr [4.04, 4.14], 4hr [2.83, 2.83], 24hr [1.94, 1.84].
      Assert EVERY gold value from the design's "Full gold-value set" table to the
      sheet's shown precision (use `pytest.approx` with tolerances consistent with
      the design, e.g. `abs=1e-4` relative where the design states "matched to
      <=1e-4"): J19; B27/B29, D27/D29; the three weight-stat Mean/SD/%RSD triples;
      K40/K41 + residue_1hr Mean/Min/Max/RSD; K46 + residue_4hr Mean/RSD; K52 +
      residue_24hr Mean/RSD; C70/C71 + release_1hr Mean/Min/Max/RSD; C76 +
      release_4hr Mean/RSD; C82/C83 + release_24hr Mean/RSD. Also assert the
      acceptance criterion exists and is the %RSD SST (e.g. parse the definition
      and assert exactly one criterion with `target == "std_stats.rsd_std"`,
      `operator == "lte"`, `limit == 2.0`), and that `resultRef` resolves
      (`residue_24hr.mean`). Each expected number must carry a comment deriving it
      from the sheet formula, matching the repo convention.
      Files: `tests/calculation/test_a6b_0002_octreotide_parity.py`
      Verify: `python -m pytest tests/calculation/test_a6b_0002_octreotide_parity.py -q` — all new tests pass, 0 failures.

- [ ] 4. Validate the whole seed catalogue through the seeder's dry run and
      confirm the new definition parses and evaluates on both empty and the gold
      fixture with no error (the gold-fixture eval is already exercised by step 3;
      this step is the catalogue-level gate the seeder applies before writing).
      Files: none (validation only)
      Verify: `python -m scripts.seed_test_templates --validate-only` exits 0 and
      its output lists `ok   TPL-A6B-0002 [A6b] ...` among the validated
      definitions (no `INVALID DEFINITIONS` section).

- [ ] 5. Seed into the live DB so `TPL-A6B-0002` is Active and
      `TST-DISS-OCT-PH10` / `Dissolution-Octreolide-pH-10` exists. Run the
      additive seeder (default Active). Then confirm: exactly one row with code
      `TPL-A6B-0002`, status `Active`, bound (`test_id`) to a `tests` row whose
      `code = 'TST-DISS-OCT-PH10'` and `name = 'Dissolution-Octreolide-pH-10'`
      EXACT; the stored `definition` JSON is canonical-JSON byte-equal to the
      module's `TEMPLATES[0].definition`; and all other template rows are
      undisturbed (same codes/count as before, +1).
      Files: `lims.db` (gitignored; not committed)
      Verify: `python -m scripts.seed_test_templates` exits 0 and logs
      `+ Test Master: TST-DISS-OCT-PH10` and `add  TPL-A6B-0002`; then a
      verification snippet (temporary, deleted in step 7) loads the row and
      asserts: one `TPL-A6B-0002` Active row, its test name is EXACT, and
      `json.dumps(stored, sort_keys=True, separators=(",",":")) ==
      json.dumps(module_def, sort_keys=True, separators=(",",":"))` — prints OK.

- [ ] 6. Confirm the full calculation suite shows the SAME 5 known pre-existing
      failures plus the new parity test passing, and A6B-0001 behavior unchanged.
      Files: none (verification only)
      Verify: `python -m pytest tests/calculation -q` — result is the prior 780
      passed plus the new parity tests passing, with EXACTLY the same 5 failures
      as the baseline (3 `TestA6BDissolutionWithReplacement` A6B-0001 tests +
      2 `test_worksheet_service` tests) and NO other new failures. Confirm no
      A6B-0001 assertion changed (those 3 remain the same known failures, not new
      ones).

- [ ] 7. Delete every throwaway script/snippet created during steps 1-6 (the
      step-5 DB-verification snippet and any ad-hoc eval scripts), so the only
      additions are the new module, its `__init__.py` registration, the new parity
      test, and the new DB rows. Confirm `git status` shows only
      `scripts/template_definitions/a6b_octreotide_ph10.py`,
      `scripts/template_definitions/__init__.py`, and
      `tests/calculation/test_a6b_0002_octreotide_parity.py` as changes (plus the
      gitignored `lims.db`, which will not appear).
      Files: remove any temp files under `backend-v2/`
      Verify: `git status --porcelain` (run from repo root or backend-v2) lists
      only the three intended files; no stray `_tmp_*`/scratch files remain.

- [ ] 8. Commit locally (do NOT push). Stage exactly the module, the `__init__.py`
      registration, and the parity test (lims.db is gitignored and must not be
      forced in). Use a concise conventional-commit message, e.g.
      `feat(templates): add TPL-A6B-0002 Octreotide pH-10 dissolution (Dissolution-Octreolide-pH-10)`.
      Report the commit hash.
      Files: git index / commit (no file edits)
      Verify: `git add backend-v2/scripts/template_definitions/a6b_octreotide_ph10.py backend-v2/scripts/template_definitions/__init__.py backend-v2/tests/calculation/test_a6b_0002_octreotide_parity.py && git commit -m "feat(templates): add TPL-A6B-0002 Octreotide pH-10 dissolution"` succeeds; `git log -1 --stat` shows exactly those three files and the hash; `git status` confirms nothing was pushed (branch ahead by 1).

## Gaps / assumptions noted

- The design's "Files to touch" and the mandated parity-file location differ from
  the authoritative brief; this plan follows the brief (new standalone module +
  dedicated parity test file) and records the divergence above. If a reviewer
  prefers the design's in-`a6_dissolution.py` placement, that is a one-location
  change, but it would contradict the user's explicit instruction, so the brief
  is used.
- Exact field `key`/`label` names for the new module are left to the implementer
  so long as the design's expressions and group keys (`std_stats`, `weights`,
  `weight_stats`, `residue_1hr/4hr/24hr`, `release_1hr/4hr/24hr`, `standard`,
  `prep`/`params`) and the gold values hold; the parity test pins the gold values
  regardless of cosmetic naming.
