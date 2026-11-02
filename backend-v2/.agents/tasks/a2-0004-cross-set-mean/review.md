# Cross-set `% Mean` for TPL-A2-0004 lipid samples

The `pct_mean` calculated field in `_lipid_sample_fields()` is changed in place from `mean([pct_assay])` (that row's own single-injection %Assay) to a blank-skipping cross-set replicate mean, `mean([ lipid_samples.pct_assay[cidx], lipid_samples.pct_assay[cidx + 4] ])`. For each of the four compounds the engine now averages that compound's %Assay from Set 1 (absolute row `cidx`) and Set 2 (absolute row `cidx + 4`) and shows the identical value on both of the compound's rows. This implements the authoritative requirement ("Tricaprylin's % Mean = mean(Set1, Set2), one value shown on both sets' rows") and overrides the older `plan.md`, which described adding a second column; the coder correctly followed the authoritative in-place instruction. `drug_lipid` is untouched and still reads `pct_mean`, so the reportable Drug/Lipid ratio now flows from the cross-set means while Set-1-only data preserves the gold ratio `0.841429`.

Watch for: nothing blocking. One unrelated working-tree file (`frontend-react/.agents/tasks/worksheet-column-merge/verification.md`, a task-doc note from a different task) is modified alongside this change — informational only, not code or DB (confirmed).

**Verdict**: APPROVED

## High-level view

The change is a one-line expression swap plus its docstring/comment. The engine supports a group referencing its own column series by absolute row index — the same mechanism `drug_lipid` already uses cross-group — so `lipid_samples.pct_assay[cidx]` and `[cidx + 4]` resolve against the whole `pct_assay` column. `referenced_paths` is only `{cidx, lipid_samples.pct_assay}` and `pct_assay` depends on none of the mean fields, so the toposort resolves `pct_mean` from `pct_assay` deterministically with no self-reference cycle; all 12 parity tests evaluate green, confirming no circularity.

The cross-set mean is correct and symmetric: for every compound the Set-1 row and the Set-2 row carry the identical value, equal to `(set1_assay + set2_assay)/2`, asserted hand-derived from the engine's own `pct_assay` returns so the oracle cannot pin a bug. Blank-skipping mean means Set-1-only data (blank Set-2 area) yields the single Set-1 value on both rows, so the Set-1 gold figures `99.98/86.20/101.77/100.39` and the ratio `0.841429` are preserved.

`drug_lipid` still reads `lipid_samples.pct_mean[(rowno-1)*4+idx]` with its formulas byte-unchanged; the git diff touches only the `pct_mean` block, leaving `pct_assay`, `cidx`, `compound_name`, `lc`, prep inputs, `area`, the `standard`/`std_areas`/`bkt_areas`/`stats` groups, context and the 8 SST criteria byte-identical.

The live DB row id 35 was synced and is byte-for-byte and canonically equal to the module definition (14226 chars each), with identity `(35, TPL-A2-0004, v1, Active)` unchanged. The parity test was extended with both fixtures (Set-1-only and both-sets) plus a DB byte-equality lock; throwaway scripts were deleted and the mandated `lims.db` backup exists.

<details>
<summary>Issues (1)</summary>

1. **Unrelated file in working tree** — `frontend-react/.agents/tasks/worksheet-column-merge/verification.md` is modified alongside this change. It is a task-doc note from a different task (recording a frontend commit hash), not code or DB and not part of this task's scope. Non-blocking; exclude it when committing this task so the A2-0004 commit stays scoped.

</details>

<details>
<summary>Details</summary>

### Cross-set mean correctness and symmetry

The new expression averages a compound's %Assay across its two set rows by absolute index. Compound index `cidx = (rowno-1) mod 4` (0=tri, 1=dppg, 2=chol, 3=depc) is identical for a compound's Set-1 row (`cidx`) and Set-2 row (`cidx + 4`), so both rows evaluate `mean([pct_assay[cidx], pct_assay[cidx+4]])` and necessarily produce the same number. `test_cross_set_mean_same_value_on_both_rows` asserts `set1_mean == set2_mean` and `== (set1_assay + set2_assay)/2` for all four compounds, deriving the expected value in-line from the engine's returned `pct_assay` rather than hard-coding it. The engine-captured cross-check `100.979/87.062/102.790/101.394` matches to `abs=1e-3`.

### No self-reference cycle

`referenced_paths` of the expression is `{(cidx,), (lipid_samples, pct_assay)}`; `pct_assay` depends on `cidx`/`area`/`stats.*` and on no mean field. The toposort therefore orders `pct_assay` before `pct_mean` with no cycle, which `TemplateDefinition.parse` and all 12 parity evaluations confirm (no schema or circular-reference error). This is a same-group cross-row read into the group's own column series, the same scope mechanism `drug_lipid` uses cross-group.

### Set-1-only gold preserved

`test_set1_only_cross_set_mean_equals_set1` fills only Set 1 (rows 4..7 blank area). `pct_assay` on rows 4..7 is `EMPTY`; the blank-skipping `mean` drops it, so `pct_mean` on both the Set-1 row and the blank Set-2 row equals the compound's Set-1 %Assay — `99.979/86.200/101.772/100.390` on both `base=0` and `base=4`. `test_drug_lipid_ratio_chain` keeps the ratio at `0.841429`, unaffected because `pct_mean` still equals the Set-1 %Assay when Set 2 is blank.

### Both-sets ratio chain

With Set 2 = Set1×1.02 truncated, `test_cross_set_ratio_chain` hand-derives `sum_lipid` from the four cross-set means and the LC context, computes `mgml_bupi = 99.9 * lc_bupi/100`, and asserts both `drug_lipid` rows and `reportable_result` equal `mgml_bupi/sum_lipid` (engine cross-check `≈0.833098`). Both rows match because both SETs reference the same cross-set means — consistent with `drug_lipid` reading the now-shared per-compound `pct_mean`.

### Scope and untouched sections

The module git diff is confined to the `pct_mean` field expression and its docstring bullet / inline comment. `drug_lipid` still reads `lipid_samples.pct_mean[(rowno-1)*4+idx]` with unchanged formulas (verified present in the DB JSON too). `pct_assay`, `cidx`, `compound_name`, `lc`, the five prep inputs, `area`, the `standard`/`std_areas`/`bkt_areas`/`stats` groups, context and the 8 SST criteria are byte-identical. DB row 35: `exact_equal=True`, `canonical_equal=True`, lengths 14226/14226, identity `(35, TPL-A2-0004, 1, Active)` unchanged. The mandated backup `lims.db.bak-a2xsetmean-20261022-102317` is present; the three throwaway scripts named in the verification note are gone. The parity file rises from 9 to 12 tests, all passing.

</details>

<details>
<summary>File map</summary>

- `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` — `pct_mean` expression swapped to the cross-set mean; docstring bullet + inline comment updated. Only change in the module.
- `tests/calculation/test_a2_0004_tabular_parity.py` — Set-1-only test reworked to assert cross-set-mean-on-both-rows + blank Set-2 behavior; new `TestA2_0004CrossSetMean` both-sets oracle (hand-derived); new `test_db_definition_matches_module` byte-equality + identity lock.
- `lims.db` (row id 35) — definition re-synced to the module; identity unchanged.
- `frontend-react/.agents/tasks/worksheet-column-merge/verification.md` — unrelated task-doc note (out of scope for this task).

Full diff: `git diff` in `backend-v2`.

</details>
