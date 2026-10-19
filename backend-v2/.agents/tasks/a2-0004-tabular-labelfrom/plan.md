# Implementation Plan — TPL-A2-0004 tabular transpose + generic `labelFrom`

## Scope & mode

No approved design document was handed in, so the design decisions below are
mine, grounded in the engine/module/frontend code I read and in a throwaway
dry-run that reproduced every gold value with the transposed layout before this
plan was written. Only two parts of the system change:

- **Part A (backend):** transpose `std_areas` and `bkt_areas` in TPL-A2-0004
  from compounds-as-COLUMNS to compounds-as-ROWS with per-row (and pooled)
  Mean/SD/%RSD, and rewire the `stats` singleton to read the row-based tables by
  compound index. Keep the `stats.*` field KEYS identical so `lipid_samples`
  %Assay and the 8 SST criteria need no structural change.
- **Part B (frontend):** add a generic, optional `labelFrom` field property
  (dynamic column-header text), and apply it in the TPL-A2-0004 module to the
  `lipid_samples` and `drug_lipid` per-compound columns.

Modify ONLY these files; do not touch any other template or Test:
- `d:\RD-instance\GIT\backend-v2\scripts\template_definitions\a2_bupivacaine_lipid_ratio.py`
- `d:\RD-instance\GIT\backend-v2\lims.db` (the single `test_templates` row `code='TPL-A2-0004'`, v1, Active, id 35)
- `d:\RD-instance\GIT\frontend-react\src\features\test-templates\models\testTemplate.types.ts`
- `d:\RD-instance\GIT\frontend-react\src\features\test-templates\components\WorksheetForm.tsx`
- New test file: `d:\RD-instance\GIT\backend-v2\tests\calculation\test_a2_0004_tabular_parity.py`

## Design decisions (one-liners, grounded in code I read)

1. **Row tables use generic `inj_1..inj_6` area columns + a `compound` cell.**
   The engine exposes a table group as column series, so `std_areas.inj_1` is a
   whole column and `std_areas.inj_1[rowno-1]` reads one row — exactly what the
   pooled BKT expression needs (`evaluator.py` `_build_scope`). Six injection
   columns match the sheet's max replicate count (rows 25–30); blank cells are
   tolerated by `mean/sd/rsd` (`_numeric` skips blanks in `expression.py`).
2. **Per-row stats use `mean([inj_1,...,inj_6])`** — a list literal of the same
   row's fields. `expression.py` `_ListNode` + `_f_mean`/`_f_sd`/`_f_rsd`
   evaluate this across that row's cells, blank-tolerant. Verified: Tricaprylin
   row mean = 8691453.5.
3. **Compound name cell uses `mirrorFrom: "standard.name"`** (UI copies the
   row-aligned value, renders read-only) — the existing mechanism in
   `WorksheetForm.tsx`. It is NOT a calculated field, so it does not perturb the
   engine; both row tables are ordered identically to `standard`
   (Tricaprylin/DPPG/Cholesterol/DEPC), so row index `i` is the same compound in
   all three groups.
4. **`stats` stays a thin-indirection singleton** keyed exactly as today
   (`mean_std_tri`, `rsd_pool_depc`, …), each field now reading the row table by
   compound index (`std_areas.mean[0]`, `bkt_areas.rsd[3]`). This keeps every
   `lipid_samples` %Assay expression and all 8 SST criteria untouched. Chosen
   over inlining into `lipid_samples` because the %Assay chain already references
   `stats.mean_std_<c>` and must keep reproducing the gold numbers. Verified: the
   full %Assay → %Mean → drug_lipid ratio chain reproduces gold.
5. **`labelFrom` is a UI-only header-text resolver** (counterpart to the
   value-copying `mirrorFrom`), applied to `lipid_samples`/`drug_lipid` columns
   whose headers should read the compound names from Standard Details. The
   transposed `std_areas`/`bkt_areas` do NOT need `labelFrom` — their compound
   identity is a row cell (`mirrorFrom`), not a column header.

## Exact field definitions and expression strings (verified against the engine)

Let `_COMPOUNDS` stay `[("tri","Tricaprylin"),("dppg","DPPG Na"),("chol","Cholesterol"),("depc","DEPC")]`.

### `std_areas` group (TABLE, compounds as ROWS)

- `rows`: `{"min": 1, "max": 10, "default": len(_COMPOUNDS), "labelFrom": "compound"}`
  (row label from the compound cell; `max` ~10 per task).
- fields, in order:
  1. `{"key": "compound", "kind": "input", "type": "text", "label": "Compound", "mirrorFrom": "standard.name"}`
  2. `inj_1` … `inj_6`: `{"key": "inj_k", "kind": "area", "label": "Injection k", "unit": "µV·s"}` for k=1..6
  3. `{"key": "mean", "kind": "calculated", "label": "Mean", "expression": "mean([inj_1, inj_2, inj_3, inj_4, inj_5, inj_6])"}`
  4. `{"key": "sd", "kind": "calculated", "label": "SD", "expression": "sd([inj_1, inj_2, inj_3, inj_4, inj_5, inj_6])"}`
  5. `{"key": "rsd", "kind": "calculated", "label": "% RSD", "unit": "%", "expression": "rsd([inj_1, inj_2, inj_3, inj_4, inj_5, inj_6])"}`
- Keep/adjust the group `footer` to reference row 0 of the new keys, e.g.
  `[{"label":"Mean (Tricaprylin)","ref":"stats.mean_std_tri"},{"label":"SD","ref":"stats.sd_std_tri"},{"label":"% RSD","ref":"stats.rsd_std_tri","unit":"%"}]`
  (footer refs are `stats.*` which are preserved; keep as-is).

### `bkt_areas` group (TABLE, compounds as ROWS, pooled with the matching `std_areas` row)

- `rows`: `{"min": 1, "max": 10, "default": 4, "labelFrom": "compound"}`.
- fields, in order:
  1. `{"key": "compound", "kind": "input", "type": "text", "label": "Compound", "mirrorFrom": "standard.name"}`
  2. `inj_1` … `inj_6`: area columns as above.
  3. `mean`/`sd`/`rsd` POOLED over the same compound's std row (by `rowno-1`) + this bkt row. Exact strings (verified):
     - `mean`: `"mean(pool([std_areas.inj_1[rowno - 1], std_areas.inj_2[rowno - 1], std_areas.inj_3[rowno - 1], std_areas.inj_4[rowno - 1], std_areas.inj_5[rowno - 1], std_areas.inj_6[rowno - 1]], [inj_1, inj_2, inj_3, inj_4, inj_5, inj_6]))"`
     - `sd`: same but `sd(pool(...))`
     - `rsd`: same but `rsd(pool(...))`
- `footer`: keep referencing `stats.mean_pool_tri` / `stats.sd_pool_tri` / `stats.rsd_pool_tri` (preserved keys).

> `rowno` is injected by the evaluator (`_build_scope`, `scope["rowno"] = row_index+1`); `[rowno - 1]` indexes the std column series at the current row. `pool([...],[...])` flattens both lists and drops blanks (`_f_pool`). Verified pooled Tricaprylin mean = 8699733.9, %RSD = 0.2383.

### `stats` singleton — REPLACE every field's expression, keep every KEY

For each `(prefix, name)` in `_COMPOUNDS` at index `idx`:

| field key          | new expression              |
|--------------------|-----------------------------|
| `mean_std_<p>`     | `std_areas.mean[idx]`       |
| `sd_std_<p>`       | `std_areas.sd[idx]`         |
| `rsd_std_<p>`      | `std_areas.rsd[idx]`        |
| `mean_pool_<p>`    | `bkt_areas.mean[idx]`       |
| `sd_pool_<p>`      | `bkt_areas.sd[idx]`         |
| `rsd_pool_<p>`     | `bkt_areas.rsd[idx]`        |

e.g. `tri`→idx 0, `dppg`→1, `chol`→2, `depc`→3. Labels/units unchanged.
`lipid_samples` %Assay expressions and the 8 criteria (`stats.rsd_std_*`,
`stats.rsd_pool_*`) are UNCHANGED.

### `labelFrom` values applied in the module (Part B)

On `lipid_samples` per-compound columns, add `"labelFrom": "standard.name[idx]"`:
- Tricaprylin: `tri_area1,tri_area2,tri_assay1,tri_assay2,tri_mean` → `"standard.name[0]"`
- DPPG: `dppg_*` (same 5) → `"standard.name[1]"`
- Cholesterol: `chol_*` → `"standard.name[2]"`
- DEPC: `depc_*` → `"standard.name[3]"`

On `drug_lipid` per-compound `<c>_mgml` columns add `"labelFrom": "standard.name[idx]"`
(`tri_mgml`→[0], `dppg_mgml`→[1], `chol_mgml`→[2], `depc_mgml`→[3]).
`labelFrom` is UI-only; it does not reach `TemplateDefinition.parse` behaviour
(the schema ignores unknown keys on fields), so it cannot change any number.

## Ordered implementation steps

- [ ] 1. Add `labelFrom?: string` to `FieldDef` in the frontend types.
      Place it right after `mirrorFrom` with a doc comment: UI-only dynamic
      column-header text, `"<group>.<field>"` or `"<group>.<field>[idx]"`;
      counterpart to `mirrorFrom` (which copies VALUES) — this drives the HEADER.
      Files: `d:\RD-instance\GIT\frontend-react\src\features\test-templates\models\testTemplate.types.ts`
      Verify: `cd d:\RD-instance\GIT\frontend-react && npm run build` — `tsc -b` type-checks with no new errors.

- [ ] 2. Implement generic `labelFrom` header resolution in `WorksheetForm.tsx`.
      Add a pure helper `resolveLabelFrom(spec: string): string | null` that:
      parses `"<group>.<field>"` with an optional `[idx]` suffix; when an index
      is present reads `computed.rows[group]?.[idx]?.[field]` (fallback to the
      editable `values[group]?.[idx]?.[field]`); when no index is present it is
      a singleton/context style ref — read `computed.values["group.field"]`.
      Return the trimmed string if non-blank, else `null`. Then, at the two
      header render sites, when `field.labelFrom` is set use the resolved text,
      falling back to `field.label ?? field.key` when it resolves blank:
      (a) the table column `<th>` (currently `{field.label ?? field.key}`);
      (b) the singleton field `<label>` blocks (editable grid and calculated grid).
      Keep it fully generic — no template codes, no compound names hardcoded.
      Note: resolution reads `computed`/`values` already in scope in the
      component; `standard.name[0]` → `computed.rows.standard[0].name`.
      Files: `d:\RD-instance\GIT\frontend-react\src\features\test-templates\components\WorksheetForm.tsx`
      Verify: `cd d:\RD-instance\GIT\frontend-react && npm run build` — build succeeds; manual reasoning check: a template with no `labelFrom` renders identical headers as before (helper is only invoked when the property is set).

- [ ] 3. Transpose `std_areas` in the module to compounds-as-ROWS.
      Replace the `_area_columns()`-based `std_areas` group with the ROW layout
      from "Exact field definitions" above: `compound` (mirrorFrom standard.name),
      `inj_1..inj_6` area inputs, and `mean/sd/rsd` list-literal expressions;
      `rows` `{min:1,max:10,default:4,labelFrom:"compound"}`. Keep the footer
      pointing at `stats.mean_std_tri/sd_std_tri/rsd_std_tri`.
      Files: `d:\RD-instance\GIT\backend-v2\scripts\template_definitions\a2_bupivacaine_lipid_ratio.py`
      Verify: `cd d:\RD-instance\GIT\backend-v2 && python -m scripts.seed_test_templates --validate-only` — TPL-A2-0004 parses and dry-runs OK.

- [ ] 4. Transpose `bkt_areas` likewise, with POOLED per-row stats.
      Same ROW layout; `mean/sd/rsd` use the `pool([std_areas.inj_k[rowno-1]...],[inj_k...])`
      strings from above. `rows` `{min:1,max:10,default:4,labelFrom:"compound"}`.
      Keep the footer pointing at `stats.mean_pool_tri/sd_pool_tri/rsd_pool_tri`.
      Files: `d:\RD-instance\GIT\backend-v2\scripts\template_definitions\a2_bupivacaine_lipid_ratio.py`
      Verify: `python -m scripts.seed_test_templates --validate-only` passes.

- [ ] 5. Rewire the `stats` singleton via `_stats_fields()`.
      Change each field's expression per the table in "stats singleton" (read
      `std_areas.<stat>[idx]` / `bkt_areas.<stat>[idx]`), keeping keys, labels,
      and units. Do NOT change `lipid_samples` %Assay expressions or the 8
      criteria.
      Files: `d:\RD-instance\GIT\backend-v2\scripts\template_definitions\a2_bupivacaine_lipid_ratio.py`
      Verify: `python -m scripts.seed_test_templates --validate-only` passes.

- [ ] 6. Apply `labelFrom` in the module to `lipid_samples` and `drug_lipid`
      per-compound columns, using `standard.name[idx]` values from "labelFrom
      values applied in the module". Add the key inside `_lipid_sample_fields()`
      (area1/area2/assay1/assay2/mean for each compound) and `_drug_lipid_fields()`
      (`<c>_mgml`). The transposed row tables get NO `labelFrom`.
      Files: `d:\RD-instance\GIT\backend-v2\scripts\template_definitions\a2_bupivacaine_lipid_ratio.py`
      Verify: `python -m scripts.seed_test_templates --validate-only` passes.

- [ ] 7. GxP numeric verification test (new pytest, mirrors the existing
      `test_seeded_template_parity.py` style — hand-derived golds, not copied
      from a run). Feed the workbook inputs (from
      `d:\RD-instance\GIT\_dumps\Bupivacaine Lipid _ Drug to lipid Ratio.txt`),
      evaluate the parsed module definition, and assert the gold targets:
      - `standard.conc_ppm` rows: Tricaprylin 118.92, DPPG 54.03, Cholesterol 285.1, DEPC 489.25
      - `std_areas.mean` rows: 8691453.5 / 4461370.5 / 32403414.83 / 44013385.5
      - `bkt_areas.mean[0]` 8699733.9 and `bkt_areas.rsd[0]` ≈ 0.2383
      - `stats.mean_std_tri`==`std_areas.mean[0]` and `stats.rsd_pool_tri`≈0.2383 (indirection still works)
      - Batch `EP20_117-299-B` %Assay inj1: tri 99.979, dppg 86.200, chol 101.772, depc 100.390
      - drug_lipid batch B: `tri_mgml` 1.99958, `sum_lipid` 15.790645, `mgml_bupi` 13.2867, `ratio` 0.841429
      Use `pytest.approx` tolerances like the sibling tests (abs=1e-2 for ppm/means, 1e-4 for %RSD/ratio).
      Batch-B input values to use: avg_weight 1.005, sample_weight 1.5008, vol_j 25, pip_k 1, vol_l 1;
      tri inj1 area 8729574, dppg 3826195, chol 32474189, depc 44235393 (area2 blank → %Mean = inj1);
      drug_lipid `pct_assay_bupi` 99.9; context lc_tri 2, lc_dppg 0.9, lc_chol 4.7, lc_depc 8.2, lc_bupi 13.3;
      std_areas/bkt_areas injections from the dump (rows 25–30 / 25–28).
      Files: `d:\RD-instance\GIT\backend-v2\tests\calculation\test_a2_0004_tabular_parity.py`
      Verify: `cd d:\RD-instance\GIT\backend-v2 && python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q` — all assertions pass.

- [ ] 8. Keep the existing catalogue-wide suite green (confirms no other
      template regressed and the seeded-parity invariants still hold).
      Files: none (runs existing tests).
      Verify: `cd d:\RD-instance\GIT\backend-v2 && python -m pytest tests/calculation -q` — all pass.

- [ ] 9. Back up the DB, then UPDATE the TPL-A2-0004 row's `definition` to equal
      the module byte-for-byte. The `definition` column is SQLAlchemy `JSON`
      (serialized with `json.dumps`, default separators, `ensure_ascii=True`), so
      write it via the same serialization. Procedure (throwaway script, then
      delete it):
      1. `copy lims.db lims.db.bak-a2areas-<timestamp>` (a backup was already made
         in setup; make another only if writing — do make this one).
      2. `from scripts.template_definitions.a2_bupivacaine_lipid_ratio import LIPID_RATIO_DEFINITION`;
         `TemplateDefinition.parse(LIPID_RATIO_DEFINITION)` then
         `WorksheetEvaluator(...).evaluate({}, {})` to re-validate before writing.
      3. `UPDATE test_templates SET definition = ? WHERE code='TPL-A2-0004'` with
         `json.dumps(LIPID_RATIO_DEFINITION)` as the bound param (id 35, v1, Active).
      4. Read the row back, `json.loads` it, and assert it `==` LIPID_RATIO_DEFINITION
         (structural equality), and that `definition_text == json.dumps(LIPID_RATIO_DEFINITION)`
         (byte equality with the serializer).
      Files: `d:\RD-instance\GIT\backend-v2\lims.db` (+ a temporary sync script, removed after).
      Verify (DB-parity, throwaway script): load the DB row's JSON, parse via
      `TemplateDefinition.parse`, dry-run evaluate, and re-assert the Step-7 gold
      targets directly from the DB definition — so the row an analyst will use,
      not just the module, reproduces the golds. Confirm the module `==` DB
      round-trip equality printed `True`.

- [ ] 10. Clean up: remove any throwaway scripts created in steps 7/9 that are
      not the committed pytest file. Confirm no `_tmp_*`/sync scripts remain under
      `backend-v2\scripts`.
      Files: none committed.
      Verify: `cd d:\RD-instance\GIT\backend-v2 && git status --porcelain` shows only the
      intended changes (module, new test, lims.db) plus the two frontend files; no stray temp scripts.

## GxP / safety notes

- The whole chain was dry-run before this plan: transposed `std_areas`/`bkt_areas`
  + rewired `stats` reproduce every gold value listed above. The expression
  strings in this plan are the exact ones the engine accepted.
- `lims.db` is a production-shaped SQLite file: back it up before the single
  UPDATE (step 9), and the UPDATE targets only `code='TPL-A2-0004'`.
- Keep DB row `definition` == module `LIPID_RATIO_DEFINITION` (serializer-exact).
- The frontend change is additive and backward-compatible: `labelFrom` is only
  consulted when a field declares it, so every existing template renders
  unchanged. No `labelFrom` is applied to the transposed row tables (they use
  `mirrorFrom` on the compound cell instead).

## Loop stop contract (unchanged, for the implementing loop)

Implementer runs first; the verdict-writer runs last and writes
`d:\RD-instance\GIT\backend-v2\.agents\tasks\a2-0004-tabular-labelfrom\review.json`
with `"verdict": "APPROVED"` only when: the module edits are in place; the DB row
equals the module byte-for-byte; the new GxP parity test and the full
`tests/calculation` suite pass; and the frontend `npm run build` (TS) succeeds.
