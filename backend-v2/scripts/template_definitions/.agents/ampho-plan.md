# Implementation Plan — "Lipid content Ampho" seed template (TPL-A2-0005)

A single focused, strictly additive change: one new seed module plus one registry
splice. Modeled on the sibling `a2_bupivacaine_lipid_ratio.py`, but reduced to a
PURE lipid-content assay — no drug-to-lipid ratio, no Bupivacaine, no cross-set
"% Mean each compound" table, no tall 2-SET sample layout. The sample table is a
flat 4-row table (one row per compound).

Do NOT touch any other template module, the Bupivacaine module, `TST-LIPID-RATIO`,
`lims.db`, the engine, or the schema. Edit in place under
`d:\RD-instance\GIT\backend-v2`; run Python from that directory as a module.

## Design decisions (grounded in the files read)

- **Sheet**: `d:\RD-instance\GIT\_dumps\Lipid content_ Ampho.txt`, sheet
  `PTF_142HIN-400-A`, dims A1:K64. Verified every cell/formula below against it.
- **Standard Details = TABLE**, one row per compound (sheet rows 22–25), reached by
  row index `standard.<field>[idx]` (Cholesterol 0, Alpha tocopherol 1, DSPG 2,
  HSPC 3). Mirrors Bupivacaine's tabular standard block. **TWO dilution stages only**
  (weight, vol1, pip1, vol2) — sheet has columns Weight/Vol/Pip/Vol and NO
  pip2/vol3 third stage. Adapt `_standard_fields` accordingly; omit pip2/vol3 and
  the `conc_ppm` column (the Ampho sheet prints no Conc. column).
- **LC as overridable context** `lc_chol / lc_alpha / lc_dspg / lc_hspc` (defaults
  52, 0.64, 81.6, 213 — sheet G22..G25), mirroring Bupivacaine's `lc_*`. LC is
  constant per compound across the sheet and is a divisor, so context is the right
  home. The `%Assay` denominator reads `lc_<c>` directly.
- **Replicate + BKT injections = transposed tables** (one row per injection, one
  area column per compound `chol_area/alpha_area/dspg_area/hspc_area`), with
  `labelFrom="standard.name[idx]"` column headers and per-compound Mean/SD/%RSD
  published by a `stats` singleton and shown in each table footer. Sheet rows 29–34
  (6 replicates) and 41–45 (up to 5 bracketing). Pooled stats =
  `mean/sd/rsd(pool(std_areas.<c>_area, bkt_areas.<c>_area))`, matching the sheet's
  `AVERAGE(B41:B45,B29:B34)` / `STDEV(...)`. Verified `pool/mean/sd/rsd` semantics in
  `expression.py` (blank-skipping; sd/rsd need ≥2 values — the 6 replicates satisfy
  this). **Mean_std denominator for %Assay is the 6-injection replicate mean** (sheet
  `E56` divides by `B35`=`AVERAGE(B29:B34)`), NOT the pooled BKT mean.
- **Sample prep = singleton** (sheet single prep row 53: F53 avg_weight=1,
  G53 sample_weight=1, H53 vol=250, I53 pip=1, J53 vol=1). Single prep → singleton is
  simplest and consistent with the sheet and with `a2_lyso_content.py`'s
  `sample_prep`. Cross-group references from the sample table are fully qualified
  (`sample_prep.vol_h` etc.) so they resolve — unqualified names only resolve within
  the current row (confirmed in `evaluator.py` / `_common.py` docstrings).
- **Sample table = flat TABLE pinned min==max==default==4** (sheet rows 56–59), one
  row per compound, compound name from `standard.name[(rowno-1)]`. Columns Area-1,
  Area-2, calculated Avg Area, calculated % Assay. Pinning min==max hides add/remove
  row controls (same device Bupivacaine uses for its fixed blocks).
- **8 BLOCKING %RSD criteria**, NMT 2.0 %, per compound × {replicate, pooled} —
  house convention (Bupivacaine, Lyso). No acceptance range on %Assay (sheet states
  none).
- **No mid-chain rounding** anywhere (sheet wraps in IFERROR with no ROUND).
  `%Assay` left unrounded; display rounding is the front end's concern.
- **Verified %Assay numerically** against sheet E56..E59 with the replicate means
  `[1572872.83, 451519.0, 290188.17, 748650.0]`: Cholesterol 125.30, Alpha
  tocopherol 115.10, DSPG 122.70, HSPC 129.86 — exact match to the task's stated
  outputs. These are formula outputs (the sheet stores no %Assay result), so
  reproduce the FORMULA, do not hardcode results.

### Exact %Assay expression (per compound, idx = row index in _COMPOUNDS)

Sheet `E56` (Cholesterol):
`=D56/B35*B22/C22*D22/E22*J53/I53*H53/G53*F53/G22*F22*H22/I22`

Maps field-for-field to the engine (built once via a `_compound_select`-free direct
per-row expression, since the flat table's compound is fixed by row index):

```
avg_area / stats.mean_std_<c>
  * standard.weight[idx] / standard.vol1[idx]        (B/C)
  * standard.pip1[idx]   / standard.vol2[idx]        (D/E)
  * sample_prep.vol_j    / sample_prep.pip_i         (J53/I53)
  * sample_prep.vol_h    / sample_prep.sample_weight (H53/G53)
  * sample_prep.avg_weight / lc_<c>                  (F53/G22; G22 = compound LC)
  * standard.potency[idx]                            (F22 = potency, sheet col F)
  * standard.mw_base[idx] / standard.mw_salt[idx]    (H22/I22)
```

Note the sheet column letters shifted vs. Bupivacaine because Ampho's standard
table has fewer columns: on the Ampho sheet **F=Potency, G=LC, H=MW Base, I=MW Salt**
(rows 22–25). `avg_area` is this row's `avg_area` field; `mean_std_<c>` is the
replicate mean for this row's compound. Because the sample table is flat (one
compound per row by index), each row binds a fixed compound — no `cidx`/`coalesce`
selector is needed; use a per-compound expression chosen by the row's index when
building the field list, OR a single expression that indexes `standard.*[(rowno-1)]`
and selects `lc`/`mean_std` by a coalesce on `rowno`. **Chosen: build the field once
and select per-compound terms via a `_assay_expression(idx, prefix)` helper invoked
inside a `coalesce(if(rowno==k+1, <expr k>, blank()), ...)` over k=0..3**, so the LC
context key and the `stats.mean_std_<c>` key (which are not index-addressable) resolve
correctly for each row. This mirrors Bupivacaine's `_compound_select` but keyed on
`rowno` instead of a hidden `cidx` (flat table, exactly 4 rows, so `rowno-1 == idx`).

## Ordered steps

- [ ] 1. Create the new module `a2_ampho_lipid_content.py` with the module docstring,
      `_COMPOUNDS`, defaults, and field-builder helpers (no SeedTemplate yet).
      Define `_COMPOUNDS = [("chol","Cholesterol"), ("alpha","Alpha tocopherol"),
      ("dspg","DSPG"), ("hspc","HSPC")]` (sheet rows 22–25 order). Define
      `_LC_DEFAULTS = {"chol":52, "alpha":0.64, "dspg":81.6, "hspc":213}` (G22..G25) and
      `_STANDARD_DEFAULTS` as `(weight, vol1, pip1, vol2, potency, mw_base, mw_salt)`:
      chol `(21.04,100,1,1,99.68,1,1)`, alpha `(32.6,250,2,100,96.4,1,1)`,
      dspg `(34.64,100,1,1,100,778.07,801.06)`, hspc `(86.14,100,1,1,100,1,1)`.
      Write a thorough sibling-style docstring that: traces each formula to its sheet
      cell (header A5–A17; standard rows 22–25; replicate 29–34 Mean/SD/%RSD 35–37;
      BKT 41–45 pooled Mean/SD/%RSD 46–48; sample prep 53; sample 56–59 incl. E56
      %Assay), states the **2-stage dilution** difference vs Bupivacaine (no pip2/vol3,
      no Conc column), states **why there is no ratio / no cross-set / no 2-SET**
      section (pure content assay), states the **LC-as-context** and **8-criteria**
      decisions, and states **no mid-chain rounding**.
      Files: `d:\RD-instance\GIT\backend-v2\scripts\template_definitions\a2_ampho_lipid_content.py`
      Verify: deferred to step 6 (module not yet importable until TEMPLATES exists);
      `python -c "import ast; ast.parse(open(r'...a2_ampho_lipid_content.py').read())"`
      parses clean.

- [ ] 2. In the same module add the field builders:
      `_standard_fields()` → `name` (text input), `weight`(mg), `vol1`(mL), `pip1`(mL),
      `vol2`(mL), `potency`(%), `mw_base`, `mw_salt` — 2-stage only, NO pip2/vol3/conc_ppm.
      `_standard_default_rows()` → 4 rows from `_STANDARD_DEFAULTS` in `_COMPOUNDS` order.
      `_area_columns()` → one `kind:"area"` column per compound
      `{prefix}_area` with `labelFrom="standard.name[idx]"`.
      `_std_area_fields()` / `_bkt_area_fields()` → `inj_label` (text input) + `_area_columns()`.
      `_stats_fields()` → per compound: `mean_std_<c>`, `sd_std_<c>`, `rsd_std_<c>`
      (= `mean/sd/rsd(std_areas.<c>_area)`), `mean_pool_<c>`, `sd_pool_<c>`,
      `rsd_pool_<c>` (= over `pool(std_areas.<c>_area, bkt_areas.<c>_area)`).
      `_MAX_INJ_ROWS = 10`, replicate default rows 6, BKT default rows 5 (sheet caps),
      min 1.
      Files: `...a2_ampho_lipid_content.py`
      Verify: deferred to step 6.

- [ ] 3. Add the sample-side builders in the same module:
      `_assay_expression(idx, prefix)` returning the exact chain from the plan's
      "Exact %Assay expression" section (uses `standard.*[idx]`, `stats.mean_std_<prefix>`,
      `sample_prep.*`, `lc_<prefix>`, this row's `avg_area`).
      `_sample_fields()` returning: `compound_name` (calculated text,
      `expression="standard.name[(rowno - 1)]"`); `area1` (area, label "Area-1");
      `area2` (area, label "Area-2"); `avg_area` (calculated, `"(area1 + area2) / 2"`,
      sheet D56); `pct_assay` (calculated, unit "%", expression =
      `coalesce(` over k=0..3 of `if(rowno == k+1, _assay_expression(k, prefix_k), blank())` `)`,
      sheet E56). Seed sample areas (step 4 defaults): chol 1955799/1953318,
      alpha 532209/526196, dspg 353084/337734, hspc 964486/958712.
      Files: `...a2_ampho_lipid_content.py`
      Verify: deferred to step 6.

- [ ] 4. Assemble `AMPHO_LIPID_DEFINITION` and the `SeedTemplate` in the same module.
      `resultRef = "samples.pct_assay"`.
      `context = context_header(label_claim=False, avg_weight=False, extra=[...])` with
      overridable text context: `product_name`, `storage_condition`, `packing_detail`,
      `test_name_ctx` ("Test"), `analysis_as_per`, `trf_no`, `ar_no` (sheet A6–A14), plus
      overridable numeric `lc_chol/lc_alpha/lc_dspg/lc_hspc` with `_LC_DEFAULTS`.
      Groups in order:
      (1) `standard` table, `rows {min:1, max:10, default:4, labelFrom:"name"}`,
          fields `_standard_fields()`, seeded via default rows helper if the module
          attaches defaults (follow Bupivacaine: default rows are documented but the
          engine seeds from `rows.default`; include the 4-row default and expose the
          default values as field `default`s OR document them — match Bupivacaine's
          approach of field-level defaults so a fresh worksheet is pre-filled).
      (2) `std_areas` table `{min:1,max:10,default:6,labelFrom:"inj_label"}`,
          `_std_area_fields()`, footer = Mean/SD/%RSD refs to
          `stats.{mean,sd,rsd}_std_{chol,alpha,dspg,hspc}` (12 footer entries).
      (3) `bkt_areas` table `{min:1,max:10,default:5,labelFrom:"inj_label"}`,
          `_bkt_area_fields()`, footer = `stats.{mean,sd,rsd}_pool_{...}`.
      (4) `stats` singleton, `_stats_fields()`.
      (5) `sample_prep` singleton with inputs `avg_weight`(default 1),
          `sample_weight`(mg, default 1), `vol_h`(mL "Vol", default 250),
          `pip_i`(mL "Pip", default 1), `vol_j`(mL "Vol", default 1) — sheet F53..J53.
      (6) `samples` table `{min:4, max:4, default:4}`, `_sample_fields()`, with the 4
          compound rows' Area-1/Area-2 seeded as defaults.
      Criteria: 8 `_rsd_criterion` entries (NMT 2.0 %, blocking) targeting
      `stats.rsd_std_{chol,alpha,dspg,hspc}` and `stats.rsd_pool_{chol,alpha,dspg,hspc}`.
      SeedTemplate: `code="TPL-A2-0005"`, `name="Lipid content Ampho"`, `archetype="A2"`,
      `result_unit="%"`, `test_code="TST-LIPID-AMPHO"`,
      `test_name="Lipid Content (Ampho) by HPLC"`, `test_type="Quantitative"`.
      Export `TEMPLATES = [AMPHO_LIPID_CONTENT]`.
      Files: `...a2_ampho_lipid_content.py`
      Verify: deferred to step 6.

- [ ] 5. Register the module in the package `__init__.py`: add import
      `from scripts.template_definitions.a2_ampho_lipid_content import TEMPLATES as _A2_AMPHO`
      next to the other `a2_*` imports, and splice `*_A2_AMPHO` into `SEED_TEMPLATES`
      immediately after `*_A2_BUPI`.
      Files: `d:\RD-instance\GIT\backend-v2\scripts\template_definitions\__init__.py`
      Verify: deferred to step 6.

- [ ] 6. Validate the whole catalogue (parse + dry-run evaluate) with the project's own
      seed validator — this is the GxP gate the task names.
      Files: none (verification only).
      Verify: from `d:\RD-instance\GIT\backend-v2` run
      `python -m scripts.seed_test_templates --validate-only`
      Expect exit code 0, a line `ok TPL-A2-0005 [A2] ...` listing ~5 groups,
      8 criteria and 10 area fields, and "All definitions valid." with nothing written.
      If any definition is invalid the script prints the offending `TPL-A2-0005 (A2): <error>`
      and exits 1 — fix the module and re-run until clean.

- [ ] 7. Confirm the %Assay numerically reproduces the sheet (GxP correctness check).
      From `d:\RD-instance\GIT\backend-v2`, construct the parsed definition and run
      `WorksheetEvaluator(...).evaluate(context, group_values)` with the seed inputs
      (replicate + BKT areas from rows 29–34/41–45, sample areas from 56–59, prep from 53,
      default LC context), then assert the four `samples.pct_assay` rows round to
      125.30 / 115.10 / 122.70 / 129.86 and the replicate means equal
      1572872.83 / 451519.0 / 290188.17 / 748650.0. A small throwaway script under the
      backend-v2 dir is fine; delete it after. (The validator in step 6 only dry-runs
      with empty inputs, so this step is what proves the formula, not just that it parses.)
      Files: none kept (temporary script removed after use).
      Verify: the printed %Assay values match the four gold numbers above to 2 dp.

## Notes / assumptions

- The sheet's standard table column for Potency is col F and LC is col G (rows 22–25);
  this differs from Bupivacaine's wider layout. The %Assay mapping above already uses
  the Ampho column letters — do not copy Bupivacaine's `H18/G39` offsets verbatim.
- DSPG appears as `DSPG ` (trailing space) and `A24` in the sheet; use clean
  `"DSPG"` as the compound name default (display-only; does not affect arithmetic).
- `test_code="TST-LIPID-AMPHO"` is a NEW Test Master entry created by `ensure_test`;
  do NOT reuse `TST-LIPID-RATIO`.
- Keep strictly additive: only the new module and the two `__init__.py` lines change.
```