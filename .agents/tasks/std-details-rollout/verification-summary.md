
# Verification summary: live-DB sync (std-details-rollout, db-loop step)

## Live-DB evidence (2026-11-05)

- Worktree: `d:\RD-instance\GIT\.worktrees\std-details-rollout`, branch `std-details-rollout`, clean before apply, HEAD `20e7da5a364917f119f42e41b66dde73acc04edd`.
- Commands, run from the worktree `backend-v2` against `d:\RD-instance\GIT\backend-v2\lims.db`:
  1. `python -m scripts.standard_tabular_rollout --db <lims.db> --dry-run --report-dir <artifacts>`: exit 0; 25 rows / 28 groups to convert, 0 reference-audit violations, 0 equivalence diffs, 9 equal to module, 9 drifted, 7 DB-only, 0 problems; DB size 2600960 and mtime unchanged.
  2. `... --apply`: exit 0; fingerprint passed (57 rows; Active 48, Draft 4, Inactive 3, Superseded 2; integrity ok); updated 25 rows in one transaction.
  3. `... --verify`: exit 0, "verify: OK".
  4. second `... --apply`: exit 0, "no changes: every roster group is already tabular; nothing written".
- **Backup (pre-state):** `d:\RD-instance\GIT\backend-v2\lims.db.bak-std-rollout-20261105-180445` (57 rows). The backend on port 8443 was not restarted.

## Independent checks (read-only, live DB vs the backup)

- Catalogue: 57 rows in both; live status counts Active 48 / Draft 4 / Inactive 3 / Superseded 2; `PRAGMA integrity_check` = ok.
- Non-roster rows: the 32 other rows are identical in every column (including `definition`, `modified_*`).
- Roster rows (25): all columns except `definition`, `modified_by`, `modified_date` are identical to the backup (version and status included). `modified_by` = `std-details-rollout`.
- Outside the standard sections: every top-level definition key and every non-target group equals the backup. In each target group, all keys except `kind`, `rows`, `rowLabel` (and the removed `renderAsTable` in A4-0004) are identical to the backup.
- Shape: all 28 target groups (25 `standard`, 3 `standard_2`) are `kind: table` with `rows {min 1, max 10, default 1}` and `rowLabel {format "STD - {n}"}`. `standard_2` is a table in TPL-A4-0001, TPL-H1-0001 and TPL-H1-0002. No Active or Draft row has a singleton `standard` / `standard_2` left. TPL-A2-0002 `standard` is a table.
- Stored JSON is the canonical `json.dumps` of the parsed definition for all 25 rows.
- Module consistency: 9 rows byte-equal to their module definition (A1-0001, A1-0003, A2-0006, A4-0001, A6A-0005, A6B-0001, A6B-0002, A8-0004, NITRO-0001). 9 rows drifted from their module outside the standard sections before and after (A2-0001, A2-0003, A3-0001, A4-0004, A6A-0001, A6C-0001, A8-0001, A12-0001, A13-0001); their converted groups match the module on `kind/rows/rowLabel`. The drift is live-DB edits made after seeding, was deliberately not overwritten (it would change calculations, for example rounding on A6A-0001 `conc_ppm`), and is reported only. 7 rows have no module (A1-0002, A6A-0002, A6A-0003, A6A-0004, H1-0001, H1-0002, A8-0003).
- `test_worksheets`: 63 rows in both, row contents identical.

## Before/after evaluation against live data

`check_equivalence(old = backup definition, new = live definition, converted keys, stored worksheets of that template)` for all 25 rows: variants empty, synthetic fully filled sheet, every stored worksheet (28 worksheets on the 25 rows), and a padded 3-row variant. Result: **0 diffs** in calculated cells, acceptance-criteria results (observed, passed, limit, severity) and reportable result for every template. Non-blank calculated cells per synthetic run were 11 to 510, so no pass is vacuous. Reportable values (synthetic): A1-0001 4.49, A2-0001 11.45, A4-0001 2285.955, A6B-0001 1277.67, A8-0001 2562684.6, others in the roster output; A6A-0001/0002/0003/0004 have no single reportable result (EMPTY, same before and after).

## Known and unchanged

- Full backend suite and `npm run build` results are recorded in the earlier verification of the source work (5 known pre-existing failures: `TestA6BDissolutionWithReplacement::{test_unit1_release_carryover, test_per_timepoint_summary, test_amount_remaining}` and two `test_worksheet_service.py` tests). This step did not re-run them.
- Rows with no standard section, already-tabular rows and Inactive/Superseded/other Draft rows: untouched (see roster.md).
