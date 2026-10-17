# Verification — TPL-A2-0004 Bupivacaine Lipid Content & Drug-to-Lipid Ratio

Iteration 1 (no `review.json` present). Implemented from scratch per
`plan.md`. Backend/data only; no frontend changes.

## What was added

- New declarative template module
  `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
  (`TPL-A2-0004`, archetype **A2**, `result_unit = None`), in the same
  declarative style as `a2_lyso_content.py`, reusing `_common.context_header`.
- Registered in `scripts/template_definitions/__init__.py`: imported
  `TEMPLATES as _A2_BUPI` and appended `*_A2_BUPI` to `SEED_TEMPLATES` after the
  other A2 entries.
- Seeded into `lims.db` as the single new template + one new Test Master entry
  `TST-LIPID-RATIO`.

The module is the source of record; the seeded DB row's `definition` JSON equals
the module byte-for-byte (confirmed below).

## Layout / archetype justification (per compound)

- **Compounds as fixed columns/scalars**, not table rows. Each compound's
  `%Assay` (sheet `N39..N42`) divides by that compound's own replicate mean
  (`$B$31..$E$31`) and multiplies by its own standard-detail row (`B18..J18`,
  `B19..`, ...). Fixed columns keep every cross-reference a plain scalar
  (`stats.mean_std_tri`, `standard.tri_weight`), mirroring `a2_lyso_content.py`.
- **Two sheets as groups of one template.** Sheet 2 (`Drug to Lipid ratio Auto
  Calc`) is pure arithmetic over sheet 1's `%Mean` (`H18 = 'Lipid '!O43`), so the
  Drug-to-Lipid group reads the Lipid sample group's `%Mean` directly via
  `lipid_samples.<cmp>_mean[rowno-1]` (batches in the same row order).
- **Archetype A2 / code TPL-A2-0004.** Dominant work is a 4-lipid HPLC content
  assay with weighed standard + replicate + pooled-bracketing suitability +
  per-compound %Assay — the A2 family. Next free code after TPL-A2-0001..0003.
  A12 ("derived roll-ups") was rejected as the home because A12's inputs are
  carried from other tests with no injections; here the content is computed from
  the worksheet's own injections. `TPL-A12-0002` / `TST-DLR` were NOT touched.
- **No mid-chain rounding** — the sheet wraps formulas in `IFERROR` but applies
  no explicit `ROUND`; rounding mid-chain would perturb the gold values.
- **SST:** eight blocking `%RSD NMT 2.0 %` criteria (replicate + pooled, per the
  4 compounds), matching the sibling A2 convention; the sheet prints no numeric
  limit, so only `limit`/`limitText` change if the lab later supplies one.

## Safety — DB backup

Backup present before any write:
`backend-v2/lims.db.bak-lipid-20261017-222441` (confirmed; made by the setup
step). No additional backup was required.

## Commands run and results

### 1. Module registered in catalogue

```
python -c "from scripts.template_definitions import SEED_TEMPLATES; print([t.code for t in SEED_TEMPLATES if t.code=='TPL-A2-0004'])"
-> ['TPL-A2-0004']
```

### 2. Seeder `--validate-only` (parse + dry-run evaluate every template)

```
python -m scripts.seed_test_templates --validate-only
```

Exit 0. `TPL-A2-0004` validated:

```
  ok   TPL-A2-0004 [A2] 6 groups, 48 inputs, 16 area fields, 47 calculated, 8 criteria
All definitions valid. --validate-only, so nothing was written.
```

No `INVALID DEFINITIONS`.

### 3. Seeder real insert (Active)

```
python -m scripts.seed_test_templates
```

Exit 0:

```
        + Test Master: TST-LIPID-RATIO — Lipid Content & Drug-to-Lipid Ratio by HPLC
  add  TPL-A2-0004 [A2] Bupivacaine Lipid Content & Drug-to-Lipid Ratio -> TST-LIPID-RATIO
  ...
Done. 1 template(s) added, 23 already present.
```

### 4. Idempotency (second run skips)

```
python -m scripts.seed_test_templates
-> skip TPL-A2-0004 — already present (v1, Active)
-> Done. 0 template(s) added, 24 already present.
```

### 5. DB state confirmed (exactly once; row == module; nothing else changed)

```
row count for TPL-A2-0004: 1
code/name/arch/unit/status/approver: TPL-A2-0004 | Bupivacaine Lipid Content & Drug-to-Lipid Ratio | A2 | None | Active | seed
definition equals module: True
total templates: 35   (was 34, +1)
total tests: 32       (was 31, +1)
TST-LIPID-RATIO: ('TST-LIPID-RATIO', 'Lipid Content & Drug-to-Lipid Ratio by HPLC', 'Quantitative', 'Active')
```

### 6. Backend test suite

```
python -m pytest -q
-> 5 failed, 757 passed
```

The 4 catalogue parity checks for the new template pass:

```
python -m pytest -q tests/calculation/test_seeded_template_parity.py -k "A2-0004"
-> 4 passed, 244 deselected
```

**The 5 failures are PRE-EXISTING and unrelated to this change.** They are:

- `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement` (3) —
  depend on `TPL-A6B-0001` / the uncommitted `a6_dissolution.py` edit from a
  prior step, not on any A2 template.
- `test_worksheet_service.py` (2) — worksheet editability-state tests, no
  relation to template definitions.

Proof: with this task's `__init__.py` registration temporarily `git stash`ed
(so `TPL-A2-0004` is absent from the catalogue), the identical 5 tests still
fail (`5 failed, 1 passed`). The stash was restored afterward. The working tree
already carried these unrelated uncommitted changes (`a6_dissolution.py`,
several `frontend-react/...` files) before this step began.

## Gold-value verification (throwaway `_verify.py`, since deleted)

The throwaway script loaded `LIPID_RATIO_DEFINITION`, fed the full per-compound
area matrix (std 6×4, bkt 4×4) and all three batches, ran `WorksheetEvaluator`,
and asserted the gold values. **All 18 assertions PASS.**

| Quantity | Computed | Expected | Tol | Pass |
|---|---|---|---|---|
| Conc ppm Tricaprylin | 118.92 | 118.92 | 0.01 | PASS |
| Conc ppm DPPG | 54.0343 | 54.0343 | 0.001 | PASS |
| Conc ppm Cholesterol | 285.1 | 285.1 | 0.1 | PASS |
| Conc ppm DEPC | 489.254 | 489.2544 | 0.001 | PASS |
| Replicate Mean Tricaprylin | 8691453.5 | 8691453.5 | 0.1 | PASS |
| Replicate Mean DPPG | 4461370.5 | 4461370.5 | 0.1 | PASS |
| Replicate Mean Cholesterol | 32403414.83 | 32403414.83 | 0.5 | PASS |
| Replicate Mean DEPC | 44013385.5 | 44013385.5 | 0.1 | PASS |
| Pooled Mean Tricaprylin | 8699733.9 | 8699733.9 | 0.1 | PASS |
| Pooled %RSD Tricaprylin | 0.238252 | 0.2383 | 0.0005 | PASS |
| Batch B %Assay Tricaprylin | 99.979 | 99.979 | 0.01 | PASS |
| Batch B %Assay DPPG | 86.2004 | 86.200 | 0.01 | PASS |
| Batch B %Assay Cholesterol | 101.772 | 101.772 | 0.01 | PASS |
| Batch B %Assay DEPC | 100.39 | 100.390 | 0.01 | PASS |
| Batch B mg/mL(Lipid) Tricaprylin | 1.99958 | 1.99958 | 0.0001 | PASS |
| Batch B Sum of Lipid | 15.790645 | 15.790645 | 0.0001 | PASS |
| Batch B mg/mL Bupivacaine | 13.2867 | 13.2867 | 0.001 | PASS |
| Batch B Drug/Lipid Ratio | 0.841429 | 0.841429 | 1e-05 | PASS |

All three batches (full computed-vs-expected table; batches C and A are not
pre-gated — printed for generalisation evidence):

| Batch | %Mean Tri | %Mean DPPG | %Mean Chol | %Mean DEPC | mg/mL Tri | Sum Lipid | mg/mL Bupi | Ratio |
|---|---|---|---|---|---|---|---|---|
| EP20_117-299-B | 99.979 | 86.2004 | 101.772 | 100.39 | 1.99958 | 15.7906 | 13.2867 | 0.841429 |
| EP20_117-299-C | 97.9437 | 93.9761 | 101.393 | 99.5972 | 1.95887 | 15.7371 | 13.0074 | 0.826543 |
| EP20_117-299-A | 100.219 | 84.0742 | 101.808 | 98.488 | 2.00439 | 15.622 | 13.3399 | 0.853916 |

Reportable result (`resultRef = drug_lipid.ratio`, last non-blank row) =
`0.8414285851744482`.

**Overall: ALL GOLD VALUES REPRODUCE — PASS.** The throwaway `_verify.py` and
`_dbcheck.py` were deleted after this evidence was recorded; `plan.md`,
`verification.md`, and `verification-output.txt` remain as the evidence trail.
