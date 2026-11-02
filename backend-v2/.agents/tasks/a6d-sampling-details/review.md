# Review — TPL-A6D-0002 "Sampling details" sub-section

Verdict: **APPROVED** — no blocking findings.

Scope reviewed: the duplication of TPL-A6D-0001 into a new Draft TPL-A6D-0002 and
the added per-cell "Sampling details" sub-section, against the approved design
(`design.md`), plan (`plan.md`), the original user request, and the coder's
recorded evidence (`verification.md`). I read the delivered author script
(`_apply_a6d_sampling_details.py`), the seed module it mirrors
(`scripts/template_definitions/a6d_franz_ivrt.py`), the schema (`template_schema.py`),
and inspected the live `lims.db` directly. I did not re-run the parity suite; I ran
narrow spot-checks only where a specific claim warranted direct confirmation.

## Evidence against each critical requirement

### 1. Duplicate via the system's own validated mechanism; original unchanged — PASS
- The author script reads the LIVE TPL-A6D-0001 definition from `lims.db`,
  deep-copies it, and validates through the service's exact two-pass gate
  (`TemplateDefinition.parse` then `WorksheetEvaluator(parsed).evaluate({}, {})`)
  before writing — the same gate `TestTemplateService.validate_definition` applies.
  This matches the `_apply_cu30_kedit.py` precedent the design cites and is not a
  hand-hacked row.
- Stored row (read directly from `lims.db`): `id=43, code=TPL-A6D-0002, version=1,
  status=Draft, archetype=A6d, result_unit=µg/cm²/√h, test_id=25` (same `TST-IVRT`
  as the source). Code/name are sensible and distinct (FR1).
- Original `TPL-A6D-0001` (id=26) confirmed unchanged: still `status=Active`, group
  order `calibration, curve, qc, cells, timepoints, flux`, no `sampling_details`
  group, per-cell counts 6/6/6. verification.md AC2 additionally asserts its
  definition bytes equal the pre-write backup (NFR3).

### 2. "Sampling details" sub-section, blank inputs, no baked-in examples — PASS
- Stored `TPL-A6D-0002` groups: `calibration, curve, qc, cells, sampling_details,
  timepoints, flux` — the new `sampling_details` group is a `singleton` labelled
  "Sampling details" positioned immediately before `timepoints` (design FR3/AC3).
- It holds exactly six fields `sample_weight_mg_1..6`, each `kind=input`,
  `type=number`, `unit=mg`, label "Cell N Sample Weight", and **no `default` key**
  — confirmed field-by-field from the stored JSON. Per `FieldDef.parse` in
  `template_schema.py`, absent `default` → `None`, so every Sample-weight cell
  renders blank (AC4).
- The example figures 257.0 / 229.4 / 227.0 / 218.2 / 254.3 / 257.2 appear nowhere
  in the stored definition (substring scan of the stored JSON) (AC5).

### 3. Per-cell keying contract and cross-section mirror — PASS
- The script regenerates the per-cell field lists of `cells`, `timepoints`
  (area + full calculated chain + the `_series(...)` aggregates) and `flux`
  (flux/fit + `_series(...)` aggregates) AND the new `sampling_details` group from a
  SINGLE `CELL_RANGE` constant, matching the seed module's generators exactly. This
  is the design's stated keying contract (`*_{n}` fields over one shared range), not
  a guess.
- Spot-check I ran live: `python _apply_a6d_sampling_details.py --mirror-demo 7`
  produced counts `{sampling_details.sample_weight_mg:7, cells.applied_mg:7,
  timepoints.area:7, flux.flux:7}` and `mean_flux` widened to include `flux_7`. So a
  one-line range bump adds the matching column across all four per-cell sections in
  lock-step and the cross-cell aggregates follow (FR4/FR5/AC7/AC8). The earlier B1
  concern (range used only for the new group) is genuinely resolved: all four groups
  are driven by the one range.
- Before writing at the default range, the script asserts that stripping
  `sampling_details` from the regenerated duplicate is byte-equal to the live source
  (`json.dumps(..., sort_keys=True)`), guaranteeing the regeneration reproduces the
  source's existing sections exactly at 6 cells — the only delta is the inserted
  sub-section.
- Caveat (already documented in design NFR4/Out-of-scope, not a blocker): the live
  frontend hide/restore "Add column" control is gated to `TPL-A6A-0004` only, so for
  A6D "add column" is an authoring-time action via `CELL_RANGE`, not a live button.
  The user's request is satisfied by the keying contract per the approved design.

### 4. Parse/evaluate and parity suite — PASS
- Spot-check I ran live: the STORED `TPL-A6D-0002` definition read back from
  `lims.db` passes `TemplateDefinition.parse` and `WorksheetEvaluator.evaluate({}, {})`
  with `has_blocking_failure = False` (AC6) — i.e. the duplicate parses and runs
  empty.
- verification.md records `pytest tests/calculation/test_seeded_template_parity.py`
  = `3 failed, 269 passed`, with the three failures all under
  `TestA6BDissolutionWithReplacement` (A6B, unrelated to this A6D task). The plan
  records this exact 3-failed/269-passed figure as the pre-existing baseline, and the
  duplicate lives only in `lims.db` (not added to `SEED_TEMPLATES`), so the
  seed-based suite is structurally unaffected. No new failures. I did not re-run the
  suite per instructions.

### 5. Mandatory backup and no DB commit — PASS
- `lims.db.bak-a6dsampling-20261026-172816` exists in `backend-v2` (NFR1/AC9);
  verification.md records it was created before the write, with matching byte size.
- `git check-ignore lims.db` confirms `lims.db` is gitignored; `git status` shows no
  staged `lims.db` and no backup staged. Nothing from this task is committed.

## Notes (non-blocking, no action required)
- `git status` shows `scripts/template_definitions/__init__.py` modified plus
  untracked `a9_sodium_metabisulfite.py` / `update_a9smbs_definition.py`. These
  register an unrelated A9 template and are pre-existing drift from other work, not
  part of this A6D change — out of scope.
- The author script `_apply_a6d_sampling_details.py` is left on disk uncommitted,
  matching the `_apply_cu30_kedit.py` precedent. My spot-check's temporary files were
  removed.

## Conclusion
All critical requirements are met and independently verified against the live
`lims.db` and the delivered script. The original template is untouched, the new
Draft carries a correctly-keyed, blank, mirroring Sample-weight sub-section, the
definition parses and runs empty, and the mandatory backup exists with no DB commit.
No blocking findings.
