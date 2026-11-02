# Design — Dissolution-Leuprolide-microsphere (TPL-A6A-0005, archetype A6a)

## Overview

This design specifies a new LIMS test template, **`Dissolution-Leuprolide-microsphere`**,
authored as a formula-exact rebuild of the workbook
`Test types/Dissolution sheet_Leuprolide_Microsphere.xlsx` (sheet `ZEG0572A`,
A1:Q193). The user's verbatim ask is to *copy* the base template
`Dissolution sheet_ without replacement_ QC release-6` (TPL-A6A-0002 v1), rename
it `Dissolution-Leuprolide-microsphere`, and rebind it to a new Test of the same
name. Per the trace note (`trace.md`), TPL-A6A-0002 is a **DB-only seeded row**
(no module exists for it), so the deliverable is a brand-new seed module that
clones the base's *structure* (its `timepoints_release` cumulative-carry
sequence and standard chain) and adapts it to the Leuprolide sheet's actual
constants and its **fixed-media, replace-fraction** carry model.

The implementation target is a new Python module at
`backend-v2/scripts/template_definitions/a6a_leuprolide_microsphere.py`,
registered in `scripts/template_definitions/__init__.py`, following the proven
pattern of `a6b_octreotide_ph10.py` (the closest sibling module: same
Leuprolide-style context header, same standard chain, same STDEV-includes-mean
weight quirk, same per-block Mean/Min/Max/RSD aggregates). **No files under
`backend-v2/src` or `frontend-react` are touched** — this is a data definition
plus its registration only.

The technology stack is **locked**: Python 3.13 seed module producing a
JSON-shaped `dict` definition, consumed by the existing
`src/domain/services/calculation` engine (`WorksheetEvaluator` /
`TemplateDefinition.parse`). The template is seeded with the existing
`python -m scripts.seed_test_templates` tool. No new libraries, no engine
changes.

## Identity (fixed; locked once approved)

| Attribute | Value |
|-----------|-------|
| Template `code` | `TPL-A6A-0005` (next free A6A code; -0001..-0004 all exist) |
| Template `name` | `Dissolution-Leuprolide-microsphere` (EXACT) |
| `archetype` | `A6a` |
| `result_unit` | `%` |
| Bound Test `test_code` | `TST-DISS-LEUP-MS` (NEW; do **not** reuse TST-DISS-QC / id 22) |
| Bound Test `test_name` | `Dissolution-Leuprolide-microsphere` (EXACT) |
| `test_type` | `Quantitative` |

The `SeedTemplate` tail of the module is:

```python
A6A_LEUP = SeedTemplate(
    code="TPL-A6A-0005",
    name="Dissolution-Leuprolide-microsphere",
    archetype="A6a",
    result_unit="%",
    test_code="TST-DISS-LEUP-MS",
    test_name="Dissolution-Leuprolide-microsphere",
    test_type="Quantitative",
    definition=A6A_LEUP_DEFINITION,
)
TEMPLATES = [A6A_LEUP]
```

Registration: add `from scripts.template_definitions.a6a_leuprolide_microsphere
import TEMPLATES as _A6A_LEUP` and splice `*_A6A_LEUP` into `SEED_TEMPLATES`
immediately after `*_A6` (which, in the current order `*_A6, *_A6B_OCT, *_A6D, …`,
places it **before `*_A6B_OCT`** — keeping the A6 family contiguous and the seed
log ordered by archetype). The seeder is additive and idempotent — it skips
existing codes and creates the missing Test by `test_code` via `ensure_test`.

### Archetype-vs-name discrepancy (documented, deliberate)

The base sheet is named *"without replacement"*, and the archetype is kept at
**`A6a`** to match the base family it is copied from. **However, this sheet
actually carries the cumulative replacement add-back** — the L/C columns
(`C46=IF(J46="","",J46+L46)`, `L46=K40`, `L52=K46+L46`, …) implement a
with-replacement running carry. We reproduce the sheet's **actual** formulas (a
live cumulative chain), not the label's implied semantics. The archetype stays
`A6a` to match the base; this discrepancy is called out here and must be
restated in the module docstring so a future reader does not "correct" the carry
away to match the archetype name. This mirrors the precedent set by the
Octreotide module, which also documents where sheet behaviour diverges from its
archetype's naming.

## Carry model — decision

Two axes of choice exist and the implementer must not be left to pick: the
**group layout** (how blocks map to rows) and the **carry expression** (how the
cumulative add-back is computed). Both are decided here.

### Group layout — `sequence`, timepoints-as-rows

1. **Per-timepoint `table` groups, units-as-rows** (the Octreotide
   `a6b_octreotide_ph10.py` pattern): each timepoint is its own 6-row table with
   a companion `_stats` singleton. This is clean but **cannot express a running
   carry across timepoints** — Octreotide only used it because its cumulative M
   column was dead (`#VALUE!`) on the source and thus not modelled.

2. **One `sequence` group, timepoints-as-rows, units-as-columns** (the base
   TPL-A6A-0002 / TPL-A6A-0004 `timepoints_release` pattern): the engine exposes
   `prev.<field>` (immediately preceding row) and `prior.<field>` (all preceding
   rows as a list) to sequence groups, which is exactly what a cross-timepoint
   cumulative carry needs.

**Decision: use the `sequence` group (option 2).** The Leuprolide sheet's
defining feature is a *live* running carry — `L[b,u] = K[b-1,u] + L[b-1,u] =
Σ K[1..b-1, u]`, with `C = J + L`. Only the sequence model can reproduce it
through the engine, and it is precisely the structure the base TPL-A6A-0002 was
copied from. We therefore clone the base's `timepoints_release` sequence and
swap its shrinking-media carry for the sheet's fixed-media replace-fraction
carry (see "Timepoint release group" below).

This makes the data layout **timepoints as the row axis, the 6 dissolution units
as columns** (`unit_1..unit_6`), matching the base. Note this differs from the
Octreotide module's units-as-rows layout; the difference is intentional and
driven by the live carry requirement.

### Carry expression — non-recursive `sum(prior.*)`, NOT recursive `prev.carry`

Within the sequence group, the running add-back `L[b,u] = Σ K[1..b-1, u]` can be
expressed two ways:

- **(A) Recursive `prev`-based running sum:**
  `carry_u = coalesce(prev.carry_u, 0) + coalesce(prev.jassay_u, 0) * A37/A35`.
- **(B) Non-recursive `prior`-sum:** a per-row hidden `kfrac_u = jassay_u *
  A37/A35`, then `unit_u = jassay_u + sum(prior.kfrac_u)`.

**Decision: use form (B), the non-recursive `sum(prior.*)` form.** This is the
pattern the only DB-pinned cumulative-release template (TPL-A6A-0004) actually
uses — confirmed in `tests/calculation/test_dissolution_a6a_release.py`, whose
reported column is `unit_N = round(uncorrected_N + sum(prior.correction_N), 0)`
with a per-row `correction_N` that depends on the *same row's* `uncorrected_N`.
It is also the structure the base TPL-A6A-0002 was copied from.

Form (A) is **rejected** because it carries a silent ordering hazard, confirmed
against the engine. In `evaluator.py::_evaluation_order` (lines ~246-248), any
dependency path rooted at `row`/`prev`/`prior` is **skipped** when building the
field dependency graph. So a `carry_u` whose only references are `prev.*` and
`prep.*` has **no dependency edge to `jassay_u`**; their relative evaluation
order is decided purely by field-declaration order, and each calculated field is
evaluated as a full top-to-bottom pass over all rows before the next field's
pass begins. If `carry_u` is evaluated before `jassay_u`, then on every row
`prev.jassay_u` is still `EMPTY`, `coalesce(…, 0)` yields `0`, and the whole
carry column silently collapses to `0` (so `unit = raw J` at every block) with
no error raised. Only a parity test would catch it.

Form (B) has **no such hazard**: `kfrac_u` references `jassay_u` directly (a real
dependency edge forces `jassay_u` first), and `unit_u = jassay_u +
sum(prior.kfrac_u)` reads an already-complete `kfrac_u` column. `sum` of an empty
range returns `0` (`expression.py::_f_sum`, Excel semantics — explicitly chosen
for exactly this first-row dissolution case), so on row 1 `unit_1 = jassay_1 = J`
(matches `C40 = J40`), and on later rows `unit_b = J + Σ K[1..b-1]` (matches
`C = J + L`). Gold values are identical under both forms (verified:
`C46 = 50.53995379830622`, `C52 = 75.98034256289799`); form (B) simply removes
the fragility for no cost.

## Technology & engine facts relied upon

Confirmed from `src/domain/services/calculation/`:

- Sequence groups expose `prev` (a dict; **`{}` on the first row**) and `prior`
  (per-field lists of preceding rows). `rowno` is **1-based** (`float(row_index + 1)`).
- `sum` of an **empty range returns `0`** (not blank) — `expression.py::_f_sum`,
  a deliberate Excel-semantics choice documented in that function as existing
  precisely for the first row of a dissolution sequence, where
  `sum(prior.correction)` has nothing to add and the result must fall back to the
  uncorrected value. This is why the chosen non-recursive carry form yields
  `unit_1 = jassay_1 = J` on row 1 with no special-casing.
- `_evaluation_order` (lines ~246-248) **skips** any dependency path rooted at
  `row`/`prev`/`prior` when building the field graph. A field that references
  another row's value through `prev`/`prior` therefore gets **no ordering edge**
  from it — the reason the recursive `prev.carry` form is order-fragile and the
  non-recursive `kfrac_u` form (where `unit_u` references same-row `jassay_u` and
  `sum(prior.kfrac_u)` reads an already-complete column) is safe.
- `sd`/`stdev` = sample SD (n-1, Excel `STDEV`); `rsd` = sd/mean*100; `mean`,
  `min`, `max`, `sum`, `pool` map 1:1 to the sheet's `AVERAGE/STDEV/MIN/MAX`.
  `pool(a, [x])` flattens ranges and literal lists, so `sd(pool(col, [mean]))`
  reproduces the STDEV-includes-mean quirk.
- `round` = Excel half-away-from-zero; `trunc` truncates. The Leuprolide sheet
  shows **no explicit ROUND/TRUNC** on I19, the J/K/L/C chain, or the block
  aggregates, so all calculated fields carry **full precision** (no `rounding`
  key) and the parity test asserts against the full-precision gold values in §5
  of the trace. (Display rounding is a presentation concern, not stored.)

## Group map (sheet section → template group)

Groups are listed in sheet order. Field keys are stable; `kind` is `context`,
`input`, `calculated`, or `area`. "Cell" ties each field/expression to its
source cell in sheet `ZEG0572A`.

### 1. Context header — `context` list (sheet rows 2-15)

Display header; **no formulas**. Model like the Octreotide `_context()` — every
box sourced or `overridable` so none renders as a permanently-blank read-only
field.

| key | label | cell | source / default |
|-----|-------|------|------------------|
| `generic_name` | Generic Name | B5 | `product.name` |
| `product_name` | Product Name | B6 | `product.name`, overridable |
| `trf_no` | TRF No. | B7 | `trf.trf_number`, overridable |
| `ar_no` | AR No. | B8 | `trf.ar_number`, overridable |
| `batch_no` | Batch No. | B9 | `trf.batch_number`, overridable |
| `stability_condition` | Stability Condition | B10 | overridable (sheet: "Initial") |
| `test_performed` | Test | B11 | default `In Vitro Release`, overridable |
| `analysis_as_per` | Analysis as per | B12 | default `AD/TATP/220/01`, overridable |
| `analysed_by` | Analysed By | B13 | `session.analyst`, overridable |
| `instrument_id` | Instrument Id. | B14 | overridable (sheet: AD/HPLC/065) |
| `date_of_analysis` (date) | Date of Analysis | B15 | `session.date`, overridable |

### 2. Standard detail — `standard` singleton (sheet rows 17-19)

| key | label | cell | kind / expression |
|-----|-------|------|-------------------|
| `name` (text) | Standard name | A19 | input, default `Leuprolide Acetate` |
| `potency` | Potency (%) | B19 | input, default `97.87` |
| `mw_base` | MW of base | C19 | input, default `1` |
| `mw_salt` | MW of salt | D19 | input, default `1` |
| `weight_mg` | Weight (mg) | E19 | input, default `20.11` |
| `dilution_1` | Dilution-1 (mL) | F19 | input, default `50` |
| `volume_1` | Volume-1 (mL) | G19 | input, default `5` |
| `dilution_2` | Dilution-2 (mL) | H19 | input, default `25` |
| `conc_ppm` | Concentration (ppm) | **I19** | calculated |

**I19 expression** (exact, sheet `=E19/F19*G19/H19*C19/D19*B19/100*1000`):

```
weight_mg / dilution_1 * volume_1 / dilution_2 * mw_base / mw_salt
    * potency / 100 * 1000
```

No `rounding` key (sheet shows no explicit round on I19); parity asserts the
full value `78.726628`.

### 3. Standard + BKT areas and statistics (sheet rows 21-29)

Three groups, mirroring the Octreotide split so the tables carry only entry
columns and the statistics live in a companion singleton:

- **`std_areas`** `table` — B22:B26 raw replicate areas (default 5 rows, max 6),
  one `area` field. Footer references `std_stats.mean_std` / `.sd_std` /
  `.rsd_std`.
- **`bkt`** `table` — D22:D26 bracketing standard areas (default 5 rows; the
  sheet has 5 filled), one `area` field. Footer references the pooled
  `std_stats.mean_bkt` / `.sd_bkt` / `.rsd_bkt`.
- **`std_stats`** `singleton`:

| key | cell | expression |
|-----|------|------------|
| `mean_std` | B27 `=AVERAGE(B22:B26)` | `mean(std_areas.area)` |
| `sd_std` | B28 `=STDEV(B22:B26)` | `sd(std_areas.area)` |
| `rsd_std` | B29 `=B28*100/B27` | `sd(std_areas.area) * 100 / mean_std` |
| `mean_bkt` | D27 `=AVERAGE(B22:B26,D22:D26)` | `mean(pool(std_areas.area, bkt.area))` |
| `sd_bkt` | D28 `=STDEV(B22:B26,D22:D26)` | `sd(pool(std_areas.area, bkt.area))` |
| `rsd_bkt` | D29 `=D28*100/D27` | `sd(pool(std_areas.area, bkt.area)) * 100 / mean_bkt` |

D27/D28/D29 **pool the 5 replicates with the 5 BKT values (10 values total)** —
the `pool(...)` call reproduces the sheet's comma-range AVERAGE/STDEV exactly.

Because the statistics group is named `std_stats` (not the helper default
`stats`), the SST criterion must target `std_stats.rsd_std` explicitly (see
"Acceptance criteria").

### 4. Dissolution parameters — `params` singleton (sheet rows 21-27, H/I cols)

Display inputs only; **none appears in a formula**. Media text is a multi-line
overridable field (long buffer text).

| key | label | cell | default |
|-----|-------|------|---------|
| `volume_ml` | Volume in mL | I22 | `50` |
| `apparatus` (text) | Apparatus | I23 | `Bottle Rotating` |
| `rpm` | RPM | I24 | `6` |
| `temperature` (text) | Temp °C | I25 | `50` |
| `media` (text, multiline, overridable) | Media | H26/H27 | `0.5% W/V PVA IN WATER pH 5.50` |

### 5. Pellet-weight table + stats (sheet rows 21-30, E/F cols)

**`weights`** `table` — "Pellets Weight in mg", one row per Dissolution Unit
(Unit-1..Unit-6; default 6 rows, max 6, `labelFrom` the unit label). Fields: a
text `unit_label` (E22:E27) and the numeric `weight` (F22:F27). Defaults only
the 3 filled values (F22=49.17, F23=50.56, F24=49.77); F25:F27 blank. Footer
references the stats singleton.

**`weight_stats`** `singleton` — reproduces the **STDEV-includes-mean quirk**
exactly as the Octreotide module does:

| key | cell | expression |
|-----|------|------------|
| `mean_wt` | F28 `=AVERAGE(F22:F27)` | `mean(weights.weight)` |
| `sd_wt` | F29 `=STDEV(F22:F28)` *(range includes the mean cell F28)* | `sd(pool(weights.weight, [mean_wt]))` |
| `rsd_wt` | F30 `=F29*100/F28` | `sd_wt * 100 / mean_wt` |

`mean(weights.weight)` averages only the filled rows (engine `mean` ignores
blanks), matching `AVERAGE` over the 3 filled cells → `49.8333…`. The
`pool(weights.weight, [mean_wt])` adds the mean cell into the SD population
(n=4) → `0.569229…`.

### 6. Blend params / media / pipette / V.F. / replace — `prep` singleton (sheet rows 31-37)

| key | label | cell | kind / default |
|-----|-------|------|----------------|
| `avg_weight` | Average weight mg | A32 | input, `100` |
| `label_claim` | Label claim mg | B32 | input, `9.8` |
| `media_vol` | Media volume | A35 `=I22` | calculated `params.volume_ml` (fixed 50) |
| `pipette_vol` | Pipette Vol. mL | B35 | input, `1` |
| `vf_vol` | V.F. Vol. mL | C35 | input, `1` |
| `withdraw_replace` | Sample withdraw/Replace | A37 | input, `1` |

`media_vol` is **calculated from `params.volume_ml`** to reproduce the sheet's
`A35=I22` link (so the fixed 50 cannot drift from the Volume-in-mL input). It is
the fixed media numerator used in every timepoint — media does **not** shrink per
timepoint on this sheet.

### 7. Timepoint release group — `timepoints_release` `sequence`

Reproduces sheet rows 40-189: **25 six-unit blocks** at rows 40, 46, 52, 58, 64,
70, 76, 82, …, 184 (every 6 rows). **7 are real labeled timepoints**; the 18
trailing blocks (rows 82-189) are blank spare template rows.

**Labeled timepoints (exact, from the trace — do not invent):**

| row index (1-based) | A-label | block start row |
|---------------------|---------|-----------------|
| 1 | `1 Hr` | 40 |
| 2 | `24 Hr` | 46 |
| 3 | `48 Hr` | 52 |
| 4 | `96 Hr` | 58 |
| 5 | `120 Hr` | 64 |
| 6 | `144 Hr` | 70 |
| 7 | `168 Hr` | 76 |

**Row geometry:** `rows = {"min": 1, "max": 25, "default": 7, "labelFrom": "time_hr"}`.
Default 7 real timepoints; max 25 to allow the full spare set.

**Fields** (timepoints as rows, 6 units as columns):

- `time_hr` — input text, the timepoint label (`1 Hr`, `24 Hr`, …). Default the 7
  labels above; blank thereafter.
- `area_1 .. area_6` — `area` inputs, the per-unit Sample Area (sheet column B
  within each block). Unit `u` at block row `r` reads B-cell `B[blockstart + u - 1]`.
- `jassay_1 .. jassay_6` — **calculated, hidden**, the raw per-unit %Assay `J`
  (sheet column J). Expression below.
- `kfrac_1 .. kfrac_6` — **calculated, hidden**, this row's replace fraction
  `K = J*A37/A35` (sheet column K). Depends only on the same row's `jassay_u`.
- `unit_1 .. unit_6` — **calculated**, the Cumulative %Release `C` per unit
  (sheet column C). This is the reported value, `unit_u = jassay_u +
  sum(prior.kfrac_u)`. Expression below.
- Per-block aggregates over the 6 `unit_n`: `mean` (D), `min_val` (E),
  `max_val` (F), `rsd` (G).

**Field declaration order (correctness note).** Even though the chosen
non-recursive form is order-robust (`unit_u` has a real dependency edge to
`jassay_u` and reads an already-complete `kfrac_u` column via `prior`), the module
**must** declare the three families in three contiguous loops —
`jassay_1..6`, then `kfrac_1..6`, then `unit_1..6` — matching the proven
TPL-A6A-0004 module (`uncorrected` → `correction` → `unit`). This keeps the
layout identical to the pinned precedent and leaves no room for a future edit to
reintroduce the `prev`-based ordering hazard.

#### %Assay chain (sheet J40 — the per-unit un-carried value)

The sheet J-cell is:

```
J40 = IF(B40="","", B40/$B$27*$E$19/$F$19*$G$19/$H$19*$C$35/$B$35
                     *$A$35/$F$22*$B$19*$C$19/$D$19*$A$32/$B$32)
```

i.e. `area / mean_std * E19/F19 * G19/H19 * C35/B35 * A35/(unit pellet wt)
* B19 * C19/D19 * A32/B32`. Note: **B19 (potency 97.87) enters as a PLAIN
multiplier** here (not `/100`), and **A35 (fixed media 50) is the numerator**
(media does not shrink). Each unit divides by **its own pellet weight**
F22..F27, read by column index from the `weights` table.

The per-unit %Assay `J_u` for unit `u` (1-based), expressed against the engine,
reading unit `u`'s pellet weight by row index `[u-1]`:

```
area_{u} / std_stats.mean_std
  * standard.weight_mg / standard.dilution_1
  * standard.volume_1 / standard.dilution_2
  * prep.vf_vol / prep.pipette_vol
  * prep.media_vol / weights.weight[{u} - 1]
  * standard.potency
  * standard.mw_base / standard.mw_salt
  * prep.avg_weight / prep.label_claim
```

This maps term-for-term: `area/mean_std` = `B/$B$27`; `weight_mg/dilution_1` =
`E19/F19`; `volume_1/dilution_2` = `G19/H19`; `vf_vol/pipette_vol` = `C35/B35`;
`media_vol/weights.weight[u-1]` = `A35/$F(21+u)`; `potency` = plain `B19`;
`mw_base/mw_salt` = `C19/D19`; `avg_weight/label_claim` = `A32/B32`.

This chain is stored as the hidden `jassay_u` calculated field (one per unit).
Because the chain is reused by name (`jassay_u`) rather than textually, the module
builds it once as a Python string `jassay(u)` and emits it into the `jassay_u`
field; `kfrac_u` and `unit_u` then reference `jassay_u` by key (no textual reuse),
giving the real dependency edges the non-recursive form relies on.

#### Replace fraction (sheet K column) — `kfrac_u`, hidden

The sheet's K cell is `K40 = IF(J40="","", J40*$A$37/$A$35)`, i.e. this row's raw
%Assay times the replace fraction `A37/A35`. It depends only on the **same row's**
`jassay_u`:

```
kfrac_{u} = jassay_{u} * prep.withdraw_replace / prep.media_vol
```

`jassay_u * A37/A35` is exactly `K`. A blank `area_u` makes `jassay_u` blank,
which propagates to a blank `kfrac_u` (reproducing the `IF(J40="","", …)` guard).

#### Cumulative %Release (sheet C column) — `unit_u`, reported

The sheet's L column is a running sum of all earlier blocks' K for the same unit
(`L[b,u] = K[b-1,u] + L[b-1,u] = Σ K[1..b-1, u]`), and `C = J + L`:

- 1 Hr block (first row): **no L** → `C40 = J40`.
- 24 Hr: `C46 = J46 + L46` where `L46 = K40`.
- 48 Hr onward: `C52 = J52 + L52` where `L52 = K46 + L46`.

The running L is expressed non-recursively as the sum over all preceding rows'
`kfrac_u`, so no `prev.carry` self-reference is needed:

```
unit_{u} = jassay_{u} + sum(prior.kfrac_{u})
```

On **row 1**, `prior.kfrac_u` is an empty range and `sum` returns `0`
(`expression.py::_f_sum`), so `unit_1 = jassay_1 = J` (matches `C40 = J40`). On a
**later row b**, `sum(prior.kfrac_u) = Σ K[1..b-1, u] = L[b,u]`, so `unit_b = J +
L` (matches `C46 = J46 + L46`, `C52 = J52 + L52`). This is the TPL-A6A-0004
pattern (`unit_N = uncorrected_N + sum(prior.correction_N)`) applied to the
Leuprolide K/J/C columns.

> Divergence from base TPL-A6A-0002, documented: the base's stored
> `timepoints_release` models carry as a recursive `coalesce(prev.carry_n,0) +
> coalesce(prev.unit_n,0)/media * withdrawal` with a **shrinking** `media =
> initial - (rowno-1)*withdrawal`. The Leuprolide sheet differs on two points —
> (1) media is **fixed** at A35 for every timepoint, and (2) the add-back is built
> from the **raw %Assay J** (via `kfrac_u = jassay_u*A37/A35`), not the cumulative
> `unit`. We therefore adopt the non-recursive `sum(prior.kfrac_u)` carry (the
> proven TPL-A6A-0004 form) rather than the base's recursive `prev.carry` form.
> The trace's §4 note phrases the carry as `coalesce(prev.unit_n,0)*A37/A35`; that
> is correct only at the first add-back (where `unit = J`) and diverges once
> `unit` becomes cumulative, which is why the add-back is built from the raw
> `jassay_u`, not `unit_u`. The gold values in §5 of the trace are J-based and
> remain the authority.

#### Per-block aggregates (sheet D/E/F/G on the block-start row, over the 6 C-cells)

With `U = [unit_1, unit_2, unit_3, unit_4, unit_5, unit_6]`:

| key | cell | expression |
|-----|------|------------|
| `mean` | D `=AVERAGE(C..C+5)` | `mean(U)` |
| `min_val` | E `=MIN(C..C+5)` | `min(U)` |
| `max_val` | F `=MAX(C..C+5)` | `max(U)` |
| `rsd` | G `=STDEV(C..C+5)*100/D` | `sd(U) * 100 / mean` |

Blank units (no area entered) are excluded from `mean/min/max/sd` by the engine's
blank handling, matching the sheet's 3-filled 1 Hr block.

#### Result reference

`"resultRef": "timepoints_release.mean"` — the per-timepoint mean %Release, the
natural A6a release result (A6A-0001 uses `timepoints.mean_released`; the base
0002 stored `None`, which we improve on here).

> Reportable-scalar note (not a blocking item): `_extract_result` for a multi-row
> group returns the **first non-blank** per-row value, i.e. the **1 Hr block
> mean**, not the terminal (168 Hr) release. No gold value pins the single
> reportable scalar, so this matches existing A6A precedent and is accepted as-is.
> If the lab later expects the terminal-timepoint mean as the single reportable,
> `resultRef` would need to point at a dedicated field; that is a lab decision to
> confirm, not a correctness defect in this design.

### 8. Signatures (sheet rows ~190+)

Handled outside the definition, matching A6B-0001/0002 — **not** modelled as a
group.

## Acceptance criteria (suitability)

One blocking machine-checkable criterion, the shared A6A/A6B/A6C convention and
the only numeric limit the sheet carries as a suitability gate:

```python
"criteria": [sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)]
```

- **Standard replicate %RSD (B29) ≤ 2.0 %**, severity `blocking`,
  `limitText` "NMT 2.0 %". The `target` **must** be stated explicitly as
  `std_stats.rsd_std` because the statistics group is renamed `std_stats` (a bare
  `sst_rsd_criterion()` defaults to `stats.rsd_std` and would never evaluate).

The pooled bracketing %RSD (D29) and the pellet-weight %RSD (F30) are **computed
and displayed** but are **not** carried as blocking criteria — the sheet shows no
numeric acceptance limit on either, so encoding one would invent a GxP limit the
source does not state. They remain available for a lab-set limit later; the
design flags this as a lab decision rather than guessing a threshold. (If the lab
confirms limits, add `std_stats.rsd_bkt` lte X and `weight_stats.rsd_wt` lte Y as
additional blocking criteria; both expressions already exist.)

## Validation of external inputs

| Field(s) | Rule | On failure |
|----------|------|------------|
| `standard.weight_mg` (E19) | required, numeric, > 0 (divisor-adjacent) | required-field block at entry; a non-numeric value is rejected by the `input`/`area` typing before evaluation |
| `standard.dilution_1/2`, `volume_1` (F19/H19/G19) | numeric, non-zero (divisors in I19 and J chain) | blank/zero → chain evaluates to blank/∞-guarded blank; analyst sees empty result, cannot sign |
| `std_stats.mean_std` (B27) | derived; must be non-zero before any J uses it as divisor | if no standard areas entered, `mean(std_areas.area)` is blank → J blank → release blank (no crash) |
| `weights.weight[u-1]` (F22..F27) | numeric, non-zero per filled unit (divisor in J) | a unit with a blank weight but a filled area yields a blank J for that unit; it is excluded from the block aggregates (matches sheet) |
| `prep.media_vol` (A35) | derived from `params.volume_ml`; non-zero | zero volume blanks the whole J chain |
| `prep.label_claim`, `prep.avg_weight` (B32/A32) | numeric, non-zero (ratio in J) | blank → J blank |
| `timepoints_release.area_u` (B-cells) | optional per unit; numeric when present | blank area → that unit's J/carry/unit blank, excluded from aggregates (reproduces `IF(B40="","",…)`) |
| `timepoints_release.time_hr` | required for a populated row (row label) | row with areas but no label still computes; label is display only |

All divisors are guarded by the engine's blank/empty propagation (a blank
operand yields a blank result rather than an exception), so no explicit
`number()`/`if` guard is required beyond what the chain already encodes. The
sheet's own `IF(B40="","",…)` guard is reproduced by the engine skipping blank
`area_u` rows.

## Invariants and ownership

- **The fixed-media invariant** (A35 is the same 50 for every timepoint) is owned
  by the `prep.media_vol` calculated field (`= params.volume_ml`), not by any
  per-row expression. This guarantees the carry denominator cannot drift between
  timepoints.
- **The running-carry invariant** (`L[b] = Σ K[1..b-1]`) is owned by the
  sequence group's reported `unit_u` field via `jassay_u + sum(prior.kfrac_u)`,
  with the per-row `kfrac_u = jassay_u*A37/A35`. The `sum(prior.*)` form is
  order-independent: `kfrac_u` has a real edge to `jassay_u`, and `unit_u` reads an
  already-complete `kfrac_u` column, so no field-ordering hazard exists (unlike a
  recursive `prev.carry` form, which `_evaluation_order` would leave unordered
  relative to `jassay_u` and could silently collapse to 0). The sequence `kind` is
  what makes `prior` available; a `table` kind would silently lose the carry (the
  engine only exposes `prev`/`prior` to sequence groups). This is the single most
  important structural decision and is why the group **must** be
  `kind: "sequence"`.
- **The STDEV-includes-mean invariant** (F29 ranges over F22:F28) is owned by
  `weight_stats.sd_wt` via `sd(pool(weights.weight, [mean_wt]))`. It is a
  deliberate reproduction of a sheet quirk, not a bug to fix.

## Testability

- **Unit-testable (pure engine, no DB):** a parity test that builds the
  `timepoints_release` sequence with the SAME formulas and feeds the sheet inputs
  through `WorksheetEvaluator(TemplateDefinition.parse(defn)).evaluate(ctx, groups)`,
  then asserts the §5 gold values. This mirrors
  `tests/calculation/test_dissolution_a6a_release.py` (which pins the same
  non-recursive `unit_N = uncorrected_N + sum(prior.correction_N)` form adopted
  here) and is independent of `lims.db`. The per-block carry (L46=K40,
  L52=K46+L46) and the first-row no-carry (C40=J40) are the critical cases to
  pin — specifically assert `C46 = 50.53995379830622` and `C52 =
  75.98034256289799`, which fail loudly if the carry ever collapses to 0.
- **Integration-testable:** `python -m scripts.seed_test_templates --validate-only`
  parses the definition and dry-runs `WorksheetEvaluator(parsed).evaluate({}, {})`;
  it must succeed (no unresolved refs, no cycle) before any seed. Then a seed into
  a scratch DB confirms the new `TPL-A6A-0005` row and the new `TST-DISS-LEUP-MS`
  Test are created and idempotent on reseed.
- The design is testable because every reported value is a pure function of
  entered inputs and other computed fields with no hidden state; the only
  cross-row dependency (`sum(prior.kfrac_u)`) is linear and acyclic (row *n* reads
  only rows `< n`).

## Authoritative gold-value set (single source for implementer + parity test)

All values full-precision from `trace.md` §5 (no stored rounding; display
rounding shown in parentheses).

**Standard concentration**
- `I19 = 78.726628` ppm (≈ 78.73) — `=20.11/50*5/25*1/1*97.87/100*1000`

**Standard area statistics**
- `B27` mean = `1108203.6`
- `D27` pooled mean (10 values) = `1102713.9`
- `B28` = `719.9265934801964`; `B29` = `0.06496338700579897` (≈ 0.06 %)
- `D28` = `6388.745720231615`; `D29` = `0.5793656650407342` (≈ 0.58 %)

**Pellet-weight statistics (STDEV-includes-mean)**
- `F28` = `49.833333333333336` (≈ 49.83)
- `F29` = `0.569229498728081` (n=4, includes mean cell)
- `F30` = `1.1422665526316007` (≈ 1.14 %)

**1 Hr block (first timepoint, C = J; no carry)** — units 1-3 filled, pellet wts
F22=49.17, F23=50.56, F24=49.77:
- `J40 = C40 = 14.996084937889453` (≈ 15.00), area B40=203438
- `J41 = C41 = 16.579857409503386`, area B41=231282
- `J42 = C42 = 12.701419313269414`, area B42=174411
- block aggregates over C40:C42: `D40` mean = `14.759120553554084` (≈ 14.8);
  `E40` min = `12.701419313269414` (≈ 12.7); `F40` max = `16.579857409503386`
  (≈ 16.6); `G40` %RSD = `13.212490048191508` (≈ 13.21)

**24 Hr block (first cumulative add-back, C = J + L; L46 = K40)**
- `K40 = J40*A37/A35 = 0.29992169875778907`; `L46 = K40 = 0.29992169875778907`
- `J46 = 50.24003209954843`, area B46=681560 → `C46 = J46 + L46 = 50.53995379830622`
  (≈ 50.5) — **proves the first add-back**
- `C47 = 54.93604802433009`; `C48 = 43.16740746631347`

**48 Hr block (running L — proves the chain)**
- `K46 = J46*A37/A35 = 1.0048006419909685`
- `L52 = K46 + L46 = 1.3047223407487576`
- `J52 = 74.67562022214923`, area B52=1013055 → `C52 = J52 + L52 = 75.98034256289799`
  (≈ 76.0)

The running L therefore accumulates every prior block's K for that unit:
`L[b,u] = K[b-1,u] + L[b-1,u] = Σ K[1..b-1, u]`, reproduced non-recursively by
`kfrac_u = jassay_u*A37/A35` and `unit_u = jassay_u + sum(prior.kfrac_u)`.

## Scope guard

- Touch only: new module `a6a_leuprolide_microsphere.py` and the two
  registration lines in `scripts/template_definitions/__init__.py`.
- Do **not** modify anything under `backend-v2/src` (resource-management /
  engine) or `frontend-react` — other workflows own those.
- Validate (`--validate-only`) before seeding; the DB backup
  (`lims.db.bak-leuprolide-20261024-220422`, 1,433,600 bytes verified) was taken
  in the trace step.

## Summary of groups

1. `context` (rows 2-15, header — 11 fields)
2. `standard` singleton (rows 17-19, incl. I19 conc_ppm)
3. `std_areas` table (B22:B26)
4. `bkt` table (D22:D26)
5. `std_stats` singleton (B27/B28/B29 + pooled D27/D28/D29)
6. `params` singleton (H21:I25 + media text)
7. `weights` table (pellet weights F22:F27)
8. `weight_stats` singleton (F28/F29/F30, STDEV-includes-mean quirk)
9. `prep` singleton (rows 31-37: avg wt, label claim, fixed media, pipette, V.F., replace)
10. `timepoints_release` sequence (25 blocks, 7 real timepoints, units 1-6 columns,
    J/K-equivalent `jassay`/`kfrac` hidden + cumulative `unit = jassay +
    sum(prior.kfrac)` + per-block Mean/Min/Max/RSD)

**Timepoint count: 25 blocks total (default 7 real labeled timepoints —
1/24/48/96/120/144/168 Hr; 18 trailing spare blocks).**

## Responses to design review (iteration 2)

Review: `design-review.json` → `design-review.md`, verdict **CHANGES_REQUESTED**
(0 HIGH, 2 MEDIUM, 2 NIT). Each finding was re-verified against the actual engine
(`evaluator.py::_evaluation_order` lines ~246-248, `expression.py::_f_sum`) and
the DB-pinned parity test `tests/calculation/test_dissolution_a6a_release.py`
before resolving.

**Finding 1 [MEDIUM] — field-declaration order of the `prev`-based carry is
load-bearing and silent if wrong. ADDRESSED (eliminated).** Confirmed: paths
rooted at `prev`/`prior` are skipped in `_evaluation_order`, so a `prev.carry`
field has no ordering edge and could silently collapse to 0. Rather than mitigate
the hazard with an ordering rule, the design **removes it** by adopting Finding
2's non-recursive form (see below). As belt-and-braces, §7 still mandates the
three contiguous declaration loops (`jassay` → `kfrac` → `unit`) matching the
proven module, and the parity test pins `C46`/`C52`.

**Finding 2 [MEDIUM] — the recursive `prev.carry` form diverges from the proven,
order-independent `sum(prior.*)` pattern. ADDRESSED.** The design now uses the
exact form the DB-pinned TPL-A6A-0004 template uses: a per-row hidden
`kfrac_u = jassay_u * prep.withdraw_replace / prep.media_vol` (real dependency
edge to `jassay_u`) and the reported `unit_u = jassay_u + sum(prior.kfrac_u)`.
`sum` of an empty range returns 0 (`_f_sum`), so row 1 gives `unit = J` and later
rows give `J + Σ K[1..b-1]`. The recursive `carry_u` field is dropped entirely.
Updated sections: "Carry model — decision" (both the layout and the new carry
expression decision), "Technology & engine facts" (added the `_f_sum` and
`_evaluation_order` facts), §7 (`kfrac_u`/`unit_u` subsections), "Invariants",
"Testability", and the gold-value footer. Gold values are unchanged and remain
the parity authority (`C46 = 50.53995379830622`, `C52 = 75.98034256289799`).

**Finding 3 [NIT] — keep `prep.media_vol` calculated (= `params.volume_ml`), not
a duplicated literal. ACKNOWLEDGED, no change.** The design already specifies
`media_vol` as a calculated field to preserve the sheet's `A35=I22` link;
confirmed no cycle (it references only the input `params.volume_ml`, and the
sequence fields reference the qualified `prep.media_vol`, forcing it first).

**Finding 4 [NIT] — registration-placement wording. ADDRESSED (clarified).** The
Identity section now states explicitly that "after `*_A6`" means **before
`*_A6B_OCT`** in the current `SEED_TEMPLATES` order, keeping the A6 family
contiguous.

**Review Unverified #2 (not scored) — `resultRef` returns the first non-blank
per-row mean (1 Hr block), not the terminal timepoint. ACKNOWLEDGED.** Added a
reportable-scalar note under "Result reference" flagging this as matching A6A
precedent and a lab decision to confirm, not a correctness defect. Trace §4's
`prev.unit`-based carry text is correctly superseded by the J-based
(`kfrac`-based) carry, as the review's Unverified #1 agrees.
