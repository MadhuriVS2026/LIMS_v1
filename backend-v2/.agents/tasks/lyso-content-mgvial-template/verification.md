# Verification — TPL-A2-0003 "Content of Lyso PC / Lyso PG (mg/vial)"

GxP parity evidence for the new mg/vial seed template, reproducing
`d:\RD-instance\GIT\Test types\Content of Lyso PC PG_ mgvial_Ampho.xlsx`.

## What was run

1. `python -m scripts.seed_test_templates --validate-only`
   → TPL-A2-0003 parses and dry-runs; "All definitions valid." (23 definitions).
   TPL-A2-0003 reports `6 groups, 20 inputs, 21 area fields, 26 calculated,
   4 criteria` — byte-identical shape to TPL-A2-0002.

2. Throwaway parity check (`_verify_lysovial.py`, since deleted) that loads the
   stored TPL-A2-0003 definition, feeds the sheet's example inputs via
   `WorksheetEvaluator`, and asserts the sheet's stored (data_only) values. The
   bracketing-injection sums were transcribed from the workbook rows 40–43
   (L40..L43 / M40..M43); rows 44–45 are blank on the sheet.

3. `python -m pytest tests/calculation/test_seeded_template_parity.py -q`
   → 242 passed (includes the new `TestA2LysoContentMgVial` class and all
   catalogue-wide invariants).

4. `python -m pytest tests/calculation -q`
   → 742 passed, 2 failed. The 2 failures
   (`test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`,
   `::test_a_qa_correction_reopens_and_republishes_the_result`) are PRE-EXISTING
   on the clean baseline (confirmed by stashing the change and re-running) and
   concern worksheet-locking logic, not the template catalogue. No regression
   from this change.

5. Backed up `lims.db` → `lims.db.bak-lysovial-20261013164543`, then
   `python -m scripts.seed_test_templates` → `add TPL-A2-0003 ... -> TST-LYSO`,
   all other 22 skipped, no new TST-LYSO Test created. DB confirms exactly one new
   row: `('TPL-A2-0003','Content of Lyso PC / Lyso PG (mg/vial)','A2','mg/vial',
   'Active','seed')`, bound to the existing TST-LYSO (id 24).

## Example inputs

- Standard: PC weight 17.547 / vol1 50 / pip 4 / vol2 20 / mw_base 1 / mw_salt 1 /
  potency 98 / lc 1. PG weight 18.411 / vol1 100 / pip 4 / vol2 20 / mw_base 511.61
  / mw_salt 534.6 / potency 98.3 / lc 1.
- Standard injection sums (PC): 11627818, 11766470, 11359907, 11205243, 11178008,
  11673323. (PG): 6413351, 6624511, 6243373, 6564217, 6385523, 6292938.
- Bracketing injection sums (PC): 11366840, 11161713, 10906605, 11093023.
  (PG): 6569572, 6393008, 6389790, 6436842.
- Sample prep: mL 10, Vol 200, Pip 10, Vol2 20. vial_factor 12.5.
- Sample injection 1 sums: PC 3012568, PG 2067344.

## Computed vs expected

| Check                | Computed        | Expected (sheet) | Result |
|----------------------|-----------------|------------------|--------|
| PC meanStd (L34)     | 11468461.500000 | 11468461.5       | PASS   |
| PG meanStd (M34)     | 6420652.166667  | 6420652.166667   | PASS   |
| PC %RSD (L36)        | 2.211413        | 2.2114 (~2.21)   | PASS   |
| PG %RSD (M36)        | 2.322627        | 2.3226 (~2.32)   | PASS   |
| PC pooled mean (L46) | 11333895.000000 | 11333895         | PASS   |
| PG pooled mean (M46) | 6431312.500000  | 6431312.5        | PASS   |
| PC pooled %RSD (L48) | 2.463418        | 2.4634 (~2.46)   | PASS   |
| PG pooled %RSD (M48) | 1.898801        | 1.8988 (~1.90)   | PASS   |
| sample inj1 PC (L57) | 3012568.000000  | 3012568          | PASS   |
| sample inj1 PG (M57) | 2067344.000000  | 2067344          | PASS   |
| Lyso PC mg/vial (C61)| 9.034220        | 9.034219643511904| PASS   |
| Lyso PG mg/vial (D61)| 5.576665        | 5.5766651873236  | PASS   |
| Lyso PC Assay % (E61)| 903.422000      | 903.4219643511904| PASS   |
| Lyso PG Assay % (F61)| 557.666500      | 557.6665187323599| PASS   |

Additional assertions:
- `vial_factor` is live and overridable: setting it to 1.0 yields PC 0.722738,
  PG 0.446133 — the x12.5 result divided by 12.5 (within 6-digit rounding). The
  factor is referenced bare as `* vial_factor`, never a buried literal.
- Standard SST %RSD criteria legitimately FAIL on this data
  (`has_blocking_failure is True`), because the sheet's own %RSD values 2.21/2.32
  exceed the NMT 2.0 % limit — the test pins the failure, it does not claim a
  clean pass.

ALL CHECKS PASS.
