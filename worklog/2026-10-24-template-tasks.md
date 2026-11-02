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
  "std_stats.rsd_std", limit=2.0)`). 20+ hand-derived gold values confirmed exact
  against the real WorksheetEvaluator. Backup
  `lims.db.bak-octreo-20261024-004505`.
- **COMPLETED (commit e780345), review APPROVED.** New module
  `scripts/template_definitions/a6b_octreotide_ph10.py` (units-as-rows, three
  %Residue + three %Release-from-assay timepoint tables, J19 conc, pooled std
  stats, sheet's STDEV-includes-mean weight stats, single std_stats.rsd_std
  NMT 2.0 % SST; dead K64 block and L/M carry-over omitted per design),
  registered in `__init__.py`. Parity test 14/14. Seeded one Active TPL-A6B-0002
  bound to the exact test name; DB definition byte-equal to the module; 37 rows
  total, others undisturbed; A6B-0001 unchanged; full suite 798 passed, same 5
  known pre-existing failures. Reviewer re-derived gold by hand (J19 91.73466,
  D27 3035369.2857, K40 4.0387, K52 1.9356, C70 1.9417).
- Open item: the WITH-REPLACEMENT M-chain cumulative correction is deliberately
  omitted (source goes #VALUE! at M70 via the empty $F$19 divisor; nothing
  reportable depends on it). If the lab needs it active, that is a follow-up.

## Frontend — Test Templates worksheet preview

- Added a **"Worksheet" column** to the Test Templates list (`/test-templates`)
  showing each template as **`CODE NAME`** (e.g. `TPL-A1-0001 Assay by HPLC`),
  rendered as a clickable text link.
- New **read-only `WorksheetPreviewPage`** at `/test-templates/:id/worksheet`.
  Renders the worksheet layout **generically from the template `definition`**
  (no per-archetype branching), reached via the list column.
- **Section-wise Excel-like rendering** of the preview, driven by the
  definition for all templates:
  - Context: compact two-up key/value grid.
  - Singleton groups: labelled key/value block; calculated fields carry a
    `calc` tag.
  - Table / sequence groups: numbered rows + one column per field, and now
    render the previously-ignored **`headerContext`** (summary strip above the
    table) and **`footer`** (inline Mean/SD/%RSD strip below the table).
  - Acceptance criteria: Criterion / Limit / Severity / Result, with a
    blocking vs advisory severity tag.
  - Reportable result: resultRef + result unit.
  - All read-only (blank em-dash placeholder cells); only data source is the
    existing `useTemplateDetail` GET.
- Build verified: `npm run build` (`tsc -b && vite build`) passes, zero TS
  errors. (ESLint is not installed in the project — known pre-existing gap.)

## Frontend — TRF "Add Test Line"

- Changed the **Test dropdown** in the TRF "Add Test Line" dialog to list
  **active test templates by name** (`CODE NAME`) instead of the plain Tests
  master list. Options are keyed by template `id` (avoids test_id collisions);
  on selection the underlying **`test_id`** is resolved and sent, so the
  add-line backend contract is unchanged. Label changed to "Test Template";
  field resets on add/close.

## TPL-A8-0001 — Content Uniformity by HPLC (new version)

- Created **v2** via new-version (code stays `TPL-A8-0001`; the system copies
  the code — a new version cannot carry a different code).
- **Removed fields** from the `additional_info` block: STD Potency
  (`std_potency`), Name of Base (`base_name`), M.W. (Base) (`mw_base`),
  Name of Salt (`salt_name`), M.W. (Salt) (`mw_salt`).
- **Kept K** (`k_value`); the Acceptance Value formula is unchanged.
- Stripped the now-removed potency/MW terms from the `conc_ppm` and `pct_lc`
  expressions (mathematically neutral — the removed inputs defaulted to
  100 / 1 / 1).
- **Renamed** v2 to **"Content Uniformity by HPLC-v2"**.
- **Submitted + approved** (e-signed) → v2 is **Active**; v1 auto-deactivated
  and back-linked (`superseded_by_id → v2`). v2 is now the selectable version
  in the TRF test selection for test 14 (`TST-CU`).

## Destructive — TRF/AR deletion (raw DB)

- Deleted **`TRF-20261012-0002`** (and its AR `AR-20261012-0002`) by direct
  SQL on `lims.db`, at user request. The app has **no TRF-delete path**
  (only test-line removal / sample soft-delete), so this bypassed the
  application, its audit trail, and GxP status rules (the TRF was
  `InProgress`).
  - Removed in one FK-safe transaction: `test_worksheets` (id 21) →
    `trf_test_lines` (id 34) → `test_request_forms` (id 23).
  - `AR-20261012-0002` was **not** a separate sample row — it was only the
    TRF's `ar_number` field, so it went with the TRF.
  - Backup before delete: `backend-v2/lims.db.bak-predelete-20261012-153955`.
  - Verified gone via API (22 TRFs remain).

## Frontend — TRF list: show test names per line

- `/trf` list "Test Lines" column now lists each line's **test name** (`Test
  Name (CODE)`, stacked) with a small `N test(s)` count, instead of just the
  bare count — so tests are identifiable at a glance. Empty TRFs show `-`.
  Frontend-only (`TRFListPage.tsx`); template names not shown (not in the TRF
  list payload — would need a backend join). Build passes.

## TPL-A6A-0005 — Dissolution-Leuprolide-microsphere (new version v2)

- **%RSD "0.1" report was not a bug.** The Standard-area `rsd_std`
  (`sd/mean*100`) correctly computed 0.0650 %; user expected the rounded
  figure. Confirmed math against the 5 areas (Mean 1108203.6, SD 719.9266,
  %RSD 0.0650 → 0.1 at 1 dp). Root cause was display precision, not the
  formula.
- Created Draft **v2**, reworked the **Cumulative % Release** section, then
  **submitted + approved** → v2 **Active**, v1 **Inactive** / superseded
  (`superseded_by_id → 41`); v2 selectable in TRF for test 37. Changes
  (formulas unchanged — honoured "without changing properties & formulas"):
  - Timepoint rows capped at **10** (editable, add-row kept).
  - **Mean / Min / Max / %RSD** rounded to **1 dp** (verified 14.8 / 12.7 /
    16.6 / 13.2 against the sheet's 1 Hr block).
  - **Unit-1..6 columns hidden** (`hidden: true`) — still computed; footer
    stats and `resultRef = timepoints_release.mean` intact.
- **Model confirmed correct against the source Excel**
  (`_dumps/Dissolution sheet_Leuprolide_Microsphere.txt`, sheet ZEG0572A):
  timepoints are rows, 6 units are columns, Cumulative %Release
  `C = J(assay) + L(carry-over of prior timepoints' K)`, each timepoint has
  its own Mean/Min/Max/RSD. The user's "samples-as-rows" drawing is the Excel
  *visual* of one timepoint block (B40:C45 = 1 Hr), NOT a different calc —
  cumulation requires timepoints-as-rows, so the stored model stays as v2.
  Existing seed module `scripts/template_definitions/a6a_leuprolide_microsphere.py`
  + parity test already encode this math.
- **P3 (frontend display) delegated** — workflow `wf_4cc76af74dd69866`
  (`a6a5-cumulative-vertical-render`): render each timepoint's 6 units
  vertically (Sample Area → Cumulative %Release) with per-timepoint stats, in
  the worksheet UI only, gated to TPL-A6A-0005 + `timepoints_release`. No
  definition/engine/formula change. (In progress at time of log.)
- Backup: `backend-v2/lims.db.bak-leuprolide-20261024-220422` (from earlier
  A6A-0005 build) + the pre-delete backup noted above.

---

## Commits (local, unpushed at time of log)

- `f0e7f29` — TPL-A12-0003 editable Acceptance Ranges strip
- `e780345` — NEW TPL-A6B-0002 Octreotide pH-10 dissolution template
- `28184ca` — worklogs for 2026-10-23 and 2026-10-24
- `b2e2e61` — feat(test-templates): worksheet column + read-only preview, TRF
  add-line by template (5 files, +402/-15), branch `MadhuriWorktree`

## Pending / queued

- Restart the app to view TPL-A6B-0002 and the A12-0003 ranges strip.
- A6A-0005 **P3 vertical render** workflow (`wf_4cc76af74dd69866`) — review
  outcome, then confirm visually at `/trf/39`.
- Uncommitted frontend changes in the working tree: TRF list test-names column
  (`TRFListPage.tsx`) and the A6A-0005 P3 render (once the workflow lands) —
  not yet committed.
- TPL-A8-0001 v2 and TPL-A6A-0005 v2 template edits live only in `lims.db`
  (gitignored); not captured as declarative seed modules in source control
  (A6A-0005 has a seed module, but the v2 10-row/1dp/hidden-unit tweaks were
  applied via the DB).
- TPL-A2-0004 Drug-to-Lipid section transpose (compounds-as-rows + merged
  summary columns) — still queued from earlier.
- Octreotide with-replacement M-chain — follow-up only if the lab needs it.
- Unpushed: `f0e7f29`, `e780345`, `28184ca`, `b2e2e61`.
- TPL-A8-0001 v2 edit lives only in `lims.db` (gitignored); not captured as a
  declarative seed module in source control.
- TRF/AR deletion was raw DB (no audit entry); restore from
  `lims.db.bak-predelete-20261012-153955` if it needs to be reversed.
