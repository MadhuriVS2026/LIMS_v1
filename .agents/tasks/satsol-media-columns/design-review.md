# Design Review — "STD Area in Media" dynamic media columns (TPL-A3-0001 v1)

Reviewed document: `d:\RD-instance\GIT\.agents\tasks\satsol-media-columns\design.md`
Reviewer: design-review subagent (fresh context; all load-bearing claims independently verified against live source and both DBs).

Scope under review (confirmed with the user, NOT re-litigated here): make the MEDIA
columns of the "STD Area in Media" table on TPL-A3-0001 v1 a dynamic add/edit/delete
set, with per-worksheet editable headings via the existing `labelFrom` mechanism
(Option 1: a Media Name input row). This review judges only whether the design
implements those confirmed decisions correctly and unambiguously.

---

## Verdict inputs

- HIGH findings: 0
- MEDIUM findings: 1 (Finding 1)
- NIT findings: 2 (Findings 2, 3)

Mechanical gate: 1 MEDIUM ⇒ **CHANGES_REQUESTED**.

---

## Findings

### Finding 1 — MEDIUM — `hiddenColumns` is never persisted, so the "default-six via a seeded `hiddenColumns`" mechanism re-hides populated columns on every reload, and the design mischaracterizes this behavior

**Where:** Decision 1 ("Default-visible set via an initial `hiddenColumns` seed"),
and the "Summary of files touched" frontend change (3).

**Problem.** The design produces the default-six view by **seeding** the
per-worksheet `hiddenColumns` React state with `std_areas.media_7 … media_10` on
mount for TPL-A3-0001. I verified in `WorksheetForm.tsx` that `hiddenColumns` is
pure in-memory UI state (`const [hiddenColumns, setHiddenColumns] =
useState<Set<string>>(new Set())`, line 200), is **never persisted** to
`group_values` and is **never restored** from the worksheet on reopen — it is
reset on every mount. It is written only by `deleteColumn`/`addColumn` within a
single session.

Consequence: if an analyst uses "Add Column" to reveal `media_7` and enters real
STD areas into it, then closes and reopens the worksheet, the proposed on-mount
seed will **re-hide `media_7 … media_10` again**. The entered data is not lost
(it lives in `group_values` and the engine still aggregates it into
`stats.mean_m7`, the footer, etc.), but the **column disappears from the rendered
table while silently continuing to affect the calculation**. In a GxP worksheet, a
column that contributes to a reportable but is invisible on reload (until the
analyst happens to click "Add Column" the right number of times) is a real
correctness/traceability hazard, not a cosmetic one.

The design explicitly asserts the opposite and is wrong on this point:
> "a worksheet the analyst later grows to ten columns simply carries fewer entries
> in `hiddenColumns`, exactly like the existing feature."

`hiddenColumns` carries **nothing** across a reload — it always re-initializes. And
it is **not** "exactly like the existing feature": TPL-A6A-0004 starts with an
**empty** `hiddenColumns` (every provisioned column visible by default) and only
hides on an explicit in-session delete; it never *seeds* hidden columns on mount,
so it never has a reopen-re-hides problem. The seeded-hidden approach is novel and
the design's equivalence claim does not hold.

**Concrete fix (pick one and specify it in the design):**

- (a) **Derive the hidden set from stored data, not a fixed template seed.** On
  mount, hide a trailing `media_N` only if **every** stored `std_areas` cell for
  that column is blank/absent. Seed:
  ```ts
  const initialHidden = () => {
    const s = new Set<string>();
    if (detail.worksheet.template_code !== 'TPL-A3-0001') return s;
    const rows = detail.worksheet.group_values?.std_areas ?? [];
    for (let n = 10; n >= 2; n--) {               // never hide media_1
      const key = `media_${n}`;
      const anyData = rows.some((r) => r?.[key] != null && r[key] !== '');
      const higherVisible = [...Array(10 - n)].some((_, k) => {
        const hk = `media_${n + 1 + k}`;
        return rows.some((r) => r?.[hk] != null && r[hk] !== '');
      });
      if (!anyData && !higherVisible) s.add(`std_areas.${key}`); // trailing suffix only
    }
    return s;
  };
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(initialHidden);
  ```
  A fresh worksheet (all `media_2..10` blank) hides `media_7..10`? No — this hides
  **all** blank trailing columns, i.e. `media_2..10`, giving a default of one
  column. That is not the required default of six. So (a) alone does not satisfy
  "six visible by default." Use (b) or (c).

- (b) **Combine a per-worksheet persisted visible-count with a default of six.**
  Persist the visible media-column count (or the `hiddenColumns` set itself) into
  `group_values` (e.g. a small `_ui` key, or reuse the seeded `std_areas` row
  shape) so reopen restores exactly what the analyst last saw; default to six when
  absent. This is the only option that makes "grows to ten … carries fewer
  entries" literally true, but it adds a persisted-UI-state concept the current
  feature does not have — call that out explicitly as added scope.

- (c) **Keep the fixed seed of `{media_7..media_10}` for the DEFAULT (unsaved)
  case only, and on reopen union it with "reveal any column that has stored
  data."** i.e. start from `{media_7..media_10}` then **remove** from the hidden
  set every `media_N` that has at least one non-blank stored cell (and every
  column below it, to keep a trailing suffix). This keeps the six-column default
  for new worksheets AND never hides a populated column on reload, with no new
  persisted state:
  ```ts
  const initialHidden = () => {
    const s = new Set<string>();
    if (detail.worksheet.template_code !== 'TPL-A3-0001') return s;
    for (let n = 7; n <= 10; n++) s.add(`std_areas.media_${n}`);
    const rows = detail.worksheet.group_values?.std_areas ?? [];
    let highestWithData = 6;
    for (let n = 7; n <= 10; n++) {
      if (rows.some((r) => r?.[`media_${n}`] != null && r[`media_${n}`] !== '')) {
        highestWithData = n;
      }
    }
    for (let n = 7; n <= highestWithData; n++) s.delete(`std_areas.media_${n}`);
    return s;
  };
  ```
  Recommended: (c) — it preserves the confirmed "six by default, rest via Add
  Column" UX for new worksheets and eliminates the reopen-re-hides hazard for
  saved ones, without introducing persisted UI state.

Whichever option is chosen, the design must stop claiming the current naive seed
behaves "exactly like the existing feature," and the Edge-cases / Testability
sections must add a **reopen-after-adding-a-column** case asserting the added
column stays visible on reload.

---

### Finding 2 — NIT — the `hiddenColumns` seed is mandated but its implementation site/initializer is left to the implementer

**Where:** Decision 1 ("a lazy initial value for the `hiddenColumns` state, gated
to TPL-A3-0001") and files-touched summary (3).

**Problem.** The design names the mechanism ("seed the initial `hiddenColumns`
state") but gives no initializer snippet and no statement of where it goes. I
verified `detail.worksheet.template_code` is in scope at the `useState` call site
(it is already read at line 181 for `allowClearColumn`, before the `hiddenColumns`
`useState` at line 200), so a lazy initializer is feasible. This is only a
completeness gap, but since the exact seed logic is the crux of Finding 1, the
design should pin it down rather than defer it.

**Concrete fix.** Specify the lazy initializer explicitly (the Finding-1 (c)
snippet is a suitable drop-in) rather than describing it in prose. State that it
replaces `useState<Set<string>>(new Set())` at the existing `hiddenColumns`
declaration.

---

### Finding 3 — NIT — worktree-vs-live split for source edits is not reconciled against the live-DB edit of Decision 5

**Where:** "Summary of files touched" (frontend path shown as
`frontend-react/src/.../WorksheetForm.tsx`) vs Decision 5 (DB edit targets the
live `d:\RD-instance\GIT\backend-v2\lims.db`).

**Problem.** All source verification in the design (and in this review) was done
against the **worktree** copy
(`.worktrees\satsol-media-columns\backend-v2\...`, `...\frontend-react\...`),
which is correct for a worktree-based change that will be merged. But Decision 5
edits the **live** (non-worktree) DB directly, and the files-touched summary lists
the frontend file by its **live** path. The design never states the obvious-but-
unwritten reconciliation: source edits (frontend + tests) land in the **worktree**
and merge normally, while the DB data edit is applied to the **live** DB (because
that is the running app's DB, per `DATABASE_URL=sqlite+aiosqlite:///./lims.db`,
which I confirmed). A reader could reasonably misread the summary as "edit the
live checkout's source directly."

**Concrete fix.** Add one sentence to the files-touched summary: "Source changes
(frontend + tests) are made in the worktree checkout and merged; only the DB
*data* edit (Decision 5) is applied directly to the live
`backend-v2\lims.db`." No behavioral change.

---

## Verified Assumptions (independently confirmed against source / DB this review)

1. **DB ground truth — definition shape.** Both the live `backend-v2\lims.db` and
   the worktree `.worktrees\satsol-media-columns\backend-v2\lims.db` hold
   TPL-A3-0001 (id 3, v1) with `length(definition) = 4177`, a single `std_areas`
   table field `area` (kind `area`) labelled "Standard Replicate Injections",
   `stats` = `mean_std/sd_std/rsd_std` over `std_areas.area`,
   `samples.solubility = area / stats.mean_std * …`, criteria `sst_std_rsd`
   (blocking, target `stats.rsd_std`) and `prep_agreement` (advisory, target
   `rsd(samples.solubility)`). Markers `labelFrom`/`Media Name`/`STD Area in
   Media`/`media_` are **absent**; `Standard Replicate Injections` **present**.
   **The design correctly reads the DB and does NOT assume the seed — and it
   explicitly builds the media table from scratch.** The design's "Correction to
   the task premise" (the live DB does NOT already contain the media table) is
   accurate. **Mandated point 1 satisfied.**

2. **Live worksheet 53 contents.** Live worksheet 53 (InProgress) `group_values`
   has keys `standard`, `std_areas`, `stats`, `samples`; `std_areas` is exactly
   `[{"area":null}×5]` (all blank, old single-`area` shape). The worktree DB's
   worksheet 53 is `{}` (empty). The design's corrected description of both DBs is
   accurate, and its migration (replace only `std_areas`, copy
   `standard/stats/samples` through, abort only if a `std_areas.area` cell is
   non-null) is safe given the all-null cells. **Mandated point 5 data basis
   confirmed.**

3. **`DATABASE_URL`.** `backend-v2\.env` sets
   `DATABASE_URL=sqlite+aiosqlite:///./lims.db` (relative). Decision 5's claim that
   the live `backend-v2\lims.db` is the DB the running app opens is correct.
   Mandated timestamped `lims.db.bak-*` backup before any write is present and
   non-negotiable in the design. **Mandated point 5 satisfied.**

4. **Positional footer renderer.** `renderGroupFooter` builds
   `valueColumns = visibleFields.slice(1)` and renders `valueColumns.map((field,
   c) => { const cell = row.cells[c]; … })`; `groupFooterRows` builds each row's
   `cells` positionally (labeled item + following unlabeled items in order). So
   footer column `c` is a positional index into the footer refs, NOT a field-keyed
   lookup. Deleting a MIDDLE column misaligns; deleting the TRAILING column drops
   both the last `valueColumns` slot and the last footer-cell slot together,
   preserving alignment. The design's HIGH-finding analysis and the trailing-only
   fix are **correct**. **Mandated point 2 satisfied.**

5. **Add/delete-column persistence model.** `hiddenColumns` is per-worksheet UI
   state; `deleteColumn` blanks values + hides, `addColumn` restores the first
   still-hidden `deletableColumns` entry; `deletableColumns = fields.filter(f =>
   !f.hidden && isEditableField(f))`. The column SET is NOT stored in the template
   definition. The design's Decision 3 (per-worksheet, consistent with
   c436559's model) is correct. The design's rejection of the `hidden:true`
   definition shortcut (because `deletableColumns` filters `!f.hidden`, making such
   columns un-restorable) is correct. **Mandated point 3 satisfied.** (The gap is
   only the *reload* behavior of the seeded hidden set — Finding 1 — not the
   persistence location, which is correct.)

6. **`allowClearColumn` gate + trash-icon condition.** Currently
   `allowClearColumn = detail.worksheet.template_code === 'TPL-A6A-0004'` (single
   gate). The trash-icon render condition is exactly
   `allowClearColumn && !calc && isEditableField(field) && editingThisGroup`,
   rendered inside `visibleFields.map(...)` in the table `<thead>`, where
   `visibleFields` (definition-ordered, with hidden columns removed) is in scope —
   so the design's `trailingMediaKey` guard is implementable as written.
   `EDITABLE_KINDS = {'input','area'}`, so both `std_label` (input) and `media_N`
   (area) would otherwise show the icon, confirming the guard is required.

7. **Engine functions.** `_f_count = float(len(_numeric(args)))` — always a number
   (0.0 for an all-blank column), never EMPTY. `_f_mean` → EMPTY on empty;
   `_f_sd`/`_f_rsd` → EMPTY for `len(nums) < 2`; `_f_rsd` → EMPTY when mean==0.
   `coalesce` exists. All as the design states.

8. **Criteria path.** `Operator.GTE = "gte"` exists; `CriterionDef.parse` requires
   `limit` (accepts a scalar, e.g. `"limit": 1`), defaults `severity` to
   `blocking`. `_evaluate_criteria` computes `observed = evaluate(target, scope)`;
   `_assess` returns `value >= limit[0]` for GTE (and `None` only when observed is
   EMPTY/None/non-numeric). `is_blocking_failure = severity is BLOCKING and passed
   is False`. So `media1_present: count(std_areas.media_1) gte 1` blocks on an
   all-blank `media_1` (observed 0.0 → passed False → blocking) and passes once ≥1
   cell is numeric. **Verified by running it (see 12 below). Mandated point 4
   enforcement confirmed.**

9. **`FieldDef.parse` and TS `FieldDef`.** Python `FieldDef.parse` reads `required`
   and silently ignores unknown keys (`labelFrom` is UI-only, safe for the engine).
   TS `FieldDef` has `labelFrom?`, `hidden?`, `overridable?`; TS `RowSpec` has only
   `min/max/default/labelFrom`. Confirms the design's retraction of `rows.seed`
   (no `seed` key exists in either Python `RowSpec` or TS `RowSpec`) and its
   reliance on field-level `labelFrom` + `hidden`.

10. **`labelFrom` resolution.** `resolveLabelFrom` parses
    `/^([A-Za-z_]\w*)\.([A-Za-z_]\w*)(?:\[(\d+)\])?$/` and reads
    `computed.rows?.[g]?.[idx]?.[f]` else `values[g]?.[idx]?.[f]`, trims, returns
    null when blank. `media_names.media_1[0]` → row 0, field `media_1`. `headerText`
    falls back to `field.label` when `resolveLabelFrom` is null. `seedValues`
    materializes a one-row array for the `media_names` singleton even with no
    stored value, so `[0]` resolves. The design's Option-1 heading mechanism is
    sound.

11. **Parity test source.** `TestA3SaturationSolubility` in
    `backend-v2\tests\calculation\test_seeded_template_parity.py` builds its
    evaluator from `SEED_TEMPLATES` (`BY_CODE[code].definition`), NOT from the DB,
    feeding `std_areas:[{area:50000},{area:50000}]` and asserting `conc_ppm==1000`,
    `solubility==5.0`, reportable `==5.0`. A **DB-only** edit therefore leaves this
    test green. `test_every_template_parses_and_runs_empty` iterates `SEED_TEMPLATES`
    too, so the DB-added `media1_present` blocking criterion does not trip it. The
    design's "parity stays green / seed-rewrite backlogged" claim is correct.
    **Mandated point 4 parity basis confirmed.**

12. **End-to-end run of the full proposed 10-column definition.** I built the
    complete generified definition (10 `media_names` cells, 10 `std_areas` area
    fields with field-level `labelFrom`, 10 `stats` trios, the 30-ref
    column-aligned footer, `samples.solubility` divided by `stats.mean_m1`,
    `sst_std_rsd` on `stats.rsd_m1`, and `media1_present`) and ran it through the
    worktree `TemplateDefinition.parse` + `WorksheetEvaluator`:
    - Parses: 5 groups, 3 criteria, `resultRef = samples.mean_solubility`.
    - `area_field_refs` = the ten `('std_areas','media_1..10')` pairs + `('samples','area')`.
    - Screenshot parity on `media_1` (1264265/1266600/1267571/1267739/1266671):
      `mean_m1 = 1266569.2`, `sd_m1 = 1386.78`, `rsd_m1 = 0.109` → rounds to
      Mean 1266569, SD 1386.78, %RSD 0.11. Matches the screenshot.
    - Empty worksheet: `media1_present` observed 0.0, passed False,
      is_blocking_failure True, `has_blocking_failure True`, reportable EMPTY.
    - Populated `media_1`: `media1_present` observed 5.0 (count of numeric cells),
      passed True, not blocking.
    - Blank trailing column `media_6`: `mean_m6` = EMPTY (per-column independence +
      blank tolerance).
    (Temporary verification scripts were removed after the run.)

---

## Unverified / Wrong Assumptions

1. **WRONG (basis of Finding 1): "a worksheet the analyst later grows to ten
   columns simply carries fewer entries in `hiddenColumns`, exactly like the
   existing feature."** `hiddenColumns` is non-persisted in-memory state, reset to
   a fresh value on every mount. It carries nothing across a reload, and the
   seeded-hidden-on-mount approach is NOT equivalent to the existing TPL-A6A-0004
   feature (which starts with an empty hidden set). See Finding 1.

2. **NOT INDEPENDENTLY VERIFIED (frontend behavior not executed): the exact render
   of the trailing-only delete guard and the default-six column render.** The guard
   logic is sound by inspection (the render condition, `visibleFields` ordering,
   `EDITABLE_KINDS`, `deletableColumns`, `addColumn`/`hiddenCountFor` were all read
   and are consistent with the design), but no React component test was executed in
   this review — the frontend behavior is confirmed only by static reading, not by
   running the UI. The design itself defers this to a committed frontend component
   test, which is appropriate; flagged here only so the implementer runs that test
   rather than treating the UI path as execution-verified.

3. **NOT VERIFIED (out of scope, correctly deferred by the design): the eventual
   rewrite of the seed `TestA3SaturationSolubility` to the media shape and the
   folding of this DB edit into `scripts/template_definitions` (`a2_a3_content.py`).**
   The design backlogs this and relies on new unit tests built from the definition
   object for new-shape coverage; I confirmed the new-shape behavior runs green
   (item 12) but did not verify the seed-capture work, which the design explicitly
   places out of scope.

---

## Conclusion

The design correctly and verifiably resolves all five mandated points: it reads the
actual DB definition (not the stale seed) and builds from scratch; the Mean/SD/%RSD
footer stays correct under add/delete via the verified positional-footer +
trailing-only-delete analysis; the media-column set is per-worksheet UI state
consistent with commit c436559; the calculation engine needs no change and the
parity test (SEED_TEMPLATES-sourced) stays green; and the live DB is correctly
identified with a mandated timestamped backup. The screenshot numbers reproduce
exactly, and the `media1_present` blocking criterion works as claimed.

The one blocking issue is Finding 1: the "default-six via a seeded `hiddenColumns`"
mechanism re-hides populated media columns on every reload because `hiddenColumns`
is non-persistent, and the design asserts the opposite. Fix the seed to reveal any
column that has stored data (recommended option c) and correct the design's
equivalence claim. Findings 2 and 3 are NITs that tighten the frontend spec and the
worktree/live reconciliation.

**Verdict: CHANGES_REQUESTED** (0 HIGH, 1 MEDIUM, 2 NIT).
