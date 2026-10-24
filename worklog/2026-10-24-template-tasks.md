# Worklog — 24 October 2026

Template / worksheet changes: an additive edit to **TPL-A12-0003 — Amphotericin
B Drug-to-Lipid Ratio** and a NEW **TPL-A6B-0002 — Octreotide pH-10 Dissolution**
template (in progress). Template & calculation edits are applied to the live
Active DB rows in `backend-v2/lims.db` (gitignored; a timestamped `lims.db.bak-*`
backup was taken before each change) and kept byte-for-byte in sync with the
declarative source modules. Source changes are committed locally.

**GxP caveat:** edits to existing templates are applied directly to the live
Active DB row, not through the app's approve / e-sign flow.

---

## TPL-A12-0003 — editable "Acceptance Ranges" strip (commit f0e7f29)

- Added an editable, DISPLAY-ONLY "Acceptance Ranges" strip to the Amphotericin
  template: a new `acceptance_ranges` singleton of 5 pre-filled, editable
  free-text fields inserted immediately before the `batches` table, so it reads
  as a ranges header after the section title.
- Defaults match the criteria: Assay of Cholesterol / HSPC / Amphotericin B
  "90.0% to 120.0%", Assay of DSPG "80.0% to 120.0%", Calculated Drug to Lipid
  ratio "Between 0.11 to 0.17".
- Strictly additive: the 5 fields feed no expression, criterion, or resultRef,
  so batch math, the drug/lipid ratio, all gold values, and the 5 blocking
  criteria are unchanged.
- Mechanism: a real editable `input`/text singleton (NOT `headerContext`, which
  the backend schema ignores and the frontend renders read-only). No frontend
  change needed — the singleton renders as an editable grid above the table.
- Verified: `--validate-only` exit 0; parity test passing (incl. 2 new range
  tests + unchanged gold 0.1511 / 0.1476 / 0.1500 and criteria); DB row 36
  UPDATEd and confirmed byte-for-byte + canonical equal to the module, still
  Active/v1/test_id 33 (TST-ALDR); A2-0004 (row 35) untouched; same 5 known
  pre-existing failures. Backup `lims.db.bak-ampho-ranges-*`.

## TPL-A6B-0002 — NEW: Octreotide pH-10 Dissolution (IN PROGRESS)

- Started building a new dissolution template reproducing the
  `Dissolution sheet_Octreotide_PH 10.xlsx` calculation sheet, bound to a NEW
  Test Master entry tagged exactly **"Dissolution-Octreolide-pH-10"**
  (TST-DISS-OCT-PH10), archetype A6b (with replacement), code TPL-A6B-0002.
- Source traced from `_dumps/Dissolution sheet_Octreotide_PH 10.txt` (full
  cell + formula dump). Design phase mapped every section to a group and
  resolved formula ambiguities by prototyping against the real evaluator:
  - Standard detail (Octreotide Acetate, potency 89.41, weight 25.65, dilution
    25/5/50 → Conc ppm), standard + BKT areas with Mean/SD/%RSD and pooled mean.
  - Dissolution parameters (Volume 10 mL, Apparatus "Bottle Rotating", RPM 50,
    Temp "37°C and 55°C", media text), 6-unit sample-weight table (1 hr / 4 hr /
    24 hr weights) with Mean/SD/%RSD, pooled-blend % assay 4.12, media/pipette/VF
    and withdraw-replace inputs.
  - Three timepoint blocks (1 hr @ 37°C, 4 hr @ 55°C, 24 hr @ 55°C), 6 units
    each: % Residue (K-column per-timepoint weight path) and the
    residue-from-assay % Release block C70 = (A32 − B70)/A32 × 100 with
    Mean/Min/Max/RSD.
  - Resolved ambiguities: the rows 58–69 %Release K64 path is a DEAD #VALUE!
    scaffold on the source (empty merged F19, blank B64:B69) → omitted; the
    L/M cumulative-replacement chain continues as #VALUE! and no reportable
    depends on a live M → not modelled, flagged as a lab decision rather than
    guessed; the sample-weight SD reproduces the sheet's STDEV-includes-mean-cell
    quirk via `sd(pool(col,[mean]))`.
- Design APPROVED (design-review: 0 HIGH, 0 MEDIUM after one revision round that
  pinned the single blocking SST criterion `sst_rsd_criterion(target=
  "std_stats.rsd_std", limit=2.0)`). Implementation plan written; build loop
  running at time of this log. 20+ hand-derived gold values confirmed exact
  against the real WorksheetEvaluator. Backup
  `lims.db.bak-octreo-20261024-004505`.
- **Status: build in progress** (workflow running). To finish: seed Active,
  confirm DB byte-equal to module, parity test + same 5 known failures, commit.

---

## Commits (local, unpushed at time of log)

- `f0e7f29` — TPL-A12-0003 editable Acceptance Ranges strip
- TPL-A6B-0002 Octreotide dissolution — pending (build loop running)

## Pending / queued

- TPL-A6B-0002 Octreotide dissolution build to complete, then restart app.
- TPL-A2-0004 Drug-to-Lipid section transpose (compounds-as-rows + merged
  summary columns) — still queued from earlier.
- Unpushed: `f0e7f29` (+ the Octreotide commit once it lands).
