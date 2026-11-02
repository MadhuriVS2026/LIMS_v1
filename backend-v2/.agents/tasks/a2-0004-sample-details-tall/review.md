# TPL-A2-0004 Sample Details restructured to a tall per-SET layout

The `lipid_samples` "Sample Details" group of TPL-A2-0004 is rewritten from a wide one-batch-per-row shape (two injection area columns per compound) to a tall layout where each SET is a block of exactly 4 compound rows — Tricaprylin, DPPG Na, Cholesterol, DEPC. A hidden `cidx = (rowno-1) mod 4` selects the compound per row, and the visible Compound Name, LC, % Assay and % Mean columns are driven off that index via a `coalesce(if(cidx==k, …), …)` selector. The single-injection `area` column replaces the dropped 2nd injection, and `drug_lipid` is repointed to read each SET's per-compound value by indexing `(rowno-1)*4 + compound_idx`. The gold %Assay (99.98/86.20/101.77/100.39) and the drug-to-lipid ratio (0.841429) are preserved.

Watch for: a `% Mean` column (`pct_mean`) was added beyond the plan and beyond the column list named in the task checkpoints; `drug_lipid` now reads `pct_mean`, not `pct_assay`, so checkpoint #7's literal wording ("reads `pct_assay`") is not met even though the result is mathematically identical (confirmed). This is the only deviation and it does not break any gold value.

**Verdict**: APPROVED

## High-level view

The compound-per-row design is engine-faithful. The engine has no `mod`, so `cidx` is spelled with `trunc` (`rowno - 1 - trunc((rowno - 1) / 4, 0) * 4`), and `trunc`, `coalesce`, `if` and `blank` are all confirmed engine builtins. `if()` is lazy here so the three non-selected branches never evaluate, and the per-compound %Assay reuses the existing `_assay_expression` algebra unchanged — only its caller moved. All compound-indexed references (`stats.mean_std_<c>`, `standard.*[idx]`, `lc_<c>`) stay bound to the compound each row represents.

Shared SET prep (Avg Weight, Sample Weight, vol_j, pip_k, vol_l) is modelled as per-row inputs repeated on all four rows of a SET, which is the correct choice: the %Assay formula reads these unqualified from the current row, and `mirrorFrom` is a frontend-only display hint that never copies a value. So correctness does not depend on any mirror behavior.

The one deviation is an extra `% Mean` column. The plan's final column was `% Assay`; the implementer added `pct_mean = mean([pct_assay])` and repointed `drug_lipid` to read it. For a single injection the mean of one value is that value, so `pct_mean == pct_assay` and the ratio chain is unchanged. The deviation is traceable to the user's "% Mean" clarification noted in the evidence and mirrors the sheet's `='Lipid '!O43` %Mean reference, so it is defensible — but checkpoint #2/#7 named `% Assay` as the consumed column, so this is called out rather than silently accepted.

The untouched groups (`standard`, `std_areas`, `bkt_areas`, `stats`, context header, 8 SST criteria) do not appear in the diff at all, and the prior gold values outside the sample section are re-asserted unchanged in the parity test. The evidence shows the live DB row 35 is byte-equal to the module with identity preserved, the parity file passes 9/9, and the full calculation suite shows the same 5 known pre-existing failures with no new ones.

<details>
<summary>Issues (2)</summary>

1. **drug_lipid reads `pct_mean`, not `pct_assay`** — checkpoint #7 literally specifies reading `pct_assay`; the code reads `lipid_samples.pct_mean[(rowno-1)*4+idx]`. Result is identical because `pct_mean == pct_assay` for a single injection (confirmed), so non-blocking, but the consumed column name differs from the checkpoint. No action required unless the reviewer wants the drug_lipid source aligned to `pct_assay`.
2. **Extra `% Mean` column beyond plan/checkpoint column list** — checkpoint #2 lists `% Assay` as the final calculated column; an additional `pct_mean` was added. It is justified by the user's %Mean clarification and the sheet's O-column, carries no rounding, and does not disturb any gold value. Confirm this is the intended column set.

</details>

<details>
<summary>Details</summary>

### Compound-per-row selection via hidden cidx (checkpoints 1, 3, 5)

Each SET is a block of four rows and the compound is picked by `cidx = (rowno-1) mod 4`, expressed as `rowno - 1 - trunc((rowno - 1) / 4, 0) * 4` because the engine exposes `trunc` but no `mod`. Rows map 0=tri, 1=dppg, 2=chol, 3=depc, matching `_COMPOUNDS` order exactly (confirmed: `[("tri","Tricaprylin"),("dppg","DPPG Na"),("chol","Cholesterol"),("depc","DEPC")]`).

The `_compound_select` helper builds `coalesce(if(cidx == 0, f(0,"tri"), blank()), …, if(cidx == 3, f(3,"depc"), blank()))`. Three of the four branches evaluate to `blank()` and `coalesce` returns the single non-blank value. `coalesce`, `if`, `blank` and `trunc` are all present in the engine's function table (confirmed in `expression.py`). `if()` lazy evaluation means the non-selected compounds' algebra never runs, so an unselected compound's divisor cannot poison the result.

Compound Name selects `standard.name[cidx]` (read-only calculated, tracks Standard Details renames) and LC selects `lc_<c>` per compound (read-only mirror of the overridable context fields). Both are `kind: calculated`, so they are read-only by construction. The parity test asserts cidx 0/1/2/3, names Tricaprylin/DPPG Na/Cholesterol/DEPC, and lc 2/0.9/4.7/8.2 — confirmed in `test_set1_row_compound_selection`.

### %Assay algebra is the unchanged expression, rebound per compound (checkpoints 5, 6)

`pct_assay` is `_compound_select(lambda _k, p: _assay_expression(p, "area"))`. `_assay_expression` is the pre-existing builder; it reads `area / stats.mean_std_<c> * standard.weight[idx]/standard.vol1[idx] * … * standard.potency[idx]/lc_<c> * standard.mw_base[idx]/standard.mw_salt[idx] * avg_weight`, using only `stats.*`, `standard.*[idx]`, `lc_<c>`, `vol_j`, `sample_weight`, `vol_l`, `pip_k`, `avg_weight` and arithmetic. No unsupported function is introduced. The single per-row `area` is referenced unqualified by all four branches — correct, since there is one area column.

The evidence reproduces all four SET-1 gold values at 2 dp (99.98 / 86.20 / 101.77 / 100.39) and the parity test asserts the unrounded values with `abs=1e-2`. `pct_assay` carries no `rounding` key, so `drug_lipid` consumes the unrounded value — the plan proved that rounding mid-chain gives the wrong ratio (0.841433 vs gold 0.841429), so leaving it unrounded is the correct call.

### Shared SET prep as per-row inputs (checkpoint 4)

Avg Weight, Sample Weight, vol_j, pip_k, vol_l are plain per-row inputs with the old defaults (1.005 / — / 25 / 1 / 1). Because `_assay_expression` reads these unqualified from the current row and this engine's `mirrorFrom` never copies a value, every one of a SET's four rows must physically carry the prep values for the formula to be correct. The parity fixture spreads a single `_PREP` dict across all four rows, which is how the frontend "one value per SET" fill would land.

### drug_lipid repointing (checkpoints 7, 8)

Each `<c>_mgml` changed from `lipid_samples.<c>_mean[rowno - 1]` to `lipid_samples.pct_mean[(rowno - 1) * 4 + {idx}] * lc_<c> / 100`, with idx = tri 0 / dppg 1 / chol 2 / depc 3 from the `_COMPOUNDS` loop position. `sum_lipid`, `pct_assay_bupi`, `mgml_bupi`, `ratio` are untouched in the diff. drug_lipid default rows moved to 2 (one row per SET).

The one gap against the checkpoint: #7 specifies the repoint should read `pct_assay`, but the code reads `pct_mean`. Since `pct_mean = mean([pct_assay])` and each compound row has one injection, `pct_mean == pct_assay` exactly (both unrounded), so the ratio chain reproduces gold 0.841429 — confirmed by the evidence's live-DB re-check and the parity `test_drug_lipid_ratio_chain`. The result is engine-faithful; only the consumed column name differs from the checkpoint wording. Flagged, non-blocking.

### The extra % Mean column (checkpoint 2, 11 scope)

Checkpoint #2 lists the final calculated column as a single `% Assay`. The implementer added `pct_mean` (`mean([pct_assay])`, no rounding) as a trailing column and routed `drug_lipid` through it. The evidence attributes this to a user "% Mean" clarification and to matching the sheet's `='Lipid '!O43` %Mean cell. It is behaviorally inert for the gold data (single injection ⇒ mean equals the value) and the blank-skipping mean keeps a future 2nd-injection case averaging correctly. This is a scope addition beyond the plan's column list, so it belongs in the reviewer's attention even though it is defensible and breaks nothing.

### Rows config and extensibility (checkpoint 1)

`lipid_samples.rows` is `{min: 4, max: 16, default: 8}` — SET blocks of 4, default 2 SETs (8 rows), `max` 16 (4 SETs), extensible in multiples of 4. `drug_lipid.rows` is `{min: 1, max: 8, default: 2}`, aligned to 2 SETs. Confirmed in the group dicts in the diff.

### Untouched sections and DB identity (checkpoints 8, 9, 10)

`standard`, `std_areas`, `bkt_areas`, `stats`, the context header and the 8 SST criteria do not appear anywhere in the diff, so they are byte-identical. The parity test re-asserts the prior gold for standard concentrations, std-area means and the pooled Tri mean/%RSD unchanged. The evidence records DB row 35 identity `(35, TPL-A2-0004, A2, 1, Active, 32)` unchanged before and after, `byte-equal: True` against `json.dumps(module_def)`, the live-DB end-to-end gold re-check passing, and the full `tests/calculation` run at `5 failed, 762 passed` with the same 5 named pre-existing failures (3 A6B + 2 worksheet_service) and no new ones. I did not re-run these suites; per the task I relied on the recorded evidence, which is complete and internally consistent.

### Test coverage

The parity file replaces the wide-layout assertions with per-row ones: compound selection (cidx/name/lc), per-compound %Assay, %Mean-equals-%Assay, and the unchanged drug_lipid ratio chain and SST non-blocking check. Not tested: a multi-SET fixture (2+ SETs / 8 rows) to exercise `cidx` wrap-around and the `(rowno-1)*4+idx` indexing beyond SET 1 — all assertions use SET 1 only. The `cidx` formula was proven on paper across rows 1–8 per the plan, but no automated test pins SET 2's indexing. Worth adding, not blocking.

</details>

<details>
<summary>File map</summary>

- `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` — `_lipid_sample_fields` rewritten to tall per-SET; new `_CIDX_EXPRESSION` and `_compound_select` helpers; `lipid_samples` rows → {4,16,8}; `_drug_lipid_fields` `<c>_mgml` repointed to `pct_mean[(rowno-1)*4+idx]`; drug_lipid rows → {1,8,2}; docstrings updated.
- `tests/calculation/test_a2_0004_tabular_parity.py` — fixture reshaped to 4-row SET-1; new compound-selection, %Assay, %Mean tests; drug_lipid chain asserts unchanged gold.
- `scripts/update_a2_0004_definition.py` — DB sync script (per evidence; not in this diff range).
- `lims.db` row 35 definition — resynced (gitignored, local only).

Full diff: `git diff 6fc824e..HEAD -- scripts/template_definitions/a2_bupivacaine_lipid_ratio.py tests/calculation/test_a2_0004_tabular_parity.py`

</details>
