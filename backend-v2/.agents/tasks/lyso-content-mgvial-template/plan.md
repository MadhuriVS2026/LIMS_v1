# Implementation Plan — Content of Lyso PC / Lyso PG (mg/vial), TPL-A2-0003

## Goal

Add ONE new seed template, `TPL-A2-0003` "Content of Lyso PC / Lyso PG (mg/vial)",
the mg/vial sibling of `TPL-A2-0002` (mg/mL). Reproduce the source workbook
`d:\RD-instance\GIT\Test types\Content of Lyso PC PG_ mgvial_Ampho.xlsx` exactly,
including an extra x12.5 vial factor on the two content formulas, and verify the
computed results match the sheet's stored values.

Backend only — do NOT touch the frontend.

## Design decisions (made during exploration, grounded in the repo)

1. **Duplicate the module structure; do NOT factor a shared builder between the
   two Lyso modules.** `a2_lyso_content.py` (TPL-A2-0002) today has NO `vial_factor`
   context field and NO `* vial_factor` in its content expressions. Any shared
   builder that injected the overridable `vial_factor` would change TPL-A2-0002's
   stored `definition` JSON (an extra context field changes the byte output even at
   default 12.5, because mg/mL multiplies by 1.0 — but there is no `vial_factor`
   field there at all today). The task forbids changing TPL-A2-0002 byte-for-byte,
   so the mg/vial template lives in its own new module that mirrors the mg/mL
   structure verbatim. Only `_common.context_header` is reused, exactly as the
   mg/mL module reuses it.

2. **Expose x12.5 as an overridable context field `vial_factor`, default 12.5**,
   referenced bare in both content expressions as `* vial_factor` (never a buried
   literal). This mirrors how `a8_content_uniformity.py` exposes `k_value`
   (`default: 2.4`, `overridable: True`) and references it bare inside a
   group-field expression. Confirmed safe in `evaluator.py`: context fields are
   seeded into `result.values` and `_build_scope` starts every row scope with
   `dict(result.values)`, so a bare `vial_factor` inside a `sample_results` row
   expression resolves. Default 12.5 reproduces the sheet out of the box.

3. **mean-std denominators are the STANDARD 6-injection means (`stats.mean_std_pc`
   / `stats.mean_std_pg`), NOT the pooled BKT means** — identical to the mg/mL
   module. Verified against the sheet: C61 divides L57 by L34 (the row-34 standard
   mean), not L46 (the pooled mean).

4. **Parity test must NOT assert SST passes on the example data.** The source
   sheet's own standard %RSD values are L36=2.211 % (PC) and M36=2.323 % (PG), both
   above the NMT 2.0 % limit, so the four %RSD criteria legitimately FAIL on the
   example inputs. The parity test pins the four reportable values and the
   statistics, and asserts the criteria are *present and failing* on this data (it
   does not claim a clean pass).

## Verified facts (from exploration — do not re-derive)

- `TPL-A2-0003` is free (DB has only `TPL-A2-0001`, `TPL-A2-0002`).
- Test Master `TST-LYSO` (id 24, "Content of Lyso PC & Lyso PG by HPLC") already
  exists; `ensure_test` reuses it — do NOT create a duplicate Test.
- Source sheet stored values (gold data, data_only read of the xlsx):
  - Standard means: `L34 = 11468461.5`, `M34 = 6420652.166666667`
  - Sample injection-1 sums: `L57 = 3012568`, `M57 = 2067344`
  - C61 Lyso PC mg/vial  = `9.034219643511904`
  - D61 Lyso PG mg/vial  = `5.5766651873235995`
  - E61 Lyso PC Assay    = `903.4219643511904`
  - F61 Lyso PG Assay    = `557.6665187323599`
  - Standard %RSD: `L36 = 2.211413...` (PC), `M36 = 2.322626...` (PG)  → both > 2.0
- The six content/assay formulas were transcribed from the task and re-derived from
  the sheet inputs; a standalone Python check reproduced all four stored values to
  full float precision. The expressions below are confirmed correct.

## Example inputs (mg/vial sheet) — differences from mg/mL defaults

Standard block: PC weight 17.547 / vol1 50 / pip 4 / vol2 20 / mw_base 1 / mw_salt 1
/ potency 98 / lc 1 — identical defaults to the mg/mL module. PG weight 18.411 /
vol1 100 / pip 4 / vol2 20 / mw_base 511.61 / mw_salt 534.6 / potency 98.3 / lc 1 —
identical to the mg/mL module. Only the **sample prep** defaults differ:

- `ml` (G53) default `10`
- `vol` (H53) default `200`   (mg/mL uses 20)
- `pip` (I53) default `10`    (mg/mL uses 1)
- `vol2` (J53) default `20`   (mg/mL uses 1)

---

## Steps

- [ ] 1. Create the new definition module `a2_lyso_content_mgvial.py` mirroring
      `a2_lyso_content.py` structurally, with the four mg/vial differences baked in.
      Copy the whole structure of `scripts/template_definitions/a2_lyso_content.py`
      (sub-peak helpers `_PC_KEYS`/`_PG_KEYS`/`_subpeak_fields`, the four
      `_rsd_criterion` entries, the standard/std_injections/bkt_injections/stats/
      sample_prep/sample_results groups, the context header via
      `_common.context_header`). Apply ONLY these changes:
        - Add an overridable `vial_factor` context field in the `extra=[...]` list
          passed to `context_header` (place it first in `extra`, before
          `product_name`): `{"key": "vial_factor", "kind": "context", "label":
          "Vial Factor", "default": 12.5, "overridable": True}`.
        - `sample_prep` field defaults: `ml`=10, `vol`=200, `pip`=10, `vol2`=20.
        - Rename the two result fields and labels to mg/vial and set `unit` to
          `"mg/vial"`: keys `pc_mgvial` / `pg_mgvial`, labels "Lyso PC mg/vial" /
          "Lyso PG mg/vial"; the two avg fields become `avg_pc_mgvial` /
          `avg_pg_mgvial` with labels "Avg Lyso PC mg/vial" / "Avg Lyso PG mg/vial".
        - Append `* vial_factor` to BOTH content expressions (keep the existing
          term order; add the factor at the end):
          - `pc_mgvial` expression (sheet C61):
            `sum_pc / stats.mean_std_pc * standard.pc_weight / standard.pc_vol1`
            `* standard.pc_pip / standard.pc_vol2 * standard.pc_mw_base / standard.pc_mw_salt`
            `* sample_prep.vol / sample_prep.ml * sample_prep.vol2 / sample_prep.pip`
            `* standard.pc_potency / 100 * vial_factor`
          - `pg_mgvial` expression (sheet D61):
            `sum_pg / stats.mean_std_pg * standard.pg_weight / standard.pg_vol1`
            `* standard.pg_pip / standard.pg_vol2 * sample_prep.vol2 / sample_prep.pip`
            `* sample_prep.vol / sample_prep.ml * standard.pg_mw_base / standard.pg_mw_salt`
            `* standard.pg_potency / 100 * vial_factor`
        - Assay expressions reference the renamed fields:
          `pc_assay` = `pc_mgvial * 100 / standard.pc_lc`;
          `pg_assay` = `pg_mgvial * 100 / standard.pg_lc`.
        - Avg expressions: `mean(sample_results.pc_mgvial)` and
          `mean(sample_results.pg_mgvial)`.
        - `resultRef` = `"sample_results.pc_mgvial"`.
        - Keep the same `rounding` on each field as the mg/mL module (mg fields
          round 6 digits, assay fields round 4 digits).
        - Build the `SeedTemplate` as: `code="TPL-A2-0003"`, `name="Content of Lyso
          PC / Lyso PG (mg/vial)"`, `archetype="A2"`, `result_unit="mg/vial"`,
          `test_code="TST-LYSO"`, `test_name="Content of Lyso PC & Lyso PG by HPLC"`,
          `test_type="Quantitative"`, `definition=<the dict above>`. Expose it as a
          module-level `TEMPLATES = [LYSO_MGVIAL]`.
        - Update the module docstring to describe the mg/vial variant and the
          vial_factor decision (one short paragraph; do not copy the mg/mL
          docstring verbatim where it is now inaccurate).
      Files: `backend-v2/scripts/template_definitions/a2_lyso_content_mgvial.py` (new)
      Verify: `python -m scripts.seed_test_templates --validate-only` from
      `backend-v2` — the run prints `ok TPL-A2-0003 [A2] ...` and ends "All
      definitions valid." (After step 2 registers it; before step 2 this template
      is not yet in `SEED_TEMPLATES`, so run this verify after step 2.)

- [ ] 2. Register the new module in the aggregator so it is seeded.
      Add `from scripts.template_definitions.a2_lyso_content_mgvial import TEMPLATES
      as _A2_LYSO_MGVIAL` next to the existing `_A2_LYSO` import, and splice
      `*_A2_LYSO_MGVIAL` into `SEED_TEMPLATES` immediately after `*_A2_LYSO`
      (keeps the archetype-ordered log).
      Files: `backend-v2/scripts/template_definitions/__init__.py`
      Verify: `python -m scripts.seed_test_templates --validate-only` from
      `backend-v2` prints `ok TPL-A2-0003 [A2] ...` among the validated templates
      and exits 0 with "All definitions valid."

- [ ] 3. Add a hand-derived parity test class for TPL-A2-0003 in the existing
      parity test file, modelled on the other `TestA*` classes. Feed the sheet's
      example inputs (context `{"vial_factor": 12.5}` plus the standard block, the
      six standard injections, the sample injection-1 sub-peaks, and the mg/vial
      sample_prep values) and assert the four reportable values match the gold data
      to within `abs=1e-6` for mg/vial (`9.034219643511904`, `5.5766651873235995`)
      and `abs=1e-4` for assay (`903.4219643511904`, `557.6665187323599`). Also
      assert `stats.mean_std_pc` ≈ `11468461.5`, `stats.mean_std_pg` ≈
      `6420652.1667`, and that with these inputs the standard %RSD criteria fail
      (`result.has_blocking_failure is True`, because sheet %RSD 2.21/2.32 > 2.0) —
      do NOT assert a clean SST pass on the example data. Add a second small
      assertion that overriding `vial_factor` to 1.0 divides both mg/vial results
      by 12.5 (confirms the factor is live and overridable). Use the exact sub-peak
      areas from the sheet for injection sums:
        - std injections PC sub-peaks per row sum to L28..L33 (11627818, 11766470,
          11359907, 11205243, 11178008, 11673323) and PG to M28..M33 (6413351,
          6624511, 6243373, 6564217, 6385523, 6292938); you may seed the summed
          `pc_1..pc_5` / `pg_1..pg_2` columns directly from the sheet rows
          (C/D/E/F/G and H/I of rows 28-33), or seed the single non-zero slot that
          produces the correct sum — prefer transcribing the real sub-peak areas.
        - sample injection 1 sub-peaks sum to L57=3012568 (PC) and M57=2067344 (PG).
      Files: `backend-v2/tests/calculation/test_seeded_template_parity.py`
      Verify: `python -m pytest tests/calculation/test_seeded_template_parity.py -q`
      from `backend-v2` — all tests pass, including the new TPL-A2-0003 class and
      the catalogue-wide invariants (`test_template_codes_are_unique`,
      `test_every_template_parses_and_runs_empty`,
      `test_every_template_has_a_resolvable_reportable_result`,
      `test_no_context_field_is_unfillable`,
      `test_area_fields_are_discoverable_for_the_waters_import`). Note:
      `test_every_archetype_in_scope_is_seeded` is unaffected because A2 is already
      in the asserted set.

- [ ] 4. Run the full calculation test suite to confirm no regression anywhere
      (the new context field and module must not perturb other templates).
      Files: none (verification only)
      Verify: `python -m pytest tests/calculation -q` from `backend-v2` — green.

- [ ] 5. Seed the new template as Active into the live DB so it appears in the UI.
      Run the idempotent seeder (it skips the two existing A2 codes and inserts only
      TPL-A2-0003; `ensure_test` reuses TST-LYSO).
      Files: none (writes a row to `backend-v2/lims.db`)
      Verify: `python -m scripts.seed_test_templates` from `backend-v2` prints
      `add  TPL-A2-0003 [A2] Content of Lyso PC / Lyso PG (mg/vial) -> TST-LYSO`
      and does NOT print a line creating a new TST-LYSO Test. Then confirm the row:
      `python -c "import sqlite3;d=sqlite3.connect(r'lims.db');print(list(d.execute(\"select code,name,archetype,result_unit,status,approved_by from test_templates where code='TPL-A2-0003'\")))"`
      shows one row `('TPL-A2-0003','Content of Lyso PC / Lyso PG (mg/vial)','A2','mg/vial','Active','seed')`.

## Notes / assumptions

- The parity test re-pins against the sheet's gold values (hand-copied from the
  xlsx `data_only` read), consistent with the file's rule that expected values are
  derived from the sheet/formula, not from a prior code run.
- No new dependency is introduced. `openpyxl` was used only during exploration to
  read the gold values and is not needed by the template or tests.
- Seeding (step 5) writes to the live `lims.db`; it is additive and idempotent, so
  it is safe to re-run.
