# Verification — Dissolution-Leuprolide-microsphere (TPL-A6A-0005, archetype A6a)

First iteration (no `build-review.json` existed). Implemented from the approved
`plan.md` / `design.md` / `trace.md`. All commands run from `backend-v2/`.

## Artifacts added / changed (scope-confined)

- **NEW** `scripts/template_definitions/a6a_leuprolide_microsphere.py` — the full
  TPL-A6A-0005 definition + `SeedTemplate` tail.
- **MODIFIED** `scripts/template_definitions/__init__.py` — 2 lines: the import
  `... import TEMPLATES as _A6A_LEUP` and the `*_A6A_LEUP` splice, placed
  immediately after `*_A6` and before `*_A6B_OCT` (`git diff --stat` = 2 insertions).
- **NEW** `tests/calculation/test_a6a_0005_leuprolide_parity.py` — parity test.
- **DB rows** in `lims.db` (gitignored — `git check-ignore lims.db` returns
  `lims.db`): one new template row + one new Test Master row.
- No throwaway scripts remain (the single `_tmp_verify_seed.py` inspection helper
  was deleted). `git status` under `backend-v2/` shows only the three source
  artifacts above among my changes; the other untracked `.agents/` /
  `_apply_cu30_kedit.py` / `tests/resource/` entries are pre-existing and NOT mine.

## 1. Parse + engine dry-run (`--validate-only`) — exit 0

`python -m scripts.seed_test_templates --validate-only` → **EXIT=0**, no
`INVALID DEFINITIONS` section. The new line reported:

```
ok   TPL-A6A-0005 [A6a] 9 groups, 21 inputs, 8 area fields, 33 calculated, 1 criteria
```

This parses `A6A_LEUP_DEFINITION` and dry-runs
`WorksheetEvaluator(parsed).evaluate({}, {})` on the empty context alongside all
29 catalogue definitions — all `ok`.

Registration check:
`python -c "from scripts.template_definitions import SEED_TEMPLATES; print([t.code for t in SEED_TEMPLATES if t.code=='TPL-A6A-0005'])"`
→ `['TPL-A6A-0005']` (exactly once).

## 2. Parity test — PASS (every gold value, to sheet full precision)

`python -m pytest tests/calculation/test_a6a_0005_leuprolide_parity.py -q`
→ **7 passed in 0.14s**. The fixture feeds the sheet's own inputs through
`WorksheetEvaluator(TemplateDefinition.parse(A6A_LEUP_DEFINITION)).evaluate(...)`.
Asserted gold values (trace §5):

- `standard.conc_ppm` (I19) = 78.726628
- `std_stats`: mean_std (B27) = 1108203.6; sd_std (B28) = 719.9265934801964;
  rsd_std (B29) = 0.06496338700579897; pooled mean_bkt (D27) = 1102713.9;
  sd_bkt (D28) = 6388.745720231615; rsd_bkt (D29) = 0.5793656650407342
- `weight_stats` (STDEV-includes-mean quirk, n=4): mean_wt (F28) = 49.833333333333336;
  sd_wt (F29) = 0.569229498728081; rsd_wt (F30) = 1.1422665526316007
- **1 Hr block (no carry, C=J):** unit_1 (C40) = 14.996084937889453 from B40=203438;
  unit_2 (C41) = 16.579857409503386; unit_3 (C42) = 12.701419313269414;
  block mean (D40) = 14.759120553554084; min (E40) = 12.701419313269414;
  max (F40) = 16.579857409503386; rsd (G40) = 13.212490048191508
- **24 Hr block (first add-back):** unit_1 (C46) = 50.53995379830622 = J46 + L46 (L46 = K40)
- **48 Hr block (running carry):** unit_1 (C52) = 75.98034256289799 = J52 + L52 (L52 = K46 + L46)
- SST criterion present: target `std_stats.rsd_std`, operator `lte`, limit `(2.0,)`,
  severity `blocking`.

The C40=J40 / C46 / C52 assertions are the carry-critical cases — they fail loudly
if the non-recursive `unit_u = jassay_u + sum(prior.kfrac_u)` chain ever collapses to 0.

## 3. Full calculation gate — no new failures, pre-existing 5 unchanged

`python -m pytest tests/calculation -q` → **5 failed, 837 passed in 53.21s**.
The 5 failures are exactly the known pre-existing unrelated ones from `plan.md`:

```
FAILED tests/calculation/test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_unit1_release_carryover
FAILED tests/calculation/test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_per_timepoint_summary
FAILED tests/calculation/test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_amount_remaining
FAILED tests/calculation/test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf
FAILED tests/calculation/test_worksheet_service.py::test_a_qa_correction_reopens_and_republishes_the_result
```

The new parity test is included in the 837 passed; no other new failures.

## 4. Seed into live DB — one new Active row, idempotent

`python -m scripts.seed_test_templates` → **EXIT=0**:

```
+ Test Master: TST-DISS-LEUP-MS — Dissolution-Leuprolide-microsphere
add  TPL-A6A-0005 [A6a] Dissolution-Leuprolide-microsphere -> TST-DISS-LEUP-MS
Done. 1 template(s) added, 28 already present.
```

Re-run → `skip TPL-A6A-0005 — already present (v1, Active)` / `Done. 0 added, 29
already present.` (idempotent).

## 5. DB integrity + non-disturbance

Read-only inspection of `lims.db` (throwaway helper since deleted):

```
ROWS_WITH_NAME = 1
code TPL-A6A-0005 | arch A6a | v 1 | status Active | unit %
bound test: TST-DISS-LEUP-MS | Dissolution-Leuprolide-microsphere | Quantitative
BYTE_EQUAL_CANONICAL = True
ACTIVE_0005_COUNT = 1
A6A-0002 (must be undisturbed): {'id': 22, 'code': 'TPL-A6A-0002',
  'name': 'Dissolution sheet_ without replacement_ QC release-6',
  'version': 1, 'status': 'Active', 'test_id': 22}
A6A-0002 bound test: {'id': 22, 'code': 'TST-DISS-QC', 'name': 'Dissolution',
  'type': 'Quantitative'}
```

- Exactly ONE Active row named `Dissolution-Leuprolide-microsphere` = TPL-A6A-0005,
  A6a, v1, result_unit `%`, bound to the new Test `TST-DISS-LEUP-MS` /
  `Dissolution-Leuprolide-microsphere` / Quantitative.
- Stored `definition` canonical JSON (`json.dumps(..., sort_keys=True)`) is
  **byte-equal** to the module's `A6A_LEUP_DEFINITION`.
- TPL-A6A-0002 (id 22, Test `TST-DISS-QC`/`Dissolution`) is unchanged (same
  version/status/test binding). DB backup `lims.db.bak-leuprolide-20261024-220422`
  (1,433,600 bytes) present.

## Notes

- Archetype kept `A6a` (matches the base family) despite the base's "without
  replacement" name; the sheet actually carries a live cumulative replacement
  add-back and the module reproduces it. This discrepancy is documented in the
  module docstring so it is not "corrected" away.
- Carry uses the non-recursive `sum(prior.kfrac_u)` form (the DB-pinned
  TPL-A6A-0004 pattern), not a recursive `prev.carry`, which `_evaluation_order`
  would leave unordered and could silently collapse to 0.
