# Verification — TPL-A6A-0005 v3: extend 6 → 20 sample slots + 20-sample UI

First iteration (no `review.json` present). Implemented from the locked design.

---

## Part A — Backend definition (v3 DRAFT)

### Parity test (authoritative value-neutrality proof)

Command (from `backend-v2`):

```
python -m pytest tests/calculation/test_a6a_0005_leuprolide_parity.py -q
```

Result:

```
.......                                              [100%]
7 passed in 0.20s
```

All 7 gold-value assertions pass unchanged after the 6→20 extension, confirming
the added blank slots 7..20 and the widened stats bracket list are value-neutral.

Known values reproduced (from the test, unchanged):
- **1 Hr block** (areas 203438 / 231282 / 174411):
  - jassay_1/2/3 → 15.00 / 16.58 / 12.70 (2dp of jassay_N)
  - kfrac_1/2/3 (C1) → 0.30 / 0.33 / 0.25
  - unit_1 = 14.996084937889453, unit_2 = 16.579857409503386,
    unit_3 = 12.701419313269414
  - mean = 14.759120553554084, min = 12.701419313269414,
    max = 16.579857409503386, rsd = 13.212490048191508
- **24 Hr block** (area_1 = 681560): jassay_1 ≈ 50.24, kfrac_1 (C1) ≈ 1.00,
  unit_1 (first cumulative add-back) = 50.53995379830622
- **48 Hr block** (area_1 = 1013055): unit_1 (running carry) = 75.98034256289799

### v3 DRAFT definition (applied via API, verified by GET)

Command (from `backend-v2`, backend live on 127.0.0.1:8443):

```
python -m scripts.update_a6a5_v3_definition
```

Result (abridged):

```
base template: id=41 code=TPL-A6A-0005 status=Active version=2
branched v3 Draft: id=44 version=3 status=Draft
definition PUT accepted (200)
v3 Draft verification (id=44):
  [PASS] version == 3 — 3
  [PASS] status == Draft (not approved) — Draft
  [PASS] area_* count == 20 — 20
  [PASS] jassay_* count == 20 — 20
  [PASS] kfrac_* count == 20 — 20
  [PASS] unit_* count == 20 — 20
  [PASS] weights.rows.max == 20 — 20
  [PASS] weights.rows.default == 6 — 6
  [PASS] timepoints_release.rows.max == 10 — 10
  [PASS] resultRef == timepoints_release.mean — timepoints_release.mean
  [PASS] stats.mean aggregates unit_20
  [PASS] stats.min_val aggregates unit_20
  [PASS] stats.max_val aggregates unit_20
  [PASS] stats.rsd aggregates unit_20
  [PASS] jassay_7 uses weights.weight[7 - 1]
  [PASS] jassay_20 uses weights.weight[20 - 1]
OVERALL: PASS (v3 id=44 left as DRAFT)
```

Generated expressions (read back from the stored Draft):

```
jassay_20 = area_20 / std_stats.mean_std * standard.weight_mg / standard.dilution_1
          * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol
          * prep.media_vol / weights.weight[20 - 1] * standard.potency
          * standard.mw_base / standard.mw_salt * prep.avg_weight / prep.label_claim
kfrac_20  = jassay_20 * prep.withdraw_replace / prep.media_vol
unit_20   = jassay_20 + sum(prior.kfrac_20)
mean      = mean([unit_1, ..., unit_20])
rsd       = sd([unit_1, ..., unit_20]) * 100 / mean
```

v3 (template id 44) is left as a **DRAFT** — NOT submitted / approved / e-signed.
The server re-validated the definition (parse + dependency graph) on PUT and
accepted it (HTTP 200), so the dependency graph is sound.

Seed module `scripts/template_definitions/a6a_leuprolide_microsphere.py` was
updated to the 20-slot form (`_SAMPLES = 20`, `_TIMEPOINTS_MAX = 10`,
`weights.rows.max = _SAMPLES`) and is byte-consistent with the definition PUT to
the DB (the script imports `A6A_LEUP_DEFINITION`). The parity test was NOT edited.

---

## Part B — Frontend (add/edit/delete rows UI)

Command (from `frontend-react`):

```
npm run build        # tsc -b && vite build
```

Result: **PASS** — zero TypeScript errors; `✓ built in 3.89s`. The only warning is
the pre-existing "chunks larger than 500 kB" advisory from vite, unrelated to this
change.

ESLint: **not installed** (pre-existing). `npx --no-install eslint --version`
reports eslint is a missing package. This is noted, not a failure.

No dev server / watch mode was started.

Changes are confined to `WorksheetForm.tsx`, gated strictly to
`template_code === 'TPL-A6A-0005' && group.key === 'timepoints_release'`.
