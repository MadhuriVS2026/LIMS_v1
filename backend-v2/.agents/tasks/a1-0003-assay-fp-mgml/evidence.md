# Evidence — TPL-A1-0003 "Assay for finished product mg/ml"

Hand-derivations of every gold value from the authoritative sheet dump
`d:\RD-instance\GIT\_dumps\Bupivacaine Assay mg ml _ Percentage.txt`
(sheet '1', `Bupivacaine Assay mg ml & Percentage.xlsx`). All derivations were
reproduced two ways: (1) direct arithmetic from the sheet's cell formulas, and
(2) through the real `WorksheetEvaluator` on a prototype of the extended
definition. Both agree to full floating-point precision.

## 1. Source cells and the two column formulas

Per-sample columns on the sheet (headers at row 30):

| Col | Header            | Sheet formula (row 31 shown; others identical by row) |
|-----|-------------------|-------------------------------------------------------|
| N   | Avg. Area         | `=AVERAGE(L31:M32)`  (Area-1/Area-2; blank→skipped)   |
| O   | % Assay           | `N31/$B$24*$C$14/$D$14*$E$14/$F$14*$G$14/$H$14*K31/J31*I31/H31*F31/G31*$K$14*$I$14/$J$14` |
| P   | % Mean Assay      | `=AVERAGE(O31:O34)` (block)                            |
| Q   | Assay (mg/mL)     | `N31/$B$24*$C$14/$D$14*$E$14/$F$14*$G$14/$H$14*$I$14/$J$14*I31/H31*K31/J31*F31/1*$K$14/100` |
| R   | Mean (mg/mL)      | `=AVERAGE(Q31:Q34)` (block)                            |

Legend (per-row cells): F = Avg Weight, G = L.C. (13.3), H = Sample Weight,
I = Vol, J = Pip, K = Vol; N = Avg. Area.
Standard (fixed, `$`-anchored, row 14): C14 = 50.59 (Wt), D14/E14/F14/G14/H14 =
100/10/50/1/1 (Vol/Pip chain), I14/J14 = 1/1 (MW base/salt), K14 = 99.64
(Potency). B24 = mean of STD areas.

### Algebraic relation O vs Q

O = `… * K/J * I/H * F/G * $K$14 …`
Q = `… * $I$14/$J$14 * I/H * K/J * F/1 * $K$14/100`

Dropping the terms common to both (and I14/J14 = 1), the ONLY differences are:
- O divides by **G** (L.C.); Q divides by **1**.
- O multiplies potency as **$K$14**; Q as **$K$14/100**.

Therefore **Q = O × G / 100 = O × L.C. / 100**. Confirmed numerically below
(difference ≈ 3.6e-15, i.e. floating-point noise).

## 2. Standard mean area (B24)

`B24 = AVERAGE(B18:B22)` over STD areas 2387569, 2388066, 2392223, 2389532,
2382677.

**B24 = 2,388,013.4** (source cells B18:B22, B24).

## 3. Per-sample gold values (hand-derived, source cells noted)

All rows share standard row 14 and F=1.005, G=13.3, I=100, J=1, K=1.

### Set-1 — sheet row 31 (`EP20_117-307`, Set-1)
Inputs: H (Sample Wt) = 0.7621, Area-1 = 2496042 (Area-2 blank ⇒ N = 2496042).
- **O31 (% Assay) = 104.48308384718301 → 104.5** (1 dp). Source: O31.
- **Q31 (Assay mg/mL) full chain = 13.896250151675343 → 13.90** (2 dp). Source: Q31.
- Via O: `O31 × 13.3 / 100 = 13.89625015167534`. Diff vs full Q = 3.55e-15.

### Set-2 — sheet row 33 (`EP20_117-307`, Set-2)
Inputs: H = 0.7469, Area-1 = 2410763.
- **O33 (% Assay) = 102.9670127290888 → 103.0** (1 dp). Source: O33.
- **Q33 (Assay mg/mL) = 13.69461269296881 → 13.69** (2 dp). Source: Q33.

### row 35 (`EP20_117-295`, 2-8°C 180 Days) — the user's quoted "99.5 / 13.23"
Inputs: H = 0.7646, Area-1 = 2383966.
- **O35 (% Assay) = 99.46535083649894 → 99.5** (1 dp). Source: O35. ✔ matches user gold.
- **Q35 (Assay mg/mL) = 13.22889166125436 → 13.23** (2 dp). Source: Q35. ✔ matches user gold.

## 4. Block means (P / R columns) — the user's quoted "103.7 → 13.80"

The sheet averages O and Q over a 4-row block (`P31=AVERAGE(O31:O34)`,
`R31=AVERAGE(Q31:Q34)`); within a block only the two populated sample rows
(Set-1 row 31, Set-2 row 33) carry data, so the block average = mean of those two.

- **% Mean Assay = mean(O31, O33) = 103.7250482881359 → 103.7** (1 dp). Source: P31. ✔ user gold.
- **Mean (mg/mL) = mean(Q31, Q33) = 13.795431422322077 → 13.80** (2 dp). Source: R31. ✔ user gold
  (user: injections ~13.90/13.69 ⇒ mean 13.80).

Cross-check of the user's second quoted figure: % 99.5 ⇒ 99.5 × 13.3/100 = **13.23**. ✔

## 5. Prototype through the real `WorksheetEvaluator`

Extended the live TPL-A1-0002 definition with `samples.assay_mgml =
pct_assay * label_claim / 100` and `stats.mean_mgml = mean(samples.assay_mgml)`
(round 2 dp), then evaluated with the Set-1 + Set-2 fixture:

```
mean_std        = 2388013.4
row0 pct_assay  = 104.48308384718301   assay_mgml = 13.89625015167534
row1 pct_assay  = 102.9670127290888    assay_mgml = 13.69461269296881
pct_mean_assay  = 103.73   (base rounds 2 dp)   mean_mgml = 13.8
```
Single-row row35 fixture: `pct_assay = 99.4653… → 99.5`, `assay_mgml =
13.2288… → 13.23`.

### Why `assay_mgml = pct_assay * label_claim / 100` (not the full Q chain)
The engine applies a calculated field's declared rounding to its own result and
feeds the **rounded** value downstream (`evaluator._apply_rounding`). The base
`samples.pct_assay` declares **no** rounding, so `assay_mgml` reads the full-
precision % Assay and the product equals the full Q chain to ~1e-15. This form
is chosen because it is algebraically identical, loses no precision, reproduces
the sheet's 2-dp mg/mL gold exactly, and mirrors the already-shipped TPL-A12-0001
convention ("Bupivacaine (mg/mL) = %AssayBup × L.C. / 100", worklog
2026-10-15). Had `pct_assay` carried mid-chain rounding, the full Q chain would
have been required instead.

### Note on % Mean Assay rounding (2 dp vs sheet 1 dp)
`stats.pct_mean_assay` carries `round 2 dp` in the live TPL-A1-0002 (reportable =
103.73). The sheet's P column displays 1 dp (103.7). The task mandates keeping
the base `pct_assay`/`pct_mean_assay` UNCHANGED, so 2-dp is retained for parity
with the live base row; `mean_mgml` matches it with `round 2 dp` (13.80).

## 6. Registration facts (live DB `backend-v2\lims.db`)
- A1 codes present: **TPL-A1-0001**, **TPL-A1-0002** (both `Active`, `test_id=3`).
  Next free A1 code = **TPL-A1-0003**.
- TPL-A1-0002 "Assay for Finished Product" exists in the DB only — it is NOT in
  any `scripts/template_definitions/*.py` module (confirmed by grep; worklog
  2026-10-15 notes template edits "live only in lims.db … not yet captured as
  declarative seed modules").
- Test codes containing ASSAY/MGML: TST-03, TST-TITR, TST-ADL-001, TST-BIOA-API,
  TST-BIOA-FP. **TST-ASSAY-FP-MGML is free.** Do NOT reuse TST-03 (bound to
  TPL-A1-0001/0002, name "Assay (Propofol)").

## 7. DB backup record (mandatory, before seeding)
- Backup file: `backend-v2\lims.db.bak-a1mgml-20261024-182021`
- Source `lims.db` size: 1404928 bytes; backup size: 1404928 bytes; **MATCH = True**.
