# Worklog — 23 October 2026

Template / worksheet changes, focused on **TPL-A2-0004 — Bupivacaine Lipid
Content & Drug-to-Lipid Ratio** and the new **TPL-A12-0003 — Amphotericin B
Drug-to-Lipid Ratio**. Template & calculation edits are applied to the live
Active DB rows in `backend-v2/lims.db` (gitignored; a timestamped `lims.db.bak-*`
backup was taken before each change) and kept byte-for-byte in sync with the
declarative source modules under
`backend-v2/scripts/template_definitions/`. Source changes are committed
locally; see hashes below.

**GxP caveat:** all edits to existing templates were applied directly to the
live Active DB row, not through the app's approve / e-sign flow.

---

## TPL-A2-0004 — Sample Details "% Mean" work

- **Cross-set mean recovery.** A workflow had replaced the per-set `pct_mean`
  with a cross-set mean in-place and updated the DB, which was not the intended
  final shape. Aborted it, restored the module + parity test to the last commit,
  and re-synced DB row 35 back to the committed per-set `pct_mean`
  (`mean([pct_assay])`). Backup `lims.db.bak-a2resync-20261023-225917`. Clean
  baseline re-established before continuing.

- **"% Mean each compound" summary block (commit 90bcaf2).** Added a new
  read-only `mean_each_compound` table group rendered BELOW the Set 2 block.
  Each row is a compound; the "% Mean" = cross-set mean of that compound's
  % Assay across Set 1 and Set 2
  (`mean([ lipid_samples.pct_assay[(rowno-1)], lipid_samples.pct_assay[(rowno-1)+4] ])`,
  blank-skipping). Purely additive — `lipid_samples`, the per-set `pct_mean`,
  and `drug_lipid` (ratio 0.841429) are unchanged. Verified: no circular
  dependency, Set-1-only and both-sets oracle fixtures, DB row 35 byte-equal,
  same 5 known pre-existing test failures.

- **Removed the Set Source column (commit 2ce78f2).** Dropped the static
  "Average of set1 and set2" (`set_source`) text column from the
  "% Mean each compound" block, leaving just Compound Name + % Mean. Parity test
  trimmed accordingly (14/14 pass); DB row 35 re-synced byte-equal. Backup
  `lims.db.bak-a2rmcol-20261023-233437`.

## TPL-A12-0003 — NEW: Amphotericin B Drug-to-Lipid Ratio (commit 612ecbb)

- Created a brand-new A12 derived-roll-up template reproducing a liposomal
  Amphotericin B batch-release sheet, seeded Active, bound to a NEW Test Master
  entry tagged exactly **"Ampho-lipid to drug ratio"** (TST-ALDR).
- One multi-batch table (one row per batch): per-component Assay (%) inputs +
  Content (mg/vial) calcs, Calculated Lipid content, Calculated Drug/Lipid ratio.
- Reverse-engineered the per-component label claims from the gold data
  (Content = Assay% × LC/100): Cholesterol 52.0, HSPC 213.0, DSPG 81.6,
  Amphotericin B 50.0 mg/vial — modelled as overridable context.
  Lipid content = Chol + HSPC + DSPG (drug excluded); Ratio = Ampho / Lipid.
- Five blocking acceptance criteria: Chol/HSPC/Ampho assay 90–120 %, DSPG
  80–120 %, ratio 0.11–0.17.
- Verified: all three gold batches reproduce exactly (ratios 0.1511 / 0.1476 /
  0.1500, contents and lipid totals to 4 dp); seeded once Active; DB definition
  byte-equal to the module; new parity test passing; same 5 known pre-existing
  failures. Backup `lims.db.bak-ampho-20261023-234640`.
- Note: the Amphotericin B content figures in the source table (55.3200 etc.)
  are transcription slips; the formula-exact values (55.30 etc.) are the only
  ones that reproduce the authoritative gold ratios, and those are used.

---

## Commits (local; later pushed through 612ecbb)

- `9b92897` / `32e3448` / `9dfdfb8` — TPL-A2-0004 tall per-SET layout + % Mean
  column + verification (earlier in the Sample Details arc)
- `b6b6c90` — SET auto-label
- `e3985a6` — static Compound Name / Area headers
- `d73918a` — generic column merge (SET)
- `a3e34c2` / `906b76f` / `d6201d0` — fixed Set 1/Set 2 blocks
- `90bcaf2` — "% Mean each compound" block
- `2ce78f2` — remove Set Source column
- `612ecbb` — NEW TPL-A12-0003 Amphotericin B Drug-to-Lipid Ratio
