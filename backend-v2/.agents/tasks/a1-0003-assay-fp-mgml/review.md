# TPL-A1-0003 "Assay for finished product mg/ml" — adds mg/mL columns to the FP assay

A new declarative seed module clones the live-only TPL-A1-0002 "Assay for Finished Product" definition and appends the two per-sample columns from `Bupivacaine Assay mg ml & Percentage.xlsx` (sheet '1'): **Assay (mg/mL)** (sheet column Q) and its overall mean **Mean (mg/mL)** (sheet column R). The clone is byte-for-byte equal to the live DB row apart from those additions, binds to a brand-new Test `TST-ASSAY-FP-MGML` rather than reusing TST-03, and keeps the base `% Assay` / `% Mean Assay` logic and the `%` reportable untouched. The mg/mL column is expressed as `pct_assay * label_claim / 100` — algebraically identical to the sheet's full Q chain and reproducing the 2-dp gold.

Watch for: nothing blocking. (confirmed) The implementer's test lives at `test_a1_0003_assay_fp_mgml_parity.py` rather than inside `test_seeded_template_parity.py` as the plan's item 3 described — a harmless location change that is covered by the catalogue-wide invariant tests; the standalone file passes 10/10. (confirmed) The `% Mean Assay` footer stays at 2-dp (103.73) while the sheet displays 1-dp (103.7); this is a deliberate, documented decision to leave the base row unchanged, not a defect.

**Verdict**: APPROVED

## High-level view

The structure mirrors the sheet. The sheet's standard block (rows 13-26), its bracketing/co-relation side tables, and the sample block (row 30 headers A..R) map onto the module's `standard`, `std_areas`, `bkt_1`, `corel_weights`, `corel_areas`, `stats` and `samples` groups. The two new sheet columns Q and R become `samples.assay_mgml` and `stats.mean_mgml`, with Mean (mg/mL) surfaced in the samples footer alongside the retained % Mean Assay — matching the sheet's P/Q/R layout.

The mg/mL formula is the one non-obvious design choice, and it is sound. Sheet Q and sheet O differ only in that O divides by the row L.C. and multiplies potency as K14, while Q divides by 1 and uses K14/100; everything else cancels (MW base/salt = 1). That reduces to Q = O × L.C. / 100, which the module writes as `pct_assay * label_claim / 100`. Because the base `pct_assay` carries no rounding, the engine feeds its full-precision value into this product, so the result equals the full Q chain to floating-point noise and reproduces the 2-dp gold. This mirrors the shipped TPL-A12-0001 convention.

The gold reproduces. % Assay, Assay (mg/mL), % Mean Assay and Mean (mg/mL) were re-derived from the sheet cells and confirmed through the real evaluator: the user's quoted 103.7 → 13.90/13.69 → 13.80 and 99.5 → 13.23 all land, mg/mL to 2-dp and % to the sheet precision.

The registration is clean and isolated. The seeded DB row is byte-equal to the module, TPL-A1-0002 and TST-03 are untouched, the new row binds a fresh Test with the exact mandated name, and the commit touches only the module, the `__init__` splice and the parity test. A DB backup was taken before seeding.

<details>
<summary>Issues (0)</summary>

No blocking or non-blocking action items. One informational note (the `% Mean Assay` 2-dp vs sheet 1-dp display) is a documented, intentional decision and requires no change.

</details>

<details>
<summary>Details</summary>

### Structure maps to the sheet (point 1 — confirmed)

The sheet's Standard Details block (A11, standard row 14 with Wt/Vol/Pip chain, MW, Potency, PPM) corresponds to the `standard` singleton group; the five STD replicate areas B18:B22 with their Mean/SD/%RSD footer map to `std_areas`; the bracketing standard block (D/E/H columns) to `bkt_1`; the STD-2 co-relation weights and areas (L17-M19, Q16:Q17, STD Co-Relation at Q23) to `corel_weights` and `corel_areas`. The sample block header (row 30: Batch No., Stability Condition, Packing Detail, TRF No., AR No., Avg Weight, L.C., Sample Weight, Vol/Pip/Vol, Area-1/Area-2, Avg. Area, % Assay, % Mean Assay, Assay (mg/mL), Mean (mg/mL)) maps onto the `samples` table's `headerContext` plus its per-row fields, with the P/Q/R summary columns surfaced as the `% Mean Assay` and `Mean (mg/mL)` footer refs. Groups, fields and footers correspond to the sheet's columns and blocks.

### The two new formulas trace correctly (point 2 — confirmed)

Sheet O31 = `N/$B$24*$C$14/$D$14*$E$14/$F$14*$G$14/$H$14*K/J*I/H*F/G*$K$14*$I$14/$J$14` and sheet Q31 = `N/$B$24*$C$14/$D$14*$E$14/$F$14*$G$14/$H$14*$I$14/$J$14*I/H*K/J*F/1*$K$14/100`. Cancelling the shared terms (and I14/J14 = MW = 1) leaves exactly two differences: O divides by G (L.C.) where Q divides by 1, and O's potency factor is K14 where Q's is K14/100. Hence Q = O × G / 100 = O × L.C. / 100. The module encodes this as `assay_mgml = pct_assay * label_claim / 100`.

The precision argument holds because the engine applies a field's declared rounding to its own output before feeding it downstream, and `samples.pct_assay` declares no rounding — so `assay_mgml` consumes the full-precision % Assay and the product equals the full Q chain. The parity test's explicit identity assertion (`assay_mgml ≈ pct_assay * 13.3 / 100`, abs 1e-9) passes, and the per-row `assay_mgml` assertions pin the full-chain Q values to abs 1e-6, so the product form is proven equivalent to the sheet's full chain, not merely asserted. `stats.mean_mgml = mean(samples.assay_mgml)` with round 2-dp is the same footer-ref shape as the existing `stats.pct_mean_assay`, giving the sheet's block R-mean across the populated sample rows.

### Gold reproduced through the real evaluator (point 3 — confirmed)

A narrow spot-check (the single new parity file) was run: `pytest tests/calculation/test_a1_0003_assay_fp_mgml_parity.py` → 10 passed. The fixture is the sheet's standard row 14 (Wt 50.59, chain 100/10/50/1/1, MW 1/1, Potency 99.64) and STD areas 2387569/2388066/2392223/2389532/2382677 (mean_std = 2388013.4, asserted). Set-1 (row 31, Sample Wt 0.7621, area 2496042) gives pct_assay 104.48308 → 104.5 and assay_mgml 13.896250 → 13.90; Set-2 (row 33, 0.7469, 2410763) gives 102.96701 → 103.0 and 13.694613 → 13.69; the block means give % Mean Assay 103.73 and Mean (mg/mL) 13.795431 → 13.80 — matching the user's 103.7 → 13.90/13.69 → 13.80. The single-row row35 fixture (0.7646, 2383966) gives 99.46535 → 99.5 and 13.228892 → 13.23, matching the user's quoted 99.5 / 13.23. mg/mL at 2-dp, % at the sheet precision.

### Base % Assay / % Mean Assay unchanged (point 4 — confirmed)

Queried directly against `lims.db`: the `pct_assay` expression in the seeded TPL-A1-0003 definition is string-equal to the one in the live TPL-A1-0002, and the `pct_mean_assay` field is identical including its `round 2 dp` rounding. `resultRef` stays `stats.pct_mean_assay` and the reportable result rides on % Mean Assay (103.73), asserted in the test. The 2-dp `% Mean Assay` vs the sheet's 1-dp display is a deliberate, documented choice to keep the base row unchanged — not a regression.

### Identity, naming and no reuse of TST-03 (point 5 — confirmed)

The `SeedTemplate` declares `name="Assay for finished product mg/ml"`, `archetype="A1"`, `result_unit="%"`, `test_code="TST-ASSAY-FP-MGML"`, `test_name="Assay for Finished Product-mgperml &%"`, `test_type="Quantitative"`. The seeded DB row's bound Test is `('TST-ASSAY-FP-MGML', 'Assay for Finished Product-mgperml &%', 'Quantitative')` with test_id=36, while TPL-A1-0002 remains bound to test_id=3 `TST-03 "Assay (Propofol)"`. TST-03 was not reused; the Test was created fresh via `ensure_test`.

### Seeding isolation and DB parity (point 6 — confirmed)

`json.loads(db_definition) == module.definition` returns True — the stored row is canonical-JSON byte-equal to the module. TPL-A1-0003 is `status=Active`, `archetype=A1`, `result_unit=%`. TPL-A1-0002's name/archetype/unit/status/test binding are unchanged, as is TST-03. The backup record in evidence/verification (`lims.db.bak-a1mgml-20261024-182021`, 1404928 bytes == source) documents the mandatory pre-seed backup.

### Scope (point 7 — confirmed)

Commit `ff6871e` touches exactly three files: `scripts/template_definitions/a1_assay_fp_mgml.py` (new, +180), `scripts/template_definitions/__init__.py` (+2, the import and the `*_A1_FP_MGML` splice after `*_A1`), and `tests/calculation/test_a1_0003_assay_fp_mgml_parity.py` (new, +144), plus the gitignored DB rows. No `_tmp_*.py` source files remain in the tree (only stale `__pycache__` bytecode from earlier-deleted scripts). The `_apply_cu30_kedit.py` stray and the other uncommitted working-tree changes belong to a separate A8/worksheet task, not this one — out of scope here.

### Test suite status (point 8 — read from evidence, not re-run)

verification.md records `pytest tests/calculation` at 5 failed / 826 passed both before and after seeding — identical. The 5 failures are the known pre-existing A6B dissolution and worksheet-service cases, unrelated to this change; the 10 new parity tests are included in the 826 passed. Per the review constraint the full suite was not re-run; the single new parity file was spot-checked and passed 10/10.

</details>

<details>
<summary>File map</summary>

- `scripts/template_definitions/a1_assay_fp_mgml.py` — new seed module: TPL-A1-0002 clone + `samples.assay_mgml`, `stats.mean_mgml`, samples footer Mean (mg/mL).
- `scripts/template_definitions/__init__.py` — imports `_A1_FP_MGML`, splices it into `SEED_TEMPLATES` after `*_A1`.
- `tests/calculation/test_a1_0003_assay_fp_mgml_parity.py` — new hand-derived parity test (10 cases).
- DB (`lims.db`, gitignored) — new rows TPL-A1-0003 (Active) and Test TST-ASSAY-FP-MGML.

Full diff: `git show ff6871e`.

</details>
