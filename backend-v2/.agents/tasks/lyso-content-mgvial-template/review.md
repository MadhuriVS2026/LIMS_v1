# Content of Lyso PC / Lyso PG (mg/vial) seed template — TPL-A2-0003

Adds TPL-A2-0003, the mg/vial sibling of TPL-A2-0002 (mg/mL), reproducing the Amphotericin B Liposome `Content of Lyso PC PG_mgvial` workbook. The change is a single new module (`a2_lyso_content_mgvial.py`) registered in the seed catalogue, a parity test class, and task evidence. The only behavioral difference from the mg/mL template is a trailing per-vial multiplier (12.5), exposed as an overridable context field `vial_factor` and referenced bare in both content expressions, plus the mg/vial sheet's sample-prep defaults. The existing TST-LYSO Test is reused with no duplicate, and the template seeds Active.

Watch for: nothing blocking. The deliberate structure duplication (rather than a shared builder) is the correct call here — a shared builder would have mutated TPL-A2-0002's stored JSON, which must stay unchanged (confirmed). The template seeds with SST %RSD criteria that legitimately *fail* on the sheet's own example data (2.21/2.32 > NMT 2.0), which is faithful to the source and pinned by a test, not a defect [confirmed].

**Verdict**: APPROVED

## High-level view

The problem — a per-vial variant of an existing per-mL content template — is solved by cloning the mg/mL module's definition and appending one factor. The vial multiplier is modeled as an overridable context field (`vial_factor`, default 12.5) rather than a literal, so overriding it to 1.0 recovers the mg/mL numbers; this mirrors the established `k_value` context-field pattern in `a8_content_uniformity.py`, and the seeded definition carries the field verbatim [confirmed].

The two reportable content expressions transcribe sheet cells C61/D61 term-for-term, including the distinctive PG term ordering, with `* vial_factor` as the trailing factor on both. The mean-std denominators are the six-injection standard means (L34/M34), not the pooled bracketing means — matching the mg/mL sibling and the sheet [confirmed].

Blast radius is contained: exactly one new template row (TPL-A2-0003) with a non-colliding code, bound to the single existing TST-LYSO Test. TPL-A2-0002, TPL-A2-0001, and TST-LYSO are untouched; the sibling source file has zero diff [confirmed]. The author's numeric evidence reproduces every expected sheet value (PC 9.0342 mg/vial, PG 5.5767 mg/vial, assays 903.42 % / 557.67 %, sample sums 3,012,568 / 2,067,344, standard and pooled stats) and all of these match the committed and stored definition [confirmed].

<details>
<summary>Issues (0)</summary>

No blocking or non-blocking action items. All task requirements verified.

</details>

<details>
<summary>Details</summary>

### Vial factor as an overridable context field

The x12.5 aliquot-to-vial multiplier is a context field, not a buried literal:

```json
{"key": "vial_factor", "kind": "context", "label": "Vial Factor", "default": 12.5, "overridable": true}
```

Both content expressions reference it bare as the trailing `* vial_factor`. This resolves inside the `sample_results` table-row scope because the evaluator seeds context fields into every row scope — the same mechanism `a8_content_uniformity.py` relies on for `k_value` inside its acceptance-value expression. The author's evidence exercises the override directly: setting `vial_factor` to 1.0 yields PC 0.722738 / PG 0.446133, exactly the x12.5 results divided by 12.5, which proves the factor is live and not a constant folded into the formula [confirmed, verified against the stored definition dump and the verification evidence].

### Content expressions transcribe C61/D61 exactly

Both reportable expressions in the stored definition match the sheet term-for-term, including the order of multiplicands:

```
pc_mgvial = sum_pc / stats.mean_std_pc
          * standard.pc_weight / standard.pc_vol1
          * standard.pc_pip / standard.pc_vol2
          * standard.pc_mw_base / standard.pc_mw_salt
          * sample_prep.vol / sample_prep.ml
          * sample_prep.vol2 / sample_prep.pip
          * standard.pc_potency / 100
          * vial_factor

pg_mgvial = sum_pg / stats.mean_std_pg
          * standard.pg_weight / standard.pg_vol1
          * standard.pg_pip / standard.pg_vol2
          * sample_prep.vol2 / sample_prep.pip
          * sample_prep.vol / sample_prep.ml
          * standard.pg_mw_base / standard.pg_mw_salt
          * standard.pg_potency / 100
          * vial_factor
```

The PG expression preserves the sheet's distinctive ordering — the `vol2/pip` dilution term comes *before* `vol/ml`, and the MW ratio comes *after* both — which differs from the PC ordering and is faithful to D61. The mean-std denominators are `stats.mean_std_pc` / `stats.mean_std_pg` (the six-injection standard means, sheet L34/M34), not the pooled `mean_pool_*` (L46/M46). The assays are `pc_mgvial * 100 / standard.pc_lc` and `pg_mgvial * 100 / standard.pg_lc` (E61/F61). All four verified against the stored DB definition, which is byte-identical to the committed source [confirmed].

### Numeric parity against the source workbook

The author's `verification.md` and commit message report a full data_only parity read; every number was cross-checked against the committed expressions and the seeded definition:

```
Lyso PC mg/vial (C61) : 9.034220        vs 9.034219643511904   PASS
Lyso PG mg/vial (D61) : 5.576665        vs 5.5766651873236     PASS
Lyso PC Assay % (E61) : 903.422000      vs 903.4219643511904   PASS
Lyso PG Assay % (F61) : 557.666500      vs 557.6665187323599   PASS
sample inj1 PC (L57)  : 3012568         vs 3012568             PASS
sample inj1 PG (M57)  : 2067344         vs 2067344             PASS
PC meanStd (L34)      : 11468461.5      PG meanStd (M34): 6420652.166667   PASS
PC/PG %RSD (L36/M36)  : 2.21 / 2.32     PC/PG pooled %RSD: 2.46 / 1.90     PASS
```

Every value the task flagged (PC 9.0342, PG 5.5767, assays 903.42 % / 557.67 %, sample sums 3,012,568 / 2,067,344, standard and pooled stats) is present and matches. The evidence file is complete, not missing [confirmed].

### Blast radius: exactly one new row, TST-LYSO reused

The seeded catalogue now holds TPL-A2-0001, TPL-A2-0002, and TPL-A2-0003 (A2, mg/vial, Active). A single TST-LYSO Test row exists, bound by both TPL-A2-0002 and TPL-A2-0003 — the seeder reused the existing Test rather than creating a duplicate. The code `TPL-A2-0003` does not collide. The sibling source `a2_lyso_content.py` has an empty diff for this commit, so TPL-A2-0002's stored definition is unchanged; the author chose structural duplication over a shared builder precisely to avoid mutating that stored JSON. The `__init__.py` change is a two-line import-and-splice in archetype order [all confirmed against the DB and git].

### Scope and cleanup

Backend/data only — no frontend files in the diff. The throwaway parity script `_verify_lysovial.py` is deleted (no trace in the tree). Evidence lives in `.agents/tasks/lyso-content-mgvial-template` (plan.md, verification.md). The commit also adds `tests/calculation/test_seeded_template_parity.py::TestA2LysoContentMgVial`, which pins the parity numbers and the legitimate SST failure on the example data [confirmed].

</details>

<details>
<summary>File map</summary>

- `scripts/template_definitions/a2_lyso_content_mgvial.py` — new TPL-A2-0003 module (mg/vial sibling of TPL-A2-0002)
- `scripts/template_definitions/__init__.py` — register the new module in seed order
- `tests/calculation/test_seeded_template_parity.py` — new TestA2LysoContentMgVial parity class
- `.agents/tasks/lyso-content-mgvial-template/plan.md`, `verification.md` — task evidence

Full diff: `git show 39eee50`

</details>
