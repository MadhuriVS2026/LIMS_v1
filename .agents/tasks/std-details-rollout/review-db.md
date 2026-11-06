# Review: live-DB sync, Standard Details to tabular

Verdict: APPROVED. No blockers.

## Evidence checked (read-only)

Sources: plan.md item 8, roster.md, verification-summary.md, commit messages 02efc3a..HEAD (7c12d0e), and direct read-only queries of `lims.db` against `lims.db.bak-std-rollout-20261105-180445`. I did not re-run any test suite or tool.

- Backup: present, timestamped, beside the DB, created at the recorded apply time (18:04:45 UTC). It has 57 rows (Active 48, Draft 4, Inactive 3, Superseded 2), `integrity_check` ok, and 63 worksheets.
- Fingerprint and abort-on-mismatch: recorded in the commit message of 20e7da5 and in the verification summary. The backup holds the expected 57/48 catalogue, so the guard had its precondition.
- Worktree: `git status --porcelain` is empty now. The apply HEAD (20e7da5) is recorded. The only later commit (7c12d0e) changes no files.
- Live DB: 57 rows, same status counts, integrity ok, 63 worksheets. The set of row ids is identical to the backup.
- Row changes: exactly 25 rows differ from the backup. For every one, the only columns that differ are `definition`, `modified_by` and `modified_date`. Identity, `version`, `status`, `result_unit`, approval and supersession columns are unchanged. The other 32 rows are identical in every column.
- Scope of definition change: for the 25 rows, no top-level key outside `groups` changed. Group order is unchanged. Exactly 28 groups differ (25 `standard` and 3 `standard_2`, in A4-0001, H1-0001 and H1-0002). In each one the only differences are `kind` singleton to table, `rows {min 1, max 10, default 1}`, `rowLabel {format "STD - {n}"}`, and removal of `renderAsTable` (A4-0004 only). Fields and formulas in those groups are unchanged. No non-standard group changed.
- No Active or Draft row has a singleton `standard` or `standard_2` left.
- Module consistency: A1-0001, A1-0003, A2-0006, A4-0001, A6A-0005, A6B-0001, A6B-0002, A8-0004 and NITRO-0001 parse to exactly their module definition. The one textual difference is the key order inside the converted group (`rows` and `rowLabel` come after `fields` in the DB text). JSON objects are unordered and the engine and UI read `fields` by array order, so this has no effect. The roster's "byte-equal" means equal after parsing.
- DB-only: A1-0002, A6A-0002, A6A-0003, A6A-0004, A8-0003, H1-0001 and H1-0002 are converted and listed. The other DB-only rows (A5-0002..4, A6D-0002) have no standard section and are listed under "no standard section". Every code in the live DB appears in roster.md.
- Roster vs live: the converted groups, versions and statuses in roster.md match the live DB.
- Before/after proof: recorded as 0 diffs across calculated cells, criteria and reportable result for all 25 rows. The checks cover the empty sheet, a synthetic filled sheet, stored worksheets and a 3-row padded variant. Non-blank calculated counts are 11 to 510, so the passes are not vacuous.

## Judgement call, not a blocker

Nine rows (A2-0001, A2-0003, A3-0001, A4-0004, A6A-0001, A6C-0001, A8-0001, A12-0001, A13-0001) are not byte-consistent with their modules. The cause is live-DB edits made after seeding, outside the standard sections. For A6A-0001 and A8-0001 the `standard` fields also differ from the module (labels, defaults, units). I confirmed that on these two the sync changed only `kind`, `rows` and `rowLabel`. The approved plan chose not to overwrite them, because copying the module would change calculations such as the rounding on A6A-0001 `conc_ppm`. That would break the hard formula-preservation constraint. The drift is listed per template in roster.md. This is an approved trade-off, so I am not blocking on it.
