# Review — TPL-A6D-0002 per-row linearity seeding + eleven Additional-Info defaults

Verdict: **APPROVED** (0 blocking findings)

First review pass. Reviewed against the approved `design.md` / `plan.md`, the coder's
`verification.md`, the actual source diff, the new test, the author script, and an
independent read of the live `lims.db`.

## What I checked

### Source changes (read the real diff, not just the note)
- `template_schema.py` — `RowSpec` gains `seed: tuple[dict[str, Any], ...] = ()`;
  `RowSpec.parse` reads `raw.get("seed") or []`, requires a list of dicts, requires
  `len(seed) <= max_`, stores `tuple(dict(r) …)`. `GroupDef.parse` validates every
  seed-row key is a real field (`set(seed_row) - seen`) and preserves `seed` through
  the singleton row-spec rebuild. The `()` default keeps every existing template
  parsing unchanged. Matches the design exactly.
- `worksheet_service.py` — `create_worksheet` now passes
  `group_values=self._seed_group_rows(definition)` instead of `{}`; new static
  `_seed_group_rows` emits one entry per group whose rows spec declares a seed and
  omits groups without one (preserving today's empty-rows behaviour). Single
  functional seam, matches the design.
- `WorksheetForm.tsx` — no change, and no change is required. Verified the render
  path firsthand (see below).

### Render path — the user's core complaint ("not viewing on the UI")
Read `frontend-react/.../WorksheetForm.tsx` directly:
- `rowCount` (line 76): `if (stored && stored.length) return stored.length;` — stored
  `group_values` rows win over `rows.default`. Nine stored rows → nine rendered rows.
- `seedValues` (lines 106–114): each cell = `source[field.key]` (stored) when present,
  else `field.default ?? null`. The seeded `calibration_curve`/`concentration_pct`
  cells render filled; the six unseeded columns render blank.
- Context grid (lines 1202–1204): `current = contextValues[field.key] ?? detail.worksheet.context_values?.[field.key]`,
  printed through the same `<span>`/editable-input path as the existing left-column
  values. All eleven baked defaults land in `context_values` at creation via
  `_seed_context` (source removed → `value is None` → `cf.default` applies), so all
  eleven render identically to Total media volume / Donor area / Temperature.

Storage therefore has a real render path. Criterion satisfied.

### Live DB read-back (independent spot-check of the storage source of truth)
Read `test_templates` id=43 and id=26 directly:
- **id=43 (TPL-A6D-0002)**: status **Draft**, v1, top keys unchanged
  (`resultRef, context, groups, criteria`). Groups:
  `['calibration','curve','qc','linearity','cells','sampling_details','timepoints','flux']`
  — `linearity` sits immediately after `qc`, before `cells`.
  - linearity: label "Standard Tapinarof for Linearity", kind `sequence`, rows
    `{min:9, max:15, default:9, labelFrom:'calibration_curve'}`, 8 fields in the exact
    required order (`calibration_curve, concentration_pct, std_weight_mg,
    diluted_to_ml_1, ml_a, ml_b, ml_taken, diluted_to_ml_2`).
  - nine seed rows, exact labels + concentrations:
    `(Calibration standard-1,1) (…-2,5) (…-3,15) (…-4,30) (…-5,40) (…-6,60)
    (LQC,1) (MQC,15) (HQC,30)`; each seed row names only the two seeded columns.
  - eleven Additional-Info context defaults, each `source=None`:
    `date_of_analysis='06 April 2026'` (type text), `working_std_no='WS/25/079'`,
    `use_before_date='26-May'`, `potency=99.67` (was 100), `temperature_c=32`,
    `time_points_min='40, 80, 120, 160, 200, 240'`, `avg_weight_mg=100`,
    `batch_no='LE6001'`, `trf_number='TRF-021-26-053'`, `ar_number='AD/048/26/0121'`,
    `donor_area=1.76`. All exact. Existing left-column context fields unchanged.
- **id=26 (TPL-A6D-0001)**: status **Active**, groups unchanged
  (`['calibration','curve','qc','cells','timepoints','flux']`). Untouched.

### Safety
- Two timestamped backups present: `lims.db.bak-a6dlinearity2-20261027-122834`
  (setup) and `lims.db.bak-a6dlinearity2-20261027-144357` (fresh, pre-write).
- Only id=43's `.definition` changed; id=26 Active and unchanged.
- `git status` confirms `lims.db` is not staged/committed; source edits and the new
  test/author script are present but uncommitted, per instructions.

### Tests
- Ran the gating targeted test only (narrow spot-check): `test_a6d_linearity_seed.py`
  → **3 passed**. Covers (a) parse round-trip of the nine pairs with the six columns
  absent + blank `evaluate({}, {})` no blocking failure, (b) unknown seed key
  rejected by the schema, (c) the nine seeded rows landing in a worksheet created
  through the real `WorksheetService`. This is the per-row seed round-trip +
  appearance-in-group_values proof the task requires.
- Did not re-run the full suites. Relied on the coder's recorded evidence:
  132 passed / 2 failed on the schema+service+repo set (the 2 are pre-existing,
  unrelated, and shown failing on the clean tree with the change stashed); parity
  277 passed / 3 failed, the 3 being the accepted `TestA6BDissolutionWithReplacement`
  A6B baseline failures — no new parity failure introduced. The 277-vs-269 count
  delta is explained (unrelated seed templates added to the suite since the note);
  the 3 A6B baseline failures are unchanged.

## Acceptance-criteria gate

| Criterion | Status |
|---|---|
| Per-row seeding end to end (parse → create_worksheet → render) | PASS |
| New worksheet returns nine pre-filled linearity rows (labels + concentrations) | PASS (runtime proof + create test + render path) |
| New worksheet returns eleven Additional-Info values | PASS (seed_context + render path) |
| Linearity: 8 columns in order, rows 9/9/15, labelFrom calibration_curve, nine seeded rows | PASS |
| Additional Info: eleven exact defaults, left-column unchanged | PASS |
| Backup exists before DB write; id=26 Active & untouched; only id=43 edited; no commit | PASS |
| Targeted seed round-trip test exists & passes; no new parity failures | PASS |

## Findings
None (no blocking findings).
