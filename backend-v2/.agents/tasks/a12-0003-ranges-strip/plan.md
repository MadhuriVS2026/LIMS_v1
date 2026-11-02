# Implementation Plan — TPL-A12-0003 Acceptance Ranges strip

Add an EDITABLE, display-only "Acceptance Ranges" strip of 5 free-text fields to the
existing template **TPL-A12-0003** ("Amphotericin B — Drug-to-Lipid Ratio"), rendered
directly ABOVE the `batches` table so it reads as a ranges header after the section
title. Purely additive and formula-exact: no existing gold value, criterion, or batch
math changes; the DB `test_templates` row for TPL-A12-0003 must end byte-for-byte equal
to the edited module.

## Findings from exploration (mechanism confirmed — do not re-decide)

All of the following were verified against the live repo during planning.

1. **`headerContext` is the wrong mechanism — confirmed, do NOT use it.**
   - The backend schema (`src/domain/services/calculation/template_schema.py`) never
     reads `headerContext`: `GroupDef.parse` only consumes `key`, `kind`, `label`,
     `rows`, `fields`. It is a frontend-only pass-through.
   - In `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`,
     `renderGroupHeaderContext` renders each `headerContext` item as a READ-ONLY value
     resolved from worksheet context (`contextValues[ref] ?? worksheet.context_values`).
     It cannot hold or persist analyst-entered text. So it cannot deliver editable,
     pre-filled fields.

2. **Chosen mechanism — a `singleton` group of `input`/`text` fields with string
   defaults, inserted immediately before `batches`.** Verified end-to-end:
   - **Parse**: `FieldDef.parse` accepts `kind: "input"`, `type: "text"`, and a string
     `default` (defaults are stored verbatim, no numeric coercion). `GroupDef.parse`
     accepts a `singleton` with a non-empty `fields` list. A prototype insertion parsed
     cleanly: `groups == ['acceptance_ranges', 'batches']`.
   - **Evaluate**: `WorksheetEvaluator.evaluate({}, {})` seeds each singleton field from
     its `default` (see `_seed_rows`: a field with no stored value but a non-None
     `default` takes the default), then mirrors the singleton into flat scalars
     `acceptance_ranges.range_*`. Prototype confirmed the exact default strings surface,
     e.g. `acceptance_ranges.range_chol == "90.0% to 120.0%"` and
     `acceptance_ranges.range_ratio == "Between 0.11 to 0.17"`.
   - **Editable + persisted**: `FieldDef.is_editable` is True for `kind == INPUT`.
     Frontend `isEditableField` returns true for `input` kinds, `seedValues` pre-fills
     each editable field from `field.default`, and these inputs are saved in
     `group_values["acceptance_ranges"]` like any other input group.
   - **Rendering (no quirk for pure-text singletons)**: the `group.kind === 'singleton'`
     branch in `WorksheetForm.tsx` (no `chart` present) renders `editableFields` as a
     labeled grid via `renderInput`; for `type === 'text'` that is a PrimeReact
     `InputText`. `fieldColClass` gives free-text fields `col-12` (full width), so the 5
     ranges stack as a clean labeled editable strip. The singleton gets its own
     Edit/Save/Delete toolbar (standard for every editable group) — acceptable and
     expected; no frontend change is required.
   - **Conclusion**: NO frontend code change is needed. The task is backend module +
     parity test + one DB row UPDATE.

3. **Target DB row — confirmed id = 36** (NOT 35; row 35 is TPL-A2-0004).
   `select id, code, archetype, version, status, test_id from test_templates where
   code='TPL-A12-0003'` returned `(36, 'TPL-A12-0003', 'A12', 1, 'Active', 33)`.
   Must stay: id 36, version 1, status Active, test_id 33 (TST-ALDR, "Ampho-lipid to
   drug ratio").

4. **Seeder is additive** (`scripts/seed_test_templates.py` skips existing codes), so a
   direct ORM/sqlite UPDATE of the existing row is required — do NOT re-seed, do NOT
   create a new version/row. The documented sync pattern is
   `scripts/update_a2_0004_definition.py` (serialises the module `definition` to JSON,
   UPDATEs the one row, asserts identity columns unchanged). Adapt it for code
   TPL-A12-0003 / row 36, then DELETE the throwaway script.

5. **No criteria/gold impact**: the 5 new fields are inputs in a separate group, never
   referenced by any `expression`, `criteria.target`, or `resultRef`
   (`batches.drug_lipid_ratio`). They cannot change batch contents, the lipid total,
   the ratio, the 5 blocking criteria, or the reportable.

## Field specification (exact — use verbatim)

New group, inserted as the FIRST element of `A12_AMPHO_RATIO_DEFINITION["groups"]`
(i.e. immediately before the existing `batches` group):

```python
{
    "key": "acceptance_ranges",
    "kind": "singleton",
    "label": "Acceptance Ranges",
    "fields": [
        {"key": "range_chol",  "kind": "input", "type": "text", "label": "Assay of Cholesterol",              "default": "90.0% to 120.0%"},
        {"key": "range_hspc",  "kind": "input", "type": "text", "label": "Assay of HSPC",                     "default": "90.0% to 120.0%"},
        {"key": "range_dspg",  "kind": "input", "type": "text", "label": "Assay of DSPG",                     "default": "80.0% to 120.0%"},
        {"key": "range_ampho", "kind": "input", "type": "text", "label": "Microbial assay of Amphotericin B", "default": "90.0% to 120.0%"},
        {"key": "range_ratio", "kind": "input", "type": "text", "label": "Calculated Drug to Lipid ratio",    "default": "Between 0.11 to 0.17"},
    ],
}
```

Exact default strings (byte-for-byte):
- `range_chol`  -> `90.0% to 120.0%`
- `range_hspc`  -> `90.0% to 120.0%`
- `range_dspg`  -> `80.0% to 120.0%`
- `range_ampho` -> `90.0% to 120.0%`
- `range_ratio` -> `Between 0.11 to 0.17`

---

## Steps

- [ ] 1. Take a fresh DB backup BEFORE any change.
      Copy `d:\RD-instance\GIT\backend-v2\lims.db` to
      `lims.db.bak-ampho-ranges-<yyyymmdd-HHMMSS>` (local timestamp). Confirm the copy
      exists and its byte size matches the original, and record the backup filename in
      an evidence note under `.agents/tasks/a12-0003-ranges-strip/` (e.g. `backup.txt`).
      Files: `d:\RD-instance\GIT\backend-v2\lims.db.bak-ampho-ranges-<ts>` (new),
      `d:\RD-instance\GIT\backend-v2\.agents\tasks\a12-0003-ranges-strip\backup.txt` (new).
      Verify (PowerShell, from `backend-v2`):
      `$ts=Get-Date -Format yyyyMMdd-HHmmss; Copy-Item lims.db "lims.db.bak-ampho-ranges-$ts"; (Get-Item lims.db).Length -eq (Get-Item "lims.db.bak-ampho-ranges-$ts").Length`
      — prints `True`; backup file present and equal size.

- [ ] 2. Add the `acceptance_ranges` singleton to the module as the first group.
      In `scripts/template_definitions/a12_ampho_drug_lipid.py`, add a small builder
      (e.g. `_acceptance_ranges_group()`) returning the dict in "Field specification"
      above, and insert its call as the FIRST element of
      `A12_AMPHO_RATIO_DEFINITION["groups"]`, before the existing `batches` dict. Add a
      short module comment noting these are informational, editable, display-only labels
      that do NOT drive pass/fail (enforcement stays in the 5 blocking `criteria`).
      Do NOT touch `context`, `criteria`, `resultRef`, `_batch_fields`, or any LC value.
      Files: `scripts/template_definitions/a12_ampho_drug_lipid.py`.
      Verify (from `backend-v2`):
      `python -c "from scripts.template_definitions.a12_ampho_drug_lipid import A12_AMPHO_RATIO_DEFINITION as d; from src.domain.services.calculation.template_schema import TemplateDefinition; from src.domain.services.calculation.evaluator import WorksheetEvaluator; p=TemplateDefinition.parse(d); assert [g.key for g in p.groups]==['acceptance_ranges','batches']; r=WorksheetEvaluator(p).evaluate({},{}); vals={k:r.values[k] for k in ['acceptance_ranges.range_chol','acceptance_ranges.range_hspc','acceptance_ranges.range_dspg','acceptance_ranges.range_ampho','acceptance_ranges.range_ratio']}; assert vals=={'acceptance_ranges.range_chol':'90.0% to 120.0%','acceptance_ranges.range_hspc':'90.0% to 120.0%','acceptance_ranges.range_dspg':'80.0% to 120.0%','acceptance_ranges.range_ampho':'90.0% to 120.0%','acceptance_ranges.range_ratio':'Between 0.11 to 0.17'}, vals; print('OK', vals)"`
      — prints `OK {...}` with the five exact defaults.

- [ ] 3. Confirm the seeder still validates the whole catalogue.
      No seeder code change. Run the validate-only dry run.
      Files: none.
      Verify (from `backend-v2`): `python -m scripts.seed_test_templates --validate-only`
      — exit code 0, output lists `ok TPL-A12-0003 [A12] ...` and
      "All definitions valid. --validate-only, so nothing was written."

- [ ] 4. Extend the parity test with the ranges assertions; keep all existing
      assertions intact.
      In `tests/calculation/test_a12_0003_ampho_parity.py`, add a test method (e.g.
      `test_acceptance_ranges_fields_exist_with_defaults`) that: parses
      `A12_AMPHO_RATIO_DEFINITION`; asserts a `acceptance_ranges` singleton group exists
      and precedes `batches` in group order; asserts its 5 fields are `kind == input`,
      `type == text`, editable, with the exact default strings; and asserts an empty
      evaluate surfaces those defaults as `acceptance_ranges.range_*`. Do NOT alter the
      existing GOLD dict, `BATCHES`, or any content/ratio/criteria test.
      Files: `tests/calculation/test_a12_0003_ampho_parity.py`.
      Verify (from `backend-v2`): `pytest tests/calculation/test_a12_0003_ampho_parity.py -q`
      — all tests pass (existing gold/criteria tests plus the new ranges test).

- [ ] 5. Push the edited definition into the live Active row 36 via a direct UPDATE.
      Create a short throwaway sync script adapted from
      `scripts/update_a2_0004_definition.py` targeting `CODE = "TPL-A12-0003"`: import
      `A12_AMPHO_RATIO` (or `A12_AMPHO_RATIO_DEFINITION`), `json.dumps` the definition,
      UPDATE `test_templates.definition` WHERE `code='TPL-A12-0003'`, and assert exactly
      one row updated with identity columns (id, code, archetype, version, status,
      test_id) unchanged (still `36 / TPL-A12-0003 / A12 / 1 / Active / 33`). Run it from
      `backend-v2`. This writes to the backed-up `lims.db` (reversible via step 1's
      backup). Then DELETE the throwaway script.
      Files: temporary `scripts/update_a12_0003_definition.py` (create then DELETE).
      Verify: script prints `1 row updated` and `identity preserved: id=36 ... version=1
      status=Active test_id=33`.

- [ ] 6. Assert the stored DB row equals the module byte-for-byte (exact and normalized
      canonical JSON).
      Compare the module `definition` against the row's stored `definition`:
      `json.dumps(module_def) == stored_text` (exact), AND
      `json.dumps(json.loads(stored_text), sort_keys=True, separators=(",",":")) ==
      json.dumps(module_def, sort_keys=True, separators=(",",":"))` (normalized
      canonical). Confirm identity columns are still `36 / TPL-A12-0003 / A12 / 1 /
      Active / 33`.
      Files: none (read-only check; may be a one-liner, not a committed script).
      Verify (from `backend-v2`):
      `python -c "import sqlite3,json; from scripts.template_definitions.a12_ampho_drug_lipid import A12_AMPHO_RATIO_DEFINITION as d; con=sqlite3.connect('lims.db'); row=con.execute(\"select id,code,archetype,version,status,test_id,definition from test_templates where code='TPL-A12-0003'\").fetchone(); assert row[:6]==(36,'TPL-A12-0003','A12',1,'Active',33), row[:6]; assert row[6]==json.dumps(d); c=lambda o: json.dumps(o,sort_keys=True,separators=(',',':')); assert c(json.loads(row[6]))==c(d); print('BYTE-EQUAL + canonical-equal; identity', row[:6])"`
      — prints the success line; both equalities hold.

- [ ] 7. Run the calculation suite and confirm the known-failure baseline is unchanged.
      Files: none.
      Verify (from `backend-v2`): `pytest tests/calculation -q`
      — EXACTLY the 5 known pre-existing unrelated failures (A6B + worksheet_service)
      and NO others; the A12-0003 parity test (including the new ranges test) passes.
      If any new failure appears, fix it before finishing. (Capture the failing node ids
      and compare to the known 5; if the environment's baseline differs, record the
      pre-change baseline by stashing the module edit, running once, and comparing.)

- [ ] 8. Clean up and confirm the final change surface.
      Ensure the throwaway sync script from step 5 is deleted and no other stray files
      remain. The only committed changes are: the module
      (`scripts/template_definitions/a12_ampho_drug_lipid.py`) and the parity test
      (`tests/calculation/test_a12_0003_ampho_parity.py`); plus the untracked local
      `lims.db` row change and the `lims.db.bak-ampho-ranges-*` backup (DB and backups
      are not committed). No frontend change.
      Files: remove `scripts/update_a12_0003_definition.py`.
      Verify (from `backend-v2`): `git status --porcelain` shows only the module and the
      parity test as modified (plus untracked evidence under `.agents/` and the backup,
      which are not staged); the throwaway script is absent.

## Verification checklist (must all hold at the end)

- [ ] seed `--validate-only` exits 0; template parses + evaluates; the 5 range fields
      exist with the exact default strings.
- [ ] All existing gold preserved exactly — Batch 10009697 (Chol 105.3 / HSPC 107.5 /
      DSPG 100.8 / Ampho 110.6 -> contents 54.7560 / 228.9750 / 82.2528 / 55.30, lipid
      365.9838, ratio 0.1511), Batch 10010727 (ratio 0.1476), Batch 040598M (ratio
      0.1500). The 5 blocking criteria (Chol/HSPC/Ampho 90–120, DSPG 80–120, ratio
      0.11–0.17) unchanged.
- [ ] DB row for TPL-A12-0003 byte-for-byte equal to the module (exact + normalized
      canonical JSON); row stays Active, id 36, version 1, test_id 33 (TST-ALDR
      "Ampho-lipid to drug ratio").
- [ ] Parity test asserts the 5 range fields exist with correct defaults AND all
      existing gold/criteria assertions still pass.
- [ ] `pytest tests/calculation`: same 5 known pre-existing failures (A6B +
      worksheet_service) plus the A12-0003 parity test passing; no other new failures.
- [ ] Throwaway script deleted; final change surface = module + parity test + the
      TPL-A12-0003 DB row (no frontend change needed).

## Assumptions / notes

- Default strings use the user's exact copy (`"90.0% to 120.0%"`, `"80.0% to 120.0%"`,
  `"Between 0.11 to 0.17"`). The ratio default collapses the user's two-line quoted
  value into a single-line string, which is how a text field stores/renders it.
- The singleton renders with its own Edit/Save/Delete toolbar (standard for every
  editable group). This is expected and the closest clean approach that yields editable,
  pre-filled fields above the batch table; no frontend change is made.
- `lims.db` and `lims.db.bak-ampho-ranges-*` are local artifacts and are NOT committed;
  the committed change is the module and the parity test only.
