# Acceptance Ranges strip added above the batch table on TPL-A12-0003

A new `acceptance_ranges` singleton of five pre-filled, editable free-text fields is inserted immediately before the `batches` group in `A12_AMPHO_RATIO_DEFINITION`, so it renders as a ranges header after the section title. The fields are informational: they are inputs with string defaults, never referenced by any expression, criterion target, or `resultRef`, so batch math, the drug-to-lipid ratio, the gold values, and the five blocking criteria are untouched. The commit changes exactly two tracked files (the module and the parity test); the DB row 36 was synced out-of-band to stay byte-for-byte equal to the module. I verified the diff, the module, the DB row, the test, and the frontend rendering path independently; I relied on the recorded evidence for the pytest suite results rather than re-running them.

Watch for: nothing blocking. (confirmed) The change is strictly additive and every required invariant holds on independent inspection.

**Verdict**: APPROVED

## High-level view

The addition is a single `singleton` group placed first in the `groups` list, ahead of `batches`. Because the five fields carry no `expression`, are not criterion targets, and are not the `resultRef`, they are inert to the calculation engine — they seed and surface their own defaults and nothing else. The gold contents, lipid total, ratio values, and the five blocking criteria are byte-identical to the base template.

The fields are `kind: input`, `type: text` with the exact default strings requested (Chol/HSPC/Ampho "90.0% to 120.0%", DSPG "80.0% to 120.0%", ratio "Between 0.11 to 0.17"), so they are editable and persisted. The frontend renders groups in definition order and treats a chart-less input singleton as an editable field grid, so the strip lands above the batch table with no frontend change.

The persisted DB row (id 36, TPL-A12-0003, A12, v1, Active, bound to TST-ALDR / test_id 33) is exactly and canonically equal to the module definition, and A2-0004 (row 35) is untouched. The parity test was extended to assert the five range fields/defaults and that gold and criteria are preserved, and the evidence records the full `tests/calculation` run as the same five known pre-existing failures with the A12-0003 parity test passing.

<details>
<summary>Issues (0)</summary>

No blocking or non-blocking issues. The change meets every required invariant on independent verification.

</details>

<details>
<summary>Details</summary>

## Additive-only placement in the groups list

The diff inserts `_acceptance_ranges_group()` as the first element of `A12_AMPHO_RATIO_DEFINITION["groups"]`, immediately before the existing `batches` table literal. `_batch_fields()` is unchanged — the content expressions (`<c>_assay * lc_<c> / 100`), the lipid-total expression (`chol_content + hspc_content + dspg_content`), the ratio (`ampho_content / lipid_content`), and the `resultRef` (`batches.drug_lipid_ratio`) are all exactly as before. The context header (product/assay source plus the four overridable `lc_*` label-claim fields) and the five criteria are byte-identical. I confirmed group order both in the module source and in the persisted row: `['acceptance_ranges', 'batches']`. (confirmed)

## The five fields are inert to the engine

Each field is `{"kind": "input", "type": "text", "default": "..."}` with no `expression`. They live in their own group whose key (`acceptance_ranges`) appears in no criterion `target` — the five criteria still target `mean(batches.<field>)` and `mean(batches.drug_lipid_ratio)`. The parity test's `test_acceptance_ranges_do_not_affect_gold_or_criteria` asserts `"acceptance_ranges" not in crit.target` for every criterion and re-checks the gold lipid/ratio values with the strip present. Because the fields neither feed an expression nor serve as a criterion target nor as the `resultRef`, they cannot perturb pass/fail. (confirmed)

## Exact default strings and editability

Verified directly against the persisted row:

```
range_chol  -> "90.0% to 120.0%"   (Assay of Cholesterol)
range_hspc  -> "90.0% to 120.0%"   (Assay of HSPC)
range_dspg  -> "80.0% to 120.0%"   (Assay of DSPG)
range_ampho -> "90.0% to 120.0%"   (Microbial assay of Amphotericin B)
range_ratio -> "Between 0.11 to 0.17" (Calculated Drug to Lipid ratio)
```

All five are `kind: input`, `type: text`. The parity test asserts `field.is_editable is True`, `field.kind is FieldKind.INPUT`, `field.type is ValueType.TEXT`, and the exact label/default pairs, plus that an empty `evaluate({}, {})` surfaces each default as a flat scalar `acceptance_ranges.<key>`. (confirmed)

## Frontend renders the strip above the batch table, no frontend change

`WorksheetForm.tsx` renders `groups.map(...)` in definition order, so `acceptance_ranges` (first) precedes `batches`. For a `singleton` with no `chart` hint it takes the field-grid branch, rendering `editableFields = fields.filter(isEditableField)`; `isEditableField` returns true for `kind: 'input'` (`EDITABLE_KINDS = {'input','area'}`). The acceptance_ranges group has no `chart` key, so it renders as an editable `InputText` grid above the table. No frontend file was modified, consistent with the evidence. (confirmed)

## Gold values and criteria preserved

The five criteria limits in the persisted row are `[90,120]/[90,120]/[80,120]/[90,120]` for the assays and `[0.11,0.17]` for the ratio, all blocking — unchanged. The evidence records the gold batch values held exactly (10009697 ratio 0.1511 with contents 54.7560 / 228.9750 / 82.2528 / 55.30 and lipid 365.9838, 10010727 ratio 0.1476, 040598M ratio 0.1500); the parity test re-asserts lipid and ratio per batch with the strip present. I did not re-run the suite; the module's batch fields and criteria are byte-identical to base, which is the mechanism that keeps the gold intact. (confirmed for criteria/formulas by inspection; gold run relied on evidence)

## DB row equals the module, identity preserved, A2-0004 untouched

Independent check of `test_templates` row for TPL-A12-0003: `exact_equal` (`stored == json.dumps(module_def)`) and `canonical_equal` (sorted/compact) both True. Identity: id 36, archetype A12, version 1, status Active, test_id 33 → tests row `('TST-ALDR', 'Ampho-lipid to drug ratio')`. A2-0004 is row 35, still Active, and is not in the commit's file list. No new DB version was created. (confirmed)

## Change surface and cleanup

`git show f0e7f29 --name-only` lists only `scripts/template_definitions/a12_ampho_drug_lipid.py` and `tests/calculation/test_a12_0003_ampho_parity.py`. No A12 throwaway scripts remain (`scripts/update_a12_0003_definition.py` and `scripts/_verify_byte.py` absent). `git status` shows no uncommitted source changes under `scripts/` or `src/` — only unrelated `.agents` task artifacts and a frontend verification file. The lims.db row change is gitignored, as expected. (confirmed)

## Test coverage

Two new tests were added: `test_acceptance_ranges_fields_exist_with_defaults` (group order, singleton kind, five field keys/kinds/types/labels/defaults, and default surfacing via empty evaluate) and `test_acceptance_ranges_do_not_affect_gold_or_criteria` (gold lipid/ratio with the strip present, no blocking failure, criterion keys set, and no criterion targeting `acceptance_ranges`). Existing gold and criteria assertions are retained. Evidence records `test_a12_0003_ampho_parity.py -q → 9 passed` and the full `tests/calculation -q → 5 failed, 780 passed`, the five being the known pre-existing A6B dissolution and worksheet_service failures — no new failures. Not independently re-run per instructions; evidence for every required check is present and internally consistent. (gold/suite relied on evidence; new-test content confirmed by reading the test file)

</details>

<details>
<summary>File map</summary>

- `scripts/template_definitions/a12_ampho_drug_lipid.py` — adds `_acceptance_ranges_group()` and inserts it first in `groups`; docstring note; nothing else changed.
- `tests/calculation/test_a12_0003_ampho_parity.py` — adds two tests asserting the range fields/defaults and gold/criteria preservation; imports FieldKind/GroupKind/ValueType.
- `lims.db` (gitignored) — row 36 definition synced byte-for-byte to the module.

Full diff: `git show f0e7f29`.

</details>
