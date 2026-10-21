# Implementation Plan — TPL-A2-0004 "Sample Details" tall per-SET restructure

Formula-exact, GxP restructure of ONLY the `lipid_samples` group (Sample Details) of
template TPL-A2-0004 "Bupivacaine Lipid Content & Drug-to-Lipid Ratio", plus the minimal
`drug_lipid` source-ref repointing that the restructure forces. One module, two related
groups. Execute with the existing implement-and-review loop — not decomposed into features.

All work is in `d:\RD-instance\GIT\backend-v2`. Run every Python command from that directory.

---

## Design decisions (made during exploration, grounded in the engine and the live DB)

These were verified by reading the engine (`expression.py`, `evaluator.py`,
`template_schema.py`) and proved on paper + with the real evaluator against the gold data
before this plan was written. Each is one or two sentences of rationale, not a design doc.

### D1. Per-row compound selection: hidden `cidx` + `if`/`coalesce` (approach (a))
Each lipid_samples row represents one compound, chosen by its position within its SET:
`cidx = (rowno-1) mod 4` (0=tri, 1=dppg, 2=chol, 3=depc). The engine has no `mod`, but it
has `trunc`, so:

```
cidx  expression:  rowno - 1 - trunc((rowno - 1) / 4, 0) * 4
```

The visible `% Assay` is a `coalesce()` of four `if(cidx == k, <compound-k assay>, blank())`
terms. Each term is the SAME algebra as the current `_assay_expression(prefix, "area")` but
bound to compound `k`'s `stats.mean_std_<c>`, `standard.*[k]` and `lc_<c>`. `if()` is lazy in
this engine, so the three non-selected branches never evaluate and cannot poison the result;
`coalesce` returns the one non-blank branch. **Chosen over approach (b)** (four hidden
sub-fields) because it is one visible calculated field instead of five, and over approach (c)
(direct row-indexed cross-refs) because the compound's divisor lives in the `stats` singleton
and its standard row lives in `standard` — there is no single series to index. **Proved:** the
real `WorksheetEvaluator` with this expression returns the four gold values exactly (99.98 /
86.20 / 101.77 / 100.39) on the SET-1 inputs.

### D2. Shared SET-prep values (Avg Weight, Sample Weight, Vol, Pip, Vol): per-row inputs
The `% Assay` formula reads `avg_weight`, `sample_weight`, `vol_j`, `pip_k`, `vol_l`
UNQUALIFIED from the current row (see `_build_scope` in `evaluator.py`). `mirrorFrom` in this
codebase is a frontend-only display hint — the engine never copies values with it (confirmed:
`FieldDef.parse` ignores it, and `a6_dissolution.py`'s `mirrorFrom` fields are only ever read
via their SOURCE group's `[rowno-1]`, never relied on for a value). Therefore these five prep
values MUST physically exist on every one of a SET's 4 rows for the formula to be correct.
They are modelled as **per-row inputs** (same keys and defaults as today: avg_weight 1.005,
vol_j 25, pip_k 1, vol_l 1; sample_weight required-by-use). `mirrorFrom` is added as a UI
convenience so the frontend can auto-fill rows 2-4 of a SET from row 1 ("one value per SET"
feel), but correctness never depends on it. **Chosen over mirror-down-for-correctness**
because the engine cannot mirror values, only display them.

### D3. SET identifier: per-row text input `set_no`
A `set_no` text input on every row (shown on each row; the frontend may visually merge it down
a block). A per-row value is the engine-faithful choice for the same reason as D2 — there is no
engine mechanism to enter a value "once per block". It feeds no formula, so its only job is
labelling/grouping; keeping it per-row keeps the stored data unambiguous.

### D4. Compound Name: calculated, read-only, tracks Standard Details
`compound_name` is a calculated text field selecting `standard.name[cidx]` via the same
`if`/`coalesce` pattern, so it auto-fetches the compound name from Standard Details and renames
when a standard is renamed. `labelFrom: "standard.name[0]"` is kept as the frontend header
hint. (A calculated field is used rather than a bare `labelFrom` because the value itself must
differ per row by `cidx`.)

### D5. LC column: calculated, read-only, mirrored from `lc_<c>`
`lc` is a calculated read-only field = `coalesce(if(cidx==k, lc_<c>, blank()) …)`, so it shows
2.000 / 0.900 / 4.700 / 8.200 for tri/dppg/chol/depc, tracking the overridable context fields.
It feeds no formula (the %Assay denominator reads `lc_<c>` directly), so it is display-only and
read-only by being `calculated`.

### D6. One Area column, single injection; %Assay NOT rounded mid-chain
The tall layout drops the 2nd injection: one `area` column per row, one `pct_assay` per row.
`pct_assay` carries **no `rounding`** — the sheet applies no mid-chain ROUND and `drug_lipid`
reads the unrounded value. **Proved:** feeding unrounded `pct_assay` into the repointed
`drug_lipid` reproduces the exact gold `sum_lipid` 15.790645 and `ratio` 0.841429; rounding
`pct_assay` to 2dp first gives 0.841433 (wrong). The 2-dp gold figures (99.98 etc.) are the
sheet's DISPLAY rounding and are asserted in the parity test with `abs=1e-2` tolerance against
the unrounded value (matching the existing test's `99.979 abs=1e-2` pattern).

### D7. Rows config
`lipid_samples.rows = {min: 4, max: 16, default: 8}` — SET blocks of exactly 4 rows, default 2
SETs (8 rows), extensible to 4 SETs (16). `drug_lipid.rows = {min: 1, max: 8, default: 2}` —
one row per SET, default aligned to 2 SETs.

### D8. `drug_lipid` repointing only
`<c>_mgml` changes from `lipid_samples.<c>_mean[rowno - 1]` to
`lipid_samples.pct_assay[(rowno - 1) * 4 + <idx>]` (tri idx 0, dppg 1, chol 2, depc 3).
`sum_lipid`, `pct_assay_bupi`, `mgml_bupi`, `ratio` are UNCHANGED. **Proved** against gold.

### Scope guard (do NOT touch)
`standard`, `std_areas`, `bkt_areas`, `stats`, the context header, the 8 SST criteria, the
frontend, and any other template. `resultRef` stays `drug_lipid.ratio`.

---

## Implementation items

- [ ] 1. Rewrite `_lipid_sample_fields()` to the tall per-SET layout in
      `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`.
      Add a small module-level helper `_compound_select(per_compound: Callable[[int,str],str])`
      that returns `coalesce(if(cidx == 0, f(0,'tri'), blank()), … k=1,2,3)` so the compound
      name, LC and %Assay selections share one builder. Keep `_assay_expression(prefix,
      area_key)` (used per-branch with `area_key="area"`) — it already produces the exact
      algebra; only its caller changes. New field list, in column order SET, Compound Name, LC,
      Avg Weight, Sample Weight, Vol, Pip, Vol, Area, % Assay:
        - `set_no` — input, type text, label "SET".
        - `cidx` — calculated, `hidden: True`, expression `rowno - 1 - trunc((rowno - 1) / 4, 0) * 4`.
        - `compound_name` — calculated, type text, label "Compound Name",
          `labelFrom: "standard.name[0]"`, expression `_compound_select(lambda k,_: f"standard.name[{k}]")`.
        - `lc` — calculated, label "LC", expression `_compound_select(lambda k,p: f"lc_{p}")`.
        - `avg_weight` — input, label "Avg Weight", default 1.005.
        - `sample_weight` — input, label "Sample Weight", unit "mg".
        - `vol_j` — input, label "Vol", unit "mL", default 25, `mirrorFrom: "<first row of SET>"` (UI hint only; see note).
        - `pip_k` — input, label "Pip", unit "mL", default 1.
        - `vol_l` — input, label "Vol", unit "mL", default 1.
        - `area` — kind area, label "Area", `labelFrom: "standard.name[0]"` (header tracks compound via frontend).
        - `pct_assay` — calculated, label "% Assay", unit "%", expression
          `_compound_select(lambda k,p: _assay_expression(p, "area"))`, NO `rounding` key (D6).
      For `avg_weight/sample_weight/vol_j/pip_k/vol_l` optionally add `mirrorFrom` pointing at
      the SET's first row IF a clean per-SET frontend expression exists; if not, omit
      `mirrorFrom` (it is UI-only and never affects the result — D2). Rewrite the docstring to
      describe the tall per-SET layout and delete the stale inj-1/inj-2/%Mean prose.
      Files: scripts/template_definitions/a2_bupivacaine_lipid_ratio.py
      Verify: `python -c "import sys; sys.path.insert(0,'.'); from scripts.template_definitions.a2_bupivacaine_lipid_ratio import LIPID_RATIO_DEFINITION as d; from src.domain.services.calculation.template_schema import TemplateDefinition; from src.domain.services.calculation.evaluator import WorksheetEvaluator as E; p=TemplateDefinition.parse(d); E(p).evaluate({},{}); print('parses+runs empty OK')"` prints OK with no exception.

- [ ] 2. Update the `lipid_samples` group dict in `LIPID_RATIO_DEFINITION` to the new rows
      config: `"rows": {"min": 4, "max": 16, "default": 8}`. Remove any `labelFrom` on the group
      that references a now-deleted field (the group currently has none; leave `kind`/`label`
      "Sample Details" unchanged). Update the inline comment above the group to "tall, SET blocks
      of 4 compound rows; default 2 SETs".
      Files: scripts/template_definitions/a2_bupivacaine_lipid_ratio.py
      Verify: same parse+run command as item 1 still prints OK (schema accepts the rows spec).

- [ ] 3. Repoint `_drug_lipid_fields()` source refs ONLY. Change each `<c>_mgml` expression from
      `lipid_samples.<c>_mean[rowno - 1] * lc_<c> / 100` to
      `lipid_samples.pct_assay[(rowno - 1) * 4 + <idx>] * lc_<c> / 100`, where `<idx>` is the
      compound's position in `_COMPOUNDS` (tri 0, dppg 1, chol 2, depc 3 — already available as
      the loop `idx`). Leave `sum_lipid`, `pct_assay_bupi`, `mgml_bupi`, `ratio` and the group's
      `label`/`kind` untouched. Set the group rows to `{"min": 1, "max": 8, "default": 2}` to
      align default rows to 2 SETs. Update the `I18` comment to note it now reads the per-SET,
      per-compound `% Assay` from the tall `lipid_samples`.
      Files: scripts/template_definitions/a2_bupivacaine_lipid_ratio.py
      Verify: same parse+run command prints OK (indexing `pct_assay` resolves; empty worksheet
      yields no blocking failure and blank reportable).

- [ ] 4. Replace the `TestA2_0004TabularParity` fixture + assertions in
      `tests/calculation/test_a2_0004_tabular_parity.py` with the tall-layout shape, keeping
      every unchanged gold value. Keep `STANDARD`, `STD_AREAS`, `BKT_AREAS`, `CONTEXT` exactly as
      they are. Change `LIPID_SAMPLES` to FOUR rows (SET 1 = tri/dppg/chol/depc), each with
      `set_no:"1"`, the shared prep values (avg_weight 1.005, sample_weight 1.5008, vol_j 25,
      pip_k 1, vol_l 1) repeated on all four rows, and the per-row `area` = 8729574 / 3826195 /
      32474189 / 44235393 respectively. Keep `DRUG_LIPID` as one row. Update assertions:
        - `test_standard_concentrations`, `test_std_area_column_means`, `test_bkt_pooled_tricaprylin`,
          `test_stats_indirection_still_resolves` — UNCHANGED (those groups are untouched).
        - Replace `test_batch_b_percent_assay_inj1` with per-row `pct_assay` asserts:
          row 0 ≈ 99.979, row 1 ≈ 86.200, row 2 ≈ 101.772, row 3 ≈ 100.390, all `abs=1e-2`
          (so the 2-dp sheet gold 99.98/86.20/101.77/100.39 is satisfied). Add a row that asserts
          `cidx` = 0/1/2/3 and `compound_name` = the four names and `lc` = 2/0.9/4.7/8.2.
        - `test_drug_lipid_ratio_chain` — UNCHANGED gold: tri_mgml ≈ 1.99958, sum_lipid ≈
          15.790645, mgml_bupi ≈ 13.2867, ratio ≈ 0.841429, reportable ≈ 0.841429 (all `abs=1e-4`).
          These now flow from the repointed index into unrounded `pct_assay` (D6).
        - `test_suitability_does_not_block_on_this_data` — UNCHANGED.
      Update the module docstring to describe the tall Sample Details layout. Keep the "derived by
      hand, not copied from a run" discipline in comments.
      Files: tests/calculation/test_a2_0004_tabular_parity.py
      Verify: `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q` — all tests
      pass.

- [ ] 5. Run the catalogue-wide seeded-template parity + schema suite to confirm nothing else
      regressed (the stats/criteria/resultRef invariants, and the A12 class that reads the same
      workbook family).
      Files: (none — verification only)
      Verify: `python -m pytest tests/calculation -q` — all pass; in particular
      `test_seeded_template_parity.py` still green (every template parses, runs empty, has a
      resolvable reportable, area fields discoverable).

- [ ] 6. Validate the seeder dry-run so the module is provably loadable the way the seeder loads
      it.
      Files: (none — verification only)
      Verify: `python -m scripts.seed_test_templates --validate-only` — exits 0 and prints an
      `ok TPL-A2-0004 [A2] …` line (the describe() counts will reflect fewer calculated fields
      than before, which is expected).

- [ ] 7. Create the DB sync script `scripts/update_a2_0004_definition.py`, modelled exactly on
      the existing `scripts/update_a6b_definition.py`. It must: import `BUPI_LIPID_RATIO` from
      `scripts.template_definitions.a2_bupivacaine_lipid_ratio`; `definition_json =
      json.dumps(BUPI_LIPID_RATIO.definition)`; open `lims.db` with sqlite3; read the
      `(id, code, archetype, version, status, test_id)` identity tuple for `code='TPL-A2-0004'`
      (which is DB row id 35) BEFORE; `UPDATE test_templates SET definition=?, modified_by=
      'a2-0004-tall', modified_date=? WHERE code='TPL-A2-0004'`; commit; assert exactly one row
      updated and the identity tuple is byte-for-byte unchanged (code/archetype/version/status/
      test_id/id all preserved — the seeder is additive and must NOT be used, and the app
      approve/e-sign flow must NOT be used). Do NOT change version or status. Print the preserved
      identity like the A6B script does.
      Files: scripts/update_a2_0004_definition.py
      Verify: the script is created and imports cleanly:
      `python -c "import sys; sys.path.insert(0,'.'); import scripts.update_a2_0004_definition as m; print('import OK', hasattr(m,'main'))"` prints `import OK True`.

- [ ] 8. Run the DB sync and assert canonical byte-equality against the module. The live DB row
      35 must end `json.dumps(module_def)`-equal to the source module (it currently is, for the
      OLD definition — this re-establishes it for the NEW one).
      Files: (writes lims.db row id 35 only)
      Verify: run `python -m scripts.update_a2_0004_definition` — prints "1 row updated" and
      "identity preserved". Then assert equality:
      `python -c "import sys,sqlite3,json; sys.path.insert(0,'.'); from scripts.template_definitions.a2_bupivacaine_lipid_ratio import BUPI_LIPID_RATIO as t; c=sqlite3.connect('lims.db'); stored=c.execute(\"select definition from test_templates where id=35\").fetchone()[0]; print('byte-equal:', stored==json.dumps(t.definition))"`
      prints `byte-equal: True`.

- [ ] 9. Re-read the live DB definition, parse and evaluate it end-to-end with the gold SET-1
      inputs to prove the stored row (not just the module) reproduces the gold values.
      Files: (none — verification only; reads lims.db)
      Verify: a one-off check that loads row 35's `definition` JSON, `TemplateDefinition.parse`s
      it, runs `WorksheetEvaluator(...).evaluate(CONTEXT, groups)` with the item-4 fixture
      (STANDARD/STD_AREAS/BKT_AREAS + the 4-row SET-1 lipid_samples + 1-row drug_lipid), and
      asserts `lipid_samples` row %Assay ≈ 99.98/86.20/101.77/100.39 (`abs=1e-2`) and
      `drug_lipid` ratio ≈ 0.841429 (`abs=1e-4`) and `has_blocking_failure is False`. Expected:
      all asserts pass, confirming the live DB row is formula-exact.

---

## Evidence to leave in `.agents/tasks/a2-0004-sample-details-tall/`
- This `plan.md`.
- (Implementer) a short `evidence.md` capturing: the `pytest tests/calculation` summary line,
  the `--validate-only` exit, the "1 row updated / identity preserved" output, the
  `byte-equal: True` line, and the item-9 live-DB gold re-check output.

## Notes / assumptions
- `(rowno-1) mod 4` uses `trunc(x, 0)` because the engine exposes `trunc` but no `mod`; proven
  to yield 0/1/2/3 across rows 1-8.
- `pct_assay` is intentionally left UNROUNDED (D6); if a future requirement wants a stored 2-dp
  value, add a separate display field rather than rounding the value `drug_lipid` consumes.
- `mirrorFrom` on the shared prep inputs is optional and UI-only; omit it if no clean per-SET
  frontend expression exists — it has zero effect on computed results.
- The task says row id 35; it was confirmed to be `TPL-A2-0004`, v1, Active, test_id 32, and its
  stored definition currently equals `json.dumps(module_def)` for the old definition. The sync
  script keys on `code='TPL-A2-0004'` (which is id 35) so it is robust if ids ever shift.
