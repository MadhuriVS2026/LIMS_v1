# TPL-A7-0002 mirrored f1/f2 dissolution template — side-by-side Reference|Test render

Adds a new dissolution profile-comparison template (TPL-A7-0002, test TST-F1F2M, archetype A7) that reuses TPL-A7-0001's f1/f2 arithmetic and five validity criteria verbatim via deep-copy, and renders the single `timepoints` sequence as two responsive side-by-side tables (Reference | Test) with timepoint label+unit edited on the Test side and mirrored read-only into the Reference side. The change is confined to four files: a new seed module, a two-line registration in `__init__.py`, a new parity test, and a new `renderMirroredProfile` in `WorksheetForm.tsx`. The backend math and the "same timepoints for both products" guarantee are preserved for free because the backing data model stays a single row carrying both products' means. The code is sound; the blocker is in the verification evidence, not the code.

Watch for: the mandatory runtime browser confirmation of non-overlapping side-by-side layout and mirroring was NOT performed (confirmed — stated explicitly in verification.md); the brief requires rejecting rather than accepting code-only reasoning for this check. eslint was not run (confirmed — not a dependency in this frontend; build type-checks clean).

**Verdict**: NEEDS_CHANGES

## High-level view

The backend is a disciplined structural clone. The new module imports `a7_profile_comparison` and deep-copies `_timepoint_fields()`, `_TIMEPOINTS_GROUP`, `_COMPARISON_GROUP`, context, and criteria, so the f1/f2 expressions and the five criteria are the literal same objects as A7. Keeping A7's single `timepoints` sequence (one row per timepoint carrying both products' means) is what preserves `abs(ref_mean - test_mean)` in-row, the `prior.`-based 20%/10% RSD-limit rule, and the structural "same timepoints for both products" guarantee. The only additive field is a per-row `unit` text input that no expression references.

The template metadata matches the brief exactly: code TPL-A7-0002, name and test_name both "Dissolution Profile Comparison (f1 / f2) — Mirrored", test code TST-F1F2M, archetype A7, resultRef `comparison.f2`, registered in `__init__.py` immediately after A7. The diff touches only four files; A7's own module and every other archetype module are untouched.

The frontend adds `renderMirroredProfile`, gated on `template_code === 'TPL-A7-0002'` + `group.key === 'timepoints'`, following the existing `renderCumulativeVertical` pattern and reusing the shared helpers (`renderInput`, `renderGroupToolbar`, `addRow`, `removeRow`, `isGroupEditing`, `renderGroupHeaderContext`). Two tables sit in a `flex flex-wrap` row, each `flex: 1 1 22rem` / `minWidth: min(22rem, 100%)`, `w-full` + `tableLayout: fixed`, with per-cell wrapping. Mirroring is inherent: both tables read/write the same backing row, Test editable, Reference read-only. No new UI libraries.

The recorded verification covers the parts that can be checked without a desktop: `--validate-only` passed with TPL-A7-0002 reporting one more input than A7 (the `unit` field), the seeder added TPL-A7-0002/TST-F1F2M and is idempotent, pytest parity passed (f1=5.9, f2=75.9, full agreement with A7 on identical inputs; the 3 A6B failures are pre-existing), and `npm run build` type-checked clean. The gaps are the two checks the brief singles out: eslint was not run, and — the blocker — the runtime browser confirmation of the side-by-side layout and mirroring was never driven. The brief states that layout and mirroring cannot be judged from code alone and that if that evidence is missing the review must reject with a finding.

<details>
<summary>Issues (2)</summary>

1. **Runtime layout/mirroring check missing (blocking)** — verification.md states the runtime browser confirmation of non-overlapping side-by-side layout and timepoint label+unit mirroring was NOT driven. The brief designates this check as un-judgeable from code and mandates rejection when it is absent. A human (or the finalize step) must start the stack, open a worksheet bound to TST-F1F2M, and confirm: tables side by side sharing window width; wide→narrow resize auto-fits then stacks with no cell clipping/overlap; typing label+unit in a Test row mirrors into the matching Reference row while mean%/%RSD stay per-product; example profiles yield f1≈5.9/f2=75.9. Capture a screenshot.
2. **eslint not run (non-blocking)** — eslint is not a declared dependency and there is no config in `frontend-react`, so `npm run lint` could not run without fetching an unpinned eslint. The production build type-checked the new code clean, so this is informational, but note the lint gate in the plan was not satisfiable as written.

</details>

<details>
<summary>Details</summary>

### Verbatim arithmetic reuse via deep-copy

The new module does not retype any expression. It imports `a7_profile_comparison as a7` and builds its fields from `copy.deepcopy(a7._timepoint_fields())`, its groups from deep-copies of `a7._TIMEPOINTS_GROUP` and `a7._COMPARISON_GROUP`, and its definition from `copy.deepcopy(a7.A7_DEFINITION)` (which carries context and criteria). I confirmed every imported symbol exists in the A7 source: `_MAX_TIMEPOINTS` (20), `_timepoint_fields()`, `_TIMEPOINTS_GROUP`, `_COMPARISON_GROUP`, `A7_DEFINITION`. Because the strings are copied, not re-authored, f1 = `sum_abs_diff / sum_ref * 100` and f2 = `50 * log10(100 / sqrt(1 + mean_sq_diff))` are byte-for-byte A7's, as are the per-row `abs_diff`, `sq_diff`, `ref_in_scope`, `*_over_85`, `worst_rsd`, `has_rsd`, `rsd_limit`, `rsd_breach`. The parity test independently pins this: it evaluates both A7_DEFINITION and A7M_DEFINITION on the same 5-point example and asserts agreement across `n_points`, `sum_abs_diff`, `sum_ref`, `sum_sq_diff`, `mean_sq_diff`, `f1`, `f2`, `points_over_85`, `rsd_breaches`, plus f1=5.9/f2=75.9 and the five criteria keys.

### Single-row data model preserves the three invariants

The chosen model keeps one `timepoints` sequence group where each row carries both products' means and %RSD. This is what makes `abs_diff = if(included > 0, abs(ref_mean - test_mean), blank())` computable in-row — a two-group model would break row alignment. It is also what guarantees "same timepoints for both products": there is one `time`/`unit` per row, so a 4h reference value cannot be compared against a 6h test value. And it keeps `rsd_limit = if(has_rsd > 0 and sum(prior.has_rsd) = 0, 20, 10)` meaningful, since `prior.` references earlier rows of the same sequence, so the 20%-at-first / 10%-thereafter rule survives untouched. The new per-row `unit` text input (default "Hr") is inserted right after `time`; no expression references it, so parity is exact.

### Frontend render and mirroring

`renderMirroredProfile` resolves field defs once (`time`, `unit`, `included`, `ref_mean`, `ref_rsd`, `test_mean`, `test_rsd`) and paints two tables over the same `rows` array. The Test table hosts the editable `time`/`unit` inputs; the Reference table renders those same cells through `readonlyShared`, which reads `values[group.key][rowIndex][field.key]` and shows an em-dash when blank. Because both tables address the identical backing cell, label+unit cannot diverge — mirroring is structural, no `mirrorFrom` wiring. `ref_mean`/`ref_rsd` live on the Reference table and `test_mean`/`test_rsd` on the Test table, independently editable per product. The `included` toggle is placed on the Reference table only (it is shared), matching the plan. Add/Remove-timepoint controls are gated on `canAddRows && editingThisGroup`, same as `renderCumulativeVertical`. The dispatch branch is inserted before the generic renderer, so the `comparison` singleton and context fall through unchanged — f1/f2 display exactly as for A7.

### Responsive layout — only runtime can confirm

The layout uses the in-repo recipe: an outer `flex flex-wrap gap-3`, each table wrapper `flex: 1 1 22rem` with `minWidth: min(22rem, 100%)`, each `<table>` `w-full` with `tableLayout: fixed`, and per-cell `wordBreak: break-word` / `overflowWrap: anywhere` plus `whiteSpace: normal` on headers. The brief is explicit that non-overlapping side-by-side layout and mirroring cannot be judged from code alone and require a runtime browser check, and verification.md records that this check was NOT driven (no browser automation / desktop in the coder's environment). That recorded gap is the blocking finding — "plausible from code" is exactly what the brief says is insufficient here.

### Isolation of the change

`git diff` name-only against the parent commit lists exactly the four expected files. A7's module `a7_profile_comparison.py` and all other archetype modules are not in the diff, satisfying the "TPL-A7-0001 and all other archetype modules UNCHANGED" requirement. The `__init__.py` change is the import of `_A7M` and `*_A7M,` placed right after `*_A7,`, ordered by archetype as the surrounding list is.

</details>

<details>
<summary>File map</summary>

- `backend-v2/scripts/template_definitions/a7_profile_comparison_mirrored.py` (new) — TPL-A7-0002 module; deep-copies A7's fields/groups/context/criteria, adds one per-row `unit` input.
- `backend-v2/scripts/template_definitions/__init__.py` — import `_A7M` and splice `*_A7M,` after `*_A7,`.
- `backend-v2/tests/calculation/test_a7_0002_mirrored_parity.py` (new) — pins f1=5.9/f2=75.9 and full parity with A7 on identical inputs; checks the five criteria keys.
- `frontend-react/src/features/test-templates/components/WorksheetForm.tsx` — `CSSProperties` import, `allowMirroredProfile` flag, `renderMirroredProfile`, and the dispatch branch.

Full diff: `git -C d:\RD-instance\GIT\.worktrees\f1f2-mirror-template diff HEAD~1`

</details>
