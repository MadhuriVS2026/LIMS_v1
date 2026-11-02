# Generalised Worksheet Formulas — by Test Template

_Generated 2026-10-26 from the live Active template definitions in `backend-v2/lims.db` (via the API). One section per template; each calculated field is listed with its section, output unit, rounding, and the generalised `expression` the calculation engine evaluates. Acceptance criteria (the pass/fail limits) are listed after the formulas._

Notes on the expression language: `mean()/sd()/rsd()/min()/max()/count()/sum()` are aggregates over a table column (`group.field`); `if(cond, a, b)` is a conditional; `pool(col,[extra])` concatenates values; bare names resolve within the current row/group, dotted names (`group.field`) reference another group. Rounding `round`/`trunc` to N digits.

## Index

| Code | Version | Status | Archetype | Template Name |
|------|---------|--------|-----------|---------------|
| TPL-A1-0001 | v1 | Active | A1 | Assay by HPLC (external standard) |
| TPL-A1-0002 | v1 | Active | A1 | Assay for Finished Product |
| TPL-A1-0003 | v1 | Active | A1 | Assay for finished product mg/ml |
| TPL-A10-0001 | v1 | Active | A10 | Loss on Drying |
| TPL-A10-0002 | v1 | Active | A10 | Weight per mL (pycnometer) |
| TPL-A11-0001 | v1 | Active | A11 | Assay by Microbial Bioassay — API |
| TPL-A11-0002 | v1 | Active | A11 | Assay by Microbial Bioassay — Finished Product |
| TPL-A12-0001 | v1 | Active | A12 | Free & Entrapped Drug (liposomal) |
| TPL-A12-0002 | v1 | Active | A12 | Drug-to-Lipid Ratio |
| TPL-A12-0003 | v1 | Active | A12 | Amphotericin B — Drug-to-Lipid Ratio |
| TPL-A13-0001 | v1 | Active | A13 | Trace / Nitrosamine Impurities by LC-MS |
| TPL-A14-0001 | v1 | Active | A14 | Linearity Qualification — Multi-Component (CAD) |
| TPL-A2-0001 | v1 | Active | A2 | Multi-Analyte Content by HPLC (summed peaks) |
| TPL-A2-0002 | v1 | Active | A2 | Content of Lyso PC / Lyso PG (mg/mL) |
| TPL-A2-0003 | v1 | Active | A2 | Content of Lyso PC / Lyso PG (mg/vial) |
| TPL-A2-0004 | v1 | Active | A2 | Bupivacaine Lipid Content & Drug-to-Lipid Ratio |
| TPL-A3-0001 | v1 | Active | A3 | Saturation Solubility by HPLC |
| TPL-A4-0001 | v1 | Active | A4 | Related Substances by HPLC (against impurity standard) |
| TPL-A5-0001 | v1 | Active | A5 | Related Substances by Area Normalisation |
| TPL-A5-0002 | v1 | Active | A5 | Related Substance by Area Normalization (RRF Division Factor) |
| TPL-A5-0003 | v1 | Active | A5 | Related Substance by Area Normalization (RRF Division Factor) |
| TPL-A5-0004 | v1 | Active | A5 | Related Substance by Area Normalization (RRF Multiplication Factor) |
| TPL-A6A-0001 | v1 | Active | A6a | Dissolution (without replacement) |
| TPL-A6A-0002 | v1 | Active | A6a | Dissolution sheet_ without replacement_ QC release-6 |
| TPL-A6A-0003 | v1 | Active | A6a | Dissolution_without replacement_Ch_12 units |
| TPL-A6A-0004 | v1 | Active | A6a | Dissolution_12units |
| TPL-A6A-0005 | v1 | Active | A6a | Dissolution-Leuprolide-microsphere |
| TPL-A6B-0001 | v1 | Active | A6b | Dissolution (with replacement) |
| TPL-A6B-0002 | v1 | Active | A6b | Dissolution (Octreotide Acetate, pH 10) |
| TPL-A6C-0001 | v1 | Active | A6c | Dissolution (whole vial, residual content) |
| TPL-A6D-0001 | v1 | Active | A6d | In-Vitro Release (Franz Diffusion Cell) |
| TPL-A7-0001 | v1 | Active | A7 | Dissolution Profile Comparison (f1 / f2) |
| TPL-A8-0001 | v1 | Inactive | A8 | Content Uniformity by HPLC |
| TPL-A8-0001 | v2 | Active | A8 | Content Uniformity by HPLC-v2 |
| TPL-A8-0002 | v1 | Active | A8 | Content Uniformity by Weight Variation |
| TPL-A8-0003 | v1 | Draft | A8 | content uniformity for tablet |
| TPL-A8-0004 | v1 | Active | A8 | Content Uniformity by HPLC — 30 Units (Stage 2) |
| TPL-A9-0001 | v1 | Active | A9 | Assay by Titration |
| TPL-H1-0001 | v1 | Active | A4 | HPLC RS - two wavelength |
| TPL-H1-0002 | v1 | Active | A4 | RS-HPLC-Two-wavelenght-Ampho |

---

## TPL-A1-0001 v1 — Assay by HPLC (external standard)

**Archetype:** A1 · **Status:** Active · **Reportable result:** `stats.pct_mean_assay`

### Section: Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Co-relation — Weights  (`corel_weights`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| STD-1 Weight | `std1_weight` | mg |  | `standard.weight_mg` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |
| Mean (pooled BKT 1) | `mean_bkt_1` |  |  | `mean(pool(std_areas.area, bkt_1.area))` |
| SD (pooled BKT 1) | `sd_bkt_1` |  |  | `sd(pool(std_areas.area, bkt_1.area))` |
| %RSD (pooled BKT 1) | `rsd_bkt_1` | % |  | `rsd(pool(std_areas.area, bkt_1.area))` |
| Mean STD 2 Area | `mean_std2` |  |  | `mean(corel_areas.std2_area)` |
| Standard Co-relation | `std_corelation` | % |  | `trunc(stats.mean_std / stats.mean_std2 * corel_weights.std2_weight / standard.weight_mg, 3) * 100` |
| % Mean Assay | `pct_mean_assay` | % | round 2 | `mean(samples.pct_assay)` |

### Section: Sample Preparations  (`samples`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Avg Weight | `avg_wt` |  |  | `avg_weight` |
| Label Claim (L.C.) | `lc` |  |  | `label_claim` |
| Avg. Area | `avg_area` |  |  | `mean([area_1, area_2])` |
| % Assay | `pct_assay` | % |  | `avg_area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 * s_vol_1 / sample_weight * avg_weight / label_claim * standard.potency * standard.mw_base / standard.mw_salt` |

---

## TPL-A1-0002 v1 — Assay for Finished Product

**Archetype:** A1 · **Status:** Active · **Reportable result:** `stats.pct_mean_assay`

### Section: Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Co-relation — Weights  (`corel_weights`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| STD-1 Weight | `std1_weight` | mg |  | `standard.weight_mg` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |
| Mean (pooled BKT 1) | `mean_bkt_1` |  |  | `mean(pool(std_areas.area, bkt_1.area))` |
| SD (pooled BKT 1) | `sd_bkt_1` |  |  | `sd(pool(std_areas.area, bkt_1.area))` |
| %RSD (pooled BKT 1) | `rsd_bkt_1` | % |  | `rsd(pool(std_areas.area, bkt_1.area))` |
| Mean STD 2 Area | `mean_std2` |  |  | `mean(corel_areas.std2_area)` |
| Standard Co-relation | `std_corelation` | % |  | `trunc(stats.mean_std / stats.mean_std2 * corel_weights.std2_weight / standard.weight_mg, 3) * 100` |
| % Mean Assay | `pct_mean_assay` | % | round 2 | `mean(samples.pct_assay)` |

### Section: Sample Preparations  (`samples`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Avg Weight | `avg_wt` |  |  | `avg_weight` |
| Label Claim (L.C.) | `lc` |  |  | `label_claim` |
| Avg. Area | `avg_area` |  |  | `mean([area_1, area_2])` |
| % Assay | `pct_assay` | % |  | `avg_area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 * s_vol_1 / sample_weight * avg_weight / label_claim * standard.potency * standard.mw_base / standard.mw_salt` |

---

## TPL-A1-0003 v1 — Assay for finished product mg/ml

**Archetype:** A1 · **Status:** Active · **Reportable result:** `stats.pct_mean_assay`

### Section: Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Co-relation — Weights  (`corel_weights`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| STD-1 Weight | `std1_weight` | mg |  | `standard.weight_mg` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |
| Mean (pooled BKT 1) | `mean_bkt_1` |  |  | `mean(pool(std_areas.area, bkt_1.area))` |
| SD (pooled BKT 1) | `sd_bkt_1` |  |  | `sd(pool(std_areas.area, bkt_1.area))` |
| %RSD (pooled BKT 1) | `rsd_bkt_1` | % |  | `rsd(pool(std_areas.area, bkt_1.area))` |
| Mean STD 2 Area | `mean_std2` |  |  | `mean(corel_areas.std2_area)` |
| Standard Co-relation | `std_corelation` | % |  | `trunc(stats.mean_std / stats.mean_std2 * corel_weights.std2_weight / standard.weight_mg, 3) * 100` |
| % Mean Assay | `pct_mean_assay` | % | round 2 | `mean(samples.pct_assay)` |
| Mean (mg/mL) | `mean_mgml` | mg/mL | round 2 | `mean(samples.assay_mgml)` |

### Section: Sample Preparations  (`samples`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Avg Weight | `avg_wt` |  |  | `avg_weight` |
| Label Claim (L.C.) | `lc` |  |  | `label_claim` |
| Avg. Area | `avg_area` |  |  | `mean([area_1, area_2])` |
| % Assay | `pct_assay` | % |  | `avg_area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 * s_vol_1 / sample_weight * avg_weight / label_claim * standard.potency * standard.mw_base / standard.mw_salt` |
| Assay (mg/mL) | `assay_mgml` | mg/mL |  | `pct_assay * label_claim / 100` |

---

## TPL-A10-0001 v1 — Loss on Drying

**Archetype:** A10 · **Status:** Active · **Reportable result:** `determinations.mean_pct_loss`

### Section: Determinations  (`determinations`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Sample Wt. | `sample_weight` | g | round 4 | `dish_plus_sample - dish_weight` |
| Loss on Drying | `pct_loss` | % | round 2 | `(dish_plus_sample - dish_plus_dried) / (dish_plus_sample - dish_weight) * 100` |
| Mean Loss on Drying | `mean_pct_loss` | % | round 2 | `mean(determinations.pct_loss)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Spread between determinations | `max(determinations.pct_loss) - min(determinations.pct_loss)` | NMT 0.5 % absolute | advisory |

---

## TPL-A10-0002 v1 — Weight per mL (pycnometer)

**Archetype:** A10 · **Status:** Active · **Reportable result:** `determinations.mean_weight_per_ml`

### Section: Weight determination using Pycnometer  (`determinations`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Relative Density | `ratio` |  | round 4 | `(with_sample - empty_weight) / (with_water - empty_weight)` |
| Weight per mL | `weight_per_ml` | g/mL | round 4 | `ratio * water_factor` |
| Mean Weight per mL | `mean_weight_per_ml` | g/mL | round 4 | `mean(determinations.weight_per_ml)` |

### Section: Weight determination using Pycnometer 2  (`gross_content`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| wt of filled individual container (W1) | `filled_weight` | g |  | input |
| wt of Individual empty container (W2) | `empty_weight` | g |  | input |
| W1 - W2 | `net_weight` | g | round 4 | `filled_weight - empty_weight` |
| Gross Content | `gross_content_ml` | mL | round 4 | `(filled_weight - empty_weight) / mean(determinations.weight_per_ml)` |
| Average (footer) | `gross_stats.mean_gross_content` | mL | round 4 | `mean(gross_content.gross_content_ml)` |

Leading `Batch No` and wrapping `Info` columns precede W1. The Average renders as
an in-table footer row aligned under the Gross Content column.

---

## TPL-A11-0001 v1 — Assay by Microbial Bioassay — API

**Archetype:** A11 · **Status:** Active · **Reportable result:** `results.mean_assay`

### Section: Standard Dose Levels  (`standard`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concentration | `conc` | µg/mL |  | `std_stock.weight_mg / std_stock.vol_1 * pip_dose / vol_dose * std_stock.pip_final / std_stock.vol_final * std_stock.potency` |
| Log Concentration | `log_conc` |  | round 4 | `ln(conc)` |
| Reference Zone Mean | `ref_avg` | mm |  | `mean(ref_p1_z1, ref_p1_z3, ref_p1_z5, ref_p2_z1, ref_p2_z3, ref_p2_z5, ref_p3_z1, ref_p3_z3, ref_p3_z5)` |
| Reference Zone %RSD | `ref_rsd` | % |  | `rsd(ref_p1_z1, ref_p1_z3, ref_p1_z5, ref_p2_z1, ref_p2_z3, ref_p2_z5, ref_p3_z1, ref_p3_z3, ref_p3_z5)` |
| Test Zone Mean | `spl_avg` | mm |  | `mean(spl_p1_z2, spl_p1_z4, spl_p1_z6, spl_p2_z2, spl_p2_z4, spl_p2_z6, spl_p3_z2, spl_p3_z4, spl_p3_z6)` |
| Test Zone %RSD | `spl_rsd` | % |  | `rsd(spl_p1_z2, spl_p1_z4, spl_p1_z6, spl_p2_z2, spl_p2_z4, spl_p2_z6, spl_p3_z2, spl_p3_z4, spl_p3_z6)` |
| Corrected Mean | `corrected_mean` | mm |  | `if(rowno = std_stock.reference_row, curve.ref_grand, spl_avg - (ref_avg - curve.ref_grand))` |

### Section: Standard Curve  (`curve`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Grand Reference Zone Mean | `ref_grand` | mm |  | `mean(standard.ref_avg)` |
| Slope | `curve_slope` |  | round 4 | `slope(standard.corrected_mean, standard.log_conc)` |
| Intercept | `curve_intercept` |  | round 4 | `intercept(standard.corrected_mean, standard.log_conc)` |
| R² | `r_squared` |  | round 4 | `correl(standard.corrected_mean, standard.log_conc) ^ 2` |

### Section: Sample Preparations  (`sample`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Nominal Concentration | `nominal_conc` | µg/mL |  | `sample_weight / s_vol_1 * s_pip_1 / s_vol_2 * 1000 * s_pip_2 / s_vol_3` |
| Reference Zone Mean | `ref_avg` | mm |  | `mean(ref_p1_z1, ref_p1_z3, ref_p1_z5, ref_p2_z1, ref_p2_z3, ref_p2_z5, ref_p3_z1, ref_p3_z3, ref_p3_z5)` |
| Reference Zone %RSD | `ref_rsd` | % |  | `rsd(ref_p1_z1, ref_p1_z3, ref_p1_z5, ref_p2_z1, ref_p2_z3, ref_p2_z5, ref_p3_z1, ref_p3_z3, ref_p3_z5)` |
| Test Zone Mean | `spl_avg` | mm |  | `mean(spl_p1_z2, spl_p1_z4, spl_p1_z6, spl_p2_z2, spl_p2_z4, spl_p2_z6, spl_p3_z2, spl_p3_z4, spl_p3_z6)` |
| Test Zone %RSD | `spl_rsd` | % |  | `rsd(spl_p1_z2, spl_p1_z4, spl_p1_z6, spl_p2_z2, spl_p2_z4, spl_p2_z6, spl_p3_z2, spl_p3_z4, spl_p3_z6)` |
| Corrected Mean (U) | `corrected_mean` | mm |  | `spl_avg - (ref_avg - curve.ref_grand)` |
| Log Concentration (Lu) | `log_conc_u` |  |  | `(corrected_mean - curve.curve_intercept) / curve.curve_slope` |
| Concentration Found (Cu) | `measured_conc` | µg/mL |  | `exp(log_conc_u)` |
| Potency | `potency_ug_per_mg` | µg/mg | round 0 | `measured_conc * s_vol_3 / s_pip_2 * s_vol_2 / s_pip_1 * s_vol_1 / sample_weight` |
| Assay | `assay_pct` | % | round 2 | `measured_conc / nominal_conc * 100` |

### Section: Results  (`results`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean Potency | `mean_potency` | µg/mg | round 0 | `mean(sample.potency_ug_per_mg)` |
| Mean Assay | `mean_assay` | % | round 2 | `mean(sample.assay_pct)` |
| SD | `sd_assay` |  | round 2 | `sd(sample.assay_pct)` |
| %RSD | `rsd_assay` | % | round 2 | `rsd(sample.assay_pct)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Widest zone-diameter %RSD across standard plates | `max(pool(standard.ref_rsd, standard.spl_rsd))` | NMT 10.0 % | blocking |
| Widest zone-diameter %RSD across sample plates | `max(pool(sample.ref_rsd, sample.spl_rsd))` | NMT 10.0 % | blocking |
| Correlation of the log-dose / zone-diameter line | `curve.r_squared` | NLT 0.95 | blocking |
| %RSD between sample preparations | `results.rsd_assay` | NMT 10.0 % | blocking |

---

## TPL-A11-0002 v1 — Assay by Microbial Bioassay — Finished Product

**Archetype:** A11 · **Status:** Active · **Reportable result:** `results.mean_assay`

### Section: Standard Dose Levels  (`standard`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concentration | `conc` | µg/mL |  | `std_stock.weight_mg / std_stock.vol_1 * pip_dose / vol_dose * std_stock.pip_final / std_stock.vol_final * std_stock.potency` |
| Log Concentration | `log_conc` |  | round 4 | `ln(conc)` |
| Reference Zone Mean | `ref_avg` | mm |  | `mean(ref_p1_z1, ref_p1_z3, ref_p1_z5, ref_p2_z1, ref_p2_z3, ref_p2_z5, ref_p3_z1, ref_p3_z3, ref_p3_z5)` |
| Reference Zone %RSD | `ref_rsd` | % |  | `rsd(ref_p1_z1, ref_p1_z3, ref_p1_z5, ref_p2_z1, ref_p2_z3, ref_p2_z5, ref_p3_z1, ref_p3_z3, ref_p3_z5)` |
| Test Zone Mean | `spl_avg` | mm |  | `mean(spl_p1_z2, spl_p1_z4, spl_p1_z6, spl_p2_z2, spl_p2_z4, spl_p2_z6, spl_p3_z2, spl_p3_z4, spl_p3_z6)` |
| Test Zone %RSD | `spl_rsd` | % |  | `rsd(spl_p1_z2, spl_p1_z4, spl_p1_z6, spl_p2_z2, spl_p2_z4, spl_p2_z6, spl_p3_z2, spl_p3_z4, spl_p3_z6)` |
| Corrected Mean | `corrected_mean` | mm |  | `if(rowno = std_stock.reference_row, curve.ref_grand, spl_avg - (ref_avg - curve.ref_grand))` |

### Section: Standard Curve  (`curve`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Grand Reference Zone Mean | `ref_grand` | mm |  | `mean(standard.ref_avg)` |
| Slope | `curve_slope` |  | round 4 | `slope(standard.corrected_mean, standard.log_conc)` |
| Intercept | `curve_intercept` |  | round 4 | `intercept(standard.corrected_mean, standard.log_conc)` |
| R² | `r_squared` |  | round 4 | `correl(standard.corrected_mean, standard.log_conc) ^ 2` |

### Section: Sample Preparations  (`sample`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Nominal Concentration | `nominal_conc` | µg/mL |  | `sample_weight / s_vol_1 * s_pip_1 / s_vol_2 * 1000 * s_pip_2 / s_vol_3` |
| Reference Zone Mean | `ref_avg` | mm |  | `mean(ref_p1_z1, ref_p1_z3, ref_p1_z5, ref_p2_z1, ref_p2_z3, ref_p2_z5, ref_p3_z1, ref_p3_z3, ref_p3_z5)` |
| Reference Zone %RSD | `ref_rsd` | % |  | `rsd(ref_p1_z1, ref_p1_z3, ref_p1_z5, ref_p2_z1, ref_p2_z3, ref_p2_z5, ref_p3_z1, ref_p3_z3, ref_p3_z5)` |
| Test Zone Mean | `spl_avg` | mm |  | `mean(spl_p1_z2, spl_p1_z4, spl_p1_z6, spl_p2_z2, spl_p2_z4, spl_p2_z6, spl_p3_z2, spl_p3_z4, spl_p3_z6)` |
| Test Zone %RSD | `spl_rsd` | % |  | `rsd(spl_p1_z2, spl_p1_z4, spl_p1_z6, spl_p2_z2, spl_p2_z4, spl_p2_z6, spl_p3_z2, spl_p3_z4, spl_p3_z6)` |
| Corrected Mean (U) | `corrected_mean` | mm |  | `spl_avg - (ref_avg - curve.ref_grand)` |
| Log Concentration (Lu) | `log_conc_u` |  |  | `(corrected_mean - curve.curve_intercept) / curve.curve_slope` |
| Concentration Found (Cu) | `measured_conc` | µg/mL |  | `exp(log_conc_u)` |
| Assay | `assay_pct` | % | round 2 | `measured_conc / nominal_conc * avg_weight / label_claim * 100` |

### Section: Results  (`results`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean Assay | `mean_assay` | % | round 2 | `mean(sample.assay_pct)` |
| SD | `sd_assay` |  | round 2 | `sd(sample.assay_pct)` |
| %RSD | `rsd_assay` | % | round 2 | `rsd(sample.assay_pct)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Widest zone-diameter %RSD across standard plates | `max(pool(standard.ref_rsd, standard.spl_rsd))` | NMT 10.0 % | blocking |
| Widest zone-diameter %RSD across sample plates | `max(pool(sample.ref_rsd, sample.spl_rsd))` | NMT 10.0 % | blocking |
| Correlation of the log-dose / zone-diameter line | `curve.r_squared` | NLT 0.95 | blocking |
| %RSD between sample preparations | `results.rsd_assay` | NMT 10.0 % | blocking |

---

## TPL-A12-0001 v1 — Free & Entrapped Drug (liposomal)

**Archetype:** A12 · **Status:** Active · **Reportable result:** `preps.mean_pct_entrapped`

### Section: Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |
| %RSD (pooled with bracketing standards) | `rsd_bkt` | % |  | `rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))` |
| Mean (pooled — Block 1) | `mean_bkt_1` |  |  | `mean(pool(std_areas.area, bkt_1.area))` |
| SD (pooled — Block 1) | `sd_bkt_1` |  |  | `sd(pool(std_areas.area, bkt_1.area))` |
| %RSD (pooled — Block 1) | `rsd_bkt_1` |  |  | `rsd(pool(std_areas.area, bkt_1.area))` |
| Mean (pooled — Block 2) | `mean_bkt_2` |  |  | `mean(pool(std_areas.area, bkt_1.area, bkt_2.area))` |
| SD (pooled — Block 2) | `sd_bkt_2` |  |  | `sd(pool(std_areas.area, bkt_1.area, bkt_2.area))` |
| %RSD (pooled — Block 2) | `rsd_bkt_2` |  |  | `rsd(pool(std_areas.area, bkt_1.area, bkt_2.area))` |

### Section: Sample Preparation  (`preps`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| % Con. | `pct_con` |  | round 4 | `area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * standard.mw_base / standard.mw_salt * standard.potency / 100 * s_vol_1 / sample_ml * s_vol_2 / s_pip_1 / number(label_claim) * 100` |
| Bupivacaine in (mg/mL) | `bup_mg_ml` |  | round 4 | `pct_assay_bup * number(label_claim) / 100` |
| % Free Drug | `pct_free` |  | round 4 | `pct_con / pct_assay_bup * 100` |
| Free Drug (mg/mL) | `free_mg_ml` |  | round 4 | `pct_free / 100 * number(label_claim)` |
| % Entrapped | `pct_entrapped` |  | round 4 | `100 - free_mg_ml / bup_mg_ml * 100` |
| Entrapped (mg/mL) | `entrapped_mg_ml` |  | round 3 | `pct_entrapped / 100 * number(label_claim)` |
| Mean % Entrapped | `mean_pct_entrapped` |  | round 4 | `mean(preps.pct_entrapped)` |
| Mean % Free Drug | `mean_pct_free` |  | round 4 | `mean(preps.pct_free)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| %RSD of pooled bracketing standards | `stats.rsd_bkt` | NMT 2.0 % | blocking |
| Carried-over % Assay of total drug | `mean(preps.pct_assay_total)` | 50 % to 150 % — outside this, check the transcription | advisory |

---

## TPL-A12-0002 v1 — Drug-to-Lipid Ratio

**Archetype:** A12 · **Status:** Active · **Reportable result:** `ratio.drug_to_lipid`

### Section: Lipid Components — carried from the Lipid Content test  (`lipids`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Content | `mg_per_ml` | mg/mL |  | `pct_mean * lc / 100` |

### Section: Drug — carried from the Assay test  (`drug`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Content | `mg_per_ml` | mg/mL |  | `pct_assay * lc / 100` |

### Section: Drug-to-Lipid Ratio  (`ratio`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Σ Lipid Content | `sum_lipid` | mg/mL |  | `if(count(lipids.mg_per_ml) > 0, sum(lipids.mg_per_ml), blank())` |
| Drug / Lipid Ratio | `drug_to_lipid` |  | round 4 | `drug.mg_per_ml / sum_lipid` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Carried-over % Assay of drug | `drug.pct_assay` | 50 % to 150 % — outside this, check the transcription | advisory |

---

## TPL-A12-0003 v1 — Amphotericin B — Drug-to-Lipid Ratio

**Archetype:** A12 · **Status:** Active · **Reportable result:** `batches.drug_lipid_ratio`

### Section: Batches — assays carried from the component tests  (`batches`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Content of Cholesterol (mg/vial) | `chol_content` | mg/vial |  | `chol_assay * lc_chol / 100` |
| Content of HSPC (mg/vial) | `hspc_content` | mg/vial |  | `hspc_assay * lc_hspc / 100` |
| Content of DSPG (mg/vial) | `dspg_content` | mg/vial |  | `dspg_assay * lc_dspg / 100` |
| Content of Amphotericin B (mg/vial) | `ampho_content` | mg/vial |  | `ampho_assay * lc_ampho / 100` |
| Calculated Lipid content (mg/vial) | `lipid_content` | mg/vial |  | `chol_content + hspc_content + dspg_content` |
| Calculated Drug to Lipid ratio | `drug_lipid_ratio` |  |  | `ampho_content / lipid_content` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Assay of Cholesterol | `mean(batches.chol_assay)` | 90.0 % to 120.0 % | blocking |
| Assay of HSPC | `mean(batches.hspc_assay)` | 90.0 % to 120.0 % | blocking |
| Assay of DSPG | `mean(batches.dspg_assay)` | 80.0 % to 120.0 % | blocking |
| Microbial assay of Amphotericin B | `mean(batches.ampho_assay)` | 90.0 % to 120.0 % | blocking |
| Drug to Lipid ratio | `mean(batches.drug_lipid_ratio)` | 0.11 to 0.17 | blocking |

---

## TPL-A13-0001 v1 — Trace / Nitrosamine Impurities by LC-MS

**Archetype:** A13 · **Status:** Active · **Reportable result:** `samples.mean_ppm`

### Section: Nitrosamine Standard  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * potency / 100 * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |

### Section: Sample Preparations  (`samples`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Blank-Corrected Area | `corrected_area` |  |  | `area - blank_area` |
| Content | `ppm` | ppm | trunc 4 | `corrected_area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * standard.potency / 100 * s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 * s_vol_1 / sample_weight * avg_weight / label_claim * 1000000` |
| Mean Content | `mean_ppm` | ppm | trunc 4 | `mean(samples.ppm)` |

### Section: Blank Assessment  (`suitability`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Blank Interference | `blank_interference` | % | round 2 | `blank_area / stats.mean_std * 100` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| Blank interference against standard response | `suitability.blank_interference` | NMT 5.0 % | blocking |

---

## TPL-A14-0001 v1 — Linearity Qualification — Multi-Component (CAD)

**Archetype:** A14 · **Status:** Active · **Reportable result:** `regression.min_correlation`

### Section: Replicate Injections — Linearity Level 2 (100 %)  (`replicates`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total Area — Component 1 | `total_1` |  | round 3 | `area_1 + area_b_1` |
| Total Area — Component 2 | `total_2` |  | round 3 | `area_2 + area_b_2` |
| Total Area — Component 3 | `total_3` |  | round 3 | `area_3 + area_b_3` |

### Section: Replicate Precision  (`precision`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean — Component 1 | `mean_1` |  |  | `mean(replicates.total_1)` |
| SD — Component 1 | `sd_1` |  | round 5 | `sd(replicates.total_1)` |
| %RSD — Component 1 | `rsd_1` | % | round 2 | `sd_1 / mean_1 * 100` |
| Mean — Component 2 | `mean_2` |  |  | `mean(replicates.total_2)` |
| SD — Component 2 | `sd_2` |  | round 5 | `sd(replicates.total_2)` |
| %RSD — Component 2 | `rsd_2` | % | round 2 | `sd_2 / mean_2 * 100` |
| Mean — Component 3 | `mean_3` |  |  | `mean(replicates.total_3)` |
| SD — Component 3 | `sd_3` |  | round 5 | `sd(replicates.total_3)` |
| %RSD — Component 3 | `rsd_3` | % | round 2 | `sd_3 / mean_3 * 100` |
| Worst %RSD | `max_rsd` | % | round 2 | `max([rsd_1, rsd_2, rsd_3])` |

### Section: Linearity Levels  (`levels`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Conc. — Component 1 | `conc_1` | mg/mL | round 3 | `std.weight_mg_1 / std.dilution_1 * stock_ml / dil_ml * std.purity_1 / 100` |
| Conc. — Component 2 | `conc_2` | mg/mL | round 3 | `std.weight_mg_2 / std.dilution_1 * stock_ml / dil_ml * std.purity_2 / 100` |
| Conc. — Component 3 | `conc_3` | mg/mL | round 3 | `std.weight_mg_3 / std.dilution_1 * stock_ml / dil_ml * std.purity_3 / 100` |
| Total Area — Component 1 | `total_area_1` |  | round 3 | `area_1 + area_b_1` |
| Total Area — Component 2 | `total_area_2` |  | round 3 | `area_2 + area_b_2` |
| Total Area — Component 3 | `total_area_3` |  | round 3 | `area_3 + area_b_3` |
| Regression x — Component 1 | `x_1` |  |  | `if(nominal_pct > 0, conc_1, blank())` |
| Regression y — Component 1 | `y_1` |  |  | `if(nominal_pct > 0, total_area_1, blank())` |
| Regression x — Component 2 | `x_2` |  |  | `if(nominal_pct > 0, conc_2, blank())` |
| Regression y — Component 2 | `y_2` |  |  | `if(nominal_pct > 0, total_area_2, blank())` |
| Regression x — Component 3 | `x_3` |  |  | `if(nominal_pct > 0, conc_3, blank())` |
| Regression y — Component 3 | `y_3` |  |  | `if(nominal_pct > 0, total_area_3, blank())` |

### Section: Regression Summary  (`regression`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Slope — Component 1 | `slope_1` |  | round 4 | `slope(levels.y_1, levels.x_1)` |
| Intercept — Component 1 | `intercept_1` |  | round 4 | `intercept(levels.y_1, levels.x_1)` |
| Correlation (R) — Component 1 | `correlation_1` |  | round 5 | `correl(levels.y_1, levels.x_1)` |
| R² — Component 1 | `r_squared_1` |  | round 5 | `correl(levels.y_1, levels.x_1) ^ 2` |
| Slope — Component 2 | `slope_2` |  | round 4 | `slope(levels.y_2, levels.x_2)` |
| Intercept — Component 2 | `intercept_2` |  | round 4 | `intercept(levels.y_2, levels.x_2)` |
| Correlation (R) — Component 2 | `correlation_2` |  | round 5 | `correl(levels.y_2, levels.x_2)` |
| R² — Component 2 | `r_squared_2` |  | round 5 | `correl(levels.y_2, levels.x_2) ^ 2` |
| Slope — Component 3 | `slope_3` |  | round 4 | `slope(levels.y_3, levels.x_3)` |
| Intercept — Component 3 | `intercept_3` |  | round 4 | `intercept(levels.y_3, levels.x_3)` |
| Correlation (R) — Component 3 | `correlation_3` |  | round 5 | `correl(levels.y_3, levels.x_3)` |
| R² — Component 3 | `r_squared_3` |  | round 5 | `correl(levels.y_3, levels.x_3) ^ 2` |
| Poorest Correlation | `min_correlation` |  | round 5 | `min([correlation_1, correlation_2, correlation_3])` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of five replicate injections at the 100 % level | `precision.max_rsd` | NMT 10.0 % | blocking |
| Correlation coefficient (R) across linearity levels | `regression.min_correlation` | NLT 0.99 | blocking |

---

## TPL-A2-0001 v1 — Multi-Analyte Content by HPLC (summed peaks)

**Archetype:** A2 · **Status:** Active · **Reportable result:** `samples.mean_pct_lc`

### Section: Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Injections (peak areas summed)  (`std_areas`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total STD Area | `area` |  |  | `if(sum([peak_1, peak_2, peak_3, peak_4]) = 0, blank(), sum([peak_1, peak_2, peak_3, peak_4]))` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |

### Section: Sample Preparations  (`samples`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total Area | `area` |  |  | `if(sum([peak_1, peak_2, peak_3, peak_4]) = 0, blank(), sum([peak_1, peak_2, peak_3, peak_4]))` |
| Content | `content` | mg | round 3 | `area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 * s_vol_1 / sample_weight * standard.potency / 100 * standard.mw_base / standard.mw_salt * vial_factor` |
| % of Label Claim | `pct_lc` | % | round 2 | `content * 100 / label_claim` |
| Mean % of Label Claim | `mean_pct_lc` | % | round 2 | `mean(samples.pct_lc)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| Mean content as % of label claim | `mean(samples.pct_lc)` | 90.0 % to 110.0 % | advisory |

---

## TPL-A2-0002 v1 — Content of Lyso PC / Lyso PG (mg/mL)

**Archetype:** A2 · **Status:** Active · **Reportable result:** `sample_results.pc_mgml`

### Section: Standard injections  (`std_injections`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Lyso PC Sum Area | `sum_pc` |  |  | `if(sum([pc_1, pc_2, pc_3, pc_4, pc_5]) = 0, blank(), sum([pc_1, pc_2, pc_3, pc_4, pc_5]))` |
| Lyso PG Sum Area | `sum_pg` |  |  | `if(sum([pg_1, pg_2]) = 0, blank(), sum([pg_1, pg_2]))` |

### Section: BKT Standard Details  (`bkt_injections`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Lyso PC Sum Area | `sum_pc` |  |  | `if(sum([pc_1, pc_2, pc_3, pc_4, pc_5]) = 0, blank(), sum([pc_1, pc_2, pc_3, pc_4, pc_5]))` |
| Lyso PG Sum Area | `sum_pg` |  |  | `if(sum([pg_1, pg_2]) = 0, blank(), sum([pg_1, pg_2]))` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Lyso PC Mean STD | `mean_std_pc` |  |  | `mean(std_injections.sum_pc)` |
| Lyso PC SD | `sd_std_pc` |  |  | `sd(std_injections.sum_pc)` |
| Lyso PC %RSD | `rsd_std_pc` | % |  | `rsd(std_injections.sum_pc)` |
| Lyso PG Mean STD | `mean_std_pg` |  |  | `mean(std_injections.sum_pg)` |
| Lyso PG SD | `sd_std_pg` |  |  | `sd(std_injections.sum_pg)` |
| Lyso PG %RSD | `rsd_std_pg` | % |  | `rsd(std_injections.sum_pg)` |
| Lyso PC Pooled Mean | `mean_pool_pc` |  |  | `mean(pool(std_injections.sum_pc, bkt_injections.sum_pc))` |
| Lyso PC Pooled SD | `sd_pool_pc` |  |  | `sd(pool(std_injections.sum_pc, bkt_injections.sum_pc))` |
| Lyso PC Pooled %RSD | `rsd_pool_pc` | % |  | `rsd(pool(std_injections.sum_pc, bkt_injections.sum_pc))` |
| Lyso PG Pooled Mean | `mean_pool_pg` |  |  | `mean(pool(std_injections.sum_pg, bkt_injections.sum_pg))` |
| Lyso PG Pooled SD | `sd_pool_pg` |  |  | `sd(pool(std_injections.sum_pg, bkt_injections.sum_pg))` |
| Lyso PG Pooled %RSD | `rsd_pool_pg` | % |  | `rsd(pool(std_injections.sum_pg, bkt_injections.sum_pg))` |

### Section: Sample Injections  (`sample_results`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Lyso PC Sum Area | `sum_pc` |  |  | `if(sum([pc_1, pc_2, pc_3, pc_4, pc_5]) = 0, blank(), sum([pc_1, pc_2, pc_3, pc_4, pc_5]))` |
| Lyso PG Sum Area | `sum_pg` |  |  | `if(sum([pg_1, pg_2]) = 0, blank(), sum([pg_1, pg_2]))` |
| Lyso PC mg/mL | `pc_mgml` | mg/mL | round 6 | `sum_pc / stats.mean_std_pc * standard.pc_weight / standard.pc_vol1 * standard.pc_pip / standard.pc_vol2 * standard.pc_mw_base / standard.pc_mw_salt * sample_prep.vol / sample_prep.ml * sample_prep.vol2 / sample_prep.pip * standard.pc_potency / 100` |
| Lyso PG mg/mL | `pg_mgml` | mg/mL | round 6 | `sum_pg / stats.mean_std_pg * standard.pg_weight / standard.pg_vol1 * standard.pg_pip / standard.pg_vol2 * sample_prep.vol2 / sample_prep.pip * sample_prep.vol / sample_prep.ml * standard.pg_mw_base / standard.pg_mw_salt * standard.pg_potency / 100` |
| Lyso PC Assay | `pc_assay` | % | round 4 | `pc_mgml * 100 / standard.pc_lc` |
| Lyso PG Assay | `pg_assay` | % | round 4 | `pg_mgml * 100 / standard.pg_lc` |
| Avg Lyso PC mg/mL | `avg_pc_mgml` | mg/mL | round 6 | `mean(sample_results.pc_mgml)` |
| Avg Lyso PG mg/mL | `avg_pg_mgml` | mg/mL | round 6 | `mean(sample_results.pg_mgml)` |
| Avg Lyso PC Assay | `avg_pc_assay` | % | round 4 | `mean(sample_results.pc_assay)` |
| Avg Lyso PG Assay | `avg_pg_assay` | % | round 4 | `mean(sample_results.pg_assay)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of Lyso PC standard replicate injections | `stats.rsd_std_pc` | NMT 2.0 % | blocking |
| %RSD of Lyso PG standard replicate injections | `stats.rsd_std_pg` | NMT 2.0 % | blocking |
| %RSD of Lyso PC pooled bracketing injections | `stats.rsd_pool_pc` | NMT 2.0 % | blocking |
| %RSD of Lyso PG pooled bracketing injections | `stats.rsd_pool_pg` | NMT 2.0 % | blocking |

---

## TPL-A2-0003 v1 — Content of Lyso PC / Lyso PG (mg/vial)

**Archetype:** A2 · **Status:** Active · **Reportable result:** `sample_results.pc_mgvial`

### Section: Standard Details  (`std_injections`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Lyso PC Sum Area | `sum_pc` |  |  | `if(sum([pc_1, pc_2, pc_3, pc_4, pc_5]) = 0, blank(), sum([pc_1, pc_2, pc_3, pc_4, pc_5]))` |
| Lyso PG Sum Area | `sum_pg` |  |  | `if(sum([pg_1, pg_2]) = 0, blank(), sum([pg_1, pg_2]))` |

### Section: BKT Standard Details  (`bkt_injections`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Lyso PC Sum Area | `sum_pc` |  |  | `if(sum([pc_1, pc_2, pc_3, pc_4, pc_5]) = 0, blank(), sum([pc_1, pc_2, pc_3, pc_4, pc_5]))` |
| Lyso PG Sum Area | `sum_pg` |  |  | `if(sum([pg_1, pg_2]) = 0, blank(), sum([pg_1, pg_2]))` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Lyso PC Mean STD | `mean_std_pc` |  |  | `mean(std_injections.sum_pc)` |
| Lyso PC SD | `sd_std_pc` |  |  | `sd(std_injections.sum_pc)` |
| Lyso PC %RSD | `rsd_std_pc` | % |  | `rsd(std_injections.sum_pc)` |
| Lyso PG Mean STD | `mean_std_pg` |  |  | `mean(std_injections.sum_pg)` |
| Lyso PG SD | `sd_std_pg` |  |  | `sd(std_injections.sum_pg)` |
| Lyso PG %RSD | `rsd_std_pg` | % |  | `rsd(std_injections.sum_pg)` |
| Lyso PC Pooled Mean | `mean_pool_pc` |  |  | `mean(pool(std_injections.sum_pc, bkt_injections.sum_pc))` |
| Lyso PC Pooled SD | `sd_pool_pc` |  |  | `sd(pool(std_injections.sum_pc, bkt_injections.sum_pc))` |
| Lyso PC Pooled %RSD | `rsd_pool_pc` | % |  | `rsd(pool(std_injections.sum_pc, bkt_injections.sum_pc))` |
| Lyso PG Pooled Mean | `mean_pool_pg` |  |  | `mean(pool(std_injections.sum_pg, bkt_injections.sum_pg))` |
| Lyso PG Pooled SD | `sd_pool_pg` |  |  | `sd(pool(std_injections.sum_pg, bkt_injections.sum_pg))` |
| Lyso PG Pooled %RSD | `rsd_pool_pg` | % |  | `rsd(pool(std_injections.sum_pg, bkt_injections.sum_pg))` |

### Section: Sample Injections  (`sample_results`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Lyso PC Sum Area | `sum_pc` |  |  | `if(sum([pc_1, pc_2, pc_3, pc_4, pc_5]) = 0, blank(), sum([pc_1, pc_2, pc_3, pc_4, pc_5]))` |
| Lyso PG Sum Area | `sum_pg` |  |  | `if(sum([pg_1, pg_2]) = 0, blank(), sum([pg_1, pg_2]))` |
| Lyso PC mg/vial | `pc_mgvial` | mg/vial | round 6 | `sum_pc / stats.mean_std_pc * standard.pc_weight / standard.pc_vol1 * standard.pc_pip / standard.pc_vol2 * standard.pc_mw_base / standard.pc_mw_salt * sample_prep.vol / sample_prep.ml * sample_prep.vol2 / sample_prep.pip * standard.pc_potency / 100 * vial_factor` |
| Lyso PG mg/vial | `pg_mgvial` | mg/vial | round 6 | `sum_pg / stats.mean_std_pg * standard.pg_weight / standard.pg_vol1 * standard.pg_pip / standard.pg_vol2 * sample_prep.vol2 / sample_prep.pip * sample_prep.vol / sample_prep.ml * standard.pg_mw_base / standard.pg_mw_salt * standard.pg_potency / 100 * vial_factor` |
| Lyso PC Assay | `pc_assay` | % | round 4 | `pc_mgvial * 100 / standard.pc_lc` |
| Lyso PG Assay | `pg_assay` | % | round 4 | `pg_mgvial * 100 / standard.pg_lc` |
| Avg Lyso PC mg/vial | `avg_pc_mgvial` | mg/vial | round 6 | `mean(sample_results.pc_mgvial)` |
| Avg Lyso PG mg/vial | `avg_pg_mgvial` | mg/vial | round 6 | `mean(sample_results.pg_mgvial)` |
| Avg Lyso PC Assay | `avg_pc_assay` | % | round 4 | `mean(sample_results.pc_assay)` |
| Avg Lyso PG Assay | `avg_pg_assay` | % | round 4 | `mean(sample_results.pg_assay)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of Lyso PC standard replicate injections | `stats.rsd_std_pc` | NMT 2.0 % | blocking |
| %RSD of Lyso PG standard replicate injections | `stats.rsd_std_pg` | NMT 2.0 % | blocking |
| %RSD of Lyso PC pooled bracketing injections | `stats.rsd_pool_pc` | NMT 2.0 % | blocking |
| %RSD of Lyso PG pooled bracketing injections | `stats.rsd_pool_pg` | NMT 2.0 % | blocking |

---

## TPL-A2-0004 v1 — Bupivacaine Lipid Content & Drug-to-Lipid Ratio

**Archetype:** A2 · **Status:** Active · **Reportable result:** `drug_lipid.ratio`

### Section: Standard Details  (`standard`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Conc. (ppm) | `conc_ppm` | ppm | round 2 | `weight / vol1 * pip1 / vol2 * pip2 / vol3 * potency / 100 * mw_base / mw_salt * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Tricaprylin Mean STD | `mean_std_tri` |  |  | `mean(std_areas.tri_area)` |
| Tricaprylin SD | `sd_std_tri` |  |  | `sd(std_areas.tri_area)` |
| Tricaprylin %RSD | `rsd_std_tri` | % |  | `rsd(std_areas.tri_area)` |
| Tricaprylin Pooled Mean | `mean_pool_tri` |  |  | `mean(pool(std_areas.tri_area, bkt_areas.tri_area))` |
| Tricaprylin Pooled SD | `sd_pool_tri` |  |  | `sd(pool(std_areas.tri_area, bkt_areas.tri_area))` |
| Tricaprylin Pooled %RSD | `rsd_pool_tri` | % |  | `rsd(pool(std_areas.tri_area, bkt_areas.tri_area))` |
| DPPG Na Mean STD | `mean_std_dppg` |  |  | `mean(std_areas.dppg_area)` |
| DPPG Na SD | `sd_std_dppg` |  |  | `sd(std_areas.dppg_area)` |
| DPPG Na %RSD | `rsd_std_dppg` | % |  | `rsd(std_areas.dppg_area)` |
| DPPG Na Pooled Mean | `mean_pool_dppg` |  |  | `mean(pool(std_areas.dppg_area, bkt_areas.dppg_area))` |
| DPPG Na Pooled SD | `sd_pool_dppg` |  |  | `sd(pool(std_areas.dppg_area, bkt_areas.dppg_area))` |
| DPPG Na Pooled %RSD | `rsd_pool_dppg` | % |  | `rsd(pool(std_areas.dppg_area, bkt_areas.dppg_area))` |
| Cholesterol Mean STD | `mean_std_chol` |  |  | `mean(std_areas.chol_area)` |
| Cholesterol SD | `sd_std_chol` |  |  | `sd(std_areas.chol_area)` |
| Cholesterol %RSD | `rsd_std_chol` | % |  | `rsd(std_areas.chol_area)` |
| Cholesterol Pooled Mean | `mean_pool_chol` |  |  | `mean(pool(std_areas.chol_area, bkt_areas.chol_area))` |
| Cholesterol Pooled SD | `sd_pool_chol` |  |  | `sd(pool(std_areas.chol_area, bkt_areas.chol_area))` |
| Cholesterol Pooled %RSD | `rsd_pool_chol` | % |  | `rsd(pool(std_areas.chol_area, bkt_areas.chol_area))` |
| DEPC Mean STD | `mean_std_depc` |  |  | `mean(std_areas.depc_area)` |
| DEPC SD | `sd_std_depc` |  |  | `sd(std_areas.depc_area)` |
| DEPC %RSD | `rsd_std_depc` | % |  | `rsd(std_areas.depc_area)` |
| DEPC Pooled Mean | `mean_pool_depc` |  |  | `mean(pool(std_areas.depc_area, bkt_areas.depc_area))` |
| DEPC Pooled SD | `sd_pool_depc` |  |  | `sd(pool(std_areas.depc_area, bkt_areas.depc_area))` |
| DEPC Pooled %RSD | `rsd_pool_depc` | % |  | `rsd(pool(std_areas.depc_area, bkt_areas.depc_area))` |

### Section: Sample Details  (`lipid_samples`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Compound Index | `cidx` |  |  | `rowno - 1 - trunc((rowno - 1) / 4, 0) * 4` |
| Compound Name | `compound_name` |  |  | `coalesce(if(cidx == 0, standard.name[0], blank()), if(cidx == 1, standard.name[1], blank()), if(cidx == 2, standard.name[2], blank()), if(cidx == 3, standard.name[3], blank()))` |
| LC | `lc` |  |  | `coalesce(if(cidx == 0, lc_tri, blank()), if(cidx == 1, lc_dppg, blank()), if(cidx == 2, lc_chol, blank()), if(cidx == 3, lc_depc, blank()))` |
| % Assay | `pct_assay` | % |  | `coalesce(if(cidx == 0, area / stats.mean_std_tri * standard.weight[0] / standard.vol1[0] * standard.pip1[0] / standard.vol2[0] * standard.pip2[0] / standard.vol3[0] * vol_j / sample_weight * vol_l / pip_k * standard.potency[0] / lc_tri * standard.mw_base[0] / standard.mw_salt[0] * avg_weight, blank()), if(cidx == 1, area / stats.mean_std_dppg * standard.weight[1] / standard.vol1[1] * standard.pip1[1] / standard.vol2[1] * standard.pip2[1] / standard.vol3[1] * vol_j / sample_weight * vol_l / pip_k * standard.potency[1] / lc_dppg * standard.mw_base[1] / standard.mw_salt[1] * avg_weight, blank()), if(cidx == 2, area / stats.mean_std_chol * standard.weight[2] / standard.vol1[2] * standard.pip1[2] / standard.vol2[2] * standard.pip2[2] / standard.vol3[2] * vol_j / sample_weight * vol_l / pip_k * standard.potency[2] / lc_chol * standard.mw_base[2] / standard.mw_salt[2] * avg_weight, blank()), if(cidx == 3, area / stats.mean_std_depc * standard.weight[3] / standard.vol1[3] * standard.pip1[3] / standard.vol2[3] * standard.pip2[3] / standard.vol3[3] * vol_j / sample_weight * vol_l / pip_k * standard.potency[3] / lc_depc * standard.mw_base[3] / standard.mw_salt[3] * avg_weight, blank()))` |
| % Mean | `pct_mean` | % |  | `mean([pct_assay])` |

### Section: % Mean each compound  (`mean_each_compound`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Compound Name | `compound_name` |  |  | `standard.name[(rowno - 1)]` |
| % Mean | `pct_mean` | % |  | `mean([ lipid_samples.pct_assay[(rowno - 1)], lipid_samples.pct_assay[(rowno - 1) + 4] ])` |

### Section: Drug to Lipid Ratio  (`drug_lipid`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Tricaprylin mg/mL (Lipid) | `tri_mgml` | mg/mL |  | `lipid_samples.pct_mean[(rowno - 1) * 4 + 0] * lc_tri / 100` |
| DPPG Na mg/mL (Lipid) | `dppg_mgml` | mg/mL |  | `lipid_samples.pct_mean[(rowno - 1) * 4 + 1] * lc_dppg / 100` |
| Cholesterol mg/mL (Lipid) | `chol_mgml` | mg/mL |  | `lipid_samples.pct_mean[(rowno - 1) * 4 + 2] * lc_chol / 100` |
| DEPC mg/mL (Lipid) | `depc_mgml` | mg/mL |  | `lipid_samples.pct_mean[(rowno - 1) * 4 + 3] * lc_depc / 100` |
| mg/mL (Sum of Lipid) | `sum_lipid` | mg/mL |  | `tri_mgml + dppg_mgml + chol_mgml + depc_mgml` |
| mg/mL of Bupivacaine | `mgml_bupi` | mg/mL |  | `pct_assay_bupi * lc_bupi / 100` |
| Drug/Lipid Ratio | `ratio` |  |  | `mgml_bupi / sum_lipid` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of Tricaprylin standard replicate injections | `stats.rsd_std_tri` | NMT 2.0 % | blocking |
| %RSD of DPPG standard replicate injections | `stats.rsd_std_dppg` | NMT 2.0 % | blocking |
| %RSD of Cholesterol standard replicate injections | `stats.rsd_std_chol` | NMT 2.0 % | blocking |
| %RSD of DEPC standard replicate injections | `stats.rsd_std_depc` | NMT 2.0 % | blocking |
| %RSD of Tricaprylin pooled bracketing injections | `stats.rsd_pool_tri` | NMT 2.0 % | blocking |
| %RSD of DPPG pooled bracketing injections | `stats.rsd_pool_dppg` | NMT 2.0 % | blocking |
| %RSD of Cholesterol pooled bracketing injections | `stats.rsd_pool_chol` | NMT 2.0 % | blocking |
| %RSD of DEPC pooled bracketing injections | `stats.rsd_pool_depc` | NMT 2.0 % | blocking |

---

## TPL-A3-0001 v1 — Saturation Solubility by HPLC

**Archetype:** A3 · **Status:** Active · **Reportable result:** `samples.mean_solubility`

### Section: Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |

### Section: Saturated Solution Preparations  (`samples`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Solubility | `solubility` | mg/mL | round 4 | `area / stats.mean_std * standard.conc_ppm * diluted_to_ml / aliquot_ml / 1000` |
| Mean Solubility | `mean_solubility` | mg/mL | round 4 | `mean(samples.solubility)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| %RSD across saturated solution preparations | `rsd(samples.solubility)` | NMT 5.0 % | advisory |

---

## TPL-A4-0001 v1 — Related Substances by HPLC (against impurity standard)

**Archetype:** A4 · **Status:** Active · **Reportable result:** `summary.total_impurities`

### Section: Reference Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Reference Standard 2 Details  (`standard_2`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |

### Section: Standard Statistics 2  (`stats_2`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas_2.area)` |
| SD | `sd_std` |  |  | `sd(std_areas_2.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas_2.area)` |

### Section: Impurities  (`impurities`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Avg. Area | `avg_area` |  |  | `mean([area_1, area_2])` |
| RRT | `rrt` |  | round 3 | `rt / main_peak_rt` |
| % (before RRF) | `pct_uncorrected` | % |  | `avg_area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * sample_prep.s_vol_2 / sample_prep.s_pip_1 * sample_prep.s_vol_3 / sample_prep.s_pip_2 * sample_prep.s_vol_1 / sample_prep.sample_weight * standard.potency / 100 * standard.mw_base / standard.mw_salt * 100` |
| % w/w | `pct` | % | round 3 | `if(rrf_mode = "RRF (multiplication factor)", pct_uncorrected * rrf, pct_uncorrected / rrf)` |
| % counted in total | `pct_for_total` | % |  | `if(pct < loq, 0, pct)` |
| Reported | `reported` |  |  | `if(pct < loq, "BLQ", pct)` |

### Section: Summary  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Single Maximum Impurity | `max_single_impurity` | % | round 3 | `if(isblank(mean(impurities.pct)), blank(), max(impurities.pct_for_total))` |
| Total Impurities | `total_impurities` | % | round 3 | `if(isblank(mean(impurities.pct)), blank(), sum(impurities.pct_for_total))` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| Single maximum impurity | `max(impurities.pct_for_total)` | NMT 0.2 % | advisory |
| Total impurities | `sum(impurities.pct_for_total)` | NMT 1.0 % | advisory |

---

## TPL-A5-0001 v1 — Related Substances by Area Normalisation

**Archetype:** A5 · **Status:** Active · **Reportable result:** `summary.total_impurities`

### Section: Normalisation Basis  (`normalisation`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total Area | `total_area` |  |  | `sum(peaks.area) + main.area` |

### Section: Impurity Peaks  (`peaks`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| RRT | `rrt` |  | round 2 | `rt / main.rt` |
| % area (before RRF) | `pct_uncorrected` | % |  | `area / normalisation.total_area * 100` |
| % Impurity | `pct` | % | round 3 | `if(rrf_mode = "RRF (multiplication factor)", pct_uncorrected * rrf, pct_uncorrected / rrf)` |
| % counted in total | `pct_for_total` | % |  | `if(pct < loq, 0, pct)` |
| Reported | `reported` |  |  | `if(pct < loq, "BLQ", pct)` |

### Section: Summary  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total Impurities | `total_impurities` | % | round 3 | `if(isblank(mean(peaks.pct)), blank(), sum(peaks.pct))` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Single maximum impurity | `max(peaks.pct_for_total)` | NMT 0.2 % | advisory |
| Total impurities | `sum(peaks.pct_for_total)` | NMT 1.0 % | advisory |

---

## TPL-A5-0002 v1 — Related Substance by Area Normalization (RRF Division Factor)

**Archetype:** A5 · **Status:** Active · **Reportable result:** `summary.total_impurities`

### Section: Normalisation Basis  (`normalisation`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total Area | `total_area` |  |  | `sum(peaks.area) + main.area` |

### Section: Impurity Peaks  (`peaks`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| RRT | `rrt` |  | round 2 | `rt / main.rt` |
| % area (before RRF) | `pct_uncorrected` | % |  | `area / normalisation.total_area * 100` |
| % Impurity | `pct` | % | round 3 | `if(rrf_mode = "RRF (multiplication factor)", pct_uncorrected * rrf, pct_uncorrected / rrf)` |
| % counted in total | `pct_for_total` | % |  | `if(pct < loq, 0, pct)` |
| Reported | `reported` |  |  | `if(pct < loq, "BLQ", pct)` |

### Section: Summary  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total Impurities | `total_impurities` | % | round 3 | `if(isblank(mean(peaks.pct)), blank(), sum(peaks.pct))` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Single maximum impurity | `max(peaks.pct_for_total)` | NMT 0.2 % | advisory |
| Total impurities | `sum(peaks.pct_for_total)` | NMT 1.0 % | advisory |

---

## TPL-A5-0003 v1 — Related Substance by Area Normalization (RRF Division Factor)

**Archetype:** A5 · **Status:** Active · **Reportable result:** `summary.total_impurities`

### Section: Normalisation Basis  (`normalisation`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total Area | `total_area` |  |  | `sum(peaks.area) + main.area` |

### Section: Impurity Peaks  (`peaks`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| RRT | `rrt` |  | round 2 | `rt / main.rt` |
| % area (before RRF) | `pct_uncorrected` | % |  | `area / normalisation.total_area * 100` |
| % Impurity | `pct` | % | round 3 | `if(rrf_mode = "RRF (multiplication factor)", pct_uncorrected * rrf, pct_uncorrected / rrf)` |
| % counted in total | `pct_for_total` | % |  | `if(pct < loq, 0, pct)` |
| Reported | `reported` |  |  | `if(pct < loq, "BLQ", pct)` |

### Section: Summary  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total Impurities | `total_impurities` | % | round 3 | `if(isblank(mean(peaks.pct)), blank(), sum(peaks.pct))` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Single maximum impurity | `max(peaks.pct_for_total)` | NMT 0.2 % | advisory |
| Total impurities | `sum(peaks.pct_for_total)` | NMT 1.0 % | advisory |

---

## TPL-A5-0004 v1 — Related Substance by Area Normalization (RRF Multiplication Factor)

**Archetype:** A5 · **Status:** Active · **Reportable result:** `summary.total_impurities`

### Section: Normalisation Basis  (`normalisation`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total Area | `total_area` |  |  | `sum(peaks.area) + main.area` |

### Section: Impurity Peaks  (`peaks`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| RRT | `rrt` |  | round 2 | `rt / main.rt` |
| % area (before RRF) | `pct_uncorrected` | % |  | `area / normalisation.total_area * 100` |
| % Impurity | `pct` | % | round 3 | `pct_uncorrected * rrf` |
| % counted in total | `pct_for_total` | % |  | `if(pct < loq, 0, pct)` |
| Reported | `reported` |  |  | `if(pct < loq, "BLQ", pct)` |

### Section: Summary  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Total Impurities | `total_impurities` | % | round 3 | `if(isblank(mean(peaks.pct)), blank(), sum(peaks.pct))` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Single maximum impurity | `max(peaks.pct_for_total)` | NMT 0.2 % | advisory |
| Total impurities | `sum(peaks.pct_for_total)` | NMT 1.0 % | advisory |

---

## TPL-A6A-0001 v1 — Dissolution (without replacement)

**Archetype:** A6a · **Status:** Active

### Section: Standard details for dissolution  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concen. (ppm) | `conc_ppm` | ppm | round 2 | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * potency / 100 * 1000` |

### Section: Standard Co-relation — Weights  (`corel_weights`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| STD-1 Weight | `std1_weight` | mg |  | `standard.weight_mg` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean (STD 1) — from replicates | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |
| Mean (STD 2) | `mean_std2` |  |  | `mean(corel_areas.std2_area)` |
| Standard Co-relation | `std_corelation` | % |  | `trunc(stats.mean_std / stats.mean_std2 * corel_weights.std2_weight / standard.weight_mg, 3) * 100` |
| Mean (pooled BKT) | `mean_bkt_1` |  |  | `mean(pool(std_areas.area, bkt_1.area))` |
| SD (pooled BKT) | `sd_bkt_1` |  |  | `sd(pool(std_areas.area, bkt_1.area))` |
| %RSD (pooled BKT) | `rsd_bkt_1` | % |  | `rsd(pool(std_areas.area, bkt_1.area))` |

### Section: System Suitability Criteria  (`sst`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| 4. % RSD of the peak area of Doxorubicin from five replicate injections of Standard solution should be not more than 2.0. | `rsd_replicates` | % | round 5 | `stats.rsd_std` |
| 5. The %RSD of the peak area of Doxorubicin from Bracketing standards and replicate injections of Standard solution should be not more than 2.0. | `rsd_bracketing` | % | round 5 | `stats.rsd_bkt_1` |

### Section: Sample Weight  (`sample_weight`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Net Wt. (g) | `net_wt` | g | round 5 | `filled_wt - empty_wt` |

### Section: Sample Weight Statistics  (`sw_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean Net Wt. | `mean_net` | g | round 2 | `mean(sample_weight.net_wt)` |
| Min Net Wt. | `min_net` | g | round 5 | `min(sample_weight.net_wt)` |
| Max Net Wt. | `max_net` | g | round 2 | `max(sample_weight.net_wt)` |

### Section: TIMEPOINT for % content  (`timepoints_pct`, sequence)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| 1 | `unit_1` |  |  | `(time_intervals.unit_1[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[0] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_1, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 2 | `unit_2` |  |  | `(time_intervals.unit_2[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[1] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_2, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 3 | `unit_3` |  |  | `(time_intervals.unit_3[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[2] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_3, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 4 | `unit_4` |  |  | `(time_intervals.unit_4[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[3] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_4, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 5 | `unit_5` |  |  | `(time_intervals.unit_5[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[4] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_5, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 6 | `unit_6` |  |  | `(time_intervals.unit_6[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[5] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_6, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 7 | `unit_7` |  |  | `(time_intervals.unit_7[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[6] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_7, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 8 | `unit_8` |  |  | `(time_intervals.unit_8[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[7] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_8, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 9 | `unit_9` |  |  | `(time_intervals.unit_9[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[8] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_9, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 10 | `unit_10` |  |  | `(time_intervals.unit_10[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[9] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_10, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 11 | `unit_11` |  |  | `(time_intervals.unit_11[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[10] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_11, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 12 | `unit_12` |  |  | `(time_intervals.unit_12[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[11] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_12, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Mean | `mean` |  | round 1 | `mean(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| SD | `sd` |  | round 1 | `sd(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| %RSD | `rsd` |  | round 2 | `rsd(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| Min. | `min_val` |  | round 1 | `min(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| Max. | `max_val` |  | round 1 | `max(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |

### Section: Timepoint of % Release  (`timepoints_release`, sequence)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| 1 | `unit_1` |  |  | `additional_info.pct_assay - timepoints_pct.unit_1[rowno - 1]` |
| 2 | `unit_2` |  |  | `additional_info.pct_assay - timepoints_pct.unit_2[rowno - 1]` |
| 3 | `unit_3` |  |  | `additional_info.pct_assay - timepoints_pct.unit_3[rowno - 1]` |
| 4 | `unit_4` |  |  | `additional_info.pct_assay - timepoints_pct.unit_4[rowno - 1]` |
| 5 | `unit_5` |  |  | `additional_info.pct_assay - timepoints_pct.unit_5[rowno - 1]` |
| 6 | `unit_6` |  |  | `additional_info.pct_assay - timepoints_pct.unit_6[rowno - 1]` |
| 7 | `unit_7` |  |  | `additional_info.pct_assay - timepoints_pct.unit_7[rowno - 1]` |
| 8 | `unit_8` |  |  | `additional_info.pct_assay - timepoints_pct.unit_8[rowno - 1]` |
| 9 | `unit_9` |  |  | `additional_info.pct_assay - timepoints_pct.unit_9[rowno - 1]` |
| 10 | `unit_10` |  |  | `additional_info.pct_assay - timepoints_pct.unit_10[rowno - 1]` |
| 11 | `unit_11` |  |  | `additional_info.pct_assay - timepoints_pct.unit_11[rowno - 1]` |
| 12 | `unit_12` |  |  | `additional_info.pct_assay - timepoints_pct.unit_12[rowno - 1]` |
| Mean | `mean` |  | round 1 | `mean(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| SD | `sd` |  | round 1 | `sd(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| %RSD | `rsd` |  | round 2 | `rsd(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| Min. | `min_val` |  | round 1 | `min(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| Max. | `max_val` |  | round 1 | `max(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |

---

## TPL-A6A-0002 v1 — Dissolution sheet_ without replacement_ QC release-6

**Archetype:** A6a · **Status:** Active

### Section: Standard details for dissolution  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concen. (ppm) | `conc_ppm` | ppm | round 2 | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * potency / 100 * 1000` |

### Section: Standard Co-relation — Weights  (`corel_weights`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| STD-1 Weight | `std1_weight` | mg |  | `standard.weight_mg` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean (STD 1) — from replicates | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |
| Mean (STD 2) | `mean_std2` |  |  | `mean(corel_areas.std2_area)` |
| Standard Co-relation | `std_corelation` | % |  | `trunc(stats.mean_std / stats.mean_std2 * corel_weights.std2_weight / standard.weight_mg, 3) * 100` |
| Mean (pooled BKT) | `mean_bkt_1` |  |  | `mean(pool(std_areas.area, bkt_1.area))` |
| SD (pooled BKT) | `sd_bkt_1` |  |  | `sd(pool(std_areas.area, bkt_1.area))` |
| %RSD (pooled BKT) | `rsd_bkt_1` | % |  | `rsd(pool(std_areas.area, bkt_1.area))` |

### Section: System Suitability Criteria  (`sst`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| 4. % RSD of the peak area of Doxorubicin from five replicate injections of Standard solution should be not more than 2.0. | `rsd_replicates` | % | round 5 | `stats.rsd_std` |
| 5. The %RSD of the peak area of Doxorubicin from Bracketing standards and replicate injections of Standard solution should be not more than 2.0. | `rsd_bracketing` | % | round 5 | `stats.rsd_bkt_1` |

### Section: Timepoint of % Release  (`timepoints_release`, sequence)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| media | `media` |  |  | `test_prep.medium_volume - (rowno - 1) * test_prep.withdrawal_volume` |
| carry_1 | `carry_1` |  |  | `coalesce(prev.carry_1, 0) + coalesce(prev.unit_1, 0) / media * test_prep.withdrawal_volume` |
| 1 | `unit_1` |  |  | `time_intervals.unit_1[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.dilution_volume / 1 * media / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * 100 + carry_1` |
| carry_2 | `carry_2` |  |  | `coalesce(prev.carry_2, 0) + coalesce(prev.unit_2, 0) / media * test_prep.withdrawal_volume` |
| 2 | `unit_2` |  |  | `time_intervals.unit_2[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.dilution_volume / 1 * media / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * 100 + carry_2` |
| carry_3 | `carry_3` |  |  | `coalesce(prev.carry_3, 0) + coalesce(prev.unit_3, 0) / media * test_prep.withdrawal_volume` |
| 3 | `unit_3` |  |  | `time_intervals.unit_3[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.dilution_volume / 1 * media / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * 100 + carry_3` |
| carry_4 | `carry_4` |  |  | `coalesce(prev.carry_4, 0) + coalesce(prev.unit_4, 0) / media * test_prep.withdrawal_volume` |
| 4 | `unit_4` |  |  | `time_intervals.unit_4[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.dilution_volume / 1 * media / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * 100 + carry_4` |
| carry_5 | `carry_5` |  |  | `coalesce(prev.carry_5, 0) + coalesce(prev.unit_5, 0) / media * test_prep.withdrawal_volume` |
| 5 | `unit_5` |  |  | `time_intervals.unit_5[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.dilution_volume / 1 * media / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * 100 + carry_5` |
| carry_6 | `carry_6` |  |  | `coalesce(prev.carry_6, 0) + coalesce(prev.unit_6, 0) / media * test_prep.withdrawal_volume` |
| 6 | `unit_6` |  |  | `time_intervals.unit_6[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.dilution_volume / 1 * media / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * 100 + carry_6` |
| Mean | `mean` |  | round 1 | `mean(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6)` |
| SD | `sd` |  | round 1 | `sd(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6)` |
| %RSD | `rsd` |  | round 2 | `rsd(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6)` |
| Min. | `min_val` |  | round 1 | `min(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6)` |
| Max. | `max_val` |  | round 1 | `max(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |

---

## TPL-A6A-0003 v1 — Dissolution_without replacement_Ch_12 units

**Archetype:** A6a · **Status:** Active

### Section: Standard details for dissolution  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concen. (ppm) | `conc_ppm` | ppm | round 2 | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * potency / 100 * 1000` |

### Section: Standard Co-relation — Weights  (`corel_weights`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| STD-1 Weight | `std1_weight` | mg |  | `standard.weight_mg` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean (STD 1) — from replicates | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |
| Mean (STD 2) | `mean_std2` |  |  | `mean(corel_areas.std2_area)` |
| Standard Co-relation | `std_corelation` | % |  | `trunc(stats.mean_std / stats.mean_std2 * corel_weights.std2_weight / standard.weight_mg, 3) * 100` |
| Mean (pooled BKT) | `mean_bkt_1` |  |  | `mean(pool(std_areas.area, bkt_1.area))` |
| SD (pooled BKT) | `sd_bkt_1` |  |  | `sd(pool(std_areas.area, bkt_1.area))` |
| %RSD (pooled BKT) | `rsd_bkt_1` | % |  | `rsd(pool(std_areas.area, bkt_1.area))` |

### Section: System Suitability Criteria  (`sst`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| 4. % RSD of the peak area of Doxorubicin from five replicate injections of Standard solution should be not more than 2.0. | `rsd_replicates` | % | round 5 | `stats.rsd_std` |
| 5. The %RSD of the peak area of Doxorubicin from Bracketing standards and replicate injections of Standard solution should be not more than 2.0. | `rsd_bracketing` | % | round 5 | `stats.rsd_bkt_1` |

### Section: Sample Weight  (`sample_weight`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Net Wt. (g) | `net_wt` | g | round 5 | `filled_wt - empty_wt` |

### Section: Sample Weight Statistics  (`sw_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean Net Wt. | `mean_net` | g | round 2 | `mean(sample_weight.net_wt)` |
| Min Net Wt. | `min_net` | g | round 5 | `min(sample_weight.net_wt)` |
| Max Net Wt. | `max_net` | g | round 2 | `max(sample_weight.net_wt)` |

### Section: TIMEPOINT for % content  (`timepoints_pct`, sequence)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| 1 | `unit_1` |  |  | `(time_intervals.unit_1[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[0] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_1, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 2 | `unit_2` |  |  | `(time_intervals.unit_2[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[1] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_2, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 3 | `unit_3` |  |  | `(time_intervals.unit_3[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[2] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_3, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 4 | `unit_4` |  |  | `(time_intervals.unit_4[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[3] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_4, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 5 | `unit_5` |  |  | `(time_intervals.unit_5[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[4] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_5, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 6 | `unit_6` |  |  | `(time_intervals.unit_6[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[5] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_6, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 7 | `unit_7` |  |  | `(time_intervals.unit_7[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[6] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_7, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 8 | `unit_8` |  |  | `(time_intervals.unit_8[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[7] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_8, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 9 | `unit_9` |  |  | `(time_intervals.unit_9[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[8] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_9, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 10 | `unit_10` |  |  | `(time_intervals.unit_10[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[9] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_10, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 11 | `unit_11` |  |  | `(time_intervals.unit_11[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[10] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_11, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| 12 | `unit_12` |  |  | `(time_intervals.unit_12[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / sample_weight.net_wt[11] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim_mgml) * additional_info.wt_per_ml * 100) + coalesce(prev.unit_12, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Mean | `mean` |  | round 1 | `mean(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| SD | `sd` |  | round 1 | `sd(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| %RSD | `rsd` |  | round 2 | `rsd(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| Min. | `min_val` |  | round 1 | `min(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| Max. | `max_val` |  | round 1 | `max(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |

### Section: Timepoint of % Release  (`timepoints_release`, sequence)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| 1 | `unit_1` |  |  | `additional_info.pct_assay - timepoints_pct.unit_1[rowno - 1]` |
| 2 | `unit_2` |  |  | `additional_info.pct_assay - timepoints_pct.unit_2[rowno - 1]` |
| 3 | `unit_3` |  |  | `additional_info.pct_assay - timepoints_pct.unit_3[rowno - 1]` |
| 4 | `unit_4` |  |  | `additional_info.pct_assay - timepoints_pct.unit_4[rowno - 1]` |
| 5 | `unit_5` |  |  | `additional_info.pct_assay - timepoints_pct.unit_5[rowno - 1]` |
| 6 | `unit_6` |  |  | `additional_info.pct_assay - timepoints_pct.unit_6[rowno - 1]` |
| 7 | `unit_7` |  |  | `additional_info.pct_assay - timepoints_pct.unit_7[rowno - 1]` |
| 8 | `unit_8` |  |  | `additional_info.pct_assay - timepoints_pct.unit_8[rowno - 1]` |
| 9 | `unit_9` |  |  | `additional_info.pct_assay - timepoints_pct.unit_9[rowno - 1]` |
| 10 | `unit_10` |  |  | `additional_info.pct_assay - timepoints_pct.unit_10[rowno - 1]` |
| 11 | `unit_11` |  |  | `additional_info.pct_assay - timepoints_pct.unit_11[rowno - 1]` |
| 12 | `unit_12` |  |  | `additional_info.pct_assay - timepoints_pct.unit_12[rowno - 1]` |
| Mean | `mean` |  | round 1 | `mean(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| SD | `sd` |  | round 1 | `sd(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| %RSD | `rsd` |  | round 2 | `rsd(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| Min. | `min_val` |  | round 1 | `min(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |
| Max. | `max_val` |  | round 1 | `max(unit_1,unit_2,unit_3,unit_4,unit_5,unit_6,unit_7,unit_8,unit_9,unit_10,unit_11,unit_12)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |

---

## TPL-A6A-0004 v1 — Dissolution_12units

**Archetype:** A6a · **Status:** Active

### Section: Standard details for dissolution  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concen. (ppm) | `conc_ppm` | ppm | round 2 | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * potency / 100 * 1000` |

### Section: Standard Co-relation — Weights  (`corel_weights`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| STD-1 Weight | `std1_weight` | mg |  | `standard.weight_mg` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean (STD 1) — from replicates | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |
| Mean (STD 2) | `mean_std2` |  |  | `mean(corel_areas.std2_area)` |
| Standard Co-relation | `std_corelation` | % |  | `trunc(stats.mean_std / stats.mean_std2 * corel_weights.std2_weight / standard.weight_mg, 3) * 100` |
| Mean (pooled BKT) | `mean_bkt_1` |  |  | `mean(pool(std_areas.area, bkt_1.area))` |
| SD (pooled BKT) | `sd_bkt_1` |  |  | `sd(pool(std_areas.area, bkt_1.area))` |
| %RSD (pooled BKT) | `rsd_bkt_1` | % |  | `rsd(pool(std_areas.area, bkt_1.area))` |
| Mean (Cumulative BKT) | `mean_cum_bkt` |  | round 4 | `mean(pool(std_areas.area, bkt_1.area))` |
| %RSD (Cumulative BKT) | `rsd_cum_bkt` | % | round 3 | `rsd(pool(std_areas.area, bkt_1.area))` |

### Section: Bracketing Standard  (`bkt_1`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Pooled Mean | `pooled_mean` |  | round 4 | `mean(pool(std_areas.area, area))` |
| Pooled %RSD | `pooled_rsd` | % | round 3 | `rsd(pool(std_areas.area, area))` |

### Section: System Suitability Criteria  (`sst`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| 4. % RSD of the peak area of Doxorubicin from five replicate injections of Standard solution should be not more than 2.0. | `rsd_replicates` | % | round 5 | `stats.rsd_std` |
| 5. The %RSD of the peak area of Doxorubicin from Bracketing standards and replicate injections of Standard solution should be not more than 2.0. | `rsd_bracketing` | % | round 5 | `stats.rsd_bkt_1` |

### Section: Timepoint of % Release  (`timepoints_release`, sequence)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| media | `media` |  |  | `if(rowno = 1, test_prep.dilution_volume, prev.media - test_prep.withdrawal_volume + test_prep.replenishment_volume)` |
| uncorrected_1 | `uncorrected_1` |  |  | `trunc( time_intervals.unit_1[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_2 | `uncorrected_2` |  |  | `trunc( time_intervals.unit_2[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_3 | `uncorrected_3` |  |  | `trunc( time_intervals.unit_3[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_4 | `uncorrected_4` |  |  | `trunc( time_intervals.unit_4[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_5 | `uncorrected_5` |  |  | `trunc( time_intervals.unit_5[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_6 | `uncorrected_6` |  |  | `trunc( time_intervals.unit_6[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_7 | `uncorrected_7` |  |  | `trunc( time_intervals.unit_7[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_8 | `uncorrected_8` |  |  | `trunc( time_intervals.unit_8[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_9 | `uncorrected_9` |  |  | `trunc( time_intervals.unit_9[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_10 | `uncorrected_10` |  |  | `trunc( time_intervals.unit_10[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_11 | `uncorrected_11` |  |  | `trunc( time_intervals.unit_11[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| uncorrected_12 | `uncorrected_12` |  |  | `trunc( time_intervals.unit_12[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * media / 1 * test_prep.aliquot_volume / test_prep.pippette_2 * standard.potency / (number(label_claim_mgml) * test_prep.sample_volume) * 1 / 1, 3 )` |
| correction_1 | `correction_1` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_1, 3 )` |
| correction_2 | `correction_2` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_2, 3 )` |
| correction_3 | `correction_3` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_3, 3 )` |
| correction_4 | `correction_4` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_4, 3 )` |
| correction_5 | `correction_5` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_5, 3 )` |
| correction_6 | `correction_6` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_6, 3 )` |
| correction_7 | `correction_7` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_7, 3 )` |
| correction_8 | `correction_8` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_8, 3 )` |
| correction_9 | `correction_9` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_9, 3 )` |
| correction_10 | `correction_10` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_10, 3 )` |
| correction_11 | `correction_11` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_11, 3 )` |
| correction_12 | `correction_12` |  |  | `trunc( test_prep.withdrawal_volume / media * uncorrected_12, 3 )` |
| 1 | `unit_1` |  |  | `round( uncorrected_1 + sum(prior.correction_1), 0 )` |
| 2 | `unit_2` |  |  | `round( uncorrected_2 + sum(prior.correction_2), 0 )` |
| 3 | `unit_3` |  |  | `round( uncorrected_3 + sum(prior.correction_3), 0 )` |
| 4 | `unit_4` |  |  | `round( uncorrected_4 + sum(prior.correction_4), 0 )` |
| 5 | `unit_5` |  |  | `round( uncorrected_5 + sum(prior.correction_5), 0 )` |
| 6 | `unit_6` |  |  | `round( uncorrected_6 + sum(prior.correction_6), 0 )` |
| 7 | `unit_7` |  |  | `round( uncorrected_7 + sum(prior.correction_7), 0 )` |
| 8 | `unit_8` |  |  | `round( uncorrected_8 + sum(prior.correction_8), 0 )` |
| 9 | `unit_9` |  |  | `round( uncorrected_9 + sum(prior.correction_9), 0 )` |
| 10 | `unit_10` |  |  | `round( uncorrected_10 + sum(prior.correction_10), 0 )` |
| 11 | `unit_11` |  |  | `round( uncorrected_11 + sum(prior.correction_11), 0 )` |
| 12 | `unit_12` |  |  | `round( uncorrected_12 + sum(prior.correction_12), 0 )` |
| Mean | `mean` |  | round 0 | `mean([unit_1, unit_2, unit_3, unit_4, unit_5, unit_6, unit_7, unit_8, unit_9, unit_10, unit_11, unit_12])` |
| SD | `sd` |  | round 1 | `sd([unit_1, unit_2, unit_3, unit_4, unit_5, unit_6, unit_7, unit_8, unit_9, unit_10, unit_11, unit_12])` |
| %RSD | `rsd` |  | round 1 | `rsd([unit_1, unit_2, unit_3, unit_4, unit_5, unit_6, unit_7, unit_8, unit_9, unit_10, unit_11, unit_12])` |
| Min. | `min_val` |  |  | `min([unit_1, unit_2, unit_3, unit_4, unit_5, unit_6, unit_7, unit_8, unit_9, unit_10, unit_11, unit_12])` |
| Max. | `max_val` |  |  | `max([unit_1, unit_2, unit_3, unit_4, unit_5, unit_6, unit_7, unit_8, unit_9, unit_10, unit_11, unit_12])` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |

---

## TPL-A6A-0005 v1 — Dissolution-Leuprolide-microsphere

**Archetype:** A6a · **Status:** Active · **Reportable result:** `timepoints_release.mean`

### Section: Standard detail  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concentration (ppm) | `conc_ppm` | ppm |  | `weight_mg / dilution_1 * volume_1 / dilution_2 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard statistics  (`std_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `mean_std` |  |  | `mean(std_areas.area)` |
| STDev | `sd_std` |  |  | `sd(std_areas.area)` |
| % RSD | `rsd_std` | % |  | `sd(std_areas.area) * 100 / mean_std` |
| Mean (bracketing) | `mean_bkt` |  |  | `mean(pool(std_areas.area, bkt.area))` |
| STDev (bracketing) | `sd_bkt` |  |  | `sd(pool(std_areas.area, bkt.area))` |
| % RSD (bracketing) | `rsd_bkt` | % |  | `sd(pool(std_areas.area, bkt.area)) * 100 / mean_bkt` |

### Section: Pellet weight statistics  (`weight_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `mean_wt` | mg |  | `mean(weights.weight)` |
| STDev | `sd_wt` | mg |  | `sd(pool(weights.weight, [mean_wt]))` |
| % RSD | `rsd_wt` | % |  | `sd_wt * 100 / mean_wt` |

### Section: Blend parameters / media / replace  (`prep`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Media volume | `media_vol` | mL |  | `params.volume_ml` |

### Section: Cumulative % Release  (`timepoints_release`, sequence)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| jassay_1 | `jassay_1` |  |  | `area_1 / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.weight[1 - 1] * standard.potency * standard.mw_base / standard.mw_salt * prep.avg_weight / prep.label_claim` |
| jassay_2 | `jassay_2` |  |  | `area_2 / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.weight[2 - 1] * standard.potency * standard.mw_base / standard.mw_salt * prep.avg_weight / prep.label_claim` |
| jassay_3 | `jassay_3` |  |  | `area_3 / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.weight[3 - 1] * standard.potency * standard.mw_base / standard.mw_salt * prep.avg_weight / prep.label_claim` |
| jassay_4 | `jassay_4` |  |  | `area_4 / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.weight[4 - 1] * standard.potency * standard.mw_base / standard.mw_salt * prep.avg_weight / prep.label_claim` |
| jassay_5 | `jassay_5` |  |  | `area_5 / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.weight[5 - 1] * standard.potency * standard.mw_base / standard.mw_salt * prep.avg_weight / prep.label_claim` |
| jassay_6 | `jassay_6` |  |  | `area_6 / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.weight[6 - 1] * standard.potency * standard.mw_base / standard.mw_salt * prep.avg_weight / prep.label_claim` |
| kfrac_1 | `kfrac_1` |  |  | `jassay_1 * prep.withdraw_replace / prep.media_vol` |
| kfrac_2 | `kfrac_2` |  |  | `jassay_2 * prep.withdraw_replace / prep.media_vol` |
| kfrac_3 | `kfrac_3` |  |  | `jassay_3 * prep.withdraw_replace / prep.media_vol` |
| kfrac_4 | `kfrac_4` |  |  | `jassay_4 * prep.withdraw_replace / prep.media_vol` |
| kfrac_5 | `kfrac_5` |  |  | `jassay_5 * prep.withdraw_replace / prep.media_vol` |
| kfrac_6 | `kfrac_6` |  |  | `jassay_6 * prep.withdraw_replace / prep.media_vol` |
| Unit-1 | `unit_1` | % |  | `jassay_1 + sum(prior.kfrac_1)` |
| Unit-2 | `unit_2` | % |  | `jassay_2 + sum(prior.kfrac_2)` |
| Unit-3 | `unit_3` | % |  | `jassay_3 + sum(prior.kfrac_3)` |
| Unit-4 | `unit_4` | % |  | `jassay_4 + sum(prior.kfrac_4)` |
| Unit-5 | `unit_5` | % |  | `jassay_5 + sum(prior.kfrac_5)` |
| Unit-6 | `unit_6` | % |  | `jassay_6 + sum(prior.kfrac_6)` |
| Mean | `mean` | % |  | `mean([unit_1, unit_2, unit_3, unit_4, unit_5, unit_6])` |
| Min | `min_val` | % |  | `min([unit_1, unit_2, unit_3, unit_4, unit_5, unit_6])` |
| Max | `max_val` | % |  | `max([unit_1, unit_2, unit_3, unit_4, unit_5, unit_6])` |
| %RSD | `rsd` | % |  | `sd([unit_1, unit_2, unit_3, unit_4, unit_5, unit_6]) * 100 / mean` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `std_stats.rsd_std` | NMT 2.0 % | blocking |

---

## TPL-A6B-0001 v1 — Dissolution (with replacement)

**Archetype:** A6b · **Status:** Active · **Reportable result:** `release.mean`

### Section: Standard Preparation  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concen. (ppm) | `conc_ppm` | ppm | round 3 | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * potency / 100 * 1000` |

### Section: STD-1 / STD-2 Co-Relation  (`corel`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| STD-1 Mean Area | `std1_mean` |  |  | `mean(corel_std1.area)` |
| STD-2 Mean Area | `std2_mean` |  |  | `mean(corel_std2.area)` |
| STD Co-Relation | `co_relation` |  |  | `std1_mean / std2_mean * std2_weight / std1_weight` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `mean_std` |  |  | `mean(std_areas.area)` |
| %RSD | `rsd_std` | % | trunc 5 | `sd(std_areas.area) / mean_std * 100` |
| Bracketing Mean | `mean_bkt` |  | trunc 1 | `mean(pool(std_areas.area, bkt.area))` |
| Bracketing %RSD | `rsd_bkt` | % | trunc 5 | `sd(pool(std_areas.area, bkt.area)) / mean_bkt * 100` |

### Section: System Suitability Criteria  (`sst`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| 4. %RSD of five replicate injections (NMT 2.0) | `item_4` | % |  | `stats.rsd_std` |
| 5. %RSD of bracketing + replicate injections (NMT 2.0) | `item_5` | % |  | `stats.rsd_bkt` |

### Section: Sample Weight  (`gravimetric`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Net Weight | `net` | g | round 5 | `filled - empty` |

### Section: Sample Weight — Summary  (`gravimetric_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `net_mean` | g | round 2 | `mean(gravimetric.net)` |
| Min | `net_min` | g | round 5 | `min(gravimetric.net)` |
| Max | `net_max` | g | round 2 | `max(gravimetric.net)` |

### Section: % Content of Doxorubicin Hydrochloride  (`release`, sequence)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| base_1 | `base_1` |  |  | `sample_area.unit_1[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[0] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_2 | `base_2` |  |  | `sample_area.unit_2[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[1] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_3 | `base_3` |  |  | `sample_area.unit_3[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[2] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_4 | `base_4` |  |  | `sample_area.unit_4[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[3] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_5 | `base_5` |  |  | `sample_area.unit_5[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[4] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_6 | `base_6` |  |  | `sample_area.unit_6[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[5] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_7 | `base_7` |  |  | `sample_area.unit_7[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[6] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_8 | `base_8` |  |  | `sample_area.unit_8[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[7] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_9 | `base_9` |  |  | `sample_area.unit_9[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[8] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_10 | `base_10` |  |  | `sample_area.unit_10[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[9] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_11 | `base_11` |  |  | `sample_area.unit_11[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[10] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| base_12 | `base_12` |  |  | `sample_area.unit_12[rowno - 1] / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * test_prep.total_volume / gravimetric.net[11] * test_prep.dilution_volume / test_prep.aliquot_volume * standard.potency / 100 / number(label_claim) * wt_per_ml * 100` |
| Unit-1 | `content_1` | % |  | `base_1 + coalesce(prev.content_1, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-2 | `content_2` | % |  | `base_2 + coalesce(prev.content_2, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-3 | `content_3` | % |  | `base_3 + coalesce(prev.content_3, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-4 | `content_4` | % |  | `base_4 + coalesce(prev.content_4, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-5 | `content_5` | % |  | `base_5 + coalesce(prev.content_5, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-6 | `content_6` | % |  | `base_6 + coalesce(prev.content_6, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-7 | `content_7` | % |  | `base_7 + coalesce(prev.content_7, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-8 | `content_8` | % |  | `base_8 + coalesce(prev.content_8, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-9 | `content_9` | % |  | `base_9 + coalesce(prev.content_9, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-10 | `content_10` | % |  | `base_10 + coalesce(prev.content_10, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-11 | `content_11` | % |  | `base_11 + coalesce(prev.content_11, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Unit-12 | `content_12` | % |  | `base_12 + coalesce(prev.content_12, 0) * test_prep.withdrawal_volume / test_prep.total_volume` |
| Mean | `mean` | % |  | `mean([content_1, content_2, content_3, content_4, content_5, content_6, content_7, content_8, content_9, content_10, content_11, content_12])` |
| SD | `sd` | % |  | `sd([content_1, content_2, content_3, content_4, content_5, content_6, content_7, content_8, content_9, content_10, content_11, content_12])` |
| %RSD | `rsd` | % |  | `rsd([content_1, content_2, content_3, content_4, content_5, content_6, content_7, content_8, content_9, content_10, content_11, content_12])` |
| Min. | `min_val` | % |  | `min([content_1, content_2, content_3, content_4, content_5, content_6, content_7, content_8, content_9, content_10, content_11, content_12])` |
| Max. | `max_val` | % |  | `max([content_1, content_2, content_3, content_4, content_5, content_6, content_7, content_8, content_9, content_10, content_11, content_12])` |

### Section: % Release of Doxorubicin Hydrochloride  (`amount`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Unit-1 | `remain_1` | % |  | `number(pct_assay) - release.content_1[rowno - 1]` |
| Unit-2 | `remain_2` | % |  | `number(pct_assay) - release.content_2[rowno - 1]` |
| Unit-3 | `remain_3` | % |  | `number(pct_assay) - release.content_3[rowno - 1]` |
| Unit-4 | `remain_4` | % |  | `number(pct_assay) - release.content_4[rowno - 1]` |
| Unit-5 | `remain_5` | % |  | `number(pct_assay) - release.content_5[rowno - 1]` |
| Unit-6 | `remain_6` | % |  | `number(pct_assay) - release.content_6[rowno - 1]` |
| Unit-7 | `remain_7` | % |  | `number(pct_assay) - release.content_7[rowno - 1]` |
| Unit-8 | `remain_8` | % |  | `number(pct_assay) - release.content_8[rowno - 1]` |
| Unit-9 | `remain_9` | % |  | `number(pct_assay) - release.content_9[rowno - 1]` |
| Unit-10 | `remain_10` | % |  | `number(pct_assay) - release.content_10[rowno - 1]` |
| Unit-11 | `remain_11` | % |  | `number(pct_assay) - release.content_11[rowno - 1]` |
| Unit-12 | `remain_12` | % |  | `number(pct_assay) - release.content_12[rowno - 1]` |
| Mean | `mean` | % |  | `mean([remain_1, remain_2, remain_3, remain_4, remain_5, remain_6, remain_7, remain_8, remain_9, remain_10, remain_11, remain_12])` |
| SD | `sd` | % |  | `sd([remain_1, remain_2, remain_3, remain_4, remain_5, remain_6, remain_7, remain_8, remain_9, remain_10, remain_11, remain_12])` |
| %RSD | `rsd` | % |  | `rsd([remain_1, remain_2, remain_3, remain_4, remain_5, remain_6, remain_7, remain_8, remain_9, remain_10, remain_11, remain_12])` |
| Min. | `min_val` | % |  | `min([remain_1, remain_2, remain_3, remain_4, remain_5, remain_6, remain_7, remain_8, remain_9, remain_10, remain_11, remain_12])` |
| Max. | `max_val` | % |  | `max([remain_1, remain_2, remain_3, remain_4, remain_5, remain_6, remain_7, remain_8, remain_9, remain_10, remain_11, remain_12])` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |

---

## TPL-A6B-0002 v1 — Dissolution (Octreotide Acetate, pH 10)

**Archetype:** A6b · **Status:** Active · **Reportable result:** `residue_24hr_stats.mean`

### Section: Standard detail  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concentration (ppm) | `conc_ppm` | ppm |  | `weight_mg / dilution_1 * volume_1 / dilution_2 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard statistics  (`std_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `mean_std` |  |  | `mean(std_areas.area)` |
| STDev | `sd_std` |  |  | `sd(std_areas.area)` |
| % RSD | `rsd_std` | % |  | `sd(std_areas.area) * 100 / mean_std` |
| Mean (bracketing) | `mean_bkt` |  |  | `mean(pool(std_areas.area, bkt.area))` |
| STDev (bracketing) | `sd_bkt` |  |  | `sd(pool(std_areas.area, bkt.area))` |
| % RSD (bracketing) | `rsd_bkt` | % |  | `sd(pool(std_areas.area, bkt.area)) * 100 / mean_bkt` |

### Section: Dissolution Unit weight statistics  (`weight_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean (1 hr) | `mean_1hr` | mg |  | `mean(weights.w_1hr)` |
| STDev (1 hr) | `sd_1hr` | mg |  | `sd(pool(weights.w_1hr, [mean_1hr]))` |
| % RSD (1 hr) | `rsd_1hr` | % |  | `sd_1hr * 100 / mean_1hr` |
| Mean (4 hr) | `mean_4hr` | mg |  | `mean(weights.w_4hr)` |
| STDev (4 hr) | `sd_4hr` | mg |  | `sd(pool(weights.w_4hr, [mean_4hr]))` |
| % RSD (4 hr) | `rsd_4hr` | % |  | `sd_4hr * 100 / mean_4hr` |
| Mean (24 hr) | `mean_24hr` | mg |  | `mean(weights.w_24hr)` |
| STDev (24 hr) | `sd_24hr` | mg |  | `sd(pool(weights.w_24hr, [mean_24hr]))` |
| % RSD (24 hr) | `rsd_24hr` | % |  | `sd_24hr * 100 / mean_24hr` |

### Section: %Residue — 1 hr at 37°C  (`residue_1hr`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| %Residue of Octreotide Base | `residue` | % |  | `area / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.w_1hr[rowno - 1] * standard.potency * standard.mw_base / standard.mw_salt` |

### Section: residue_1hr statistics  (`residue_1hr_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `mean` | % |  | `mean(residue_1hr.residue)` |
| Min | `min_v` | % |  | `min(residue_1hr.residue)` |
| Max | `max_v` | % |  | `max(residue_1hr.residue)` |
| RSD | `rsd` | % |  | `sd(residue_1hr.residue) * 100 / residue_1hr_stats.mean` |

### Section: %Residue — 4 hr at 55°C  (`residue_4hr`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| %Residue of Octreotide Base | `residue` | % |  | `area / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.w_4hr[rowno - 1] * standard.potency * standard.mw_base / standard.mw_salt` |

### Section: residue_4hr statistics  (`residue_4hr_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `mean` | % |  | `mean(residue_4hr.residue)` |
| Min | `min_v` | % |  | `min(residue_4hr.residue)` |
| Max | `max_v` | % |  | `max(residue_4hr.residue)` |
| RSD | `rsd` | % |  | `sd(residue_4hr.residue) * 100 / residue_4hr_stats.mean` |

### Section: %Residue — 24 hr at 55°C  (`residue_24hr`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| %Residue of Octreotide Base | `residue` | % |  | `area / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.w_24hr[rowno - 1] * standard.potency * standard.mw_base / standard.mw_salt` |

### Section: residue_24hr statistics  (`residue_24hr_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `mean` | % |  | `mean(residue_24hr.residue)` |
| Min | `min_v` | % |  | `min(residue_24hr.residue)` |
| Max | `max_v` | % |  | `max(residue_24hr.residue)` |
| RSD | `rsd` | % |  | `sd(residue_24hr.residue) * 100 / residue_24hr_stats.mean` |

### Section: % Results  (`results_banner`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| _banner | `_banner` |  |  | `blank()` |

### Section: %Release — 1 hr at 37°C  (`release_1hr`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| %Release of Octreotide Base | `rel` | % |  | `(number(prep.pct_assay) - residue_in) / number(prep.pct_assay) * 100` |

### Section: release_1hr statistics  (`release_1hr_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `mean` | % |  | `mean(release_1hr.rel)` |
| Min | `min_v` | % |  | `min(release_1hr.rel)` |
| Max | `max_v` | % |  | `max(release_1hr.rel)` |
| RSD | `rsd` | % |  | `sd(release_1hr.rel) * 100 / release_1hr_stats.mean` |

### Section: %Release — 4 hr at 55°C  (`release_4hr`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| %Release of Octreotide Base | `rel` | % |  | `(number(prep.pct_assay) - residue_in) / number(prep.pct_assay) * 100` |

### Section: release_4hr statistics  (`release_4hr_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `mean` | % |  | `mean(release_4hr.rel)` |
| Min | `min_v` | % |  | `min(release_4hr.rel)` |
| Max | `max_v` | % |  | `max(release_4hr.rel)` |
| RSD | `rsd` | % |  | `sd(release_4hr.rel) * 100 / release_4hr_stats.mean` |

### Section: %Release — 24 hr at 55°C  (`release_24hr`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| %Release of Octreotide Base | `rel` | % |  | `(number(prep.pct_assay) - residue_in) / number(prep.pct_assay) * 100` |

### Section: release_24hr statistics  (`release_24hr_stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean | `mean` | % |  | `mean(release_24hr.rel)` |
| Min | `min_v` | % |  | `min(release_24hr.rel)` |
| Max | `max_v` | % |  | `max(release_24hr.rel)` |
| RSD | `rsd` | % |  | `sd(release_24hr.rel) * 100 / release_24hr_stats.mean` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `std_stats.rsd_std` | NMT 2.0 % | blocking |

---

## TPL-A6C-0001 v1 — Dissolution (whole vial, residual content)

**Archetype:** A6c · **Status:** Active · **Reportable result:** `units.mean_released`

### Section: Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |

### Section: Units (bottle-rotating, per-unit weight)  (`units`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Residual Content | `residue_pct` | % | round 1 | `area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * standard.potency / 100 * s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 * s_vol_1 / unit_weight * avg_weight / label_claim * 100` |
| Released | `released` | % | round 1 | `(batch_assay - residue_pct) / batch_assay * 100` |
| Mean Released | `mean_released` | % | round 1 | `mean(units.released)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| %RSD across units | `rsd(units.released)` | NMT 10.0 % | advisory |

---

## TPL-A6D-0001 v1 — In-Vitro Release (Franz Diffusion Cell)

**Archetype:** A6d · **Status:** Active · **Reportable result:** `flux.mean_flux`

### Section: Calibration Standards  (`calibration`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Theoretical Conc. | `theoretical_ppm` | ppm |  | `weight_mg / c_vol_1 * c_pip_1 / c_vol_2 * c_pip_2 / c_vol_3 * potency / 100 * 1000` |
| Observed Conc. | `observed_ppm` | ppm |  | `(area - curve.curve_intercept) / curve.curve_slope` |
| % Recovery | `recovery_pct` | % | round 2 | `observed_ppm / theoretical_ppm * 100` |

### Section: Regression  (`curve`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Slope | `curve_slope` | area / ppm | round 2 | `slope(calibration.area, calibration.theoretical_ppm)` |
| Intercept | `curve_intercept` |  | round 2 | `intercept(calibration.area, calibration.theoretical_ppm)` |
| Correlation (r) | `correlation` |  | round 4 | `correl(calibration.area, calibration.theoretical_ppm)` |

### Section: Bracketing QC Standards  (`qc`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Observed Conc. | `observed_ppm` | ppm |  | `(area - curve.curve_intercept) / curve.curve_slope` |
| % Recovery | `recovery_pct` | % | round 2 | `observed_ppm / theoretical_ppm * 100` |

### Section: Sampling Timepoints  (`timepoints`, sequence)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| √Time | `sqrt_hours` | √h |  | `sqrt(time_min / 60)` |
| Cell 1 Conc. | `conc_1` | ppm |  | `(area_1 - curve.curve_intercept) / curve.curve_slope` |
| Cell 2 Conc. | `conc_2` | ppm |  | `(area_2 - curve.curve_intercept) / curve.curve_slope` |
| Cell 3 Conc. | `conc_3` | ppm |  | `(area_3 - curve.curve_intercept) / curve.curve_slope` |
| Cell 4 Conc. | `conc_4` | ppm |  | `(area_4 - curve.curve_intercept) / curve.curve_slope` |
| Cell 5 Conc. | `conc_5` | ppm |  | `(area_5 - curve.curve_intercept) / curve.curve_slope` |
| Cell 6 Conc. | `conc_6` | ppm |  | `(area_6 - curve.curve_intercept) / curve.curve_slope` |
| Cell 1 Amount (uncorrected) | `amount_1` | µg |  | `conc_1 * sample_vol / sample_pip * receptor_volume` |
| Cell 2 Amount (uncorrected) | `amount_2` | µg |  | `conc_2 * sample_vol / sample_pip * receptor_volume` |
| Cell 3 Amount (uncorrected) | `amount_3` | µg |  | `conc_3 * sample_vol / sample_pip * receptor_volume` |
| Cell 4 Amount (uncorrected) | `amount_4` | µg |  | `conc_4 * sample_vol / sample_pip * receptor_volume` |
| Cell 5 Amount (uncorrected) | `amount_5` | µg |  | `conc_5 * sample_vol / sample_pip * receptor_volume` |
| Cell 6 Amount (uncorrected) | `amount_6` | µg |  | `conc_6 * sample_vol / sample_pip * receptor_volume` |
| Cell 1 carry-over | `carry_1` | µg |  | `sum(prior.amount_1) * replacement_volume / receptor_volume` |
| Cell 2 carry-over | `carry_2` | µg |  | `sum(prior.amount_2) * replacement_volume / receptor_volume` |
| Cell 3 carry-over | `carry_3` | µg |  | `sum(prior.amount_3) * replacement_volume / receptor_volume` |
| Cell 4 carry-over | `carry_4` | µg |  | `sum(prior.amount_4) * replacement_volume / receptor_volume` |
| Cell 5 carry-over | `carry_5` | µg |  | `sum(prior.amount_5) * replacement_volume / receptor_volume` |
| Cell 6 carry-over | `carry_6` | µg |  | `sum(prior.amount_6) * replacement_volume / receptor_volume` |
| Cell 1 Cumulative | `cumulative_1` | µg |  | `amount_1 + carry_1` |
| Cell 2 Cumulative | `cumulative_2` | µg |  | `amount_2 + carry_2` |
| Cell 3 Cumulative | `cumulative_3` | µg |  | `amount_3 + carry_3` |
| Cell 4 Cumulative | `cumulative_4` | µg |  | `amount_4 + carry_4` |
| Cell 5 Cumulative | `cumulative_5` | µg |  | `amount_5 + carry_5` |
| Cell 6 Cumulative | `cumulative_6` | µg |  | `amount_6 + carry_6` |
| Cell 1 Cumulative / Area | `per_area_1` | µg/cm² |  | `cumulative_1 / donor_area` |
| Cell 2 Cumulative / Area | `per_area_2` | µg/cm² |  | `cumulative_2 / donor_area` |
| Cell 3 Cumulative / Area | `per_area_3` | µg/cm² |  | `cumulative_3 / donor_area` |
| Cell 4 Cumulative / Area | `per_area_4` | µg/cm² |  | `cumulative_4 / donor_area` |
| Cell 5 Cumulative / Area | `per_area_5` | µg/cm² |  | `cumulative_5 / donor_area` |
| Cell 6 Cumulative / Area | `per_area_6` | µg/cm² |  | `cumulative_6 / donor_area` |
| Cell 1 Released | `released_pct_1` | % | round 2 | `cumulative_1 / (cells.applied_mg_1 * label_claim / 100 * 1000) * 100` |
| Cell 2 Released | `released_pct_2` | % | round 2 | `cumulative_2 / (cells.applied_mg_2 * label_claim / 100 * 1000) * 100` |
| Cell 3 Released | `released_pct_3` | % | round 2 | `cumulative_3 / (cells.applied_mg_3 * label_claim / 100 * 1000) * 100` |
| Cell 4 Released | `released_pct_4` | % | round 2 | `cumulative_4 / (cells.applied_mg_4 * label_claim / 100 * 1000) * 100` |
| Cell 5 Released | `released_pct_5` | % | round 2 | `cumulative_5 / (cells.applied_mg_5 * label_claim / 100 * 1000) * 100` |
| Cell 6 Released | `released_pct_6` | % | round 2 | `cumulative_6 / (cells.applied_mg_6 * label_claim / 100 * 1000) * 100` |
| Mean Cumulative / Area | `mean_per_area` | µg/cm² | round 3 | `mean([per_area_1, per_area_2, per_area_3, per_area_4, per_area_5, per_area_6])` |
| %RSD Across Cells | `rsd_per_area` | % | round 1 | `rsd([per_area_1, per_area_2, per_area_3, per_area_4, per_area_5, per_area_6])` |

### Section: Release Rate  (`flux`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Cell 1 Flux | `flux_1` | µg/cm²/√h | round 2 | `slope(timepoints.per_area_1, timepoints.sqrt_hours)` |
| Cell 2 Flux | `flux_2` | µg/cm²/√h | round 2 | `slope(timepoints.per_area_2, timepoints.sqrt_hours)` |
| Cell 3 Flux | `flux_3` | µg/cm²/√h | round 2 | `slope(timepoints.per_area_3, timepoints.sqrt_hours)` |
| Cell 4 Flux | `flux_4` | µg/cm²/√h | round 2 | `slope(timepoints.per_area_4, timepoints.sqrt_hours)` |
| Cell 5 Flux | `flux_5` | µg/cm²/√h | round 2 | `slope(timepoints.per_area_5, timepoints.sqrt_hours)` |
| Cell 6 Flux | `flux_6` | µg/cm²/√h | round 2 | `slope(timepoints.per_area_6, timepoints.sqrt_hours)` |
| Cell 1 Higuchi r | `fit_1` |  | round 4 | `correl(timepoints.per_area_1, timepoints.sqrt_hours)` |
| Cell 2 Higuchi r | `fit_2` |  | round 4 | `correl(timepoints.per_area_2, timepoints.sqrt_hours)` |
| Cell 3 Higuchi r | `fit_3` |  | round 4 | `correl(timepoints.per_area_3, timepoints.sqrt_hours)` |
| Cell 4 Higuchi r | `fit_4` |  | round 4 | `correl(timepoints.per_area_4, timepoints.sqrt_hours)` |
| Cell 5 Higuchi r | `fit_5` |  | round 4 | `correl(timepoints.per_area_5, timepoints.sqrt_hours)` |
| Cell 6 Higuchi r | `fit_6` |  | round 4 | `correl(timepoints.per_area_6, timepoints.sqrt_hours)` |
| Mean Flux | `mean_flux` | µg/cm²/√h | round 2 | `mean([flux_1, flux_2, flux_3, flux_4, flux_5, flux_6])` |
| %RSD of Flux | `rsd_flux` | % | round 1 | `rsd([flux_1, flux_2, flux_3, flux_4, flux_5, flux_6])` |
| Poorest Higuchi Fit | `min_fit` |  | round 4 | `min([fit_1, fit_2, fit_3, fit_4, fit_5, fit_6])` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Correlation of the calibration curve | `curve.correlation` | NLT 0.99 | blocking |
| Lowest bracketing QC recovery | `min(qc.recovery_pct)` | NLT 85 % (convention) | advisory |
| Highest bracketing QC recovery | `max(qc.recovery_pct)` | NMT 115 % (convention) | advisory |
| Poorest per-cell Higuchi correlation | `flux.min_fit` | NLT 0.97 (SUPAC-SS) | advisory |
| %RSD of flux across cells | `flux.rsd_flux` | NMT 15 % (convention) | advisory |

---

## TPL-A7-0001 v1 — Dissolution Profile Comparison (f1 / f2)

**Archetype:** A7 · **Status:** Active · **Reportable result:** `comparison.f2`

### Section: Mean % Dissolved by Time Point  (`timepoints`, sequence)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| | R(t) − T(t) | | `abs_diff` | % |  | `if(included > 0, abs(ref_mean - test_mean), blank())` |
| [ R(t) − T(t) ]² | `sq_diff` |  |  | `abs_diff ^ 2` |
| R(t) counted in Σ R(t) | `ref_in_scope` | % |  | `if(isblank(abs_diff), blank(), ref_mean)` |
| Reference > 85 % (counted) | `ref_over_85` |  |  | `if(isblank(abs_diff), 0, if(ref_mean > 85, 1, 0))` |
| Test > 85 % (counted) | `test_over_85` |  |  | `if(isblank(abs_diff), 0, if(test_mean > 85, 1, 0))` |
| Worst %RSD of the two products | `worst_rsd` | % |  | `max([ref_rsd, test_rsd])` |
| %RSD recorded | `has_rsd` |  |  | `if(isblank(worst_rsd), 0, 1)` |
| Applicable %RSD limit | `rsd_limit` | % |  | `if(has_rsd > 0 and sum(prior.has_rsd) = 0, 20, 10)` |
| %RSD outside limit | `rsd_breach` |  |  | `if(isblank(worst_rsd), 0, if(worst_rsd > rsd_limit, 1, 0))` |

### Section: f1 / f2 Comparison  (`comparison`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| n (time points compared) | `n_points` |  |  | `if(count(timepoints.sq_diff) > 0, count(timepoints.sq_diff), blank())` |
| Σ | R(t) − T(t) | | `sum_abs_diff` | % |  | `if(isblank(n_points), blank(), sum(timepoints.abs_diff))` |
| Σ R(t) — reference product | `sum_ref` | % |  | `if(isblank(n_points), blank(), sum(timepoints.ref_in_scope))` |
| Σ [ R(t) − T(t) ]² | `sum_sq_diff` |  |  | `if(isblank(n_points), blank(), sum(timepoints.sq_diff))` |
| Σ [ R(t) − T(t) ]² / n | `mean_sq_diff` |  |  | `sum_sq_diff / n_points` |
| f1 — difference factor | `f1` |  | round 1 | `sum_abs_diff / sum_ref * 100` |
| f2 — similarity factor | `f2` |  | round 1 | `50 * log10(100 / sqrt(1 + mean_sq_diff))` |
| Included time points above 85 % (worse product) | `points_over_85` |  |  | `if(isblank(n_points), blank(), max([sum(timepoints.ref_over_85), sum(timepoints.test_over_85)]))` |
| Time points outside the %RSD limit | `rsd_breaches` |  |  | `if(isblank(n_points), blank(), sum(timepoints.rsd_breach))` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Time points included in the comparison | `comparison.n_points` | NLT 3 | blocking |
| Included mean values above 85 % dissolved, per product | `comparison.points_over_85` | NMT 1 | blocking |
| Time points outside the %RSD limit (NMT 20 % at the first, NMT 10 % thereafter) | `comparison.rsd_breaches` | None | blocking |
| f2 — similarity factor | `comparison.f2` | NLT 50 for similar profiles | advisory |
| f1 — difference factor | `comparison.f1` | NMT 15 for similar profiles | advisory |

---

## TPL-A8-0001 v1 — Content Uniformity by HPLC

**Archetype:** A8 · **Status:** Inactive · **Reportable result:** `summary.acceptance_value`

### Section: STD Prep.  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | µg/mL |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * additional_info.mw_base / additional_info.mw_salt * additional_info.std_potency / 100 * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD STD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD STD | `rsd_std` | % | round 1 | `rsd(std_areas.area)` |
| Mean BKT Area | `mean_bkt` |  |  | `mean(std_areas.bkt_area)` |
| %RSD BKT | `rsd_bkt` | % | round 1 | `rsd(std_areas.bkt_area)` |

### Section: Individual Units  (`units`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| % C.U. | `pct_lc` | % | round 1 | `area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * additional_info.std_potency / 100 * additional_info.mw_base / additional_info.mw_salt * sample_dil.s_vol_1 / sample_dil.s_pip_1 * sample_dil.s_vol_2 / sample_dil.s_pip_2 * sample_dil.s_vol_3 / additional_info.label_claim_mg * 100` |

### Section: Uniformity Assessment  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Units Tested | `unit_count` |  |  | `count(units.pct_lc)` |
| Mean (X) | `mean_pct` | % | round 1 | `mean(units.pct_lc)` |
| Minimum | `min_pct` | % | round 1 | `min(units.pct_lc)` |
| Maximum | `max_pct` | % | round 1 | `max(units.pct_lc)` |
| SD (s) | `sd_pct` |  | round 2 | `sd(units.pct_lc)` |
| % RSD | `rsd_pct` | % | round 2 | `rsd(units.pct_lc)` |
| M | `m_value` |  | round 1 | `if(mean_pct < 98.5, 98.5, if(mean_pct > 101.5, 101.5, mean_pct))` |
| Acceptance Value (AV) | `acceptance_value` |  | round 1 | `if(mean_pct < 98.5, (98.5 - mean_pct) + additional_info.k_value * sd_pct, if(mean_pct > 101.5, (mean_pct - 101.5) + additional_info.k_value * sd_pct, additional_info.k_value * sd_pct))` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| Acceptance Value | `summary.acceptance_value` | NMT 15.0 | blocking |

---

## TPL-A8-0001 v2 — Content Uniformity by HPLC-v2

**Archetype:** A8 · **Status:** Active · **Reportable result:** `summary.acceptance_value`

### Section: STD Prep.  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | µg/mL |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * 1000` |

### Section: Sample Preparation Test Prep  (`sample_dil`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Conc. | `conc` | ppm | round 4 | `s_weight / s_vol_1 * s_pip_1 / s_vol_2 * s_pip_2 / s_vol_3` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD STD | `sd_std` |  | round 1 | `sd(std_areas.area)` |
| %RSD STD | `rsd_std` | % | round 1 | `rsd(std_areas.area)` |
| Mean BKT Area | `mean_bkt` |  |  | `mean(std_areas.bkt_area)` |
| SD BKT | `sd_bkt` |  | round 1 | `sd(std_areas.bkt_area)` |
| %RSD BKT | `rsd_bkt` | % | round 1 | `rsd(std_areas.bkt_area)` |

### Section: Individual Units  (`units`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| % L.C. | `pct_lc` | % | round 1 | `area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * sample_dil.s_vol_1 / sample_dil.s_pip_1 * sample_dil.s_vol_2 / sample_dil.s_pip_2 * sample_dil.s_vol_3 * additional_info.assay / 100 * additional_info.factor / additional_info.label_claim_mg * 100` |

### Section: Uniformity Assessment  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Units Tested | `unit_count` |  |  | `count(units.pct_lc)` |
| Mean (X) | `mean_pct` | % | round 1 | `mean(units.pct_lc)` |
| Minimum | `min_pct` | % | round 1 | `min(units.pct_lc)` |
| Maximum | `max_pct` | % | round 1 | `max(units.pct_lc)` |
| SD (s) | `sd_pct` |  | round 2 | `sd(units.pct_lc)` |
| % RSD | `rsd_pct` | % | round 2 | `rsd(units.pct_lc)` |
| M | `m_value` |  | round 1 | `if(mean_pct < 98.5, 98.5, if(mean_pct > 101.5, 101.5, mean_pct))` |
| Acceptance Value (AV) | `acceptance_value` |  | round 1 | `if(mean_pct < 98.5, (98.5 - mean_pct) + additional_info.k_value * sd_pct, if(mean_pct > 101.5, (mean_pct - 101.5) + additional_info.k_value * sd_pct, additional_info.k_value * sd_pct))` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| Acceptance Value | `summary.acceptance_value` | NMT 15.0 | blocking |

---

## TPL-A8-0002 v1 — Content Uniformity by Weight Variation

**Archetype:** A8 · **Status:** Active · **Reportable result:** `summary.acceptance_value`

### Section: Individual Units (gravimetric)  (`units`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Net Wt. | `net_weight` | mg | round 2 | `filled_weight - empty_weight` |
| % C.U (raw) | `pct_cu_raw` |  |  | `net_weight / avg_weights.av_net_weight * additional_info.pct_assay` |
| % C.U | `pct_lc` | % | round 1 | `net_weight / avg_weights.av_net_weight * additional_info.pct_assay` |

### Section: Average Weights  (`avg_weights`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Av. Filled Weight (mg) | `av_filled_weight` | mg | round 2 | `mean(units.filled_weight)` |
| Av. Empty Weight (mg) | `av_empty_weight` | mg | round 2 | `mean(units.empty_weight)` |
| Av. Net Weight (mg) | `av_net_weight` | mg | round 2 | `av_filled_weight - av_empty_weight` |

### Section: Uniformity Assessment  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Units Tested | `unit_count` |  |  | `count(units.pct_cu_raw)` |
| Mean (X) | `mean_pct` | % | round 1 | `mean(units.pct_cu_raw)` |
| SD (s) | `sd_pct` |  | round 2 | `sd(units.pct_cu_raw)` |
| %RSD | `rsd_pct` | % | round 2 | `rsd(units.pct_cu_raw)` |
| Minimum | `min_pct` | % | round 1 | `min(units.pct_cu_raw)` |
| Maximum | `max_pct` | % | round 1 | `max(units.pct_cu_raw)` |
| Acceptance Value (AV) | `acceptance_value` |  | round 1 | `if(mean_pct < 101.5, if(mean_pct < 98.5, (98.5 - mean_pct) + k_value * sd_pct, k_value * sd_pct), (mean_pct - 101.5) + k_value * sd_pct)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| Acceptance Value | `summary.acceptance_value` | NMT 15.0 | blocking |
| Units tested (stage 1) | `count(units.pct_lc)` | NLT 10 units | advisory |

---

## TPL-A8-0003 v1 — content uniformity for tablet

**Archetype:** A8 · **Status:** Draft · **Reportable result:** `summary.acceptance_value`

### Section: Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |

### Section: Individual Units  (`units`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| % of Label Claim | `pct_lc` | % | round 1 | `area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * standard.potency / 100 * standard.mw_base / standard.mw_salt * s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 * s_vol_1 / unit_weight * avg_weight / label_claim * 100` |

### Section: Uniformity Assessment  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Units Tested | `unit_count` |  |  | `count(units.pct_lc)` |
| Mean (X) | `mean_pct` | % | round 1 | `mean(units.pct_lc)` |
| SD (s) | `sd_pct` |  | round 4 | `sd(units.pct_lc)` |
| %RSD | `rsd_pct` | % | round 1 | `rsd(units.pct_lc)` |
| Minimum | `min_pct` | % |  | `min(units.pct_lc)` |
| Maximum | `max_pct` | % |  | `max(units.pct_lc)` |
| Acceptance Value (AV) | `acceptance_value` |  | round 1 | `if(mean_pct < 101.5, if(mean_pct < 98.5, (98.5 - mean_pct) + k_value * sd_pct, k_value * sd_pct), (mean_pct - 101.5) + k_value * sd_pct)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| Acceptance Value | `summary.acceptance_value` | NMT 15.0 | blocking |
| Units tested (stage 1) | `count(units.pct_lc)` | NLT 10 units | advisory |

---

## TPL-A8-0004 v1 — Content Uniformity by HPLC — 30 Units (Stage 2)

**Archetype:** A8 · **Status:** Active · **Reportable result:** `summary.acceptance_value`

### Section: Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |
| Mean (pooled with bracketing standards) | `mean_bkt` |  |  | `mean(pool(std_areas.area, bkt_1.area))` |
| SD (pooled with bracketing standards) | `sd_bkt` |  |  | `sd(pool(std_areas.area, bkt_1.area))` |
| %RSD (pooled with bracketing standards) | `rsd_bkt` | % |  | `rsd(pool(std_areas.area, bkt_1.area))` |

### Section: Standard Suitability Summary (STD vs BKT)  (`suitability_summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean (STD) | `mean_std_disp` |  |  | `stats.mean_std` |
| % RSD (STD) | `rsd_std_disp` | % |  | `stats.rsd_std` |
| Mean (BKT, pooled) | `mean_bkt_disp` |  |  | `stats.mean_bkt` |
| % RSD (BKT, pooled) | `rsd_bkt_disp` | % |  | `stats.rsd_bkt` |

### Section: Individual Units  (`units`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| % C.U. | `pct_lc` |  | round 1 | `area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * standard.potency / 100 * standard.mw_base / standard.mw_salt * sample_dilution.s_vol_1 / sample_dilution.s_pip_1 * sample_dilution.s_vol_2 / sample_dilution.s_pip_2 * sample_dilution.s_vol_3 * avg_weight / label_claim * 100` |

### Section: Uniformity Assessment  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Units Tested | `unit_count` |  |  | `count(units.pct_lc)` |
| Mean (X) | `mean_pct` | % | round 1 | `mean(units.pct_lc)` |
| SD (s) | `sd_pct` |  | round 4 | `sd(units.pct_lc)` |
| %RSD | `rsd_pct` | % | round 1 | `rsd(units.pct_lc)` |
| Minimum | `min_pct` | % |  | `min(units.pct_lc)` |
| Maximum | `max_pct` | % |  | `max(units.pct_lc)` |
| Acceptance Value (AV) | `acceptance_value` |  | round 1 | `if(mean_pct < 101.5, if(mean_pct < 98.5, (98.5 - mean_pct) + additional_info.k_value * sd_pct, additional_info.k_value * sd_pct), (mean_pct - 101.5) + additional_info.k_value * sd_pct)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| %RSD of pooled bracketing standards | `stats.rsd_bkt` | NMT 2.0 % | blocking |
| Acceptance Value | `summary.acceptance_value` | NMT 15.0 | blocking |
| Units tested (stage 1) | `count(units.pct_lc)` | NLT 10 units | advisory |

---

## TPL-A9-0001 v1 — Assay by Titration

**Archetype:** A9 · **Status:** Active · **Reportable result:** `determinations.mean_pct_lc`

### Section: Determinations  (`determinations`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Net Titre | `net_titre` | mL | round 2 | `titre_ml - blank_ml` |
| Content | `mg_per_ml` | mg/mL | round 4 | `(net_titre * normality * equivalence_factor * 1000) / (sample_ml * 1000)` |
| % of Label Claim | `pct_lc` | % | round 2 | `mg_per_ml / label_claim * 100` |
| Mean % of Label Claim | `mean_pct_lc` | % | round 2 | `mean(determinations.pct_lc)` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD between determinations | `rsd(determinations.pct_lc)` | NMT 2.0 % | blocking |

---

## TPL-H1-0001 v1 — HPLC RS - two wavelength

**Archetype:** A4 · **Status:** Active · **Reportable result:** `summary.total_impurities`

### Section: Reference Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Reference Standard 2 Details  (`standard_2`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Standard Concentration | `conc_ppm` | ppm |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |

### Section: Standard Statistics 2  (`stats_2`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas_2.area)` |
| SD | `sd_std` |  |  | `sd(std_areas_2.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas_2.area)` |

### Section: Impurities  (`impurities`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Avg. Area | `avg_area` |  |  | `mean([area_1, area_2])` |
| RRT | `rrt` |  | round 3 | `rt / main_peak_rt` |
| % (before RRF) | `pct_uncorrected` | % |  | `avg_area / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * sample_prep.s_vol_2 / sample_prep.s_pip_1 * sample_prep.s_vol_3 / sample_prep.s_pip_2 * sample_prep.s_vol_1 / sample_prep.sample_weight * standard.potency / 100 * standard.mw_base / standard.mw_salt * 100` |
| % w/w | `pct` | % | round 3 | `if(rrf_mode = "RRF (multiplication factor)", pct_uncorrected * rrf, pct_uncorrected / rrf)` |
| % counted in total | `pct_for_total` | % |  | `if(pct < loq, 0, pct)` |
| Reported | `reported` |  |  | `if(pct < loq, "BLQ", pct)` |

### Section: Summary  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Single Maximum Impurity | `max_single_impurity` | % | round 3 | `if(isblank(mean(impurities.pct)), blank(), max(impurities.pct_for_total))` |
| Total Impurities | `total_impurities` | % | round 3 | `if(isblank(mean(impurities.pct)), blank(), sum(impurities.pct_for_total))` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| Single maximum impurity | `max(impurities.pct_for_total)` | NMT 0.2 % | advisory |
| Total impurities | `sum(impurities.pct_for_total)` | NMT 1.0 % | advisory |

---

## TPL-H1-0002 v1 — RS-HPLC-Two-wavelenght-Ampho

**Archetype:** A4 · **Status:** Active · **Reportable result:** `summary.total_impurities`

### Section: Reference Standard Details  (`standard`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concentration | `conc_ppm` | µg/ml |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Reference Standard 2 Details  (`standard_2`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Concentration | `conc_ppm` | µg/ml |  | `weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 * mw_base / mw_salt * potency / 100 * 1000` |

### Section: Standard Statistics  (`stats`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas.area)` |
| SD | `sd_std` |  |  | `sd(std_areas.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas.area)` |

### Section: Standard Statistics 2  (`stats_2`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Mean STD Area | `mean_std` |  |  | `mean(std_areas_2.area)` |
| SD | `sd_std` |  |  | `sd(std_areas_2.area)` |
| %RSD | `rsd_std` | % |  | `rsd(std_areas_2.area)` |

### Section: Impurities  (`impurities`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| RRT | `rrt` |  | round 2 | `coalesce(rt, 0) / main_peak.rt_main` |
| % Impurity | `pct` | % | round 3 | `coalesce(response, 0) / stats.mean_std * standard.weight_mg / standard.vol_1 * standard.pip_1 / standard.vol_2 * standard.pip_2 / standard.vol_3 * sample_prep.s_vol_2 / sample_prep.s_pip_1 * sample_prep.s_vol_1 / sample_prep.sample_weight * sample_prep.avg_weight_mg / sample_prep.label_claim_mg * standard.potency / 100 * standard.mw_base / standard.mw_salt * 100 / rrf` |
| Reporting % Impurity | `reported` |  |  | `if(pct < loq, "BLQ", pct)` |
| % counted in total | `pct_for_total` | % |  | `if(pct < loq, 0, pct)` |
| % excl Impurity-B | `pct_excl_b` |  |  | `if(name = "Impurity-B" or name = "Impurity B", 0, pct_for_total)` |

### Section: Impurities (Standard 2)  (`impurities_2`, table)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| RRT | `rrt` |  | round 2 | `coalesce(rt, 0) / main_peak.rt_main` |
| % Impurity | `pct` | % | round 3 | `coalesce(response, 0) / stats_2.mean_std * standard_2.weight_mg / standard_2.vol_1 * standard_2.pip_1 / standard_2.vol_2 * standard_2.pip_2 / standard_2.vol_3 * sample_prep.s_vol_2 / sample_prep.s_pip_1 * sample_prep.s_vol_1 / sample_prep.sample_weight * sample_prep.avg_weight_mg / sample_prep.label_claim_mg * standard_2.potency / 100 * standard_2.mw_base / standard_2.mw_salt * 100 / rrf` |
| Reporting % Impurity | `reported` |  |  | `if(pct < loq, "BLQ", pct)` |
| % counted in total | `pct_for_total` | % |  | `if(pct < loq, 0, pct)` |
| % excl Impurity-B | `pct_excl_b` |  |  | `if(name = "Impurity-B" or name = "Impurity B", 0, pct_for_total)` |

### Section: Summary  (`summary`, singleton)

| Field | Key | Unit | Rounding | Formula |
|-------|-----|------|----------|---------|
| Single unknown impurity at 303nm (NMT 1.0%) | `single_unknown_303` |  | round 3 | `if(isblank(mean(impurities.pct)), blank(), max(impurities.pct_for_total))` |
| Single unknown impurity at 383nm (NMT 2.0%) | `single_unknown_383` |  | round 3 | `if(isblank(mean(impurities_2.pct)), blank(), max(impurities_2.pct_for_total))` |
| Total Impurity excluding Impurity B | `total_excl_impurity_b` |  | round 3 | `if(isblank(mean(impurities.pct)) and isblank(mean(impurities_2.pct)), blank(), sum(impurities.pct_excl_b) + sum(impurities_2.pct_excl_b))` |
| Total Impurities (NMT 15.0%) | `total_impurities` |  | round 3 | `if(isblank(mean(impurities.pct)) and isblank(mean(impurities_2.pct)), blank(), sum(impurities.pct_for_total) + sum(impurities_2.pct_for_total))` |

**Acceptance criteria**

| Criterion | Target | Limit | Severity |
|-----------|--------|-------|----------|
| %RSD of standard replicate injections | `stats.rsd_std` | NMT 2.0 % | blocking |
| Single maximum impurity | `max(impurities.pct_for_total)` | NMT 0.2 % | advisory |
| Total impurities | `sum(impurities.pct_for_total)` | NMT 1.0 % | advisory |

---
