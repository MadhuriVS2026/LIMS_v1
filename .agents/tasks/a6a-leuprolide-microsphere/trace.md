# Trace Note — Dissolution-Leuprolide-microsphere (A6a copy of TPL-A6A-0002)

Investigation + backup step. This is a trace/oracle document, NOT code. A later
step builds the template; this note tells it exactly what to reproduce and the
gold values a parity test can assert.

---

## 0. Mandatory DB backup (done first)

- Source: `d:\RD-instance\GIT\backend-v2\lims.db`
- **Backup file:** `d:\RD-instance\GIT\backend-v2\lims.db.bak-leuprolide-20261024-220422`
- **Verified byte size:** `1433600` bytes on BOTH source and backup (match = True).

---

## 1. Base template TPL-A6A-0002 — module or DB-only?

**DB-only row.** TPL-A6A-0002 exists ONLY as a seeded row in the live DB
(`test_templates.id = 22`, archetype `A6a`, v1, status Active, result_unit `%`).
It is NOT produced by any module under `backend-v2/scripts/template_definitions/`.

- `scripts/template_definitions/a6_dissolution.py` defines only
  **TPL-A6A-0001** (`A6A`, "Dissolution (without replacement)"), plus A6B-0001
  and A6C-0001. Its `TEMPLATES = [A6A, A6B, A6C]`.
- TPL-A6A-0002/0003/0004 are all DB-only rows (0004's docstring in
  a6_dissolution.py explicitly says so and warns not to retrofit it).
- The closest sibling MODULE for structure/patterns is
  `a6b_octreotide_ph10.py` (TPL-A6B-0002) — same Leuprolide-style context
  header (rows 2-15), same standard-chain, same STDEV-includes-mean weight
  quirk, same per-block Mean/Min/Max/RSD.

**Base-copy source:** the TPL-A6A-0002 **definition JSON** read from the DB (see
§4). Its `timepoints_release` sequence group already models a 6-unit cumulative
carry-over release — the exact structure the Leuprolide sheet needs. The new
template should be authored as a copy of this JSON definition, adjusted to the
Leuprolide sheet's constants and its *fixed-media + replace-fraction* carry
model (see §3 and the carry-model note in §4).

Bound test for TPL-A6A-0002: `tests.id = 22`, code `TST-DISS-QC`, name
`Dissolution`, type `Quantitative`.

---

## 2. Chosen new code + bound Test

- **New template code: `TPL-A6A-0005`.**
  Existing A6A codes in the live DB are TPL-A6A-0001, -0002, -0003, -0004 (all
  Active, result_unit `%`). -0005 is the next free sequential code.
- **Template name (EXACT):** `Dissolution-Leuprolide-microsphere`
- **Bound Test name (EXACT):** `Dissolution-Leuprolide-microsphere`
  - Create a NEW Test Master entry (the seeder `ensure_test` creates a missing
    Test by `test_code`). Suggested `test_code`: `TST-DISS-LEUP-MS` (new, unique;
    do NOT reuse TST-DISS-QC/id22 — that would retie 0002's test). `test_type`:
    `Quantitative`.
- **archetype:** `A6a`  **result_unit:** `%` (base A6A/TPL-A6A-0002 unit).

Seeding path: add a new `SeedTemplate` (likely a new module, registered in
`scripts/template_definitions/__init__.py` `SEED_TEMPLATES`) and run
`python -m scripts.seed_test_templates --validate-only` first (parse + dry-run
`WorksheetEvaluator(parsed).evaluate({}, {})`), then seed. The seeder is additive
and idempotent (skips existing codes).

---

## 3. Authoritative source — sheet `ZEG0572A` (A1:Q193)

Source dump: `d:\RD-instance\GIT\_dumps\Dissolution sheet_Leuprolide_Microsphere.txt`
(full cell+formula dump of `Test types/Dissolution sheet_Leuprolide_Microsphere.xlsx`).
Read in full (rows A1..A192).

Note: the sheet title A4 = "Blend Uniformity Calculation Sheet", but the content
is an **In-Vitro Release / dissolution** calc (Test B11 = "In Vitro Release").
Model as dissolution.

### Context rows 2-15 (display header, no formulas)

| Cell | Label | Value |
|------|-------|-------|
| A2 | — | R & D Gandhinagar |
| A3 | — | Analytical Development |
| A4 | Title | Blend Uniformity Calculation Sheet |
| B5 | Generic Name | Leuprolide acetate for depot suspension_22.5mg |
| B6 | Product Name | Leuprolide acetate for depot suspension_22.5mg |
| B7 | TRF No. | TRF-031-26-055 |
| B8 | AR No. | AD/045/26/0265 |
| B9 | Batch No. | ZEG0572A |
| B10 | Stability Condition | Initial |
| B11 | Test | In Vitro Release |
| B12 | Analysis as per | AD/TATP/220/01 |
| B13 | Analysed By | Ashish Parmar |
| B14 | Instrument Id. | AD/HPLC/065 |
| B15 | Date of Analysis | 2026-06-09 |

### Standard detail rows 17-19

| Cell | Field | Value |
|------|-------|-------|
| A19 | Standard name | Leuprolide Acetate |
| B19 | Potency (%) | 97.87 |
| C19 | MW of base | 1 |
| D19 | MW of salt | 1 |
| E19 | Weight (mg) | 20.11 |
| F19 | Dilution-1 (mL) | 50 |
| G19 | Volume-1 (mL) | 5 |
| H19 | Dilution-2 (mL) | 25 |
| **I19** | Concentration (ppm) | `=E19/F19*G19/H19*C19/D19*B19/100*1000` |

### Standard areas + BKT rows 21-29

- B22:B26 standard areas = 1108135, 1107954, 1107711, 1107762, 1109456
- D22:D26 BKT standard areas = 1101413, 1101192, 1096506, 1094608, 1092402
- `B27 = AVERAGE(B22:B26)`  (mean of 5 replicates)
- `D27 = AVERAGE(B22:B26, D22:D26)`  (pooled mean, 10 values — INCLUDES D22:D26)
- `B28 = STDEV(B22:B26)`;  `D28 = STDEV(B22:B26, D22:D26)`
- `B29 = B28*100/B27`;  `D29 = D28*100/D27`

### Dissolution parameters H21:I25 (display inputs)

| Cell | Field | Value |
|------|-------|-------|
| I22 | Volume in mL | 50 |
| I23 | Apparatus | Bottle Rotating |
| I24 | RPM | 6 |
| I25 | Temp °C | 50 |
| H26/H27 | Media | 0.5% W/V PVA IN WATER pH 5.50 |

### Pellet weights E/F rows 21-30 (per Dissolution Unit)

- E22:E27 labels: Unit-1 .. Unit-6
- F22:F27 "Pellets Weight in mg": **F22=49.17, F23=50.56, F24=49.77**, F25/F26/F27 blank
  (only 3 filled).
- `F28 = AVERAGE(F22:F27)` (over the 3 filled)
- `F29 = STDEV(F22:F28)` — **STDEV range INCLUDES the mean cell F28** (same quirk
  as Octreotide A6B — model as `sd(pool(weights.<w>, [mean]))`).
- `F30 = F29*100/F28`

### Blend params rows 31-37

| Cell | Field | Value |
|------|-------|-------|
| A32 | Average weight mg | 100 |
| B32 | Label claim mg | 9.8 |
| A35 | Media volume | `=I22` (= 50) |
| B35 | Pipette Vol. mL | 1 |
| C35 | V.F. Vol. mL | 1 |
| A37 | Sample withdraw/Replace | 1 |

---

## 4. Timepoint blocks — enumeration, formulas, carry chain

Blocks are 6 unit-rows each, starting row 40 and repeating every 6 rows through
row 189. **25 blocks total** at rows 40, 46, 52, 58, 64, 70, 76, 82, 88, 94,
100, 106, 112, 118, 124, 130, 136, 142, 148, 154, 160, 166, 172, 178, 184.

**Labeled timepoints (A-column), in order — 7 filled, 18 blank:**

| Block start row | A-label |
|-----------------|---------|
| 40  | 1 Hr |
| 46  | 24 Hr |
| 52  | 48 Hr |
| 58  | 96 Hr |
| 64  | 120 Hr |
| 70  | 144 Hr |
| 76  | 168 Hr |
| 82..184 | (blank — spare timepoint rows, no label, no sample area entered) |

Only blocks 1 Hr..168 Hr have sample areas entered. The 18 trailing blocks
(82-189) are empty template rows. The new sequence group should allow up to ~25
rows but default to the 7 real timepoints (1/24/48/96/120/144/168 Hr).

### Per-unit columns (within each block, 6 unit-rows for units 1..6)

Column B = Sample Area (input). The per-unit formula references that unit's own
pellet weight: row-offset 0→F22, 1→F23, 2→F24, 3→F25, 4→F26, 5→F27.

**%Assay J (e.g. J40):**
```
J40 = IF(B40="","", B40/$B$27*$E$19/$F$19*$G$19/$H$19*$C$35/$B$35
                     *$A$35/$F$22*$B$19*$C$19/$D$19*$A$32/$B$32)
```
i.e. `area / mean_std * E19/F19 * G19/H19 * C35/B35 * A35/(unit pellet wt)
      * B19 * C19/D19 * A32/B32`.
Note B19 (potency 97.87) enters as a **plain multiplier** here (not /100), and
A35 (fixed media 50) is the numerator — media does NOT shrink per timepoint in
this sheet.

**K (replace fraction), e.g. K40:**
```
K40 = IF(J40="","", J40*$A$37/$A$35)       (= J40 * 1/50)
```

**L (cumulative add-back) — the with-replacement carry chain:**
- 1 Hr block (rows 40-45): **no L column.** Cumulative C = J directly.
- 24 Hr block (first carry): `L46 = IF(K40="","", K40)` — just the prior block's K.
  (`L47=K41, L48=K42, L49=K43, L50=K44, L51=K45`.)
- 48 Hr onward (running cumulative): `L52 = IF(K46="","", K46+L46)`, i.e.
  **L[this] = K[prior block, same unit-offset] + L[prior block, same unit-offset]**.
  Every later block follows the same pattern (L58=K52+L52, L64=K58+L58, ...).

So L is a running sum of all earlier blocks' K values for that unit:
`L[block b, unit u] = Σ K[blocks 1..b-1, unit u]`.

**Cumulative %Release C:**
- First block (1 Hr): `C40 = J40` (no add-back).
- Later blocks: `C46 = IF(J46="","", J46 + L46)` → `C = J + L`.

This is the **with-replacement cumulative release**: each timepoint's raw %Assay
plus the fraction already withdrawn (and replaced) in all prior timepoints.

**Per-block aggregates (on the block-start row, over the 6 C-cells):**
- `D = AVERAGE(C..C+5)`  (Mean)
- `E = MIN(C..C+5)`
- `F = MAX(C..C+5)`
- `G = STDEV(C..C+5)*100/D`  (%RSD)

### Carry-model note for the implementer (important)

The base **TPL-A6A-0002** `timepoints_release` sequence models carry as a
*without-replacement, shrinking-media* chain:
```
media  = test_prep.medium_volume - (rowno - 1) * test_prep.withdrawal_volume
carry_n = coalesce(prev.carry_n,0) + coalesce(prev.unit_n,0)/media * withdrawal_volume
unit_n  = <area-to-% chain using `media`> + carry_n
```
The **Leuprolide sheet differs**: media is FIXED at A35 (=50) for every
timepoint, and the add-back is `K = J*A37/A35` with a running-sum L. To reproduce
the sheet exactly, the new template's sequence carry should be:
```
# fixed media (A35), replace fraction A37 (both from prep/context)
carry_n  = coalesce(prev.carry_n, 0) + coalesce(prev.unit_n, 0) * A37 / A35
unit_n   = <area-to-% chain, fixed A35 numerator, divide by this unit's pellet wt>
            + carry_n
```
where `coalesce(prev.unit_n,0)*A37/A35` is exactly the sheet's prior-block
`K = J*A37/A35`, and `coalesce(prev.carry_n,0)` accumulates it (matching
`L[b] = K[b-1] + L[b-1]`). On row 1 `prev` is empty so carry=0 and `unit_n = J`
(matches C40=J40). This mirrors how the proven A6B Octreotide / A6A-0002 modules
express cumulative add-back with `coalesce(prev.*, 0)`.

### Reusable base definition JSON (from DB, to copy)

TPL-A6A-0002 definition structure (read from `test_templates.definition`,
id=22), to clone and adapt:
- context: product, batch_no, label_claim_mgml (number, divisor), trf_no, ar_no,
  date_of_analysis, avg_weight, initial_volume, withdrawal_volume, method_no,
  instrument_id, analysed_by.
- groups: `additional_info` (strength, test_performed, pct_assay, disso_media,
  apparatus, rpm, temp_c, lnb_no, parameter, wt_per_ml, disso_id, hplc_id,
  column_id), `standard` (name/weight_mg/vol_1/pip_1/vol_2/pip_2/vol_3/potency +
  `conc_ppm = weight_mg/vol_1*pip_1/vol_2*pip_2/vol_3*potency/100*1000`, round 2),
  `std_areas` (table, area), `corel_weights`, `corel_areas`, `stats`
  (mean_std/sd_std/rsd_std + corelation + bracketing), `bkt_1`, `sst`,
  `test_prep`, `ti_header`, `time_intervals` (table: time_hr + unit_1..unit_6
  raw areas), `tpr_header`, **`timepoints_release`** (sequence: time_hr, media,
  carry_1..6, unit_1..6, mean/sd/rsd/min_val/max_val), `release_chart`,
  `remarks`.
- resultRef in DB was `None`; A6A-0001 uses `timepoints.mean_released`. Set the
  new template's `resultRef` to the release-group mean (e.g.
  `timepoints_release.mean`).
- criteria: `sst_std_rsd` → `stats.rsd_std`, lte 2.0, blocking.

Adaptations for Leuprolide vs base 0002:
1. Standard conc chain is the SAME shape but the sheet's I19 uses C19/D19
   (MW base/salt) — include `mw_base/mw_salt` (both 1). conc_ppm rounding: sheet
   shows no explicit round on I19; keep base's round-2 or use the raw value for
   parity (see gold I19 below — assert to shown rounding).
2. Standard stats: add the pooled bracketing D27/D28/D29 (AVERAGE/STDEV over
   B22:B26 + D22:D26) — the sheet's BKT is the D-column, 5 values.
3. Add the **pellet-weight table** (6 units, "Pellets Weight in mg") with the
   STDEV-includes-mean quirk for Mean/SD/%RSD (model like Octreotide weight_stats).
4. Blend params: A32=100 (avg weight mg), B32=9.8 (label claim mg), A35=`=I22`
   (fixed media 50), B35=1, C35=1, A37=1.
5. The per-unit %Assay chain divides by the unit's pellet weight (F22..F27), and
   multiplies A32/B32 and B19 (plain) — see §5 chain.
6. Fixed-media carry model per the note above (NOT the shrinking-media 0002 model).

---

## 5. Hand-derived gold values (exact arithmetic — oracle for parity test)

Engine facts confirmed from `src/domain/services/calculation/expression.py`:
`sd`/`stdev` = sample SD (n-1, Excel STDEV); `rsd` = sd/mean*100; `round` =
half-away-from-zero (Excel); `trunc` truncates; `mean(empty)`=blank, `sum(empty)`=0;
`coalesce` = first non-blank; `pool` flattens ranges. So the sheet's AVERAGE/STDEV
map 1:1 to `mean`/`sd`.

### Standard concentration

```
I19 = E19/F19*G19/H19*C19/D19*B19/100*1000
    = 20.11/50 * 5/25 * 1/1 * 97.87/100 * 1000
    = 0.4022 * 0.2 * 0.9787 * 1000
I19 = 78.726628 ppm   (≈ 78.73)
```

### Standard area statistics

```
B27 = AVERAGE(1108135,1107954,1107711,1107762,1109456) = 1108203.6
D27 = AVERAGE(B22:B26 + D22:D26, 10 values)             = 1102713.9
B28 = STDEV(B22:B26)       = 719.9265934801964
B29 = B28*100/B27          = 0.06496338700579897   (≈ 0.06 %)
D28 = STDEV(10 pooled)     = 6388.745720231615
D29 = D28*100/D27          = 0.5793656650407342    (≈ 0.58 %)
```

### Pellet-weight statistics (STDEV-includes-mean quirk)

```
Filled F22:F24 = 49.17, 50.56, 49.77
F28 = AVERAGE(49.17,50.56,49.77)                 = 49.833333333333336  (≈ 49.83)
F29 = STDEV(49.17,50.56,49.77, F28=49.8333...)   = 0.569229498728081   (n=4, incl mean)
F30 = F29*100/F28                                = 1.1422665526316007  (≈ 1.14 %)
```

### 1 Hr block (first timepoint — C = J directly)

Chain per unit: `J = B/B27 * E19/F19 * G19/H19 * C35/B35 * A35/Fw * B19 * C19/D19 * A32/B32`
with B27=1108203.6, E19/F19=20.11/50, G19/H19=5/25, C35/B35=1, A35=50, B19=97.87,
C19/D19=1, A32/B32=100/9.8.

```
B40 = 203438, unit-1 pellet F22 = 49.17:
J40 = 14.996084937889453     (≈ 15.00)   → C40 = J40 = 14.996084937889453
B41 = 231282, F23 = 50.56:  J41 = 16.579857409503386  → C41
B42 = 174411, F24 = 49.77:  J42 = 12.701419313269414  → C42
Block aggregates over C40:C42 (3 filled):
  D40 Mean = 14.759120553554084   (≈ 14.8)
  E40 Min  = 12.701419313269414   (≈ 12.7)
  F40 Max  = 16.579857409503386   (≈ 16.6)
  G40 %RSD = STDEV(C40:C42)*100/D40 = 13.212490048191508  (≈ 13.21)
```

### 24 Hr block (first cumulative add-back, C = J + L; L46 = K40)

```
K40 = J40*A37/A35 = 14.996084937889453 * 1/50 = 0.29992169875778907
K41 = 0.33159714819006775 ;  K42 = 0.25402838626538826
L46 = K40 = 0.29992169875778907

B46 = 681560, F22 = 49.17:
J46 = 50.24003209954843
C46 = J46 + L46 = 50.53995379830622        (≈ 50.5)   ← proves first add-back
C47 = J47 + L47(=K41) = 54.73775... + = 54.93604802433009
C48 = J48 + L48(=K42) = 43.16740746631347
```

### 48 Hr block (running L — proves the chain)

```
K46 = J46*A37/A35 = 50.24003209954843/50 = 1.0048006419909685
L52 = K46 + L46 = 1.0048006419909685 + 0.29992169875778907 = 1.3047223407487576
B52 = 1013055, F22 = 49.17:
J52 = 74.67562022214923
C52 = J52 + L52 = 75.98034256289799        (≈ 76.0)
```

The running L therefore accumulates every prior block's K for that unit:
`L[b,u] = K[b-1,u] + L[b-1,u] = Σ K[1..b-1, u]`. Reproduced by
`carry_n = coalesce(prev.carry_n,0) + coalesce(prev.unit_n,0)*A37/A35`.

---

## 6. Headline summary (for the step message)

- Backup: `lims.db.bak-leuprolide-20261024-220422`, 1,433,600 bytes (verified).
- New code: **TPL-A6A-0005**; name & test name EXACTLY
  `Dissolution-Leuprolide-microsphere`; archetype A6a; result_unit `%`.
- Base: TPL-A6A-0002 is a **DB-only row** (not a module); copy its definition
  JSON; closest pattern module is a6b_octreotide_ph10.py.
- Timepoints: **25 blocks** (rows 40-189); **7 real labeled** (1/24/48/96/120/144/168 Hr),
  18 spare/blank.
- Gold: I19=78.726628; B27=1108203.6; F28=49.8333, F29=0.569229, F30=1.14227;
  J40=C40=14.996085; C46=50.539954 (=J46 50.240032 + L46 0.299922); C52=75.980343.
