# Verification — TPL-A6D-0002 per-row linearity seeding + eleven Additional-Info defaults

First iteration (no `review.json` present). Implemented from the approved
`design.md` / `plan.md`. All commands run from `backend-v2` unless noted.

## What changed

Source code (committable, NOT committed per instructions):

- `src/domain/services/calculation/template_schema.py` — added the additive
  `rows.seed` capability. `RowSpec` gains `seed: tuple[dict[str, Any], ...] = ()`;
  `RowSpec.parse` reads `raw.get("seed")`, requires a list of dict objects with
  `len(seed) <= max`, stores `tuple(dict(r) for r in raw_seed)`. `GroupDef.parse`
  validates every seed-row key is a real field of the group (and preserves `seed`
  through the singleton row-spec rebuild). Absent `seed` → `()`, so every existing
  template parses unchanged.
- `src/application/services/worksheet_service.py` — `create_worksheet` now passes
  `group_values=self._seed_group_rows(definition)` instead of `{}`. New static
  `_seed_group_rows` emits one entry per group whose rows spec declares a seed
  (`{group.key: [dict(r) for r in group.rows.seed]}`); groups without a seed are
  omitted, preserving today's empty-rows behaviour.
- `frontend-react/.../WorksheetForm.tsx` — **no change** (verified render path, see
  below).

Test (committable, NOT committed):

- `tests/calculation/test_a6d_linearity_seed.py` — three tests: seed round-trips
  through parse (nine label/concentration pairs, six columns absent, blank
  `evaluate({}, {})` has no blocking failure); an unknown seed field key is
  rejected by the schema; the nine seeded rows land in a worksheet created through
  the real `WorksheetService`.

Author script (kept, NOT committed):

- `_apply_a6d_linearity.py` — reads live TPL-A6D-0002 (id=43), deep-copies, inserts
  the `linearity` sequence group after `qc`/before `cells`, edits the eleven
  Additional-Info context defaults (drops competing sources), validates via
  `TemplateDefinition.parse` + `WorksheetEvaluator.evaluate({}, {})`, writes id=43's
  `.definition`, re-reads byte-equal. Supports `--validate-only` (no DB write).

Data (gitignored, NOT committed): `lims.db` row id=43 `.definition` only.

## Backup taken before any DB write

```
lims.db.bak-a6dlinearity2-20261027-144357   (fresh, this run; 1.6 MB)
lims.db.bak-a6dlinearity2-20261027-122834   (setup step's earlier backup)
```

## Commands run and results

### 1. Schema + evaluator + new test + service + repo tests
```
python -m pytest tests/calculation/test_template_entities.py \
  tests/calculation/test_evaluator.py \
  tests/calculation/test_a6d_linearity_seed.py \
  tests/calculation/test_worksheet_service.py \
  tests/calculation/test_template_repository.py -q
```
Result: **132 passed, 2 failed**. The two failures
(`test_a_different_analyst_cannot_enter_results_on_an_assigned_trf`,
`test_a_qa_correction_reopens_and_republishes_the_result`) are **pre-existing and
unrelated** — confirmed by re-running them with my `worksheet_service.py` change
`git stash`ed: they fail identically on the clean tree (worksheet already
`Confirmed`, an A1 stand-in template concern). My three new tests all pass.

### 2. Parity regression
```
python -m pytest tests/calculation/test_seeded_template_parity.py -q
```
Result: **277 passed, 3 failed** — all three failures are the accepted baseline
`TestA6BDissolutionWithReplacement` A6B failures (`test_unit1_release_carryover`,
`test_per_timepoint_summary`, `test_amount_remaining`). No new failure introduced
by `rows.seed`. (Pass count is 277 rather than the plan's noted 269 because other
unrelated seed templates were added to the suite since the baseline note; the three
A6B failures are the baseline that matters and are unchanged.)

### 3. Author-script dry run (no DB write)
```
python _apply_a6d_linearity.py --validate-only
```
Result: `validation OK: parse + evaluate({}, {}) no blocking failure; linearity
seeded, 11 Additional-Info defaults, no example figures`.

### 4. Fresh backup + real DB write
```
Copy-Item lims.db lims.db.bak-a6dlinearity2-20261027-144357
python _apply_a6d_linearity.py
```
Result: `wrote/updated id=43 (TPL-A6D-0002) status=Draft … re-read byte-equal OK`.

### 5. Independent DB read-back
- id=43: status Draft, ver 1, arch A6d, test_id 25, unit `µg/cm²/√h`, name
  unchanged.
- groups: `['calibration','curve','qc','linearity','cells','sampling_details','timepoints','flux']`
  — `linearity` sits immediately after `qc` and before `cells`.
- linearity rows spec: `{min:9, max:15, default:9, labelFrom:'calibration_curve'}`;
  nine seed rows: `(Calibration standard-1,1) (…-2,5) (…-3,15) (…-4,30) (…-5,40)
  (…-6,60) (LQC,1) (MQC,15) (HQC,30)`.
- eleven Additional-Info context defaults, each with `source=None`:
  `date_of_analysis='06 April 2026'`, `working_std_no='WS/25/079'`,
  `use_before_date='26-May'`, `potency=99.67`, `temperature_c=32`,
  `time_points_min='40, 80, 120, 160, 200, 240'`, `avg_weight_mg=100`,
  `batch_no='LE6001'`, `trf_number='TRF-021-26-053'`, `ar_number='AD/048/26/0121'`,
  `donor_area=1.76`.
- id=26 (TPL-A6D-0001): **Active, unchanged**, groups still
  `['calibration','curve','qc','cells','timepoints','flux']`.

### 6. Runtime end-to-end proof (disposable DB copy; script & copy deleted)
Against a throwaway `lims.runtimeproof.tmp.db` (never the shipped file), with the
copy's TPL-A6D-0002 promoted to Active, a worksheet was created for a `TST-IVRT`
line through the real `WorksheetService.create_worksheet`:
- `group_values["linearity"]` returned the **nine** seeded rows with exactly the
  labels/concentrations above; each row contains only `calibration_curve` and
  `concentration_pct` (the six input columns open blank).
- `context_values` returned **all eleven** Additional-Info values pre-filled with
  the exact baked defaults.
Output ended `RUNTIME PROOF OK: nine seeded linearity rows + eleven Additional-Info
values present`. The disposable DB copy and the proof script were then deleted.

### 7. Frontend render path (verify-only) + build
No `WorksheetForm.tsx` change. Confirmed by reading the current file:
- `seedValues` reads `detail.worksheet.group_values?.[group.key]` as `stored`;
  `rowCount` returns `stored.length` when stored rows exist → nine rows render, the
  two seeded cells filled (stored value wins over `field.default`), six columns
  blank.
- Context grid (`contextFields.map`, `contextFields = definition.context`) renders
  each field's `current = contextValues[field.key] ?? detail.worksheet.context_values?.[field.key]`
  through the same `<span>`/`InputText`/`InputNumber` as the existing left-column
  values; all eleven are `overridable:true` so they render pre-filled and editable,
  identical to Total media volume / Donor area / Temperature.
```
npm run build   (from frontend-react)
```
Result: `✓ built in 5.15s` (tsc + vite build clean).

## Cleanup
- Deleted throwaway `_runtime_proof_a6d_linearity.py` and
  `lims.runtimeproof.tmp.db`.
- Kept `_apply_a6d_linearity.py` and `tests/calculation/test_a6d_linearity_seed.py`.

## Not committed (per instructions)
Source edits (`template_schema.py`, `worksheet_service.py`), the new test, the
author script, and `lims.db` were **not** committed — awaiting explicit user
request.
```
