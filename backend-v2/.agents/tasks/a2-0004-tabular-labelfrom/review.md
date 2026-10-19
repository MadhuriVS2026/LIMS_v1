# TPL-A2-0004 tabular transpose of the standard/BKT injection blocks plus a generic `labelFrom` column-header resolver

This change turns the two injection blocks of TPL-A2-0004 (Bupivacaine Lipid Content & Drug-to-Lipid Ratio) from compounds-as-columns into compounds-as-rows, so a four-standard method reads as one row per compound with six injection columns and per-row Mean/SD/%RSD — the house rule the user asked for (tabular standard details when more than two standards). The `stats` singleton is rewired to pull each per-compound number out of the new row tables by index, keeping every `stats.*` key identical so the downstream %Assay chain and the eight SST criteria are untouched. On the frontend, a new optional `labelFrom` field property lets a column header (or singleton label) source its text from a worksheet value — applied here so the per-compound `lipid_samples` and `drug_lipid` columns display the compound names fetched from Standard Details, and renaming a standard renames those columns. The DB row for the template is updated to equal the module definition byte-for-byte.

Watch for: nothing blocking. The full `tests/calculation` suite reports 5 failures, but they are **confirmed** pre-existing (TPL-A6B-0001 dissolution + two worksheet_service tests) — they contain no reference to TPL-A2-0004 and the coder reproduced them with the A2-0004 edit stashed. The new GxP parity test passes 7/7 and the frontend `tsc -b` build is green per recorded evidence.

**Verdict**: APPROVED

## High-level view

The backend transpose is numerically sound. The GxP verification report reproduces all 19 gold targets (standard concentrations, per-row std means, pooled BKT mean/%RSD, the full batch-B %Assay → %Mean → drug/lipid ratio chain, and the reportable) to each value's display precision, with no blocking SST failure on this data. The transpose relies on the engine exposing a table group as column series: per-row stats evaluate a list literal of that row's `inj_1..inj_6`, and the pooled BKT stats index the matching std row via `std_areas.inj_k[rowno - 1]`, flattening both lists with `pool(...)` which drops blanks. The pooled Tricaprylin mean of 8699733.9 (6 std + 4 bkt over 10) matches sheet H31.

The `stats` singleton keeps every key (`mean_std_tri`, `rsd_pool_depc`, …) and only swaps each expression to read `std_areas.<stat>[idx]` / `bkt_areas.<stat>[idx]`. Because the keys are preserved, the `lipid_samples` %Assay expressions and the eight %RSD criteria are structurally unchanged, which the parity test confirms end-to-end through the indirection.

The DB row and the module are byte-for-byte equal — independently confirmed here (`stored_text == json.dumps(LIPID_RATIO_DEFINITION)` is True; single row, id 35, v1, Active). So the definition an analyst runs is the one that was verified.

`labelFrom` is a UI-only, additive property: `WorksheetForm` only consults it when a field declares it, falling back to the static `label ?? key` otherwise, so every existing template renders headers exactly as before. The resolver is generic — it parses `"<group>.<field>"` with an optional `[idx]` and reads the computed (then entered) value — with no template code or compound name hardcoded. It's applied to the right columns with the right indices (`standard.name[0..3]` for tri/dppg/chol/depc on the `lipid_samples` area/assay/mean columns and the `drug_lipid` `<c>_mgml` columns); the transposed row tables correctly use `mirrorFrom` on the compound cell instead of `labelFrom` on a header.

Scope is respected: only the A2-0004 module, its DB row, and the two frontend files (plus the new parity test) changed. No other template or Test was touched.

<details>
<summary>Issues (0)</summary>

No blocking or non-blocking action items. All gold targets reproduce, DB parity holds byte-for-byte, scope is respected, and the recorded frontend build is green.

</details>

<details>
<summary>Details</summary>

## Numeric parity of the transpose (all gold targets)

The verification report is the authoritative numeric evidence and it was not re-run here. It records OVERALL PASS with all 19 gold targets reproducing: the four `standard.conc_ppm` values exactly (118.92 / 54.03 / 285.1 / 489.25, rounded 2dp by the template), the four `std_areas.mean` rows, the pooled `bkt_areas` Tricaprylin mean (8699733.9) and %RSD (≈0.2383), the four batch-B inj-1 %Assay values, and the drug/lipid chain down to the reportable ratio 0.841429 — each compared at its own display precision, with sub-rounding differences in the Note column. No target is FAIL and none is missing, so question (1) passes.

The new `test_a2_0004_tabular_parity.py` locks these same targets with hand-derived golds (not run-copied), asserting through the `stats` indirection — e.g. `stats.mean_std_tri == std_areas.mean[0]` and the batch-B %Assay values — which is exactly the regression guard a GxP transpose needs.

## Row-based tables and the pooled BKT expressions

`std_areas` and `bkt_areas` each become a table with a `compound` cell (`mirrorFrom: "standard.name"`, read-only), six `inj_1..inj_6` area columns, and `mean`/`sd`/`rsd`. `std_areas` per-row stats are `mean([inj_1..inj_6])` etc. — a list literal of the current row's cells. `bkt_areas` pools each row with the same compound's std row:

```
mean(pool([std_areas.inj_1[rowno - 1], ... std_areas.inj_6[rowno - 1]], [inj_1, ... inj_6]))
```

`rowno` is the evaluator-injected 1-based row index, so `[rowno - 1]` selects the aligned std row — valid because `standard`, `std_areas`, and `bkt_areas` are ordered identically (tri/dppg/chol/depc). Blank BKT injections (inj_5/inj_6) are dropped by `pool`, matching the sheet's `AVERAGE(H25:H30,B25:B30)`. The `rows` spec moves to `{min:1, max:10, default:4, labelFrom:"compound"}`, which supports the "more than two standards" rule without an upper surprise.

## `stats` singleton: keys preserved, source moved

Every field keeps its key, label, and unit; only the expression changes from a per-column `mean(std_areas.<c>_area)` to a per-row `std_areas.mean[idx]` (and `bkt_areas.<stat>[idx]` for the pooled set), with `idx` from `enumerate(_COMPOUNDS)`. Because the keys are stable, the `lipid_samples` %Assay expressions and the eight criteria didn't need to change, and the parity test's batch-B assertions confirm the whole chain still resolves through the indirection. This answers question (3).

## `labelFrom` resolver — generic and backward-compatible

`FieldDef` gains an optional `labelFrom?: string`. `WorksheetForm` adds `resolveLabelFrom(spec, rowIndex)` which regex-parses `"<group>.<field>"` with an optional `[idx]`; with an index it reads `computed.rows[group][idx][field]` (falling back to editable `values[group][idx][field]`), trims, and returns `null` when blank. `headerText(field, rowIndex)` uses the resolved text only when `labelFrom` is set and resolves non-blank, otherwise `field.label ?? field.key`. It's wired at all three header sites (table `<th>`, singleton editable label, singleton calculated label). Nothing is hardcoded to this template, and existing templates — which never set `labelFrom` — take the unchanged fallback path, so headers render as before. This answers question (5).

The module applies `labelFrom: "standard.name[idx]"` to the correct columns with the correct indices: `lipid_samples` `<c>_area1/area2/assay1/assay2/mean` and `drug_lipid` `<c>_mgml`, with tri=0/dppg=1/chol=2/depc=3. The transposed row tables deliberately get no `labelFrom` (their compound identity is a `mirrorFrom` row cell), which is the right call. Because a table column header is rendered once per column (rowIndex defaults to 0), the explicit `[idx]` suffix is what carries the correct compound regardless of row — consistent with how it's used here.

## DB-vs-module parity and scope

Independently confirmed here against `lims.db` (read-only): the stored `definition` for `code='TPL-A2-0004'` equals `json.dumps(LIPID_RATIO_DEFINITION)` byte-for-byte and structurally, there is exactly one such row (id 35, v1, Active). So the row an analyst executes is the verified definition. `git status` shows only the A2-0004 module, the two frontend files, and the new parity test as the code changes; no other template or Test is modified. This answers question (2).

## Build and suite evidence (recorded, not re-run)

Per the implementation evidence, the frontend `npm run build` (`tsc -b && vite build`) exits 0 with zero TS errors (the >500 kB chunk note is a pre-existing advisory), answering question (6). The backend `--validate-only` parse/dry-run passes for all templates and the new parity test is 7/7. The full `tests/calculation` run reports 5 failures in TPL-A6B-0001 dissolution and two worksheet_service tests; these are **confirmed** pre-existing — a grep shows none reference TPL-A2-0004, and the coder reproduced the identical failures with the A2-0004 edit stashed. They are out of scope for this change.

</details>

<details>
<summary>File map</summary>

- `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` — transposed `std_areas`/`bkt_areas` to compounds-as-rows with per-row (and pooled) Mean/SD/%RSD; rewired `stats` to index the row tables; added `labelFrom` to `lipid_samples`/`drug_lipid` per-compound columns.
- `backend-v2/lims.db` — single `test_templates` row `code='TPL-A2-0004'` (id 35, v1, Active) `definition` updated to equal the module byte-for-byte.
- `frontend-react/src/features/test-templates/models/testTemplate.types.ts` — added optional `labelFrom?: string` to `FieldDef`.
- `frontend-react/src/features/test-templates/components/WorksheetForm.tsx` — added generic `resolveLabelFrom`/`headerText` helpers and applied them at the three header render sites.
- `backend-v2/tests/calculation/test_a2_0004_tabular_parity.py` (new) — hand-derived GxP parity test for the transposed layout and the stats indirection.

Full diff: `git diff HEAD -- backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py frontend-react/src/features/test-templates/components/WorksheetForm.tsx frontend-react/src/features/test-templates/models/testTemplate.types.ts`

</details>
