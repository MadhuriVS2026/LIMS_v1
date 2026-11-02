# Fix %-release carry-over correction in TPL-A6A-0004 (Dissolution_12units)

The `timepoints_release` sequence group of template id 34 was rewritten so the 12-unit dissolution %-release reproduces the Bupivacaine gold sheet exactly. The buggy single-expression release (wrong media field, no TRUNC/ROUND staging, carry accumulating the already-cumulative value) is replaced by the sheet's three stages: a TRUNC-3 uncorrected helper (C57), a TRUNC-3 per-row correction factor (C73), and a ROUND-0 cumulative corrected value that adds the sum of all prior corrections (C88). Media is re-sourced from `test_prep.dilution_volume` (750) instead of `test_prep.medium_volume` (which held 1), and because withdrawal equals replenishment in this sheet, media stays 750 on every row. The summary row gains the sheet's rounding (mean→0 dp, sd/rsd→1 dp). The change is DB-only; `lims.db` row 34 now shows `modified_by='release-fix'`.

Watch for: the acceptance gate is numeric and the recorded computed-vs-expected table reports ALL PASS for the U-1 series, media==750, and the summary (confirmed). The after-definition in the DB matches the plan's transcription expression-for-expression (confirmed). The stored worksheet 27 has corrupted 30-min areas for units 2–4, so the 30-min cross-unit summary was validated against a clean vector rather than stored data — this is analyst-entered data left untouched, out of scope (confirmed, documented). Three frontend files are modified in the working tree but are unrelated to this backend calc fix (confirmed).

**Verdict**: APPROVED

## High-level view

The media bug is the root cause and it is fixed. The old `media = medium_volume - (rowno-1)*withdrawal` read field value 1 and went negative after the first timepoint; the new `media = if(rowno=1, dilution_volume, prev.media - withdrawal + replenishment)` sources 750 and holds it flat because withdrawal (5) equals replenishment (5), matching the sheet's T56/T57 column.

The release math is now the sheet's three distinct stages with TRUNC/ROUND at the exact points: `uncorrected_N` TRUNC-3 (C57), `correction_N = TRUNC(withdrawal/media * uncorrected_N, 3)` (C73), and the visible `unit_N = ROUND(uncorrected_N + sum(prior.correction_N), 0)` (C88 cumulative). The carry is now a separate truncated correction factor summed over prior rows, not the previous combined-value accumulation.

The group's shape is preserved: 12 units wired through `time_intervals.unit_N[rowno-1]`, rows `{min:1, max:20, default:12}`, the mirrored `time_hr` first field, 18 visible fields (time_hr + unit_1..12 + mean/sd/rsd/min/max) and 25 hidden helpers (media + 12 uncorrected + 12 correction). The summary carries the sheet's rounding and relies on the engine dropping blank units.

Scope is clean: only `timepoints_release` differs from the pre-fix snapshot; context, criteria, and every other group are byte-identical. The before snapshot (`tpl34_before.json`) is the reversible backup and the throwaway evaluator is deleted. The 30-min data corruption in worksheet 27 is correctly identified as out-of-scope analyst data and was not silently rewritten.

<details>
<summary>Issues (1)</summary>

1. **Unrelated frontend changes in working tree** (non-blocking) — `WorksheetForm.tsx`, `PrintWorksheetPage.tsx`, `TemplateListPage.tsx` are modified in the tree but belong to a different change; keep them out of any commit that lands this backend-only calc fix.

</details>

<details>
<summary>Details</summary>

### Media bug fix and the net-750 behavior

The pre-fix `media` expression was `test_prep.medium_volume - (rowno - 1) * test_prep.withdrawal_volume`. In worksheet 27 `medium_volume` holds 1, so media evaluated to 1, −4, −9 … and release went negative after the first timepoint. The fix sources the real bath volume from `test_prep.dilution_volume` (750) and models replenishment per row:

```
media = if(rowno = 1, test_prep.dilution_volume,
           prev.media - test_prep.withdrawal_volume + test_prep.replenishment_volume)
```

Because withdrawal (5) and replenishment (5) are equal in this sheet, media stays 750 on every row — matching the sheet's T56=`F18`=750 and T57=`T56-E23+G23`=750. The recorded table reports media==750 for all 12 rows (confirmed). The field is now a declarative `prev.media` recurrence rather than a closed-form multiple of `rowno`, so a sheet where withdrawal and replenishment differ will track correctly instead of being hard-coded to the equal case.

### Three-stage release math with TRUNC/ROUND at the sheet's points

The old `unit_N` folded the whole chain into one expression with no truncation, used the wrong divisor chain (`dilution_volume / 1 * media / aliquot_volume`), and `carry_N` accumulated `prev.unit_N` — the already-cumulative corrected value — which double-counts. The rewrite splits into the sheet's three stages:

```
uncorrected_N = TRUNC( area/mean_std * (standard chain) * media/1
                       * aliquot_volume/pippette_2
                       * potency/(label_claim_mgml * sample_volume) * 1/1, 3 )      # C57
correction_N  = TRUNC( withdrawal_volume / media * uncorrected_N, 3 )               # C73
unit_N        = ROUND( uncorrected_N + sum(prior.correction_N), 0 )                 # C88 cumulative
```

The mapping transcribes the workbook cell formula term-for-term: `media/1`←F18/1, `aliquot_volume/pippette_2`←H18/G18 SPL pipette chain, `potency/(label_claim_mgml*sample_volume)`←E16/J12, trailing `1/1`←P26/P27 MW. The cumulative correction is now a sum of separate truncated per-row correction factors over all preceding rows (`sum(prior.correction_N)`), which is the C88 `ROUND(E57+C73+D73,…)` pattern — the earlier double-counting is gone. On row 1 `sum([])` returns 0, so the first corrected value is `ROUND(uncorrected,0)` as the sheet has it.

The recorded computed-vs-expected table pins this chain against U-1's full series: uncorrected 30min 19.91 → 8h 84.244, correction 30min 0.132 / 1h 0.287 / 2h 0.422, corrected `[20,43,64,74,78,83,87]` — all PASS (confirmed from the evidence table). TRUNC lives in the expression (no field-level `rounding` on the helpers) and ROUND-0 is in the visible `unit_N` expression, matching the brief's TRUNC/ROUND points exactly.

### Structure, wiring, and visibility preserved

The 12-unit shape is intact. Each `uncorrected_N` reads `time_intervals.unit_N[rowno - 1]` (verified for all N=1..12), so the release group stays wired to the Timepoints-For-Sample area table by the same index convention. `rows` remains `{min:1, max:20, default:12}` and `time_hr` is still the first field with `mirrorFrom: time_intervals.time_hr`. The visible set is exactly `time_hr` + `unit_1..unit_12` + `mean/sd/rsd/min_val/max_val` (18 fields); the hidden set is `media` + `uncorrected_1..12` + `correction_1..12` (25 fields). This is the arrangement the brief requires — helpers hidden, the analyst-facing columns and summary visible.

### Summary rounding and blank-unit exclusion

`mean`, `sd`, and `rsd` now carry `rounding` of 0, 1, and 1 dp respectively; `min_val`/`max_val` are unrounded. The expressions use the engine's `mean/sd/rsd/min/max`, which drop blanks (and `sd`/`rsd` return blank for fewer than two numbers), so units left empty are excluded from the summary rather than treated as zero. The evidence confirms the summary reproduces: 1h Mean=41/Max=43 against clean stored data, and 30min Mean=19/SD=1.1/%RSD=5.8/Min=17/Max=20 against the clean 30-min vector (confirmed).

### Scope, backup, and the worksheet-27 data caveat

A field-by-field comparison of the pre-fix snapshot against the live DB definition shows only `timepoints_release` changed; `context`, `criteria`, `resultRef`, and every other group (`standard`, `stats`, `std_areas`, `test_prep`, `time_intervals`, `release_chart`, …) are byte-identical (confirmed). Only TPL-A6A-0004 (id 34) was touched. The pre-fix `tpl34_before.json` is retained as the reversible backup and the throwaway `verify_gold.py` is no longer present in the task directory (confirmed).

Worksheet 27's stored 30-min row holds U-1's 1h/2h/3h areas in units 2–4 (mis-entered analyst data). The coder correctly validated the 30-min cross-unit summary against the clean sheet vector rather than the corrupted stored row, and left the analyst-entered DB data untouched as out-of-scope. This is the right call for a formula-exact calc fix — rewriting source data silently would be the wrong move — and it is documented in both the plan and the verification note (confirmed).

### Unrelated frontend changes bundled in the tree

`git status` shows `WorksheetForm.tsx`, `PrintWorksheetPage.tsx`, and `TemplateListPage.tsx` modified. These are UI changes unrelated to the backend %-release formula and are out of scope for this review. They are not blocking, but they should not ride along in a commit that lands this DB-only calc fix.

</details>

<details>
<summary>File map</summary>

- `lims.db` (row 34 of `test_templates`) — `timepoints_release` group rewritten (media re-sourced, three-stage TRUNC/ROUND release, summary rounding); `modified_by='release-fix'`. The DB is not under version control, so there is no git diff; the change was read directly from the live row and compared against the pre-fix snapshot.
- `.agents/tasks/a6a0004-release-fix/tpl34_before.json` — pre-fix snapshot / reversible backup.
- `.agents/tasks/a6a0004-release-fix/verification.md` — recorded computed-vs-expected table (the numeric gate evidence).
- `.agents/tasks/a6a0004-release-fix/plan.md` — implementation plan with the confirmed sheet formulas and gold values.
- (working tree, unrelated) `frontend-react/.../WorksheetForm.tsx`, `PrintWorksheetPage.tsx`, `TemplateListPage.tsx` — UI changes, out of scope.

</details>
