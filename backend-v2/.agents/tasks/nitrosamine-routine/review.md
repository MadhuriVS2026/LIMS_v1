# Review — Nitrosamine Routine analysis sheet (TPL-NITRO-0001)

Scope: new seed module `scripts/template_definitions/nitrosamine_routine.py`, the
registry edit in `scripts/template_definitions/__init__.py`, and the parity test
`tests/calculation/test_nitrosamine_routine_parity.py`.

## Verdict: APPROVED

This is a later review pass. The prior pass raised exactly one blocking finding
(B1 — required verification evidence was missing); all formula/gold-value
correctness checks already passed. The coder has now supplied
`verification.md` with the three required command runs and their results, and
proved the broader-suite failures are pre-existing and independent of the
registry edit. B1 is resolved and no new blockers were found.

## Resolution of prior finding B1 (verification evidence)

`verification.md` records the three required commands:

1. Parity test — `pytest tests/calculation/test_nitrosamine_routine_parity.py`
   → 7 passed. **Independently re-run on this pass: 7 passed (exit 0).**
2. Broader suites — `pytest test_seeded_template_parity.py test_workbook_parity.py`
   → 338 passed, 3 failed. The 3 failures are all in
   `TestA6BDissolutionWithReplacement` (`test_unit1_release_carryover`,
   `test_per_timepoint_summary`, `test_amount_remaining`), an unrelated A6B
   template whose `release`/`amount` groups return EMPTY. The coder proved these
   are pre-existing by showing the same three fail identically with `_NITRO`
   removed from the registry.
3. Registry import smoke — `from scripts.template_definitions import SEED_TEMPLATES`
   → 34 templates, `TPL-NITRO-0001` present.

Spot-check on this pass (justified by the doubt that the "no perturbation"
conclusion rests on): ran
`test_seeded_template_parity.py::TestA6BDissolutionWithReplacement` with `_NITRO`
registered → the same 3 tests fail (EMPTY vs expected) in that unrelated A6B
class, 1 passes. This matches the coder's evidence: the failures live entirely in
a different template with no `amount`/`release` groups, and the nitrosamine
template plays no part in them. Registering `TPL-NITRO-0001` did not perturb any
cross-template suite.

## Correctness findings (all PASS — re-confirmed)

### Standard conc O11 — term order and gold
Module `std_conc_ppb` =
`weight_mg/stock_i*ml_stock_i/stock_ii*ml_stock_ii/stock_iii*purity/100*1000*ml_stock_iii/stock_iv*ml_stock_iv/standard_solution*1000`.
With the cell→key mapping (E=weight_mg, F=stock_i, G=ml_stock_i, H=stock_ii,
I=ml_stock_ii, J=stock_iii, D=purity, K=ml_stock_iii, L=stock_iv, M=ml_stock_iv,
N=standard_solution) this reproduces the sheet order
`E11/F11*G11/H11*I11/J11*D11/100*1000*K11/L11*M11/N11*1000` exactly, including
`D11/100*1000` sitting mid-expression. Independently computed = 1.0416537600000002,
matching the asserted gold.

### Per-sample PPM — term order, per-row columns, TRUNC
`_ppm_expression()` reproduces `N/$D$23 * $E$11/$F$11 * $G$11/$H$11 * $I$11/$J$11
* $K$11/$L$11 * $M$11/$N$11 * $D$11/100 * J/I * L/K * E/F * H/G * 1000000` in
order: `corrected/std_stats.avg_area` · the `$`-anchored standard-prep constants ·
per-row un-anchored `dilution_2/ml_1` (J/I), `dilution_3/ml_2` (L/K),
`avg_weight/label_claim` (E/F), `dilution_1/sample_weight` (H/G) · `1000000`, with
`rounding: {mode: trunc, digits: 4}`. Per-row columns resolve to this row's own
values. Independently reproduced S1=0.0611, S2=0.0649, S3=1.8211, S4=1.6230,
S5=1.1254, S16=1.8798 — all match.

### Left-block standard stats
`mean/sd` over `std_areas.corrected` (blank-tolerant, matching AVERAGEIF(<>0) /
STDEV-IF). Computed D23=76406, D24=479.69365224067747, D25=0.6278219671762394 —
match the asserted golds.

### Right-block BKT stats — pooled blank-chromatogram cell
`pool([std_stats.avg_area], bkt.corrected)` pools the left-block standard average
(76406) with the three filled BKT corrected areas. Computed G23=81345.75,
G24=4455.392341496613, G25=5.477105247043163 (last-digit float variance within
pytest.approx). Unused BKT rows are modeled BLANK (`rows.min: 0`, only 3
provided); `_f_mean`/`_f_sd` use `_numeric`, which drops EMPTY, so blanks are
excluded (not 0). Confirmed.

### SST criterion — blocking on standard %RSD only
`criteria=[sst_rsd_criterion(target="std_stats.rsd_area", limit=2.0)]` — a single
blocking `lte 2.0` on D25. BKT %RSD (G25) is shown via the footer ref but carries
no criterion. The decision is documented in the module docstring (ACCEPTANCE
CRITERIA paragraph: BKT %RSD "DISPLAYED but NOT blocking"). The explicit `target=`
is required because the stats group is renamed `std_stats`. Tests
`test_sst_rsd_criterion_present_and_blocking` and `test_bkt_rsd_not_a_criterion`
guard both halves.

### resultRef and metadata
`resultRef="samples.ppm"` points at the sample table's PPM field. `code`
`TPL-NITRO-0001` and `test_code` `TST-NITRO-ARGA` are unique in the registry.
`result_unit="ppm"`, `test_type="Quantitative"`, `test_name` present; archetype
`A2` choice is documented in the docstring.

### Archetype structure / helper reuse
Follows the `a6a_leuprolide_microsphere.py` archetype: per-section builder
functions, `SeedTemplate` wrapper, `TEMPLATES` list, docstring-documented quirks,
reuse of `_common.sst_rsd_criterion` and `SeedTemplate`. Registered in
`__init__.py` as `_NITRO` and appended to `SEED_TEMPLATES`.

### Parity test integrity
Asserts O11, D23/D24/D25, G23/G24/G25, all 16 sample PPMs, reportable result, SST
presence/blocking, and BKT-not-a-criterion — all to full precision via
`pytest.approx`. Not loosened; it pins the stored formulas by importing the
definition directly.

## Conclusion
All correctness requirements hold and the previously-missing verification
evidence is now recorded and independently corroborated. No blocking findings
remain.
