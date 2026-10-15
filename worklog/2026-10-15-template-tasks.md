# Worklog — 15 October 2026

Template / worksheet changes. All template & calculation edits were applied to
`backend-v2/lims.db` (gitignored; a timestamped `lims.db.bak-*` backup was made
before each change). Frontend changes are in source and were committed/pushed.

---

## TPL-A6A-0004 — Dissolution (main focus)

- Renamed **"Dissolution_15units" → "Dissolution_12units"**.
- Trimmed unit columns **15 → 12** across all three sections (Timepoints For
  Sample, % Drug Release - Uncorrected, Timepoint of % Release), including the
  carry/summary formulas.
- Removed the **"% Drug Release - Uncorrected"** section.
- Made **"Timepoint of % Release"** show the same columns as "Timepoints For
  Sample": hid the internal `media` / `carry_*` helper columns; kept
  Mean / SD / %RSD / Min / Max.
- Added a **Mean / Co-Relation footer** below "Standard Co-relation — Areas"
  (Mean = `stats.mean_std2` → 1725867; Co-Relation = `stats.std_corelation`
  → 1.005, 3 dp).
- Extended the **Graphical data chart** series to **12 units** (+ Mean default).
- **Fixed the % release calculation** (verified workflow, APPROVED):
  - Root cause: `media` was sourced from the wrong field (held 1, not 750),
    so media went 1, -4, -9... and all timepoints after the first went negative.
  - Fix: media now `if(rowno=1, test_prep.dilution_volume, prev.media -
    withdrawal + replenishment)` → stays 750.
  - Rebuilt the Bupivacaine three-stage math: uncorrected release (TRUNC 3) →
    correction factor (TRUNC 3) → cumulative corrected release (ROUND 0),
    summary rounding (mean 0 / sd 1 / rsd 1).
  - Verified against the sheet: U-1 corrected 30 min=20, 1 h=43, 2 h=64, …;
    30-min summary Mean=19, SD=1.1, %RSD=5.8. Parity test 8/8.
  - Note: worksheet 27's stored 30-min areas for units 2–4 look corrupted
    (data-entry issue, not formula) — may need re-entry.

## TPL-A12-0001 — Free & Entrapped Drug (liposomal)

- Fixed **Bracketing Standard Block 1 & 2** input tables not showing: row spec
  default was 0 → set to `{min:1, max:6, default:6}` so 6 rows render.
- Added a **Title text box** above each bracketing block table.
- Rebuilt the **Sample Preparation** table with the requested columns and
  reverse-engineered + verified all 6 calculated columns against the example
  rows (all match exactly):
  - % Con. = `area/mean_std × std_chain × potency/100 × (Vol1/sample_ml ×
    Vol2/Pip1) / L.C. × 100`
  - Bupivacaine (mg/mL) = `%AssayBup × L.C. / 100`
  - % Free Drug = `%Con / %AssayBup × 100`
  - Free Drug (mg/mL) = `%Free / 100 × L.C.`
  - % Entrapped = `100 − (FreeMgml / BupMgml × 100)`
  - Entrapped (mg/mL) = `%Entrapped / 100 × L.C.`
  - (Verified: row1 → %Con 5.0399, Bup 13.4995, %Free 4.9654, Free 0.6604,
    %Entrap 95.108, Entrap 12.649.)
- Removed per-row **Packing Detail / TRF No. / A.R. No. / L.C.** columns and
  moved them **above the table as auto-fetched header values** from the TRF
  (`trf.pack_details`, `trf.trf_number`, `trf.ar_number`,
  `trf.label_claim_numeric`). Rewired the L.C.-dependent formulas to the
  context field (`number(label_claim)`).
  - Caveat: header auto-fetch reflects one bound TRF per worksheet; prep sets
    spanning two TRFs would need separate worksheets.

## Frontend / print

- Added the **print-to-PDF chart**: the dissolution chart renders as a static
  PNG image in the printed worksheet (`WorksheetChartPrintImage.tsx`), since a
  live canvas prints blank. Wired into `PrintWorksheetPage.tsx`.

## Git

- Committed the frontend source changes: **`c436559`**
  "feat(worksheet): template search, compact wide tables with add/delete
  columns, landscape print, print-to-PDF chart image".
- Pushed branch **`MadhuriWorktree`** to `origin` (GitHub: MadhuriVS2026/LIMS_v1).

## Open / deferred

- Template & calculation edits live only in `lims.db` (gitignored). Not yet
  captured as declarative seed modules in source control.
- Worksheet 27 30-min areas for units 2–4 may be corrupted (re-enter).
