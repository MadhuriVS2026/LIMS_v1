# GxP numeric verification — TPL-A2-0004 (Bupivacaine Lipid Content & Drug-to-Lipid Ratio)

**OVERALL: PASS** — all 19 gold targets reproduce to the sheet's rounding; the DB
row and the module definition are byte-for-byte equal; no blocking SST failure on
this data.

No feature code was changed in this step. A throwaway script loaded the definition,
ran `WorksheetEvaluator(TemplateDefinition.parse(defn)).evaluate(context, groups)`,
and asserted the gold values. The script and its JSON output were deleted afterward.

## Definition source parity (DB vs module)
- DB row: `test_templates.definition WHERE code='TPL-A2-0004'` in
  `backend-v2/lims.db` (`DATABASE_URL=sqlite+aiosqlite:///./lims.db`).
- Module: `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
  → `LIPID_RATIO_DEFINITION`.
- `stored_text == json.dumps(LIPID_RATIO_DEFINITION)` → **True (byte-for-byte equal)**.
- `json.loads(stored_text) == LIPID_RATIO_DEFINITION` → **True (structural equal)**.
- Re-ran the evaluator from the DB definition too; its `drug_lipid.ratio` equals the
  module's to < 1e-12 → **DB_RATIO_MATCHES_MODULE: True**.

## Inputs used (traced to `_dumps/Bupivacaine Lipid _ Drug to lipid Ratio.txt`, sheet `'Lipid '` / `'Drug to Lipid ratio Auto Calc'`)

Context (per-compound label claims G39..G42, Bupivacaine LC L18):
`lc_tri=2, lc_dppg=0.9, lc_chol=4.7, lc_depc=8.2, lc_bupi=13.3`.

Standard Details (rows 18–21, cols B..J):

| Compound | weight | vol1 | pip1 | vol2 | pip2 | vol3 | potency | mw_base | mw_salt |
|---|---|---|---|---|---|---|---|---|---|
| Tricaprylin | 99.1 | 50 | 6 | 100 | 1 | 1 | 100 | 1 | 1 |
| DPPG Na | 46.79 | 50 | 6 | 100 | 1 | 1 | 99.3 | 721.9602 | 744.95 |
| Cholesterol | 28.51 | 100 | 1 | 1 | 1 | 1 | 100 | 1 | 1 |
| DEPC | 49.32 | 100 | 1 | 1 | 1 | 1 | 99.2 | 1 | 1 |

Standard replicate injections — `std_areas`, one row per compound (rows 25–30, cols B/C/D/E):

| Compound | inj_1 | inj_2 | inj_3 | inj_4 | inj_5 | inj_6 |
|---|---|---|---|---|---|---|
| Tricaprylin | 8711513 | 8674291 | 8679908 | 8671826 | 8715229 | 8695954 |
| DPPG Na | 4437526 | 4473096 | 4461331 | 4528571 | 4403707 | 4463992 |
| Cholesterol | 32277247 | 32439471 | 32393636 | 32357224 | 32429381 | 32523530 |
| DEPC | 44369260 | 44366857 | 44211085 | 43613144 | 43626749 | 43893218 |

BKT injections — `bkt_areas`, one row per compound (rows 25–28, cols H/I/J/K; inj_5/6 blank):

| Compound | inj_1 | inj_2 | inj_3 | inj_4 |
|---|---|---|---|---|
| Tricaprylin | 8713270 | 8686255 | 8719164 | 8729929 |
| DPPG Na | 4473297 | 4509972 | 4448498 | 4472750 |
| Cholesterol | 32509936 | 32485699 | 32455877 | 32460029 |
| DEPC | 43884434 | 43979519 | 43323151 | 44269558 |

Sample batch `EP20_117-299-B` (rows 39/43), inj-1 areas only (inj-2 blank → %Mean = inj-1):
`avg_weight(H39)=1.005, sample_weight(I39)=1.5008, vol_j(J39)=25, pip_k(K39)=1, vol_l(L39)=1`;
`tri_area1(M39)=8729574, dppg_area1(M40)=3826195, chol_area1(M41)=32474189, depc_area1(M42)=44235393`.
Drug-to-Lipid batch B: `pct_assay_bupi(K18)=99.9`.

## Computed vs expected (all targets)

| Target | Computed | Expected | Pass | Note |
|---|---|---|---|---|
| Std Conc ppm — Tricaprylin | 118.92 | 118.92 | ✅ | exact |
| Std Conc ppm — DPPG | 54.03 | 54.03 | ✅ | exact |
| Std Conc ppm — Cholesterol | 285.1 | 285.1 | ✅ | exact |
| Std Conc ppm — DEPC | 489.25 | 489.25 | ✅ | exact |
| std_areas Mean — Tricaprylin | 8691453.5 | 8691453.5 | ✅ | exact |
| std_areas Mean — DPPG | 4461370.5 | 4461370.5 | ✅ | exact |
| std_areas Mean — Cholesterol | 32403414.8333 | 32403414.83 | ✅ | diff 3.3e-03 (2dp display) |
| std_areas Mean — DEPC | 44013385.5 | 44013385.5 | ✅ | exact |
| bkt_areas Mean — Tricaprylin (pooled) | 8699733.9 | 8699733.9 | ✅ | exact (pool of 10: 6 std + 4 bkt) |
| bkt_areas %RSD — Tricaprylin (pooled) | 0.238252 | 0.2383 | ✅ | diff 4.8e-05 (4dp) |
| Batch B %Assay inj1 — Tricaprylin | 99.979001 | 99.979 | ✅ | diff 1.3e-06 |
| Batch B %Assay inj1 — DPPG | 86.200388 | 86.200 | ✅ | diff 3.9e-04 (3dp) |
| Batch B %Assay inj1 — Cholesterol | 101.772429 | 101.772 | ✅ | diff 4.3e-04 (3dp) |
| Batch B %Assay inj1 — DEPC | 100.389722 | 100.390 | ✅ | diff 2.8e-04 (3dp) |
| Drug/Lipid — tri mg/mL(Lipid) | 1.99958003 | 1.99958 | ✅ | diff 2.5e-08 |
| Drug/Lipid — Sum of Lipid | 15.7906449 | 15.790645 | ✅ | diff 9.7e-08 |
| Drug/Lipid — mg/mL Bupivacaine | 13.2867 | 13.2867 | ✅ | diff 1.8e-15 |
| Drug/Lipid — Drug/Lipid Ratio | 0.84142859 | 0.841429 | ✅ | diff 4.1e-07 |
| Reportable result (== ratio) | 0.84142859 | 0.841429 | ✅ | diff 4.1e-07 |

## Rounding notes
- `standard.conc_ppm` is rounded to 2 dp by the template (`rounding: round/2`), matching
  the sheet's K18..K21 displayed to 2 dp. Gold values 118.92 / 54.03 / 285.1 / 489.25
  reproduce exactly.
- All other calculated fields apply NO mid-chain rounding (the sheet wraps formulas in
  IFERROR but no ROUND), so the engine carries full precision and each computed value was
  compared against the sheet's displayed/gold value at that value's own display precision
  (differences are sub-rounding, shown in the Note column). The `ratio` reportable is
  unrounded by design; display rounding is the front end's concern.
- `bkt_areas` Tricaprylin Mean = pooled AVERAGE(H25:H30, B25:B30) over the 6 std + 4 bkt
  Tricaprylin injections = (52148721 + 34848618) / 10 = 8699733.9. Matches sheet H31.

## SST
`has_blocking_failure = False` — none of the 8 per-compound %RSD criteria (NMT 2.0 %)
block on this data.

## Method
Throwaway script `backend-v2/_verify_a2_0004.py` (DELETED) opened `lims.db` read-only via
`sqlite3`, compared the stored definition text to `json.dumps(LIPID_RATIO_DEFINITION)`,
built `WorksheetEvaluator(TemplateDefinition.parse(defn))`, called `.evaluate(context, groups)`
for BOTH the module and the DB-loaded definition, and asserted every gold target with an
absolute tolerance scaled to the gold value's display precision. Output JSON
`_verify_a2_0004_out.json` and helper `_tbls.py` were also deleted. No feature code modified.
