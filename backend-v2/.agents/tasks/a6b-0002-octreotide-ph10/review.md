# TPL-A6B-0002 Octreotide pH-10 dissolution — formula-exact rebuild of a units-as-rows sheet

The change adds a new seeded dissolution template that reproduces `Dissolution sheet_Octreotide_PH 10.xlsx` (sheet `42_2-8°C_`) as a fresh module `a6b_octreotide_ph10.py`, registers it once in `__init__.py`, and ships a 14-assertion parity test. Unlike the 12-unit Doxorubicin A6B-0001 archetype (timepoints down the rows, recursive carry-over), this sheet is modeled units-as-rows with three independent 6-unit timepoint tables (1 hr/4 hr/24 hr), each dividing %Residue by its own weight column. Every traced formula was re-derived by hand against the authoritative dump and matches; all gold values reproduce to the sheet's shown precision; the Test tag preserves the user's `Dissolution-Octreolide-pH-10` spelling; and scope is tight (three files, A6B-0001 untouched). The two deliberate omissions — the dead area-driven K64 %Release block and the L/M carry-over columns — are forced by the source itself being `#VALUE!` in those cells and are documented, not silent.

Watch for: the cumulative WITH-REPLACEMENT M-chain the brief asked to confirm is **not modeled** (confirmed) — this is a deliberate, documented omission because the chain goes `#VALUE!` at M70 on the source sheet, not a bug; and the DB-level checks (Active row, canonical-JSON byte-equality) rest on the coder's recorded evidence rather than independent re-run (per instruction).

**Verdict**: APPROVED

## High-level view

The formula mapping is exact. J19 concentration, the B27/D27 means (D27 pooled across B-replicates + D-BKT via `pool`), B29/D29 %RSD, the F/G/H weight stats (including the deliberately-reproduced `STDEV(F22:F28)` quirk that folds the mean cell into the SD range), the per-timepoint %Residue K-chain with its own-weight-column divisor, and the C70 residue-from-assay %Release all line up cell-for-cell with the dump. Hand re-derivation of K40, K52, D27, and C70 reproduced the gold values to full precision.

The M carry-over chain is absent by design. On the source, M46→M52→M64 are computable sums but M70 onward is fed by L64/K64, and K64 divides by the empty merged cell `$F$19`, so the source's own M70+ cells are cached `#VALUE!`. No reportable value depends on a live M, so the omission changes nothing a lab would read off the sheet; re-enabling it is explicitly left as a lab decision.

The acceptance criterion correctly navigates a real trap: the shared `sst_rsd_criterion()` helper defaults its target to `stats.rsd_std`, but this template renames the statistics group to `std_stats`, so the call passes `target="std_stats.rsd_std"` explicitly. A verbatim copy of the A6B-0001 call would have produced a criterion pointing at a non-existent field that never evaluates. The parity test pins this target.

Scope and identity are clean. Only the new module, one `__init__` registration line, and the new parity test changed; A6B-0001's module is not in the diff. The Test tag is the exact user spelling. The DB invariants and the unchanged 5 pre-existing failures are taken from the coder's verification evidence, which is specific and internally consistent.

<details>
<summary>Issues (2)</summary>

1. **M carry-over chain not modeled (non-blocking, confirmed)** — deliberate and documented; the source's own M70+ cells are `#VALUE!` via the dead K64 path, so nothing reportable depends on a live M. If a future lab decision wants the running sum live, model L as `residue/10*withdraw_replace` and M as a sequence cumulative sum. No action required for this template.
2. **DB-level parity taken on evidence, not re-run (non-blocking, by instruction)** — Active-row / canonical-JSON-byte-equal / 5-known-failures claims rest on `verification.md`, not independent re-execution, per the review instruction not to re-run the suites. Evidence is specific and consistent; flagged only for transparency.

</details>

<details>
<summary>Details</summary>

### Formula parity against the dump — every traced cell matches

J19 `=E19/G19*H19/I19*C19/D19*B19/100*1000` maps term-for-term to `weight_mg/dilution_1*volume_1/dilution_2*mw_base/mw_salt*potency/100*1000`. Hand check: 25.65/25·5/50·1·89.41/100·1000 = 91.73466, equal to gold.

The standard statistics are exact. B27=`AVERAGE(B22:B26)`→`mean(std_areas.area)`; B29=`B28*100/B27`→`sd(...)*100/mean_std`. D27 is the subtle one — the dump shows `AVERAGE(B22:B26,D22:D26)`, i.e. the five B-replicates pooled with the two D-BKT areas (not the D-replicates), and the module writes `mean(pool(std_areas.area, bkt.area))`. Hand check of the 7-value pool gives 3035369.2857…, equal to gold D27.

The sample-weight stats reproduce the sheet quirk correctly: F28=`AVERAGE(F22:F27)` but F29=`STDEV(F22:F28)` with the range extending one row into the mean cell. The module encodes this as `sd(pool(weights.w_1hr, [mean_1hr]))` — SD over the raw weights pooled with the computed mean cell — and the 1/4/24 hr Mean/SD/%RSD gold values (23.745/0.155/0.6528, 24.985/0.145/0.5803, 24.475/0.865/3.5342) all reproduce. A silent "correction" of this range would have broken parity; keeping it is required.

The %Residue K-chain `K40 = B40/$B$27*$E$19/$G$19*$H$19/$I$19*$C$35/$B$35*$A$35/$F22*$B$19*$C$19/$D$19` maps cleanly: `$C$35`→vf_vol, `$B$35`→pipette_vol, `$A$35`→media_vol, with the per-unit own-weight divisor `/$F22` (1 hr), `/$G22` (4 hr), `/$H22` (24 hr) expressed as `weights.w_1hr[rowno-1]` / `w_4hr` / `w_24hr`. Hand check: K40 = 4.03866283…, K52 (24 hr, weight 25.34) = 1.93559199…, both equal to gold. The C40==K40 mirror on the sheet is collapsed into a single calculated field, which is correct since C just echoes K.

The %Release block uses the live C70 path `=($A$32-B70)/($A$32)*100` → `(number(prep.pct_assay)-residue_in)/number(prep.pct_assay)*100`, with `number()` guarding the pct_assay divisor against free text. Hand check C70 = 1.94174757…, equal to gold.

### The WITH-REPLACEMENT M-chain is a documented omission, not a gap

The brief asked to confirm M52=L46+M46, M64=L52+M52, M70=L64+M64. The dump confirms those formulas exist and that M46=`IF(L40="","",L40)` seeds the chain. But M70 and everything after it reads L64, and L64=`IF(K64="","",K64*…)` where K64 divides by `$F$19` — the empty half of the merged `E19:F19` cell. B64:B69 hold only the column-header string with no per-unit area inputs. So on the source workbook K64, L64, and the entire M70+ cascade are cached `#VALUE!` (`t="e"`). The coder's decision to omit L/M entirely is therefore faithful to the sheet: no value a lab reads off this sheet depends on a live M, and reproducing a `#VALUE!` would be meaningless. The design records the re-enable recipe should a lab later decide the running sum should be live. Modeling a live M against a source that goes `#VALUE!` at M70 would have invented behavior the sheet does not have.

### Acceptance criterion avoids the renamed-group trap

`sst_rsd_criterion()` in `_common.py` defaults `target="stats.rsd_std"`. This template renames the standard-statistics group to `std_stats` (to disambiguate from the weight/residue stats), so a verbatim copy of A6B-0001's `sst_rsd_criterion()` would have emitted a criterion targeting the non-existent `stats.rsd_std` — parsing fine, evaluating never. The module passes `target="std_stats.rsd_std", limit=2.0` explicitly. The schema parses the scalar limit into the tuple `(2.0,)` for the single-limit `lte` operator, and the parity test asserts exactly `crit.target == "std_stats.rsd_std"`, `operator lte`, `limit == (2.0,)`. This matches the A6B-0001 "NMT 2.0 % standard-replicate %RSD" convention — the only machine-checkable limit the sheet defensibly supports, since it prints no numeric spec column.

### Scope, identity, and A6B-0001 isolation

The commit (e780345) touches exactly three files: the new `a6b_octreotide_ph10.py`, a two-line `__init__.py` addition (import + splice `*_A6B_OCT` in A6 order), and the new parity test. `a6_dissolution.py` — which carries A6B-0001 — is not in the diff, so A6B-0001 is provably unaffected. The design's "Files to touch" had anticipated appending into `a6_dissolution.py`; the coder instead used a separate module, which is a cleaner, equally-valid choice that further isolates A6B-0001. Identity matches the design: code TPL-A6B-0002, archetype `A6b`, result_unit `%`, test_code `TST-DISS-OCT-PH10`, and test_name `Dissolution-Octreolide-pH-10` with the user's "Octreolide" spelling preserved verbatim.

### Evidence-based checks (not independently re-run, per instruction)

verification.md records: parse+empty-eval clean; registered once at index 11; the parity test 14-passed; seeder `--validate-only` clean (`14 groups, 24 inputs, 5 area fields, 46 calculated, 1 criteria`); live seed adding the Test Master row and the template; a DB snippet confirming one Active TPL-A6B-0002 row bound to the EXACT test name with stored canonical-JSON byte-equal to the module's definition; and the full calculation suite going from a `5 failed, 780 passed` baseline to `5 failed, 798 passed` with the same 5 pre-existing failures (3 A6B-0001 + 2 worksheet_service) and +18 passes (14 new parity + 4 catalogue invariants). The evidence is specific, internally consistent, and names the commit hash, so per the review instruction it is accepted without re-running the suites.

### Test coverage

The parity test fixtures the dump's entered values exactly (5 std areas, 2 BKT, units 1-2 weights with 3-6 blank, two sample areas per residue timepoint, two entered %Residue per release timepoint) and asserts every gold value in the design's full set, plus resultRef resolution, the criterion shape, and an empty-worksheet-is-blank-not-error case. Not independently exercised here: the DB-row/canonical-JSON invariants (covered by the coder's throwaway snippet, since deleted) and the catalogue-wide parametrized invariants (covered by the suite count delta). Both are reasonable to leave to the recorded evidence.

</details>

<details>
<summary>File map</summary>

- `scripts/template_definitions/a6b_octreotide_ph10.py` — NEW: the TPL-A6B-0002 definition (context, standard, std/bkt areas + stats, params, weights + weight stats, prep, three %Residue timepoint tables, three %Release-from-assay tables, single std-%RSD criterion).
- `scripts/template_definitions/__init__.py` — import `_A6B_OCT` and splice `*_A6B_OCT` into `SEED_TEMPLATES` in A6 order.
- `tests/calculation/test_a6b_0002_octreotide_parity.py` — NEW: 14-assertion parity test against the dump's gold set.

Full diff: `git show e780345`. Authoritative formula source: `_dumps/Dissolution sheet_Octreotide_PH 10.txt`.

</details>
