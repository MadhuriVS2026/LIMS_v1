# Design Review — Dissolution-Leuprolide-microsphere (TPL-A6A-0005, archetype A6a)

Reviewed: `d:\RD-instance\GIT\.agents\tasks\a6a-leuprolide-microsphere\design.md`
Against: `trace.md` (authoritative formula map + gold values) and
`backend-v2/scripts/template_definitions/a6b_octreotide_ph10.py` (proven pattern).
Engine facts independently verified against source under
`backend-v2/src/domain/services/calculation/`.

This review was done fresh, without the context that produced the design. Every
formula mapping, engine claim, and gold value cited by the design was checked
against the actual source where source exists.

---

## Verdict inputs

Mechanical count of blocking findings: **0 HIGH, 0 MEDIUM.** NIT findings only.
Verdict: **APPROVED.**

---

## Findings

### 1. [NIT] `volume_ml` label/range wording for the `params` group cites rows "21-27" but H/I content is rows 22-27
Location: §4 "Dissolution parameters — `params` singleton (sheet rows 21-27, H/I cols)" and §Summary "params (H21:I25…)".
The trace places the dissolution parameters at I22..I25 with media at H26/H27. The design header says "rows 21-27" and the summary says "H21:I25". This is a cosmetic cell-range annotation, not a field or formula defect — all five field cells (I22/I23/I24/I25/H26-H27) are individually correct and the media cell range matches the trace.
Concrete fix: change the group header annotation to "(sheet rows 22-27, H/I cols)" and the summary line to "params (I22:I25 + media H26/H27)". No field change.

### 2. [NIT] `sd_bkt` / `rsd_bkt` and `mean_bkt` are displayed but the trace does not pin their gold values individually in the design's §5 footer for the pooled SD
Location: §3 `std_stats` and the gold-value footer (`D28 = 6388.745720231615`, `D29 = 0.5793656650407342`).
The design's own gold footer DOES carry D28/D29 (verified present in the truncated tail), so this is complete. The only nit is that the `std_stats` group table in §3 references these as "computed and displayed" without restating they are parity-pinned; a reader skimming §3 alone might not realize D27/D28/D29 are asserted. This does not affect correctness — the expressions `mean/sd(pool(std_areas.area, bkt.area))` are faithful to the comma-range `AVERAGE/STDEV(B22:B26,D22:D26)`.
Concrete fix: add a one-line cross-reference in §3 ("D27/D28/D29 parity gold: 1102713.9 / 6388.7457… / 0.57936…, see gold set"). Optional.

### 3. [NIT] Registration placement prose is correct but slightly indirect
Location: §Identity "Registration" paragraph.
The design says splice `*_A6A_LEUP` "immediately after `*_A6`" which "places it before `*_A6B_OCT`". Verified against the actual `SEED_TEMPLATES` list in `scripts/template_definitions/__init__.py` — current order is `…, *_A4_A5, *_A6, *_A6B_OCT, *_A6D, …`, so "after `*_A6`, before `*_A6B_OCT`" is exactly right. The nit is only that stating both the import line and the splice line verbatim would remove any ambiguity for the coder.
Concrete fix: show the two exact lines to add:
```python
from scripts.template_definitions.a6a_leuprolide_microsphere import TEMPLATES as _A6A_LEUP
# …then in SEED_TEMPLATES, between *_A6 and *_A6B_OCT:
    *_A6,
    *_A6A_LEUP,
    *_A6B_OCT,
```

---

## Gate checklist (as requested)

All required gate items were checked and PASS:

- **I19 Concentration(ppm) chain** — PASS. Design expression
  `weight_mg/dilution_1*volume_1/dilution_2*mw_base/mw_salt*potency/100*1000`
  maps term-for-term to sheet `=E19/F19*G19/H19*C19/D19*B19/100*1000`
  (E19=weight_mg, F19=dilution_1, G19=volume_1, H19=dilution_2, C19=mw_base,
  D19=mw_salt, B19=potency). Gold `78.726628` consistent with
  `20.11/50*5/25*1*97.87/100*1000`. The standard group correctly assigns
  dilution_1=50 (F19), volume_1=5 (G19), dilution_2=25 (H19).

- **Pooled standard + BKT Mean (pool)** — PASS. `mean_bkt =
  mean(pool(std_areas.area, bkt.area))` reproduces `D27 =
  AVERAGE(B22:B26,D22:D26)` (10 values → gold 1102713.9). `_f_pool` verified to
  flatten ranges and drop blanks, matching Excel comma-range semantics.

- **%RSD formulas** — PASS. `rsd_std = sd(std_areas.area)*100/mean_std` ≡ `B29 =
  B28*100/B27`; `rsd_bkt = sd(pool…)*100/mean_bkt` ≡ `D29 = D28*100/D27`;
  `rsd_wt = sd_wt*100/mean_wt` ≡ `F30 = F29*100/F28`; per-block `rsd =
  sd(U)*100/mean` ≡ `G = STDEV(C..C+5)*100/D`. All faithful.

- **Pellet-weight STDEV-includes-mean quirk** — PASS. `sd_wt =
  sd(pool(weights.weight, [mean_wt]))` reproduces `F29 = STDEV(F22:F28)` (range
  includes the mean cell). `_f_pool` keeps 3 filled weights + mean cell = n=4;
  gold `F29 = 0.569229498728081`. This is NOT a plain `sd(weights.weight)`, as
  required, and matches the Octreotide module's `sd(pool(weights.w_1hr,
  [mean_1hr]))` pattern exactly.

- **L/K cumulative add-back chain** — PASS, resolved precisely.
  - First timepoint: `unit_1 = jassay_1 + sum(prior.kfrac_1)`; on row 1
    `prior.kfrac_1` is empty and `_f_sum` returns 0 (verified in
    `expression.py::_f_sum`, which is explicitly documented for the first
    dissolution row), so `unit_1 = jassay_1 = J` ≡ `C40 = J40`. No L. Correct.
  - `kfrac_u = jassay_u * prep.withdraw_replace / prep.media_vol` ≡ `K =
    J*A37/A35`. Correct.
  - Later rows: `unit_b = jassay_b + sum(prior.kfrac_u) = J + Σ K[1..b-1] = J +
    L` ≡ `C46 = J46 + L46` (L46=K40) and `C52 = J52 + L52` (L52=K46+L46).
    Correct.
  - The design correctly chose the non-recursive `sum(prior.*)` form over the
    recursive `prev.carry` form, and the rationale is independently verified:
    `_evaluation_order` (lines 206-269) DOES `continue` (skip) any path rooted at
    `row`/`prev`/`prior`, so a `prev.carry` field gets no ordering edge and could
    silently collapse to 0 — the hazard the design describes is real. The chosen
    form `kfrac_u` referencing `jassay_u` creates a real dependency edge
    (verified: qualified/bare same-group refs to calculated fields DO add edges),
    so ordering is forced correctly.
  - **Matches the Octreotide/A6A-0004 approach** — PASS. The DB-pinned parity
    test `tests/calculation/test_dissolution_a6a_release.py` uses exactly
    `unit_N = round(uncorrected_N + sum(prior.correction_N), 0)` with
    `correction_N = trunc(withdrawal/media*uncorrected_N,3)` and declares the
    three families in three contiguous loops (uncorrected → correction → unit).
    The design mirrors this (jassay → kfrac → unit). The only intentional
    difference (no `round`/`trunc`, full precision) is correct because the
    Leuprolide sheet shows no explicit ROUND/TRUNC on the J/K/L/C chain.

- **Timepoint count and labels** — PASS. Design: 25 blocks at rows 40,46,…,184
  (every 6 rows), 7 real labeled (1/24/48/96/120/144/168 Hr), 18 spare blank.
  Matches trace §4 enumeration exactly (`25 blocks total`, same start rows, same
  7 labels in order). `rows = {min:1, max:25, default:7}` is consistent. All
  blocks covered (default 7 real + spare capacity to 25). Not assumed — taken
  from the trace/dump.

- **Identity** — PASS.
  - Template name / test name EXACTLY `Dissolution-Leuprolide-microsphere` (both
    places). Correct.
  - New `test_code = TST-DISS-LEUP-MS`, explicitly NOT reusing TST-DISS-QC/id22.
    Matches trace §2.
  - `archetype = A6a`. Correct per trace.
  - **"without replacement" naming discrepancy explicitly documented** — PASS.
    §"Archetype-vs-name discrepancy" states the base is named "without
    replacement" but the sheet actually carries a with-replacement cumulative
    add-back; archetype kept A6a to match the base family; mandates restating in
    the module docstring. Thorough.
  - Next free A6A code `TPL-A6A-0005` (-0001..-0004 exist). Matches trace §2.
    (Existence of -0001..-0004 is a DB assertion from the trace; not
    independently re-queried here — see Unverified section.)
  - `result_unit = %`. Matches base A6A unit per trace.

- **Suitability criteria** — PASS. One blocking criterion
  `sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)`. Verified:
  `sst_rsd_criterion` exists in `_common.py` with signature
  `(target="stats.rsd_std", limit=2.0)`, so the explicit `target=` override is
  REQUIRED because the stats group is renamed `std_stats` — the design calls
  this out correctly, matching the Octreotide module's identical note. The
  design also correctly declines to invent limits on D29/F30 (sheet carries no
  numeric limit), documenting them as lab decisions. Consistent with the trace.

- **Full gold-value target list** — PASS and consistent with trace §5:
  I19=78.726628; B27=1108203.6; D27=1102713.9; B28=719.9265934801964;
  B29=0.06496338700579897; D28=6388.745720231615; D29=0.5793656650407342;
  F28=49.833333333333336; F29=0.569229498728081; F30=1.1422665526316007;
  1 Hr block J40=C40=14.996084937889453, C41=16.579857409503386,
  C42=12.701419313269414, D40=14.759120553554084, E40=12.701419313269414,
  F40=16.579857409503386, G40=13.212490048191508; 24 Hr K40=0.29992169875778907,
  L46=K40, J46=50.24003209954843, C46=50.53995379830622; 48 Hr
  K46=1.0048006419909685, L52=1.3047223407487576, J52=74.67562022214923,
  C52=75.98034256289799. Every value in the design matches the trace.

---

## Verified Assumptions

1. `_f_sum` returns `0` for an empty range — VERIFIED in
   `expression.py::_f_sum` (docstring explicitly cites the first dissolution row
   case). This underpins `unit_1 = jassay_1` with no special-casing.
2. `_evaluation_order` skips `row`/`prev`/`prior`-rooted dependency paths —
   VERIFIED in `evaluator.py` lines 206-269 (`if root in ("row","prev","prior"):
   continue`). The design's order-hazard argument for rejecting the recursive
   form is sound.
3. Qualified (`group.field`) and bare same-group references to calculated
   fields DO create ordering edges — VERIFIED (same function), so
   `kfrac_u→jassay_u` and `unit_u→jassay_u`/`kfrac_u` edges exist as claimed.
4. `sd`/`stdev` = sample SD (n-1, Excel STDEV) — VERIFIED
   (`expression.py::_f_sd`, uses `len(nums)-1`).
5. `pool` flattens ranges and drops blanks — VERIFIED (`_f_pool`). So
   `sd(pool(weights.weight, [mean_wt]))` yields n=4 over 3 filled + mean, and
   `mean(pool(std_areas.area, bkt.area))` yields 10 values.
6. The non-recursive `unit_N = ... + sum(prior.correction_N)` pattern with the
   three-contiguous-loop declaration is the DB-pinned A6A-0004 form — VERIFIED
   in `tests/calculation/test_dissolution_a6a_release.py`. The design faithfully
   mirrors it.
7. `sst_rsd_criterion` default target is `stats.rsd_std` — VERIFIED in
   `_common.py`; the explicit `target="std_stats.rsd_std"` is genuinely required.
8. `SEED_TEMPLATES` order is `…, *_A6, *_A6B_OCT, *_A6D, …` — VERIFIED in
   `scripts/template_definitions/__init__.py`; registration placement claim is
   correct.
9. Octreotide module uses `sd(pool(weights.w_1hr, [mean_1hr]))`,
   `mean(pool(std_areas.area, bkt.area))`, renamed `std_stats`, and
   `sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)` — VERIFIED by
   reading `a6b_octreotide_ph10.py`. The design's "same pattern" claims hold.
10. I19/J40/C46/C52 arithmetic — spot-checked against the trace's hand-derived
    values and the sheet formulas; internally consistent.

## Unverified / Wrong Assumptions

1. **DB-only existence of TPL-A6A-0001..-0004 and TST-DISS-QC/id22, and the
   byte-exact backup** — UNVERIFIED by this review. These are DB-state claims
   from the trace (`lims.db` not queried here, per the "do not run builds/tests"
   instruction). The design relies on them for "next free A6A code = -0005" and
   "do not reuse id22". Taken on the trace's authority; no contradiction found.
   Not a finding — the trace is the authoritative source for DB state per the
   task framing.
2. **Trace §4's `prev.unit`-based carry phrasing is superseded** — The trace's
   implementer note phrases the carry as `coalesce(prev.unit_n,0)*A37/A35`. The
   design correctly identifies that this is accurate only at the first add-back
   (where `unit = J`) and diverges once `unit` becomes cumulative, and instead
   builds the add-back from the raw `jassay_u` (`kfrac_u = jassay_u*A37/A35`).
   The gold values are J-based and remain the authority, so the design's
   correction of the trace prose is RIGHT, not a defect. Confirmed: `C52 = J52 +
   (K46+L46)` uses prior K (J-based), and `K46 = J46*A37/A35`, not
   `unit46*A37/A35`. The design's choice is faithful to the sheet.
3. **`resultRef = timepoints_release.mean` returns the first non-blank per-row
   mean (1 Hr block), not the terminal (168 Hr) mean** — The design flags this
   as a known behavior of `_extract_result` for multi-row groups. Independently
   corroborated: `test_evaluator.py::test_multi_row_result_takes_first_non_blank`
   and `test_a12_0003_ampho_parity.py` confirm the engine returns the first
   non-blank per-row value as the reportable. No gold value pins the single
   reportable scalar, so this is consistent with A6A precedent. The design
   correctly classifies it as a lab decision, not a correctness defect — not
   scored as a finding.
