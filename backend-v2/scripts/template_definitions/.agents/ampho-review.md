# Review — "Lipid content Ampho" seed template (TPL-A2-0005)

Verdict: **APPROVED** — no blocking findings.

## Scope reviewed
- New module `backend-v2/scripts/template_definitions/a2_ampho_lipid_content.py`
- Registration in `backend-v2/scripts/template_definitions/__init__.py`
- Source dump `_dumps/Lipid content_ Ampho.txt` (sheet `PTF_142HIN-400-A`)
- Plan `.agents/ampho-plan.md`
- Recorded verification evidence: commit `e7111e7` message
- Shared helper `_common.py` and expression engine function registry

## Verification evidence (read, not re-run)
Commit `e7111e7` records:
- `python -m scripts.seed_test_templates --validate-only` → exit 0, all valid;
  TPL-A2-0005 [A2] 6 groups, 15 inputs, 10 area fields, 27 calculated, 8 criteria.
- Throwaway `WorksheetEvaluator` run on seed defaults: replicate means
  1572872.83 / 451519.0 / 290188.17 / 748650.0; %Assay Cholesterol 125.30,
  Alpha tocopherol 115.10, DSPG 122.70, HSPC 129.86.

Evidence is present and specific, so the full suite was not re-run. Two narrow
spot-checks were run to resolve the GxP-critical formula doubt:
- Cholesterol: `avg/mean * 21.04/100 * 1/1 * 250/1 * 1/52 * 99.68 * 1/1` = **125.298** → 125.30 ✓
- DSPG (exercises MW base/salt): `avg/mean * 34.64/100 * 1/1 * 250/1 * 1/81.6 * 100 * 778.07/801.06` = **122.697** → 122.70 ✓
Both match recorded values exactly.

## Formula correctness (GxP core)
Sheet E56 (Cholesterol):
`=D56/B35 * B22/C22 * D22/E22 * J53/I53 * H53/G53 * F53/G22 * F22 * H22/I22`

Generated `_assay_expression(idx, prefix)` maps field-for-field:
- `avg_area / stats.mean_std_<c>` = D56/B35 (B35 = AVERAGE(B29:B34), the six-injection replicate mean — NOT the pooled BKT mean) ✓
- `standard.weight[idx] / standard.vol1[idx]` = B22/C22 ✓
- `standard.pip1[idx] / standard.vol2[idx]` = D22/E22 ✓
- `sample_prep.vol_j / sample_prep.pip_i` = J53/I53 ✓
- `sample_prep.vol_h / sample_prep.sample_weight` = H53/G53 ✓
- `sample_prep.avg_weight / lc_<c>` = F53/G22 (G = LC) ✓
- `standard.potency[idx]` = F22 (F = Potency) ✓
- `standard.mw_base[idx] / standard.mw_salt[idx]` = H22/I22 ✓

Column-letter shift vs Bupivacaine (F=Potency, G=LC, H=MW Base, I=MW Salt) is
correctly applied. No mid-chain rounding anywhere; Avg Area = (area1+area2)/2 (D56).
Per-row binding uses `coalesce(if(rowno==k+1, <chain k>, blank()), ...)`; `if` is
lazy and `coalesce` returns the single non-blank branch — correct for the flat
4-row layout. All engine functions used (`mean`, `sd`, `rsd`, `pool`, `coalesce`,
`blank`, `if`) are registered in `expression.py`, so no unknown-function failure
is reachable.

## Structural checks
- **Standard table**: two dilution stages only (weight, vol1, pip1, vol2, potency,
  mw_base, mw_salt). No pip2/vol3 third stage, no conc_ppm column. Default rows
  match brief: Cholesterol 21.04/100/1/1/99.68/1/1; Alpha tocopherol
  32.6/250/2/100/96.4/1/1; DSPG 34.64/100/1/1/100/778.07/801.06; HSPC
  86.14/100/1/1/100/1/1. ✓
- **LC**: overridable context `lc_chol/lc_alpha/lc_dspg/lc_hspc` defaults
  52, 0.64, 81.6, 213 (G22..G25), consumed by the %Assay denominator. ✓
- **Replicate/BKT**: transposed tables, 6 replicate default / up to 5 BKT, one
  area column per compound with `labelFrom="standard.name[idx]"`. Pooled stats use
  `pool(std_areas.<c>_area, bkt_areas.<c>_area)` with `mean()/sd()/rsd()`
  (rows 46–48 = AVERAGE/STDEV over B41:B45,B29:B34). ✓
- **Sample table**: flat, pinned min==max==4, one compound per row, compound name
  `standard.name[(rowno - 1)]`. No ratio / cross-set / 2-SET layout. Sample prep
  singleton scalars avg_weight 1, sample_weight 1, vol_h 250, pip_i 1, vol_j 1
  (F53..J53). ✓
- **Criteria**: 8 blocking %RSD criteria, NMT 2.0 %, targeting
  `stats.rsd_std_<c>` and `stats.rsd_pool_<c>` per compound. No %Assay acceptance
  range. ✓
- **Metadata**: code TPL-A2-0005, name "Lipid content Ampho", archetype A2,
  result_unit "%", resultRef `samples.pct_assay`, test_code TST-LIPID-AMPHO,
  test_name "Lipid Content (Ampho) by HPLC", test_type Quantitative. Does NOT
  reuse TST-LIPID-RATIO. ✓

## Additivity / isolation
`git show --stat e7111e7`: only two files changed (+492), the new module and two
`__init__.py` lines (import `_A2_AMPHO`, splice after `_A2_BUPI`). No change to the
Bupivacaine module, any other template, the engine, the schema, or `lims.db`. The
module is committed; the unrelated items in `git status` are pre-existing and out
of scope. ✓

## Docstring
The module docstring traces every table and formula to its sheet cells (header
A5–A17; standard 22–25; replicate 29–34 with Mean/SD/%RSD 35–37; BKT 41–45 with
pooled 46–48; sample prep 53; sample 56–59 incl. E56) and states the structural
decisions (two-stage dilution, LC-as-context, 8 criteria, flat sample table, no
ratio/cross-set/2-SET, no mid-chain rounding). ✓

## Findings
None.
