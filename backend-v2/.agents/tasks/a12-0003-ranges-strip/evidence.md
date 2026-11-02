# Evidence — TPL-A12-0003 Acceptance Ranges strip (iteration 1)

Additive, editable, display-only "Acceptance Ranges" strip (5 pre-filled free-text
fields) rendered above the batch table. No gold value, batch formula, context
field, or criterion changed. DB row byte-for-byte equal to the module.

## 1. DB backup (mandatory first action)
- Source: `backend-v2/lims.db`
- Backup: `backend-v2/lims.db.bak-ampho-ranges-20261024-003512`
- Byte sizes: orig=1331200, bak=1331200, equal=True

## 2. Mechanism verified before coding
- Schema: `singleton` group of `input`/`text` fields with string `default` parses
  cleanly (`FieldDef.parse` stores `default` verbatim; `is_editable` True for INPUT).
- Evaluate: empty `WorksheetEvaluator(p).evaluate({}, {})` seeds + surfaces defaults
  as `acceptance_ranges.range_*` flat scalars.
  Output: `OK {'acceptance_ranges.range_chol': '90.0% to 120.0%', ...range_hspc...:
  '90.0% to 120.0%', ...range_dspg...: '80.0% to 120.0%', ...range_ampho...:
  '90.0% to 120.0%', ...range_ratio...: 'Between 0.11 to 0.17'}`.
- Group order asserted: `['acceptance_ranges', 'batches']`.
- Frontend: `WorksheetForm.tsx` singleton branch (no `chart`) renders `editableFields`
  via `renderInput`; `isEditableField` true for `input`; text fields render as editable
  PrimeReact InputText grid. NO frontend change needed.

## 3. Seeder validate-only
`python -m scripts.seed_test_templates --validate-only` -> exit 0
`ok   TPL-A12-0003 [A12] 2 groups, 11 inputs, 0 area fields, 6 calculated, 5 criteria`
`All definitions valid. --validate-only, so nothing was written.`

## 4. DB row UPDATE (direct ORM, additive sync — no re-seed, no new version)
Throwaway script (adapted from update_a2_0004_definition.py, since deleted) targeting
code TPL-A12-0003 / row 36:
`1 row updated`
`identity preserved: id=36 code=TPL-A12-0003 archetype=A12 version=1 status=Active test_id=33`

## 5. Byte-equality (exact + normalized canonical JSON)
`BYTE-EQUAL + canonical-equal; identity (36, 'TPL-A12-0003', 'A12', 1, 'Active', 33)`
- `stored == json.dumps(module_def)` (exact)
- `canon(json.loads(stored)) == canon(module_def)` (sort_keys, compact)
Row stays Active, id 36, version 1, test_id 33 (TST-ALDR "Ampho-lipid to drug ratio").

## 6. Parity test
`pytest tests/calculation/test_a12_0003_ampho_parity.py -q` -> `9 passed`
New tests: `test_acceptance_ranges_fields_exist_with_defaults`,
`test_acceptance_ranges_do_not_affect_gold_or_criteria`.
Existing gold preserved exactly: Batch 10009697 ratio 0.1511 (contents 54.7560 /
228.9750 / 82.2528 / 55.30, lipid 365.9838), 10010727 ratio 0.1476, 040598M ratio
0.1500. 5 blocking criteria unchanged (Chol/HSPC/Ampho 90-120, DSPG 80-120, ratio
0.11-0.17).

## 7. Full calculation suite baseline
`pytest tests/calculation -q` -> `5 failed, 780 passed`
Exactly the 5 KNOWN pre-existing unrelated failures, no new failures:
- tests/calculation/test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_unit1_release_carryover
- tests/calculation/test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_per_timepoint_summary
- tests/calculation/test_seeded_template_parity.py::TestA6BDissolutionWithReplacement::test_amount_remaining
- tests/calculation/test_worksheet_service.py::test_a_different_analyst_cannot_enter_results_on_an_assigned_trf
- tests/calculation/test_worksheet_service.py::test_a_qa_correction_reopens_and_republishes_the_result
The A12-0003 parity test (incl. new ranges tests) passes.

## 8. Cleanup
Throwaway `scripts/update_a12_0003_definition.py` and `_verify_byte.py` deleted.
Final change surface: module + parity test (committed) + lims.db row 36 (gitignored)
+ backup (gitignored). No frontend change.

## 9. Commit
Local commit (not pushed): `f0e7f29` — staged only the module and the parity test.

