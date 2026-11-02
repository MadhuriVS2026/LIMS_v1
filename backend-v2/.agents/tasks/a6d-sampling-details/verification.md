# Verification — TPL-A6D-0002 "Sampling details" sub-section

Implementation of the APPROVED design/plan under `.agents/tasks/a6d-sampling-details/`.
All work recorded here was run from `d:\RD-instance\GIT\backend-v2`. `lims.db` is the
source of truth and was read directly; it is gitignored and was NOT committed.

New template produced:
- **Code:** `TPL-A6D-0002`
- **Name:** `In-Vitro Release (Franz Diffusion Cell) — with Sampling Details`
- **Row:** id=43, version=1, status=Draft, archetype=A6d, result_unit=µg/cm²/√h,
  test_id=25 (same `TST-IVRT` as TPL-A6D-0001).

## 1. Mandatory backup (NFR1 / AC9) — done before any DB write

```
Copy-Item lims.db lims.db.bak-a6dsampling-<ts>
```
Created `lims.db.bak-a6dsampling-20261026-172816`. Byte size equals live `lims.db`
(1 486 848 == 1 486 848), confirmed a complete copy. Created as the first action,
before the author script ran.

## 2. Live-definition baseline (source of truth)

Read directly from `lims.db` (not just the seed module):
- Exactly one `TPL-A6D-%` row before the change: id=26, code=TPL-A6D-0001,
  version=1, status=Active, archetype=A6d, result_unit=µg/cm²/√h, test_id=25.
- Group order: `calibration, curve, qc, cells, timepoints, flux`; no
  `sampling_details` group present.
- Per-cell counts: `cells.applied_mg`=6, `timepoints.area`=6, `flux.flux`=6.
- `TPL-A6D-0002` was the next free code.

## 3. Duplication + edit (FR1–FR6)

Author script `backend-v2/_apply_a6d_sampling_details.py` (pattern:
`_apply_cu30_kedit.py`): reads the LIVE `TPL-A6D-0001` definition, deep-copies it,
**regenerates every per-cell group (`cells`, `timepoints` area + full calculated
chain + the `_series(...)` aggregates, `flux` flux/fit + the `_series(...)`
aggregates) AND the new `sampling_details` sub-section from one shared
`CELL_RANGE = range(1, 7)` constant** (the add-column / cross-section mirror
contract), then inserts the `singleton` `sampling_details` group (label "Sampling
details") immediately before `timepoints`, holding one blank `sample_weight_mg_{n}`
input per cell. No `default` key is set on any field, so they render blank. The
example figures (257.0 / 229.4 / 227.0 / 218.2 / 254.3 / 257.2) appear nowhere in
the script or the stored definition. Idempotent: aborts without writing if
`TPL-A6D-0002` already exists.

The per-cell generators (`build_cells_fields`, `build_timepoints_fields`,
`build_flux_fields`, `_series`) mirror the seed module
`scripts/template_definitions/a6d_franz_ivrt.py` exactly (same keys, labels,
units, expressions, rounding, field order). Because the script regenerates the
per-cell groups rather than copying them verbatim, the single `CELL_RANGE` now
genuinely drives the cell count in all four groups — the review B1 fix.

### Duplicate == source + one group (guard against silent drift)

Before writing, the script asserts that stripping the new `sampling_details`
group from the regenerated duplicate yields a definition byte-equal to the live
`TPL-A6D-0001` (`json.dumps(..., sort_keys=True)`). This proves the per-cell
regeneration reproduces the source exactly at the default 6 cells, so the ONLY
difference between the duplicate and its source is the inserted sub-section:
```
byte-equal check OK: duplicate == source + sampling_details group only
```

### Two-pass validation (AC6) — service's exact gate

`python _apply_a6d_sampling_details.py --validate-only`
```
validation OK: parse + evaluate({}, {}) succeeded, no blocking failure
--validate-only: no DB write performed.
```
`TemplateDefinition.parse(definition)` then `WorksheetEvaluator(parsed).evaluate({}, {})`
both succeed; `has_blocking_failure is False`.

### Write + byte-equality re-read (FR6)

`python _apply_a6d_sampling_details.py`
```
byte-equal check OK: duplicate == source + sampling_details group only
validation OK: parse + evaluate({}, {}) succeeded, no blocking failure
per-cell parity OK across all groups: {'sampling_details.sample_weight_mg': 6, 'cells.applied_mg': 6, 'timepoints.area': 6, 'flux.flux': 6}
wrote TPL-A6D-0002 id=43 status=Draft; re-read byte-equal OK
```
`json.dumps(new.definition, sort_keys=True)` on re-read equals the written
definition.

Note on this iteration: the previously stored (flawed-mechanism) `TPL-A6D-0002`
row was deleted and re-written by the corrected script. The stored definition is
identical in content (6 cells everywhere, blank Sample-weight inputs); what
changed is the author script now truly mirrors on a `CELL_RANGE` bump.

## 4. Post-condition checks (AC1–AC5, AC7, AC9)

`python _tmp_verify_a6d.py` (read-only; temporary, deleted after):
```
PASS AC1: TPL-A6D-0002 id=43 version=1 status=Draft archetype=A6d unit ok test_id=25==25
PASS AC2: id=26 still Active; definition byte-equal to lims.db.bak-a6dsampling-20261026-172816
PASS AC3: sampling_details (singleton, 'Sampling details') at index 4, immediately before timepoints at 5
PASS AC4: 6 sample_weight_mg_1..6 inputs, type=number unit=mg, no default key
PASS AC5: none of the example figures present in the stored definition
PASS AC7: per-cell parity, all four groups have 6 cells {'sampling_details.sample_weight_mg': 6, 'cells.applied_mg': 6, 'timepoints.area': 6, 'flux.flux': 6}
PASS AC9: mandatory backup present: lims.db.bak-a6dsampling-20261026-172816
PASS: exactly 2 TPL-A6D-% rows
ALL POST-CONDITION CHECKS PASSED
```
- AC2 explicitly asserts `TPL-A6D-0001` (id=26) is still Active and its definition
  bytes equal those in the backup — the source template is byte-unchanged (NFR3).

## 5. Add-column / cross-section mirror demonstration (AC8) — via the DELIVERED author script

This now exercises the **delivered artifact** itself (`_apply_a6d_sampling_details.py
--mirror-demo N`), not a parallel throwaway script. The `--mirror-demo` path calls
the exact same `build_duplicate_definition(source, range(1, N+1))` used by the real
write, so it proves the single `CELL_RANGE` genuinely mirrors across all four
per-cell groups (the review B1 fix). NO DB write is performed.

`python _apply_a6d_sampling_details.py --mirror-demo 7`
```
validation OK: parse + evaluate({}, {}) succeeded, no blocking failure
MIRROR DEMO range(1,8): all per-cell groups mirrored, counts={'sampling_details.sample_weight_mg': 7, 'cells.applied_mg': 7, 'timepoints.area': 7, 'flux.flux': 7}
  mean_flux series includes flux_7: mean([flux_1, flux_2, flux_3, flux_4, flux_5, flux_6, flux_7])
  parse + evaluate({}, {}) OK; NO DB write performed.
```

`python _apply_a6d_sampling_details.py --mirror-demo 8`
```
validation OK: parse + evaluate({}, {}) succeeded, no blocking failure
MIRROR DEMO range(1,9): all per-cell groups mirrored, counts={'sampling_details.sample_weight_mg': 8, 'cells.applied_mg': 8, 'timepoints.area': 8, 'flux.flux': 8}
  mean_flux series includes flux_8: mean([flux_1, flux_2, flux_3, flux_4, flux_5, flux_6, flux_7, flux_8])
  parse + evaluate({}, {}) OK; NO DB write performed.
```

At range(1,8) every per-cell group moves in lock-step to 7 cells —
`sample_weight_mg_7` AND `applied_mg_7`, `area_7` (+ full calc chain
`conc_7`…`released_pct_7`), `flux_7`/`fit_7` — and the cross-cell `_series(...)`
aggregates (e.g. `mean_flux`) include the new index. At range(1,9) they all move to
8. The 7-/8-cell definitions parse and dry-run evaluate with no blocking failure.
No row was written to the DB (still exactly 2 `TPL-A6D-%` rows, confirmed in
section 4). This is the actual add-column/mirror contract delivered by the script
FR5/AC8 name — not a property demonstrated on a separate script.

### Why this closes review finding B1

B1 observed that the earlier script defined `CELL_RANGE` but used it only for
`sampling_details`, copying `cells`/`timepoints`/`flux` verbatim, so a range bump
would desync the sections, and that the AC8 evidence exercised a throwaway script
using the seed module rather than the delivered one. The corrected script now
regenerates all four per-cell groups and the `_series(...)` aggregates from the
single `CELL_RANGE` (see section 3), and AC8 is re-demonstrated by running the
**author script itself** at ranges 1..8 and 1..9 above. The pre-write byte-equal
assert (section 3) guarantees the regeneration reproduces the live source exactly
at the default 6 cells, so TPL-A6D-0001 and the duplicate's existing sections are
unchanged.

## 6. Template parity suite (AC10)

`python -m pytest tests/calculation/test_seeded_template_parity.py -q`
```
3 failed, 269 passed in 1.47s
FAILED ...::TestA6BDissolutionWithReplacement::test_unit1_release_carryover
FAILED ...::TestA6BDissolutionWithReplacement::test_per_timepoint_summary
FAILED ...::TestA6BDissolutionWithReplacement::test_amount_remaining
```
This equals the recorded pre-existing baseline exactly: `3 failed, 269 passed`,
with all three failures under `TestA6BDissolutionWithReplacement` (A6B — a
dissolution-with-replacement template unrelated to this A6D task). No NEW failures,
and the passed count is unchanged. The catalogue-wide invariants and every A6D /
A6D-adjacent test pass. These three A6B failures pre-exist this change (the
duplicate lives only in `lims.db` and is not added to `SEED_TEMPLATES`, so the
seed-based parity suite is structurally unaffected by it).

## 7. App / rendered-worksheet verification (AC: catalogue + render) — fallback used

The full app (`start-lims.bat`, backend 127.0.0.1:8443 + frontend localhost:5174)
was NOT launched in this environment. The HTTPS endpoint was probed and is not
running; the `GET /api/v1/test-templates` route is auth-gated (Admin/Analyst/
Supervisor/QA) and cannot be exercised non-interactively without a login/e-sign
flow. Per the plan's documented fallback, verification was done at the
definition/DB level instead:

- Catalogue presence: `TPL-A6D-0002` "…— with Sampling Details" exists as a Draft
  row (AC1). A catalogue listing that includes Drafts will show it.
- Rendered-worksheet content: the stored `sampling_details` group is a `singleton`
  with six `sample_weight_mg_{n}` inputs, each `kind=input`, `type=number`,
  `unit=mg`, and **no `default`** — so the generic singleton renderer draws six
  blank Sample-weight boxes (Cell 1…Cell 6), none pre-filled (AC4/AC5). The
  existing `cells`/`timepoints`/`flux` groups are untouched at 6 cells and the
  math is unchanged (definition is a deep copy with exactly one group inserted;
  the empty-input dry-run evaluate passes).
- Add-column + mirror: as the design documents, the live hide/restore "Add column"
  UI control is gated to `TPL-A6A-0004` only (`WorksheetForm.tsx`), so A6D's
  add-column + mirror is delivered at AUTHORING time via the single `CELL_RANGE`
  constant and is demonstrated by section 5 above, not by a live button for A6D.

## 8. Cleanup

Temporary scripts used during verification (`_tmp_dump_a6d.py`, `_tmp_del_a6d2.py`,
`_tmp_verify_a6d.py`) were deleted after use. The add-column / mirror demonstration
no longer uses a throwaway script — it runs through the delivered author script's
`--mirror-demo` flag. The author script `_apply_a6d_sampling_details.py` is left on
disk (matching the `_apply_cu30_kedit.py` precedent) and is uncommitted. `lims.db`
and the `lims.db.bak-a6dsampling-*` backup are gitignored and were not committed.
Nothing was committed.
