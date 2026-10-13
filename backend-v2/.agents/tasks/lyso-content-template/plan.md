# Implementation Plan — Content of Lyso PC / Lyso PG (mg/mL) template

One new declarative seed template that reproduces the Excel sheet
`d:\RD-instance\GIT\Test types\Content of Lyso PC PG_mgmL_Ampho.xlsx`
(dump: `d:\RD-instance\GIT\_dumps\Content of Lyso PC PG_mgmL_Ampho.txt`) exactly.
Backend/data only. Do NOT touch the frontend. Do NOT modify or renumber any
existing template.

## Pinned decisions (made during exploration, grounded in the codebase)

- **Template code: `TPL-A2-0002`.** The A2 family currently holds only
  `TPL-A2-0001` (verified by grep of `scripts/template_definitions/**`), so
  `-0002` is the next free, non-colliding code. All other families
  (`TPL-A1..A14`) are untouched.
- **Archetype: `A2`** ("Multi-Analyte Content by HPLC"). Confirmed the closest
  fit: like A2, each analyte response is a *sum of named sub-peaks per injection*
  with the `IF(SUM(...)=0, blank, SUM(...))` guard, computed against a weighed
  standard, reported as content (A2's A2 reports mg via a vial factor; here we
  report mg/mL directly like A3). Reusing archetype label `A2` is correct — the
  archetype tag is a family label, not a unique key (A6 reuses `A6a/A6b/A6c`,
  A8 reuses `A8` across two templates).
- **Test Master binding: new entry `TST-LYSO`**, name `Content of Lyso PC &
  Lyso PG by HPLC`, type `Quantitative`. `TST-LYSO` does not exist (grep of
  `test_code=` shows no collision). `ensure_test` in `seed_test_templates.py`
  creates it on first seed. Matches the naming/type convention of every other
  `SeedTemplate` (e.g. `TST-CONT` / `Quantitative`).
- **result_unit: `mg/mL`** (matches A3's precedent for an absolute mg/mL result).
- **resultRef: `sample_results.pc_mgml`** (the Lyso PC mg/mL reportable; the
  evaluator's `_extract_result` returns the last non-blank value of a multi-row
  group, which for the 1–2 sample injections is the Avg/last injection — the
  sheet's primary reported column is Lyso PC mg/mL, cell C-column).
- **Layout strategy: wide side-by-side PC/PG columns (NOT a compound-keyed
  table).** The sheet lays both compounds out as parallel columns and the sample
  result row (`C61..F61`) references *both* compounds and *both* standard means
  in a single row. The 1-D group model (evaluator.py scoping) makes a single
  row that reads two different compound-standard means trivial when the standard
  values are per-compound *scalar* fields in a singleton, and awkward if they
  are two rows of a table. So: standard details = one **singleton** with
  `pc_*`/`pg_*` scalar fields; injections = **table** groups with `pc_*` sub-peak
  area columns, `pg_*` sub-peak area columns, and calculated `sum_pc`/`sum_pg`;
  stats = one **singleton**; sample results = one **table** with the four
  calculated result columns.
- **Per-compound dilution chain is 2-stage, hand-written (NOT the generic
  3-stage `_common` helpers).** The sheet's standard chain is `C/D * E/F`
  (Weight/Vol1 * Pip/Vol2) and the per-compound MW + potency terms differ, so
  the generic `standard_group`/`standard_chain_terms` (which assume shared
  `vol_1/pip_1/vol_2/pip_2/vol_3` and one potency) do not fit. We still reuse
  `context_header` and `sst_rsd_criterion` from `_common.py`.

### Exact formula → expression mapping (verified numerically, all expected numbers reproduce to rounding)

Standard scalars (singleton `standard`): `pc_weight,pc_vol1,pc_pip,pc_vol2,pc_mw_base,pc_mw_salt,pc_potency,pc_lc` and the `pg_*` equivalents.
Sample dilution scalars (singleton `sample_prep`): `ml, vol, pip, vol2`.

- Per-injection PC sum area: `if(sum([pc_1,pc_2,pc_3,pc_4,pc_5]) = 0, blank(), sum([pc_1,pc_2,pc_3,pc_4,pc_5]))` (sheet `IF(SUM(C:G)=0," ",SUM(C:G))`, 5 PC slots C–G).
- Per-injection PG sum area: `if(sum([pg_1,pg_2]) = 0, blank(), sum([pg_1,pg_2]))` (sheet `SUM(H:I)`, 2 PG slots H–I).
- Standard stats PC: mean `mean(std_injections.sum_pc)` (= sheet `L34`), sd `sd(std_injections.sum_pc)` (`L35`), %rsd `rsd(std_injections.sum_pc)` (`L36`).  PG analogous over `.sum_pg`.
- Pooled BKT stats PC: mean `mean(pool(std_injections.sum_pc, bkt_injections.sum_pc))` (= sheet `L46`, pools L28:L33 with L40:L45; `pool` skips blanks), sd `sd(pool(...))`, %rsd `rsd(pool(...))`. PG analogous over `.sum_pg`.
- **Lyso PC mg/mL** (sheet `C61 = L57/L34*C23/D23*E23/F23*G23/H23*H53/G53*J53/I53*I23/100`):
  `sum_pc / stats.mean_std_pc * standard.pc_weight / standard.pc_vol1 * standard.pc_pip / standard.pc_vol2 * standard.pc_mw_base / standard.pc_mw_salt * sample_prep.vol / sample_prep.ml * sample_prep.vol2 / sample_prep.pip * standard.pc_potency / 100`
- **Lyso PG mg/mL** (sheet `D61 = M57/M34*C24/D24*E24/F24*J53/I53*H53/G53*G24/H24*I24/100`):
  `sum_pg / stats.mean_std_pg * standard.pg_weight / standard.pg_vol1 * standard.pg_pip / standard.pg_vol2 * sample_prep.vol2 / sample_prep.pip * sample_prep.vol / sample_prep.ml * standard.pg_mw_base / standard.pg_mw_salt * standard.pg_potency / 100`
  (NOTE: mean-std denominators are the 6-injection standard stats `stats.mean_std_pc/pg`, NOT the pooled BKT means.)
- **Lyso PC Assay %** (`E61 = C61*100/J23`): `pc_mgml * 100 / standard.pc_lc`.
- **Lyso PG Assay %** (`F61 = D61*100/J24`): `pg_mgml * 100 / standard.pg_lc`.
- Avg row (`C63=(C61+C62)/2`): use `mean(sample_results.pc_mgml)` etc. — `mean`
  skips the blank second injection, so one injection still produces a result
  (tolerant of blank injection-2, matching the sheet's intent even though the
  sheet's literal `/2` would halve a single value; `mean` is the correct
  blank-tolerant form and the house pattern — see A2 `mean_pct_lc`).

### Criteria (system suitability, all blocking NMT 2.0)

Use the `sst_rsd_criterion` convention from `_common.py` (same shape, blocking,
`limitText` "NMT 2.0 %"), one per observed value, keyed uniquely:
- `stats.rsd_std_pc` NMT 2.0, `stats.rsd_std_pg` NMT 2.0,
- `stats.rsd_pool_pc` NMT 2.0, `stats.rsd_pool_pg` NMT 2.0.
(`sst_rsd_criterion(target=..., )` sets a fixed `key="sst_std_rsd"`; since four
criteria are needed with distinct keys, build the four dicts directly in the
same shape rather than calling the helper four times, OR call the helper and
override `key`. Plan: build four explicit dicts following the helper's shape.)

## Build & test commands (discovered)

- Project: FastAPI/SQLite LIMS at `backend-v2`, Python, pytest
  (`pyproject.toml` → `[tool.pytest.ini_options]`, `testpaths=["tests"]`,
  `asyncio_mode="auto"`). No README/AGENTS/CONTRIBUTING/steering files exist.
- Validate all seed definitions (parses + dry-run evaluate, no DB writes):
  `python -m scripts.seed_test_templates --validate-only` (run from `backend-v2`).
- Seed as Active (`approved_by='seed'`), additive/idempotent:
  `python -m scripts.seed_test_templates`.
- Unit tests for the calculation engine: `python -m pytest tests/calculation`
  (run from `backend-v2`).

---

## Ordered implementation items

- [ ] 1. Create the new template-definition module `a2_lyso_content.py`.
      Build it as a single `LYSO = SeedTemplate(code="TPL-A2-0002", name="Content of Lyso PC / Lyso PG (mg/mL)", archetype="A2", result_unit="mg/mL", test_code="TST-LYSO", test_name="Content of Lyso PC & Lyso PG by HPLC", test_type="Quantitative", definition=LYSO_DEFINITION)` and `TEMPLATES = [LYSO]`, mirroring the module shape of `a2_a3_content.py`. Reuse `context_header` and import `SeedTemplate` from `._common`. The `LYSO_DEFINITION` dict must contain, in order, the groups described in items 2–7, plus `resultRef="sample_results.pc_mgml"` and the four criteria from item 8. Follow the docstring convention (brief rationale: wide PC/PG layout, 2-stage per-compound chain, pooled BKT, mean-std ≠ pooled-mean).
      Files: `d:\RD-instance\GIT\backend-v2\scripts\template_definitions\a2_lyso_content.py` (new)
      Verify: deferred to item 9 (`--validate-only`) — module is not yet registered, so no standalone build step; this item just authors the file.

- [ ] 2. Add the CONTEXT/HEADER block to `LYSO_DEFINITION["context"]`.
      Use `context_header(extra=[...])` with text/overridable context fields for the sheet's header: Generic Name & Product Name (`context_header` already provides `generic_name` sourced from `product.name`; add `product_name` text/overridable), Batch No. (provided), Storage Condition, Packing Detail, Test, Analysis as per, Analysed By (provided), Instrument Id. (provided as `instrument_id`), TRF No., AR No., Date of Analysis (provided). Add only the missing ones as `extra` (`storage_condition`, `packing_detail`, `test_name_ctx`, `analysis_as_per`, `trf_no`, `ar_no`, `product_name`) as `kind:"context", type:"text", overridable:true`. Do not add `label_claim`/`avg_weight` divisors — this sheet has none; call `context_header(label_claim=False, avg_weight=False, extra=[...])`.
      Files: `a2_lyso_content.py`
      Verify: deferred to item 9.

- [ ] 3. Add the `standard` singleton group (per-compound scalar standard details).
      Fields (all `kind:"input"`, numbers, with sheet defaults as `default`): `pc_weight` (17.547), `pc_vol1` (50), `pc_pip` (4), `pc_vol2` (20), `pc_mw_base` (1), `pc_mw_salt` (1), `pc_potency` (98), `pc_lc` (1); `pg_weight` (18.411), `pg_vol1` (100), `pg_pip` (4), `pg_vol2` (20), `pg_mw_base` (511.61), `pg_mw_salt` (534.6), `pg_potency` (98.3), `pg_lc` (1). `kind:"singleton"`, `label:"Standard Details"`.
      Files: `a2_lyso_content.py`
      Verify: deferred to item 9.

- [ ] 4. Add the `std_injections` table group (6 standard replicate injections).
      `kind:"table"`, `rows:{min:1,max:6,default:6}`. Fields: five PC sub-peak AREA columns `pc_1..pc_5` (`kind:"area"`, labels "Lyso PC-1".."Lyso PC-5"), two PG sub-peak AREA columns `pg_1,pg_2` (labels "Lyso PG-1","Lyso PG-2"); calculated `sum_pc` = `if(sum([pc_1,pc_2,pc_3,pc_4,pc_5]) = 0, blank(), sum([pc_1,pc_2,pc_3,pc_4,pc_5]))`; calculated `sum_pg` = `if(sum([pg_1,pg_2]) = 0, blank(), sum([pg_1,pg_2]))`.
      Files: `a2_lyso_content.py`
      Verify: deferred to item 9.

- [ ] 5. Add the `bkt_injections` table group (bracketing standard, up to 6).
      Identical field set to `std_injections` (same `pc_1..pc_5`, `pg_1,pg_2`, `sum_pc`, `sum_pg`), `kind:"table"`, `rows:{min:1,max:6,default:6}`, `label:"BKT Standard Details"`. (Blank rows are tolerated: `sum_*` returns blank for an empty row and `pool`/`mean`/`sd` skip blanks.)
      Files: `a2_lyso_content.py`
      Verify: deferred to item 9.

- [ ] 6. Add the `stats` singleton group (standard stats + pooled BKT stats).
      Calculated fields: `mean_std_pc`=`mean(std_injections.sum_pc)`, `sd_std_pc`=`sd(std_injections.sum_pc)`, `rsd_std_pc`=`rsd(std_injections.sum_pc)`; `mean_std_pg`,`sd_std_pg`,`rsd_std_pg` over `.sum_pg`; `mean_pool_pc`=`mean(pool(std_injections.sum_pc, bkt_injections.sum_pc))`, `sd_pool_pc`=`sd(pool(std_injections.sum_pc, bkt_injections.sum_pc))`, `rsd_pool_pc`=`rsd(pool(std_injections.sum_pc, bkt_injections.sum_pc))`; `mean_pool_pg`,`sd_pool_pg`,`rsd_pool_pg` over the `.sum_pg` pool. Units `%` on the `rsd_*` fields. (No rounding on means used as denominators, to match the sheet which divides by the raw `L34`.)
      Files: `a2_lyso_content.py`
      Verify: deferred to item 9.

- [ ] 7. Add the `sample_prep` singleton and `sample_results` table groups.
      `sample_prep` singleton (`label:"Sample Details"`): input fields `ml` (default 10), `vol` (default 20), `pip` (default 1), `vol2` (default 1). `sample_results` table (`label:"Sample Injections"`, `rows:{min:1,max:2,default:2}`): five PC AREA columns `pc_1..pc_5`, two PG AREA columns `pg_1,pg_2`; calculated `sum_pc`,`sum_pg` (same IF-blank guard as item 4); calculated `pc_mgml`, `pg_mgml`, `pc_assay`, `pg_assay` using the exact expressions in the "formula mapping" section above; and `avg_pc_mgml`=`mean(sample_results.pc_mgml)`, `avg_pg_mgml`=`mean(sample_results.pg_mgml)`, `avg_pc_assay`=`mean(sample_results.pc_assay)`, `avg_pg_assay`=`mean(sample_results.pg_assay)`. Rounding: match the sheet's reported precision — `pc_mgml`/`pg_mgml` and their averages `round` 6 digits; `pc_assay`/`pg_assay` and averages `round` 4 digits. (Expected: inj-1 PC=0.036137 mg/mL, PG=0.022307 mg/mL, PC assay=3.6137 %, PG assay=2.2307 %.)
      Files: `a2_lyso_content.py`
      Verify: deferred to item 9.

- [ ] 8. Add the four blocking SST %RSD criteria to `LYSO_DEFINITION["criteria"]`.
      Four dicts in `sst_rsd_criterion` shape (`operator:"lte"`, `limit:2.0`, `severity:"blocking"`, `limitText:"NMT 2.0 %"`), with distinct keys/labels and targets: `stats.rsd_std_pc`, `stats.rsd_std_pg`, `stats.rsd_pool_pc`, `stats.rsd_pool_pg`.
      Files: `a2_lyso_content.py`
      Verify: deferred to item 9.

- [ ] 9. Register the module in `__init__.py` and validate the whole catalogue.
      Add `from scripts.template_definitions.a2_lyso_content import TEMPLATES as _A2_LYSO` and splice `*_A2_LYSO` into `SEED_TEMPLATES` immediately after `*_A2_A3` (keeps archetype ordering). Change nothing else.
      Files: `d:\RD-instance\GIT\backend-v2\scripts\template_definitions\__init__.py`
      Verify: from `backend-v2`, run `python -m scripts.seed_test_templates --validate-only`. Expected: the new `TPL-A2-0002 [A2]` line prints `ok ...` with its group/input/area/calculated/criteria counts, every other template still `ok`, and the run ends "All definitions valid. --validate-only, so nothing was written." (exit 0). This proves the definition parses and dry-run-evaluates (the same two passes `TestTemplateService` applies).

- [ ] 10. Write a throwaway verification script that reproduces the sheet's numbers.
      Create `scripts/_verify_lyso.py` (temporary; deleted in item 12) that imports `LYSO` from `scripts.template_definitions.a2_lyso_content`, parses it with `TemplateDefinition.parse`, and runs `WorksheetEvaluator(...).evaluate(context_values={}, group_values={...})` with the sheet's example inputs: `standard` singleton = the item-3 defaults; `std_injections` = the 6 rows from the dump (pc_1=C, pc_2=D, pc_3=E, pc_4=F, pc_5=G; pg_1=H, pg_2=I — e.g. inj1 pc_2=1706610, pc_3=872445, pc_5=9048763, pg_2=6413351; transcribe all 6 rows incl. the H-column values on rows 3/4); `bkt_injections` = the 4 populated BKT rows (rows 40–43) plus 2 blank rows; `sample_prep` = {ml:10,vol:20,pip:1,vol2:1}; `sample_results` = inj-1 (pc_2=426014,pc_3=903320,pc_5=1683234,pg_1=598217,pg_2=1469127) and a blank inj-2. Assert with a tolerance (e.g. `abs(a-b) <= abs(b)*1e-4`): `stats.mean_std_pc`≈11468461.5, `stats.mean_std_pg`≈6420652.17, `stats.rsd_std_pc`≈2.21, `stats.rsd_std_pg`≈2.32, `stats.mean_pool_pc`≈11333895, `stats.mean_pool_pg`≈6431312.5, `stats.rsd_pool_pc`≈2.46, `stats.rsd_pool_pg`≈1.90, `sample_results[0].sum_pc`=3012568, `.sum_pg`=2067344, `.pc_mgml`≈0.036137, `.pg_mgml`≈0.022307, `.pc_assay`≈3.6137, `.pg_assay`≈2.2307. Print PASS/FAIL per assertion and exit non-zero on any failure.
      Files: `d:\RD-instance\GIT\backend-v2\scripts\_verify_lyso.py` (new, temporary)
      Verify: from `backend-v2`, run `python -m scripts._verify_lyso`. Expected: every assertion PASS, exit 0. If any value is off, the expression mapping or input transcription is wrong — fix before proceeding.

- [ ] 11. Run the calculation unit-test suite to confirm nothing regressed.
      No existing test is modified; this is a regression guard that the engine still parses/evaluates the extended catalogue.
      Files: none
      Verify: from `backend-v2`, `python -m pytest tests/calculation`. Expected: all tests pass.

- [ ] 12. Seed the template and clean up the throwaway script.
      From `backend-v2`, run `python -m scripts.seed_test_templates` (Active, `approved_by='seed'`). Then delete `scripts/_verify_lyso.py`.
      Files: deletes `d:\RD-instance\GIT\backend-v2\scripts\_verify_lyso.py`
      Verify: the seeder prints `+ Test Master: TST-LYSO — Content of Lyso PC & Lyso PG by HPLC` and `add TPL-A2-0002 [A2] Content of Lyso PC / Lyso PG (mg/mL) -> TST-LYSO`, ends "Done. 1 template(s) added, N already present." (exit 0). Re-running the seeder prints `skip TPL-A2-0002 — already present` (idempotency check). Confirm `scripts/_verify_lyso.py` no longer exists.

## Notes / assumptions

- The Avg row uses blank-tolerant `mean(...)` rather than the sheet's literal
  `(C61+C62)/2`; with a single filled injection this yields that injection's
  value (the correct behaviour), matching the A2 `mean_pct_lc` house pattern.
- `pg_mw_base`/`pg_mw_salt` are entered as given (511.61 / 534.6); the ratio
  0.957 is applied exactly as the sheet does. PC's MW terms are 1/1 (no-op).
- No frontend changes. No existing template, test, or seeder logic is modified
  beyond the single `__init__.py` registration line.
