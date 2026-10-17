# Implementation Plan — Bupivacaine Lipid Content & Drug-to-Lipid Ratio template

## Goal (authoritative)

Add exactly ONE brand-new declarative calculation template that reproduces the
two-sheet Bupivacaine workbook
`d:\RD-instance\GIT\Test types\Bupivacaine Lipid & Drug to lipid Ratio.xlsx`
(sheets `'Lipid '` and `'Drug to Lipid ratio Auto Calc'`) — every table and
formula — verified against the sheet's stored values. Author a template module
under `backend-v2/scripts/template_definitions/`, wire it into `SEED_TEMPLATES`,
and seed it into the DB. Backend/data only; no frontend changes. Do NOT modify or
renumber any existing template or Test. One new Test Master entry may be created.

This plan does NOT decompose into separable features: the deliverable is a single
template module + a single seed entry + one verification pass over one workbook.
It is implemented as one coherent unit by the existing implement-and-review loop.

---

## Investigation summary (already completed by the planner — do not re-derive)

Files read in full: the engine (`template_schema.py`, `evaluator.py`,
`expression.py`); the seeder (`seed_test_templates.py`); the package aggregator
(`template_definitions/__init__.py`); the shared builders (`_common.py`); and the
closest existing patterns (`a2_lyso_content.py`, `a2_lyso_content_mgvial.py`,
`a2_a3_content.py`, `a12_derived_rollups.py`). The workbook was dumped to
`d:\RD-instance\GIT\_dumps\Bupivacaine Lipid _ Drug to lipid Ratio.txt` with every
cell formula; all gold values below were reproduced by a scratch calculation
before this plan was written.

### Engine facts that constrain the design

- `WorksheetEvaluator(TemplateDefinition.parse(defn)).evaluate(context_values, group_values)`
  returns a `WorksheetResult` with `.rows[group_key]` (list of row dicts) and
  `.values["group.field"]` (singletons/context scalars) and `.reportable_result`.
- Group kinds: `singleton` (1 row), `table` (N rows), `sequence` (prev/prior
  access). Field kinds: `context` (overridable/source), `input`, `area`,
  `calculated` (needs `expression`).
- Scoping: a multi-row group exposes each field as a **column series** —
  `std_areas.tri_area` is the whole column, usable in `mean(...)`/`sum(...)`.
  `group.col[rowno-1]` reads a specific row. Context + singleton fields are in
  scope unqualified inside every row.
- `pool(a, b, ...)` flattens ranges and drops blanks — the bracketing pattern.
- Blank semantics mirror Excel `IFERROR(...,"")`: division by zero and missing
  inputs yield `EMPTY`; `mean`/`sd`/`rsd` skip blanks; `sum` of empty is 0.
- `sd`/`rsd` need >= 2 numeric values or they return `EMPTY` (matches STDEV).
- `resultRef` must be `group.field`; for a multi-row group the reportable is the
  **last non-blank** value down the rows.
- Rounding is applied to a calculated field's own result and the **rounded value
  is what downstream fields see** — so only round where the sheet rounds.
- Non-numeric context used in arithmetic must be wrapped in `number(...)`.
  The per-compound numeric inputs here are entered `input` fields, so no wrapping
  is needed inside group formulas.
- The seeder validates (parse + dry-run `evaluate({}, {})`) every definition
  before writing, **skips** any `code` already present, and creates a missing
  Test Master entry via `ensure_test`. `--validate-only` parses without writing.

---

## Design decisions (fixed here; restate as module-level comments)

### (a) ONE template, two sheets modelled as sections

The workbook produces ONE reportable per batch (Drug/Lipid Ratio) that depends on
the Lipid sheet's `%Mean` per compound. Sheet 2 is pure arithmetic over sheet 1's
outputs (`H18 = 'Lipid '!O43`), so both sheets become groups of one template. The
Drug-to-Lipid group reads the Lipid sample group's `%Mean` directly rather than
re-entering it, eliminating the manual cross-sheet transcription the existing
`TPL-A12-0002` had to tolerate.

This template is DISTINCT from the existing `TPL-A12-0002 "Drug-to-Lipid Ratio"`,
which models the ratio as a carried-over roll-up with the lipid `%Mean` and drug
`%Assay` typed in by hand and performs NO HPLC lipid-content calculation. Here the
lipid content is computed from first principles (standard, replicates, pooled
bracketing, per-compound assay) and the ratio falls out of it. Do NOT touch
`a12_derived_rollups.py` or `TPL-A12-0002`.

### (b) Per-compound layout: compounds-as-fixed-COLUMNS (mirror a2_lyso_content)

**Decision: lay the 4 lipid compounds out as fixed columns/scalars, NOT as table
rows.** Rationale, grounded in the sheet formulas:

- Sheet `N39` (Tricaprylin %Assay) =
  `M39/$B$31 * B$18/$C$18 * $D$18/$E$18 * $F$18/$G$18 * J39/I39 * L39/K39 * $H$18/G39 * $I$18/$J$18 * H39`.
  Each compound's assay divides by **that compound's own replicate-mean column**
  (`$B$31`/`$C$31`/`$D$31`/`$E$31`) and multiplies by **that compound's own
  standard-detail row** (`B18..J18` for Tricaprylin, `B19..J19` for DPPG, etc.).
- If compounds were table rows, a DPPG sample row would need to reach "the DPPG
  column mean" and "the DPPG standard row" by aligned row index — fragile, and it
  makes the per-compound std-mean denominator reference awkward exactly as the
  task warned. The fixed-column layout keeps every one of those cross-references a
  plain scalar (`stats.mean_std_tri`, `standard.tri_weight`, ...), which is how
  `a2_lyso_content.py` already handles its two analytes successfully.
- So: standard details are a **singleton** of per-compound scalar fields; the
  replicate-injection table has **4 area columns** (one per compound); the
  bracketing table has **4 area columns**; statistics are a **singleton** of
  per-compound mean/sd/rsd (replicate) and pooled mean/sd/rsd (bracketing); the
  Lipid sample section is a **table of batches**, each batch row carrying the 4
  compounds' injection-1 and injection-2 areas and the 4 per-compound `%Assay` and
  `%Mean` columns; the Drug-to-Lipid section is a **table of batches** carrying
  the 4 per-compound `mg/mL(Lipid)` plus the sum and ratio.

The visual per-row-per-compound shape of the sheet's Sample Details is a
presentation detail; the arithmetic is per-compound-column and that is what the
engine reproduces faithfully with least duplication.

### (c) resultRef

`resultRef = "drug_lipid.ratio"` — the Drug/Lipid Ratio. The Drug-to-Lipid group
is a table (one row per batch); the engine returns the **last non-blank** ratio,
which is the correct "reportable" semantics for a multi-batch sheet. Document that
each batch row also exposes its own ratio for display.

### (d) Metadata

- **Archetype / code:** use archetype **A2** (multi-analyte HPLC content), next
  free code **`TPL-A2-0004`**. Justification: the dominant, novel work in this
  template is a multi-analyte (4-lipid) HPLC content assay with weighed standard,
  replicate + pooled-bracketing suitability, and per-compound assay — exactly the
  A2 family (`TPL-A2-0001..0003` are all multi-analyte HPLC content). A12
  "derived roll-ups" is the WRONG home: A12's defining trait is that its inputs
  are carried from *other tests* with no injections on the worksheet; this
  template computes the lipid content from its own injections. The Drug-to-Lipid
  ratio is a downstream arithmetic section, not the archetype's identity. Existing
  A2 codes confirmed in use: `TPL-A2-0001`, `TPL-A2-0002`, `TPL-A2-0003` → next
  free is `TPL-A2-0004`.
- **name:** `"Bupivacaine Lipid Content & Drug-to-Lipid Ratio"`.
- **result_unit:** `None` (unitless). The reportable is a ratio of two mg/mL
  quantities; the sheet shows no unit and `TPL-A12-0002` already uses `None` for
  the same ratio. (`"ratio"` is acceptable but `None` reads cleaner and matches
  precedent.)
- **Test Master binding:** new Test, created via `ensure_test` if absent.
  `test_code = "TST-LIPID-RATIO"`, `test_name = "Lipid Content & Drug-to-Lipid
  Ratio by HPLC"`, `test_type = "Quantitative"`. These match existing conventions
  (`TST-LYSO`, `TST-DLR`, `TST-CONT`: uppercase hyphenated code, descriptive name,
  `Quantitative` type). Do not reuse `TST-DLR` — that Test is bound to the
  carried-over `TPL-A12-0002` and this is a different method.
- Seed **Active** with `approved_by="seed"` (the seeder default).

### (e) SST / acceptance criteria — decision and justification

The sheet computes `%RSD` for the standard replicate injections per compound
(row 33) and `%RSD` for the pooled replicate+bracketing per compound (row 33 of
the BKT block) but prints **no numeric limit text**. Following the house
convention (`a2_lyso_content.py` uses NMT 2.0 % per compound via
`sst_rsd_criterion`-shaped entries), add **eight blocking criteria**: replicate
`%RSD` NMT 2.0 % and pooled-bracketing `%RSD` NMT 2.0 %, for each of the 4
compounds. This mirrors the closest precedent exactly. **Documented choice:**
per-compound (not overall) because the sheet computes RSD per compound column;
limit 2.0 % because that is the established NMT in every sibling HPLC template and
the sheet states none. Note in the module comment that if the lab later supplies a
different printed limit, only the `limit`/`limitText` change.

---

## Gold verification values (acceptance gates on these; reproduced by the planner)

Standard Conc (ppm), `K = B/C*D/E*F/G*H/100*I/J*1000`:
- Tricaprylin = **118.92**
- DPPG (Na)   = **54.0343** (54.03431768633169)
- Cholesterol = **285.1**
- DEPC        = **489.2544** (489.25440000000003)

Standard replicate means (AVERAGE of 6 injections):
- Tricaprylin = **8691453.5**
- DPPG        = **4461370.5**
- Cholesterol = **32403414.83** (32403414.833333332)
- DEPC        = **44013385.5**

Pooled bracketing (replicate 6 + bracketing 4), Tricaprylin:
- Mean = **8699733.9**
- %RSD = **0.2383** (0.23825156731474995)

Batch `EP20_117-299-B` %Assay (single injection → `%Mean` equals it):
- Tricaprylin = **99.979**
- DPPG        = **86.200**
- Cholesterol = **101.772**
- DEPC        = **100.390**

Drug-to-Lipid, batch `EP20_117-299-B` (LC: Tri 2, DPPG 0.9, Chol 4.7, DEPC 8.2;
`%Assay Bupivacaine` K=99.9, `LC Bupivacaine` L=13.3):
- `I` (Tricaprylin mg/mL Lipid) = **1.99958**
- `J` (Sum of Lipid)            = **15.790645**
- `M` (mg/mL Bupivacaine)       = **13.2867**
- `N` (Drug/Lipid Ratio)        = **0.841429**

All of the above were reproduced exactly by a scratch script during planning, so
the template is known to be expressible in the engine; the implementer's job is to
encode the same arithmetic declaratively and re-prove it.

### Full input matrix to feed the verification script (read from the xlsx / dump)

Standard details (rows 18–21): columns `Weight B, Vol C, Pip D, Vol E, Pip F,
Vol G, Potency H, MW_Base I, MW_Salt J`:
- Tricaprylin: 99.1, 50, 6, 100, 1, 1, 100, 1, 1
- DPPG (Na):   46.79, 50, 6, 100, 1, 1, 99.3, 721.9602, 744.95
- Cholesterol: 28.51, 100, 1, 1, 1, 1, 100, 1, 1
- DEPC:        49.32, 100, 1, 1, 1, 1, 99.2, 1, 1

Standard replicate areas (rows 25–30), columns B/C/D/E = Tri/DPPG/Chol/DEPC:
```
1  8711513  4437526  32277247  44369260
2  8674291  4473096  32439471  44366857
3  8679908  4461331  32393636  44211085
4  8671826  4528571  32357224  43613144
5  8715229  4403707  32429381  43626749
6  8695954  4463992  32523530  43893218
```
Bracketing areas (rows 25–28), columns H/I/J/K = Tri/DPPG/Chol/DEPC (4 rows only):
```
1  8713270  4473297  32509936  43884434
2  8686255  4509972  32485699  43979519
3  8719164  4448498  32455877  43323151
4  8729929  4472750  32460029  44269558
```
Per-compound LC (sheet G column): Tri 2, DPPG 0.9, Chol 4.7, DEPC 8.2.

Three batches, sample prep + injection areas (sheet M column). Each batch:
`Avg Weight H=1.005, Vol J=25, Pip K=1, Vol L=1`; `Sample Weight I` as below.
Injection-1 areas (Tri/DPPG/Chol/DEPC) then injection-2 areas where present:
- `EP20_117-299-B` (rows 39–46): I=1.5008; inj1 areas
  8729574 / 3826195 / 32474189 / 44235393; inj2 rows (43–46) blank areas →
  `%Mean` = inj1 value. `%Assay Bupivacaine` K=99.9.
- `EP20_117-299-C` (rows 48–55): I=1.5051; inj1 areas
  8576367 / 4183290 / 32445874 / 44011931; inj2 blank. K=97.8.
- `EP20_117-299-A` (rows 57–64): I=1.5104; inj1 areas
  8806534 / 3755690 / 32693267 / 43675013; inj2 blank. K=100.3.

(Batch B is the gold-gated batch; C and A are additional rows to confirm the
table/`%Mean`/ratio logic generalises. Their expected ratios are not pre-stated —
the script prints them for the computed-vs-expected table and the only hard
assertions are the batch-B gold values plus the ppm/mean/pooled standard values.)

---

## Formula mapping (sheet cell → template field expression)

Standard singleton `standard` (per compound `tri_/dppg_/chol_/depc_`):
- `*_conc_ppm` (K18..K21) =
  `*_weight / *_vol1 * *_pip1 / *_vol2 * *_pip2 / *_vol3 * *_potency / 100 * *_mw_base / *_mw_salt * 1000`
  (map sheet B=weight, C=vol1, D=pip1, E=vol2, F=pip2, G=vol3, H=potency,
  I=mw_base, J=mw_salt). Note Tricaprylin/Chol/DEPC have pip2/vol3 = 1, so the
  generic 3-term form collapses correctly.

Replicate table `std_areas` — 4 area columns `tri_area/dppg_area/chol_area/depc_area`.
Bracketing table `bkt_areas` — same 4 columns.

Statistics singleton `stats`:
- `mean_std_tri` (B31) = `mean(std_areas.tri_area)`; likewise dppg/chol/depc with C31/D31/E31.
- `sd_std_tri` (B32) = `sd(std_areas.tri_area)`; `rsd_std_tri` (B33) = `rsd(std_areas.tri_area)`.
- `mean_pool_tri` (H31) = `mean(pool(std_areas.tri_area, bkt_areas.tri_area))`;
  `sd_pool_tri` (H32) = `sd(pool(...))`; `rsd_pool_tri` (H33) = `rsd(pool(...))`.
  Repeat for all 4 compounds.

Lipid sample table `lipid_samples` (one row per batch). Inputs per row:
`batch_no, storage, packing, trf_no, ar_no` (text), `avg_weight` (H),
`sample_weight` (I), `vol_j` (J=25), `pip_k` (K=1), `vol_l` (L=1), and per
compound the two injection areas `*_area1`, `*_area2`.
- `tri_assay1` (N39) =
  `tri_area1 / stats.mean_std_tri * standard.tri_weight / standard.tri_vol1
   * standard.tri_pip1 / standard.tri_vol2 * standard.tri_pip2 / standard.tri_vol3
   * vol_j / sample_weight * vol_l / pip_k
   * standard.tri_potency / lc_tri * standard.tri_mw_base / standard.tri_mw_salt
   * avg_weight`
  where `lc_tri` is a per-row (or context) LC = 2. **Verify the factor order maps
  the sheet exactly**: sheet is `M/$B$31 * B18/C18 * D18/E18 * F18/G18 * J/I * L/K
  * H18/G39 * I18/J18 * H39` → `H18` is potency, `G39` is LC, `I18/J18` is
  mw_base/mw_salt, `H39` is avg weight. (Confirmed numerically: 99.979.)
- `tri_assay2` (N43) identical with `tri_area2`.
- `tri_mean` (O43) = `mean([tri_assay1, tri_assay2])` → blank second injection
  yields inj1 value (engine `mean` skips blanks). Repeat for dppg/chol/depc.
- Decide LC placement: cleanest is **context fields** `lc_tri/lc_dppg/lc_chol/lc_depc`
  (overridable, defaults 2/0.9/4.7/8.2) since LC is constant per compound across
  batches (sheet G39/G40/G41/G42 are repeated per batch). Document this; it also
  feeds the Drug-to-Lipid section's `G` column.

Drug-to-Lipid table `drug_lipid` (one row per batch, same ordering as
`lipid_samples`). Per row:
- `pct_assay_bupi` (K18) = input, default per batch not pre-set (99.9 / 97.8 /
  100.3 are per-batch inputs; leave as `input`, required).
- `lc_bupi` (L18) = context/input, default 13.3.
- `tri_mgml` (I18) = `lc_tri * lipid_samples.tri_mean[rowno-1] / 100` — i.e. the
  Lipid section `%Mean` for the same batch × compound LC / 100. Use `rowno-1`
  indexed access to pair the batch row. (Alternatively compute the four `mg/mL`
  inside `lipid_samples` and index the whole quantity; pick whichever keeps the
  reference legible — **document the choice**.) Repeat dppg/chol/depc.
- `sum_lipid` (J18) = `tri_mgml + dppg_mgml + chol_mgml + depc_mgml` (sheet uses
  `SUM(I18:I21)` over the 4 compound rows; as columns this is the 4-term sum).
- `mgml_bupi` (M18) = `pct_assay_bupi * lc_bupi / 100`.
- `ratio` (N18) = `mgml_bupi / sum_lipid`.

Apply rounding ONLY where the sheet's stored values imply it and the gold values
require it — the sheet wraps in `IFERROR` but applies no explicit ROUND, so keep
calculated fields unrounded internally and let the verification compare at the
sheet's display rounding (ppm 2–4 dp, assay 3 dp, mg/mL 5 dp, ratio 6 dp). If any
reportable needs rounding for display, round `ratio` to 6 dp at most; do not round
mid-chain (it would perturb the gold values). **Document that no mid-chain
rounding is applied.**

---

## Ordered implementation items

- [ ] 1. Author the template definition module
      `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`.
      Build the `definition` dict with: context header (reuse
      `context_header(label_claim=False, avg_weight=False, extra=[...])` for
      Generic Name / Product Name / Test / Analysis as per / Analysed By /
      Instrument Id. / Date of Analysis / TRF No. / AR No., plus the per-compound
      LC context fields `lc_tri/lc_dppg/lc_chol/lc_depc` defaults 2/0.9/4.7/8.2
      and `lc_bupi` default 13.3); the `standard` singleton (4×9 per-compound
      inputs + 4 `*_conc_ppm` calculated); the `std_areas` table (4 area columns,
      max 6 rows); the `bkt_areas` table (4 area columns, max 6 rows); the `stats`
      singleton (per-compound replicate mean/sd/rsd + pooled mean/sd/rsd); the
      `lipid_samples` table (batch inputs + per-compound 2-injection areas + per
      compound `*_assay1/*_assay2/*_mean`); the `drug_lipid` table (per-compound
      `*_mgml` + `sum_lipid` + `pct_assay_bupi` + `mgml_bupi` + `ratio`).
      Set `resultRef = "drug_lipid.ratio"`. Add the 8 SST criteria. Define
      `SeedTemplate(code="TPL-A2-0004", name="Bupivacaine Lipid Content &
      Drug-to-Lipid Ratio", archetype="A2", result_unit=None,
      test_code="TST-LIPID-RATIO", test_name="Lipid Content & Drug-to-Lipid Ratio
      by HPLC", test_type="Quantitative", definition=...)` and `TEMPLATES = [...]`.
      Put the Decision (a)–(e) rationale and the sheet-cell→field map in the module
      docstring and inline comments, citing sheet cells (K18, B31, N39, O43, I18,
      J18, M18, N18).
      Files: `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
      Verify: `cd backend-v2 && python -c "import ast; ast.parse(open('scripts/template_definitions/a2_bupivacaine_lipid_ratio.py',encoding='utf-8').read())"` — parses clean (full validation happens in item 3).

- [ ] 2. Register the new module in the seed aggregator.
      Import `TEMPLATES as _A2_BUPI` from the new module in
      `template_definitions/__init__.py` and append `*_A2_BUPI` to
      `SEED_TEMPLATES` (place it after the other A2 entries so the seed log stays
      archetype-ordered). Do not reorder or remove any existing import.
      Files: `backend-v2/scripts/template_definitions/__init__.py`
      Verify: `cd backend-v2 && python -c "from scripts.template_definitions import SEED_TEMPLATES; print([t.code for t in SEED_TEMPLATES if t.code=='TPL-A2-0004'])"` — prints `['TPL-A2-0004']`.

- [ ] 3. Validate the definition through the real seeder path (parse + dry-run).
      Run the seeder's validate-only mode, which does
      `TemplateDefinition.parse(defn)` + `WorksheetEvaluator(...).evaluate({},{})`
      for every template.
      Files: (none — validation only)
      Verify: `cd backend-v2 && python -m scripts.seed_test_templates --validate-only` — exits 0, lists `ok TPL-A2-0004 [A2] ...`, and reports no INVALID DEFINITIONS. Fix any schema/evaluation error before proceeding.

- [ ] 4. Write and run a THROWAWAY verification script proving the gold values.
      Create `backend-v2/.agents/tasks/bupivacaine-lipid-ratio/_verify.py` that:
      reads the input matrix (either hard-coded from this plan or parsed straight
      from the xlsx with `openpyxl`/zipfile), constructs `context_values` and
      `group_values` (std_areas 6 rows × 4 cols; bkt_areas 4 rows × 4 cols;
      lipid_samples 3 batch rows; drug_lipid 3 batch rows with `pct_assay_bupi`
      99.9/97.8/100.3), builds the template via
      `TemplateDefinition.parse(LIPID_RATIO_DEFINITION)` and runs
      `WorksheetEvaluator(...).evaluate(...)`. Assert to the sheet's rounding:
      the 4 Conc ppm; the 4 replicate means; pooled Tricaprylin mean 8699733.9 and
      %RSD 0.2383; batch-B %Assay 99.979 / 86.200 / 101.772 / 100.390; and
      Drug-to-Lipid batch B I(Tri) 1.99958, Sum 15.790645, M 13.2867, Ratio
      0.841429. Print a computed-vs-expected table for all three batches and save
      it to `.agents/tasks/bupivacaine-lipid-ratio/verification-output.txt`.
      Files: `backend-v2/.agents/tasks/bupivacaine-lipid-ratio/_verify.py`,
      `backend-v2/.agents/tasks/bupivacaine-lipid-ratio/verification-output.txt`
      Verify: `cd backend-v2 && python .agents/tasks/bupivacaine-lipid-ratio/_verify.py` — exits 0, all assertions pass, prints the computed-vs-expected table with every gold value matching to the stated rounding.

- [ ] 5. Seed the template into the DB (additive, idempotent).
      Run the seeder in its default Active mode. It creates the `TST-LIPID-RATIO`
      Test Master entry via `ensure_test` and inserts `TPL-A2-0004`; it SKIPS any
      already-present code, so re-runs are safe.
      Files: (DB write only; no source files change)
      Verify: `cd backend-v2 && python -m scripts.seed_test_templates` — exits 0 and logs `+ Test Master: TST-LIPID-RATIO ...` and `add TPL-A2-0004 [A2] Bupivacaine Lipid Content & Drug-to-Lipid Ratio -> TST-LIPID-RATIO`. A second run logs `skip TPL-A2-0004 — already present`.

- [ ] 6. Run the backend test suite to confirm no regression.
      Run the project's test runner (discover the command from `backend-v2`:
      check for `pytest.ini`/`pyproject.toml`/`setup.cfg`; the suite is pytest).
      Files: (none)
      Verify: `cd backend-v2 && python -m pytest -q` — exits 0 (all existing tests pass; the new seed entry does not alter any stored existing template `definition`). If the runner differs, use the one declared in the project config discovered here.

- [ ] 7. DELETE the throwaway verification script; keep the evidence.
      Remove `_verify.py` but leave `verification-output.txt` (and this `plan.md`)
      under `.agents/tasks/bupivacaine-lipid-ratio/` as the evidence trail.
      Files: delete `backend-v2/.agents/tasks/bupivacaine-lipid-ratio/_verify.py`
      Verify: `cd backend-v2 && python -c "import os; print(not os.path.exists('.agents/tasks/bupivacaine-lipid-ratio/_verify.py') and os.path.exists('.agents/tasks/bupivacaine-lipid-ratio/verification-output.txt'))"` — prints `True`.

---

## Guardrails for the implementer

- Add ONLY `TPL-A2-0004`. Do NOT edit, renumber, or re-seed any existing template
  or Test (especially `a12_derived_rollups.py` / `TPL-A12-0002` / `TST-DLR`).
- Do not change stored `definition` JSON of existing templates — the seeder and
  the e-signature trail depend on them staying byte-for-byte stable.
- Reuse `_common.context_header` for the header; the per-compound and ratio
  arithmetic is bespoke (like `a2_lyso_content.py`) and should be written inline
  rather than forced through the 3-stage dilution helpers.
- No mid-chain rounding — it perturbs the gold values. Round only the final
  `ratio` for display if at all, at 6 dp.
- No frontend changes.

## Open assumptions (reasonable defaults taken; flag only if a reviewer disagrees)

- SST limit 2.0 % NMT per compound (sheet prints none; matches every sibling HPLC
  template).
- Per-compound LC and `lc_bupi` modelled as overridable context (constant across
  batches in the sheet). If the lab needs per-batch LC override, promote them to
  per-row inputs in `lipid_samples`/`drug_lipid` — the arithmetic is unchanged.
- `result_unit = None` (unitless ratio), matching `TPL-A12-0002`.
