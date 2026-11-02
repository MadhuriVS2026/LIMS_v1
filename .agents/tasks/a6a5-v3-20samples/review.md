# Review — TPL-A6A-0005 v3: extend 6 → 20 sample slots + 20-sample UI

Coordinated backend-definition + frontend change for archetype A6a template
TPL-A6A-0005. Part A branches a v3 DRAFT of the Active v2 template and widens the
per-sample field families (`area_N`/`jassay_N`/`kfrac_N`/`unit_N`) and the four
stats aggregates from N=1..6 to N=1..20, raises `weights.rows.max` to 20, and caps
`timepoints_release.rows.max` at 10. Part B extends the existing custom vertical
render in `WorksheetForm.tsx` to drive up to 20 sample rows per timepoint with
reveal-on-add / clear-on-delete, plus the already-present timepoint add/delete/edit/
save controls, all reusing the shared persistence helpers. The calculation engine is
untouched and the recorded parity test passes byte-for-byte.

Watch for: a separate, unrelated A9 sodium-metabisulfite template is bundled in the
same working tree (new seed module + `__init__.py` registration) — out of scope for
this task, non-blocking, but flagged (**confirmed**).

**Verdict**: APPROVED

## High-level view

The backend definition is byte-faithful to the locked design. The sample families and
stats list are built from a single `_SAMPLES = 20` constant in the four contiguous
loops the v2 module already used, with `jassay_N` carrying the literal
`weights.weight[N - 1]` index as required and `kfrac_N`/`unit_N`/stats following the
exact prescribed forms. `weights.rows.max` is 20 with default held at 6, the timepoint
cap is 10, and `resultRef` plus the cumulative-carry model are unchanged.

The value-neutrality of the 6→20 extension is proved by the unedited parity test, which
the coder recorded as 7/7 passing. The v3 definition was pushed via the branch→PUT API
route and read back: version 3, status Draft (not approved/e-signed), correct field
counts, correct weights index, stats aggregating `unit_20`.

The engine directory and the entire `backend-v2/src` tree show zero modifications, so
no calculation code was touched.

The frontend change is confined to the one `renderCumulativeVertical` block, gated
strictly to `template_code === 'TPL-A6A-0005'` AND `group.key === 'timepoints_release'`.
It adds per-timepoint visible-sample-count state with filled-slot derivation, an inner
Add-row that reveals the next empty slot, and a per-row clear that blanks `area_N` via
the shared `setCell`. Computed `jassay_N`/`kfrac_N`/`unit_N` come straight from
`computed.rows`; C2 is the display-only `unit_N − jassay_N` subtraction, blank-guarded.
Caps are 20 samples and 10 timepoints.

Verification evidence is present and passing: parity test 7/7, `npm run build` clean
with zero TS errors, ESLint noted as not installed (not a failure).

<details>
<summary>Issues (1)</summary>

1. **Unrelated A9 template bundled** — a new `a9_sodium_metabisulfite.py` seed module
   and its `__init__.py` registration sit in the same working tree; they are outside
   this task's scope. Non-blocking. Confirm they belong to a separate task/commit so
   they don't ride along unreviewed.

</details>

<details>
<summary>Details</summary>

### Per-N formula pattern and the N-1 weights index

`_jassay_expression(u)` emits the full operator chain with `weights.weight[{u} - 1]`
left as literal text, so `area_7` reads `weights.weight[7 - 1]` and `area_20` reads
`weights.weight[20 - 1]` — matching the design's "do NOT pre-compute to `[6]`/`[19]`"
instruction and the recorded read-back (`jassay_7 uses weights.weight[7 - 1]`,
`jassay_20 uses weights.weight[20 - 1]`). `kfrac_N` is
`jassay_N * prep.withdraw_replace / prep.media_vol` and `unit_N` is
`jassay_N + sum(prior.kfrac_N)` with kind `calculated`, label `Unit-N`, unit `%`. The
four families are built in four contiguous `range(1, _SAMPLES + 1)` loops with field
order preserved (all `area_N`, then all `jassay_N`, then all `kfrac_N`, then all
`unit_N`, then stats), as specified (**confirmed**).

### Stats aggregation over unit_1..unit_20

The bracket list `ul` is built once over `range(1, _SAMPLES + 1)` and fed to `mean`,
`min_val`, `max_val`, and `rsd = sd(ul) * 100 / mean`. The read-back confirms all four
aggregate `unit_20`. The design's deliberate decision to keep the stats fields
byte-faithful to v2 (no `round/1dp` key, matching the live definition and the parity
test's full-precision assertions) is respected; the task prompt's mention of "round/1dp"
is a display concern and the parity test pins full precision, so the plain `calculated`
form is correct here (**confirmed**).

### Caps and resultRef

`weights.rows.max = _SAMPLES` (20) with `default = _UNITS` (6) and `min 1`, so
`area_20` can resolve its pellet weight while the default stays at 6. The timepoint
sequence is capped via `_TIMEPOINTS_MAX = 10` (`rows.max = 10`, default 7, min 1).
`resultRef` stays `timepoints_release.mean` and the non-recursive `sum(prior.kfrac_N)`
cumulation model is intact (**confirmed**).

### Parity and DRAFT status

The coder recorded the unedited parity test passing 7/7 (`7 passed in 0.20s`), which is
the authoritative value-neutrality proof: slots 7..20 are blank in the fixture and the
blank-tolerant aggregates leave every gold value unchanged. The recorded gold values
match the task's expected set (1 Hr jassay 15.00/16.58/12.70, kfrac 0.30/0.33/0.25,
unit 14.996.../16.579.../12.701...; 24 Hr jassay 50.24, kfrac 1.00; cumulative carry
intact). The v3 draft read-back asserts `version == 3`, `status == Draft` — not
submitted/approved/e-signed. The seed module was updated to the 20-slot form and the
Part-A script imports `A6A_LEUP_DEFINITION`, so the DB draft and the parity-tested
module are the same source (**confirmed** from verification.md; parity not re-run per
instructions).

### Engine untouched

`git status --porcelain` over `backend-v2/src/domain/services/calculation` and the whole
`backend-v2/src` tree returns nothing — no calculation or API/service code changed. The
definition change rides entirely on the seed module and the one-shot update script
(**confirmed**).

### Frontend gating and reuse

The vertical render is reached only when `allowCumulativeVertical`
(`detail.worksheet.template_code === 'TPL-A6A-0005'`) AND `group.key ===
'timepoints_release'`; every other template and group falls through to the generic
renderer. `SAMPLE_MAX` is derived from the count of provisioned `area_N` fields
(falling back to 20), so the UI tracks the definition rather than a hard-coded width.
Add-row bumps a per-timepoint `visibleSamples[rowIndex]` count; per-row clear calls the
shared `setCell(group.key, rowIndex, 'area_N', null)` and decrements the visible count.
The timepoint block reuses `addRow`/`removeRow`/`renderGroupToolbar`. No parallel
persistence path exists — the only writes go through `setCell` and the existing toolbar
save/autosave (**confirmed**).

### Reveal-on-add / clear-on-delete / hidden unused rows

`visibleCountFor` returns an explicit `visibleSamples` entry when set, else the highest
N whose `area_N` carries a present value (so reopening a saved sheet shows exactly the
filled rows), clamped to `[1, SAMPLE_MAX]`. The row map renders only
`areaFields.slice(0, visibleCountFor(rowIndex))`, so unused slots are hidden rather than
rendering a wall of empty rows. Add-row is disabled at `>= SAMPLE_MAX` (20); per-row
clear is disabled at `<= 1`, keeping a minimum of one visible row (**confirmed**).

### Caps in the UI

Sample cap is 20 via `SAMPLE_MAX` and the add-row `disabled` guard. Timepoint cap is 10,
read from the v3 definition's `rows.max` into `max`, driving both the
`{rows.length} of {max} timepoint(s)` caption and the Add-Timepoint `disabled={rows.length
>= max}` guard, with `removeRow` bounded by `min`. No separate hard-coded caps were
introduced (**confirmed**).

### Computed values and C2 blank-guard

`jassay_N`, `kfrac_N`, and `unit_N` are read directly from
`computed.rows?.[group.key]?.[rowIndex]` and formatted via `assay2dp` (a `displayValue`
wrapper) / `computedCell`; no assay math is recomputed in the UI. C2 is the only UI
arithmetic — `unitVal - jassayVal`, computed only when both are numbers, else `null`
rendered as an em-dash — matching the design's blank-guard and the no-prior-carry first
timepoint (**confirmed**).

### Accessibility and edit-lock gating

Column headers use `th scope="col"`; the appended action column carries an `sr-only`
"Actions" label. The clear and add buttons carry descriptive `aria-label`s
(`Clear sample N of timepoint M`, `Add sample row to timepoint M`, `Remove timepoint M`).
Every mutating control is wrapped in `canAddRows && editingThisGroup` (where
`canAddRows = editable && max > min`), so nothing is interactive until Edit is clicked
and the TRF status permits (**confirmed**).

### Verification evidence

verification.md records the parity-test command and `7 passed in 0.20s`, the v3 DRAFT
API verification summary (all PASS, left as DRAFT), and the frontend `npm run build`
result (zero TS errors, `✓ built in 3.89s`, only the pre-existing vite chunk-size
advisory). ESLint is noted as not installed (pre-existing), explicitly flagged as not a
failure. All Part-C evidence required by the task is present and passing (**confirmed**).

### Unrelated bundled change

`a9_sodium_metabisulfite.py` (new seed module) and its registration in
`template_definitions/__init__.py` are present in the working tree but have nothing to do
with TPL-A6A-0005. They do not touch the engine, the A6A definition, or the frontend
gating, so they are non-blocking for this review — but they should travel in their own
task/commit rather than riding along here (**confirmed**).

</details>

<details>
<summary>File map</summary>

- `backend-v2/scripts/template_definitions/a6a_leuprolide_microsphere.py` — `_SAMPLES = 20`, `_TIMEPOINTS_MAX = 10`; sample loops + stats widened to 20, `weights.rows.max = _SAMPLES`.
- `backend-v2/scripts/update_a6a5_v3_definition.py` — one-shot branch→PUT→verify script that creates the v3 DRAFT (new file).
- `frontend-react/src/features/test-templates/components/WorksheetForm.tsx` — 20-sample reveal/clear + visible-count state in the gated `renderCumulativeVertical` block.
- `backend-v2/scripts/template_definitions/a9_sodium_metabisulfite.py` + `__init__.py` — unrelated A9 template (out of scope, non-blocking).

Full diff: `git -C d:\RD-instance\GIT diff HEAD`.

</details>
