# Rebuild TPL-A6B-0001 as a 12-unit Doxorubicin with-replacement dissolution template

The stored `definition` JSON of the existing `TPL-A6B-0001` row was replaced in place to reproduce the Doxorubicin with-replacement whole-vial 12-unit QC-release sheet. The rebuild recasts the template into 14 groups: standard prep with a 100/5/50/5/10 dilution chain, 5-replicate and up-to-24 bracketing standard tables, an STD-1/STD-2 co-relation block, a system-suitability singleton, a 7-volume test-prep singleton, units-as-columns gravimetric weights, a cumulative with-replacement `release` sequence group carrying the sheet's carry-over term, an `amount` (%Assay − %release) table, and a release-vs-time chart. The source module (`scripts/template_definitions/a6_dissolution.py`) was updated and then written into `lims.db` via a new `scripts/update_a6b_definition.py` sync script; the stored row now equals the module dict exactly. The author's evaluator-based gate records all 21 sheet gold values reproducing to the sheet's rounding.

Watch for: nothing blocking. The rounding wrappers the brief calls for (Std Conc ROUND 3, replicate/pooled %RSD TRUNC 5, pooled mean TRUNC 1) are present as structured `rounding` attributes rather than inline in the formula strings — confirmed by reading the stored field objects (confirmed). Min/Max are computed over all 12 visible unit columns rather than the sheet's narrower `B:G` span; for the pinned 0.5hr row these coincide, so the gate does not exercise the general case (possible, author-documented).

**Verdict**: APPROVED

## High-level view

The change is a definition-only replacement: identity columns (code, archetype `A6b`, `test_id=12`, `version=1`, status `Active`, `id=7`) are untouched and `TPL-A6B-0001` is the sole row carrying `modified_by='a6b-rebuild'`. No other template and no Test rows were affected.

The numeric contract is the acceptance bar, and it holds. The stored definition reproduces the sheet's gold values through the real engine: Std Conc 15.055, replicate Mean 1290029 and %RSD 0.44098, pooled %RSD 0.86913, STD co-relation 1.00234, Unit-1 %release across all five timepoints, per-timepoint Mean/SD/%RSD/Min/Max, and the amount-remaining table — 21/21 PASS in the author's gate loaded from the DB row.

Rounding is modelled declaratively. Each rounding-sensitive field carries a `rounding: {mode, digits}` object (`round`/3 for Std Conc, `trunc`/5 for both %RSDs, `trunc`/1 for pooled mean); the replicate mean is left raw to match the sheet's AVERAGE. This is cleaner than embedding ROUND/TRUNC in the expression and matches the sheet cell-by-cell.

The with-replacement physics lives in the `release` sequence group: each unit's content is `base_n + coalesce(prev.content_n, 0) * withdrawal/total`, where `base_n` is the per-unit raw assay normalized by that unit's own net vial weight. The twelve `base_n` carry columns are hidden; the visible surface is `time_hr` + 12 unit columns + Mean/SD/%RSD/Min/Max, exactly as the brief requires.

The DB row and the declarative source module are byte-for-byte equal after a canonical JSON compare, so the committed module is a faithful record of what is stored. A timestamped `lims.db.bak-a6b0001-*` backup predates the write, the throwaway gold-value script was removed, and the verification evidence remains in the task directory.

<details>
<summary>Issues (2)</summary>

1. **Min/Max span generality** — Min/Max are taken over all 12 visible unit columns, whereas the sheet's 0.5hr cells reference `MIN/MAX(B:G)` (6 units). They coincide at the pinned 0.5hr row so the gate passes, but the general-row behavior is unverified. Author-documented; non-blocking. Confirm with QA that the 12-unit span is the intended reporting definition.
2. **Rounding expressed as attributes, not formulas** — The brief phrases rounding as `ROUND(...,3)` / `TRUNC(...,5)` inside the formulas; the implementation uses structured `rounding` attributes instead. Functionally equivalent and confirmed correct against gold values — noted only so a reviewer grepping the formula strings for `round`/`trunc` doesn't mistake their absence for a gap.

</details>

<details>
<summary>Details</summary>

### Identity preserved, single-row replacement

The row was mutated in place: reading `test_templates` back shows `code=TPL-A6B-0001, archetype=A6b, version=1, status=Active, test_id=12, id=7`, and `TPL-A6B-0001` is the only row with `modified_by='a6b-rebuild'`. No new template code was introduced (the seeder skips existing codes, which is why a dedicated `update_a6b_definition.py` was added to force the overwrite), and no Test rows were touched. This satisfies the "replace, don't create" constraint.

### DB row equals the declarative source module

A canonical `json.dumps(..., sort_keys=True)` compare of the stored `definition` against `A6B_DEFINITION` from `scripts/template_definitions/a6_dissolution.py` returns equal. The committed module is therefore an accurate record of what the engine will load, and the parity suite exercises the same structure that is stored.

### Rounding modelled as structured attributes

The one place worth reading carefully: the brief states Std Conc as `ROUND(...,3)`, replicate/pooled %RSD as `TRUNC(...,5)`, pooled mean as `TRUNC(...,1)`. The formula strings contain none of these wrappers, which on a first pass looks like a gap. Reading the full field objects resolves it — the rounding is carried out of band:

```
conc_ppm : expression "…* 1000"          rounding {mode: round, digits: 3}
rsd_std  : expression "sd(...)/mean*100"  rounding {mode: trunc, digits: 5}
mean_bkt : expression "mean(pool(...))"   rounding {mode: trunc, digits: 1}
rsd_bkt  : expression "sd(pool(...))/…"   rounding {mode: trunc, digits: 5}
mean_std : expression "mean(std_areas.area)"   (no rounding — raw AVERAGE)
```

This matches the sheet cell-for-cell, and the replicate mean being left raw is why the gate pins it at the full-precision `1290029`.

### With-replacement carry-over in the `release` sequence group

The physics of the whole-vial-replacement method is the core of this template. Each unit's per-timepoint content is:

```
content_n = base_n + coalesce(prev.content_n, 0) * withdrawal_volume / total_volume
```

where `base_n` is the raw assay for that unit — raw area over standard mean, through the full standard dilution chain and test-prep volumes, normalized by that unit's own `gravimetric.net_n` vial weight, scaled by potency, label claim and `wt_per_ml`. `coalesce(prev.content_n, 0)` makes the first timepoint reduce to `base_n` and every later timepoint add back the fraction of drug removed in prior pulls — the standard with-replacement correction.

```
            base_n (this timepoint, per-unit net-weight normalized)
              +
   prev row content_n  ×  withdrawal_volume / total_volume   (carry-over)
```

The twelve `base_n` columns are `hidden:true`; the visible columns are `time_hr`, `content_1..content_12`, and `mean / sd / rsd / min_val / max_val`. That is exactly the "time + 12 units + Mean/SD/%RSD/Min/Max" visible surface the brief specifies.

### Min/Max span

`min_val`/`max_val` in both `release` and `amount` are computed over the full 12-unit list. The sheet's 0.5hr summary cells use `MIN(B59:G59)/MAX(B59:G59)` — only the first six units. For the 0.5hr row the 12-unit extremes (82.9124 / 87.6712) happen to equal the 6-unit extremes, so the gate's Min/Max checks pass without distinguishing the two definitions. The author flagged this in the verification notes. It is not a gold-value failure, but the general-row reporting semantics (12-unit vs banked 6-unit span) are a QA decision rather than something the numeric gate has proven.

### Amount-remaining table

`amount.remain_n = number(pct_assay) - release.content_n[rowno-1]` reproduces the sheet's `% Release` table as %Assay minus the computed content, with its own Mean/SD/%RSD/Min/Max over the 12 units. The group-key naming (`release` = computed content, `amount` = %Assay − release) follows the user brief rather than the sheet's row titles, and the divergence is documented in the module.

### SST and co-relation wiring

System-suitability items 1–3 are text inputs defaulting to "Complies"; item 4 references `stats.rsd_std` (replicate %RSD) and item 5 references `stats.rsd_bkt` (pooled bracketing %RSD), so the SST acceptance lines track the computed stats rather than duplicating the formulas. The co-relation block computes `std1_mean/std2_mean * std2_weight/std1_weight` from the two STD area tables, reproducing the gate's 1.00234.

### Chart configuration

`release_chart` carries a group-level `chart` object: title "% Release vs Time", `sourceGroup: release`, `xField: time_hr`, twelve unit series (`content_1..content_12`) plus a Mean series, and `defaultSeries: ["mean"]` — mirroring the TPL-A6A-0004 pattern. `resultRef` is `release.mean`.

### Verification evidence and safety

The author's gate (`scripts/_verify_a6b_gold.py`, since deleted) loaded the definition from `lims.db`, fed the sheet inputs, ran the real evaluator and asserted 21 gold values: Std Conc, replicate Mean/%RSD, pooled %RSD, STD co-relation, Unit-1 %release at all five timepoints, 0.5hr Mean/SD/%RSD/Min/Max, 3/7/24/48hr Means, and two amount-remaining values — all PASS. A `lims.db.bak-a6b0001-20261016-122436` backup exists from before the write. The `--validate-only` seeder parse succeeds (14 groups, 48 inputs, 16 area fields, 71 calculated, 1 criteria). The throwaway gold script is confirmed removed; `verification.md` remains.

### Test coverage

The seeded-template parity suite was rewritten with a `TestA6BDissolutionWithReplacement` class plus the four catalogue-wide invariants, and passes (244). The broader `tests/calculation` run is 752 passed / 2 failed; the two failures are worksheet-lifecycle locking assertions on an in-memory A1 stand-in template, reproduce on the baseline with this task's edits stashed, and are unrelated to A6B. The TPL-A6A-0004 guard test passed untouched.

Not tested: the Min/Max span on rows where the 12-unit and 6-unit extremes diverge (the gate only pins 0.5hr, where they coincide).

</details>

<details>
<summary>File map</summary>

- `backend-v2/scripts/template_definitions/a6_dissolution.py` — `A6B_DEFINITION` rebuilt to the 12-unit Doxorubicin with-replacement structure (standard/replicate/bracketing stats, co-relation, SST, test-prep, gravimetric, `release` sequence with carry-over, `amount` table, chart).
- `backend-v2/scripts/update_a6b_definition.py` — new one-shot script that overwrites the stored `TPL-A6B-0001` definition in `lims.db` (seeder skips existing codes).
- `backend-v2/tests/calculation/test_seeded_template_parity.py` — parity class rewritten to the new A6B structure.
- `backend-v2/.agents/tasks/a6b0001-dissolution-rebuild/{plan.md, verification.md}` — plan and gold-value evidence.
- `backend-v2/lims.db` — `TPL-A6B-0001` row `definition` replaced in place (not tracked in git; verified directly). Backup `lims.db.bak-a6b0001-20261016-122436` present.

Full diff: `git show 827271c`.

</details>
