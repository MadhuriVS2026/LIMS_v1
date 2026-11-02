# Build Review — Dissolution-Leuprolide-microsphere (TPL-A6A-0005, archetype A6a)

Verdict: **APPROVED** — no blocking findings.

## Scope reviewed
- `backend-v2/scripts/template_definitions/a6a_leuprolide_microsphere.py` (new module + `SeedTemplate` tail)
- `backend-v2/scripts/template_definitions/__init__.py` (registration)
- `backend-v2/tests/calculation/test_a6a_0005_leuprolide_parity.py` (parity oracle)
- Design `design.md`, trace `trace.md` (authoritative formulas + gold values), verification `verification.md`
- Sibling `a6b_octreotide_ph10.py` + `_common.py` for pattern conformity

## Identity — EXACT, confirmed
| Attribute | Required | Module | OK |
|-----------|----------|--------|----|
| Template name | `Dissolution-Leuprolide-microsphere` | same | ✓ |
| Bound Test name | `Dissolution-Leuprolide-microsphere` | same | ✓ |
| test_code | `TST-DISS-LEUP-MS` (new, not reused) | same | ✓ |
| test_type | `Quantitative` | same | ✓ |
| archetype | `A6a` | `A6a` | ✓ |
| code | `TPL-A6A-0005` (next free) | `TPL-A6A-0005` | ✓ |
| result_unit | `%` | `%` | ✓ |

`grep` confirms `TPL-A6A-0005` / `TST-DISS-LEUP-MS` appear only in this module and
its test — no collision, no reuse of `TST-DISS-QC`/id22. Registered exactly once
in `SEED_TEMPLATES` (`*_A6A_LEUP` spliced after `*_A6`, before `*_A6B_OCT`).

## Formula fidelity — every cell traced to source

- **I19 Concentration(ppm)**: `weight_mg/dilution_1*volume_1/dilution_2*mw_base/mw_salt*potency/100*1000`
  — exact shape of `=E19/F19*G19/H19*C19/D19*B19/100*1000`. Independent recompute = 78.726628. ✓
- **Pooled standard stats**: `mean_std`/`sd_std`/`rsd_std` over `std_areas.area` (B27/B28/B29);
  `mean_bkt`/`sd_bkt`/`rsd_bkt` over `pool(std_areas.area, bkt.area)` — reproduces the 10-value
  comma-range AVERAGE/STDEV of D27/D28/D29. Recompute: B27=1108203.6, D27=1102713.9,
  B28=719.9265934801964, D28=6388.745720231615. ✓
- **Pellet-weight SD quirk**: `sd(pool(weights.weight, [mean_wt]))` reproduces the
  STDEV-INCLUDES-MEAN quirk (F29 range F22:F28). Recompute n=4: F28=49.833333333333336,
  F29=0.569229498728081, F30=1.1422665526316007. ✓
- **J/K/L cumulative chain**: per-unit %Assay `jassay_u` matches the J chain (B19 PLAIN
  multiplier, fixed A35 numerator, divides by this unit's pellet weight `weights.weight[u-1]`);
  `kfrac_u = jassay_u*A37/A35` (K); reported `unit_u = jassay_u + sum(prior.kfrac_u)` (C).
  First timepoint: `sum` over empty prior = 0 ⇒ C40=J40. Later: C = J + Σ K[1..b-1] = J + L.
  Independent recompute: C40=14.996084937889453, C46=50.53995379830622 (=J46+K40),
  C52=75.98034256289799 (=J52+(K46+K40)). All match the asserted gold exactly. ✓
- **Per-block aggregates**: `mean`/`min_val`/`max_val`/`rsd` over `[unit_1..unit_6]`
  (D/E/F/G). Recompute over the 3 filled 1 Hr units: D40=14.759120553554084,
  E40=12.701419313269414, F40=16.579857409503386, G40=13.212490048191508. ✓
- **Timepoint blocks**: sequence group `rows={min:1,max:25,default:7,labelFrom:time_hr}`;
  7 real labels `1/24/48/96/120/144/168 Hr`; 18 spare blocks allowed. Matches trace §4. ✓

The non-recursive `sum(prior.kfrac_u)` carry (vs. recursive `prev.carry`) is correctly
chosen and matches the DB-pinned TPL-A6A-0004 pattern; three contiguous declaration loops
(`jassay`→`kfrac`→`unit`) eliminate the `_evaluation_order` ordering hazard. Design's
divergence note (add-back built from raw J, not cumulative unit) is honored in code.

## Parity test — true oracle
The gold values asserted are reproducible by hand from the raw sheet inputs (I
recomputed all of them in a standalone script with no engine involvement, and every
value matched to full precision). The test feeds sheet inputs through
`WorksheetEvaluator(TemplateDefinition.parse(...))` and asserts I19, the standard/BKT
stats, the pellet-weight quirk stats, the full 1 Hr block (units + Mean/Min/Max/RSD),
and the carry-critical C46 and C52. It also asserts the SST criterion exists
(`std_stats.rsd_std`, `lte`, limit `(2.0,)`, `blocking`). This is the correct suitability
gate and the only numeric limit the sheet carries.

## Verification evidence (read, not rerun)
Per `verification.md`: `--validate-only` EXIT 0 (`ok TPL-A6A-0005 [A6a] 9 groups …`);
parity `7 passed`; full `tests/calculation` = `5 failed, 837 passed`, the 5 being the
known pre-existing A6B carryover + worksheet-service auth failures (unrelated, untouched
by this data-only change); seed EXIT 0 with one new Test + one new template row,
idempotent on reseed; canonical JSON byte-equal to the module; exactly one Active
`TPL-A6A-0005` row; TPL-A6A-0002 (id22 / `TST-DISS-QC`) unchanged. DB backup present.

## Non-blocking observations (not findings; honoring approved trade-offs)
- `rsd_bkt` (D29) and `rsd_wt` (F30) are computed/displayed but not gated — sheet carries
  no numeric limit on either; encoding one would invent a GxP limit. Design documents this
  as a deferred lab decision. Correct.
- `resultRef = timepoints_release.mean` resolves to the first non-blank row (1 Hr block
  mean) per `_extract_result`; no gold value pins the single reportable scalar, matching
  A6A precedent. Documented and accepted.
- archetype `A6a` kept despite the base's "without replacement" name while the sheet
  carries a live cumulative add-back; documented in the module docstring to prevent a
  future "correction". Intentional.

## Conclusion
Identity is exact, every formula traces to its source cell, the carry chain is exact and
independently verified, the parity test is a genuine hand-derived oracle covering every
gold value and the suitability criterion, and DB integrity is intact with no disturbed
rows. No reachable correctness, security, or data failure found. **APPROVED.**
