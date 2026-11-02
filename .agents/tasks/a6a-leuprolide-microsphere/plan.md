# Implementation Plan — Dissolution-Leuprolide-microsphere (TPL-A6A-0005, archetype A6a)

Plan built from the approved design (`design.md`) and trace oracle (`trace.md`).
It sequences the work faithfully without re-deciding the architecture; every
decision (code = `TPL-A6A-0005`, carry form = non-recursive `sum(prior.kfrac_u)`,
group = `sequence`, test_code = `TST-DISS-LEUP-MS`) is already fixed by the design
and is reproduced, not re-opened.

## Context discovered during exploration (grounding for the implementer)

- **Chosen A6A code: `TPL-A6A-0005`** (next free; -0001..-0004 all exist as Active
  DB rows). TPL-A6A-0002 (the base the user named) is a **DB-only** row, so the
  deliverable is a brand-new module, not an edit to an existing module.
- **Pattern module to mirror:** `backend-v2/scripts/template_definitions/a6b_octreotide_ph10.py`
  (context header, standard chain, `std_areas`/`bkt`/`std_stats` split, pellet
  `weights`/`weight_stats` with the STDEV-includes-mean quirk, per-block
  Mean/Min/Max/RSD companion singletons).
- **Carry-pattern precedent (pinned):** `backend-v2/tests/calculation/test_dissolution_a6a_release.py`
  pins TPL-A6A-0004's `sequence` group with the exact non-recursive form the design
  adopts: three contiguous field loops (`uncorrected_N` → `correction_N` →
  `unit_N = round(uncorrected_N + sum(prior.correction_N), 0)`), `rowno` 1-based,
  `prior.*` lists, `sum(empty)=0`. Our module uses `jassay_u` → `kfrac_u` →
  `unit_u = jassay_u + sum(prior.kfrac_u)` (no rounding, full precision).
- **Helpers:** `scripts/template_definitions/_common.py` provides `SeedTemplate`
  (dataclass: code/name/archetype/result_unit/test_code/test_name/test_type/definition)
  and `sst_rsd_criterion(target=..., limit=...)`. The design's groups are renamed
  (`std_stats`, not `stats`), so the criterion MUST pass `target="std_stats.rsd_std"`
  explicitly — a bare call defaults to `stats.rsd_std` and never evaluates.
- **Registration:** `scripts/template_definitions/__init__.py` imports each module's
  `TEMPLATES` and splices them into `SEED_TEMPLATES`, ordered by archetype. Add the
  new import and splice `*_A6A_LEUP` immediately after `*_A6` and before `*_A6B_OCT`.
- **Seeder:** `python -m scripts.seed_test_templates` — additive and idempotent
  (skips existing codes, creates a missing Test via `ensure_test` by `test_code`).
  `--validate-only` parses every definition and dry-runs `WorksheetEvaluator(parsed).evaluate({}, {})`,
  returning exit 0 on success. Default seed stamps `status=Active`, `approved_by="seed"`.
- **Live DB:** `backend-v2/lims.db`. Backup already taken in the trace step
  (`lims.db.bak-leuprolide-20261024-220422`, 1,433,600 bytes verified).
- **Build/test commands (run from `backend-v2/`):**
  - Validate: `python -m scripts.seed_test_templates --validate-only`
  - Targeted parity test: `python -m pytest tests/calculation/test_a6a_0005_leuprolide_parity.py -q`
  - Full calculation gate: `python -m pytest tests/calculation -q`
- **Baseline test state (captured now, must be preserved):** `python -m pytest tests/calculation -q`
  = **5 failed, 826 passed**. The 5 pre-existing unrelated failures are:
  `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_unit1_release_carryover`,
  `::test_per_timepoint_summary`, `::test_amount_remaining`, and
  `test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`,
  `::test_a_qa_correction_reopens_and_republishes_the_result`. These must stay the
  SAME; the new test must pass; no other new failures.
- **No AGENTS.md / CONTRIBUTING / `.kiro/steering` exist** in the repo; `pyproject.toml`
  sets `testpaths=["tests"]`, `asyncio_mode="auto"`, and silences only the structural
  `cannot collect test class` warning.

## Scope guard

Touch only: the new module, the two registration lines in `__init__.py`, the new
parity test, and the DB rows (via the seeder). Do NOT touch anything under
`backend-v2/src` or `frontend-react` — other workflows own those. Do NOT disturb
`TPL-A6A-0002` or any resource-management row.

---

# Implementation Plan

- [ ] 1. Create the new template module `a6a_leuprolide_microsphere.py` with the full definition and the `SeedTemplate` tail.
      Build it by mirroring `a6b_octreotide_ph10.py` structure and adapting to the Leuprolide
      constants. Include ALL 10 groups from the design's group map, in sheet order:
      (1) `_context()` list — 11 fields B5..B15 per design §1, each sourced or overridable;
      (2) `standard` singleton rows 17-19 with inputs (name/potency/mw_base/mw_salt/weight_mg/
      dilution_1/volume_1/dilution_2, defaults 97.87/1/1/20.11/50/5/25) and calculated `conc_ppm`
      = `weight_mg / dilution_1 * volume_1 / dilution_2 * mw_base / mw_salt * potency / 100 * 1000`
      (no rounding);
      (3) `std_areas` table (1 `area` field, default 5/max 6, footer → `std_stats.*_std`);
      (4) `bkt` table (1 `area` field, default 5, footer → `std_stats.*_bkt`);
      (5) `std_stats` singleton — `mean_std=mean(std_areas.area)`, `sd_std=sd(std_areas.area)`,
      `rsd_std=sd(std_areas.area)*100/mean_std`, and pooled `mean_bkt=mean(pool(std_areas.area, bkt.area))`,
      `sd_bkt=sd(pool(std_areas.area, bkt.area))`, `rsd_bkt=sd(pool(std_areas.area, bkt.area))*100/mean_bkt`;
      (6) `params` singleton — `volume_ml`(50), `apparatus`("Bottle Rotating"), `rpm`(6),
      `temperature`("50"), `media`(multiline, overridable, "0.5% W/V PVA IN WATER pH 5.50");
      (7) `weights` table — `unit_label`(text) + `weight`, default 6/max 6/`labelFrom`:"unit_label",
      footer → `weight_stats.*`;
      (8) `weight_stats` singleton — `mean_wt=mean(weights.weight)`, `sd_wt=sd(pool(weights.weight, [mean_wt]))`
      (STDEV-includes-mean quirk, deliberate), `rsd_wt=sd_wt*100/mean_wt`;
      (9) `prep` singleton — `avg_weight`(100), `label_claim`(9.8), calculated `media_vol`=`params.volume_ml`
      (preserves the sheet's A35=I22 link), `pipette_vol`(1), `vf_vol`(1), `withdraw_replace`(1);
      (10) `timepoints_release` **sequence** (see item 2).
      Set `"resultRef": "timepoints_release.mean"` and
      `"criteria": [sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)]`.
      Tail: `A6A_LEUP = SeedTemplate(code="TPL-A6A-0005", name="Dissolution-Leuprolide-microsphere",
      archetype="A6a", result_unit="%", test_code="TST-DISS-LEUP-MS",
      test_name="Dissolution-Leuprolide-microsphere", test_type="Quantitative",
      definition=A6A_LEUP_DEFINITION)` and `TEMPLATES = [A6A_LEUP]`.
      Module docstring MUST record the archetype-vs-"without replacement"-name discrepancy
      (archetype stays A6a to match the base family; the sheet actually carries a live
      cumulative replacement add-back) so a future reader does not "correct" the carry away.
      Files: `backend-v2/scripts/template_definitions/a6a_leuprolide_microsphere.py`
      Verify: `python -c "from scripts.template_definitions.a6a_leuprolide_microsphere import TEMPLATES; print(TEMPLATES[0].code)"`
      run from `backend-v2/` prints `TPL-A6A-0005` with no import error. (Full engine
      validation is item 4.)

- [ ] 2. Build the `timepoints_release` sequence group inside the module (part of item 1's file; called out separately for clarity).
      `kind: "sequence"`, `rows = {"min": 1, "max": 25, "default": 7, "labelFrom": "time_hr"}`
      (25 blocks total per trace §4; default 7 real labeled timepoints 1/24/48/96/120/144/168 Hr).
      Fields in THREE contiguous loops over units 1..6 (matching the pinned TPL-A6A-0004 order),
      preceded by `time_hr` (input text, defaulting the 7 labels then blank) and `area_1..area_6`
      (`area` inputs): loop A `jassay_1..6` (calculated, hidden) using the per-unit chain
      `area_{u} / std_stats.mean_std * standard.weight_mg / standard.dilution_1 *
      standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol *
      prep.media_vol / weights.weight[{u} - 1] * standard.potency * standard.mw_base /
      standard.mw_salt * prep.avg_weight / prep.label_claim` (potency PLAIN, A35 numerator,
      divide by unit's own pellet weight by 0-based index `[u-1]`); loop B `kfrac_1..6`
      (calculated, hidden) = `jassay_{u} * prep.withdraw_replace / prep.media_vol`; loop C
      `unit_1..6` (calculated, reported) = `jassay_{u} + sum(prior.kfrac_{u})`. Then per-block
      aggregates over `U=[unit_1..unit_6]`: `mean=mean(U)`, `min_val=min(U)`, `max_val=max(U)`,
      `rsd=sd(U)*100/mean`. No `rounding` key on any calculated field (full precision).
      Build each expression once as a Python f-string helper keyed by `u` (like
      `_residue_expression` in the Octreotide module) and reference `jassay_u`/`kfrac_u` by key
      so real dependency edges exist (this is what makes the non-recursive carry order-safe).
      Files: `backend-v2/scripts/template_definitions/a6a_leuprolide_microsphere.py`
      Verify: covered by item 1's import check and item 4's engine dry-run; carry correctness is
      pinned by the parity test in item 3.

- [ ] 3. Register the new module in the seed index.
      Add `from scripts.template_definitions.a6a_leuprolide_microsphere import TEMPLATES as _A6A_LEUP`
      with the other imports, and splice `*_A6A_LEUP` into `SEED_TEMPLATES` immediately after
      `*_A6` and before `*_A6B_OCT` (keeps the A6 family contiguous / log ordered by archetype).
      Files: `backend-v2/scripts/template_definitions/__init__.py`
      Verify: `python -c "from scripts.template_definitions import SEED_TEMPLATES; print([t.code for t in SEED_TEMPLATES if t.code=='TPL-A6A-0005'])"`
      run from `backend-v2/` prints `['TPL-A6A-0005']` exactly once.

- [ ] 4. Run engine validation / dry-run on the full catalogue including the new template.
      This parses the new definition and dry-runs `WorksheetEvaluator(parsed).evaluate({}, {})`
      (empty-context evaluation) alongside every existing template, catching unresolved refs,
      cycles, or bad field keys before any DB write.
      Files: none (runs items 1-3's output).
      Verify: `python -m scripts.seed_test_templates --validate-only` run from `backend-v2/`
      exits 0 and its log line for `TPL-A6A-0005` shows `ok TPL-A6A-0005 [A6a] ...` with no
      INVALID DEFINITIONS section.

- [ ] 5. Write the parity test asserting every gold value from the trace/design to the sheet's rounding.
      Create the test modeled on `tests/calculation/test_dissolution_a6a_release.py`: import the
      module's `A6A_LEUP_DEFINITION` (or `TEMPLATES[0].definition`), `TemplateDefinition.parse` it,
      build a `group_values` fixture of the sheet inputs (standard row 17-19 values; `std_areas`
      = [1108135,1107954,1107711,1107762,1109456]; `bkt` = [1101413,1101192,1096506,1094608,1092402];
      `weights` = 3 filled [49.17,50.56,49.77] + blanks; `prep` defaults; `timepoints_release` rows
      for 1/24/48 Hr with the trace §5 `area_u` values — B40=203438/B41=231282/B42=174411,
      B46=681560, B52=1013055), and `WorksheetEvaluator(parsed).evaluate(ctx, group_values)`.
      Assert (full precision, `pytest.approx`): `standard.conc_ppm`≈78.726628; `std_stats.mean_std`
      ≈1108203.6, `sd_std`≈719.9265934801964, `rsd_std`≈0.06496338700579897, `mean_bkt`≈1102713.9,
      `sd_bkt`≈6388.745720231615, `rsd_bkt`≈0.5793656650407342; `weight_stats.mean_wt`≈49.833333333333336,
      `sd_wt`≈0.569229498728081, `rsd_wt`≈1.1422665526316007; row0 `unit_1`(C40)≈14.996084937889453,
      `unit_2`(C41)≈16.579857409503386, `unit_3`(C42)≈12.701419313269414, block `mean`≈14.759120553554084,
      `min_val`≈12.701419313269414, `max_val`≈16.579857409503386, `rsd`≈13.212490048191508;
      row1 (24 Hr) `unit_1`(C46)≈50.53995379830622, `unit_2`(C47)≈54.93604802433009,
      `unit_3`(C48)≈43.16740746631347; row2 (48 Hr) `unit_1`(C52)≈75.98034256289799 (the two
      carry-critical assertions that fail loudly if the chain collapses to 0). Also assert the
      SST criterion exists: `std_stats.rsd_std` appears as a `blocking` criterion with
      `operator=lte`, `limit=2.0` in `parsed.criteria`.
      Files: `backend-v2/tests/calculation/test_a6a_0005_leuprolide_parity.py`
      Verify: `python -m pytest tests/calculation/test_a6a_0005_leuprolide_parity.py -q` run from
      `backend-v2/` — all assertions pass.

- [ ] 6. Run the full calculation test gate and confirm no regressions.
      Files: none.
      Verify: `python -m pytest tests/calculation -q` run from `backend-v2/` reports the SAME 5
      pre-existing failures named in the context section (3 A6B-with-replacement + 2 worksheet-service),
      the new `test_a6a_0005_leuprolide_parity.py` passing, and NO other new failures. Expected
      summary: `6 failed, N passed`? — NO: the new test adds to the passed count, so the count of
      FAILED tests must remain exactly the 5 named ones (new test passes). If any additional test
      fails, stop and fix the module before proceeding.

- [ ] 7. Seed the new template into the live DB additively.
      Run the additive seeder against `backend-v2/lims.db`. It must create exactly one new Active
      `TPL-A6A-0005` row (v1, archetype A6a, result_unit `%`) bound to a newly created Test
      `TST-DISS-LEUP-MS` / `Dissolution-Leuprolide-microsphere` (type Quantitative), skipping all
      existing codes. The DB backup already exists from the trace step; do not re-back-up unless
      missing.
      Files: writes rows into `backend-v2/lims.db` (no source files changed).
      Verify: `python -m scripts.seed_test_templates` run from `backend-v2/` prints
      `add TPL-A6A-0005 [A6a] Dissolution-Leuprolide-microsphere -> TST-DISS-LEUP-MS` and
      `+ Test Master: TST-DISS-LEUP-MS — Dissolution-Leuprolide-microsphere`, and every other
      template line reads `skip ... already present`. Re-run once more and confirm it now prints
      `skip TPL-A6A-0005 — already present` (idempotency).

- [ ] 8. Verify the seeded row integrity and non-disturbance of other rows.
      Confirm: (a) exactly ONE Active row with name `Dissolution-Leuprolide-microsphere` and code
      `TPL-A6A-0005`, bound to the Test whose name is exactly `Dissolution-Leuprolide-microsphere`;
      (b) the stored `definition` canonical JSON is byte-equal to the module's `A6A_LEUP_DEFINITION`
      (serialize both with `json.dumps(..., sort_keys=True)` and compare); (c) `TPL-A6A-0002`
      (id 22, Test `Dissolution`/`TST-DISS-QC`) and all resource-management rows are unchanged.
      Files: none (read-only DB inspection; a throwaway inspection snippet is permitted but must be
      deleted in item 9).
      Verify: a short read-only query over `test_templates` / `tests` confirms the single new
      Active row and the byte-equal definition, and shows `TPL-A6A-0002` untouched (same version,
      status, test binding as before the seed).

- [ ] 9. Clean up and final gate.
      Delete any throwaway inspection/verification scripts created during items 7-8. Confirm the
      only added/changed artifacts are: the new module, the two registration lines in `__init__.py`,
      the new parity test, and the DB rows. Re-run the full calculation gate one last time to
      confirm the final state is green against the baseline.
      Files: remove any temporary `*.py` helpers created for inspection.
      Verify: `git status` under `backend-v2/` shows only `scripts/template_definitions/a6a_leuprolide_microsphere.py`
      (new), `scripts/template_definitions/__init__.py` (modified), `tests/calculation/test_a6a_0005_leuprolide_parity.py`
      (new), and `lims.db` (modified) — no stray scripts; and `python -m pytest tests/calculation -q`
      shows the same 5 pre-existing failures plus the new test passing.
