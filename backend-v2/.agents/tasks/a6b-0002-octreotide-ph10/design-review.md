# Design Review — TPL-A6B-0002, Dissolution (Octreotide Acetate, pH-10, with replacement)

Reviewed document: `design.md` (round 2 — a prior review raised 2 MEDIUM + 3 NIT,
all marked addressed in the "Responses to design review" section).

Review method: read the design fresh, then independently verified against the
authoritative sources — the cell+formula dump
`_dumps/Dissolution sheet_Octreotide_PH 10.txt` (sheet `42_2-8°C_`, A1:R91), the
reference archetype `scripts/template_definitions/a6_dissolution.py`
(TPL-A6B-0001), the shared helpers `_common.py`, and the real expression /
evaluator engine (`src/domain/services/calculation/expression.py`,
`evaluator.py`). Every gold value in the design was recomputed from the sheet
formulas; the engine-feasibility claims (list literals, `pool`, `number`,
indexed cross-group refs, `rowno`, result extraction) were checked against the
actual engine source.

## Summary verdict

APPROVED — 0 HIGH, 0 MEDIUM, 2 NIT.

Every requirement in the brief is satisfied and every independently checkable
claim held:

1. Every sheet section maps to a concrete template group (group map table is
   complete and each row is defensible).
2. Every calculated field carries an exact expression + source cell matching the
   dump.
3. The K/L/M semantics are resolved with evidence: the %Residue K40 per-timepoint
   unit-weight path, the %Release K64 F19/G19 + `/$A$32` path (shown to be a dead
   `#VALUE!` scaffold), and the WITH-REPLACEMENT M running sum are all analyzed
   correctly.
4. The hand-derived gold set is complete and reproduces to full double precision
   when recomputed from the sheet formulas.
5. Code is `TPL-A6B-0002`; the Test name is EXACTLY `Dissolution-Octreolide-pH-10`
   (including the "Octreolide" misspelling from the user's verbatim request).
6. A6B-0001 conventions are mirrored (criteria style via `sst_rsd_criterion`,
   `result_unit="%"`, signatures handled outside the definition body).

Per the mechanical rule (HIGH+MEDIUM count), 0 blocking findings ⇒ APPROVED.

## Verified assumptions (independently reproduced)

Each value below was recomputed from the sheet formula with raw cell inputs from
the dump; all matched the design's gold figures to full precision.

| Cell / field | Design gold | Recomputed | Match |
|---|---|---|---|
| J19 `conc_ppm` (E19/G19*H19/I19*C19/D19*B19/100*1000) | 91.73466 | 91.73465999999999 | ✓ |
| B27 mean_std `AVERAGE(B22:B26)` | 3035052.8 | 3035052.8 | ✓ |
| B29 rsd_std `B28*100/B27` | 0.20177293603399474 | 0.2017729360339947 | ✓ |
| D27 mean_bkt `AVERAGE(B22:B26,D22:D26)` | 3035369.2857142859 | 3035369.285714286 | ✓ |
| D29 rsd_bkt `D28*100/D27` | 0.16659794279279921 | 0.16659794279279924 | ✓ |
| F28/F29/F30 weight 1hr | 23.745 / 0.155 / 0.6527690040008397 | identical | ✓ |
| G28/G29/G30 weight 4hr | 24.985 / 0.145 / 0.58034820892535355 | identical | ✓ |
| H28/H29/H30 weight 24hr | 24.475 / 0.865 / 3.5342185903983667 | identical | ✓ |
| K40 residue 1hr unit-1 | 4.0386628322462599 | 4.03866283224626 | ✓ |
| K41 residue 1hr unit-2 | 4.136333922855612 | 4.136333922855612 | ✓ |
| D40/E40/F40/G40 1hr block | 4.0874983775509364 / 4.0386… / 4.1363… / 1.6896371353947515 | identical | ✓ |
| K46 / D46 / G46 residue 4hr | 2.8280543211589846 / 2.8295742711996321 / 0.07596669165011731 | identical | ✓ |
| K52 / D52 / G52 residue 24hr | 1.9355919975161624 / 1.8876063496116782 / 3.5951327499900718 | identical | ✓ |
| C70 / C71 release 1hr | 1.9417475728155356 / -0.48543689320387312 | identical | ✓ |
| D70/E70/F70/G70 1hr release block | 0.7281553398… / -0.4854… / 1.9417… / 235.70226039551304 | identical | ✓ |
| C76 / D76 / G76 release 4hr | 31.310679611650489 / 31.3106… / 0 | identical | ✓ |
| C82 / C83 / D82 / G82 release 24hr | 52.9126… / 55.3398… / 54.126213592233015 / 3.1708824268455151 | identical | ✓ |

Engine-feasibility assumptions, verified against engine source:

- **`pool`, `number`, `mean`, `sd`, `min`, `max` exist** — `expression.py`
  `_FUNCTIONS` registers all of them.
- **List-literal expressions and field refs inside `[...]`** (used by the
  weight-stats quirk `sd(pool(weights.w_1hr, [mean_1hr]))`) are a supported,
  established pattern — `a1_assay.py`, `assay.py`, `a4_a5_related_substances.py`,
  and `a2_bupivacaine_lipid_ratio.py` all use `mean([...])` with embedded field
  refs and absolute indices.
- **Indexed cross-group reference `weights.w_1hr[rowno - 1]`** is valid:
  `evaluator._build_scope` exposes every multi-row group as a column dict
  `{field: [values]}`, and seeds `scope["rowno"] = row_index + 1` in every
  group's row scope — so the `residue_1hr` table can index into `weights`.
- **Qualified column aggregate vs bare row ref**: the design's claim that
  `mean(residue_1hr.residue)` (qualified) aggregates the column while a bare
  `mean(residue)` would return the row scalar is correct — `_build_scope`
  `scope.update(current)` makes bare names resolve to the current row.
- **`resultRef` extraction** — `_extract_result` iterates rows forward and returns
  the FIRST non-EMPTY value (the inline comment saying "last non-blank" is stale
  but the design's round-1 NIT #3 already corrected the prose to
  "first-non-blank"; since `mean` is row-constant, first == last ==
  `residue_24hr.mean`). Claim holds.
- **`sst_rsd_criterion` default target** is `"stats.rsd_std"` in `_common.py`, so
  the design's insistence on passing `target="std_stats.rsd_std"` explicitly is
  both necessary and correct — a bare call would target a non-existent group.
- **Identity free**: `TPL-A6B-0002`, `TST-DISS-OCT-PH10`, and the
  `Dissolution-Octreolide-pH-10` name do not appear anywhere in the codebase; the
  seeder's `ensure_test` creates the Test Master row from `seed.test_name`, so the
  user's "tag" lands on the user-visible Test name exactly as required.
- **F19 is a merged-empty cell**: the dump's MERGED list includes `E19:F19`, and
  the standard row writes only `E19=25.65` with F19 blank — consistent with the
  design's claim that `K64 = .../$F$19/...` divides by blank and the sheet caches
  `#VALUE!`. The K64 "dead path" conclusion is well-founded.

## Unverified / wrong assumptions

- **`#VALUE!` cached cell types (`t="e"`) for K64/K72-75 and the M70+ cascade.**
  The design states it read the live `.xlsx` via `zipfile`+XML and saw cached
  `t="e"` error cells. I did not re-open the binary `.xlsx` in this review (worked
  from the dump + engine). However, the structural evidence I *can* see fully
  supports the conclusion: `E19:F19` is merged so F19 is empty, and the K64 chain
  divides by `$F$19`, which forces a non-finite/blank result; the B64:B69 cells
  are header strings in the dump with no area inputs. The decision to OMIT that
  block (rather than reproduce a `#VALUE!`) is sound regardless of the exact cell
  type. Not a blocker; noted only because the `t="e"` detail itself was not
  re-derived here.
- **The M WITH-REPLACEMENT running sum (M52=L46+M46, M64=L52+M52, M70=L64+M64…).**
  The design reads this chain correctly from the dump and argues it is not modeled
  because its continuation into rows 70+ is fed by the dead K64/L64 path and no
  reportable value depends on a live M. I confirmed the formula shapes in the dump
  match the design's description (M46=L40, M52=L46+M46, M64=L52+M52, M70=L64+M64),
  and that M70+ inherits `#VALUE!` from L64. Omission is justified; I did not
  prototype a live M chain because nothing reportable needs it.

## Findings

1. **NIT — stale "last non-blank" comment in `_extract_result` is a latent trap
   for the implementer.** In `evaluator.py` the `_extract_result` docstring/inline
   comment says the reportable result is the "last non-blank value", but the loop
   returns the FIRST non-blank. The design already reworded its own prose
   (round-1 NIT #3) and the choice is immaterial for a row-constant `mean`, so
   there is no correctness issue for THIS template. Concrete note for the
   implementer: do not rely on "last" semantics if a future field on the result
   group is ever row-varying; `residue_24hr.mean` is safe precisely because it is
   identical on every row.

2. **NIT — the weight-stats "quirk" expression deserves an inline code comment at
   implementation time.** `sd_1hr = sd(pool(weights.w_1hr, [mean_1hr]))`
   deliberately reproduces the sheet bug where `STDEV(F22:F28)` includes the mean
   cell F28, inflating/altering the SD (verified: 0.155 with the mean cell vs
   0.219 for the two raw values). This is numerically correct and intentional, but
   it is non-obvious and a future maintainer could "fix" it and silently break
   parity. Concrete fix: carry a one-line comment on each `sd_*` field, e.g.
   `# sheet F29=STDEV(F22:F28) includes the mean cell F28 — pool([mean_*]) reproduces it; do not "simplify".`

No HIGH or MEDIUM findings. The two round-1 MEDIUM items (criteria array
unspecified; renamed-group target mismatch) are fully resolved in the current
design: the "Acceptance criteria" section specifies exactly one blocking
criterion `sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)` and locks the
explicit target with an explicit warning not to copy A6B-0001's bare call.

## Verdict

APPROVED. Zero HIGH/MEDIUM findings. The design is self-contained, every
calculated field is traceable to a source cell with a reproduced gold value, the
K/L/M semantics and the dead K64 path are correctly resolved with evidence, and
the identity, Test tag, and A6B-0001 conventions are exactly as the brief
requires. The two NITs are implementation-time hygiene, not correctness gates.
