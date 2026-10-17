# TPL-A2-0004 Bupivacaine Lipid Content & Drug-to-Lipid Ratio — template review

A single new declarative template module (`a2_bupivacaine_lipid_ratio.py`)
reproduces the two-sheet Bupivacaine workbook (`'Lipid '` + `'Drug to Lipid ratio
Auto Calc'`) as one template with six groups, registered in `SEED_TEMPLATES`
after the other A2 entries and seeded into `lims.db` as a single new row plus a
new Test Master entry `TST-LIPID-RATIO`. The module is the source of record and
the seeded DB row's `definition` JSON equals it byte-for-byte. Every sheet formula
was traced cell-by-cell against the workbook dump and matches; the coder's gold
table reproduces all 18 assertions including the batch-B anchor values.

Watch for: nothing blocking. The module, its registration, and the seeded row are
a clean, isolated addition committed by itself (`dbd273f`); the `a6_dissolution.py`
and `frontend-react/*` edits in the working tree are pre-existing, from a prior
step, and outside this change (**confirmed**).

**Verdict**: APPROVED

## High-level view

The four lipid compounds are laid out as fixed columns/scalars rather than table
rows, exactly as the sibling `a2_lyso_content.py` does. That keeps every
cross-reference in the per-compound %Assay a plain scalar — each compound divides
by its own replicate mean (`$B$31..$E$31` → `stats.mean_std_<c>`) and multiplies
by its own standard-detail row — which is the single most important fidelity point
in the sheet and is encoded correctly.

The two sheets collapse into one template because sheet 2 is pure arithmetic over
sheet 1's per-compound `%Mean`. The Drug-to-Lipid group reads the matching Lipid
batch's `%Mean` by row index (`lipid_samples.<c>_mean[rowno - 1]`), relying on the
two batch tables carrying rows in the same order. The reportable is the last
non-blank `drug_lipid.ratio`.

Archetype A2 and code TPL-A2-0004 are the correct next free slot (0001/0002/0003
in use); nothing is renumbered and the carried-over `TPL-A12-0002`/`TST-DLR` are
untouched. result_unit is None, status Active, approver seed. The seeded row
equals the module and total template count went 34→35, as claimed.

Formula fidelity holds end-to-end: Std Conc ppm, replicate Mean/SD/%RSD, pooled
bracketing via `pool(...)`, the full N39 %Assay chain, the blank-tolerant `%Mean`
average, and the Drug-to-Lipid mg/mL / sum / Bupivacaine mg/mL / ratio columns all
map term-for-term to the sheet, with no mid-chain rounding.

The only judgement calls are the eight NMT 2.0 % SST criteria and modelling the
per-compound label claims as overridable context — both are documented, the sheet
prints no numeric limit, and both follow the house convention. Neither blocks.

<details>
<summary>Issues (0)</summary>

No blocking or non-blocking action items. The SST limit (2.0 % NMT per compound)
and the context-vs-per-row modelling of label claims are documented assumptions,
not defects; they change only `limit`/`limitText` or field placement if the lab
later supplies different values.

</details>

<details>
<summary>Details</summary>

## Per-compound layout and the %Assay denominators

The sheet's `N39` (Tricaprylin %Assay) is
`M39/$B$31 * B18/C18 * D18/E18 * F18/G18 * J39/I39 * L39/K39 * H18/G39 * I18/J18 * H39`,
and `N40`/`N41`/`N42` divide by `$C$31`/`$D$31`/`$E$31` and pull from rows 19/20/21
respectively. That is the sheet's defining structure: each compound's assay is
anchored to its own replicate-mean column and its own standard row. The module
lays the compounds out as fixed columns — `stats.mean_std_<c>`, `standard.<c>_*` —
so `_assay_expression("tri", ...)` reads
`area / stats.mean_std_tri * standard.tri_weight / standard.tri_vol1 * ... *
standard.tri_potency / lc_tri * standard.tri_mw_base / standard.tri_mw_salt *
avg_weight`. Mapping each sheet column (B=weight, C=vol1, D=pip1, E=vol2, F=pip2,
G=vol3, H=potency, I=mw_base, J=mw_salt; J39=vol_j, I39=sample_weight, L39=vol_l,
K39=pip_k, G39=lc, H39=avg_weight) against the expression confirms a term-for-term
identity for all four compounds. A compounds-as-rows layout would have forced the
"DPPG mean" and "DPPG standard row" references through aligned row indices; the
column layout keeps them scalar, matching the proven sibling.

## Standard, replicate and pooled-bracketing statistics

`K18 = B18/C18*D18/E18*F18/G18*H18/100*I18/J18*1000` maps exactly to the
`<c>_conc_ppm` expression. Replicate stats are `AVERAGE/STDEV` over `B25:B30`
(`mean`/`sd`/`rsd` of `std_areas.<c>_area`). The pooled bracketing stats are the
sheet's `AVERAGE(H25:H30,B25:B30)` / `STDEV(B25:B30,H25:H30)` — the module uses
`pool(std_areas.<c>_area, bkt_areas.<c>_area)`, which flattens and drops the two
blank bracketing rows, so a 6+4 pool reconciles to the sheet. `rsd` is `sd/mean*100`,
matching `H33 = H32*100/H31`. The gold values (pooled Tricaprylin mean 8699733.9,
%RSD 0.2383) reproduce.

## Blank-tolerant %Mean averaging

`O43 = AVERAGE(N39, N43)` averages the two injections, and a blank second
injection must leave the inj-1 value. The module writes
`mean([<c>_assay1, <c>_assay2])`. Traced through the engine: a `_ListNode`
evaluates to `[value, EMPTY]`, and `_f_mean` → `_numeric` flattens and skips the
EMPTY, so a single filled injection returns its own value — identical to Excel's
`AVERAGE` over a range with one blank. This is the correct construct and the
batch-B `%Mean` equals its single injection's %Assay, as the gold table shows.

## Drug-to-Lipid cross-sheet reference

Sheet 2's `I18 = H18*G18/100` where `H18 = 'Lipid '!O43` (the %Mean) and
`G18 = 'Lipid '!G39` (the compound LC). The module writes
`lipid_samples.<c>_mean[rowno - 1] * lc_<c> / 100`, reading the matching batch's
%Mean by row index and multiplying by the same per-compound LC that feeds the
Lipid %Assay denominator. This depends on `lipid_samples` and `drug_lipid` holding
batches in the same row order; the dependency is documented in the module and is
the natural analogue of the sheet's `='Lipid '!O43` cross-sheet link. `J18 =
SUM(I18:I21)` becomes the four-term `tri_mgml + dppg_mgml + chol_mgml + depc_mgml`;
`M18 = K18*L18/100` is `pct_assay_bupi * lc_bupi / 100`; `N18 = M18/J18` is
`mgml_bupi / sum_lipid`. `resultRef = drug_lipid.ratio` returns the last non-blank
ratio. Batch-B gold values (mg/mL Tri 1.99958, Sum 15.790645, Bupivacaine 13.2867,
ratio 0.841429) all reproduce.

## Metadata, code allocation and isolation

Existing A2 codes are TPL-A2-0001/0002/0003; TPL-A2-0004 is the next free slot and
collides with nothing. The DB spot-check (re-run narrowly, not the full seeder)
confirms exactly one row for TPL-A2-0004 with name "Bupivacaine Lipid Content &
Drug-to-Lipid Ratio", archetype A2, result_unit None, status Active, approver
seed, and that `json.loads(definition) == LIPID_RATIO_DEFINITION` — the module
equals the seeded row. Total templates went 34→35. The change is committed in
isolation (`dbd273f`): only the new module, a two-line `__init__.py` import/append,
and the task evidence files. The carried-over `a12_derived_rollups.py` /
`TPL-A12-0002` / `TST-DLR` are untouched. The `a6_dissolution.py` and
`frontend-react/*` edits present in the working tree are pre-existing uncommitted
changes from a prior step, not part of this commit.

## SST criteria and label-claim modelling

The sheet computes per-compound %RSD for both the replicate (row 33) and pooled
bracketing blocks but prints no numeric limit. The module adds eight blocking
`NMT 2.0 %` criteria — replicate + pooled, per compound — matching the sibling A2
convention. The per-compound label claims (`G39..G42`) and Bupivacaine LC (`L18`)
are modelled as overridable context because they are constant per compound across
every batch on the sheet. Both are documented assumptions; if the lab supplies a
printed limit or needs per-batch LC, only `limit`/`limitText` or field placement
change, with the arithmetic unaffected.

## Verification evidence relied on

The coder's `verification.md` records `--validate-only` (ok, 6 groups, 48 inputs,
16 area fields, 47 calculated, 8 criteria), a real insert and an idempotent
re-run (skip), the DB-equals-module check, and a throwaway gold-value script
asserting all 18 values across three batches. The five failing suite tests are
shown to be pre-existing and unrelated (A6B dissolution + worksheet editability),
proven by a stash experiment. I independently re-confirmed the DB row count,
metadata, module-equals-row, and template count, and traced every sheet formula
against the workbook dump. I did not re-run the full seeder or the gold script —
the evidence left no specific doubt that warranted it.

</details>

<details>
<summary>File map</summary>

- `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` — new; the full
  template definition (context header, standard singleton, replicate + BKT area
  tables, stats singleton, lipid_samples table, drug_lipid table, 8 SST criteria,
  SeedTemplate TPL-A2-0004 / TST-LIPID-RATIO).
- `scripts/template_definitions/__init__.py` — +2 lines; import `TEMPLATES as
  _A2_BUPI` and append `*_A2_BUPI` to `SEED_TEMPLATES` after the other A2 entries.
- `.agents/tasks/bupivacaine-lipid-ratio/{plan,verification}.md`,
  `verification-output.txt` — evidence trail.

Source commit: `dbd273f`. Workbook dump:
`_dumps/Bupivacaine Lipid _ Drug to lipid Ratio.txt`.

</details>
