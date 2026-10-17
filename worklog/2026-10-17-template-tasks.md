# Worklog — 17 October 2026

Template / worksheet changes. Template & calculation edits are in
`backend-v2/lims.db` (gitignored; a timestamped `lims.db.bak-*` backup was made
before each change) and, where a declarative module exists, kept in sync with
the source under `backend-v2/scripts/template_definitions/`. Frontend changes
are in source. All source changes are committed (not pushed).

---

## TPL-A6B-0001 — Dissolution (with replacement), Doxorubicin 12-unit

(Built earlier via workflow; today's follow-up edits:)

- **Spelling + units fix**: "Unite-N" labels -> "Unit-N" across the Sample
  Area, % Content and % Release tables; removed the `µV·s` unit from the 12
  Sample Area columns.
- **Time Interval auto-fetch**: the "Time Interval (Hours)" column in both
  "% Content of Doxorubicin Hydrochloride" and "% Release of Doxorubicin
  Hydrochloride" now mirrors (read-only) from the Sample Area table
  (`mirrorFrom: sample_area.time_hr`).
- **Spec Limit column**: added a free-text "Spec Limit" column as the last
  column of "% Release of Doxorubicin Hydrochloride" (acceptance range entered
  per timepoint).
- **Graphs**: added an editable "Graph Title" text box to the chart section;
  added a SECOND chart for "% Release of Doxorubicin Hydrochloride" (sourced
  from the amount table), alongside the existing "% Content" chart. Both plot
  the 12 units + Mean (Mean default).
- **Frontend wiring** for the editable title: `WorksheetChart.tsx` now renders
  a chart title from the editable field; `WorksheetForm.tsx` renders the title
  input and passes the live title; `WorksheetChartPrintImage.tsx` +
  `PrintWorksheetPage.tsx` use the edited title in the PDF; `ChartConfig` type
  gained `titleField`.
- Kept DB row and `a6_dissolution.py` byte-for-byte in sync; all verified to
  parse + evaluate.

## TPL-A2-0004 — NEW: Bupivacaine Lipid Content & Drug-to-Lipid Ratio

- Created a brand-new template (archetype A2, Active) reproducing the two-sheet
  Bupivacaine "Lipid Assay + Drug-to-Lipid Ratio" workbook. Bound to a new Test
  Master **TST-LIPID-RATIO** ("Lipid Content & Drug-to-Lipid Ratio by HPLC").
- 4 lipid compounds (Tricaprylin, DPPG, Cholesterol, DEPC): standard Conc
  (ppm), 6-injection replicate stats, pooled bracketing stats, multi-batch
  per-compound % Assay with two-injection averaging; plus the Drug-to-Lipid
  sheet (mg/mL per lipid, Sum of Lipid, mg/mL Bupivacaine, Drug/Lipid Ratio).
- New declarative module `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
  (registered in `__init__.py`); DB row equals the module byte-for-byte.
- Built and verified via workflow (planner -> coder -> reviewer -> finalize),
  **APPROVED**. All 18 gold values reproduce exactly: Std Conc
  (118.92 / 54.0343 / 285.1 / 489.2544), replicate means, pooled bracketing
  (Tricaprylin mean 8699733.9, %RSD 0.2383), batch EP20_117-299-B %Assay
  (99.979 / 86.200 / 101.772 / 100.390), Drug/Lipid Ratio 0.841429.
- Scope confirmed: templates 34->35, tests 31->32 (exactly +1 each); nothing
  else changed. DB backed up (`lims.db.bak-lipid-20261017-222441`).
- Note: a separate `TPL-A12-0002 "Drug-to-Lipid Ratio"` already existed; this
  new full two-sheet template did not collide with or alter it.

## Git

Commits on branch `MadhuriWorktree` (NOT pushed yet):
- `dbd273f` — feat(TPL-A2-0004): Bupivacaine Lipid Content and Drug-to-Lipid
  Ratio template (module + __init__ + evidence).
- `bae82b2` — docs(TPL-A2-0004): review evidence.
- `6fc9dcf` — feat(TPL-A6B-0001): time-interval mirror, Spec Limit column, dual
  % Content/% Release charts with editable titles; chart title rendering in UI
  and print (a6_dissolution.py + 5 frontend files).

Branch is 3 commits ahead of `origin/MadhuriWorktree`.

## Open / deferred

- Not pushed to origin yet (awaiting go-ahead).
- Template & calculation edits live only in `lims.db` (gitignored) except where
  a declarative seed module exists; TPL-A6B-0001's structure IS captured in
  `a6_dissolution.py`, TPL-A2-0004 in `a2_bupivacaine_lipid_ratio.py`.
- `.agents/` workflow artifacts (plan/review/verification docs, JSON dumps)
  remain untracked and uncommitted.
- 5 pre-existing pytest failures (A6B dissolution + worksheet-service state)
  are unrelated to today's work (reproduce with changes stashed).
