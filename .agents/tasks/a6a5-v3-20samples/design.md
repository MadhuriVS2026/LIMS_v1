# Design / Trace — TPL-A6A-0005 v3: extend 6 → 20 sample slots + 20-sample UI

Template: **TPL-A6A-0005** "Dissolution-Leuprolide-microsphere" (archetype A6a).
Live: **Active v2**, template **id 41**, `resultRef = timepoints_release.mean`.

Goal (two coordinated parts, this step is design/trace ONLY — no code written):

- **Part A (backend definition):** branch a new **v3 DRAFT** of id 41 and replace its
  definition with the 20-slot form — `weights` table `rows.max` 6 → 20, and the
  `timepoints_release` sequence's per-sample field families (`area_N`, `jassay_N`,
  `kfrac_N`, `unit_N`) extended from N=1..6 to N=1..20, with the four stats fields
  re-aggregated over `unit_1..unit_20`. Everything else unchanged. v3 stays DRAFT
  (NOT approved).
- **Part B (frontend):** extend the existing TPL-A6A-0005 custom render of
  `timepoints_release` in `WorksheetForm.tsx` to support up to 20 sample rows
  (filled-only + Add-row + per-row clear) and the timepoint-block Add/Delete/Edit/Save
  controls, all reusing existing mechanisms.

---

## 0. Grounding — what the code actually shows

Read before writing this document:

- Seed module `backend-v2/scripts/template_definitions/a6a_leuprolide_microsphere.py`
  — the v2 definition builder. `_UNITS = 6`. The per-N field families are built in
  four contiguous loops over `range(1, _UNITS + 1)`; stats aggregate a bracket list
  `[unit_1, ..., unit_6]`.
- Parity test `backend-v2/tests/calculation/test_a6a_0005_leuprolide_parity.py` —
  pins the gold values by evaluating `A6A_LEUP_DEFINITION` directly (DB-independent).
- Frontend `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
  — the `renderCumulativeVertical(group)` block (gated by
  `allowCumulativeVertical = template_code === 'TPL-A6A-0005'` AND
  `group.key === 'timepoints_release'`), plus the shared `addRow` / `removeRow` /
  `setCell` / `saveGroup` / `clearGroup` / `renderGroupToolbar` helpers.
- API endpoints `backend-v2/src/api/v1/endpoints/test_template_endpoints.py` and
  `auth_endpoints.py`; service `test_template_service.py`.

### Discrepancies found and decisions (recorded, not silently resolved)

1. **Timepoint cap.** The task says "timepoints max 10", but the LIVE v2 definition
   has `timepoints_release.rows.max = 25` (7 real labels + 18 spare blocks, a faithful
   copy of the 25-block sheet). **Decision: lower `rows.max` to 10** to satisfy the
   explicit cap in the original user request (message 12: "timepoint 10 and sample 20
   lines limit"). Keep `min 1`, `default 7`, `labelFrom time_hr`. This is the one
   intentional change beyond the sample extension; it is safe because only 7 blocks
   were ever labelled/used and lowering the max cannot drop stored data for the 3-block
   parity fixture. If the reviewer prefers preserving 25, that is a one-line revert —
   flagged here so it is a conscious choice, not an accident.
2. **Weights cap.** Task says extend `weights` to `rows.max = 20` (keep `min 1`,
   `default 6`, `labelFrom 'unit_label'`). The v2 module uses `_UNITS` (=6) for
   `weights.rows.max` AND `default`. **Decision:** set `weights.rows.max = 20` but keep
   `default = 6` (do NOT tie default to the new max). The weights index drives
   `jassay_N` via `weights.weight[N - 1]`, so 20 weight slots must exist for `area_20`
   to resolve its pellet weight.
3. **`_UNITS` constant.** v2 ties `weights.rows.max`, `weights.default`, and all four
   per-N loops + the stats bracket list to the single `_UNITS = 6`. **Decision:**
   introduce a separate `_SAMPLES = 20` for the sample families and the stats list, and
   set `weights.rows.max = _SAMPLES` while keeping `weights.rows.default = 6`. This
   keeps the extension a one-constant change and byte-faithful to the existing loop
   shapes.

---

## (a) Exact per-N field templates (N and the N-1 weights index substituted)

The four families are produced by the same four loops the v2 module already uses; we
only widen the range to `1..20`. Field ORDER is preserved: all `area_N` first, then all
`jassay_N`, then all `kfrac_N`, then all `unit_N`, then the four stats fields. The
`weights` index is **N-1** (0-based), so `area_7` reads `weights.weight[6]` and
`area_20` reads `weights.weight[19]`.

### area_N (editable instrument input)

```python
{"key": f"area_{N}", "kind": "area", "label": f"Sample Area {N}"}
```

- N=7:  `{"key": "area_7",  "kind": "area", "label": "Sample Area 7"}`
- N=20: `{"key": "area_20", "kind": "area", "label": "Sample Area 20"}`

### jassay_N (calculated, hidden — raw %Assay J-column)

Produced by `_jassay_expression(N)` — identical operator chain to v2, with `N`
substituted and the weights index `[N - 1]`:

```
area_N / std_stats.mean_std
 * standard.weight_mg / standard.dilution_1
 * standard.volume_1 / standard.dilution_2
 * prep.vf_vol / prep.pipette_vol
 * prep.media_vol / weights.weight[N - 1]
 * standard.potency
 * standard.mw_base / standard.mw_salt
 * prep.avg_weight / prep.label_claim
```

- **N=7** (`weights.weight[7 - 1]`):
  ```python
  {"key": "jassay_7", "kind": "calculated", "hidden": True,
   "expression": "area_7 / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.weight[7 - 1] * standard.potency * standard.mw_base / standard.mw_salt * prep.avg_weight / prep.label_claim"}
  ```
- **N=20** (`weights.weight[20 - 1]`):
  ```python
  {"key": "jassay_20", "kind": "calculated", "hidden": True,
   "expression": "area_20 / std_stats.mean_std * standard.weight_mg / standard.dilution_1 * standard.volume_1 / standard.dilution_2 * prep.vf_vol / prep.pipette_vol * prep.media_vol / weights.weight[20 - 1] * standard.potency * standard.mw_base / standard.mw_salt * prep.avg_weight / prep.label_claim"}
  ```

> Note: the module builds `weights.weight[{u} - 1]` as a literal string (the `- 1` is
> left in the expression text, as in v2), so the byte-faithful form keeps `[7 - 1]`,
> `[20 - 1]`, etc. — do NOT pre-compute to `[6]`/`[19]`; match the existing module text.

### kfrac_N (calculated, hidden — replace fraction K = J·A37/A35)

```python
{"key": f"kfrac_{N}", "kind": "calculated", "hidden": True,
 "expression": f"jassay_{N} * prep.withdraw_replace / prep.media_vol"}
```

- N=7:  `"expression": "jassay_7 * prep.withdraw_replace / prep.media_vol"`
- N=20: `"expression": "jassay_20 * prep.withdraw_replace / prep.media_vol"`

### unit_N (calculated, reported — Cumulative %Release C = J + Σ K[1..b-1], unit %)

```python
{"key": f"unit_{N}", "kind": "calculated", "label": f"Unit-{N}", "unit": "%",
 "expression": f"jassay_{N} + sum(prior.kfrac_{N})"}
```

- N=7:  `{"key": "unit_7",  "label": "Unit-7",  "unit": "%", "expression": "jassay_7 + sum(prior.kfrac_7)"}`
- N=20: `{"key": "unit_20", "label": "Unit-20", "unit": "%", "expression": "jassay_20 + sum(prior.kfrac_20)"}`

`sum(prior.kfrac_N)` is the non-recursive cumulative-carry form; on the first timepoint
row the prior range is empty so `sum = 0` and `unit_N = jassay_N` (= sheet C40). This is
the proven form (see module docstring, TPL-A6A-0004 precedent) and MUST be kept — the
recursive `prev.carry` form has no ordering edge and silently collapses to 0.

---

## (b) Extended stats expressions over unit_1..unit_20

Build the bracket list once:

```python
ul = "[" + ", ".join(f"unit_{u}" for u in range(1, _SAMPLES + 1)) + "]"
#   = "[unit_1, unit_2, unit_3, ..., unit_19, unit_20]"
```

Then the four stats fields (rounding/units unchanged from v2 — the v2 stats carry no
`rounding` key; they are plain `calculated` with `unit "%"`, so keep them plain unless
the reviewer wants `round/1dp` added. The task text mentions "rounding round/1dp"; the
v2 module does NOT set rounding on these fields. **Decision: keep byte-faithful to v2 —
NO rounding key** — matching the live definition and the parity test, which asserts full
precision. Flagged so it is a conscious choice):

```python
{"key": "mean",    "kind": "calculated", "label": "Mean", "unit": "%",
 "expression": f"mean({ul})"}
{"key": "min_val", "kind": "calculated", "label": "Min",  "unit": "%",
 "expression": f"min({ul})"}
{"key": "max_val", "kind": "calculated", "label": "Max",  "unit": "%",
 "expression": f"max({ul})"}
{"key": "rsd",     "kind": "calculated", "label": "%RSD", "unit": "%",
 "expression": f"sd({ul}) * 100 / mean"}
```

Fully expanded for 20 samples:

```
mean    = mean([unit_1, unit_2, ..., unit_20])
min_val = min([unit_1, unit_2, ..., unit_20])
max_val = max([unit_1, unit_2, ..., unit_20])
rsd     = sd([unit_1, unit_2, ..., unit_20]) * 100 / mean
```

`time_hr`, `resultRef (timepoints_release.mean)`, the cumulation model, and all other
groups/fields are unchanged.

---

## (c) Parity values to verify, and how they are proved

Gold values (unchanged by the extension — samples 7..20 are blank in the fixture, so
`mean/min/max/rsd` over the three filled units are identical whether the list is length
6 or length 20; `mean([x,y,z,blank,...])` ignores blanks, as the engine's blank-tolerant
aggregates already do in v2). The existing parity test asserts:

**1 Hr block (areas 203438 / 231282 / 174411 → Units 1/2/3):**
- jassay_1/2/3 ≈ 15.00 / 16.58 / 12.70 (2dp view of `jassay_N`)
- kfrac_1/2/3 (C1) ≈ 0.30 / 0.33 / 0.25
- unit_1 = 14.996084937889453 (= C40, no carry → `unit_1 == jassay_1`)
- unit_2 = 16.579857409503386
- unit_3 = 12.701419313269414
- mean = 14.759120553554084, min = 12.701419313269414,
  max = 16.579857409503386, rsd = 13.212490048191508

**24 Hr block (area_1 = 681560):**
- jassay_1 ≈ 50.24 (full: J46 = 50.240032), kfrac_1 (C1) ≈ 1.00
- unit_1 (C46) = 50.53995379830622 — the first cumulative add-back (L46 = K40)

**48 Hr block (area_1 = 1013055):**
- jassay_1 ≈ 74.68 (J52), unit_1 (C52) = 75.98034256289799 — running carry
  (L52 = K46 + L46)

The task prompt's "24 Hr: jassay 50.24/54.60/42.91, kfrac 1.00/1.09/0.86, C2
0.30/0.33/0.25" describe the full 3-unit 24 Hr row and the UI-derived **C2 = unit_N −
jassay_N** carry-over column; these are display values (C2 is a frontend-only
subtraction, see Part B) and are not separate backend assertions beyond the unit/jassay
numbers already pinned.

**How it is proved:**
1. The existing parity test imports `A6A_LEUP_DEFINITION` directly and evaluates it with
   the sheet inputs. Because the per-N extension only ADDS blank slots 7..20 and widens
   the stats bracket list (blank-tolerant aggregates), **every existing assertion must
   still pass byte-for-byte after the extension**. Run:
   ```
   cd backend-v2
   python -m pytest tests/calculation/test_a6a_0005_leuprolide_parity.py -q
   ```
   Expected: all tests pass (no value drift). This is the authoritative proof for the
   module/definition.
2. The v3 definition pushed to the DB must be byte-identical to the module's
   `A6A_LEUP_DEFINITION` (the Part-A script serialises the same builder output), so the
   module parity test also certifies the DB draft. The script additionally prints a
   verification summary (see Part A): field counts (`area_*`=20, `jassay_*`=20,
   `kfrac_*`=20, `unit_*`=20), `weights.rows.max == 20`,
   `timepoints_release.rows.max == 10`, and the stats expressions, read back from the
   stored draft via `GET /test-templates/{v3_id}`.

---

## (d) Part B — precise frontend edit plan (WorksheetForm.tsx)

All edits are confined to the existing `renderCumulativeVertical` block and a small
amount of component state. Gating stays strict: the block is only reached when
`allowCumulativeVertical` (`template_code === 'TPL-A6A-0005'`) AND
`group.key === 'timepoints_release'`. No other render path changes.

Reused existing mechanisms (confirmed present):
- `renderInput(group, rowIndex, field)` — editable input for `area_N` (disabled unless
  `isGroupEditing(group.key)`).
- `computedCell(group, rowIndex, field)` — read-only computed cells for `unit_N` and the
  stats (rounding/blank handling from the engine).
- `computed.rows?.[group.key]?.[rowIndex]?.[key]` — hidden `jassay_N` / `kfrac_N` /
  `unit_N` values; `assay2dp(...)` formats them to 2dp.
- C2 blank-guard: `const carryOver = typeof unitVal === 'number' && typeof jassayVal === 'number' ? unitVal - jassayVal : null;` then `assay2dp(carryOver)` — **UI-only arithmetic, keep as-is.**
- Timepoint block add/delete/edit/save: `addRow(group)`, `removeRow(group, rowIndex)`,
  `renderGroupToolbar(group)` (Edit→`startEditGroup`, Save→`saveGroup`,
  Delete→`clearGroup`), `isGroupEditing`. **Reuse — no parallel persistence path.**
- Row-level clear of a slot = set `area_N` to `null` via the existing `setCell(group.key,
  rowIndex, 'area_N', null)`; because `unit_N`/`jassay_N`/`kfrac_N` are computed from
  `area_N`, blanking the area makes those cells drop out exactly like the sheet's blank
  rows. **Reuse `setCell` — no new persistence path.**

Changes to make:

1. **Widen the fixed arrays from 6 to 20.** In `renderCumulativeVertical`, change:
   ```ts
   const areaFields = Array.from({ length: 6 }, (_, i) => fieldByKey(`area_${i + 1}`));
   const unitFields = Array.from({ length: 6 }, (_, i) => fieldByKey(`unit_${i + 1}`));
   ```
   to length **20** (or, better, derive the count from the definition:
   `const SAMPLE_MAX = 20;` or count `area_*` fields in `group.fields`). Keep deriving
   `jassay_N`/`kfrac_N`/`unit_N` by index as today.

2. **Add per-timepoint visible-sample-count state.** Introduce a new component-level
   state keyed by timepoint row index, e.g.
   `const [visibleSamples, setVisibleSamples] = useState<Record<number, number>>({});`
   (near the other `useState` hooks, ~line 190). A helper
   `visibleCountFor(rowIndex)` returns, in order of precedence:
   - an explicit entry in `visibleSamples[rowIndex]` if set; else
   - the number of **filled** slots = highest N (1..20) whose `area_N` is a present
     value in `values[group.key][rowIndex]` (so reopening a saved sheet shows exactly
     the filled rows); clamped to `>= 1` and `<= 20`.
   This replaces "show all 6": the `areaFields.map(...)` body renders only indices
   `u < visibleCountFor(rowIndex)`.

3. **Sample "Add row" control (inner).** Below the per-timepoint sample table, when
   `editingThisGroup && editable`, render a small "Add row" button (icon `pi pi-plus`),
   disabled when `visibleCountFor(rowIndex) >= 20`. onClick increments
   `visibleSamples[rowIndex]` by 1 (revealing the next empty `area_N` slot). No data
   write — the new slot is empty until the analyst types, at which point `setCell`
   fires as usual. Show a "`{count} of 20 sample(s)`" caption like the timepoint
   caption.

4. **Per-sample delete (clear) control.** Add a trailing cell/column to each sample row
   (only when `editingThisGroup && editable`) with a trash `Button`
   (`aria-label={`Clear sample ${u + 1} of timepoint ${rowIndex + 1}`}`). onClick:
   - `setCell(group.key, rowIndex, `area_${u + 1}`, null)` to blank the slot (drops the
     computed cells), AND
   - decrement the visible count for that row (so the row disappears from view),
     re-deriving so remaining filled rows stay visible. Keep a minimum of 1 visible row.
   This mirrors the existing `deleteColumn` intent (blank-so-it-drops-out) but per-cell,
   using the already-present `setCell`.

5. **Timepoint-block controls (outer).** Already present in the block header:
   "Add Timepoint" (`addRow`), per-block trash (`removeRow`), and `renderGroupToolbar`
   (Edit/Save/Delete). The only change is to **respect the 10 cap**: the existing
   `max = group.rows?.max ?? 1` now reads 10 from the v3 definition, so the existing
   `disabled={rows.length >= max}` and the `{rows.length} of {max} timepoint(s)` caption
   become the "max 10" guard automatically — no code change beyond the definition's new
   `rows.max`. Confirm `addRow`/`removeRow` already enforce `max`/`min` (they do:
   `addRow` returns early at `>= max`, `removeRow` at `<= min`).

6. **Accessibility.** Keep the existing `th scope="col"` headers; give the new trash
   buttons `aria-label`s (above); the "Add row"/"Add Timepoint" buttons keep text
   labels. The sample-area inputs already get an `aria-label` from `renderInput`.

7. **Edit-lock gating.** All new controls are wrapped in `editingThisGroup && editable`,
   identical to the existing timepoint add/remove controls, so nothing is interactive
   until the analyst clicks Edit and the TRF status permits.

No change to `seedValues`, `setCell`, `addRow`, `removeRow`, `saveGroup`, `clearGroup`,
`onSave`/`onAutosave`, or any non-TPL-A6A-0005 path.

Frontend verification:
```
cd frontend-react
npm run build        # tsc + vite build must pass with the widened arrays + new state
npx eslint src/features/test-templates/components/WorksheetForm.tsx
```
Expected: type-check/build clean. If a component test for WorksheetForm exists, run it:
```
npx vitest run src/features/test-templates
```

---

## (e) Part A — application plan

**Authoritative path: a new API-driven script** (matching the lifecycle the service
enforces — definitions are only editable while Draft; an Active template must be
branched), NOT the in-place `sqlite3` pattern of `update_a6b_definition.py`. The task
requires a NEW v3 DRAFT; branching is the correct, audited route.

New file: `backend-v2/scripts/update_a6a5_v3_definition.py`. Steps:

1. **Login.** `POST http://127.0.0.1:8443/api/v1/auth/login` with
   `application/x-www-form-urlencoded` body `username=admin&password=admin123`
   (OAuth2PasswordRequestForm). Read `access_token` from the JSON; set
   `Authorization: Bearer <token>` on all subsequent calls.
2. **Resolve id 41.** `GET /api/v1/test-templates/41` — assert `code == TPL-A6A-0005`,
   `status == Active`, `version == 2`. (Also `GET /test-templates/41/versions` to
   confirm no in-flight unapproved version exists; the service rejects a second draft.)
3. **Branch v3 DRAFT.** `POST /api/v1/test-templates/41/new-version`. Response is the new
   Draft (version 3, status Draft); capture its `id` (call it `v3_id`).
4. **Build the extended definition in-process** by importing the updated builder:
   `from scripts.template_definitions.a6a_leuprolide_microsphere import A6A_LEUP_DEFINITION`
   (after the module is edited to `_SAMPLES = 20`, see below), OR build it by
   deep-copying the fetched v2 definition and programmatically appending slots 7..20 +
   widening stats + `weights.rows.max`/`timepoints_release.rows.max`. **Decision: import
   the module builder** so the DB draft and the parity-tested module cannot diverge.
5. **PUT the definition onto the draft.**
   `PUT /api/v1/test-templates/{v3_id}/definition` with body
   `{"definition": <A6A_LEUP_DEFINITION>}`. The service re-validates (parse + dry-run
   evaluate) and stores it. Any schema/eval error surfaces here.
6. **Verify and print.** `GET /api/v1/test-templates/{v3_id}` and assert/print:
   - `version == 3`, `status == Draft` (NOT Active — leave it as a draft),
   - counts: 20 each of `area_*`, `jassay_*`, `kfrac_*`, `unit_*` in
     `timepoints_release.fields`,
   - `weights.rows.max == 20`, `weights.rows.default == 6`,
   - `timepoints_release.rows.max == 10`, `default == 7`, `min == 1`,
   - the four stats expressions contain `unit_20`,
   - `jassay_7` expression contains `weights.weight[7 - 1]` and `jassay_20` contains
     `weights.weight[20 - 1]`.
   Print a concise PASS/FAIL summary. **Do NOT call `/submit` or `/approve`** — v3 must
   remain a DRAFT.

**Seed module + parity test:** **Decision: YES, update the seed module to the 20-slot
form** (change `_UNITS`-driven sample loops/stats to a new `_SAMPLES = 20`, set
`weights.rows.max = _SAMPLES` while keeping `weights.rows.default = 6`, and
`timepoints_release.rows.max = 10`). This keeps the module byte-consistent with the DB
draft (the script imports it) and keeps a single source of truth. The parity test is NOT
edited — its gold assertions must continue to pass unchanged, which is exactly the proof
that the extension is value-neutral (step (c)). If any assertion drifts, the extension is
wrong and must be fixed before the DB is touched.

Implementation order for the coder (each step leaves the tree buildable):
1. Edit the seed module (`_SAMPLES = 20`, widen loops + stats, `weights.rows.max`,
   `timepoints_release.rows.max = 10`). Verify: run the parity test — all pass.
2. Write `scripts/update_a6a5_v3_definition.py`. Verify (requires the backend running on
   8443): run the script; it prints the v3 DRAFT verification summary. If the backend is
   not running, the module parity test still certifies the definition; note the script
   is a one-shot DB mutation to run against the live dev DB.
3. Edit `WorksheetForm.tsx` per Part B. Verify: `npm run build` + eslint clean.

---

## Summary of the locked field list

Per timepoint, the definition carries **N = 1..20** of each of:
- `area_N` — kind `area` (editable), label "Sample Area N".
- `jassay_N` — kind `calculated`, `hidden: true`; `_jassay_expression(N)` with the
  `weights.weight[N - 1]` index.
- `kfrac_N` — kind `calculated`, `hidden: true`; `jassay_N * prep.withdraw_replace /
  prep.media_vol`.
- `unit_N` — kind `calculated`, label "Unit-N", unit "%"; `jassay_N +
  sum(prior.kfrac_N)`.

Plus the four stats fields aggregating `[unit_1 .. unit_20]`: `mean`, `min_val`,
`max_val`, `rsd = sd(...) * 100 / mean`. `weights.rows.max = 20` (default 6),
`timepoints_release.rows.max = 10` (default 7, min 1). `resultRef`, `time_hr`,
cumulation model, and all other groups unchanged.

**Parity approach:** the extension only adds blank slots 7..20 + widens the stats list,
so the unedited parity test (`test_a6a_0005_leuprolide_parity.py`) must pass byte-for-
byte — that is the authoritative proof of value-neutrality for both the module and the
DB draft (the Part-A script PUTs the exact module output). v3 is left as a **DRAFT**.
