# Implementation Plan — TPL-A1-0003 "Assay for finished product mg/ml"

Goal: create a NEW seed template that clones the live **TPL-A1-0002 "Assay for
Finished Product"** and adds two per-sample columns — **Assay (mg/mL)** (sheet Q)
and **Mean (mg/mL)** (sheet R) — reproducing `Bupivacaine Assay mg ml &
Percentage.xlsx` exactly. Seed it Active, bound to a NEW Test, and keep the live
DB row byte-for-byte equal to the module.

Run all Python from `d:\RD-instance\GIT\backend-v2`. Full hand-derivations and the
evaluator prototype are in `.agents/tasks/a1-0003-assay-fp-mgml/evidence.md`.

## Design decisions (grounded in codebase + sheet)

1. **Next free A1 code = `TPL-A1-0003`.** Confirmed against live
   `backend-v2\lims.db` table `test_templates`: only TPL-A1-0001 and TPL-A1-0002
   exist (both Active). (evidence §6)
2. **New Test = `TST-ASSAY-FP-MGML`**, name EXACTLY
   `Assay for Finished Product-mgperml &%`, type `Quantitative`, created via
   `ensure_test`. Confirmed free in `tests` table; do NOT reuse TST-03 (bound to
   the existing A1 templates). (evidence §6)
3. **Clone source = the live TPL-A1-0002 JSON definition**, not the A1-0001
   module. TPL-A1-0002 exists only in the DB; its full definition is captured in
   evidence/plan. The new module reproduces it verbatim, then adds two fields.
4. **`samples.assay_mgml = pct_assay * label_claim / 100`** (NOT the full sheet-Q
   chain). The engine (`evaluator._apply_rounding`) feeds a calculated field's
   *rounded* value downstream, but base `pct_assay` declares no rounding, so this
   product equals the full Q chain to ~1e-15 and reproduces the sheet's 2-dp
   mg/mL gold exactly. Mirrors the shipped TPL-A12-0001 convention. (evidence §5)
5. **`stats.mean_mgml = mean(samples.assay_mgml)` with `round 2 dp`** — the
   overall mean mg/mL across sample rows, surfaced the same way as
   `stats.pct_mean_assay` (a samples-table footer ref). The template's `samples`
   rows are per-sample (each row's `avg_area` already averages its 2 injections),
   so the mean is across sample rows — the same semantics as the existing
   `pct_mean_assay`, and it reproduces the sheet's block R-mean on the two
   populated rows. (evidence §4)
6. **Base `pct_assay`, `pct_mean_assay`, and all standard/stats groups unchanged.**
   `pct_mean_assay` keeps its live `round 2 dp` (reportable 103.73); `result_unit`
   stays `%`; `resultRef` stays `stats.pct_mean_assay`. (evidence §5 note)
7. **Decomposition:** this is ONE coherent feature (one module + registration +
   parity test). It does not split into separable FEATs, so the workflow's
   existing implement-and-review loop runs this plan. The loop stop contract is
   unchanged: the reviewer writes `review.json` with top-level `verdict:
   "APPROVED"`.

## Field additions (exact)

Append to the `samples` group `fields` (after `pct_assay`):
```python
{"key": "assay_mgml", "kind": "calculated", "label": "Assay (mg/mL)",
 "unit": "mg/mL", "expression": "pct_assay * label_claim / 100"}
```
Append to the `stats` group `fields` (after `pct_mean_assay`):
```python
{"key": "mean_mgml", "kind": "calculated", "label": "Mean (mg/mL)",
 "unit": "mg/mL", "expression": "mean(samples.assay_mgml)",
 "rounding": {"mode": "round", "digits": 2}}
```
Append to the `samples` group `footer` (after the existing `% Mean Assay` entry):
```python
{"label": "Mean (mg/mL)", "ref": "stats.mean_mgml", "unit": "mg/mL"}
```
Keep the existing `% Mean Assay` footer entry. Per-row Assay (mg/mL) shows as the
`assay_mgml` column; Mean (mg/mL) shows once in the footer — mirroring the sheet's
P/Q/R layout.

## Gold values to reproduce (all hand-derived — see evidence.md)

| Quantity | Source cell | Full value | Rounded |
|----------|-------------|-----------|---------|
| Mean STD area | B24 | 2,388,013.4 | — |
| Set-1 % Assay | O31 | 104.48308384718301 | 104.5 (1dp) |
| Set-1 Assay mg/mL | Q31 | 13.896250151675343 | 13.90 (2dp) |
| Set-2 % Assay | O33 | 102.9670127290888 | 103.0 |
| Set-2 Assay mg/mL | Q33 | 13.69461269296881 | 13.69 |
| row35 % Assay | O35 | 99.46535083649894 | 99.5 |
| row35 Assay mg/mL | Q35 | 13.22889166125436 | 13.23 |
| Block % Mean Assay (Set-1,Set-2) | P31 | 103.7250482881359 | 103.7 |
| Block Mean mg/mL (Set-1,Set-2) | R31 | 13.795431422322077 | 13.80 |

Standard fixture: Wt 50.59, chain 100/10/50/1/1, MW 1/1, Potency 99.64; STD areas
2387569/2388066/2392223/2389532/2382677. Context: label_claim 13.3, avg_weight
1.005. Sample Vol/Pip/Vol = 100/1/1 per row.

---

## Ordered work items

- [ ] 1. Create the new seed module `scripts/template_definitions/a1_assay_fp_mgml.py`.
      Define `A1_FP_MGML_DEFINITION` as the full TPL-A1-0002 definition (copy it
      verbatim from the live DB: `resultRef` `stats.pct_mean_assay`, the 12 context
      fields, and groups `standard`, `std_areas`, `bkt_1`, `corel_weights`,
      `corel_areas`, `stats`, `samples`, `criteria: []`) WITH the three additions
      from "Field additions" above (`samples.assay_mgml`, `stats.mean_mgml`,
      samples footer `Mean (mg/mL)`). Keep base `pct_assay`/`pct_mean_assay`
      unchanged. Build it the way sibling modules do — reuse `_common` helpers
      (`context_header`, `standard_group`, `dilution_fields`, `standard_chain_terms`,
      `sample_chain_terms`) following `a1_assay.py`, OR inline the dict; either is
      fine as long as the parsed definition matches the live TPL-A1-0002 groups
      plus the two new fields. Add a `SeedTemplate`:
      `code="TPL-A1-0003"`, `name="Assay for finished product mg/ml"`,
      `archetype="A1"`, `result_unit="%"`, `test_code="TST-ASSAY-FP-MGML"`,
      `test_name="Assay for Finished Product-mgperml &%"`,
      `test_type="Quantitative"`, `definition=A1_FP_MGML_DEFINITION`. Export
      `TEMPLATES = [A1_FP_MGML]`. Write a module docstring explaining it clones
      TPL-A1-0002 and adds the mg/mL columns, and the `assay_mgml` precision
      rationale from decision 4.
      Files: `backend-v2/scripts/template_definitions/a1_assay_fp_mgml.py`
      Verify: `python -c "from scripts.template_definitions.a1_assay_fp_mgml import TEMPLATES; from src.domain.services.calculation.template_schema import TemplateDefinition; d=TemplateDefinition.parse(TEMPLATES[0].definition); print(TEMPLATES[0].code, TEMPLATES[0].test_name); print('samples has assay_mgml:', any(f.key=='assay_mgml' for g in d.groups if g.key=='samples' for f in g.fields))"`
      — prints `TPL-A1-0003 Assay for Finished Product-mgperml &%` and `True`.

- [ ] 2. Register the new module in the seed catalogue.
      In `scripts/template_definitions/__init__.py` import
      `from scripts.template_definitions.a1_assay_fp_mgml import TEMPLATES as _A1_FP_MGML`
      and splice `*_A1_FP_MGML` into `SEED_TEMPLATES` immediately after `*_A1`
      (A1 order). Depends on item 1.
      Files: `backend-v2/scripts/template_definitions/__init__.py`
      Verify: `python -c "from scripts.template_definitions import SEED_TEMPLATES; codes=[t.code for t in SEED_TEMPLATES]; print('TPL-A1-0003' in codes); assert len(codes)==len(set(codes))"`
      — prints `True` and raises nothing (codes unique).

- [ ] 3. Add a hand-derived parity test class for the new template.
      In `tests/calculation/test_seeded_template_parity.py` add `TestA1FPMgml`
      next to `TestA1Assay`, following that file's fixture/`evaluator(code)`
      pattern. Use the standard + Set-1/Set-2 fixture and a separate single-row
      row35 fixture from the gold table above. Assert (abs tolerances like the
      sibling tests): `stats.mean_std` ≈ 2388013.4; row0 `pct_assay` ≈ 104.483084
      and `assay_mgml` ≈ 13.896250; row1 `pct_assay` ≈ 102.967013 and `assay_mgml`
      ≈ 13.694613; `stats.mean_mgml` ≈ 13.80 and `stats.pct_mean_assay` ≈ 103.73;
      row35 `pct_assay` ≈ 99.465351 and `assay_mgml` ≈ 13.228892; and an explicit
      `assay_mgml ≈ pct_assay * 13.3 / 100` identity check on row0. Put the sheet
      cell + arithmetic in a comment above each assertion (the file requires
      hand-derived expecteds). Depends on items 1-2.
      Files: `backend-v2/tests/calculation/test_seeded_template_parity.py`
      Verify: `python -m pytest tests/calculation/test_seeded_template_parity.py -k "A1FPMgml or codes or runs_empty or reportable or context_field or area_fields" -q`
      — new class passes and the catalogue-wide invariants still pass.

- [ ] 4. Validate the whole seed catalogue parses + dry-runs (no DB write).
      Depends on items 1-3.
      Files: none.
      Verify: `python -m scripts.seed_test_templates --validate-only`
      — exit code 0, output lists `ok TPL-A1-0003 [A1] ...`, "All definitions valid".

- [ ] 5. MANDATORY DB backup, THEN seed the new template Active into the live DB.
      First copy `lims.db` to `lims.db.bak-a1mgml-<yyyymmdd-HHMMSS>` in
      `backend-v2`, verify the byte size matches the source, and record the backup
      filename + size in evidence.md. THEN run the seeder (additive/idempotent;
      it skips existing codes and creates TST-ASSAY-FP-MGML via `ensure_test`).
      Depends on item 4. This writes to the live DB — make the backup first.
      Files: `backend-v2/lims.db` (data only; gitignored),
      `.agents/tasks/a1-0003-assay-fp-mgml/evidence.md` (append backup record).
      Backup (PowerShell):
      `$ts=Get-Date -Format 'yyyyMMdd-HHmmss'; Copy-Item lims.db "lims.db.bak-a1mgml-$ts"; (Get-Item lims.db).Length; (Get-Item "lims.db.bak-a1mgml-$ts").Length`
      Seed: `python -m scripts.seed_test_templates`
      Verify: seeder prints `add TPL-A1-0003 [A1] Assay for finished product mg/ml -> TST-ASSAY-FP-MGML` (and `+ Test Master: TST-ASSAY-FP-MGML`) and exits 0; backup size equals source size.

- [ ] 6. Confirm the live DB row is byte-for-byte equal to the module definition.
      Query the seeded row and compare its stored `definition`, `name`,
      `archetype`, `result_unit`, and bound Test (`code`/`name`/`type`) against
      `TEMPLATES[0]`. The stored JSON must equal `json.dumps` of the module
      definition after a canonical round-trip (compare parsed dict equality).
      Depends on item 5.
      Files: none (read-only check; a throwaway script is fine but delete it after).
      Verify: `python` one-off that loads the module `TEMPLATES[0].definition` and
      the DB row's `definition` (via sqlite3 on `lims.db`, code `TPL-A1-0003`) and
      asserts `json.loads(db_definition) == module_definition`, Test code/name
      match, `result_unit=='%'`, `status=='Active'` — prints `PARITY OK` and exits 0.

- [ ] 7. Run the full calculation test suite to confirm nothing regressed.
      Depends on items 1-6.
      Files: none.
      Verify: `python -m pytest tests/calculation -q` — all tests pass (new parity
      class included, existing A1/E2E tests unchanged).

## Notes / assumptions
- The live TPL-A1-0002 definition is reproduced from the DB dump captured during
  planning; item 1's verifier plus item 6's byte-for-byte check guard against any
  transcription drift. If the implementer prefers, re-dump TPL-A1-0002 from
  `lims.db` and diff before adding the two fields.
- `% Mean Assay` stays at 2-dp rounding (live base behaviour); the sheet's 1-dp P
  column is a display choice, and the task mandates leaving the base unchanged.
  `Mean (mg/mL)` matches at 2 dp (13.80). Documented in evidence §5.
- All `_tmp_*` exploration scripts created during planning were deleted; none
  remain in the worktree.
