# Worklog — 31 October 2026

TPL-A6D-0002 "In-Vitro Release (Franz Diffusion Cell) — with Sampling Details"
(id=43, Active). Template edits were applied to `backend-v2/lims.db` (gitignored)
with a timestamped `lims.db.bak-*` backup before each change.

## Future scope — variable number of Franz cells

**Goal:** make the template usable for runs with more (or fewer) than 6 cells,
so adding a row in "Cell Loading details" flows through every calculation.

**Today's limitation:** "Cell Loading details" (`cells`) is an add/delete-row
table, but the sections that use it have fixed columns for exactly 6 cells:

- Sampling Timepoints (`timepoints`): `area_1..6`, `conc_1..6`, `amount_1..6`,
  `carry_1..6`, `cumulative_1..6`, `per_area_1..6`, `released_pct_1..6`, and the
  across-cell mean / %RSD.
- Release Rate (`flux`): `flux_1..6`, `fit_1..6`, mean / %RSD / poorest fit.
- Sampling details (`sampling_details`): `sample_weight_mg_1..6`.

A "Cell 7" row is stored but feeds no calculation. Each cell's % Released reads
its weight by position: `cells.weight_mg[n-1]`.

**Options to evaluate:**

1. **Fixed upper limit, hidden spare columns.** Author the per-cell fields for,
   say, 12 cells, hide columns 7–12, and show them as cells are added. Cheapest;
   reuses the existing per-cell formulas. Needs: a frontend rule linking the
   number of `cells` rows to which per-cell columns show (today's add/delete
   column control is limited to TPL-A6A-0004), and blank-tolerant
   mean / %RSD / flux so unused cells don't skew results.
2. **Cells as rows (fully dynamic).** Restructure so each cell is a row and
   timepoints are columns or a nested table. No upper limit, but it is a large
   change to the template, the engine (per-cell regression over a nested
   series) and the worksheet layout.

**Decide before starting:** maximum cell count needed in practice; whether
"Sampling details" sample weights should merge into "Cell Loading details"
(they hold the same per-cell weights today); and which reports or prints must
change.

## Done today (summary)

- Calibration: "Standard Tapinarof for Linearity" (12 columns, rows deletable,
  min 2), calibration curve graph with trendline and equation (title editable
  via Edit/Save), Slope / Intercept / Correlation box (fit over standards only).
- "Calibration curve for LQC-MQC-HQC" input table, and "% Recovery" table
  (18 injections, one per row); QC recovery limits 85–115 % read that table.
- "Cell Loading" replaced by "Cell Loading details" (Cell no, Weight (mg),
  add/edit/delete rows); worksheets 55 and 56 converted.
- Commits on `MadhuriWorktree` (not pushed): `5305536`, `1306446`.
  The graph-title Edit/Save fix in `WorksheetForm.tsx` is not yet committed.
