# Independent Review — "% Mean each compound" additive block on TPL-A2-0004

Reviewed commit `90bcaf2` on branch `MadhuriWorktree` (local, not pushed). Method:
read the full diff of both tracked files, the surrounding module structure, the
expression engine (`mean`, string-literal, `referenced_paths`), the full parity
test, and the coder's recorded evidence in
`.agents/tasks/a2-0004-mean-each-compound`. One independent arithmetic
recomputation of the cross-set oracle was performed. The seed-validate,
evaluator, DB-equality, and `pytest tests/calculation` suites were NOT re-run per
the review mandate — the recorded evidence was read and cross-checked instead.

**Verdict: APPROVED** — every one of the 7 required points holds with no blocking
concern.

## Point 1 — Additive-only, correct placement

The module diff (`a2_bupivacaine_lipid_ratio.py`, +82/-0) adds exactly two
things: a new builder `_mean_each_compound_fields()` (returning the 3 columns +
docstring) and one new group dict `mean_each_compound`. The group entry sits in
the `groups` list **immediately after** `lipid_samples` and **before**
`drug_lipid` (confirmed by reading lines ~674–710 of the module). The 8 SST
`criteria` are untouched (the diff makes no edit in the `criteria` block, and the
8 `_rsd_criterion` lines are intact). `lipid_samples` fields, `pct_mean`,
`pct_assay`, `cidx`, `standard`, `std_areas`, `bkt_areas`, `stats`, context
fields, and `drug_lipid` show zero diff lines. The new field feeds no downstream
formula (`drug_lipid` still reads `lipid_samples.pct_mean` directly), so nothing
is perturbed. **confirmed.**

## Point 2 — Cross-set mean correct under both fixtures

The `pct_mean` expression is
`mean([ lipid_samples.pct_assay[(rowno - 1)], lipid_samples.pct_assay[(rowno - 1) + 4] ])`.
With `lipid_samples` pinned to 8 rows (Set 1 = rows 0–3, Set 2 = rows 4–7), idx
and idx+4 correctly pair each compound's Set-1 and Set-2 % Assay.

Set-2-blank fixture: `mean` = sum(non-blank)/count(non-blank) (verified in
`expression.py` `_f_mean`), and `_is_blank` skips None/EMPTY/whitespace, so
`mean([set1, blank]) = set1`. Evidence table shows 99.98 / 86.20 / 101.77 /
100.39 — matching each compound's Set-1 % Assay. **confirmed.**

Both-sets fixture: I independently recomputed the oracle from the two stated
per-set % Assay vectors (Set 1 `[99.979001, 86.200388, 101.772429, 100.389722]`,
Set 2 `[99.067648, 87.863142, 100.286346, 100.990233]`):

| compound | (Set1+Set2)/2 computed by me | evaluator (evidence) |
|----------|------------------------------|----------------------|
| Tricaprylin | 99.5233245 | 99.52332444 |
| DPPG Na | 87.031765 | 87.03176476 |
| Cholesterol | 101.0293875 | 101.02938757 |
| DEPC | 100.6899775 | 100.68997727 |

The oracle is a genuine hand-derived arithmetic mean (I reproduced it from the
input % Assays, not from engine output), and it matches the evaluator to display
precision. The trailing-digit differences are the full-precision pct_assay vs the
6-dp values tabulated — consistent, not a discrepancy. **confirmed.**

## Point 3 — No circular dependency; parses/evaluates; seed validate exit 0

`referenced_paths` truncates a reference at its first non-name part (verified in
`expression.py`), so the `pct_mean` expression resolves to
`{('rowno',), ('lipid_samples','pct_assay')}` — a dependency on a DIFFERENT group
only, with no self/back reference. This is the same cross-group absolute-index
pattern `drug_lipid` already uses, so the topological sort has no cycle. The
`compound_name` expression `standard.name[(rowno-1)]` and the string-literal
`set_source` likewise introduce no cycle. Evidence records `seed --validate-only`
exit 0 with TPL-A2-0004 now reporting 7 groups / 40 calculated (was 6 / 37: +1
group, +3 calculated). **confirmed.**

## Point 4 — Existing gold preserved exactly

The existing `TestA2_0004TabularParity` class assertions are unmodified by the
diff and still assert: std conc 118.92/54.03/285.1/489.25, std means
8691453.5/4461370.5/32403414.83/44013385.5, pooled Tri mean 8699733.9 / %RSD
0.2383, per-compound % Assay 99.98/86.20/101.77/100.39, per-set `pct_mean` ==
`pct_assay`, drug/lipid ratio and reportable 0.841429. The new block feeds nothing
downstream, and the engine proof plus the passing gold assertions confirm it does
not perturb these. **confirmed.**

## Point 5 — DB row 35 byte-equal, identity unchanged

`db_equality.txt` records, after syncing via the (pre-existing, tracked)
`update_a2_0004_definition.py`: identity `(35, TPL-A2-0004, v1, Active, test_id
32)` unchanged (asserted before==after inside the sync script), `exact_equal
True` (DB JSON byte-for-byte == `json.dumps(module)`), and `normalized_equal True`
(`json.loads(DB) == module dict`). A mandatory pre-change backup
(`lims.db.bak-a2meanblock-20261023-230342`, 1331200 == 1331200 bytes) was taken.
**confirmed.**

## Point 6 — Parity test extended; same 5 known failures

The test diff (+112/-1) adds: 4 blank Set-2 rows to `LIPID_SAMPLES` and a second
`DRUG_LIPID` entry (fixture now matches the 8-row / 2-row pinned groups — a
fixture shape alignment, not a gold change, since blank areas skip), a new
`LIPID_SAMPLES_BOTH_SETS` fixture, one new method
`test_mean_each_compound_block_set1_only` on the existing class, and a new class
`TestA2_0004MeanEachCompoundBothSets` with four methods covering the cross-set
mean (oracle + absolute values), compound name + static label, and an explicit
`test_existing_gold_unchanged_by_new_block` re-asserting ratio 0.841429 and
per-set pct_mean. `pytest.txt`: the parity file reports 14 passed; full
`tests/calculation` reports 5 failed / 767 passed — the SAME 5 pre-existing
unrelated failures (3 A6B dissolution + 2 worksheet_service), no new ones.
**confirmed** (from recorded evidence; not re-run per mandate).

## Point 7 — Scope respected

`git show --stat` confirms exactly 2 tracked files changed (the module and the
parity test). Both are clean/committed (no working-tree drift). DB row 35 updated
out-of-band (lims.db is not git-tracked). Branch is `MadhuriWorktree` with a
single checkout at `D:/RD-instance/GIT` — `git worktree list` shows no separate
worktree. Commit is local, ahead of origin by 10, not pushed. The
`update_a2_0004_definition.py` present on disk is a tracked file from the prior
commit `9b92897`, not a throwaway from this task, so it is out of scope.
**confirmed.**

## Observations (non-blocking)

- The test-fixture row-count change (4→8 `lipid_samples` rows, 1→2 `drug_lipid`)
  is a fixture-shape alignment to the module's pinned row counts; it alters no
  computed gold, as the still-passing existing assertions prove. Worth noting only
  so a future reader does not mistake it for a data change.
