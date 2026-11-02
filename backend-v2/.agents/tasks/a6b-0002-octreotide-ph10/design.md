# Design — TPL-A6B-0002, Dissolution (Octreotide Acetate, pH-10, with replacement)

New seeded dissolution template that reproduces the calculation sheet
`Test types/Dissolution sheet_Octreotide_PH 10.xlsx` (sheet `42_2-8°C_`,
A1:R91). Backend/data only: a new `SeedTemplate` added to the declarative
module `scripts/template_definitions/a6_dissolution.py`, seeded Active, bound to
a NEW Test Master entry. No existing template or Test is touched.

Authoritative source is the full cell+formula dump
`_dumps/Dissolution sheet_Octreotide_PH 10.txt`, cross-checked against the live
`.xlsx` via `zipfile`+XML (the cached `<v>` values in `xl/worksheets/sheet1.xml`
are the sheet's own computed results and are the parity oracle below).

## Identity

| Field | Value |
|---|---|
| Template code | `TPL-A6B-0002` (confirmed free: only `TPL-A6B-0001` exists; A6A goes to 0004, A6B only 0001) |
| Template name | `Dissolution (Octreotide Acetate, pH 10)` |
| archetype | `A6b` |
| result_unit | `%` (matches A6B-0001 convention) |
| resultRef | `residue_24hr.mean` (final live timepoint's %Residue mean; see note) |
| test_code | `TST-DISS-OCT-PH10` |
| test_name | `Dissolution-Octreolide-pH-10` (EXACT user tag, including the "Octreolide" spelling) |
| test_type | `Quantitative` |

Created via the seeder's `ensure_test` (absent today). Do NOT reuse an existing
Test.

## Modeling decision: units-as-rows, timepoints-as-separate-groups

A6B-0001 (Doxorubicin) is a 12-unit sheet with the recursive carry-over running
*down* the timepoint rows, so it puts timepoints on the row axis and units as 12
columns, using a `sequence` group with `prev`/`prior`.

The Octreotide sheet is shaped differently and simpler to reproduce faithfully
with a **per-timepoint table, units as rows**:

* Each timepoint (1 hr @37°C, 4 hr @55°C, 24 hr @55°C) is a fixed 6-unit block
  (rows 40-45, 46-51, 52-57). The per-unit %Residue formula divides by *that
  unit's own weight* for *that timepoint* — `$F22` for 1 hr unit-1, `$G22` for
  4 hr unit-1, `$H22` for 24 hr unit-1 — i.e. each timepoint block reads a
  different weight column but the same unit rows (22..27).
* The aggregates (Mean/Min/Max/RSD) are per-timepoint over that block's 6 units
  (`AVERAGE(C40:C45)` etc.), with blanks excluded.

So I model each timepoint as its own 6-row `table` group whose per-unit %Residue
references the matching weight column. Units-as-rows (6) + three timepoint groups
reproduce the sheet exactly and keep every formula a single-row expression. This
is chosen over A6B-0001's sequence shape because the Octreotide carry-over (M
column) is **not** part of any live reportable value on this sheet (see the M/
dead-path analysis), so the recursion machinery is unnecessary; faithful
reproduction of the live %Residue and %Release blocks is what matters.

Row counts: 5 standard areas, 5 BKT slots (2 filled), 6 sample-weight rows, 6
units per timepoint × 3 timepoints, 6 rows in the %Release-from-assay block ×
3 timepoints.

## Group map (sheet section → template group)

| Sheet section (rows) | Group key | kind | Notes |
|---|---|---|---|
| Context header (2-15) | `context` fields | context | Generic/Product/TRF/AR/Batch/Condition/Test/Method/Analyst/Instrument/Date |
| Standard detail (17-19) | `standard` | singleton | potency, MW base/salt, weight, dilution chain, conc_ppm |
| Standard areas (B22:B26) | `std_areas` | table (5) | raw replicate areas |
| BKT areas (D22:D26) | `bkt` | table (0-5, dflt 2) | bracketing standard areas |
| Std stats (B27-B29, D27-D29) | `std_stats` | singleton | Mean / pooled Mean / SD / %RSD |
| Dissolution params (I21:J25) | `params` | singleton | Volume mL, Apparatus, RPM, Temp, Media text |
| Sample weights (E/F/G/H 22-30) | `weights` | table (6) | per-unit mg for 1/4/24 hr |
| Sample-weight stats (28-30) | `weight_stats` | singleton | Mean/SD/%RSD per timepoint column |
| Pooled assay + media (31-37) | `prep` | context/singleton | %Assay A32, media A35, pipette B35, VF C35, withdraw/replace A37 |
| %Residue 1 hr @37°C (40-45) | `residue_1hr` | table (6) | area + %Residue + Mean/Min/Max/RSD |
| %Residue 4 hr @55°C (46-51) | `residue_4hr` | table (6) | " (uses G-weights) |
| %Residue 24 hr @55°C (52-57) | `residue_24hr` | table (6) | " (uses H-weights) |
| %Release 1 hr (70-75) | `release_1hr` | table (6) | entered %Residue + release-from-assay + aggregates |
| %Release 4 hr (76-81) | `release_4hr` | table (6) | " |
| %Release 24 hr (82-87) | `release_24hr` | table (6) | " |
| Signatures (89-90) | — | — | handled outside the definition, as in A6B-0001 (no signature group) |

### Context fields (rows 2-15)
Modeled per the A6B-0001 convention: sourced where a source exists, otherwise
`overridable` (so every header box is fillable and passes
`test_no_context_field_is_unfillable`). Display-only header text carries no
formula.

* `generic_name` (B5) source `product.name`; `product_name` (B6 `=B5`) mirror /
  overridable; `trf_no` (B7) source `trf.trf_number`; `ar_no` (B8) source
  `trf.ar_number`; `batch_no` (B9) source `trf.batch_number`;
  `stability_condition` (B10), `test_performed` (B11 "In Vitro Release"),
  `analysis_as_per` (B12 "In house"), `analysed_by` (B13) source
  `session.analyst`, `instrument_id` (B14), `date_of_analysis` (B15) source
  `session.date`. All overridable.

## Acceptance criteria (template `criteria` array) — RESOLVES review findings 1 & 2

The sheet itself prints **no numeric acceptance limit**: there is no rows-27-32
SST item list (unlike the Doxorubicin A6B-0001 sheet), and the %Release block
(rows 70-87) carries no spec-limit column at all — the Octreotide sheet has no
`spec_limit` cell anywhere. The only computed quantity that maps to a standard,
universally-applied HPLC system-suitability limit is the **standard-replicate
%RSD** (B29 = `std_stats.rsd_std`), for which "NMT 2.0 %" is the conventional
SST bar A6B-0001/A6A/A6C all encode via `sst_rsd_criterion()`.

**Decision (option a):** carry exactly one blocking criterion — the standard
replicate %RSD SST — and nothing else, because that is the only machine-checkable
limit with a defensible, non-invented threshold and it is the shared convention
across every seeded dissolution template:

```python
"criteria": [
    sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0),
]
```

This yields `limitText="NMT 2.0 %"`, `operator=lte`, `severity=blocking`
(the `sst_rsd_criterion` defaults in `_common.py`).

**Group-name/target coupling (finding 2), LOCKED:** `sst_rsd_criterion()`
defaults to `target="stats.rsd_std"`, which is A6B-0001's group name. This
template deliberately renames the standard-statistics group to `std_stats`, so
the call **MUST pass `target="std_stats.rsd_std"` explicitly**. A bare
`sst_rsd_criterion()` would target a non-existent `stats.rsd_std` and never
evaluate — the implementer must not copy the A6B-0001 call verbatim.

**Rejected (option b):** `"criteria": []`. The per-timepoint %Release acceptance
in this product's method is applied as free-text spec outside this sheet, so one
could argue the template encodes no limit. Rejected because B29 is a genuine,
computed SST %RSD and leaving the array empty would diverge from the stated goal
of mirroring the A6B-0001 convention without any offsetting benefit. The single
%RSD criterion is both faithful to convention and the only limit we can assert
without inventing a number the sheet does not contain.

## Technology stack (LOCKED)

Python declarative `SeedTemplate` dict; parsed by
`src/domain/services/calculation/template_schema.TemplateDefinition.parse`;
evaluated by `src/domain/services/calculation/evaluator.WorksheetEvaluator`.
Expression engine functions used: `mean`, `sd`, `rsd` (not used; %RSD written
explicitly to match the sheet's `SD*100/Mean`), `min`, `max`, `pool`, `number`.
Seeded through `scripts/seed_test_templates.py` (`ensure_test` + additive
insert). Parity asserted in
`tests/calculation/test_seeded_template_parity.py`. The `criteria` array holds
the single `sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)` fixed in
the Acceptance-criteria section above. No new runtime dependencies.

## Calculated fields — exact expressions and source cells

Bare field names resolve to the **current row**. Column aggregates MUST use the
qualified series name (`group.field`) — this was verified against the real
evaluator (an unqualified `mean(residue)` returns the row's own value, not the
column). Cross-timepoint per-unit weight lookup uses row-indexing
`weights.w_1hr[rowno - 1]`.

### Standard concentration — J19
Source `J19 = E19/G19*H19/I19*C19/D19*B19/100*1000`.

```
standard.conc_ppm =
  weight_mg / dilution_1 * volume_1 / dilution_2
  * mw_base / mw_salt * potency / 100 * 1000
```
(`weight_mg`=E19=25.65, `dilution_1`=G19=25, `volume_1`=H19=5,
`dilution_2`=I19=50, `mw_base`=C19=1, `mw_salt`=D19=1, `potency`=B19=89.41.)
**Gold J19 = 91.73466.**

### Standard area statistics — B27/B28/B29, D27/D28/D29
```
std_stats.mean_std = mean(std_areas.area)                       # B27 AVERAGE(B22:B26)
std_stats.sd_std   = sd(std_areas.area)                         # B28 STDEV(B22:B26)
std_stats.rsd_std  = sd(std_areas.area) * 100 / mean_std        # B29 =B28*100/B27
std_stats.mean_bkt = mean(pool(std_areas.area, bkt.area))       # D27 AVERAGE(B22:B26,D22:D26)
std_stats.sd_bkt   = sd(pool(std_areas.area, bkt.area))         # D28 STDEV(B22:B26,D22:D26)
std_stats.rsd_bkt  = sd(pool(std_areas.area, bkt.area)) * 100 / mean_bkt  # D29 =D28*100/D27
```
**Gold:** B27 = 3035052.8; B29 = 0.20177293603399474; D27 =
3035369.2857142859; D29 = 0.16659794279279921. (Pooled mean uses `pool(...)` to
reproduce `AVERAGE(B22:B26,D22:D26)` over 7 values.)

### Sample-weight statistics — F28/F29/F30 (and G, H)
Source: `F28=AVERAGE(F22:F27)`, `F29=STDEV(F22:F28)`, `F30=F29*100/F28`.
**Sheet quirk, reproduced deliberately:** the STDEV range `F22:F28` INCLUDES the
mean cell F28. With only units 1-2 filled that yields SD over
`{23.59, 23.9, mean=23.745}` = 0.155, not the SD of the two raw values (0.219).
Prototyped and confirmed against the evaluator:

```
weight_stats.mean_1hr = mean(weights.w_1hr)                                 # F28
weight_stats.sd_1hr   = sd(pool(weights.w_1hr, [mean_1hr]))                 # F29 (incl. mean cell)
weight_stats.rsd_1hr  = sd_1hr * 100 / mean_1hr                            # F30
# identical shape for _4hr (G col) and _24hr (H col)
```
**Gold (1 hr):** Mean 23.745; SD 0.155; %RSD 0.6527690040008397.
**Gold (4 hr):** Mean 24.985; SD 0.145; %RSD 0.58034820892535355.
**Gold (24 hr):** Mean 24.475; SD 0.865; %RSD 3.5342185903983667.

### %Residue of Octreotide Base — K40..K57 (= C40..C57)
On the sheet `C40==K40`, so the K-column holds the real formula and C just
mirrors it. We compute it directly as the per-unit field. Source K40:
```
K40 = B40/$B$27*$E$19/$G$19*$H$19/$I$19*$C$35/$B$35*$A$35/$F22*$B$19*$C$19/$D$19
```
Template (1 hr block; `$F22`=that unit's 1 hr weight by row):
```
residue_1hr.residue =
  area / std_stats.mean_std
  * standard.weight_mg / standard.dilution_1
  * standard.volume_1 / standard.dilution_2
  * vf_vol / pipette_vol
  * media_vol / weights.w_1hr[rowno - 1]
  * standard.potency * standard.mw_base / standard.mw_salt
```
Mapping: `$E$19`=weight_mg, `$G$19`=dilution_1, `$H$19`=volume_1, `$I$19`=
dilution_2, `$C$35`=vf_vol(V.F. Vol=1), `$B$35`=pipette_vol(=1), `$A$35`=
media_vol(=10), `$F22..$F27`=weights.w_1hr per unit, `$B$19`=potency,
`$C$19`=mw_base, `$D$19`=mw_salt.
The 4 hr block is identical but reads `weights.w_4hr[rowno-1]` (`$G22..$G27`);
the 24 hr block reads `weights.w_24hr[rowno-1]` (`$H22..$H27`).

**Gold (1 hr):** B40=3152088 → K40 = 4.0386628322462599; B41=3270742 →
K41 = 4.136333922855612.
Per-block aggregates (`AVERAGE/MIN/MAX(C40:C45)`, `STDEV(C40:C45)*100/Mean`,
blanks excluded):
```
residue_1hr.mean  = mean(residue_1hr.residue)          # D40 = 4.0874983775509364
residue_1hr.min_v = min(residue_1hr.residue)           # E40 = 4.0386628322462599
residue_1hr.max_v = max(residue_1hr.residue)           # F40 = 4.136333922855612
residue_1hr.rsd   = sd(residue_1hr.residue) * 100 / mean   # G40 = 1.6896371353947515
```
**Gold (4 hr):** B46=2351327 → K46 = 2.8280543211589846; D46 =
2.8295742711996321; G46 = 0.07596669165011731.
**Gold (24 hr):** B52=1622756 → K52 = 1.9355919975161624; D52 =
1.8876063496116782; G52 = 3.5951327499900718.

### L column — L40..L87 (per-withdrawal replace fraction)
Source `L40 = IF(K40="","", K40*$A$37/$A$35)` = K × (withdraw/replace ÷ media
vol) = K × 1/10. This is an intermediate feeding only the M carry-over column
(see below). Because the M chain is a **dead/error path on this sheet** (next
section), L and M are NOT modeled as reportable template fields. They are
documented here for completeness only. If a future revision needs the carry-over
made live, model L as `residue_*.l = residue / 10 * withdraw_replace` and M as a
`sequence`-group cumulative sum as in A6B-0001 — but that would change the
sheet's own (broken) behavior and must be a lab decision, not an author guess.

### %Release of Octreotide Base — the K64 path is DEAD; use the C70 path

**Resolved ambiguity (the brief's F19/G19 question).** The brief asked to trace
the %Release `K64` formula's use of `$E$19/$F$19*$G$19/$I$19` and the `/$A$32`
normalization. Reading the real xlsx:

* **F19 is EMPTY** (E18:F18 and E19:F19 are merged cells; the value lives in E19,
  F19 is blank). So `K64 = .../$F$19/...` divides by blank → the sheet's own
  cached value for `K64` is literally `#VALUE!` (cell type `t="e"`). Likewise
  K72:K75 and the entire M70+ cascade (M70 = L64+M64, and L64 is `#VALUE!`) are
  `#VALUE!` in the source workbook.
* **B64:B69 hold the block's header/label text and no per-unit area inputs were
  entered** — `B64` is a shared-string cell (`t="s"`, the "%Residue of Octreotide
  Base" column header), not an empty cell; the per-unit area inputs that would
  feed K64 were never populated. So, combined with the empty `$F$19` divisor,
  `K64` is cached `#VALUE!` (cell `t="e"`), and even ignoring the F19 bug the
  block has no inputs.

Conclusion: the rows 58-69 "%Release of Octreotide Base" area-driven block is a
**broken, unused scaffold** in the source. Reproducing a `#VALUE!` is not a
meaningful template output, so this block is **omitted** from the template
(documented, not silently dropped). This decision is forced by the real
evaluator/xlsx evidence, not a guess.

**The live %Release presentation is the rows 70-87 block**, which takes
*manually entered* %Residue values (B70=4.04, B71=4.14, B76=2.83, B77=2.83,
B82=1.94, B83=1.84) and computes release-from-assay:
Source `C70 = ($A$32 - B70) / ($A$32) * 100` (A32 = %Assay of blend = 4.12).
```
release_1hr.residue_in = <input>                                   # B70..B75
release_1hr.rel = (number(pct_assay) - residue_in) / number(pct_assay) * 100   # C70
release_1hr.mean  = mean(release_1hr.rel)      # D70
release_1hr.min_v = min(release_1hr.rel)       # E70
release_1hr.max_v = max(release_1hr.rel)       # F70
release_1hr.rsd   = sd(release_1hr.rel) * 100 / mean   # G70
```
`pct_assay` (A32=4.12) is a context/prep input, overridable.
**Gold (1 hr):** B70=4.04 → C70 = 1.9417475728155356; B71=4.14 →
C71 = -0.48543689320387312; D70 = 0.72815533980583125; E70 =
-0.48543689320387312; F70 = 1.9417475728155356; G70 = 235.70226039551304.
**Gold (4 hr):** B76=2.83 → C76 = 31.310679611650489; D76 = 31.310679611650489;
G76 = 0.
**Gold (24 hr):** B82=1.94 → C82 = 52.912621359223301; B83=1.84 →
C83 = 55.339805825242728; D82 = 54.126213592233015; G82 = 3.1708824268455151.

The 4 hr (`release_4hr`, rows 76-81) and 24 hr (`release_24hr`, rows 82-87)
blocks are identical in shape.

## Error handling and validation per input

All numeric inputs are optional at the field level (an unentered unit is a blank
in the aggregate, which is exactly how the sheet behaves — AVERAGE/STDEV skip
blanks). The engine's semantics do the error handling:

* **Blank input** → `EMPTY` propagates; aggregates exclude it; no exception. This
  is the designed, recoverable path (a partially filled sheet with 2 of 6 units
  entered still computes a valid 2-unit mean, matching the source).
* **Division by blank / zero** (e.g. a unit's weight left blank while its area is
  entered) → the chain yields `EMPTY`/non-finite and the unit drops out of the
  aggregate; non-fatal, surfaced as a blank cell. The sheet's own `IF(B="","",…)`
  guard is equivalent.
* **Non-numeric context used as divisor** — `pct_assay` and `label-claim`-style
  divisors are wrapped with `number(...)` so a free-text value cannot silently
  blank the whole column (mirrors A6B-0001's `number(label_claim)` guard).
* **Circular reference** → `WorksheetEvaluator` raises `EvaluationError` at
  evaluate time; caught by the seeder's `validate()` dry-run before anything is
  written (fatal, reported to whoever runs the seed).
* **Invalid expression / unknown function** → `ExpressionError` →
  `EvaluationError` at parse/evaluate, same pre-write gate.

Validation rules per external input:

| Input | required | type | limits | on failure |
|---|---|---|---|---|
| standard weight/dilutions/potency | first weight required | number | >0 (divisors) | blank → column blanks (sheet-equivalent) |
| std_areas.area (×5) | optional | number | ≥0 | blank excluded from Mean/%RSD |
| bkt.area (×0-5) | optional | number | ≥0 | blank excluded from pooled Mean/%RSD |
| weights.w_1/4/24hr | optional | number | >0 (denominator) | blank → that unit's residue blanks |
| pct_assay (A32) | overridable, default 4.12 | number | >0 (divisor) | `number()`-guarded |
| media_vol/pipette_vol/vf_vol/withdraw_replace | default 10/1/1/1 | number | >0 | defaults match sheet |
| residue_in (release blocks) | optional | number | any | blank excluded from aggregates |

Invariant ownership: the "aggregate excludes blanks" invariant is owned by the
expression engine (`_f_mean`/`_f_sd` drop `EMPTY`), not re-implemented per field
— so it cannot drift between timepoint blocks. The "divisor must be numeric"
invariant is owned at the field level via `number(...)` on context divisors.

## Testability

* **Unit-testable (parity) via `WorksheetEvaluator`:** every calculated field —
  J19, B27/B29, D27/D29, the three weight-stat triples, the three %Residue
  blocks (K + Mean/Min/Max/RSD), and the three %Release-from-assay blocks. All
  gold values above are hand-derived from the sheet formulas and independently
  confirmed against the live xlsx cached values, so the parity test is a true
  oracle (not a snapshot of current code). This is the GxP acceptance bar.
* **Integration-testable:** seed via `scripts.seed_test_templates`
  (`--validate-only` then real seed), confirm the new `TPL-A6B-0002` row and the
  new `TST-DISS-OCT-PH10` Test Master row exist and parse/dry-run clean.
* A design that was hard to test would be one that tried to reproduce the
  `#VALUE!` K64 path; dropping that dead block is part of what keeps the template
  deterministically testable.

## Full gold-value set to assert (parity oracle)

Derived by hand from the sheet formulas, confirmed against the xlsx cached
values and re-confirmed through the real `WorksheetEvaluator` in prototyping
(all matched to ≤1e-4 relative):

| Cell | Field | Gold value |
|---|---|---|
| J19 | standard.conc_ppm | 91.73466 |
| B27 | std_stats.mean_std | 3035052.8 |
| B29 | std_stats.rsd_std | 0.20177293603399474 |
| D27 | std_stats.mean_bkt | 3035369.2857142859 |
| D29 | std_stats.rsd_bkt | 0.16659794279279921 |
| F28/F29/F30 | weight_stats 1hr Mean/SD/%RSD | 23.745 / 0.155 / 0.6527690040008397 |
| G28/G29/G30 | weight_stats 4hr | 24.985 / 0.145 / 0.58034820892535355 |
| H28/H29/H30 | weight_stats 24hr | 24.475 / 0.865 / 3.5342185903983667 |
| K40 | residue_1hr.residue[0] (B40=3152088) | 4.0386628322462599 |
| K41 | residue_1hr.residue[1] (B41=3270742) | 4.136333922855612 |
| D40/E40/F40/G40 | residue_1hr Mean/Min/Max/RSD | 4.0874983775509364 / 4.0386628322462599 / 4.136333922855612 / 1.6896371353947515 |
| K46 | residue_4hr.residue[0] (B46=2351327) | 2.8280543211589846 |
| D46/G46 | residue_4hr Mean/RSD | 2.8295742711996321 / 0.07596669165011731 |
| K52 | residue_24hr.residue[0] (B52=1622756) | 1.9355919975161624 |
| D52/G52 | residue_24hr Mean/RSD | 1.8876063496116782 / 3.5951327499900718 |
| C70 | release_1hr.rel[0] (B70=4.04) | 1.9417475728155356 |
| C71 | release_1hr.rel[1] (B71=4.14) | -0.48543689320387312 |
| D70/E70/F70/G70 | release_1hr Mean/Min/Max/RSD | 0.72815533980583125 / -0.48543689320387312 / 1.9417475728155356 / 235.70226039551304 |
| C76 | release_4hr.rel[0] (B76=2.83) | 31.310679611650489 |
| D76/G76 | release_4hr Mean/RSD | 31.310679611650489 / 0 |
| C82 | release_24hr.rel[0] (B82=1.94) | 52.912621359223301 |
| C83 | release_24hr.rel[1] (B83=1.84) | 55.339805825242728 |
| D82/G82 | release_24hr Mean/RSD | 54.126213592233015 / 3.1708824268455151 |

## resultRef note

The sheet has no single "reportable result" cell; it reports three timepoint
means per section. `resultRef = "residue_24hr.mean"` (the final live %Residue
timepoint) is chosen as the single scalar the engine surfaces, consistent with
the evaluator's first-non-blank-of-the-group behavior
(`WorksheetEvaluator._extract_result` iterates rows forward and returns the
first non-EMPTY value). Since `mean` is a column aggregate identical on every
row of the block, first == last == the 24 hr %Residue mean (1.8876…), so the
choice of row is immaterial. It is a reporting convenience; the parity test
asserts every block, not just this ref.

## Deliberately NOT reproduced (documented)

1. **The rows 58-69 area-driven "%Release of Octreotide Base" block** — `K64`
   divides by the empty `F19` cell and `B64:B69` hold only header/label text with
   no per-unit area inputs, so the source's own cells are `#VALUE!` (`t="e"`).
   Omitted as a broken, unused scaffold. The live %Release presentation (rows
   70-87, residue-from-assay) IS reproduced.
2. **The L/M carry-over columns** — L is an intermediate; M (M46→M52→M64→M70…) is
   the cumulative replacement running sum, but its continuation into the %Release
   rows is `#VALUE!` on the sheet (fed by the dead K64 path). Since no reportable
   value on the sheet depends on a live M, the cumulative chain is not modeled.
   Re-enabling it would require changing the sheet's own behavior and is a lab
   decision, not an author guess.
3. **Signature block (rows 89-90)** — handled outside the definition, matching
   A6B-0001 (no signature group in the template body).

## Files to touch (implementation phase, not this step)

* `scripts/template_definitions/a6_dissolution.py` — add `A6B_OCT_*` builders +
  `A6B_OCT = SeedTemplate(code="TPL-A6B-0002", ...)`; append to `TEMPLATES`.
  (A6A/A6B/A6C/-0001 siblings unchanged.)
* `tests/calculation/test_seeded_template_parity.py` — new parity class asserting
  the full gold set above.
* Seed into `lims.db` via `scripts.seed_test_templates` (additive; `ensure_test`
  creates `TST-DISS-OCT-PH10`). A pre-seed DB backup already exists per
  `backup.md`.

## Responses to design review

Review: `design-review.md` / `design-review.json` — verdict CHANGES_REQUESTED
(0 HIGH, 2 MEDIUM, 3 NIT). All five findings addressed below.

1. **MEDIUM — criteria array never specified. ADDRESSED.** Added the
   "Acceptance criteria" section. Chose option (a): one blocking criterion,
   `sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)` (standard-replicate
   %RSD, NMT 2.0 %), the only machine-checkable limit on the sheet and the shared
   convention across A6A/A6B/A6C. Option (b) empty-criteria is documented as the
   rejected alternative with reasoning. Aligns with the original requirement to
   mirror A6B-0001 conventions.

2. **MEDIUM — default `sst_rsd_criterion()` target mismatches renamed group.
   ADDRESSED.** The Acceptance-criteria section LOCKS the explicit
   `target="std_stats.rsd_std"` and states the group-name/target coupling plus an
   explicit warning not to copy A6B-0001's bare call. The Technology-stack
   paragraph now also names the criterion.

3. **NIT — resultRef prose said "last non-blank" but engine returns first.
   ADDRESSED.** Reworded the resultRef note to "first-non-blank-of-the-group,"
   noting first == last because `mean` is row-constant. `resultRef` unchanged
   (`residue_24hr.mean`).

4. **NIT — "B64:B69 are blank" imprecise (B64 is a header string).
   ADDRESSED.** Reworded both the dead-path section and the "Deliberately NOT
   reproduced" item to "header/label text, no per-unit area inputs; K64 cached
   `#VALUE!` (`t="e"`)." Conclusion unchanged.

5. **NIT — `mirrorFrom`/`hidden` keys are renderer-only, ignored by the calc
   engine. ACKNOWLEDGED, no change needed.** This design does not use
   `mirrorFrom`/`hidden`; the release/residue blocks are self-contained (each
   timepoint table carries its own `residue_in` input and its own aggregates), so
   there is no dangling mirror source. Implementation will keep them
   self-contained and will NOT add a `mirrorFrom` pointing at the omitted
   rows-58-69 block.
