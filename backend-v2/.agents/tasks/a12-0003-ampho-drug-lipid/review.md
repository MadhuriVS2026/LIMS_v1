# TPL-A12-0003 Amphotericin B — Drug-to-Lipid Ratio template

A new A12 derived roll-up template that carries three lipid component assays and the Amphotericin B microbial assay per batch, computes each content from a reverse-engineered label claim (`Content = Assay% × LC/100`), sums the three lipid contents (drug excluded) into a total lipid content, and reports the drug-to-lipid ratio. It is modelled as one multi-batch table (one row per batch) because the source sheet lists multiple batches, differing in shape from the singleton A12-0002 but sharing its carry-over nature. The four per-component label claims (Chol 52.0 / HSPC 213.0 / DSPG 81.6 / Ampho 50.0 mg/vial) were recovered from the gold data and exposed as overridable context. The build is scoped, committed as HEAD (612ecbb), and reverify of the formula, identity, and DB state all hold.

Watch for: the Amphotericin B content-column figures printed in the task text (55.3200 / 54.3650 / 54.6900) are transcription slips — the specified formula yields 55.30 / 54.35 / 54.70, and only those reproduce the authoritative gold ratios (confirmed). The implementer documented this and asserts the formula-exact values; the system behaviour is unaffected.

**Verdict**: APPROVED

## High-level view

The arithmetic reproduces every gold value exactly. I independently recomputed all three batches from the four LC factors: the twelve component contents, the three lipid totals, and the three ratios (0.1511 / 0.1476 / 0.1500) all match to the sheet's 4 dp. The lipid total correctly excludes the Amphotericin B drug content. The only discrepancy is the ampho content column, where the task's printed figures round to a ratio that does not match the authoritative gold; the formula-derived values do, and that is what is implemented and asserted.

The identity is correct and distinct. TPL-A12-0003 was the next-free A12 code, seeded exactly once as Active with `result_unit` None, bound to a brand-new test TST-ALDR named exactly `Ampho-lipid to drug ratio` (Quantitative). No existing test such as TST-DLR was reused. The stored DB definition is canonical-JSON byte-equal to the module's `SeedTemplate.definition`.

The criteria match the sheet's limit row and the sibling convention. Four blocking assay ranges (Chol 90–120, HSPC 90–120, DSPG 80–120, Ampho 90–120) and one blocking ratio range (0.11–0.17); the content columns are N/A on the sheet and carry no criterion. Each criterion targets `mean(batches.<field>)` because the engine needs a scalar target over a per-row table, mirroring how A12-0001 targets `mean(preps.pct_assay_total)`.

The scope is clean and the backup was taken. The commit touches only the new module, its two-line registration in `__init__.py`, the new parity test, and the task's backup/verification notes. The DB backup matches the source size byte-for-byte. The pre-existing 5 failures (A6B + worksheet_service) are unchanged and the 7 new parity tests pass with no other new failures, per the implementer's note, which I did not re-run.

<details>
<summary>Issues (1)</summary>

1. **Ampho content-column transcription slip (non-blocking, documented)** — the task text's ampho content figures (55.3200 / 54.3650 / 54.6900) disagree with the specified formula (55.30 / 54.35 / 54.70) and only the formula values reproduce the gold ratios. Already documented in the verification note and the test file, and the formula-exact values are asserted. No action required; noted so a future reviewer does not "fix" the test toward the slipped figures.

</details>

<details>
<summary>Details</summary>

### Formula and LC factors reproduce every gold value

I recomputed all three batches independently from the four label claims rather than trusting the note. With Chol 52.0, HSPC 213.0, DSPG 81.6, Ampho 50.0:

```
batch 10009697  chol 54.7560  hspc 228.9750  dspg 82.2528  lipid 365.9838  ratio 0.1511  ✓
batch 10010727  chol 54.9120  hspc 228.1230  dspg 85.1088  lipid 368.1438  ratio 0.1476  ✓
batch 040598M   chol 55.1720  hspc 226.4190  dspg 82.9872  lipid 364.5782  ratio 0.1500  ✓
```

Every lipid content and every ratio matches the gold to 4 dp (confirmed). The lipid total is `chol_content + hspc_content + dspg_content` with the Amphotericin B content explicitly excluded (confirmed by reading the expression). No mid-chain rounding appears in any stored expression, so the unrounded ratio carries full precision into the reportable.

On the ampho content column: the formula `110.6 × 50/100 = 55.30` gives ratio `55.30/365.9838 = 0.1511` (the gold), whereas the task-printed 55.32 gives 0.1512 (confirmed). The content column figures are transcription slips; the formula plus the authoritative ratios are self-consistent, and the parity test asserts the formula-exact ampho contents (55.30 / 54.35 / 54.70), with the slip documented in both the module and the test.

The parity test `test_a12_0003_ampho_parity.py` asserts the four contents per batch, the three lipid totals (drug-excluded), the three ratios, the reportable equal to the first batch ratio, the presence and limits of all five criteria, and a failing path where an out-of-range ratio raises a blocking failure. The expected values are the task oracle, not copied from a run.

### Identity and DB state

Direct query of `lims.db` (confirmed): TPL-A12-0003 is present as exactly one row, Active, `result_unit` None, archetype A12. The A12 code set is exactly 0001/0002/0003, so 0003 was the genuine next-free code. The bound test is TST-ALDR / `Ampho-lipid to drug ratio` / Quantitative, with an exact name match and a TST-ALDR count of 1 — a new test, not a reuse of TST-DLR (which belongs to the separate TPL-A12-0002). The stored definition is canonical-JSON byte-equal to the module's `A12_AMPHO_RATIO.definition` (confirmed by `json.dumps(..., sort_keys=True, separators=(',',':'))` on both).

### Criteria shape and targeting

```
chol_assay_range       mean(batches.chol_assay)        between 90.0  120.0  blocking
hspc_assay_range       mean(batches.hspc_assay)        between 90.0  120.0  blocking
dspg_assay_range       mean(batches.dspg_assay)        between 80.0  120.0  blocking
ampho_assay_range      mean(batches.ampho_assay)       between 90.0  120.0  blocking
drug_lipid_ratio_range mean(batches.drug_lipid_ratio)  between 0.11  0.17   blocking
```

Limits match the sheet's limit row exactly, including the DSPG lower bound of 80.0 (distinct from the 90.0 of the other three). All five are blocking. The content columns are N/A on the sheet and carry no criterion (confirmed — only five criteria exist). The `mean(batches.<field>)` targeting is a deliberate choice: the engine needs a scalar target for a per-row table, and this matches A12-0001's `mean(preps.pct_assay_total)`. The choice is documented in the module docstring and the verification note.

One minor, non-blocking divergence from the sibling: A12-0002's reportable `drug_to_lipid` carries explicit `rounding: round 4dp`, while this template's `drug_lipid_ratio` carries none. The implementer chose no mid-chain rounding deliberately, and the unrounded value already reproduces gold to 4 dp, so the reportable is correct either way; display rounding happens downstream. Worth a glance if a future change expects an explicitly-rounded stored ratio, but it changes nothing here.

### Scope and safety

The commit (612ecbb) adds exactly: the new module `a12_ampho_drug_lipid.py`, a two-line registration in `__init__.py` (import `_A12_AMPHO`, appended after `*_A12` in archetype order), the parity test, and the task's `backup.txt` / `verification.md`. No other template module or test row is touched (confirmed by `git show --stat`). The DB backup `lims.db.bak-ampho-20261023-234640` exists and matches the source size (1331200 bytes, confirmed). Throwaway helper scripts were deleted by the implementer; I removed my own temp verification script as well.

### Test suite status

Per the verification note, `pytest tests/calculation` reports 5 failed / 778 passed, the 5 being the known pre-existing A6B (3) and worksheet_service (2) failures, with the 7 new parity tests passing and no other new failures. I did not re-run the full suite (re-running what the implementer already ran yields no new information); my narrow spot-checks were the independent formula recomputation, the validate-only seed (`ok TPL-A12-0003 ... 6 inputs, 6 calculated, 5 criteria`, exit 0), and the direct DB queries above.

</details>

<details>
<summary>File map</summary>

- `scripts/template_definitions/a12_ampho_drug_lipid.py` — new A12 module: batch table, four LC context factors, content/lipid/ratio formulas, five criteria.
- `scripts/template_definitions/__init__.py` — registers `_A12_AMPHO` in archetype order.
- `tests/calculation/test_a12_0003_ampho_parity.py` — parity test (7 cases) against the task gold.
- `.agents/tasks/a12-0003-ampho-drug-lipid/backup.txt` — DB backup record.
- `.agents/tasks/a12-0003-ampho-drug-lipid/verification.md` — implementer verification note.

Full diff: `git show 612ecbb`.

</details>
