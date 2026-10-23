# TPL-A12-0003 — Amphotericin B Drug-to-Lipid Ratio — verification note

## Identity / backup

- **Backup filename:** `lims.db.bak-ampho-20261023-234640` (from `backup.txt`; original + backup both 1331200 bytes, size match verified).
- **Next-free A12 code (confirmed):** `TPL-A12-0003`. Pre-seed the DB held only `TPL-A12-0001` and `TPL-A12-0002` (both Active); no `TST-ALDR` test existed. So `TPL-A12-0003` / `TST-ALDR` were both free.
- name = `Amphotericin B — Drug-to-Lipid Ratio`, archetype `A12`, result_unit `None`.
- test_code `TST-ALDR`, test_name EXACTLY `Ampho-lipid to drug ratio`, test_type `Quantitative`.

## Modeling choices

- **Archetype A12 (derived roll-up):** every number is a component assay carried from another test; no injection/standard/area block; the reportable is a computed ratio. Same family as `a12_derived_rollups.py` (`TPL-A12-0002`).
- **Layout:** ONE multi-batch TABLE `batches`, one row per batch (`rows {min:1, max:24, default:3}`, `labelFrom: batch_no`), because the source sheet lists multiple batches — mirrors the sample-table shape, not singletons.
- **LC / content factors:** the four per-component label claims were reverse-engineered from the gold data (`content / assay * 100`, constant across the three batches) and modelled as OVERRIDABLE CONTEXT fields so a lab can adjust them without a new template, mirroring `a2_bupivacaine_lipid_ratio.py`:
  - `lc_chol = 52.0`, `lc_hspc = 213.0`, `lc_dspg = 81.6`, `lc_ampho = 50.0` (all mg/vial).
  - Each content column reads `<c>_assay * lc_<c> / 100`.
- **Formulas:** `Content = Assay% × LC/100`; `lipid_content = chol_content + hspc_content + dspg_content` (three LIPIDS only — Amphotericin B drug EXCLUDED); `drug_lipid_ratio = ampho_content / lipid_content`. **No mid-chain rounding** in any stored expression; the unrounded ratio reproduces every gold ratio to the sheet's 4 dp.
- **resultRef:** `batches.drug_lipid_ratio` — for a multi-row group the engine returns the first non-blank row value (the per-batch reportable), consistent with the other multi-batch templates.
- **Criteria (all 5 BLOCKING), targeted at the batch-row mean** (`mean(batches.<field>)`) — the engine needs a scalar target for a per-row table; this matches how `TPL-A12-0001` targets its carried per-row assay (`mean(preps.pct_assay_total)`):
  - `chol_assay_range` Cholesterol assay between 90.0 and 120.0 %.
  - `hspc_assay_range` HSPC assay between 90.0 and 120.0 %.
  - `dspg_assay_range` DSPG assay between 80.0 and 120.0 %.
  - `ampho_assay_range` Amphotericin B microbial assay between 90.0 and 120.0 %.
  - `drug_lipid_ratio_range` ratio between 0.11 and 0.17 (product acceptance range).
  - The content columns are `N/A` in the sheet → no criterion.

## Gold-value discrepancy (recorded)

The task text's **Amphotericin B content column** prints 55.3200 / 54.3650 / 54.6900, but the formula the task also specifies (`Content = Assay × LC/100`, LC 50.0) gives 55.30 / 54.35 / 54.70, and **only those formula-derived values reproduce the authoritative gold ratios** 0.1511 / 0.1476 / 0.1500:

| batch | ampho assay | formula content (50.0) | task content | ratio with formula | gold ratio |
|-------|-------------|------------------------|--------------|--------------------|------------|
| 10009697 | 110.6 | 55.30 | 55.3200 | 0.1511 | 0.1511 |
| 10010727 | 108.7 | 54.35 | 54.3650 | 0.1476 | 0.1476 |
| 040598M  | 109.4 | 54.70 | 54.6900 | 0.1500 | 0.1500 |

Using 55.32 gives ratio 0.1512 (≠ gold 0.1511). So the content-column figures are transcription slips; the formula + the authoritative ratios are self-consistent. The template implements the specified formula exactly, so this changes nothing the user sees or how the system behaves (same formula, labels, criteria, identity) — no warning raised. The parity test asserts the formula-exact ampho contents (55.30 / 54.35 / 54.70), all three lipid contents, and all three ratios to the sheet's 4 dp, and the choice is documented in the test file.

## Commands run and results

1. **`python -m scripts.seed_test_templates --validate-only`** → **EXIT 0**. All 25 definitions valid; new one listed `ok TPL-A12-0003 [A12] 1 groups, 6 inputs, 0 area fields, 6 calculated, 5 criteria`.

2. **`python -m pytest tests/calculation/test_a12_0003_ampho_parity.py -q`** → **7 passed** (component contents, lipid content excludes drug, ratios, reportable = first batch ratio, passes on gold data, criteria exist with correct limits, ratio criterion fails when out of range).

3. **`python -m scripts.seed_test_templates`** (no `--validate-only`) → **EXIT 0**:
   - `+ Test Master: TST-ALDR — Ampho-lipid to drug ratio`
   - `add  TPL-A12-0003 [A12] Amphotericin B — Drug-to-Lipid Ratio -> TST-ALDR`
   - `Done. 1 template(s) added, 24 already present.` (only the new row inserted; all others skipped as already present.)

4. **DB confirmation query** (sqlite3 on `lims.db`):
   - row count for `TPL-A12-0003`: **1**
   - code `TPL-A12-0003`, name `Amphotericin B — Drug-to-Lipid Ratio`, archetype `A12`, status **Active**, result_unit **None**
   - bound test code `TST-ALDR`, bound test name `'Ampho-lipid to drug ratio'`, **EXACT match: True**, type `Quantitative`
   - `TST-ALDR` count: **1**
   - **canonical-JSON byte-equal (stored definition vs module `SeedTemplate.definition`): True** (`json.dumps(..., sort_keys=True, separators=(',',':'))` on both, compared equal).

5. **`python -m pytest tests/calculation -q`** → **5 failed, 778 passed in 21.65s**. The 5 failures are exactly the KNOWN pre-existing unrelated ones:
   - `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_unit1_release_carryover`
   - `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_per_timepoint_summary`
   - `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_amount_remaining`
   - `test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`
   - `test_worksheet_service.py::test_a_qa_correction_reopens_and_republishes_the_result`
   The new `test_a12_0003_ampho_parity.py` (7 tests) passes within the 778; **no other new failures.**

## Files changed / added

- Added `scripts/template_definitions/a12_ampho_drug_lipid.py` (new module, docstring records LC factors + formula derivations).
- Registered in `scripts/template_definitions/__init__.py` (import `_A12_AMPHO`, appended after `*_A12` in A12 order).
- Added `tests/calculation/test_a12_0003_ampho_parity.py` (parity test).
- New DB rows: `test_templates` TPL-A12-0003 (Active) + `tests` TST-ALDR. No other template/test row disturbed.
- Throwaway helper scripts (`_tmp_check.py`, `_tmp_verify.py`) deleted.
