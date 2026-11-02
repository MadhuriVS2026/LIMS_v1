# Verification — TPL-A1-0003 "Assay for finished product mg/ml"

Evidence the reviewer can read WITHOUT re-running the suites. Every command was
run from `d:\RD-instance\GIT\backend-v2`.

## Identity
- **A1 code used: `TPL-A1-0003`** (next free A1; A1-0001/0002 already present, both Active).
- Template name EXACTLY `Assay for finished product mg/ml`.
- Bound Test: code `TST-ASSAY-FP-MGML`, name EXACTLY `Assay for Finished Product-mgperml &%`,
  type `Quantitative`, created via `ensure_test` (TST-03 NOT reused).
- archetype `A1`, result_unit `%`, resultRef `stats.pct_mean_assay` (unchanged).

## MANDATORY DB backup (made BEFORE seeding)
- File: `backend-v2\lims.db.bak-a1mgml-20261024-182021`
- Source size 1404928 bytes == backup size 1404928 bytes → **MATCH = True**.

## What changed (only these)
- NEW module `scripts/template_definitions/a1_assay_fp_mgml.py` — clones the live
  TPL-A1-0002 definition verbatim and adds:
  - `samples.assay_mgml` (label "Assay (mg/mL)", unit "mg/mL", expr `pct_assay * label_claim / 100`)
  - `stats.mean_mgml` (label "Mean (mg/mL)", unit "mg/mL", expr `mean(samples.assay_mgml)`, round 2 dp)
  - samples footer entry `('Mean (mg/mL)','stats.mean_mgml')` ALONGSIDE the kept `('% Mean Assay','stats.pct_mean_assay')`.
  - Base `pct_assay` / `pct_mean_assay` and all other groups UNCHANGED.
- `scripts/template_definitions/__init__.py` — imports `_A1_FP_MGML` and splices it
  into `SEED_TEMPLATES` immediately after `*_A1` (A1 order).
- NEW parity test `tests/calculation/test_a1_0003_assay_fp_mgml_parity.py`.
- NEW DB rows: template `TPL-A1-0003` (Active) + Test `TST-ASSAY-FP-MGML` (lims.db, gitignored).

## (1) Parity test — PASS
`python -m pytest tests/calculation/test_a1_0003_assay_fp_mgml_parity.py -q` → **10 passed**.

Gold reproduced (hand-derived from sheet '1' of `Bupivacaine Assay mg ml & Percentage.xlsx`),
confirmed through the real `WorksheetEvaluator`:

| Quantity | Sheet cell | Value | Rounded |
|----------|-----------|-------|---------|
| Mean STD area | B24 | 2388013.4 | — |
| Set-1 % Assay | O31 | 104.48308384718301 | 104.5 |
| Set-1 Assay mg/mL | Q31 | 13.896250151675343 → engine 13.89625015167534 | 13.90 |
| Set-2 % Assay | O33 | 102.9670127290888 | 103.0 |
| Set-2 Assay mg/mL | Q33 | 13.69461269296881 | 13.69 |
| row35 % Assay | O35 | 99.46535083649894 | 99.5 (user gold) |
| row35 Assay mg/mL | Q35 | 13.22889166125436 | 13.23 (user gold) |
| Block % Mean Assay | P31 | 103.7250… → base round-2dp 103.73 | 103.7 (sheet 1 dp) |
| Block Mean mg/mL | R31 | 13.795431422322077 | 13.80 (user gold) |

- Identity check `assay_mgml ≈ pct_assay × 13.3 / 100` holds to ~1e-15 (Q = O × L.C./100).
- Base `% Mean Assay` logic unchanged: `stats.pct_mean_assay` = 103.73, reportable = 103.73.

## (2) Seed validate-only — exit 0
`python -m scripts.seed_test_templates --validate-only` → exit 0, "All definitions valid",
lists `ok TPL-A1-0003 [A1] 7 groups, 18 inputs, 5 area fields, 17 calculated, 0 criteria`
(TPL-A1-0001 shows 15 calculated; +2 = the two new mg/mL fields). Parses + evaluates
empty + fixture via `TemplateDefinition.parse` + `WorksheetEvaluator`.

## (3) Seed into live DB + byte-for-byte parity — PASS
`python -m scripts.seed_test_templates` → `add TPL-A1-0003 … -> TST-ASSAY-FP-MGML`,
`+ Test Master: TST-ASSAY-FP-MGML`, exit 0.

Byte-equality check (throwaway script, since deleted) over `lims.db`:
- `json.loads(db.definition) == module.definition` → **True**.
- template name == module name; archetype match; result_unit `%`; status `Active`.
- bound Test code `TST-ASSAY-FP-MGML`, name EXACTLY `Assay for Finished Product-mgperml &%`, type `Quantitative`.
- **TPL-A1-0002 definition/name/status UNCHANGED**; **TST-03 (Assay (Propofol)) UNCHANGED**.
- Verdict printed: `PARITY OK`.

## (4) Full calculation suite — no new failures
`python -m pytest tests/calculation -q`
- Before seeding: **5 failed, 826 passed** (826 already includes the 10 new parity tests).
- After seeding:  **5 failed, 826 passed** — identical.
- The 5 failures are the known pre-existing ones, unrelated to this change:
  - `TestA6BDissolutionWithReplacement::test_unit1_release_carryover`
  - `TestA6BDissolutionWithReplacement::test_per_timepoint_summary`
  - `TestA6BDissolutionWithReplacement::test_amount_remaining`
  - `test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`
  - `test_worksheet_service.py::test_a_qa_correction_reopens_and_republishes_the_result`

## (5) Cleanup
All `_tmp_*` exploration scripts deleted; worktree adds only the new module, its
`__init__` registration, and the new parity test (plus the gitignored DB rows).

## Commit
- Staged ONLY: `backend-v2/scripts/template_definitions/a1_assay_fp_mgml.py`,
  `backend-v2/scripts/template_definitions/__init__.py`,
  `backend-v2/tests/calculation/test_a1_0003_assay_fp_mgml_parity.py` (lims.db gitignored).
- Commit hash: `ff6871ef12c80cf276b55986b3c03648f312d44e` (short `ff6871e`).
- Not pushed (caller handles release).
