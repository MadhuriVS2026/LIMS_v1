# TPL-A2-0004 — "% Mean each compound" additive summary block

Iteration 1 (no prior `review.json` existed).

## What was added (PURELY ADDITIVE — one new group)

A new read-only `table` group `mean_each_compound` (label "% Mean each
compound"), placed in the `groups` list IMMEDIATELY AFTER `lipid_samples` so the
generic frontend renders it as a labeled 4-row block directly BELOW the Sample
Details (Set 2) block.

Chosen shape: **table, fixed at exactly 4 rows** (`rows` pinned
`{min:4, max:4, default:4}`), one row per compound in `_COMPOUNDS` order
(row 0 Tricaprylin, 1 DPPG Na, 2 Cholesterol, 3 DEPC). The compound index is the
row position `rowno - 1` (0..3) — four rows, one per compound, so no `cidx`-style
modulo is needed. Three columns:

1. `compound_name` (calculated, text) = `standard.name[(rowno - 1)]` — auto-fetched
   from Standard Details, the same mechanism `lipid_samples.compound_name` uses.
2. `set_source` (calculated, text) = the string literal `'Average of set1 and set2'`.
   The engine evaluates a bare STRING token to that string (expression.py
   `_Literal`), so a calculated text field whose expression is the quoted
   constant renders identical fixed descriptive text on every row — engine-faithful,
   no input/default.
3. `pct_mean` (calculated, unit "%") =
   `mean([ lipid_samples.pct_assay[(rowno - 1)], lipid_samples.pct_assay[(rowno - 1) + 4] ])`
   — the cross-set mean of that compound's % Assay in Set 1 (lipid_samples row idx)
   and Set 2 (row idx+4), blank-skipping. NO rounding.

Nothing else changed: `lipid_samples` fields, `pct_mean`, `pct_assay`, `cidx`,
`standard`, `std_areas`, `bkt_areas`, `stats`, context, the 8 SST criteria and
`drug_lipid` are untouched. The new group feeds NO downstream formula (drug_lipid
still reads `lipid_samples.pct_mean` directly), so the per-set pct_mean and the
drug/lipid ratio are unchanged.

## Engine proof — no circular dependency

`referenced_paths("mean([ lipid_samples.pct_assay[(rowno - 1)], lipid_samples.pct_assay[(rowno - 1) + 4] ])")`
= `{('rowno',), ('lipid_samples', 'pct_assay')}`

The new field depends only on `lipid_samples.pct_assay` (a DIFFERENT group) —
the same cross-group absolute-index pattern `drug_lipid` already uses — with no
self/back reference, so the topological sort has no cycle. Confirmed by a clean
`evaluate()` (below) raising no EvaluationError.

## MANDATORY DB backup

`lims.db` copied to `lims.db.bak-a2meanblock-20261023-230342` (see `backup.txt`);
orig 1331200 bytes == copy 1331200 bytes.

## seed --validate-only

Exit code **0**. TPL-A2-0004 now reports `7 groups ... 40 calculated` (was 6
groups / 37 calculated: +1 group, +3 calculated for the three new columns). All
24 definitions valid.

## Fixture evaluations (real WorksheetEvaluator)

### Set-1-only fixture (Set 2 blank)
New block `% Mean each compound`:
| row | compound_name | set_source | pct_mean | rounds to |
|-----|---------------|------------|----------|-----------|
| 0 | Tricaprylin | "Average of set1 and set2" | 99.9790012647194 | 99.98 |
| 1 | DPPG Na | "Average of set1 and set2" | 86.20038794286894 | 86.20 |
| 2 | Cholesterol | "Average of set1 and set2" | 101.77242947915475 | 101.77 |
| 3 | DEPC | "Average of set1 and set2" | 100.38972196375907 | 100.39 |

Each = mean of a single Set-1 value (Set 2 blank, skipped) = that compound's
Set-1 % Assay. Existing gold preserved: per-set `lipid_samples.pct_mean` =
[99.979001, 86.200388, 101.772429, 100.389722]; drug/lipid ratio
0.8414285851744482 → **0.841429** (gold); reportable 0.841429.

### Both-sets fixture (Set 2 DIFFERENT areas: tri 8650000 / dppg 3900000 / chol 32000000 / depc 44500000)
`lipid_samples.pct_assay` Set 1 = [99.979001, 86.200388, 101.772429, 100.389722];
Set 2 = [99.067648, 87.863142, 100.286346, 100.990233].

Hand-derived oracle (mean of Set1 & Set2 per compound):
| compound | (Set1 + Set2)/2 | expected | evaluator |
|----------|------------------|----------|-----------|
| Tricaprylin | (99.979001 + 99.067648)/2 | 99.523324 | 99.52332444437062 |
| DPPG Na | (86.200388 + 87.863142)/2 | 87.031765 | 87.03176475875566 |
| Cholesterol | (101.772429 + 100.286346)/2 | 101.029388 | 101.02938757343864 |
| DEPC | (100.389722 + 100.990233)/2 | 100.689977 | 100.6899772724399 |

All match. Per-set `lipid_samples.pct_mean` set1 STILL [99.979001, 86.200388,
101.772429, 100.389722] (reads row's own Set-1 % Assay, unchanged); drug/lipid
ratio STILL 0.8414285851744482 → 0.841429 (the new block does not perturb it).

## DB row 35 byte-equality (after sync)
See `db_equality.txt` — identity (35, TPL-A2-0004, v1, Active) unchanged;
exact_equal True; normalized_equal True.

## pytest tests/calculation
See `pytest.txt` — same 5 known pre-existing unrelated failures (A6B +
worksheet_service), no new ones; the extended parity test passes.
