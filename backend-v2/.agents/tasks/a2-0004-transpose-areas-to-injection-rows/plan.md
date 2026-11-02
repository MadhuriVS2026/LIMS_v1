# Implementation Plan — TPL-A2-0004: transpose std_areas / bkt_areas to injection-rows × compound-columns

## Goal (verbatim intent)

Flip the **Standard Replicate Injections** (`std_areas`) and **BKT Standard Injections**
(`bkt_areas`) sections of template **TPL-A2-0004** from the CURRENT orientation
(one ROW per compound, six injection COLUMNS, per-row Mean/SD/%RSD) to the
OPPOSITE orientation:

- **ROWS = Injection 1..6**, expandable (user wants to add injection rows; cap at 12).
- **COLUMNS = one AREA column per compound**: `tri_area`, `dppg_area`, `chol_area`,
  `depc_area` (order tri, dppg, chol, depc). Each column HEADER auto-fetches the
  compound name from Standard Details via `labelFrom="standard.name[<idx>]"`
  (idx: tri 0, dppg 1, chol 2, depc 3).
- **Mean / SD / % RSD** aggregate DOWN each compound column, rendered as a group
  **footer** (one entry per compound column), not as data rows.
- `bkt_areas` Mean/SD/%RSD are **POOLED** per compound column with the matching
  `std_areas` compound column.

This is a formula-exact GxP change: every gold value must reproduce to the
sheet's rounding, `stats.*` KEYS must not change, and the live DB row 35 must end
byte-for-byte equal to the serialized source module.

---

## What exploration established (grounding — do not re-decide)

1. **Multi-row group field = column series.** `evaluator.py` `_build_scope` exposes
   every multi-row group as `group.field = [values down the rows]`. So
   `mean(std_areas.tri_area)` aggregates DOWN the `tri_area` column, blanks
   skipped. Indexing `std_areas.tri_area[0]` picks one row. This is exactly the
   target aggregate shape. (src/domain/services/calculation/evaluator.py, lines ~318-335.)

2. **Engine functions** `mean/sd/rsd` skip blanks (`_numeric`); `sd`/`rsd` need
   >= 2 values; `pool([...],[...])` flattens multiple series and drops blanks.
   (src/domain/services/calculation/expression.py — `_f_mean`, `_f_sd`, `_f_rsd`,
   `_f_pool`, `_numeric`.) Confirmed blanks-excluded behavior matches the sheet's
   `AVERAGE`/`STDEV` over padded ranges.

3. **Footer is a frontend-only pass-through.** The backend `TemplateDefinition`
   parser (template_schema.py `GroupDef.parse`) reads only known keys and ignores
   `footer`, `labelFrom`, `mirrorFrom`. Footers never enter the calculation. The
   frontend renders `footer` beneath the table. Therefore a footer entry per
   compound column is the correct place for per-column Mean/SD/%RSD, and fake
   Mean/SD/%RSD **data rows must NOT be used** — a data row would be picked up by
   `mean(std_areas.tri_area)` and corrupt the column aggregate. (Verified: the
   prototype below reproduces all gold values precisely with the footer approach.)

4. **`labelFrom` resolver is live** (commit c46fdcb, current HEAD). Frontend
   `WorksheetForm.tsx` `headerText()` / `resolveLabelFrom()` accept
   `"<group>.<field>[idx]"` and render the resolved worksheet value at **column
   header** sites; it is UI-only and never changes a number. The existing
   `lipid_samples` area columns already use `labelFrom="standard.name[idx]"`, so
   the same pattern applies to the new `std_areas`/`bkt_areas` columns. **No
   frontend change is needed or permitted** (task scope).

5. **`rows.labelFrom` must name one of the group's own fields** (template_schema.py
   `GroupDef.parse` raises `TemplateSchemaError` otherwise). The current groups set
   `rows.labelFrom="compound"`; that field is being removed. The new row-label
   field must exist in the group — plan uses an `inj_label` text input column and
   sets `rows.labelFrom="inj_label"`.

6. **DB serialization is byte-identical to `json.dumps(definition)`.** The `JSON`
   column (test_template_model.py) uses SQLAlchemy's default serializer; the
   session (session.py) sets no custom `json_serializer`. Verified live: the
   stored row-35 text `== json.dumps(LIPID_RATIO_DEFINITION)` exactly today. So a
   byte-for-byte DB update is achieved by writing the module's serialized
   definition to row 35 — safest via the ORM (load row 35, assign
   `definition = LIPID_RATIO_DEFINITION`, commit), which uses the same serializer
   as seeding.

7. **The seeder will NOT update row 35.** `seed_test_templates.py` is additive and
   skips any code already present. TPL-A2-0004 already exists (row 35, v1, Active,
   single row). Hence the direct DB UPDATE in step 6 — NOT the app approve/e-sign
   flow, NOT a re-seed.

8. **Baseline is green.** `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py`
   passes 7/7 against the CURRENT compounds-as-rows module. This test file and its
   gold values are reused after the transpose (same gold numbers; only the input
   layout changes).

### Prototype proof (gold values reproduce under the target structure)

A throwaway prototype built the transposed `std_areas`/`bkt_areas` (injection
rows, compound columns), rewired `stats` to `mean(std_areas.<c>_area)` /
`mean(pool(std_areas.<c>_area, bkt_areas.<c>_area))`, and evaluated the parity
test's data (transposed to injection rows). Results matched the sheet gold to
rounding:

- `stats.mean_std_tri` = 8691453.5 ✓   `mean_std_dppg` = 4461370.5 ✓
- `stats.mean_std_chol` = 32403414.83 ✓   `mean_std_depc` = 44013385.5 ✓
- `stats.mean_pool_tri` = 8699733.9 ✓   `stats.rsd_pool_tri` = 0.2383 ✓
- `lipid_samples[0].tri_assay1` = 99.979 ✓
- `drug_lipid[0].ratio` = reportable = 0.841429 ✓   no blocking failure ✓

---

## Design decisions locked (record in the module docstring/comments)

- **D1 — Orientation:** injections-as-rows, compounds-as-columns, for both
  `std_areas` and `bkt_areas`. (User request; messages 11-12.)
- **D2 — Columns:** `tri_area, dppg_area, chol_area, depc_area` (fixed, in
  `_COMPOUNDS` order), each `kind:"area"`, each
  `labelFrom="standard.name[<idx>]"` so the header auto-fetches the compound name.
- **D3 — Row label:** add an `inj_label` text input column ("Injection") and set
  `rows.labelFrom="inj_label"`; seed default rows "Injection 1".."Injection 6"
  (std) / "Injection 1".."Injection 4" (bkt) is optional — rows default count
  governs rendering. Rows `{min:1, max:12, default:6}` for std (expandable),
  `{min:1, max:12, default:6}` for bkt (expandable; bkt data commonly fills 4).
- **D4 — Mean/SD/%RSD via FOOTER, one entry per compound column.** Justification:
  footers are frontend-only and never feed the calculation, so Mean/SD/%RSD
  rendered as a footer row leave the `mean(std_areas.<c>_area)` column aggregate
  clean; fake Mean/SD/%RSD data rows would be swept into the aggregate and break
  every gold value (proven by the engine's column-series semantics). The footer
  references the `stats.*` scalars, matching the established pattern already used
  by the current `std_areas`/`bkt_areas` footers.
- **D5 — Per-column aggregate spans:** use the WHOLE column series (no explicit
  index span) — `mean(std_areas.tri_area)` covers every injection row and skips
  blanks automatically. This is simpler and more correct than an index range
  `tri_area[0..n]`, and it adapts to the expandable row count for free. Because
  Mean/SD/%RSD live in the footer (not data rows), the column series contains only
  injection rows, so the whole-column aggregate is exactly the intended span.
- **D6 — BKT pooling:** `mean(pool(std_areas.<c>_area, bkt_areas.<c>_area))`,
  and likewise `sd(...)` / `rsd(...)`, matching the sheet's
  `AVERAGE(H25:H30,B25:B30)` / `STDEV(B25:B30,H25:H30)`.
- **D7 — stats KEYS unchanged:** keep `mean_std_<c>`, `sd_std_<c>`, `rsd_std_<c>`,
  `mean_pool_<c>`, `sd_pool_<c>`, `rsd_pool_<c>`. Only each expression's SOURCE
  changes from `std_areas.mean[idx]` / `bkt_areas.mean[idx]` (per-row) to the
  per-column aggregate. The `lipid_samples` %Assay chain (`stats.mean_std_<c>`)
  and the 8 SST criteria reference these keys and need NO change.
- **D8 — Drop fields that no longer exist:** the per-row `compound` (mirrorFrom),
  `inj_1..inj_6`, and the per-row `mean/sd/rsd` calculated fields are removed from
  `std_areas`/`bkt_areas`. `_injection_columns()` and `_inj_list()` helpers are no
  longer used by these groups; remove or repurpose them (keep only if still
  referenced elsewhere — grep confirms they are used ONLY by these two groups).

---

## Ordered implementation steps

- [ ] 1. **Rewrite the two area-field builders and the stats builder** in
      `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`.
      - Add a helper `_area_columns()` returning the 4 compound area columns:
        for `idx,(prefix,name)` in `_COMPOUNDS`:
        `{"key": f"{prefix}_area", "kind": "area", "label": f"{name} Area",
          "unit": "µV·s", "labelFrom": f"standard.name[{idx}]"}`.
      - Rewrite `_std_area_fields()` to return
        `[{"key":"inj_label","kind":"input","type":"text","label":"Injection"},
          *_area_columns()]` (no inj_1..6, no per-row compound/mean/sd/rsd).
      - Rewrite `_bkt_area_fields()` to the SAME shape (inj_label + 4 area cols).
        The pooling now lives in `stats`, not per row, so `bkt_areas` has no
        calculated fields.
      - Rewrite `_stats_fields()` so each stat aggregates the compound column:
        `mean_std_<c>  = mean(std_areas.<c>_area)`
        `sd_std_<c>    = sd(std_areas.<c>_area)`
        `rsd_std_<c>   = rsd(std_areas.<c>_area)`
        `mean_pool_<c> = mean(pool(std_areas.<c>_area, bkt_areas.<c>_area))`
        `sd_pool_<c>   = sd(pool(std_areas.<c>_area, bkt_areas.<c>_area))`
        `rsd_pool_<c>  = rsd(pool(std_areas.<c>_area, bkt_areas.<c>_area))`
        KEYS, labels, and units stay as they are now.
      - Remove `_injection_columns()` and `_inj_list()` (and `_INJ_COLUMNS` if
        unused after) — first grep to confirm no other reference.
      Files: `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
      Verify: `python -c "from scripts.template_definitions.a2_bupivacaine_lipid_ratio import LIPID_RATIO_DEFINITION as D; print('ok')"` imports clean.

- [ ] 2. **Update the two group dicts** (`std_areas`, `bkt_areas`) in
      `LIPID_RATIO_DEFINITION["groups"]`.
      - `std_areas`: `rows = {"min":1, "max":12, "default":6, "labelFrom":"inj_label"}`;
        `fields = _std_area_fields()`; replace the footer with one entry per
        compound column rendering Mean/SD/%RSD. Use the per-compound footer shape,
        e.g. a footer list that labels the three aggregate rows and references
        `stats.mean_std_<c>` / `stats.sd_std_<c>` / `stats.rsd_std_<c>` for each of
        the four compounds (follow the frontend footer entry shape already present;
        keep a leading row-label entry + one `ref` per compound column so Mean/SD/
        %RSD line up under their columns).
      - `bkt_areas`: `rows = {"min":1, "max":12, "default":6, "labelFrom":"inj_label"}`;
        `fields = _bkt_area_fields()`; footer references the POOLED stats
        `stats.mean_pool_<c>` / `stats.sd_pool_<c>` / `stats.rsd_pool_<c>` per column.
      Files: `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
      Verify: `python -m scripts.seed_test_templates --validate-only` — TPL-A2-0004
      parses and dry-runs without error (prints `ok TPL-A2-0004 ...`).

- [ ] 3. **Correct the module docstring and the house-rule comments** that claim
      compounds-as-rows. Update: the `_std_area_fields`/`_bkt_area_fields`
      docstrings, the `_stats_fields` docstring, and the two inline group comments
      ("transposed to one ROW per compound ...") to describe the new
      injections-as-rows / compounds-as-columns orientation, the footer-per-column
      Mean/SD/%RSD, and the whole-column aggregate / pooling. Record decisions
      D1-D8 briefly.
      Files: `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
      Verify: `python -m scripts.seed_test_templates --validate-only` still clean
      (no behavior change; comment-only).

- [ ] 4. **Rewrite the parity test** `tests/calculation/test_a2_0004_tabular_parity.py`
      to feed the new layout while asserting the SAME gold values.
      - Replace `STD_AREAS` / `BKT_AREAS` fixtures with injection-row dicts:
        each row `{"inj_label": "Injection k", "tri_area":..., "dppg_area":...,
        "chol_area":..., "depc_area":...}`. STD has 6 rows, BKT has 4 rows
        (inj 5/6 absent → blanks skipped), transposing the existing numbers.
      - Keep every assertion value unchanged (means, pooled mean/rsd, assay,
        ratio, reportable, no-blocking). Update the module docstring of the test
        to state the new orientation.
      - `test_std_area_row_means` / `test_bkt_pooled_tricaprylin` now read the
        per-compound aggregates from `result.values["stats.mean_std_<c>"]` /
        `stats.mean_pool_tri` / `stats.rsd_pool_tri` (the per-row `mean` field no
        longer exists). Assert the same numbers.
      Files: `backend-v2/tests/calculation/test_a2_0004_tabular_parity.py`
      Verify: `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q`
      — all tests pass with the gold values (8691453.5, 4461370.5, 32403414.83,
      44013385.5, pooled 8699733.9 / rsd 0.2383, tri_assay1 99.979, ratio 0.841429).

- [ ] 5. **Run the full calculation + seed-parity suites** to prove nothing else
      regressed (the stats KEYS are unchanged, so %Assay and SST must still pass).
      Files: none (verification).
      Verify:
      `python -m pytest tests/calculation -q` — green, including
      `test_seeded_template_parity.py` and `test_assay_template_e2e.py`.

- [ ] 6. **Update live DB row 35 byte-for-byte** from the edited module, via the
      ORM (NOT the app approve/e-sign flow, NOT a re-seed — the seeder skips
      existing codes).
      Procedure (run from `backend-v2`):
      ```python
      # scripts-free one-shot; uses the same JSON serializer as seeding.
      import asyncio
      from sqlalchemy import select
      from scripts.template_definitions.a2_bupivacaine_lipid_ratio import LIPID_RATIO_DEFINITION
      from src.infrastructure.database.models.test_template_model import TestTemplateModel
      from src.infrastructure.database.session import async_session_factory

      async def main():
          async with async_session_factory() as s:
              row = (await s.execute(
                  select(TestTemplateModel).where(TestTemplateModel.id == 35)
              )).scalar_one()
              assert row.code == "TPL-A2-0004" and row.version == 1  # guard
              row.definition = LIPID_RATIO_DEFINITION
              await s.commit()
      asyncio.run(main())
      ```
      Guard: assert `code == "TPL-A2-0004"` and `version == 1` before writing, so a
      wrong row is never touched. Do NOT change `status`, `version`, `approved_by`,
      or any other column. Back up `lims.db` first (`copy lims.db lims.db.bak`).
      Files: `backend-v2/lims.db` (row 35 `definition` only).
      Verify (byte-for-byte equality to the serialized module):
      ```
      python -c "import sqlite3,json; from scripts.template_definitions.a2_bupivacaine_lipid_ratio import LIPID_RATIO_DEFINITION as D; raw=sqlite3.connect('lims.db').execute('select definition from test_templates where id=35').fetchone()[0]; print('exact', raw==json.dumps(D)); print('normalized', json.loads(raw)==D)"
      ```
      Expected: `exact True` and `normalized True`. Also confirm row identity
      unchanged: `select id,code,version,status from test_templates where id=35`
      → `(35, 'TPL-A2-0004', 1, 'Active')`.

- [ ] 7. **Final evidence capture + full regression gate.**
      - Re-run `python -m scripts.seed_test_templates --validate-only` (clean) and
        `python -m pytest tests/calculation -q` (green) and record the output under
        the evidence dir
        `backend-v2/.agents/tasks/a2-0004-transpose-areas-to-injection-rows/`.
      - Confirm scope: `git status` shows only
        `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`,
        `tests/calculation/test_a2_0004_tabular_parity.py`, and the binary
        `lims.db` changed (plus evidence files under `.agents/`). No frontend, no
        other template, no unrelated files.
      Files: evidence files under
      `backend-v2/.agents/tasks/a2-0004-transpose-areas-to-injection-rows/`.
      Verify: both commands pass; `git status` matches the allowed scope.

---

## Verification checklist (every gold-value target)

Standard concentrations (unchanged by this task, must still hold):
- `standard[0].conc_ppm` ≈ 118.92, `[1]` ≈ 54.03, `[2]` ≈ 285.1, `[3]` ≈ 489.25

Per-compound standard replicate means (column aggregate, sheet B31/C31/D31/E31):
- `stats.mean_std_tri`  ≈ 8691453.5
- `stats.mean_std_dppg` ≈ 4461370.5
- `stats.mean_std_chol` ≈ 32403414.83
- `stats.mean_std_depc` ≈ 44013385.5

Pooled BKT (Tricaprylin, sheet H31 pooled std+bkt):
- `stats.mean_pool_tri` ≈ 8699733.9
- `stats.rsd_pool_tri`  ≈ 0.2383

stats indirection still resolves (KEYS unchanged):
- `stats.mean_std_tri` equals the Tricaprylin column mean
- `stats.rsd_pool_tri` ≈ 0.2383

Batch EP20_117-299-B %Assay (inj 1), via the stats indirection:
- `tri_assay1` ≈ 99.979, `dppg_assay1` ≈ 86.200,
  `chol_assay1` ≈ 101.772, `depc_assay1` ≈ 100.390

Drug/Lipid ratio chain (sheet 2):
- `tri_mgml` ≈ 1.99958, `sum_lipid` ≈ 15.790645,
  `mgml_bupi` ≈ 13.2867, `ratio` = reportable ≈ 0.841429

Suitability: `result.has_blocking_failure is False` on this data.

DB parity: row-35 `definition` text `== json.dumps(LIPID_RATIO_DEFINITION)`
(exact) and `json.loads(definition) == LIPID_RATIO_DEFINITION` (normalized);
row identity `(35, TPL-A2-0004, 1, Active)` unchanged.

Suite gates: `python -m scripts.seed_test_templates --validate-only` clean;
`python -m pytest tests/calculation -q` green (parity + seeded-parity + e2e).

---

## Scope guard (touch ONLY)

1. `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` —
   `_std_area_fields`, `_bkt_area_fields`, `_stats_fields`, the new `_area_columns`
   helper, the `std_areas`/`bkt_areas` group dicts (fields, rows, footer), and the
   docstring/comments.
2. `backend-v2/lims.db` — row id 35 `definition` column only (direct ORM UPDATE).
3. `backend-v2/tests/calculation/test_a2_0004_tabular_parity.py` — the parity test.

Do NOT touch any other template, the frontend (the `labelFrom` resolver is already
live), the engine, `_common.py`, or unrelated files. Do NOT change row-35 status,
version, or approval columns. Do NOT use the app approve/e-sign flow or re-seed.

## Known gaps / assumptions

- The exact frontend footer entry shape (how a per-column footer row is keyed) is
  rendered by `WorksheetForm.tsx`; the backend ignores `footer` entirely, so any
  reasonable per-column footer list is accepted by validation. Follow the shape
  already used by the current `std_areas`/`bkt_areas` footers (`{"label","ref","unit"}`),
  extended to one `ref` per compound column. If the frontend expects a strict
  shape, that is a UI-render concern only and cannot affect gold values or the DB
  update; it is out of scope to modify the frontend.
- `bkt_areas` default row count is set to 6 (expandable to 12); the sheet fills 4,
  and blank rows are skipped by the aggregates, so the default count does not
  affect any gold value.
