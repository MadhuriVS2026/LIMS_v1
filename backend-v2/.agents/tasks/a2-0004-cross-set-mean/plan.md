# Implementation Plan — TPL-A2-0004: add a cross-set "% Mean (Compound)" column

## Goal (authoritative, per revised requirement)

Do **NOT** replace the existing `% Mean` column. Keep the current per-set
`pct_mean` field unchanged in semantics (expression `mean([pct_assay])` = that
row's own % Assay), relabel its header to **"% Mean (Set)"**, and **ADD** a new
calculated field `pct_mean_compound` labelled **"% Mean (Compound)"** immediately
after it. The new field is the cross-set mean: for each compound, the mean of
that compound's `pct_assay` in Set 1 and Set 2, displayed identically on BOTH of
that compound's rows. `drug_lipid` is **UNCHANGED** and keeps reading
`lipid_samples.pct_mean[(rowno-1)*4+idx]` (the per-set value), so the gold ratio
`0.841429` stays bound to the per-set mean until the user decides which mean is
canonical.

Both columns are visible so the user can compare them.

---

## Engine verification (DONE in this planning step — do not re-litigate)

Verified against the REAL engine (`TemplateDefinition.parse` +
`WorksheetEvaluator(...).evaluate(...)` from `backend-v2`), by temporarily
inserting `pct_mean_compound` after `pct_mean` in a deep-copied
`LIPID_RATIO_DEFINITION` and evaluating 8-row fixtures. Findings:

1. **Self-group cross-row absolute indexing IS supported directly.** In
   `evaluator.WorksheetEvaluator._build_scope`, every group — including the one
   being evaluated — is placed in scope as a column-series dict
   `scope["lipid_samples"] = {field: [values down the rows]}`. So from inside a
   `lipid_samples` row formula, `lipid_samples.pct_assay[k]` resolves to the
   whole `pct_assay` column indexed at absolute 0-based row `k`. This is the same
   mechanism `drug_lipid` already uses cross-group; it works same-group too.

2. **A field value is a valid index expression.** In
   `expression._Evaluator._resolve`, an index part is evaluated
   (`self.eval(part)`) and coerced with `_as_number(...)` then `int(...)`, so
   `lipid_samples.pct_assay[cidx]` (cidx = 0.0..3.0) and
   `lipid_samples.pct_assay[cidx + 4]` (a `_Binary` node) both work. Out-of-range
   or blank indices return `EMPTY` rather than raising.

3. **No circular dependency.** `referenced_paths` of the chosen expression is
   `{('cidx',), ('lipid_samples','pct_assay')}`. In
   `evaluator._evaluation_order`, `pct_mean_compound` therefore depends only on
   `(lipid_samples, cidx)` and `(lipid_samples, pct_assay)`; `pct_assay` depends
   on `cidx`/`area`/`stats.*` and NOT on any mean field. The toposort resolves
   deterministically with no cycle. (`mean([...])` is blank-skipping via
   `expression._numeric`, so a blank Set-2 `pct_assay` is simply dropped.)

### Final chosen expression (proven)

```
mean([ lipid_samples.pct_assay[cidx], lipid_samples.pct_assay[cidx + 4] ])
```

The task's preferred `cidx`-as-index form works as-is; the inlined
`(rowno-1)-trunc((rowno-1)/4,0)*4` fallback is **NOT needed**.

### Oracle values captured from the real engine

Rows 0..7 = Set1(tri,dppg,chol,depc), Set2(tri,dppg,chol,depc). Prep per row:
`avg_weight=1.005, sample_weight=1.5008, vol_j=25, pip_k=1, vol_l=1`,
context `lc_tri=2, lc_dppg=0.9, lc_chol=4.7, lc_depc=8.2, lc_bupi=13.3`,
standard/std_areas/bkt_areas exactly as in the current parity test.

**Set-1-only fixture** (Set1 areas `[8729574, 3826195, 32474189, 44235393]`,
Set 2 rows blank area):
- `pct_assay` Set1 rows = `99.979001, 86.200388, 101.772429, 100.389722`
  (2-dp gold `99.98 / 86.20 / 101.77 / 100.39`).
- `pct_mean` (per-set) Set1 rows = each row's own `pct_assay` (identical to
  above); Set2 rows = `EMPTY`.
- `pct_mean_compound` on BOTH the Set1 row and the Set2 row of each compound =
  the Set1 `pct_assay` (blank Set2 skipped): `99.979001, 86.200388, 101.772429,
  100.389722`. So `pct_mean` and `pct_mean_compound` read EQUAL on the filled
  Set1 rows; on the blank Set2 rows `pct_mean` is EMPTY while
  `pct_mean_compound` repeats the compound's Set1 value.
- `drug_lipid` row 0: `tri_mgml≈1.99958`, `sum_lipid≈15.790645`,
  `mgml_bupi≈13.2867`, `ratio≈0.841429`; `reportable_result≈0.841429`.

**Both-sets oracle** (Set 2 area = `int(Set1_area * 1.02)`, i.e.
`[8904165, 3902718, 33123672, 45120100]`):
- Set1 `pct_assay` = `99.979001, 86.200388, 101.772429, 100.389722`.
- Set2 `pct_assay` = `101.978584, 87.924383, 103.807870, 102.397513`.
- `pct_mean` (per-set) = each row's own `pct_assay` (Set1 row ≠ Set2 row).
- `pct_mean_compound` on BOTH rows of a compound = cross-set mean:
  `100.978792, 87.062385, 102.790150, 101.393617`.
  (Note: the test should derive these in-line as `(set1+set2)/2` from the two
  `pct_assay` values the engine returns, not hard-code them, so the oracle can't
  silently pin a bug — mirror the existing test's hand-derivation style.)

---

## Scope (touch ONLY these)

- `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py` — the `pct_mean`
  relabel + new `pct_mean_compound` field (and the `_lipid_sample_fields`
  docstring).
- `lims.db` DB row id 35 (`test_templates`, TPL-A2-0004 v1 Active) via the
  existing sync script.
- `tests/calculation/test_a2_0004_tabular_parity.py` — assert both columns under
  both fixtures + a DB byte-equality assertion.

Do **NOT** touch `pct_assay`, `cidx`, `compound_name`, `lc`, prep inputs, `area`,
the `standard`/`std_areas`/`bkt_areas`/`stats` groups, context, the 8 SST
criteria, or `drug_lipid`'s formulas.

---

## Baseline (confirmed this step)

- `tests/calculation/test_a2_0004_tabular_parity.py` → 9 passed (green).
- Full `tests/calculation` → **762 passed, 5 failed**. The 5 failures are
  pre-existing and unrelated to A2-0004:
  `test_seeded_template_parity.py::TestA6BDissolutionWithReplacement` ×3 and
  `test_worksheet_service.py` ×2. The change must keep this at exactly 5 failures
  (no NEW failures) and raise the A2-0004 parity count from 9.
- DB row 35 `definition` JSON currently equals `json.dumps(BUPI_LIPID_RATIO.definition)`
  byte-for-byte (both 14169 chars) — confirming the sync contract.

Run all Python from `backend-v2`.

---

## Steps

- [ ] 1. Relabel the existing per-set `% Mean` field and update its docstring/comment.
      In `_lipid_sample_fields()` change the `pct_mean` field's `"label"` from
      `"% Mean"` to `"% Mean (Set)"`. Keep its `key` (`pct_mean`), `kind`, `unit`
      (`%`), rounding (none) and expression (`mean([pct_assay])`) EXACTLY as they
      are — `drug_lipid` depends on the key and the per-set value. Update the
      field's inline comment / the `_lipid_sample_fields` docstring bullet for
      `pct_mean` to say it is the per-SET mean (= that row's own % Assay, single
      injection) kept so `drug_lipid` stays bound to it.
      Files: `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
      Verify: `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py::TestA2_0004TabularParity::test_drug_lipid_ratio_chain -q`
      still passes (ratio 0.841429 unaffected by a label-only change).

- [ ] 2. Add the new `pct_mean_compound` calculated field immediately AFTER `pct_mean`.
      In `_lipid_sample_fields()`, insert a field dict right after `pct_mean`:
      `{"key": "pct_mean_compound", "kind": "calculated", "label": "% Mean (Compound)",
      "unit": "%", "expression": "mean([ lipid_samples.pct_assay[cidx], lipid_samples.pct_assay[cidx + 4] ])"}`
      with NO rounding. Add a docstring bullet in `_lipid_sample_fields` explaining:
      cross-set mean per compound via the hidden `cidx` and absolute rows
      `cidx`/`cidx+4`; self-group cross-row reference proven against the engine;
      blank-skipping so Set-2-blank yields the Set-1 value; `drug_lipid` does NOT
      read this field (stays on per-set `pct_mean`).
      Files: `scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`
      Verify: `python -c "from scripts.template_definitions.a2_bupivacaine_lipid_ratio import LIPID_RATIO_DEFINITION; from src.domain.services.calculation.template_schema import TemplateDefinition; TemplateDefinition.parse(LIPID_RATIO_DEFINITION); print('parses OK')"`
      prints `parses OK` (no circular-reference / schema error).

- [ ] 3. Extend the parity test: Set-1-only fixture asserts BOTH mean columns.
      In `tests/calculation/test_a2_0004_tabular_parity.py`, rename/extend
      `test_set1_percent_mean_equals_percent_assay` (or add a sibling) so that for
      the existing Set-1-only `LIPID_SAMPLES` fixture it asserts: for rows 0..3,
      `pct_mean` == that row's `pct_assay` AND `pct_mean_compound` == that row's
      `pct_assay` (both equal when only Set 1 is filled), matching
      `99.979/86.200/101.772/100.390` to `abs=1e-2`. Note the fixture is still 4
      rows (Set 2 absent); if `lipid_samples` evaluates with fewer than 8 rows,
      confirm the engine seeds 8 (min==max==8) and the Set-2 rows (4..7) have
      blank `area` — assert `pct_mean` is EMPTY on rows 4..7 while
      `pct_mean_compound` on rows 4..7 repeats the matching compound's Set-1 value.
      Files: `tests/calculation/test_a2_0004_tabular_parity.py`
      Verify: `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q`
      — the new/updated Set-1 assertions pass.

- [ ] 4. Add a both-sets oracle test.
      Add a new test method that evaluates a SECOND `lipid_samples` fixture with 8
      filled rows: Set 1 areas `[8729574, 3826195, 32474189, 44235393]` and Set 2
      areas `[8904165, 3902718, 33123672, 45120100]` (= Set1×1.02, truncated to
      int), all other prep identical, `drug_lipid` with two rows
      (`pct_assay_bupi=99.9`). Assert: (a) per-set `pct_mean[i]` == `pct_assay[i]`
      for all 8 rows and `pct_mean` differs between a compound's Set1 and Set2 rows;
      (b) `pct_mean_compound` on rows `cidx` and `cidx+4` are EQUAL and both equal
      `(pct_assay[cidx] + pct_assay[cidx+4]) / 2` — derive the expected value
      in-line from the two returned `pct_assay` values (do not hard-code), matching
      the engine-captured `100.979/87.062/102.790/101.394` to `abs=1e-3` as a
      cross-check comment.
      Files: `tests/calculation/test_a2_0004_tabular_parity.py`
      Verify: `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q`
      — the both-sets test passes.

- [ ] 5. Sync the DB (direct ORM/SQLite UPDATE of row 35) via the existing script.
      Run the documented sync mechanism so DB row 35's `definition` matches the
      updated module. The script `scripts/update_a2_0004_definition.py` already
      does exactly this (serialises `BUPI_LIPID_RATIO.definition`, UPDATEs
      `test_templates` where code='TPL-A2-0004', asserts exactly one row changed
      and that id/code/archetype/version/status/test_id are unchanged). Make a
      timestamped backup of `lims.db` first (house convention: `lims.db.bak-<ts>`),
      then run the script.
      Files: `lims.db` (row id 35 only). No code change to the script expected; if
      it needs none, this step is purely running it.
      Verify: `python scripts/update_a2_0004_definition.py` prints
      `1 row updated` and `identity preserved: id=35 ... version=1 status=Active ...`.

- [ ] 6. Add a DB byte-equality assertion to the parity test.
      Add a test that opens `lims.db` (sqlite3, read-only is fine), reads
      `definition` for `TPL-A2-0004`, and asserts it is byte-for-byte equal to
      `json.dumps(BUPI_LIPID_RATIO.definition)` (import `BUPI_LIPID_RATIO` from the
      module; use the SAME `json.dumps` default separators the sync script uses so
      the canonical form matches). This locks the stored definition to the source
      module after step 5. Guard with `pytest.mark.skipif(not os.path.exists("lims.db"))`
      only if the suite is expected to run without the DB; otherwise assert directly.
      Files: `tests/calculation/test_a2_0004_tabular_parity.py`
      Verify: `python -m pytest tests/calculation/test_a2_0004_tabular_parity.py -q`
      — the byte-equality test passes (fails before step 5 is run, passes after).

- [ ] 7. Full regression gate.
      Confirm no new failures were introduced.
      Files: none.
      Verify: `python -m pytest tests/calculation -q` → the A2-0004 parity file is
      fully green and the overall suite shows **exactly the same 5 pre-existing
      failures** (A6B dissolution ×3, worksheet_service ×2) and no others; total
      passed count rises by the number of new A2-0004 assertions/tests added.

---

## Notes / assumptions

- Frontend needs no change: it renders calculated columns generically, so the new
  `% Mean (Compound)` column appears automatically between `% Mean (Set)` and the
  Drug-to-Lipid section's consumption of `pct_mean`.
- The `json.dumps` form for the byte-equality test must match the sync script's
  `json.dumps(BUPI_LIPID_RATIO.definition)` (default separators, no `sort_keys`),
  which is already how the DB was written; confirmed equal (14169 chars) before
  any change.
- `pct_mean_compound` deliberately has NO rounding, matching `pct_mean`/`pct_assay`
  (display rounding is the front end's concern); mid-chain rounding would perturb
  the cross-set mean.
- Step ordering: the DB byte-equality test (step 6) only passes AFTER the DB sync
  (step 5), so run them in that order; steps 1–4 are module/test edits that leave
  the suite buildable at each point (the byte-equality test is added last).
