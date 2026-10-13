# Verification evidence — Content of Lyso PC / Lyso PG (mg/mL)

GxP verification record for the new seed template reproducing the workbook
`Content of Lyso PC PG_mgmL_Ampho.xlsx` (dump:
`d:\RD-instance\GIT\_dumps\Content of Lyso PC PG_mgmL_Ampho.txt`).

Iteration: **FIRST** (no `review.json` present at task start).

## Chosen identifiers

| Item | Value |
|------|-------|
| Template code | `TPL-A2-0002` (next free, non-colliding code in the A2 family — only `TPL-A2-0001` existed) |
| Template name | `Content of Lyso PC / Lyso PG (mg/mL)` |
| Archetype | `A2` (Multi-Analyte Content by HPLC) — summed sub-peaks per injection against a weighed standard |
| result_unit | `mg/mL` |
| resultRef | `sample_results.pc_mgml` |
| Test Master binding | `TST-LYSO` — `Content of Lyso PC & Lyso PG by HPLC`, type `Quantitative` (created by `ensure_test`; did not previously exist) |

Files added:
`scripts/template_definitions/a2_lyso_content.py` (new module, `TEMPLATES=[LYSO]`),
registered in `scripts/template_definitions/__init__.py` (one import + one splice,
inserted after `*_A2_A3`). No existing template, test, or seeder logic modified.

## Database backup

An existing pre-task backup was present and was **not** overwritten:
`backend-v2/lims.db.bak-lyso-20261013-143012`.

## Commands run and output

### 1. Seeder in validate-only mode (parse + dry-run evaluate, no DB writes)

`python -m scripts.seed_test_templates --validate-only` (from `backend-v2`), exit 0:

```
  ok   TPL-A2-0002 [A2] 6 groups, 20 inputs, 21 area fields, 26 calculated, 4 criteria
  ...(all 22 definitions ok)...
All definitions valid. --validate-only, so nothing was written.
```

### 2. Throwaway check script (reproduce the sheet's stored numbers)

`python -m scripts._verify_lyso` (from `backend-v2`), exit 0. The script loads the
`LYSO` definition, parses it with `TemplateDefinition.parse`, builds `group_values`
from the sheet's example inputs (standard scalars, 6 standard injections, 4
populated + 2 blank BKT injections, sample inj-1 + blank inj-2), runs
`WorksheetEvaluator.evaluate`, and asserts each result against the sheet.

Tolerance: relative `1e-4` for exact values; absolute `0.005` for the four %RSD
values, which the plan quotes at 2-decimal precision.

```
field                              computed           expected  result
stats.mean_std_pc           11468461.500000    11468461.500000  PASS
stats.mean_std_pg            6420652.166667     6420652.170000  PASS
stats.rsd_std_pc                   2.211413           2.210000  PASS
stats.rsd_std_pg                   2.322627           2.320000  PASS
stats.mean_pool_pc          11333895.000000    11333895.000000  PASS
stats.mean_pool_pg           6431312.500000     6431312.500000  PASS
stats.rsd_pool_pc                  2.463418           2.460000  PASS
stats.rsd_pool_pg                  1.898801           1.900000  PASS
sample[0].sum_pc             3012568.000000     3012568.000000  PASS
sample[0].sum_pg             2067344.000000     2067344.000000  PASS
sample[0].pc_mgml                  0.036137           0.036137  PASS
sample[0].pg_mgml                  0.022307           0.022307  PASS
sample[0].pc_assay                 3.613700           3.613700  PASS
sample[0].pg_assay                 2.230700           2.230700  PASS

ALL PASS
```

### 3. Actual seeder (insert Active)

`python -m scripts.seed_test_templates` (from `backend-v2`), exit 0. Among the
templates added:

```
        + Test Master: TST-LYSO — Content of Lyso PC & Lyso PG by HPLC
  add  TPL-A2-0002 [A2] Content of Lyso PC / Lyso PG (mg/mL) -> TST-LYSO
Done. 8 template(s) added, 14 already present.
```

(The database held only part of the catalogue; the seeder, being additive, also
inserted other previously-missing templates. `TPL-A2-0002` is the one in scope.)

Re-running the seeder confirms idempotency (exit 0):

```
  skip TPL-A2-0002 — already present (v1, Active)
Done. 0 template(s) added, 22 already present.
```

### 4. Confirmation query

`python .agents/tasks/lyso-content-template/_q.py` (temporary query, deleted after
capture):

```
--- count of TPL-A2-0002 ---
(1,)
--- new template row (joined to test) ---
('TPL-A2-0002', 'Content of Lyso PC / Lyso PG (mg/mL)', 'A2', 1, 'Active', 'mg/mL', 'seed', 'TST-LYSO', 'Content of Lyso PC & Lyso PG by HPLC', 'Quantitative')
--- TST-LYSO test master ---
('TST-LYSO', 'Content of Lyso PC & Lyso PG by HPLC', 'Quantitative', 'Active', 'seed')
--- all A2 family templates ---
('TPL-A2-0001', 'A2', 'Active')
('TPL-A2-0002', 'A2', 'Active')
```

`TPL-A2-0002` appears **exactly once**, Active, version 1, bound to `TST-LYSO`.
The pre-existing `TPL-A2-0001` row is unchanged (still Active).

## Computed-vs-expected table (all expected numbers)

| Field | Computed | Expected | Pass/Fail |
|-------|----------|----------|-----------|
| Standard mean PC | 11,468,461.5 | 11,468,461.5 | PASS |
| Standard mean PG | 6,420,652.167 | 6,420,652.17 | PASS |
| Standard %RSD PC | 2.2114 | ~2.21 | PASS |
| Standard %RSD PG | 2.3226 | ~2.32 | PASS |
| Pooled BKT mean PC | 11,333,895 | 11,333,895 | PASS |
| Pooled BKT mean PG | 6,431,312.5 | 6,431,312.5 | PASS |
| Pooled BKT %RSD PC | 2.4634 | ~2.46 | PASS |
| Pooled BKT %RSD PG | 1.8988 | ~1.90 | PASS |
| Sample inj-1 Sum Area PC | 3,012,568 | 3,012,568 | PASS |
| Sample inj-1 Sum Area PG | 2,067,344 | 2,067,344 | PASS |
| Reportable inj-1 Lyso PC | 0.036137 mg/mL | 0.036137 mg/mL | PASS |
| Reportable inj-1 Lyso PG | 0.022307 mg/mL | 0.022307 mg/mL | PASS |
| Reportable inj-1 Lyso PC Assay | 3.6137 % | 3.6137 % | PASS |
| Reportable inj-1 Lyso PG Assay | 2.2307 % | 2.2307 % | PASS |

All 14 expected numbers reproduce. The %RSD rows match to the 2-decimal precision
the plan quotes (the computed 4-decimal values round to the expected figures).

## Regression check

`python -m pytest tests/calculation` (from `backend-v2`): **730 passed, 2 failed**.
The two failures are in `tests/calculation/test_worksheet_service.py`
(`test_a_qa_correction_reopens_and_republishes_the_result`,
`test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`) and concern
worksheet-editing / QA-correction permission logic, unrelated to template
definitions. Verified pre-existing: both still fail with the `__init__.py`
registration temporarily reverted (git stash), so they are not caused by this
change.

## Cleanup

- `scripts/_verify_lyso.py` — deleted after capturing output.
- `.agents/tasks/lyso-content-template/_q.py` — deleted after capturing output.
