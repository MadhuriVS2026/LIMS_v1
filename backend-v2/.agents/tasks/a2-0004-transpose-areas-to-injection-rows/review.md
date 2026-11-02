# Transpose TPL-A2-0004 std_areas / bkt_areas to injection-rows × compound-columns

This change flips the two injection blocks of template TPL-A2-0004 (Bupivacaine Lipid Content & Drug-to-Lipid Ratio) from compounds-as-rows to injections-as-rows / compounds-as-columns, per the user's explicit request (messages 11-12). Each injection is now a row (Injection 1..N, expandable to 12, default 6) and each lipid compound gets one AREA column (`tri_area`, `dppg_area`, `chol_area`, `depc_area`), whose header auto-fetches the compound name from Standard Details via `labelFrom="standard.name[<idx>]"`. Per-compound Mean/SD/%RSD moved out of per-row calculated fields into the `stats` singleton as whole-column aggregates and render in each group's footer; the BKT footer pools each compound column with its std counterpart. The `stats.*` keys are unchanged, so the downstream %Assay chain and the 8 SST criteria are untouched; only each stat's source expression moved. Live DB row id 35 was updated byte-for-byte from the serialized module, and the parity test was re-fixtured to the new layout with gold values held constant.

Watch for: nothing blocking. The design hinges on the engine's column-series semantics (`mean(std_areas.tri_area)` aggregating down the column, blanks skipped) and on footers being calculation-inert — both independently confirmed (confirmed). All gold values reproduce per the evidence and the DB row matches the module exactly (confirmed).

**Verdict**: APPROVED

## High-level view

The orientation flip is implemented exactly as the plan locked it (D1-D8). `_area_columns()` emits the four compound AREA columns in `_COMPOUNDS` order with the correct `labelFrom` indices (tri 0, dppg 1, chol 2, depc 3); both `std_areas` and `bkt_areas` now use `[inj_label, *_area_columns()]` with expandable rows `{min:1, max:12, default:6, labelFrom:"inj_label"}`. The old per-row `compound`/`inj_1..6`/`mean`/`sd`/`rsd` fields and the `_INJ_COLUMNS`/`_injection_columns()`/`_inj_list()` helpers are gone with no dangling references.

The statistics moved from per-row table cells to per-column aggregates in the `stats` singleton. Std stats are `mean|sd|rsd(std_areas.<c>_area)`; pooled BKT stats are `mean|sd|rsd(pool(std_areas.<c>_area, bkt_areas.<c>_area))`. This is the correct engine idiom: the evaluator exposes each multi-row group field as a column series and its own docstring names `mean(standard.area)` and `rsd(pool(std.area, bkt.area))` as the supported shapes. Because Mean/SD/%RSD live in the footer (a frontend-only pass-through the backend parser ignores) and not in data rows, each column series holds only injection values, so the whole-column aggregate spans exactly the intended range and adapts to the expandable row count.

The `stats.*` keys (`mean_std_<c>`, `sd_std_<c>`, `rsd_std_<c>`, `mean_pool_<c>`, `sd_pool_<c>`, `rsd_pool_<c>`), labels, and units are unchanged. The `_assay_expression` chain and the 8 SST `_rsd_criterion` entries still reference those keys untouched, so the %Assay and ratio chains carry through with no edit.

Gold values reproduce to the sheet's rounding per the parity test (7/7), and the test's expectations are hand-derived from the workbook rather than copied from a run, so they constrain the code rather than pin it. The live DB row id 35 definition is byte-for-byte equal to the serialized module and its identity `(35, TPL-A2-0004, 1, Active)` is unchanged. Scope is limited to the module, the parity test, and the DB row; the working tree is committed clean with no throwaway scripts left behind.

<details>
<summary>Issues (0)</summary>

No blocking or non-blocking findings. Every checklist item verified.

</details>

<details>
<summary>Details</summary>

## Orientation flip and column headers

`_area_columns()` builds the four AREA columns from `enumerate(_COMPOUNDS)`, giving `tri_area`/`dppg_area`/`chol_area`/`depc_area` in that order, each with `kind:"area"`, unit `µV·s`, and `labelFrom=f"standard.name[{idx}]"` — idx 0/1/2/3 matching tri/dppg/chol/depc (confirmed, item 1 and 2). Both `_std_area_fields()` and `_bkt_area_fields()` return `[{inj_label text input}, *_area_columns()]`, and both group dicts carry `rows {min:1, max:12, default:6, labelFrom:"inj_label"}` via `_MAX_INJ_ROWS`/`_DEFAULT_INJ_ROWS` (confirmed). `inj_label` is a real field in each group, satisfying the schema rule that `rows.labelFrom` must name one of the group's own fields. The removed `compound` mirror, `inj_1..6`, and per-row `mean`/`sd`/`rsd` are gone, and the dead `_INJ_COLUMNS`/`_injection_columns()`/`_inj_list()` helpers were deleted — the diff shows no remaining references to them.

Mean/SD/%RSD render as a group footer (the plan's preferred approach), one `ref` per compound column, keyed to the `stats` singleton. A fake Mean/SD/%RSD data row would have been swept into `mean(std_areas.<c>_area)` and corrupted the aggregate; the footer avoids that because the backend parser ignores `footer` entirely (confirmed).

## Statistics as per-column aggregates with pooled BKT

`_stats_fields()` now emits, per compound, `mean_std_<c> = mean(std_areas.<c>_area)`, `sd_std_<c> = sd(...)`, `rsd_std_<c> = rsd(...)`, and the pooled trio `mean|sd|rsd(pool(std_areas.<c>_area, bkt_areas.<c>_area))` (confirmed, item 3). The engine idiom is sound: `evaluator.py` exposes every multi-row group field as a column series (`group.field` → list down the rows) and its module docstring cites `mean(standard.area)` and `rsd(pool(std.area, bkt.area))` as the exact shapes this enables. `_f_pool` flattens the two series and `_f_mean`/`_numeric` skip blanks, which is why BKT with only 4 filled rows pools correctly against the 6 std rows — `(52148721 + 34848618) / 10 = 8699733.9` for Tricaprylin, matching the sheet's `AVERAGE(H25:H30,B25:B30)`.

The pooling for the std stats correctly uses only `std_areas`, and the BKT footer references the pooled keys (`stats.*_pool_*`) — so the pooled Mean/SD/%RSD show under the BKT block as the sheet does, computed from std+bkt together (confirmed, item 3).

## stats keys unchanged; downstream chains untouched

The six `stats.*` key patterns, labels, and units are identical to the base; only the right-hand expression moved from `std_areas.mean[idx]` / `bkt_areas.mean[idx]` to the column aggregates (confirmed, item 4). `_assay_expression` still divides by `stats.mean_std_<prefix>` and the eight `_rsd_criterion` entries still target `stats.rsd_std_<c>` / `stats.rsd_pool_<c>` — none of that code changed in the diff. The %Assay chain and the ratio chain therefore carry through unmodified.

## Gold values and the parity test

The rewritten `test_a2_0004_tabular_parity.py` feeds `STD_AREAS` (6 injection rows) and `BKT_AREAS` (4 injection rows), and its assertions reproduce the full gold set per the evidence (confirmed, item 5): Std Conc Tri 118.92 / DPPG 54.03 / Chol 285.1 / DEPC 489.25; std_areas Mean Tri 8691453.5 / DPPG 4461370.5 / Chol 32403414.83 / DEPC 44013385.5; pooled Tri Mean 8699733.9, %RSD 0.2383; Batch EP20_117-299-B %Assay 99.979 / 86.200 / 101.772 / 100.390; Drug/Lipid Tri mg/mL 1.99958, Sum of Lipid 15.790645, mg/mL Bupivacaine 13.2867, Ratio 0.841429; and `has_blocking_failure is False`. The column-mean and pooled assertions now read `result.values["stats.*"]` since the per-row `mean`/`rsd` fields no longer exist. The test docstring states the expectations are derived by hand from the workbook dump rather than copied from a run, so they constrain behavior rather than pin it. Per the task instruction I did not re-run the parity suite; the evidence reports 7/7 and the fixtures/assertions in the file are consistent with that.

## DB row 35 byte-for-byte parity

Independently spot-checked against the live DB: row id 35 reads `(35, TPL-A2-0004, 1, Active)` and its `definition` text is `exact True` against `json.dumps(LIPID_RATIO_DEFINITION)` and `normalized True` against the loaded dict (confirmed, item 6). The update used the ORM path (same serializer as seeding), status/version/approval columns untouched.

## Scope and commit

Tracked changes are exactly the module and the parity test (`git show --stat` and `git diff HEAD` confirm nothing else staged/committed and the working tree is clean) (confirmed, item 7). Untracked files are all under `.agents/` task/evidence directories; no throwaway script remains in the source tree (the plan's one-shot DB updater was removed). A local, unpushed commit exists at `7e3e270053634fde066b83df3f00476a8df6837f` with a clear message describing the transpose, the stats move, the pooling, and the verification results (confirmed, item 9).

## Suite failure count

Per the evidence, the full `tests/calculation` suite is 5 failed / 760 passed, and the 5 failures are the known pre-existing A6B dissolution and worksheet_service cases unrelated to this template (confirmed from evidence, item 8). Per the task instruction I did not re-run the full suite; nothing in the diff touches the engine, `_common.py`, or any other template, so there is no plausible path for this change to alter that count.

</details>

<details>
<summary>File map</summary>

- `backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` — transpose of `std_areas`/`bkt_areas` to injection-rows × compound-columns; new `_area_columns()` helper; stats moved to per-column aggregates + pooling; docstring/comments updated; dead injection-column helpers removed.
- `backend-v2/tests/calculation/test_a2_0004_tabular_parity.py` — fixtures re-shaped to injection rows; column-mean / pooled assertions read `stats.*`; gold values unchanged.
- `backend-v2/lims.db` (gitignored) — row id 35 `definition` column updated byte-for-byte from the module; identity unchanged.

Full diff: `git show 7e3e270053634fde066b83df3f00476a8df6837f`.

</details>
