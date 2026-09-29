# R&D Analytical Test Calculation Workbooks — Structured Catalog

Source folder: `d:\Anti Gravity LIMS\rd-lab-instance\Test types`
Workbooks catalogued: **35** (27 `.xlsx` + 8 `.xls`). *Note: the folder contains 35 files, not 36 — see "Discrepancies" at the end.*

Extraction method: `.xlsx` read with `openpyxl(data_only=False)` so raw formulas are captured. The 8 legacy `.xls` files were losslessly converted to `.xlsx` via Excel automation (formulas preserved) before reading, because `xlrd` cannot expose formula text.

## Field classification legend

| Class | Meaning |
|---|---|
| `CONTEXT` | Identity/header metadata the LIMS already knows and must auto-populate (generic name, product, label claim, TRF/AR/batch no., test name, MOA no., date, analyst, instrument, condition, packing). |
| `INPUT_AREA` | **Chromatography-system value (peak AREA / RT / height).** Comes from Waters Empower or equivalent. Manual entry for now — these are the integration-critical fields. |
| `INPUT_WEIGHING` | Physically measured / operator-entered numeric (weights, volumes, pipette aliquots, potency, LC, MW, RRF, media volume, suitability numbers). |
| `COMPUTED` | Derived by an Excel formula. Raw formula + plain algebraic translation recorded. |
| `CONSTANT` | Hard-coded literal inside a formula or a fixed cell (e.g. `495`, `490`, `0.997043`, `k=2.4`). |

---

## 1. `Assay by HPLC.xlsx`

- **Test category:** Assay by HPLC (single-standard external-standard assay), stability-oriented (Amphotericin B Liposome for Injection 50 mg/vial).
- **Sheet(s):** `1` (single sheet). Dimensions `A1:R69`.
- **Layout shape:** Header block → *Standard Details* block (single standard row + 3 injection-set columns: STD / BKT STD / BKT STD continued) → *STD Co-Relation* mini-block → *Sample Details* repeating row-pair grid (16 sample slots in row pairs, grouped in 4s for `% Mean Assay`).
- **Archetype:** A1 — single-standard + sample-rows assay.

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Emcure / R & D Ahmedabad / Analytical Development / Assay Calculation Sheet | A1:A4 | CONSTANT | Static letterhead text |
| Generic Name | B6 | CONTEXT | `Amphotericin B Liposome for injection 50 mg/vial` |
| Product Name | B7 | COMPUTED | `=B6` → Product Name = Generic Name (mirror) |
| Test | B8 | CONTEXT | `Assay of Amphotericin B (Standard Lot No. R087G0)` — note std lot embedded in free text |
| Analysis as per (MOA) | B9 | CONTEXT | `QC-DP-MOA-066-06` |
| Analysed By | L6 | CONTEXT | |
| Instrument ID | L7 | CONTEXT | `AD/HPLC/048` |
| Date of Analysis | L8 | CONTEXT | date |
| Standard Name | A14 | CONTEXT | `Amphotericin B` |
| Weight in mg | C14 | INPUT_WEIGHING | 5.054 |
| Vol | D14 | INPUT_WEIGHING | 50 |
| Pip | E14 | INPUT_WEIGHING | 5 |
| Vol | F14 | INPUT_WEIGHING | 100 |
| Pip | G14 | INPUT_WEIGHING | 1 |
| Vol | H14 | INPUT_WEIGHING | 1 |
| MW - Base | I14 | INPUT_WEIGHING | 1 (neutral when not a salt) |
| MW - Salt | J14 | INPUT_WEIGHING | 1 |
| Potency | K14 | INPUT_WEIGHING | 99.4 |
| PPM (std conc.) | L14 | COMPUTED | `=IFERROR((C14/D14*E14/F14*G14/H14*I14/J14*K14/100*1000), "")` → `PPM = StdWt/Vol1*Pip1/Vol2*Pip2/Vol3*MWbase/MWsalt*Potency/100*1000` |
| STD Area, injections 1–6 | B18:B23 | INPUT_AREA | **Chromatography** — 6 replicate standard areas |
| BKT STD Area, injections 1–6 | E18:E23 | INPUT_AREA | **Chromatography** — bracketing standard set 2 |
| BKT STD Area, injections 7–12 | I18:I23 | INPUT_AREA | **Chromatography** — bracketing standard set 3 |
| Mean (STD) | B24 | COMPUTED | `=IFERROR((AVERAGE(B18:B23)), "")` → mean of 6 STD areas |
| SD (STD) | B25 | COMPUTED | `=IFERROR((STDEV(B18:B23)), "")` |
| % RSD (STD) | B26 | COMPUTED | `=IFERROR((B25*100/B24), "")` → SD*100/Mean |
| Mean (STD+BKT1) | E24 | COMPUTED | `=IFERROR((AVERAGE(E18:E23,B18:B23)), "")` → pooled mean over both sets |
| SD (STD+BKT1) | E25 | COMPUTED | `=IFERROR((STDEV(B18:B23,E18:E23)), "")` |
| % RSD (STD+BKT1) | E26 | COMPUTED | `=IFERROR((E25*100/E24), "")` |
| Mean (STD+BKT1+BKT2) | I24 | COMPUTED | `=IFERROR((AVERAGE(B18:B23,I18:I23,E18:E23)), "")` |
| SD pooled | I25 | COMPUTED | `=IFERROR((STDEV(B18:B23,E18:E23,I18:I23)), "")` |
| % RSD pooled | I26 | COMPUTED | `=IFERROR((I25*100/I24), "")` |
| STD-1 / STD-2 weight (mg) | M17, M18 | INPUT_WEIGHING | `M17 = =C14` (mirrors std weight); STD-2 weight entered |
| Inj. 1–6 area (STD-1 column) | P16:P21 | COMPUTED | `=B18 … =B23` — mirrors of STD area cells |
| Mean STD-1 | P22 | COMPUTED | `=B24` |
| Mean STD-2 | Q22 | COMPUTED | `=IFERROR((AVERAGE(Q16:Q17)), "")` |
| **STD Co-Relation (%)** | Q23 | COMPUTED | `=IFERROR((TRUNC((P22/Q22*M18/M17),3)), "")*100` → `TRUNC(MeanStd1/MeanStd2 * WtStd2/WtStd1, 3) * 100` — **TRUNC to 3 decimals then ×100** |
| Batch No. | A31, A33, A35, A37 … | CONTEXT | per sample row-pair |
| Stability Condition | B31… | CONTEXT | `Initial_1`, `Initial_2` |
| Packing Detail | C31… | CONTEXT | `Glass Vial` |
| TRF No. | D31… | CONTEXT | |
| AR No. | E31… | CONTEXT | |
| Avg Weight | F31… | INPUT_WEIGHING | 1 |
| L.C. | G31… | CONTEXT/INPUT | 50 (label claim mg) |
| Sample Weight | H31… | INPUT_WEIGHING | |
| Vol | I31… | INPUT_WEIGHING | 500 |
| Pip | J31… | INPUT_WEIGHING | 5 |
| Vol | K31… | INPUT_WEIGHING | 100 |
| Pip | L31… | INPUT_WEIGHING | 1 |
| Vol | M31… | INPUT_WEIGHING | 1 |
| Area-1 | N31, N33… | INPUT_AREA | **Chromatography** |
| Area-2 | O31, O33… | INPUT_AREA | **Chromatography** (second injection of same prep) |
| Avg. Area | P31, P33… | COMPUTED | `=IFERROR((AVERAGE(N31:O32)), "")` → mean of the 2×2 area block for the row-pair |
| **% Assay** | Q31, Q33… | COMPUTED | `=IFERROR((P31/$B$24*$C$14/$D$14*$E$14/$F$14*$G$14/$H$14*K31/J31*M31/L31*I31/H31*F31/G31*$K$14*$I$14/$J$14), "")` → `%Assay = AvgArea/MeanStdArea * StdWt/StdVol1 * StdPip1/StdVol2 * StdPip2/StdVol3 * SmpVol3/SmpPip2 * SmpVol4/SmpPip3 * SmpVol1/SmpWt * AvgWt/LC * Potency * MWbase/MWsalt` |
| **% Mean Assay** | R31, R35, R39 … (every 4 rows) | COMPUTED | `=IFERROR((AVERAGE(Q31:Q34)), "")` → mean of the two sample preparations (2 row-pairs) |
| Analyzed By / Checked By | A64 / J64 | CONTEXT | signature block |

- **Reportable result(s):** `% Mean Assay` (R column). Supporting: `% Assay` per preparation, standard `% RSD`, `STD Co-Relation %`.
- **Repeating structure:** standard injections 6; bracketing standard sets 2 × 6 (up to 18 std areas pooled); sample slots 16 (rows 31–62 in row-pairs), grouped 4 rows (= 2 preparations) per `% Mean Assay`.
- **System suitability:** `% RSD` of standard replicates (three progressive pooled windows). No criteria text stored in cells.
- **Conditional/lookup logic:** `IFERROR(...,"")` wraps every formula; `TRUNC(x,3)` for STD co-relation. No ROUND on the reportable — full precision carried.

---

## 2. `Assay_ Microbial_Amphotericin B_API.xlsx`

- **Test category:** Microbiological (bioassay / cylinder-plate agar-diffusion) Assay — Amphotericin B **API**.
- **Sheet(s):** `Accuracy Calculation sheet ` (main, `A1:O78`), `Sheet2` (chart feed: log-conc vs corrected zone diameter).
- **Layout shape:** Header (sample details left / standard details right) → standard stock 5-level dilution series → sample 3-set preparation → **zone-reading grid** (5 std levels × 3 plates × 6 zones) → sample zone grid (3 sets × 3 plates × 6 zones) → regression results block.
- **Archetype:** A6 — bioassay / regression (log-concentration vs zone diameter).

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Date | A3/B3 | CONTEXT | |
| Product Name | B4 | CONTEXT | `Amphotericin B API` |
| Batch No. | B5 | CONTEXT | `HAN1711203U` |
| Condition | B6 | CONTEXT | `2 to 8°C (Protect from light)` |
| Std Name | H3 | CONTEXT | `Amphotericin B USP RS` |
| Std Batch No. | H4 | CONTEXT | `R087G0` |
| Std Potency | H5 | INPUT_WEIGHING | `994` (µg/mg) |
| Std Valid up to | H6 | CONTEXT | |
| Std Weight in mg | B11 | INPUT_WEIGHING | 10.05 |
| Dilution (*mL) | C11 | INPUT_WEIGHING | 10 |
| Sample Taken (*mL) — 5 levels | D11:D15 | INPUT_WEIGHING | 0.643 / 0.803 / 1 / 1.255 / 1.566 |
| Dilution (*mL) — 5 levels | E11:E15 | INPUT_WEIGHING | 50 each |
| Concentration (µg/mL) stage-1 | F11:F15 | COMPUTED | `=B11/C11*D11/E11*H5` → `Conc1 = StdWt/Dil1*Aliquot/Dil2*Potency` |
| Volume taken (mL) | G11:G15 | INPUT_WEIGHING | 1 |
| Dilution (**mL) | H11:H15 | INPUT_WEIGHING | 20 |
| Concentration (µg/mL) final | I11:I15 | COMPUTED | `=(B11/C11*D11/E11*G11/H11*H5)` → full 3-stage dilution × potency |
| Std. Name | J11:J15 | CONSTANT | S1…S5 level labels |
| Log Concentration | K11:K15 | COMPUTED | `=ROUND(LN(I11),4)` → **natural log, ROUND 4** |
| Solvent note | A16 | CONSTANT | `* = Dimethyl sulphoxide, ** = Buffer solution pH 10.5` |
| Sample Weight in mg (Set-1/2/3) | B20:B22 | INPUT_WEIGHING | 10.043 / 10.046 / 10.049 |
| Dilutions C/D/E | C20:E22 | INPUT_WEIGHING | 10 / 1 / 50 |
| Conc (µg/mL) stage-1 | F20:F22 | COMPUTED | `=B20/C20*D20/E20*1000` → **`1000` is a CONSTANT unit factor (mg→µg)** |
| Dilution G/H | G20:H22 | INPUT_WEIGHING | 1 / 20 |
| Conc (µg/mL) final | I20:I22 | COMPUTED | `=F20*G20/H20` |
| Std log-conc (per level) | B42, B45, B48, B51, B54 | COMPUTED | `=K11 … =K15` mirrors |
| Plates | C42:C53 | CONSTANT | 1,2,3 per level |
| Reference zone readings Zone 1/3/5 | D42:F53 (3 plates × 3 zones per level) | INPUT_WEIGHING | zone diameter in mm — physically measured |
| Reference zone Average | G42, G45, G48, G51 | COMPUTED | `=AVERAGE(D42:F44)` → mean of 9 readings |
| Reference zone % RSD | H42, H45, … | COMPUTED | `=STDEV(D42:F44)*100/G42` |
| Sample/test zone readings Zone 2/4/6 | I42:K53 | INPUT_WEIGHING | mm |
| Test zone Average | L42, L45, … | COMPUTED | `=AVERAGE(I42:K44)` |
| Test zone % RSD | M42, M45, … | COMPUTED | `=STDEV(I42:K44)*100/L42` |
| **Corrected Mean** | N42, N45, N48, N51 | COMPUTED | `=L42-(G42-G54)` → `CorrMean = TestZoneAvg - (RefZoneAvg - GrandRefAvg)` |
| S3 (Reference) grand average | G54 | COMPUTED | `=AVERAGE(G42:G53)` → grand mean of all reference zones |
| S3 corrected mean | N54 | COMPUTED | `=G54` |
| Sample zone readings (3 sets × 3 plates × 6 zones) | D58:K66 | INPUT_WEIGHING | mm |
| Sample ref averages / %RSD | G58,H58,G61,H61,G64,H64 | COMPUTED | `=AVERAGE(D58:F60)`, `=STDEV(D58:F60)*100/G58` |
| Sample test averages / %RSD | L58,M58,… | COMPUTED | `=AVERAGE(I58:K60)`, `=STDEV(I58:K60)*100/L58` |
| Sample Corrected Mean (U) | N58, N61, N64 | COMPUTED | `=L58-(G58-G54)` |
| Slope | C70:C72 | COMPUTED | `=ROUND(SLOPE(N42:N54,B42:B54),4)` → **linear regression slope, ROUND 4** |
| Intercept | D70:D72 | COMPUTED | `=ROUND(INTERCEPT(N42:N54,B42:B54),4)` → **ROUND 4** |
| Corrected Average | E70:E72 | COMPUTED | `=N58` / `=N61` / `=N64` |
| Log concentration of Sample | F70:F72 | COMPUTED | `=(E70-D70)/C70` → `(CorrAvg - Intercept)/Slope` |
| Concentration (µg/mg) | G70:G72 | COMPUTED | `=ROUND(EXP(F70)*H20/G20*E20/D20*C20/B20,0)` → **EXP then ×reverse dilution chain, ROUND 0** |
| **Assay (%)** | H70:H72 | COMPUTED | `=ROUND(EXP(F70)/I21*100,2)` → **ROUND 2**. NB: all three rows divide by `I21` (Set-2 conc) — see Discrepancies |
| Average conc / Average assay | G73 / H73 | COMPUTED | `=AVERAGE(G70:G72)` / `=AVERAGE(H70:H72)` |
| SD of assay | H74 | COMPUTED | `=STDEV(H70:H72)` |
| %RSD of assay | H75 | COMPUTED | `=H74*100/H73` |
| Criteria text | J69 | CONSTANT | `Where, RSD : NMT 10 % , R2 = NLT 95 %` |
| Analyzed By / Checked By | A78 / J78 | CONTEXT | |
| Chart feed (Sheet2) | D5:E9 | COMPUTED/CONSTANT | log-conc literals `-0.4462, -0.2224, 0.2236, 0.4447` (hardcoded!) paired with `='Accuracy Calculation sheet '!N42` etc. |

- **Reportable result(s):** `Assay (%)` per set and the **Average Assay (%)** (H73); `Concentration (µg/mg)` (G70:G73).
- **Repeating structure:** standard levels 5 (S1,S2,S3,S4,S5); plates 3 per level; zones 6 per plate (3 reference + 3 test); sample preparations 3 sets × 3 plates × 6 zones.
- **System suitability:** text criterion `RSD NMT 10 %`, `R² NLT 95 %` (J69) with computed `% RSD` columns as the observations.
- **Conditional/lookup logic:** `ROUND(...,4)` on log-conc/slope/intercept, `ROUND(...,0)` on µg/mg, `ROUND(...,2)` on Assay %; `LN`, `EXP`, `SLOPE`, `INTERCEPT`. No IFERROR guards on this sheet.

---

## 3. `Assay_Microbial_Amphotericin B_FP.xlsx`

- **Test category:** Microbiological bioassay Assay — Amphotericin B **Finished Product** (liposomal injection). Same engine as #2, mg/vial basis.
- **Sheet(s):** `Final Bioassay sheet ` (`A1:O66`), `Sheet2` (chart feed).
- **Layout shape:** Identical to #2 but with only **2 sample preparations** and an extra `Average Weight (mg/vial)` column; label-claim divisor 50.
- **Archetype:** A6 — bioassay / regression.

### Field inventory (deltas vs #2 called out; shared structure abbreviated)

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Date | A3 | CONTEXT | |
| Product Name | B4 | CONTEXT | `Amphotericin B Liposome for injection 50 mg / viaL` |
| Batch No. | B5 (blank) | CONTEXT | |
| Label Claim | B6 | CONTEXT | `Each vial contain 50 mg of Amphotericin B` |
| Condition | A7 | CONTEXT | |
| TRF No. | A8 | CONTEXT | |
| Std Name / Batch / Potency / Valid up to | J3 / J4 / J5 / J6 | CONTEXT + INPUT_WEIGHING (`J5 = 994`) | |
| Std Weight in mg | B12 | INPUT_WEIGHING | 10.05 |
| Dilution (*mL) | C12 | INPUT_WEIGHING | 10 |
| Sample Taken (*mL) 5 levels | D12:D16 | INPUT_WEIGHING | 0.64 / 0.8 / 1 / 1.25 / 1.56 |
| Dilution (*mL) | E12:E16 | INPUT_WEIGHING | 50 |
| Concentration (µg/mL) | F12:F16 | COMPUTED | `=B12/C12*D12/E12*J5` |
| Log Concentration (stage-1) | G12:G16 | COMPUTED | `=LN(F12)` — **unrounded LN** (differs from API sheet) |
| Volume taken / Dilution (**mL) | H12:H16 / I12:I16 | INPUT_WEIGHING | 1 / 20 |
| Concentration (µg/mL) final | J12:J16 | COMPUTED | `=(B12/C12*D12/E12*H12/I12*J5)` |
| Std. Name | K12:K16 | CONSTANT | S1…S5 |
| Log Concentration (final) | L12:L16 | COMPUTED | `=ROUND(LN(J12),4)` |
| Solvent note | A17 | CONSTANT | `* = N,N, Dimethyl Formamide , ** = Buffer solution pH 10.5` |
| Amphotericin B Weight in mg (2 preps) | B21:B22 | INPUT_WEIGHING | 1475 / 1490 (whole-vial mg) |
| Dilutions C/D/E | C21:E22 | INPUT_WEIGHING | 50 / 1 / 50 |
| Concentration (µg/mL) | F21:F22 | COMPUTED | `=B21/C21*D21/E21*1000` — **F22 wrongly references B21/C21 (see Discrepancies)** |
| Dilution G/H | G21:H22 | INPUT_WEIGHING | 1 / 20 |
| Concentration final | I21:I22 | COMPUTED | `=F21*G21/H21` |
| Average Weight (mg/vial) | J21:J22 | COMPUTED | `=B21` / `=B22` |
| Zone grid (5 std levels × 3 plates × 6 zones) | D37:K48 | INPUT_WEIGHING | mm |
| Ref avg / %RSD | G37,H37,… | COMPUTED | `=AVERAGE(D37:F39)`, `=STDEV(D37:F39)*100/G37` |
| Test avg / %RSD | L37,M37,… | COMPUTED | `=AVERAGE(I37:K39)`, `=STDEV(I37:K39)*100/L37` |
| Corrected Mean | N37,N40,N43,N46 | COMPUTED | `=L37-(G37-G49)` |
| Reference grand average | G49 | COMPUTED | `=AVERAGE(G37:G48)`; `N49 = =G49` |
| Sample zone grid (2 preps × 3 plates × 6 zones) | D53:K58 | INPUT_WEIGHING | mm |
| Sample corrected mean (U) | N53, N56 | COMPUTED | `=L53-(G53-G49)` |
| Slope / Intercept | C62:C63 / D62:D63 | COMPUTED | `=ROUND(SLOPE(N37:N49,B37:B49),4)` / `=ROUND(INTERCEPT(N37:N49,B37:B49),4)` |
| Corrected Average | E62:E63 | COMPUTED | `=N53` / `=N56` |
| Log conc of Sample (Lu) | F62:F63 | COMPUTED | `=(E62-D62)/C62` |
| Concentration (µg/mL) (Cu) | G62:G63 | COMPUTED | `=EXP(F62)` — **no rounding** |
| **Assay (%)** | H62:H63 | COMPUTED | `=G62/1000*C21/B21*E21/D21*H21/G21*J21/50*100` → `Assay% = Cu/1000 * Dil1/Wt * Dil3/Dil2 * Dil5/Dil4 * AvgWtPerVial/LC(50) * 100`. `1000` (µg→mg) and `50` (label claim mg/vial) are **CONSTANTS** |
| Criteria text | J61 | CONSTANT | `Where, RSD : NMT 10% , R2 = NLT 95 %` |
| Analyzed By / Checked By | A66 / J66 | CONTEXT | |

- **Reportable result(s):** `Assay (%)` per preparation (H62:H63) — mean taken off-sheet.
- **Repeating structure:** std levels 5 × 3 plates × 6 zones; sample preparations 2 × 3 plates × 6 zones.
- **System suitability:** `%RSD NMT 10 %`, `R² NLT 95 %`.
- **Conditional/lookup logic:** `ROUND(...,4)`, `LN`, `EXP`, `SLOPE`, `INTERCEPT`. No IFERROR.

---

## 4. `Bupivacaine Assay mg ml & Percentage.xlsx`

- **Test category:** Assay by HPLC with **dual reportable units** (`% Assay` and `mg/mL`) — Bupivacaine liposome injectable suspension 1.3 % (13.3 mg/mL).
- **Sheet(s):** `1`. Dimensions `A1:R65`.
- **Layout shape:** Identical skeleton to #1 (Assay by HPLC) with the sample grid extended by two extra computed columns (`Assay (mg/mL)`, `Mean (mg/mL)`) and one fewer dilution stage on the sample side.
- **Archetype:** A1 — single-standard + sample-rows assay.

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Generic Name | B6 | CONTEXT | `Bupivacaine liposome injectable suspension 1.3% (13.3 mg/mL)` |
| Product Name | B7 | CONTEXT | literal (not mirrored here, unlike #1) |
| Test | B8 | CONTEXT | `Assay` |
| Analysis as per | B9 | CONTEXT | `AD/ATP/650/02` |
| Analysed By | L6 | CONTEXT | |
| Instrument ID | L7 | CONTEXT | `AD/HPLC/005` |
| Template ID | J8/L8 | CONTEXT | (blank — placeholder for LIMS template id) |
| Date of Analysis | L9 | CONTEXT | |
| Standard Name | A14 | CONTEXT | `Bupivacaine` |
| Wt. in mg | C14 | INPUT_WEIGHING | 50.59 |
| Vol / Pip / Vol / Pip / Vol | D14, E14, F14, G14, H14 | INPUT_WEIGHING | 100 / 10 / 50 / 1 / 1 |
| MW-Base / MW-Salt | I14 / J14 | INPUT_WEIGHING | 1 / 1 |
| Potency | K14 | INPUT_WEIGHING | 99.64 |
| PPM | L14 | COMPUTED | `=IFERROR((C14/D14*E14/F14*G14/H14*I14/J14*K14/100*1000), "")` |
| STD Area 1–6 | B18:B23 | INPUT_AREA | **Chromatography** |
| BKT STD Area 1–6 | E18:E23 | INPUT_AREA | **Chromatography** |
| BKT STD Area 7–12 | I18:I23 | INPUT_AREA | **Chromatography** |
| STD-2 areas (co-relation) | Q16:Q17 | INPUT_AREA | 2387736 / 2388617 |
| STD-1 / STD-2 weights | M18 (`=C14`) / M19 (50.47) | COMPUTED / INPUT_WEIGHING | |
| Mean / SD / %RSD (3 pooled windows) | B24:B26, E24:E26, I24:I26 | COMPUTED | same formulas as #1 |
| Mean STD-1 / STD-2 | P22 (`=B24`) / Q22 | COMPUTED | `=IFERROR((AVERAGE(Q16:Q17)), "")` |
| **STD Co-Relation** | Q23 | COMPUTED | `=IFERROR((TRUNC((P22/Q22*M19/M18),3)), "")*100` — **TRUNC 3 then ×100** |
| Batch No. / Stability Condition / Packing Detail / TRF No. / AR No. | A31…E31 (per row-pair) | CONTEXT | e.g. `EP20_117-307`, `2-8°C_Initial_Set-1`, `Glass Vial`, `TRF_010-25-72`, `AD/008/25/0078` |
| Avg Weight | F31… | INPUT_WEIGHING | 1.005 |
| L.C. | G31… | CONTEXT/INPUT | 13.3 |
| Sample Weight | H31… | INPUT_WEIGHING | 0.7621 |
| Vol / Pip / Vol | I31 / J31 / K31 | INPUT_WEIGHING | 100 / 1 / 1 |
| Area-1 / Area-2 | L31 / M31 | INPUT_AREA | **Chromatography** |
| Avg. Area | N31 | COMPUTED | `=IFERROR((AVERAGE(L31:M32)), "")` |
| **% Assay** | O31 | COMPUTED | `=IFERROR((N31/$B$24*$C$14/$D$14*$E$14/$F$14*$G$14/$H$14*K31/J31*I31/H31*F31/G31*$K$14*$I$14/$J$14), "")` → `%Assay = AvgArea/MeanStd * StdWt/V1*P1/V2*P2/V3 * SmpV3/SmpP1 * SmpV1/SmpWt * AvgWt/LC * Potency * MWb/MWs` |
| **% Mean Assay** | P31, P35, … | COMPUTED | `=IFERROR((AVERAGE(O31:O34)), "")` |
| **Assay (mg/mL)** | Q31 | COMPUTED | `=IFERROR((N31/$B$24*$C$14/$D$14*$E$14/$F$14*$G$14/$H$14*$I$14/$J$14*I31/H31*K31/J31*F31/1*$K$14/100), "")` → same chain but **`AvgWt/1` instead of `AvgWt/LC`, and `Potency/100` instead of `×Potency`**, giving mg/mL |
| **Mean (mg/mL)** | R31, R35, … | COMPUTED | `=IFERROR((AVERAGE(Q31:Q34)), "")` |
| Analyzed By / Checked By | A60 / J60 | CONTEXT | |

- **Reportable result(s):** `% Mean Assay` (P) **and** `Mean (mg/mL)` (R).
- **Repeating structure:** std injections 6 + BKT 2 × 6; sample slots 14 (rows 31–58, row-pairs), `% Mean Assay` / `Mean (mg/mL)` every 4 rows (2 preparations).
- **System suitability:** standard `% RSD` (three pooled windows) + `STD Co-Relation`.
- **Conditional/lookup logic:** `IFERROR(...,"")` everywhere; `TRUNC(x,3)`.

---

## 5. `Bupivacaine Disso 15 Units.xls`

- **Test category:** Dissolution / Drug-release profile by HPLC, **with replacement** (cumulative-correction method). Bupivacaine Liposome Injectable Suspension 1.3 %.
- **Sheet(s):** `ES24E007A` (sheet named after the batch). Dimensions `A1:T109`, laid out as 2 printed pages.
- **Layout shape:** **2-D grid** — rows = dissolution units, columns = time-points. Four stacked grids of the same shape: (a) Sample Area, (b) % Drug Release Uncorrected, (c) Correction factors F1…F14, (d) % Release (cumulative, reportable) + column statistics. Plus a hidden/side "Factor calc" column pair (S/T) that propagates the running media volume.
- **Archetype:** A3 — 2-D dissolution grid (with-replacement variant).

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Company / dept / product / test titles | B2:B5 | CONSTANT/CONTEXT | `Emcure`, `R&D, Analytical`, product string, `Dissolution Profile (By HPLC)` |
| Product Name | D7 | CONTEXT | |
| Condition | D8 | CONTEXT | `2-8°C_Initial` |
| Pack style | D9 | CONTEXT | `Clear Glass 20ml Vial` |
| Remarks | D10 | CONTEXT | |
| Date of Analysis | D12 | CONTEXT | |
| Name of Active | D13 | CONTEXT | `Bupivacaine` |
| L.C. | G13 | INPUT_WEIGHING | 13.3 (mg/mL) |
| **Final (L.C. × Taken mL)** | J12 | COMPUTED | `=IFERROR((G13*D18), "")` → `FinalLC = LC × SampleTakenmL` |
| TRF No. | N12 | CONTEXT | `TRF-033-26-100` |
| AR No. | N13 | CONTEXT | |
| Standard WRS No. | E15 | CONTEXT | `WS/026/038` |
| Protocol No. | N15 | CONTEXT | |
| Potency / Purity | E16 | INPUT_WEIGHING | 99.9 |
| LNB No. | N16 | CONTEXT | |
| Batch / Lot No. | N17 | CONTEXT | `ES24E007A` |
| STD Prep. chain | D17 (22.2 mg), F17 (25), G17 (2), H17 (100), I17 (1), J17 (1) | INPUT_WEIGHING | wt / vol / pip / vol / pip / vol |
| SPL Prep. chain | D18 (1 mL), F18 (750), G18 (1), H18 (1), I18 (1), J18 (1) | INPUT_WEIGHING | taken mL / media vol / pip / vol … |
| Media Volume | B23 | INPUT_WEIGHING | 750 |
| RPM | C23 | INPUT_WEIGHING | 50 |
| Temp (°C) | D23 | INPUT_WEIGHING | 37 |
| **Withdraw volume (mL)** | E23 | INPUT_WEIGHING | 5 |
| **Replacement volume (mL)** | G23 | INPUT_WEIGHING | 5 |
| Apparatus | I23 | CONTEXT | `Paddle` |
| Disso. Media | O22 | CONTEXT | `4X Phosphate Buffer Saline pH 7.4 Solution` |
| M.W. Base / Salt | P26 / P27 | INPUT_WEIGHING | 1 / 1 |
| STD-1 Area 1–6 | B27:G27 | INPUT_AREA | **Chromatography** |
| STD-1 Mean | H27 | COMPUTED | `=IFERROR((ROUND(AVERAGE(B27:G27),4)), "")` → **ROUND 4** |
| STD-1 % RSD | I27 | COMPUTED | `=IFERROR(((STDEV(B27:G27)/H27*100)), "")` |
| STD-2 Wt. (mg) | E29 | INPUT_WEIGHING | 22.9 |
| STD-2 Area-1 / Area-2 | C31 / C32 | INPUT_AREA | **Chromatography** |
| STD-2 Mean | D31 | COMPUTED | `=IFERROR((AVERAGE(C31:C32)), "")` |
| **Co-Relation** | E31 | COMPUTED | `=IFERROR((H27/D31*E29/D17), "")` → `MeanStd1/MeanStd2 × WtStd2/WtStd1` (no TRUNC here) |
| BKT-1 … BKT-9 Area | I30:Q30 | INPUT_AREA | **Chromatography** (bracketing standards) |
| BKT-1..9 running Mean | I31:Q31 | COMPUTED | `=IFERROR(ROUND(AVERAGE($B$27:$G$27,I30),4),"")` → mean of the 6 STD-1 areas plus that one bracket |
| BKT-1..9 running % RSD | I32:Q32 | COMPUTED | `=IFERROR(((STDEV($B$27:$G$27,I30))/I31*100), "")` |
| BKT-10 … BKT-22 Area | C35:O35 | INPUT_AREA | **Chromatography** (13 more brackets → 22 total) |
| BKT-10..22 running Mean / %RSD | C36:O36 / C37:O37 | COMPUTED | same pattern as above |
| **Cumulative BKT Mean** | P36 | COMPUTED | `=IFERROR((AVERAGE(B27:G27,I30:Q30,C35:O35)), "")` → mean of all 6 + 22 standard areas |
| **Cumulative BKT % RSD** | P37 | COMPUTED | `=IFERROR((STDEV(B27:G27,I30:Q30,C35:O35)/P36*100), "")` |
| Time-point headers | C40:Q40 | CONSTANT | `30 Min, 1 Hr, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24 Hr` → **15 time-points** |
| **Sample Area grid** | C41:Q52 | INPUT_AREA | **Chromatography** — 12 units × 15 time-points = 180 area cells |
| Factor calc — first vol | T56 | COMPUTED | `=F18` (= media volume 750) |
| Factor calc — running media volume | T57:T70 | COMPUTED | `=T56-$E$23+$G$23` → `Vol(n) = Vol(n-1) − WithdrawVol + ReplacementVol` (cascade, 14 steps) |
| Factor calc — time labels | S56:S70 | COMPUTED | `=C56 … =Q56` mirrors |
| **% Drug Release Uncorrected** | C57:Q68 | COMPUTED | `=IFERROR((TRUNC((C41/$H$27*$D$17/$F$17*$G$17/$H$17*$I$17/$J$17*$F$18/1*$H$18/$G$18*$E$16/$J$12*$P$26/$P$27),3)),"")` → `%Rel_uncorr = Area/MeanStdArea * StdWt/StdVol1 * StdPip1/StdVol2 * StdPip2/StdVol3 * MediaVol(t)/1 * SmpVol/SmpPip * Potency/FinalLC * MWbase/MWsalt`, **TRUNC 3**. First time-point uses `$F$18`; subsequent ones use the running `$T$57…$T$70` volumes. |
| **Correction factor F1…F14** | C73:P84 | COMPUTED | `=IFERROR(TRUNC(($E$23/$F$18*C57),3),"")` then `=IFERROR(TRUNC(($E$23/$T$57*D57),3),"")` … → `F(t) = WithdrawVol / MediaVol(t) × %Rel_uncorr(t)`, **TRUNC 3** |
| **% Release (cumulative, reportable)** | C88:Q99 | COMPUTED | `=IFERROR(ROUND(C57,0),"")` for t1; `=IFERROR(ROUND((D57+C73),0),"")`; `=IFERROR(ROUND((E57+C73+D73),0),"")` … up to `=IFERROR(ROUND((Q57+C73+…+P73),0),"")` → `%Rel(t) = ROUND(%Rel_uncorr(t) + Σ F(1..t−1), 0)` — **ROUND to 0 decimals (integer)** |
| Mean per time-point | C100:Q100 | COMPUTED | `=IFERROR((ROUND((AVERAGE(C88:C99)),0)), "")` — **ROUND 0** |
| SD per time-point | C101:Q101 | COMPUTED | `=IFERROR(ROUND(STDEV(C88:C99),1),"")` — **ROUND 1** |
| %RSD per time-point | C102:Q102 | COMPUTED | `=IFERROR(ROUND((C101*100/C100),1),"")` — **ROUND 1** |
| Min / Max per time-point | C103:Q103 / C104:Q104 | COMPUTED | `=IFERROR(MIN(C88:C99),"")` / `=IFERROR(MAX(C88:C99),"")` |
| Analysed by / Checked by | B106 / I106 | CONTEXT | |

- **Reportable result(s):** the `% Release` cumulative profile (C88:Q99) plus per-time-point `Mean`, `SD`, `%RSD`, `Min`, `Max`.
- **Repeating structure:** units **12** (U-1…U-12) despite the file name saying *15 Units*; time-points **15**; standard injections 6; bracketing standards **22** (BKT-1…BKT-22) individually tracked with running mean/%RSD; correction factors 14 (one fewer than time-points).
- **System suitability:** STD-1 `% RSD`, each bracket's running `% RSD`, cumulative-BKT `% RSD`, and `Co-Relation` between STD-1 and STD-2. No embedded acceptance-criteria text.
- **Conditional/lookup logic:** `IFERROR(...,"")` throughout; `TRUNC(x,3)` for uncorrected % and correction factors; `ROUND(x,0)` for the reportable cumulative %; `ROUND(x,1)` for SD/%RSD; `ROUND(x,4)` for std area means.
- ⚠ **Bug:** in the uncorrected grid, the 14 Hr column (`L57:L68`) references `$T$64` — the same volume as the 12 Hr column (`K57:K68`) — instead of `$T$65`, and `$T$65` is never used in that grid (the correction-factor grid does use `$T$65`). Also the `Mean/SD/%RSD` block covers `C88:C99` (12 rows) which is consistent with 12 units.

---

## 6. `Bupivacaine Free & Entrrapted Drug Calculation.xlsx`

- **Test category:** Free & Entrapped (encapsulated) drug determination by HPLC — liposomal Bupivacaine.
- **Sheet(s):** `Sheet ` (trailing space). Dimensions `A1:R56`.
- **Layout shape:** Header → *Standard Details* (1 standard + 3 injection windows) → *Sample Details* repeating rows (12 slots at 2-row pitch) with 8 computed result columns.
- **Archetype:** A1-variant — single-standard + sample-rows, multiple derived reportables.

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Generic Name / Product Name | B5 / B6 | CONTEXT | `Bupivacaine liposome injectable suspension 13.3 mg/ml` |
| Test | B7 | CONTEXT | `Free & Entrapped Drug` |
| Analysis as per | B8 | CONTEXT | `QC-DP-MOA-077-03` |
| Template ID / Instrument Id. / Analysed By / Date of Analysis | K5 / K6 / K7 / K8 | CONTEXT | (label cells; value cells blank in this copy) |
| STD Name | A12 | CONTEXT | `Bupivacaine` |
| Weight in mg | B12 | INPUT_WEIGHING | 66.44 |
| Vol / Pip / Vol / Pip / Vol | C12 / D12 / E12 / F12 / G12 | INPUT_WEIGHING | 50 / 5 / 25 / 1 / 1 |
| M.W of Base / M.W. of Salt | H12 / J12 | INPUT_WEIGHING | 1 / 1 |
| Potency | L12 | INPUT_WEIGHING | 99.64 |
| PPM | N12 | COMPUTED | `=B12/C12*D12/E12*F12/G12*H12/J12*L12/100*1000` |
| STD Area inj 1–6 | B16:B21 | INPUT_AREA | **Chromatography** |
| BKT STD Area inj 1–6 | E16:E21 | INPUT_AREA | **Chromatography** |
| BKT STD Area inj 7–12 | J16:J21 | INPUT_AREA | **Chromatography** |
| Mean / SD / % RSD (STD) | B22 / B23 / B24 | COMPUTED | `=AVERAGE(B16:B21)`, `=STDEV(B16:B21)`, `=B23*100/B22` |
| Mean / SD / % RSD (STD+BKT1) | E22 / E23 / E24 | COMPUTED | `=AVERAGE(E16:E21,B16:B21)`, `=STDEV(B16:B21,E16:E21)`, `=E23*100/E22` |
| Mean / SD / % RSD (all three) | J22 / J23 / J24 | COMPUTED | `=AVERAGE(B16:B21,J16:J21,E16:E21)`, `=STDEV(B16:B21,E16:E21,J16:J21)`, `=J23*100/J22` |
| Batch No. | B28, B30, … | CONTEXT | `5% Trial-1`, `13% Trial-2`, … |
| Stability Condition / Packing Detail | (B/C columns) | CONTEXT | `Glass Vial` |
| TRF No. / A.R. No. | D28 / E28 | CONTEXT | |
| L.C. | F28 | CONTEXT/INPUT | 13.3 |
| Sample taken in ml | G28 | INPUT_WEIGHING | 1 |
| Vol / Pip / Vol | H28 / I28 / J28 | INPUT_WEIGHING | 5 / 1 / 1 |
| Sample Area | K28 | INPUT_AREA | **Chromatography** — free-drug (supernatant) peak area |
| **% Con.** (free-drug concentration as % of LC) | L28 | COMPUTED | `=IFERROR((K28/$B$22*$B$12/$C$12*$D$12/$E$12*$F$12/$G$12*$H$12/$J$12*H28/G28*J28/I28*1/F28*$L$12), "")` → `%Con = Area/MeanStd * StdWt/V1*P1/V2*P2/V3 * MWb/MWs * SmpVol/SmpTaken * SmpVol2/SmpPip * 1/LC * Potency` |
| % Assay of Bupivacaine (from the Assay sheet) | M28 | INPUT_WEIGHING | 101.5 — **manually carried over from the Assay test** |
| Bupivacaine in (mg/mL) | N28 | COMPUTED | `=IFERROR((M28*F28/100), "")` → `%Assay × LC / 100` |
| **% Free Drug** | O28 | COMPUTED | `=IFERROR((L28/M28)*100, "")` → `%Con / %Assay × 100` |
| **Free Drug (mg/mL)** | P28 | COMPUTED | `=IFERROR((K28/$B$22*…*$L$12/100)/N28*F28, "")` → same dilution chain with `Potency/100`, then `/ Bupivacaine(mg/mL) × LC` |
| **% Entrapped** | Q28 | COMPUTED | `=IFERROR(((M28-O28)/(M28)*100), "")` → `(%Assay − %FreeDrug)/%Assay × 100` |
| **Entrapped (mg/mL)** | R28 | COMPUTED | `=IFERROR(((N28-P28)/(N28)*F28), "")` → `(mg/mL total − mg/mL free)/mg/mL total × LC` |
| Analyzed By / Checked By | A52 / K52 | CONTEXT | |

- **Reportable result(s):** `% Free Drug`, `Free Drug (mg/mL)`, `% Entrapped`, `Entrapped (mg/mL)`. `% Con.` and `Bupivacaine (mg/mL)` are intermediates.
- **Repeating structure:** standard injections 6 + BKT 2 × 6; sample slots **12** (rows 28–50 at 2-row pitch).
- **System suitability:** standard `% RSD` in three pooled windows.
- **Conditional/lookup logic:** `IFERROR(...,"")` only; **no rounding at all** — full float precision carried into the reportables.
- ⚠ Cross-test dependency: `% Assay of Bupivacaine` (M column) is a hardcoded value copied from a separate Assay sheet. In LIMS this must be a **linked result reference**, not free entry.

---

## 7. `Bupivacaine Lipid & Drug to lipid Ratio.xlsx`

- **Test category:** Lipid content by HPLC (4 lipid components) **plus** derived Drug-to-Lipid ratio.
- **Sheet(s):** `Lipid ` (`A1:P107`) and `Drug to Lipid ratio Auto Calc` (`A1:N58`) — the second sheet is fully driven by cross-sheet references.
- **Layout shape:** Sheet 1: header → 4-compound standard table → 2 injection blocks (STD 6 inj, BKT 6 inj) per compound → sample blocks of **4 compound rows × 2 preparations** repeated 7 times. Sheet 2: one 4-row block per batch pulling `% Mean` from sheet 1 and computing the ratio.
- **Archetype:** A2 — multi-component (per-compound standard) assay; with a dependent roll-up sheet.

### Sheet `Lipid ` — field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Generic Name / Product Name | C7 / C8 | CONTEXT | |
| Test | C9 | CONTEXT | `Lipid Content` |
| Analysis as per | C10 | CONTEXT | `AD/ATP/648/02` |
| Analysed By | C11 | CONTEXT | |
| Instrument Id. | C12 | CONTEXT | `AD/HPLC/006` |
| Date of Analysis | C13 | CONTEXT | |
| Compound Name (4 rows) | A18:A21 | CONTEXT | `Tricaprylin`, `DPPG Na`, `Cholesterol`, `DEPC` |
| Weight in mg | B18:B21 | INPUT_WEIGHING | 99.1 / 46.79 / 28.51 / 49.32 |
| Vol / Pip / Vol / Pip / Vol | C18:G21 | INPUT_WEIGHING | per compound |
| Potency | H18:H21 | INPUT_WEIGHING | 100 / 99.3 / 100 / 99.2 |
| M.W of Base / M.W. of Salt | I18:I21 / J18:J21 | INPUT_WEIGHING | DPPG uses 721.9602 / 744.95; others 1/1 |
| Conc. (ppm) | K18:K21 | COMPUTED | `=IFERROR((B18/C18*D18/E18*F18/G18*H18/100*I18/J18*1000), "")` |
| STD Areas per compound, inj 1–6 | B25:E30 | INPUT_AREA | **Chromatography** — 4 compounds × 6 injections |
| BKT STD Areas per compound, inj 1–6 | H25:K30 | INPUT_AREA | **Chromatography** |
| Mean / SD / %RSD (STD) | B31:E31 / B32:E32 / B33:E33 | COMPUTED | `=IFERROR((AVERAGE(B25:B30)), "")`, `=IFERROR((STDEV(B25:B30)),"")`, `=IFERROR((B32*100/B31),"")` |
| Mean / SD / %RSD (STD+BKT) | H31:K31 / H32:K32 / H33:K33 | COMPUTED | `=IFERROR((AVERAGE(H25:H30,B25:B30)), "")` etc. |
| Batch No. / Storage Condition / Packing Detail / TRF No. / AR No. | A39, B39, C39, D39, E39 (per block) | CONTEXT | `EP20_117-299-B`, `2-8°C_3M`, `Glass Vial`, … |
| Compound Name (per row) | F39:F42 | COMPUTED | `=A18`, `=C23`, `=A20`, `=A21` mirrors |
| LC (per compound) | G39:G42 | INPUT_WEIGHING | 2 / 0.9 / 4.7 / 8.2 |
| Avg Weight | H39 | INPUT_WEIGHING | 1.005 |
| Sample Weight | I39 | INPUT_WEIGHING | 1.5008 |
| Vol / Pip / Vol | J39 / K39 / L39 | INPUT_WEIGHING | 25 / 1 / 1 |
| Area | M39:M42 (and M43:M46 for prep-2) | INPUT_AREA | **Chromatography** |
| **% Assay (per compound, per prep)** | N39:N42, N43:N46, … | COMPUTED | `=IFERROR((M39/$B$31*B$18/$C$18*$D$18/$E$18*$F$18/$G$18*J39/I39*L39/K39*$H$18/G39*$I$18/$J$18*H39), "")` → `%Assay = Area/MeanStdArea(compound) * StdWt/V1*P1/V2*P2/V3 * SmpVol/SmpWt * SmpVol2/SmpPip * Potency/LC * MWbase/MWsalt * AvgWeight` |
| **% Mean (per compound)** | O43:O46, O52:O55, … | COMPUTED | `=IFERROR((AVERAGE(N39,N43)), "")` → mean of the two preparations for that compound |
| Analyzed By / Checked By | A102 / I102 | CONTEXT | |

### Sheet `Drug to Lipid ratio Auto Calc` — field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Generic Name / Product Name / Analysis as per / Analysed By / Instrument Id. / Date | C7, C8, C10, C11, C12, C13 | COMPUTED (cross-sheet CONTEXT mirror) | `='Lipid '!C7:K7` etc. |
| Test | C9 | CONTEXT | `Drug to Lipid Ratio` |
| Batch No. / Storage Condition / Packing Detail / TRF No. / AR No. | A18:E18 (per block) | COMPUTED | `='Lipid '!A39` … `='Lipid '!E39` |
| Compound Name | F18:F21 | CONSTANT | Tricaprylin / DPPG / Cholesterol / DEPC |
| L.C. (Lipid) | G18:G21 | COMPUTED | `='Lipid '!G39` … |
| % Mean (Lipid) | H18:H21 | COMPUTED | `='Lipid '!O43` … |
| mg/mL (Lipid) | I18:I21 | COMPUTED | `=IFERROR((H18*G18/100), "")` → `%Mean × LC / 100` |
| **mg/mL (Sum of Lipid)** | J18 | COMPUTED | `=IFERROR((SUM(I18:I21)), "")` → sum of the 4 lipid mg/mL |
| % Assay of Bupivacaine | K18 | INPUT_WEIGHING | 99.9 — **manually carried from the Assay test** |
| L.C. of Bupivacaine | L18 | INPUT_WEIGHING | 13.3 |
| mg/mL of Bupivacaine | M18 | COMPUTED | `=IFERROR((K18*L18/100), "")` |
| **Drug/Lipid Ratio** | N18 | COMPUTED | `=IFERROR((M18/J18), "")` → `mg/mL drug ÷ Σ mg/mL lipid` |
| Analyzed By / Checked By | A53 / K53 | CONTEXT | |

- **Reportable result(s):** per-compound `% Mean (Lipid)`, `mg/mL (Lipid)`, `mg/mL (Sum of Lipid)`, and **`Drug/Lipid Ratio`**.
- **Repeating structure:** compounds **4**; standard injections 6 + BKT 6 per compound; sample blocks **7** batches × 4 compounds × 2 preparations (rows 39–100 on 9-row pitch); ratio sheet 7 blocks.
- **System suitability:** `% RSD` per compound (STD, and STD+BKT pooled).
- **Conditional/lookup logic:** `IFERROR` only; no rounding. Note the mixed-anchor typo `B$18` (row-absolute only) in the Tricaprylin `% Assay` formulas — works only because the block copies down in 9-row steps.

---

## 8. `CU by HPLC.xls`

- **Test category:** Content Uniformity by HPLC with USP `<905>` Acceptance-Value calculation. Rasagiline Mesylate Tablets 1 mg.
- **Sheet(s):** `Sheet1`. Dimensions `A1:K73`.
- **Layout shape:** Header → Std-prep / Test-prep dilution factor strips → 10 sample-unit rows → AV calculation block → standard-injection block + bracketing block.
- **Archetype:** A4 — content-uniformity / acceptance-value.

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| PRODUCT | D6 | CONTEXT | `Rasagiline Mesylate Tab 1 mg` |
| B. No. | I6 | CONTEXT | `2678123` |
| Stage | I7 | CONTEXT | `CRT` |
| Label Claim | D8 | CONTEXT | `Each tablet Contains Rasagiline 1 mg` |
| AR No. | I8 | CONTEXT | |
| TRF No. | I9 | CONTEXT | |
| Remark | D10 | CONTEXT | `initial` |
| Assay as is | E14 | INPUT_WEIGHING | 99.6 (standard assay/potency) |
| Label Claim (numeric) | G14 | INPUT_WEIGHING | 1 |
| Factor | I14 | INPUT_WEIGHING | 0.64088 — **salt→base conversion factor** |
| Std Prep. weight (mg) | C15 | INPUT_WEIGHING | 31.5 |
| Std Prep. dilution chain (mL) | D15, E15, F15, G15, H15 | INPUT_WEIGHING | 100 / 5 / 50 / 1 / 1 |
| Std Conc. | I15 | INPUT_WEIGHING | 0.0315 (entered, not formula) |
| Test Prep. tab/cap | C18 | INPUT_WEIGHING | 1 |
| Test Prep. dilution chain (mL) | D18, E18, F18, G18, H18 | INPUT_WEIGHING | 50 / 1 / 1 / 1 / 1 |
| Test Conc. | I18 | INPUT_WEIGHING | 0.02 |
| Sample (Unit) 1–10 | C28:C37 | CONSTANT | unit index |
| Area (per unit) | D28:D37 | INPUT_AREA | **Chromatography** |
| Weight (per unit) | E28:E37 | INPUT_WEIGHING | tablet weight mg (captured but **not used** in the % of LC formula) |
| **% of LC (per unit)** | F28:F37 | COMPUTED | `=IFERROR(ROUND(D28/$D$51*$C$15/$D$15*$E$15/$F$15*$G$15/$H$15*$D$18/$G$14*$H$18/$G$18*$F$18/$E$18*$I$14*$E$14/100*100,1),"")` → `%LC = Area/MeanStdArea * StdWt/V1 * Pip/V2 * Pip/V3 * TestV1/LC * TestV5/TestV4 * TestV3/TestV2 * Factor * AssayAsIs/100 * 100`, **ROUND 1** |
| Mean (x) | F38 | COMPUTED | `=IFERROR(ROUND(AVERAGE(F28:F37),1),"")` — **ROUND 1** |
| Minimum | F39 | COMPUTED | `=IFERROR(MIN(F28:F37),"")` |
| Maximum | F40 | COMPUTED | `=IFERROR(MAX(F28:F37),"")` |
| SD (s) | F41 | COMPUTED | `=IFERROR(ROUND(STDEV(F28:F37),4),"")` — **ROUND 4** |
| % RSD | F42 | COMPUTED | `=IFERROR(ROUND(F41*100/F38,2),"")` — **ROUND 2** |
| n | D42 | INPUT_WEIGHING | 10 |
| **k** | D43 | COMPUTED (lookup) | `=IF(D42=10,2.4, IF(D42=30,2))` → **k = 2.4 when n=10, 2 when n=30** (CONSTANTS 2.4 / 2) |
| M-rule text | C39:C41 | CONSTANT | `If 98.5% ≥ X ≤ 101.5 % then M=X`, `If X < 98.5 %, then M=98.5 %`, `If X > 101.5 %, then M=101.5 %` |
| AV formula text | D39:D41 | CONSTANT | `AV=ks`, `AV=98.5-X+ks`, `AV=X-101.5+ks` |
| **Acceptance value (AV)** | F43 | COMPUTED | `=IFERROR(ROUND(IF(F38<101.5,IF(F38<98.5,((98.5-F38)+($D$43*F41)),$D$43*F41),((F38-101.5)+($D$43*F41))),1),"")` → nested-IF USP AV, **ROUND 1**. Constants `98.5`, `101.5` |
| AV Limit | H43 | CONSTANT | `Not more than 15.0` |
| Std Area inj 1–5 | D46:D50 | INPUT_AREA | **Chromatography** |
| Std Mean | D51 | COMPUTED | `=IFERROR(AVERAGE(D46:D50),"")` |
| Std ± SD | D52 | COMPUTED | `=IFERROR(STDEV(D46:D50),"")` |
| Std % RSD | D53 | COMPUTED | `=IFERROR((D52/D51)*(100),"")` |
| Std %RSD limit | E53 | CONSTANT | `NMT 2.0 %` |
| Bracketing Std areas (mirror) | H46:H50 | COMPUTED | `=D46 … =D50` |
| BKT area | H51 | INPUT_AREA | **Chromatography** |
| BKT Mean / ±SD / %RSD | H52 / H53 / H54 | COMPUTED | `=IFERROR(AVERAGE(H46:H51),"")`, `=IFERROR(STDEV(H46:H51),"")`, `=IFERROR((H53/H52)*(100),"")` |
| Spare column stats | H40:H42 | COMPUTED | `=IF(COUNT(H28:H37)=0," ",AVERAGE(H28:H37))`, `=IF(H40=" "," ",STDEV(H28:H37))`, `=IF(H41=" "," ",(H41*100/H40))` — **uses `COUNT` and sentinel `" "` instead of IFERROR** |
| Analysed By / Checked By | C57 / G57 | CONTEXT | |

- **Reportable result(s):** `Acceptance value (AV)` (F43) plus `Mean`, `Min`, `Max`, `SD`, `% RSD` of the 10 unit `% of LC` values.
- **Repeating structure:** sample units **10** (n selectable 10 or 30 via the k lookup); std injections 5 + 1 bracket.
- **System suitability:** std `% RSD` vs `NMT 2.0 %`; `AV` vs `Not more than 15.0`.
- **Conditional/lookup logic:** `IFERROR`, nested `IF` for the USP AV branch, `IF` lookup for k, `COUNT` guard, `ROUND(x,1)` on `% of LC`/Mean/AV, `ROUND(x,4)` on SD, `ROUND(x,2)` on %RSD.

---

## 9. `CU by weight variation.xlsx`

- **Test category:** Content Uniformity **by weight variation** (for vials) with USP `<905>` Acceptance Value. Amphotericin B Liposome for Injection.
- **Sheet(s):** `CONTENT UNIFORMITY`. Dimensions `A1:K58`.
- **Layout shape:** Header → 2 side-by-side blocks of 15 unit rows (units 1–15 left, 16–30 right) → statistics + AV block.
- **Archetype:** A4 — content-uniformity / acceptance-value (gravimetric variant, **no chromatography input at all**).

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Product Name | C5 | CONTEXT | `Amphotericin B Liposome for Injection` |
| Batch No. | C7 | CONTEXT | `ES210158` |
| Lable Claim | C8 | CONTEXT | `Each vial contains 50.0 mg Amphotericin B USP` |
| T.R.F. No. | C9 | CONTEXT | |
| A.R. No. | C10 | CONTEXT | |
| Template No. | C11 | CONTEXT | `LNB_AD_526` |
| **% Assay** | C12 | INPUT_WEIGHING | 108.9 — **carried over from the Assay test** |
| Av. Filled Weight (mg) | C13 | COMPUTED | `=IFERROR((AVERAGE(B23:B37,H23:H37)), "")` |
| Av. Empty Weight (mg) | C14 | COMPUTED | `=IFERROR((AVERAGE(C23:C37,I23:I37)), "")` |
| Av. Net Weight (mg) | D14 | COMPUTED | `=IFERROR((AVERAGE(D23:D37,J23:J37)), "")` |
| C.U. of (condition) | I19 | CONTEXT | `INITIAL` |
| (Number of Units) n | C19 | INPUT_WEIGHING | 10 |
| **K** | C20 | COMPUTED (lookup) | `=IF(C19=10,2.4, IF(C19=30,2))` |
| Filled Vial Weight (units 1–15 / 16–30) | B23:B37 / H23:H37 | INPUT_WEIGHING | mg |
| Empty Vial Weight | C23:C37 / I23:I37 | INPUT_WEIGHING | mg |
| Net Weight | D23:D37 / J23:J37 | COMPUTED | `=IFERROR((B23-C23), "")` |
| **% C.U. (per unit)** | E23:E37 / K23:K37 | COMPUTED | `=IFERROR((D23*$C$12/$D$14), "")` → `%CU = NetWeight × %Assay / AvNetWeight` |
| Mean (x) | K39 | COMPUTED | `=IFERROR((ROUND(AVERAGE(E23:E37,K23:K37),1)), "")` — **ROUND 1** |
| Minimum | K40 | COMPUTED | `=IFERROR((MIN(E23:E37,K23:K37)), "")` |
| Maximum | K41 | COMPUTED | `=IFERROR((MAX(E23:E37,K23:K37)), "")` |
| SD (s) | K42 | COMPUTED | `=IFERROR((ROUND(STDEV(E23:E37,K23:K37),2)), "")` — **ROUND 2** |
| % RSD | K43 | COMPUTED | `=IFERROR((ROUND(K42*100/K39,2)), "")` — **ROUND 2** |
| M-rule text | A41:A43 | CONSTANT | USP M-selection rules (98.5 / 101.5) |
| AV formula text | D41:D43 | CONSTANT | `AV=ks`, `AV=98.5-X+ks`, `AV=X-101.5+ks` |
| **Acceptance value (AV)** | J46 | COMPUTED | `=IFERROR((ROUND(IF(K39<101.5,IF(K39<98.5,((98.5-K39)+($C$20*K42)),$C$20*K42),((K39-101.5)+($C$20*K42))),1)), "")` — **ROUND 1** |
| M value | A47 | COMPUTED | `=IF(98.5>=K39<=101.5,K39)+IF(K39<98.5, "98.5")+IF(K39>101.5, "101.5")` — ⚠ **invalid chained comparison; returns `#VALUE!` in most cases** |
| M fallback | C47 | COMPUTED | `=IF(A47=0,K39, "")` with note `If 'M' value gives '0.0', than consider below value for 'M'` |
| Analyzed By / Checked By | A50 / H50 | CONTEXT | |

- **Reportable result(s):** `Acceptance value (AV)`, `Mean % C.U.`, `Min`, `Max`, `SD`, `% RSD`.
- **Repeating structure:** unit slots **30** (2 columns × 15 rows); populated 10 in this copy; n selectable 10/30.
- **System suitability:** none chromatographic; AV limit implied (NMT 15.0).
- **Conditional/lookup logic:** `IFERROR`, nested `IF` AV branch, `IF` k lookup, `ROUND(x,1)` / `ROUND(x,2)`; **one broken formula (A47)**.

---

## 10. `Calculation of Sodium Metabisulfite by Titrimetry.xlsx`

- **Test category:** Titrimetry (content of Sodium Metabisulfite in Amikacin Sulfate Injection) — **no chromatography**.
- **Sheet(s):** `Initial `. Dimensions `A1:M53`.
- **Layout shape:** Header → titrant normality/factor strip → repeating sample rows (16 slots at 2-row pitch, grouped in 4s for `% Mean`).
- **Archetype:** A5 — simple titrimetric/gravimetric single-record + sample rows.

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Product Name | B6 | CONTEXT | `Amikacin Sulfate Injection USP 250mg/mL` |
| Test | B7 | CONTEXT | `Content of Sodium Metabisulfite` |
| Analysis as per | B8 | CONTEXT | `QC-DP-MOA-006-05 (For US Market)` |
| Analyzed By | K6 | CONTEXT | |
| Instrument ID | K7 | CONTEXT | `NA` |
| Date of Analysis | K8 | CONTEXT | |
| LNB No. | I9 | CONTEXT | |
| Titrant name | B10 | CONTEXT | `K2Cr2O7` |
| **Normality (N)** | D10 | INPUT_WEIGHING | 0.1019 |
| **Factor** | G10 | INPUT_WEIGHING | 47.5 (mg equivalent per mL per N) |
| Batch No. | A15, A17, … | CONTEXT | `EP20_336-350 (US Market)` |
| Stability Condition | B15… | CONTEXT | `Initial_Set-1` |
| Packing Detail | C15… | CONTEXT | `Glass Vial` |
| TRF No. / AR No. | D15 / E15 | CONTEXT | |
| ml of Sample | F15… | INPUT_WEIGHING | 10 |
| **ml of Titrant** | G15… | INPUT_WEIGHING | 11.9 — burette reading |
| L.C. of Sodium metabisulfite | H15… | CONTEXT/INPUT | 6.6 |
| Normality (per row) | I15… | COMPUTED | `=$D$10` |
| Factor (per row) | J15… | COMPUTED | `=$G$10` |
| **mg/ml** | K15… | COMPUTED | `=IFERROR(((G15*I15*J15*1000)/(F15*1000)), "")` → `mg/mL = TitrantVol × Normality × Factor × 1000 / (SampleVol × 1000)` (the two `1000`s are CONSTANTS and cancel) |
| **% Result** | L15… | COMPUTED | `=IFERROR((K15/H15*100), "")` → `mg/mL ÷ LC × 100` |
| **% Mean** | M15, M19, M23, … | COMPUTED | `=IFERROR((AVERAGE(L15:L18)), "")` → mean of 2 sets (4 rows) |
| Analyzed By / Checked By | A48 / F48 | CONTEXT | |

- **Reportable result(s):** `% Mean` (M column); supporting `mg/ml` and `% Result` per set.
- **Repeating structure:** sample slots **16** (rows 15–46 at 2-row pitch), `% Mean` every 4 rows.
- **System suitability:** none.
- **Conditional/lookup logic:** `IFERROR(...,"")` only; no rounding.

---

## 11. `Content of Lyso PC PG_ mgvial_Ampho.xlsx`

- **Test category:** Content of degradation lipids **Lyso-PC / Lyso-PG** by HPLC, reported as **mg/vial**. Amphotericin B Liposome for Injection.
- **Sheet(s):** `1`. Dimensions `B2:P67`.
- **Layout shape:** Header → 2-compound standard table → **multi-peak area grid** (Lyso PC resolves into up to 5 peaks, Lyso PG into 2) with row-wise `Sum Area` roll-up → BKT standard grid of the same shape → sample area grid (2 injections) → results block.
- **Archetype:** A2-variant — multi-component assay with **row-wise peak summation** (a compound = sum of several peaks).

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Generic Name / Product Name | C6 / C7 | CONTEXT | `Amphotericin B Liposome for injection` |
| Batch No. | C8 | CONTEXT | `ES20E019` |
| TRF No. / AR No. | C9 / C10 | CONTEXT | `NA` |
| Batch No. (mirror) | C11 | COMPUTED | `=C8` |
| Sorage Condition | C12 | CONTEXT | `Initial` |
| Packing Detail | C13 | CONTEXT | `5% Dextrose (PVC Bag, 0.2mg/mL)` |
| Test | C14 | CONTEXT | `LYSO PC-LYSO PG` |
| Analysis as per | C15 | CONTEXT | `IN HOUSE` |
| Analysed By | C16 | CONTEXT | |
| Instrument Id. | C17 | CONTEXT | `AD/HPLC/041` |
| Date of Analysis | C18 | CONTEXT | |
| Compound Name | B23 / B24 | CONTEXT | `Lyso PC`, `Lyso PG` |
| Weight in mg | C23 / C24 | INPUT_WEIGHING | 17.547 / 18.411 |
| Vol / Pip / Vol | D23:F24 | INPUT_WEIGHING | 50,4,20 / 100,4,20 |
| MV of Base / MV of Salt | G23,H23 / G24,H24 | INPUT_WEIGHING | 1/1 and 511.61/534.6 |
| Potency | I23 / I24 | INPUT_WEIGHING | 98 / 98.3 |
| LC | J23 / J24 | INPUT_WEIGHING | 1 / 1 |
| STD peak areas Lyso PC-1…5 | C28:G33 | INPUT_AREA | **Chromatography** — 6 injections × 5 sub-peaks |
| STD peak areas Lyso PG-1…2 | H28:I33 | INPUT_AREA | **Chromatography** — 6 injections × 2 sub-peaks |
| Lyso PC Sum Area per injection | L28:L33 | COMPUTED | `=IF(SUM(C28:G28)=0," ",SUM(C28:G28))` → **row-wise SUM with blank sentinel** |
| Lyso PG Sum Area per injection | M28:M33 | COMPUTED | `=IF(SUM(H28:I28)=0," ",SUM(H28:I28))` |
| Mean (STD) | L34 / M34 | COMPUTED | `=IF(COUNT(L28:L33)=0," ",AVERAGE(L28:L33))` |
| SD (STD) | L35 / M35 | COMPUTED | `=STDEV(L28:L33)` |
| % RSD (STD) | L36 / M36 | COMPUTED | `=L35*100/L34` |
| BKT STD peak areas | C40:I45 | INPUT_AREA | **Chromatography** |
| BKT Sum Area | L40:L45 / M40:M45 | COMPUTED | same `IF(SUM(...)=0," ",SUM(...))` pattern |
| Pooled Mean / SD / %RSD | L46,M46 / L47,M47 / L48,M48 | COMPUTED | `=IF(COUNT(L28:L33,L40:L45)=0," ",AVERAGE(L28:L33,L40:L45))`, `=STDEV(L28:L33,L40:L45)`, `=L47*100/L46` |
| Sample Batch No./Condition/Packing/TRF/AR | B53:F53 | COMPUTED | `=C11`, `=C12`, `=C13`, `=C9`, `=C10` (mirrors of header) |
| mL (sample taken) | G53 | INPUT_WEIGHING | 10 |
| Vol / Pip / Vol | H53 / I53 / J53 | INPUT_WEIGHING | 200 / 10 / 20 |
| Sample peak areas (2 injections × 7 sub-peaks) | C57:I58 | INPUT_AREA | **Chromatography** |
| Sample Sum Area | L57:L58 / M57:M58 | COMPUTED | `=IF(SUM(C57:G57)=0," ",SUM(C57:G57))` |
| **Lyso PC mg/vial (inj-1)** | C61 | COMPUTED | `=L57/L34*C23/D23*E23/F23*G23/H23*H53/G53*J53/I53*I23/100*12.5` → `mg/vial = SumArea/MeanStdSum * StdWt/V1 * Pip/V2 * MWbase/MWsalt * SmpVol/SmpmL * SmpVol2/SmpPip * Potency/100 × 12.5`. **`12.5` is a hardcoded CONSTANT (vial-volume factor) present only on inj-1** |
| Lyso PC mg/vial (inj-2) | C62 | COMPUTED | `=L58/L34*C23/D23*E23/F23*G23/H23*J53/I53*H53/G53*I23/100` — ⚠ **`12.5` factor is MISSING here** |
| Lyso PG mg/vial (inj-1 / inj-2) | D61 / D62 | COMPUTED | `=M57/M34*C24/D24*E24/F24*J53/I53*H53/G53*G24/H24*I24/100*12.5` / same without `*12.5` |
| Lyso PC Assay (%) | E61 / E62 | COMPUTED | `=C61*100/J23` → `mg/vial × 100 / LC` |
| Lyso PG Assay (%) | F61 / F62 | COMPUTED | `=D61*100/J24` |
| **Avg (all four result columns)** | C63:F63 | COMPUTED | `=(C61+C62)/2` etc. |
| Stray scratch cells | P22 / P25 | COMPUTED | `=C28+D28+E28+G28`, `=+L28+G28` — leftover working cells, no label |
| Analyzed By / Checked By / Date | B65 / K65 / B66 | CONTEXT | |

- **Reportable result(s):** `Lyso PC mg/vial`, `Lyso PG mg/vial`, `Lyso PC Assay %`, `Lyso PG Assay %` (Avg row 63).
- **Repeating structure:** compounds 2; sub-peaks per compound 5 (PC) and 2 (PG); STD injections 6; BKT injections 6; sample injections 2.
- **System suitability:** `% RSD` of Sum Area per compound, STD-only and STD+BKT pooled.
- **Conditional/lookup logic:** `IF(SUM(...)=0," ",…)` and `IF(COUNT(...)=0," ",…)` sentinels instead of IFERROR; no rounding.
- ⚠ **Inconsistency:** the `12.5` factor on injection-1 rows but not injection-2 rows makes the `Avg` row mathematically wrong. Needs a business decision.

---

## 12. `Content of Lyso PC PG_mgmL_Ampho.xlsx`

- **Test category:** Same test as #11 but reported as **mg/mL** instead of mg/vial.
- **Sheet(s):** `1`. Dimensions `B2:P67`. **Structurally identical to #11** — same cells, same labels, same standard/BKT/sample grids.
- **Archetype:** A2-variant (multi-peak-sum multi-component assay).

### Deltas vs #11 (everything else identical)

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Sample Vol / Pip / Vol | H53 / I53 / J53 | INPUT_WEIGHING | **20 / 1 / 1** (vs 200 / 10 / 20 in the mg/vial sheet) |
| Result column headers | C60 / D60 | CONSTANT | `Lyso PC mg/mL`, `Lyso PG mg/mL` |
| **Lyso PC mg/mL (inj-1)** | C61 | COMPUTED | `=L57/L34*C23/D23*E23/F23*G23/H23*H53/G53*J53/I53*I23/100` — **no `12.5` factor** |
| Lyso PC mg/mL (inj-2) | C62 | COMPUTED | `=L58/L34*C23/D23*E23/F23*G23/H23*J53/I53*H53/G53*I23/100` |
| Lyso PG mg/mL (inj-1 / inj-2) | D61 / D62 | COMPUTED | `=M57/M34*C24/D24*E24/F24*J53/I53*H53/G53*G24/H24*I24/100` (both rows) |
| Lyso PC / PG Assay % | E61:F62 | COMPUTED | `=C61*100/J23`, `=D61*100/J24` |
| Avg | C63:F63 | COMPUTED | `=(C61+C62)/2` etc. |

- **Reportable result(s):** `Lyso PC mg/mL`, `Lyso PG mg/mL`, `Lyso PC Assay %`, `Lyso PG Assay %`.
- **Repeating structure / suitability / logic:** as #11.
- ✅ This variant is internally consistent (no stray `12.5`), which confirms #11's inj-1 factor is the anomaly.

---

## 13. `Dissolution sheet_ Franz diffusion cell_Tapinarof.xls`

- **Test category:** **IVRT** (In-Vitro Release Testing) via Franz diffusion cell — Topical Tapinarof Cream 1 % w/w. Calibration-curve based (not single-standard).
- **Sheet(s):** `LE6001` (batch-named). Dimensions `A1:T114`.
- **Layout shape:** Header → 6-point calibration curve + LQC/MQC/HQC → SLOPE/INTERCEPT/CORREL block → 18 bracketing QC injections (2 columns × 9) → **2-D grid** (6 time-points × 6 diffusion cells) repeated 5 times: Area, Concentration µg, Correction factor, Cumulative µg, Cumulative µg/cm², Cumulative % → per-cell SLOPE/CORREL/r².
- **Archetype:** A3-variant — 2-D release grid **driven by a regression calibration curve** rather than a single standard.

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Product name | B5 | CONTEXT | `Topical Tapinarof Cream 1% w/w` |
| Component name | B6 | CONTEXT | `Tapinarof` |
| Label claim (%) | B7 | INPUT_WEIGHING | 1 |
| Instrument | B8 | CONTEXT | `Hanson Franz Diffusion` |
| Instrument ID | B9 | CONTEXT | `AD/DTDS/001` |
| Membrane type/make | B10 | CONTEXT | `0.45µm Ultipor Nylon PALL Life Science` |
| Membrane B.No | B11 | CONTEXT | |
| Receptor media | B12 | CONTEXT | `DMSO+IPA+Water(60:20:20)` |
| **Total media volume (mL)** | B13 | INPUT_WEIGHING | 7 |
| Sample Dilution (mL) | B14 / C14 | INPUT_WEIGHING | 1 / 1 |
| **Media replacement volume (mL)** | B15 | INPUT_WEIGHING | 1 |
| Date of Analysis | J5 | CONTEXT | |
| Working/reference standard number | J6 | CONTEXT | `WS/25/079` |
| Use before date | J7 | CONTEXT | |
| Potency (%) | J8 | INPUT_WEIGHING | 99.67 |
| Temperature (°C) | J9 | INPUT_WEIGHING | 32 |
| Time points (Min) | J10 | CONTEXT | `40, 80,120,160,200,240` (free text) |
| Average weight (mg) | J11 | INPUT_WEIGHING | 100 |
| Batch No. | J12 | CONTEXT | `LE6001` |
| TRF number / A R No. | J13 / J14 | CONTEXT | |
| **Surface Area of Donor chamber (cm²)** | J15 | INPUT_WEIGHING | 1.76 |
| Calibration Concentration (%) levels | B19:B24 | CONSTANT | 0.01, 0.05, 0.15, 0.3, 0.4, 0.6 |
| Standard Weight in mg | C19 | INPUT_WEIGHING | 89.73 |
| Diluted to (mL) / mL / mL | D19, E19, F19 (and E22, F22 for the upper levels) | INPUT_WEIGHING | 50 / 5 / 50 ; 1 / 1 |
| mL taken / Diluted to (mL) per level | G19:G24 / H19:H24 | INPUT_WEIGHING | 1,5,15,3,4,6 / 50 each |
| LQC / MQC / HQC prep chains | C25:H27 | INPUT_WEIGHING | 3 QC levels |
| **Theoretical concentration (ppm)** | B31:B36 | COMPUTED | `=$C$19/$D$19*$E$19/$F$19*G19/H19*1000*$J$8/100` → `ppm = StdWt/Vol1 * Pip/Vol2 * mLtaken/DilutedTo × 1000 × Potency/100` (`1000` CONSTANT) |
| **Area Response (calibration)** | C31:C36 | INPUT_AREA | **Chromatography** |
| Observed concentration (ppm) | D31:D36 | COMPUTED | `=(C31-$C$38)/$C$37` → `(Area − Intercept)/Slope` |
| % Recovery | E31:E36 | COMPUTED | `=D31/B31*100` |
| **SLOPE** | C37 | COMPUTED | `=ROUND(SLOPE(C31:C36,B31:B36),2)` — **ROUND 2** |
| **INTERCEPT** | C38 | COMPUTED | `=ROUND(INTERCEPT(C31:C36,B31:B36),1)` — **ROUND 1** |
| **CORRELATION** | C39 | COMPUTED | `=ROUND(CORREL(C31:C36,B31:B36),3)` — **ROUND 3** |
| Bracketing QC theoretical conc. | B43:B51 / G43:G51 | COMPUTED | `=$C$25/$D$25*$E$25/$F$25*$G$25/$H$25*1000*$J$8/100` per QC level |
| Bracketing QC Area Response | C43:C51 / H43:H51 | INPUT_AREA | **Chromatography** — 18 bracketing injections (LQC/MQC/HQC × 6) |
| Bracketing observed conc. | D43:D51 / I43:I51 | COMPUTED | `=IFERROR((C43-$C$38)/$C$37," ")` |
| Bracketing % Recovery | E43:E51 / J43:J51 | COMPUTED | `=D43/B43*100` |
| **Sample weight (mg) per cell** | B54:G54 | INPUT_WEIGHING | 257.0 / 229.4 / 227.0 / 218.2 / 254.3 / 257.2 |
| Cell headers (mirrors) | B55:G55 | COMPUTED | `=B53 …` |
| Time (Min) | A56:A61 | CONSTANT | 40, 80, 120, 160, 200, 240 |
| **Sample Area grid** | B56:G61 | INPUT_AREA | **Chromatography** — 6 time-points × 6 cells = 36 areas |
| **Concentration in µg** | B65:G70 | COMPUTED | `=IFERROR(((B56-$C$38)/$C$37)*$B$13*$C$14/$B$14," ")` → `((Area − Intercept)/Slope) × TotalMediaVol × Dil2/Dil1` |
| **Correction factor** | B74:G79 | COMPUTED | first time-point hardcoded `0`; then `=IFERROR(B65*$B$15/$B$13," ")` → `Conc(t−1) × ReplacementVol / TotalMediaVol` |
| **Cumulative Drug release (µg)** | B83:G88 | COMPUTED | `=IFERROR(B65+B74," ")`, `=IFERROR(B66+B75+B74," ")` … → `Conc(t) + Σ CorrectionFactor(1..t)` |
| Time (√T) axis | A92:A97 | COMPUTED | `=SQRT($A$56)` … → **square-root-of-time transform** |
| **Cumulative µg/cm²** | B92:G97 | COMPUTED | `=IFERROR(B83/$J$15," ")` → `Cumulativeµg / DonorSurfaceArea` |
| Average / SD / %RSD across cells | H92:H97 / I92:I97 / J92:J97 | COMPUTED | `=AVERAGE(B92:G92)`, `=STDEV(B92:G92)`, `=I92/H92*100` |
| Slope per cell (Higuchi) | B98:G98 | COMPUTED | `=IFERROR(SLOPE(B92:B97,$A$92:$A$97)," ")` |
| Correlation (r) per cell | B99:G99 | COMPUTED | `=IFERROR(CORREL($A$92:$A$97,B92:B97)," ")` |
| r² per cell | B100:G100 | COMPUTED | `=IFERROR(B99*B99," ")` |
| Formula note | A102 | CONSTANT | `Cumulative % drug release= (Cumulative drug release/1000*Avg.weight/Label Claim/sample weight*100)` |
| **Cumulative % drug release** | B104:G109 | COMPUTED | `=IFERROR(B83/1000*$J$11/$B$54/$B$7*100," ")` → `Cumµg/1000 × AvgWeight / SampleWeight / LabelClaim × 100` (`1000` CONSTANT) |
| Average / SD / %RSD | H104:J109 | COMPUTED | `=AVERAGE(B104:G104)`, `=STDEV(...)`, `=I104/H104*100` |
| Correlation / r² (on % release) | B110:G110 / B111:G111 | COMPUTED | `=IFERROR(CORREL($A$92:$A$97,B104:B109)," ")`, `=IFERROR(B110*B110," ")` |
| Analysed by / Checked by / Date | A112 / H112 / A113 | CONTEXT | `H113 = =A113` |

- **Reportable result(s):** `Cumulative µg/cm²` profile (with Average/SD/%RSD), Higuchi `Slope`, `r²`, and `Cumulative % drug release` profile.
- **Repeating structure:** calibration levels **6** + QC levels 3; bracketing QC injections **18**; diffusion cells **6**; time-points **6**; five stacked 6 × 6 grids.
- **System suitability:** calibration `CORRELATION` (ROUND 3), `% Recovery` per calibration and per bracketing QC, per-cell `r²`, per-time-point `%RSD`.
- **Conditional/lookup logic:** `IFERROR(...," ")` (space sentinel, not empty string), `ROUND(x,1/2/3)`, `SLOPE`, `INTERCEPT`, `CORREL`, `SQRT`.

---

## 14. `Dissolution sheet_ without replacement_ Characterization_6 units_Ampho.xlsx`

- **Test category:** In-Vitro Release / Dissolution by HPLC, **without media replacement** (Characterization protocol). Amphotericin B Liposome for Injection 50 mg/vial.
- **Sheet(s):** `1`. Dimensions `A1:U82`, printed as 2 pages.
- **Layout shape:** Header + dissolution parameters → single standard prep with 3-stage dilution → 6 standard injections + 24 bracketing standards → **explicit System Suitability Criteria table** → Test Preparation strip → **2-D grid**: 8 time-points × 6 units (Sample Area) and the same shape for `% Content` with row-wise Mean/SD/%RSD/Min/Max.
- **Archetype:** A3 — 2-D dissolution grid (without-replacement variant with **hardcoded declining media-volume constants**).

### Field inventory

| Label | Cell | Class | Detail / raw formula |
|---|---|---|---|
| Company header | A1 | CONSTANT | `Emcure Pharmaceuticals Limited - R & D (GANDHINAGAR)` |
| PRODUCT | B2 | CONTEXT | `Amphotericin B Liposome for Injection, 50 mg/vial` |
| **LABEL CLAIM (mg/mL)** | B4 | INPUT_WEIGHING | 50 |
| STRENGTH | B5 | CONTEXT | `50 mg/vial` |
| TEST PERFORMED | B6 | CONTEXT | `In Vitro Release` |
| DATE OF ANALYSIS | B7 | CONTEXT | |
| Batch No. | B9 | CONTEXT | `ES20E012` |
| Protocol No. | F10 | CONTEXT | `MP/AD/EP20_394-05/01` |
| LNB No. | O6 | CONTEXT | `LNB_AD_569` |
| Disso Media | L2 | CONTEXT | `Phosphate Buffer pH 7.4 with 2% Sodium deoxycholate` |
| Apparatus | L3 | CONTEXT | `USP-II` |
| RPM | L4 | INPUT_WEIGHING | 75 |
| Tempre (°C) | L5 | INPUT_WEIGHING | 37 |
| STANDARD PREPARATION name | B12 | CONTEXT | `Amphotericin B USPRS` |
| Wt. in mg | C13 | INPUT_WEIGHING | 5.037 |
| Dilution chain (mL) | E13 (25), G13 (5), J13 (100), L13 (5), N13 (50) | INPUT_WEIGHING | diluent / media stages |
| %Potency | Q13 | INPUT_WEIGHING | 99.4 |
| **Concen. (ppm)** | S13 | COMPUTED | `=ROUND(C13/E13*G13/J13*L13/N13*Q13/100*1000,3)` → **ROUND 3**, `1000` CONSTANT |
| Standard Area Inj-1…Inj-6 | C16:H16 | INPUT_AREA | **Chromatography** |
| Standard Mean | I16 | COMPUTED | `=AVERAGE(C16:H16)` |
| Standard RSD | J16 | COMPUTED | `=TRUNC(STDEV(C16:H16)/I16*100,5)` — **TRUNC 5** |
| Bracketing Std Areas BKT-1…BKT-24 | B19:G19, B21:F21, B23:F23, B25:F25 (4 rows of 6) | INPUT_AREA | **Chromatography** — 24 bracketing standards |
| Bracketing pooled Mean | H19 | COMPUTED | `=TRUNC(AVERAGE(B16:H16,A19:G19,A21:F21,A23:F23,A25:F25),1)` — **TRUNC 1**; ⚠ ranges start at column A while the data starts at B (off-by-one) |
| Bracketing pooled RSD | I19 | COMPUTED | `=TRUNC(STDEV(B16:H16,B19:G19,B21:F21,B23:F23,B25:F25)/H19*100,5)` — **TRUNC 5** |
| **System Suitability Criteria (5 rows of text)** | A28:A32 | CONSTANT | 1. no blank interference; 2. tailing factor **NMT 2.5**; 3. theoretical plates **NLT 1500**; 4. std %RSD NMT 5.0 %; 5. bracketing+std %RSD NMT 5.0 % |
| Observation — blank interference | G28 | INPUT_WEIGHING (text) | `Complies` |
| Observation — **tailing factor** | G29 | INPUT_WEIGHING | 1.28 |
| Observation — **theoretical plates** | G30 | INPUT_WEIGHING | 7140 |
| Observation — std %RSD | G31 | COMPUTED | `=J16` |
| Observation — bracketing %RSD | G32 | COMPUTED | `=I19` |
| Sample (Wt.) | B35 | INPUT_WEIGHING | 1 |
| With Water (mL) | D35 | INPUT_WEIGHING | 100 |
| (mL) | F35 | INPUT_WEIGHING | 1 |
| **Media Volume (mL)** | H35 | INPUT_WEIGHING | 500 |
| (mL) / (mL) | K35 / L35 | INPUT_WEIGHING | 1 / 1 |
| **Withdrawal Volume (mL)** | N35 | INPUT_WEIGHING | 5 |
| **Replenishment Volume (mL)** | P35 | INPUT_WEIGHING | 0 (→ without replacement) |
| DISSO ID / HPLC ID / Column ID | J40 / M40 / P40 | CONTEXT | `AD/TDT/009`, `AD/HPLC/015`, `AD/LC/2408` |
| Time Interval (Hours) | A41:A48 | CONSTANT | 1, 2, 3, 4, 6, 8, 10, 12 |
| **Sample Area grid** | B41:G48 | INPUT_AREA | **Chromatography** — 8 time-points × 6 units |
| **% Content, t = 1 h** | B57:G57 | COMPUTED | `=B41/$I$16*$C$13/$E$13*$G$13/$J$13*$L$13/$N$13*$D$35/1*$H$35/$F$35*$Q$13/100*1/$B$4*100` → `%Content = Area/MeanStdArea * StdWt/Vol1 * Pip/Vol2 * Pip/Vol3 * WithWater/1 * MediaVol/1mL * Potency/100 * 1/LabelClaim * 100` |
| **% Content, t = 2 h** | B58:G58 | COMPUTED | `=B42/$I$16*…*$D$35/1*495/$F$35*$Q$13/100*1/$B$4*100+(B57/495*5)` → same chain but media volume **hardcoded `495`**, plus carry-back term `+ (%Content(t−1)/495 × 5)` where `5` = withdrawal volume |
| **% Content, t = 3 h** | B59:G59 | COMPUTED | media volume `490`; carry-back `+(B58/490*5)+(B57/495*5)` |
| **% Content, t = 4 h** | B60:G60 | COMPUTED | media volume `485`; carry-back over 3 prior points |
| **% Content, t = 6 h** | B61:G61 | COMPUTED | media volume `480` |
| **% Content, t = 8 h** | B62:G62 | COMPUTED | media volume `475` |
| **% Content, t = 10 h** | B63:G63 | COMPUTED | media volume `470` |
| **% Content, t = 12 h** | B64:G64 | COMPUTED | media volume `465`; carry-back `+(B63/465*5)+(B62/470*5)+(B61/475*5)+(B60/480*5)+(B59/485*5)+(B58/490*5)+(B57/495*5)` |
| Mean per time-point | H57:H64 | COMPUTED | `=AVERAGE(B57:G57)` |
| SD per time-point | I57:I64 | COMPUTED | `=STDEV(B57:G57)` |
| %RSD per time-point | J57:J64 | COMPUTED | `=I57/H57*100` |
| Min / Max per time-point | K57:K64 / L57:L64 | COMPUTED | `=MIN(B57:G57)` / `=MAX(B57:G57)` |

- **Reportable result(s):** `% Content of Amphotericin B` profile per time-point per unit, with `Mean`, `SD`, `%RSD`, `Min.`, `Max.` per time-point.
- **Repeating structure:** units **6**; time-points **8**; standard injections 6; bracketing standards **24** (4 × 6, pooled only).
- **System suitability:** explicit 5-criterion table with criteria text + observation pairs (2 of the observations — tailing factor and theoretical plates — are manual chromatographic-system values, not areas).
- **Conditional/lookup logic:** `TRUNC(x,5)` on RSDs, `TRUNC(x,1)` on pooled bracketing mean, `ROUND(x,3)` on std ppm. **No IFERROR anywhere.**
- ⚠ **CONSTANTS to parameterise:** the declining media-volume series `495, 490, 485, 480, 475, 470, 465` and the withdrawal volume `5` are **hardcoded in every formula** instead of derived from `Media Volume (H35) − n × Withdrawal Volume (N35)`. The engine should compute `V(n) = MediaVol − n × WithdrawalVol`.

---

## 15. `Dissolution sheet_ without replacement_ QC release_6 units_Ampho.xlsx`

- **Test category:** Same IVR test as #14 but the **QC-release** protocol (fewer time-points, tighter suitability limits).
- **Sheet(s):** `1`. Dimensions `A1:U84`. **Cell-for-cell the same template as #14** (same header cells, same standard block, same suitability table, same Test Preparation strip).
- **Archetype:** A3 — 2-D dissolution grid (without-replacement).

### Deltas vs #14

| Label | Cell | Class | Detail |
|---|---|---|---|
| TEST PERFORMED | B6 | CONTEXT | `IVR` (vs `In Vitro Release`) |
| Batch No. | B9 | CONTEXT | `ES23E018_25°C_3M` — **stability condition embedded in the batch string** |
| LNB No. / Protocol No. | O6 / F10 | CONTEXT | `NA` |
| Wt. in mg | C13 | INPUT_WEIGHING | 5 |
| HPLC ID / Column ID | M40 / P40 | CONTEXT | `AD/HPLC/042`, `AD/LC/2525` |
| Suitability criterion 2 — tailing factor | A29 | CONSTANT | **NMT 2.0** (vs 2.5 in the characterization sheet) |
| Suitability observation — tailing factor | G29 | INPUT_WEIGHING | 1.48 |
| Suitability criterion 3 — theoretical plates | A30 | CONSTANT | **NLT 2000** (vs 1500) |
| Suitability observation — plates | G30 | INPUT_WEIGHING | 5179 |
| Time Interval (Hours) | A41:A43 | CONSTANT | **1, 4, 8** — only 3 time-points |
| Sample Area grid | B41:G43 | INPUT_AREA | **Chromatography** — 3 time-points × 6 units |
| % Content grid | B58:G60 | COMPUTED | identical formula family; media volumes `$H$35` (t1), then hardcoded **`495`** (t2), **`490`** (t3), with carry-back `+(B58/495*5)` etc. |
| Mean / SD / %RSD / Max | H58:J60, L58:L60 | COMPUTED | `=AVERAGE(B58:G58)`, `=STDEV(B58:G58)`, `=I58/H58*100`, `=MAX(B58:G58)` |
| **Min** | K58:K60 | COMPUTED | `=MIN(B58:E58)` — ⚠ **only spans units 1–4, should be `B58:G58`** |

- **Reportable result(s):** `% Content of Amphotericin B` per time-point per unit with Mean/SD/%RSD/Min/Max.
- **Repeating structure:** units 6; time-points 3; std injections 6; bracketing standards 24 slots.
- **System suitability:** same 5-criterion table with product-specific limits.
- **Conditional/lookup logic:** `TRUNC(x,5)`, `TRUNC(x,1)`, `ROUND(x,3)`; no IFERROR.
- ⚠ Note the media-volume series is indexed on **withdrawal count**, not elapsed hours: t=4 h uses `495` because it is the 2nd withdrawal. The engine must model volume by withdrawal index.

---
