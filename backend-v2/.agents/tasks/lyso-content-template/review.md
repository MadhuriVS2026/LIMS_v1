# Lyso PC / Lyso PG content template (TPL-A2-0002)

A single new declarative seed template reproduces the `Content of Lyso PC PG_mgmL_Ampho` workbook: a two-analyte HPLC content assay reporting Lyso PC and Lyso PG in mg/mL (and as %) against a weighed standard, with a pooled bracketing-standard SST block. The change is backend/data only — one new module `a2_lyso_content.py` plus two registration lines in `__init__.py`, committed as HEAD `0a0dd8b`. The template is correct only if it reproduces the sheet's stored numbers, and the coder's evidence plus a formula-level spot-check confirm it does.

Watch for: nothing blocking. The sample-result expressions correctly divide by the 6-injection standard means (`L34/M34`), not the pooled BKT means (`L46/M46`) — the single most error-prone point in this sheet, and it is right (confirmed). The two unrelated pre-existing calculation-service test failures are not caused by this change (confirmed via git-stash isolation in the evidence).

**Verdict**: APPROVED

## High-level view

The layout choice is a wide, side-by-side PC/PG model rather than a compound-keyed table: standard details are a singleton of per-compound scalar fields (`pc_*`/`pg_*`), each injection table carries both compounds' sub-peak area columns plus summed `sum_pc`/`sum_pg`, and the single sample-result row reads both compounds' standard means as plain scalars. This is the right call for a sheet whose result row (`C61..F61`) cross-references both analytes at once.

The per-compound dilution chain is hand-written (`Weight/Vol1 * Pip/Vol2` with per-compound MW and potency terms) rather than routed through the generic 3-stage `_common` helpers, which assume shared stage fields and a single potency and do not fit here. `context_header` and the `sst_rsd_criterion` shape are still reused, so the module stays in the house declarative style.

The reportable expressions transcribe sheet `C61/D61/E61/F61` term-for-term, including the critical detail that the mean-standard denominators are `stats.mean_std_pc/pg` (the six-injection means), never the pooled bracketing means. Pooled BKT statistics use `pool(...)` over the SUM-AREA columns, which drops blank rows so a partially filled bracketing block still reconciles. Per-injection sum areas sum the correct sub-peak slots (PC: C–G, PG: H–I) behind the sheet's `IF(SUM(...)=0," ",SUM(...))` blank guard.

Exactly one new template was added — `TPL-A2-0002`, Active, version 1, `approved_by='seed'`, bound to the newly created `TST-LYSO` Test Master entry, with a non-colliding code in an A2 family that previously held only `TPL-A2-0001`. No existing template was modified or renumbered. All four SST %RSD criteria are blocking at NMT 2.0 %.

<details>
<summary>Issues (0)</summary>

No blocking or non-blocking actionable findings. All expected numbers reproduce and the key expressions match the sheet exactly.

</details>

<details>
<summary>Details</summary>

### Numeric reproduction

The evidence file records the throwaway check (`python -m scripts._verify_lyso`, exit 0) reproducing all fourteen stored values, each matching the review brief's targets: Standard means PC 11,468,461.5 / PG 6,420,652.17, Standard %RSD PC 2.21 / PG 2.32; Pooled BKT means PC 11,333,895 / PG 6,431,312.5, %RSD PC 2.46 / PG 1.90; Sample inj-1 sum areas PC 3,012,568 / PG 2,067,344; Reportable inj-1 Lyso PC 0.036137 / PG 0.022307 mg/mL and Assays 3.6137 % / 2.2307 %. Exact values are asserted at relative 1e-4; the four %RSD values at absolute 0.005 (the plan quotes them to two decimals, and the computed four-decimal figures round to the expected ones). Every assertion is PASS.

### Reportable-expression transcription (spot-checked against the dump)

I traced `pc_mgml` and `pg_mgml` cell-by-cell against the sheet dump rather than relying solely on the evidence table, because the mean-std-vs-pooled-mean distinction is the one place this sheet is easy to get wrong.

Sheet `C61 = L57/L34 * C23/D23 * E23/F23 * G23/H23 * H53/G53 * J53/I53 * I23/100`. The module's `pc_mgml` is `sum_pc / stats.mean_std_pc * standard.pc_weight/pc_vol1 * standard.pc_pip/pc_vol2 * standard.pc_mw_base/pc_mw_salt * sample_prep.vol/sample_prep.ml * sample_prep.vol2/sample_prep.pip * standard.pc_potency/100`. Term for term: L57→sum_pc, L34→mean_std_pc, C23/D23→pc_weight/pc_vol1, E23/F23→pc_pip/pc_vol2, G23/H23→pc_mw_base/pc_mw_salt, H53/G53→sample Vol/mL (sheet H52=Vol, G52=mL), J53/I53→sample Vol2/Pip (J52=Vol, I52=Pip), I23/100→pc_potency/100. Match.

Sheet `D61 = M57/M34 * C24/D24 * E24/F24 * J53/I53 * H53/G53 * G24/H24 * I24/100`. The module's `pg_mgml` reorders the sample terms as `vol2/pip` then `vol/ml` and the MW terms as `pg_mw_base/pg_mw_salt`, matching the sheet's `J53/I53 * H53/G53 ... G24/H24` ordering exactly. Match. Assays `E61=C61*100/J23` and `F61=D61*100/J24` map to `pc_mgml*100/pc_lc` and `pg_mgml*100/pg_lc`. Match.

The mean-std denominators are `stats.mean_std_pc` / `stats.mean_std_pg`, i.e. the six-injection standard means (`L34/M34`), not the pooled bracketing means (`L46/M46`). Confirmed correct.

### Sum-area guards and pooled statistics

Per-injection sum columns are `if(sum([pc_1..pc_5]) = 0, blank(), sum([pc_1..pc_5]))` (sheet PC slots C–G) and `if(sum([pg_1,pg_2]) = 0, blank(), sum([pg_1,pg_2]))` (PG slots H–I), reproducing the sheet's `IF(SUM(...)=0," ",SUM(...))`. The entered-area transcription in the check (`D28`→pc_2, `E28`→pc_3, `G28`→pc_5, `I28`→pg_2) matches the dump rows.

The pooled stats are `mean/sd/rsd(pool(std_injections.sum_pc, bkt_injections.sum_pc))` and the PG equivalents. `_f_pool` in `expression.py` flattens and drops blanks, so the two empty BKT rows (dump rows 44–45) are skipped — pooling the six standard with the four populated bracketing injections = ten values, matching the sheet's `AVERAGE(L28:L33,L40:L45)`. `_f_sd` is sample SD (n-1, Excel STDEV) and `_f_rsd` is `sd/mean*100`, matching `L36 = L35*100/L34`. The Avg sample row uses blank-tolerant `mean(sample_results.pc_mgml)`, so a single filled injection yields that injection's value — the documented house pattern, diverging intentionally from the sheet's literal `(C61+C62)/2`.

### Registration, uniqueness, and binding

`git show --stat 0a0dd8b` lists exactly four files: the new module (+334), `__init__.py` (+2: one import, one `*_A2_LYSO` splice after `*_A2_A3`), and the two task docs. No existing template module appears in the diff, so nothing was modified or renumbered. The evidence's confirmation query shows `TPL-A2-0002` present exactly once — Active, version 1, `approved_by='seed'`, `mg/mL`, bound to `TST-LYSO` (`Content of Lyso PC & Lyso PG by HPLC`, Quantitative) — and the pre-existing `TPL-A2-0001` still Active. The code is the next free code in a family that held only `-0001`.

### Reuse and style

The module imports `SeedTemplate` and `context_header` from `_common` and rebuilds the `sst_rsd_criterion` shape via a local `_rsd_criterion` helper, because four distinct-keyed criteria are needed and the shared helper hard-codes a single `key`. All four criteria are `operator:"lte"`, `limit:2.0`, `severity:"blocking"`, `limitText:"NMT 2.0 %"`, targeting `rsd_std_pc/pg` and `rsd_pool_pc/pg`. The declarative dict shape, docstring-carries-rationale convention, and group ordering match the sibling modules. Backend/data only; no frontend touched.

### Verification hygiene

Both throwaway scripts (`scripts/_verify_lyso.py`, `.agents/tasks/lyso-content-template/_q.py`) are confirmed absent on disk. The seeder ran clean in validate-only and additive modes and is idempotent on re-run. The two `test_worksheet_service.py` failures concern QA-correction / analyst-permission logic and were shown pre-existing by temporarily reverting the registration — unrelated to this change.

</details>

<details>
<summary>File map</summary>

- `scripts/template_definitions/a2_lyso_content.py` — new module; `LYSO` SeedTemplate + `LYSO_DEFINITION` (standard singleton, std/bkt injection tables, stats singleton, sample_prep singleton, sample_results table, four SST criteria).
- `scripts/template_definitions/__init__.py` — one import and one `*_A2_LYSO` splice after `*_A2_A3`.
- `.agents/tasks/lyso-content-template/plan.md`, `verification.md` — task docs.

Full diff: `git show 0a0dd8b` (from `d:\RD-instance\GIT`).

</details>
