# Worklog — 19 October 2026

Template / worksheet changes, all focused on **TPL-A2-0004 — Bupivacaine Lipid
Content & Drug-to-Lipid Ratio**. Template & calculation edits are applied to the
live Active row (id 35, v1) in `backend-v2/lims.db` (gitignored; a timestamped
`lims.db.bak-*` backup was made before each change) and kept byte-for-byte in
sync with the declarative source module
`backend-v2/scripts/template_definitions/a2_bupivacaine_lipid_ratio.py`.
Frontend changes are in source. Source changes are committed; the two completed
transposes were pushed. Each change was built via an implement-and-review
workflow with full gold-value verification.

**GxP caveat:** all template edits were applied directly to the live Active DB
row, not through the app's approve / e-sign flow.

---

## TPL-A2-0004 — tabular transpose + frontend `labelFrom` (commit c46fdcb)

- Transposed `std_areas` (Standard Replicate Injections) and `bkt_areas` (BKT
  Standard Injections) to **compounds-as-rows** with per-row and pooled
  Mean / SD / %RSD columns.
- Rewired the `stats` singleton to read the row tables by compound index
  (`std_areas.mean[idx]` / `bkt_areas.rsd[idx]`); **all `stats.*` keys
  unchanged**, so the `lipid_samples` %Assay chain and the 8 SST criteria were
  untouched.
- **Frontend `labelFrom` feature (new, generic):** added `labelFrom?: string`
  to `FieldDef` with `resolveLabelFrom` / `headerText` helpers at all three
  table-header render sites. Applied `labelFrom="standard.name[idx]"` to the
  `lipid_samples` and `drug_lipid` per-compound columns so column headers
  auto-fetch the compound name from Standard Details. Backward-compatible.
- Verified: all 19 gold values reproduce; DB row byte-for-byte equal to the
  module; parity test 7/7; frontend `tsc -b && vite build` green.

## TPL-A2-0004 — re-transpose to injection-rows × compound-columns (commit 7e3e270)

- Per the user's correction, flipped `std_areas` and `bkt_areas` to the
  **opposite** orientation: **injections-as-rows × compounds-as-columns**.
  - Columns = the compounds (`tri` / `dppg` / `chol` / `depc`), headers
    auto-fetched from Standard Details via `labelFrom="standard.name[idx]"`.
  - Rows = Injection 1..N, **expandable** (default 6, max 12) — the user wanted
    to add more injection rows (confirmed "Option A": expandable injection
    *rows*, not injection columns).
  - **Mean / SD / %RSD** rendered per compound column in the group footer, each
    aggregating down its column; BKT's are **pooled** with the matching
    `std_areas` compound column (sheet's `AVERAGE(H25:H30,B25:B30)`).
- `stats.*` keys again kept identical — only the source expression of each stat
  moved from a per-row value to a per-column aggregate.
- Verified: all 19 gold values reproduce (std means 8691453.5 / 4461370.5 /
  32403414.83 / 44013385.5; pooled Tri mean 8699733.9, %RSD 0.2383; Batch-B
  %Assay 99.979 / 86.200 / 101.772 / 100.390; ratio 0.841429); DB row
  byte-for-byte equal to the module; parity test 7/7; calculation suite 760
  passed, same 5 pre-existing unrelated failures (A6B + worksheet_service).

## Push

- Pushed `cd3ed90..7e3e270` to `origin/MadhuriWorktree` after the user reviewed
  — both transposes delivered (`c46fdcb`, `7e3e270`).

## TPL-A2-0004 — spare compound slots (capacity 6) — STARTED, NOT COMPLETED

- Started a workflow (`wf_20b5b30f961913a9`) to add **2 pre-provisioned hidden
  spare compound slots** (total capacity 6: the 4 real lipids + 2 spare), so
  adding a new compound row in Standard Details flows a brand-new compound
  through **every** section — standard Conc, std_areas/BKT injection columns,
  `stats` aggregates, %Assay, mg/mL(Lipid), Sum of Lipid, LC context, and an
  SST %RSD criterion (chosen scope: "1a — full flow-through"; approach: option 2
  pre-provisioned hidden slots, no new engine feature).
- Design constraints captured for resumption: spare slots blank must NOT change
  any gold value (blank exclusion from aggregates); existing `stats.*` keys stay
  byte-identical with spare keys additive only; spare-slot SST criteria must not
  spuriously fail when blank; `sum_lipid` must stay exactly 15.790645 when spare
  mg/mL are blank.
- **Status: aborted at the planning step at the user's request (stop for
  today).** Only the backup + evidence dir were created; **no module or DB
  changes were made**. Backup taken: `lims.db.bak-a2slots-20261019-232021`.
  The planning artifact is under
  `backend-v2/.agents/tasks/a2-0004-sixth-compound-slots/`.

---

## Next session

- Resume the **spare compound slots (capacity 6)** work: re-launch the
  implement-and-review workflow with the scope above (1a full flow-through via
  pre-provisioned hidden slots).
- After it completes and is reviewed in the UI, commit + push that change.
- Backups on disk from today: `lims.db.bak-a2areas-20261019-153914`,
  `lims.db.bak-a2areas-20261019201840`,
  `lims.db.bak-a2areas-transpose-20261019-224718`,
  `lims.db.bak-a2slots-20261019-232021`.
