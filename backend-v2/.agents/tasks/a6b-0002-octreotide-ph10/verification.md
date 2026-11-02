# Verification — TPL-A6B-0002, Dissolution-Octreolide-pH-10

First iteration (no `review.json` present). Implemented from the approved
`design.md` / `plan.md`, mirroring the A6B-0001 archetype in
`scripts/template_definitions/a6_dissolution.py`.

All commands run from `d:\RD-instance\GIT\backend-v2`.

## Files added / changed

- `scripts/template_definitions/a6b_octreotide_ph10.py` — NEW module. Defines
  `A6B_OCT = SeedTemplate(code="TPL-A6B-0002", ...)` and `TEMPLATES = [A6B_OCT]`.
  Units-as-rows / three timepoint tables shape; standard J19 conc, std areas +
  BKT with pooled `pool(...)` mean, dissolution params, sample-weight F/G/H table
  with Mean/SD/%RSD (SD deliberately over raw weights pooled with the mean cell,
  reproducing `STDEV(F22:F28)`), prep inputs (A32=4.12, A35=10, B35=1, C35=1,
  A37=1), three %Residue blocks (K chain per-timepoint weight column via
  `weights.w_*hr[rowno-1]`, Mean/Min/Max/RSD), three %Release-from-assay blocks
  (`C70 = (A32-B70)/A32*100`, Mean/Min/Max/RSD). Dead K64 block and L/M
  carry-over columns deliberately omitted per design. Single acceptance
  criterion `sst_rsd_criterion(target="std_stats.rsd_std", limit=2.0)`.
- `scripts/template_definitions/__init__.py` — import `_A6B_OCT` and splice
  `*_A6B_OCT` into `SEED_TEMPLATES` in A6 order (after `*_A6`, before `*_A6D`).
- `tests/calculation/test_a6b_0002_octreotide_parity.py` — NEW parity test.

## Identity (EXACT)

- Template code `TPL-A6B-0002`, archetype `A6b`, result_unit `%` (matches
  A6B-0001).
- Test `test_code='TST-DISS-OCT-PH10'`, `test_name='Dissolution-Octreolide-pH-10'`
  (user's 'Octreolide' spelling preserved), `test_type='Quantitative'`, created
  via the seeder's `ensure_test`.

## Checks run and results

1. **Parse + empty eval** of the module:
   `parsed+empty-eval ok TPL-A6B-0002` (exit 0).
2. **Registration**: `registered once at index 11` (exit 0) — present exactly
   once in `SEED_TEMPLATES`.
3. **Parity test**: `python -m pytest tests/calculation/test_a6b_0002_octreotide_parity.py -q`
   → **14 passed**. Asserts every gold value from the design's "Full gold-value
   set": J19=91.73466; B27/B29, D27/D29; the three weight-stat Mean/SD/%RSD
   triples; K40/K41 + residue_1hr Mean/Min/Max/RSD; K46 + residue_4hr Mean/RSD;
   K52 + residue_24hr Mean/RSD; C70/C71 + release_1hr Mean/Min/Max/RSD; C76 +
   release_4hr Mean/RSD; C82/C83 + release_24hr Mean/RSD; resultRef resolves to
   `residue_24hr.mean` (1.8876…); the single `std_stats.rsd_std` lte 2.0 SST
   criterion exists; empty worksheet is blank with no blocking failure.
4. **Seeder --validate-only**: exit 0,
   `ok   TPL-A6B-0002 [A6b] 14 groups, 24 inputs, 5 area fields, 46 calculated, 1 criteria`,
   no `INVALID DEFINITIONS` section, "All definitions valid."
5. **Live seed**: `python -m scripts.seed_test_templates` exit 0 —
   `+ Test Master: TST-DISS-OCT-PH10 — Dissolution-Octreolide-pH-10` and
   `add  TPL-A6B-0002 [A6b] ... -> TST-DISS-OCT-PH10`; `Done. 1 template(s)
   added, 25 already present.`
6. **DB invariants** (temporary snippet, since deleted): exactly one
   `TPL-A6B-0002` row, status `Active`, bound to a `tests` row with
   `code='TST-DISS-OCT-PH10'` and `name='Dissolution-Octreolide-pH-10'` EXACT;
   stored `definition` canonical-JSON (`sort_keys=True, separators=(',',':')`)
   BYTE-EQUAL to the module's `TEMPLATES[0].definition`; result_unit `%`; total
   template rows now 37; no duplicate Active A6B-0002. Output:
   `OK one Active row; test name EXACT; canonical-JSON byte-equal; total
   templates= 37 ; active A6B-0002 count= 1`.
7. **Full calculation suite baseline** (before changes):
   `5 failed, 780 passed` — the known pre-existing failures
   (`TestA6BDissolutionWithReplacement::{test_unit1_release_carryover,
   test_per_timepoint_summary, test_amount_remaining}` for A6B-0001 and
   `test_worksheet_service::{test_a_different_analyst_cannot_enter_results_on_an_assigned_trf,
   test_a_qa_correction_reopens_and_republishes_the_result}`).
8. **Full calculation suite after changes**:
   `python -m pytest tests/calculation -q` → **5 failed, 798 passed**. The 5
   failures are EXACTLY the same pre-existing ones (A6B-0001 behaviour UNCHANGED
   — still the same 3 known failures, no new A6B-0001 failures). The +18 passes
   are the 14 new parity tests plus the 4 catalogue-wide parametrized invariants
   that auto-cover the new template. No OTHER new failures.

## Cleanup

Throwaway DB-verification script `_tmp_verify_db.py` deleted. `git status`
shows only the three intended code files as the change set for this task
(`__init__.py` modified; `a6b_octreotide_ph10.py` and
`test_a6b_0002_octreotide_parity.py` new). `lims.db` is gitignored
(`backend-v2/*.db`) and is not committed.

## Commit

Committed locally (not pushed). Commit hash: **e780345**
(`feat(templates): add TPL-A6B-0002 Octreotide pH-10 dissolution
(Dissolution-Octreolide-pH-10)`). 3 files changed, 589 insertions: the new
module, the `__init__.py` registration, and the new parity test. `lims.db` not
committed (gitignored).
