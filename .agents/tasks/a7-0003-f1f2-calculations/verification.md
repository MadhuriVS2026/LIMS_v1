# Verification — TPL-A7-0003 "Dissolution F1-F2-calculations"

Finalization run for the f1/f2-calculations template feature. Worktree:
`d:\RD-instance\GIT\.worktrees\f1f2-calculations`. User checkout root:
`d:\RD-instance\GIT` (branch `MadhuriWorktree`).

## Outcome summary

- Step A (pre-rebase verification): **all blocking checks PASSED.**
- Step B (rebase + fast-forward): **BLOCKED** by a pre-existing base defect
  unrelated to this feature (a dangling import in the base's `__init__.py`).
  Rebase itself succeeded; the ff-only merge was **NOT performed** — stopped to
  surface a product decision. See "Blocker" below.
- Step C (this report): written.
- Runtime browser layout check: **NOT performed** (no browser drivable in this
  environment). Reviewer instructions below.

---

## Step A — final verification (run BEFORE the rebase, on commit `e0ff3ef`)

### A1. Seed definition validation — PASS
Command (cwd `backend-v2`):
```
python -m scripts.seed_test_templates --validate-only
```
Result: exit 0. Line emitted:
```
ok   TPL-A7-0003 [A7] 5 groups, 20 inputs, 0 area fields, 11 calculated, 2 criteria
```
Closing line: `All definitions valid. --validate-only, so nothing was written.`
33 definitions validated.

### A2. Catalogue parity + new f1/f2 test — PASS (with known, unrelated failures)
Command (cwd `backend-v2`):
```
python -m pytest tests/calculation/test_seeded_template_parity.py -q
```
Result: **3 failed, 281 passed**. The 3 failures are all
`TestA6BDissolutionWithReplacement` (`test_unit1_release_carryover`,
`test_per_timepoint_summary`, `test_amount_remaining`).

These are PRE-EXISTING and NOT caused by this change. Proven by running the same
class on the clean base checkout (`d:\RD-instance\GIT`, branch `MadhuriWorktree`):
```
python -m pytest "tests/calculation/test_seeded_template_parity.py::TestA6BDissolutionWithReplacement" -q
```
-> **3 failed, 1 passed**, identical assertions / expected values
(e.g. `release[0].content_1 == 83.2069`, obtained `EMPTY`). The A6B
with-replacement model is unrelated to TPL-A7-0003.

New f1/f2 test (cwd `backend-v2`):
```
python -m pytest tests/calculation/test_a7_0003_f1f2_calculations.py -q
```
-> **8 passed.**

### A3. Frontend build — PASS
Command (cwd `frontend-react`, `node_modules` already present, no `npm ci` needed):
```
npm run build        # tsc -b && vite build
```
Result: `tsc -b` produced no TypeScript errors; `vite build` succeeded
(336 modules, `built in 3.68s`). The only output note is Vite's advisory about a
chunk >500 kB — a non-blocking size hint, not an error.

**All Step A blocking checks passed:** seed validate ok, new template parity ok,
frontend build ok; the pre-existing A6B failures are unrelated and do not block.

---

## Step B — rebase and fast-forward

### Rebase onto the base — completed (conflict resolved cleanly)
```
git -C "d:\RD-instance\GIT\.worktrees\f1f2-calculations" rebase MadhuriWorktree
```
- The base had advanced since the branch was cut: it now carries
  `a7_profile_comparison_mirrored` (`_A7M`, TPL-A7-0002), `a9_sodium_metabisulfite`
  (`_A9_SMBS`), the Nitrosamine template (`7a20fa8`), and Lenacapavir RS
  (`6f3c2bd`).
- One conflict, in `backend-v2/scripts/template_definitions/__init__.py` (the
  import list and the `SEED_TEMPLATES` splice). Resolved by **preserving BOTH
  sides**: kept the base's `_A7M`/`_A9_SMBS` wiring and this feature's `_A7C`
  import + `*_A7C,` splice. No feature logic dropped, no base wiring dropped.
- A second `rebase MadhuriWorktree` was run to pick up the Lenacapavir commit
  (`6f3c2bd`) the base HEAD had moved to, so the branch now descends from the
  current base HEAD (required for ff-only). This second rebase was clean
  (no conflict). Rebased branch head: `d16ecaf`.
- Fast-forward is now possible: `git merge-base --is-ancestor MadhuriWorktree
  f1f2-calculations` exits 0.

### Re-verification AFTER rebase — FAILS due to a pre-existing base defect
```
python -m scripts.seed_test_templates --validate-only      # cwd backend-v2
python -m pytest tests/calculation/test_a7_0003_f1f2_calculations.py -q
```
Both now fail at import time with:
```
ModuleNotFoundError: No module named 'scripts.template_definitions.a7_profile_comparison_mirrored'
  ... __init__.py line 42: from scripts.template_definitions.a7_profile_comparison_mirrored import TEMPLATES as _A7M
```

### Root cause (NOT introduced by this feature)
- The base branch `MadhuriWorktree` committed the `_A7M` import into
  `__init__.py` in commit `7a20fa8`, but the module file
  `a7_profile_comparison_mirrored.py` was **never committed**.
- In the user's checkout `d:\RD-instance\GIT`, that file exists only as an
  **untracked** working-tree file (`git status` -> `?? .../a7_profile_comparison_mirrored.py`;
  `git log --all -- <file>` is empty; `git ls-tree MadhuriWorktree` does not list it).
- The base therefore only runs because the untracked file happens to sit on disk
  in the user's checkout. A clean worktree (this one) has no such file, so the
  whole `scripts.template_definitions` package import fails — which is why the
  post-rebase validate and the entire backend test collection error out here.
- This feature's own diff vs. base is exactly 4 files / +2 lines in `__init__.py`
  (`_A7C` import + splice) and does not reference the mirror module.

### Fast-forward merge — NOT performed (stopped on purpose)
`git -C "d:\RD-instance\GIT" merge --ff-only f1f2-calculations` was **not** run.
Reasons:
1. The required post-rebase re-verification does not pass in a clean worktree,
   so I will not present the branch as verified.
2. The only clean fixes are product decisions about ANOTHER task's deliverable
   (TPL-A7-0002), which are not mine to make inside this loop:
   - commit the untracked `a7_profile_comparison_mirrored.py` (ships another
     task's module), or
   - remove the base's dangling `_A7M` import + `*_A7M,` splice (reverts the
     base's intended TPL-A7-0002 wiring).
   A third option — merge anyway (the user's checkout has the file on disk, so it
   runs there) — leaves a committed tree that is import-broken in any clean
   checkout/CI and was declined without confirmation.

Branch state is otherwise ready: it is a strict descendant of `MadhuriWorktree`,
so a fast-forward is mechanically possible the moment the dangling-import
decision is made.

---

## Step C — what could NOT be verified

### Runtime browser layout check — NOT performed (environment cannot drive a browser)
I could not drive a browser in this environment, so the side-by-side responsive
layout is **NOT verified**. It must NOT be considered verified from reading code
alone. Reviewer/finalizer steps to verify at runtime:

1. Start the stack: run `start-lims.bat` (or `uvicorn` for the backend + `vite dev`
   for the frontend per the dev setup).
2. Open or create a worksheet on a TRF test line bound to `TST-F1F2CALC`
   (template `TPL-A7-0003`).
3. Confirm the two product header blocks ("Test Product" and "Reference Product")
   sit SIDE BY SIDE and share the window width on a wide screen.
4. Resize wide -> narrow and confirm the two blocks auto-fit, then STACK
   vertically with no overlap or clipping (flex-wrap + `minWidth: min(22rem,100%)`).
5. Confirm each header shows all six fields (Product Name, Batch No., Date of
   Analysis, Media, RPM, Volume) and each is independently editable.
6. Confirm Sections 3 and 4 render as two separate (stacked) repeating timepoint
   tables.
7. f1/f2 IS wired: enter matching time points + means in both tables and confirm
   the comparison section computes f1 and f2 (sanity cross-check from the plan:
   reference means 9,23,41,58,89 and test means 7,21,39,56,84 -> f1 ≈ 5.9,
   f2 ≈ 75.9 at 1 dp).

### DB seeding at runtime — not exercised here
`--validate-only` was used (nothing written). An actual `python -m
scripts.seed_test_templates` run to insert TPL-A7-0003 + Test Master TST-F1F2CALC
was not performed in this finalization pass (the earlier implementation pass
recorded an idempotent add/skip). `lims.db` and its backups are gitignored and
were never staged.

---

## Commands run in this pass (chronological)

1. `git -C ...f1f2-calculations log/status` — inspect branch state.
2. `python -m scripts.seed_test_templates --validate-only` (worktree) — PASS.
3. `python -m pytest tests/calculation/test_seeded_template_parity.py -q`
   (worktree) — 3 failed (A6B, pre-existing) / 281 passed.
4. `python -m pytest ...TestA6BDissolutionWithReplacement -q` (base checkout) —
   3 failed / 1 passed, identical -> failures pre-exist on base.
5. `python -m pytest tests/calculation/test_a7_0003_f1f2_calculations.py -q`
   (worktree) — 8 passed.
6. `npm run build` (worktree frontend) — PASS.
7. `git rebase MadhuriWorktree` (worktree) — conflict in `__init__.py`, resolved
   preserving both sides; continued; then a second clean `rebase MadhuriWorktree`
   to reach base HEAD `6f3c2bd`.
8. Post-rebase `--validate-only` and f1/f2 pytest (worktree) — FAIL:
   `ModuleNotFoundError: a7_profile_comparison_mirrored` (pre-existing base
   defect; module imported by base `__init__.py` but never committed).
9. ff-only merge into `d:\RD-instance\GIT` — NOT performed (see Step B).
