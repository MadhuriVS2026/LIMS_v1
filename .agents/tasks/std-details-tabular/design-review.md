# Design Review — Convert singleton "Standard Details" to one-row table

**Design under review:** `d:\RD-instance\GIT\.agents\tasks\std-details-tabular\design.md`
**Reviewed against:** worktree code at `d:\RD-instance\GIT\.worktrees\std-details-tabular\` and the authoritative DB `d:\RD-instance\GIT\backend-v2\lims.db`.
**Verdict:** CHANGES_REQUESTED (1 HIGH, 2 MEDIUM).

The design is unusually thorough and most of its factual claims check out against the real code and DB. The classification, lifecycle, status model, seeding precedent, and frontend-renderer reuse are all verified correct. However, the single most important technical claim — *where* the row-0 collapse is implemented in the calculation engine — is self-contradictory and, as written, would break the entire catalogue. That is the blocking finding. Two further findings concern a seed-helper edit that silently converts an explicitly out-of-scope group.

---

## Findings

### 1. HIGH — The row-0 collapse cannot live in `_resolve`; as described it breaks 816 live aggregate references

**Where:** Section (c), "The general rule (chosen approach)" and "Residual risk and the guard."

**Problem.** The design places the first-element collapse inside `expression.py` `_Evaluator._resolve` (line 407): *"when the dotted walk's final resolved value is a `ColumnSeries` and the reference is a plain `group.field` with no trailing index, return `series[0]`."* It then claims aggregates are unaffected because *"the function receives the `_Ref`'s resolved value and `_flatten`s it ... it passes through unchanged."* These two statements contradict each other.

`_resolve` is the single code path that produces the value an aggregate argument evaluates to. In `_Evaluator._call`, arguments are evaluated with `args = [self.eval(a) for a in node.args]`; for a `_Ref` argument, `self.eval` calls `_resolve(node)`. `_resolve` receives no signal about its caller — it cannot tell `standard.weight_mg` used bare in arithmetic from `std_areas.area` used inside `mean(...)`. Both arrive as a 2-part `_Ref` with no trailing index. If `_resolve` collapses to `series[0]` at end-of-walk, then `mean(std_areas.area)` receives a single scalar, not the series, and returns the mean of one value.

I verified empirically against all 48 Active templates: there are **816** occurrences of a bare, non-indexed `group.field` reference to a multi-row group that is passed *directly into an aggregate* (`mean(std_areas.area)`, `sd(std_areas.area)`, `rsd(pool(std_areas.area, bkt_1.area))`, `mean(samples.pct_assay)`, etc.). Every one of these would collapse to its first element under the stated `_resolve` implementation, corrupting the core statistics of effectively every assay/content/dissolution template. This is the opposite of the design's "no existing result changes" guarantee.

The indexing claim *is* fine — `group.field[0]` consumes the index mid-walk, before any end-of-walk collapse — but the aggregate claim is not, and the design's own unit test (c)(1)(b) ("an aggregate over a two-row group still returns the aggregate of both rows — collapse is bypassed") would **fail** under the implementation the design specifies.

**Concrete fix.** Do not collapse in `_resolve`. Keep `_resolve` returning the full `ColumnSeries` (a `list` subclass) so `_flatten` and every aggregate keep seeing the whole series. Apply the first-element collapse only at the point of *scalar numeric consumption*, where context proves a scalar is wanted and a list is not:

- Collapse inside `_as_number` (expression.py): if the value is a non-empty `ColumnSeries`, coerce `series[0]`; if empty, `EMPTY`. This covers every arithmetic/comparison operand (`_binary`, `_unary`) and rounding, which is exactly where a bare `standard.weight_mg` is used, while aggregates (which call `_numeric`/`_flatten`, not `_as_number`) see the full series untouched.
- Alternatively, make `ColumnSeries` collapse only under arithmetic dunder methods and leave iteration/`_flatten` intact. Either way the collapse site must be scalar-coercion, never the resolver.

Update the prose in (c) to name `_as_number` (not `_resolve`) as the collapse site, and add an explicit unit test that `mean(group.field)` over a two-row group returns the mean of both rows with the collapse in place (this is the test that distinguishes the correct implementation from the broken one).

---

### 2. MEDIUM — Converting the shared `standard_group()` helper also converts the out-of-scope `standard_2` group

**Where:** Section (d)(i) ("Via the shared `standard_group()` helper") and the per-template note in (g) that `standard_2` is "a different section ... out of scope."

**Problem.** `scripts/template_definitions/_common.py` `standard_group(*, key="standard", ...)` (line 208) takes a `key` parameter and returns `{"key": key, "kind": "singleton", ...}`. `a4_a5_related_substances.py` line 77 calls `standard_group(key="standard_2", ...)` to emit the second reference-standard singleton. The design's plan — "Converting the helper to emit `kind:"table"` ... fixes every caller at once" — would therefore flip `standard_2` to a table as well. The design's reassurance that "the helper change still only affects a group keyed `standard`" is factually wrong: the helper has no idea which key it is producing; the `kind` literal it emits is shared by every caller including the `standard_2` one.

Verified in the DB: `TPL-A4-0001`, `TPL-H1-0001`, `TPL-H1-0002` each carry both `standard` (singleton) and `standard_2` (singleton). The DB-driven version-bump driver only flips `key=="standard"`, so it leaves `standard_2` a singleton; the helper edit would make the seed module emit `standard_2` as a table. Module and DB then disagree on `standard_2` for A4-0001 (module-backed), contradicting the stated scope and the design's own invariant that identity/structure outside `standard` is preserved. (H1-0001/0002 are DB-only so have no module, but A4-0001 is module-backed.) The parity suite would only catch this if a fixture evaluates `standard_2`; since there are zero bare refs to it, a naive oracle may not, letting the divergence pass silently.

**Concrete fix.** Make the helper conversion key-aware instead of flipping the shared literal unconditionally. Either:
- Add a `multi_row: bool = False` (or `kind: str = "singleton"`) parameter to `standard_group()` and have the in-scope callers pass it, so `standard_group(key="standard_2", ...)` stays singleton; or
- Keep `standard_group()` emitting singleton and perform the `kind`/`rows` mutation at each in-scope caller site (still one edit per emitting site, but never touching `standard_2`).

Then assert in the parity/DB-diff gate that `standard_2` remains `kind:"singleton"` in A4-0001/H1-0001/H1-0002 after conversion.

---

### 3. MEDIUM — Seed-source attribution for A4-0004 is wrong (listed as "inline", is actually the shared helper via spread)

**Where:** Section (g) roster ("TPL-A4-0004 | ... | `a4_rs_against_standard_rrf_division.py` (drop `renderAsTable`)") and the checklist item 2 which lists `a4_rs_against_standard_rrf_division.py` among "module-local helpers/inline literals."

**Problem.** `a4_rs_against_standard_rrf_division.py` line 249 emits A4-0004's standard as `{**standard_group(label=..., conc_label=...), "renderAsTable": True}` — i.e. it spreads the **shared** `standard_group()` helper and adds `renderAsTable`. It is not an inline literal and not a module-local helper. This matters because it couples A4-0004's conversion to the finding-2 helper edit: if the helper is made key-aware per finding 2's fix, A4-0004 (which uses `key="standard"` by default) is converted by the helper, and the only site-specific edit left is dropping `"renderAsTable": True` from the spread. If instead the helper is left singleton and conversion done per-caller, this site needs the explicit mutation. The design's "inline literal, convert individually" instruction would lead an implementer to hand-build a literal that duplicates the helper, risking drift from the parity-tested helper output.

**Concrete fix.** Reclassify A4-0004 in (g) and checklist item 2 as "shared `standard_group()` via `**`-spread, plus drop `renderAsTable`." Tie its conversion to whatever helper strategy finding 2 adopts; the only A4-0004-specific edit is removing the `renderAsTable` key from the spread, not rebuilding the standard block.

---

### 4. NIT — `rowLabel` is a frontend-only key not parsed by the backend schema; state this explicitly

**Where:** Sections (b) "Rendering controls" and (e); checklist.

**Observation (verified, not a defect).** `RowLabelConfig` in `frontend-react/.../testTemplate.types.ts` (line 314) defines `format: string` with `{n}` as the 1-based row number — the design's `rowLabel: { format: "STD - {n}" }` matches exactly. The backend `RowSpec.parse`/`GroupDef.parse` (`template_schema.py`) parse only `rows`, `labelFrom`, `seed`; they ignore unknown keys, so adding a group-level `rowLabel` passes server validation (it is dropped on parse, not rejected). This is benign but worth stating so the implementer does not expect `rowLabel` to round-trip through the backend parsed model. 

**Concrete fix.** Add one sentence to (b)/(e): "`rowLabel` is a frontend-only presentation hint stored in the raw definition JSON; the backend schema parser ignores it, so it neither validates nor affects evaluation."

---

### 5. NIT — "No `lims.db` in the worktree" is used as rationale but the backend default DB path is not pinned

**Where:** Section (d) "The authoritative DB and the mandatory backup."

**Observation.** Verified: the worktree `backend-v2` has no `lims.db`; the main-repo `d:\RD-instance\GIT\backend-v2\lims.db` exists (54 rows). The design fixes the target DB and mandates the backup — good. But the API-driven route (new-version → PUT → submit → approve) runs against whatever DB the *running backend process* is configured to use (via `.env`/`DATABASE_URL`), and the design leaves "run the backend from the main repo, or copy the live `lims.db` into the worktree backend-v2 ... and copy the mutated DB back" as an either/or without specifying how the backend is pointed at the chosen file. A mismatch here silently bumps versions in the wrong (or a throwaway) DB.

**Concrete fix.** State the exact mechanism the driver uses to guarantee the backend targets the authoritative file — e.g. set `DATABASE_URL=sqlite:///d:/RD-instance/GIT/backend-v2/lims.db` for the backend process and have `_apply_standard_tabular.py` assert, before any write, that `GET /test-templates` returns the expected 54-row/48-Active catalogue (fingerprint the DB) so a wrong-DB run aborts.

---

## Verified Assumptions

1. **Classification flag.** The `kind` key parsed into `GroupKind` (`template_schema.py`): `SINGLETON/TABLE/SEQUENCE`; `GroupDef.is_multi_row` true for table/sequence. Label is not used. **Correct.**
2. **Classification roster.** Running the (a) procedure against the live DB yields exactly **25 singleton / 4 table / 19 no-`standard`-group = 48 Active**, matching the (g) roster code-for-code, including A8-0003 as the single excluded Draft. **Correct.**
3. **Scope exclusions.** A11 uses `key="standard", kind="table"` (step-5 exclusion); A2-0004/A2-0005 likewise table; A6D/A14 have no `standard` group (step-3 exclusion). **Correct.**
4. **Engine modules/functions and line numbers.** `_build_scope` (line 314), `_sheet_scope` (line 390), the multi-row/singleton scope projection (lines 322–327 / 394–399), the `values` mirror (lines 164–168), `_resolve` (line 407), `_flatten` (line 368), the list-index branch (line 417). All **correct**.
5. **values→rows migration.** The mirror at lines 164–168 populates `values["group.field"]` only for non-multi-row groups, so after conversion `values["standard.*"]` is no longer emitted and the numbers live in `rows["standard"][0]`. **Correct**; the parity-diff-by-logical-identity requirement is sound.
6. **No bare multi-row ref today.** Catalogue-wide scan of all 48 Active templates finds **zero** bare (non-aggregated, non-indexed) `group.field` references to any multi-row group. **Correct** — this is what makes the *intended* rule a no-op today (and is exactly why the collapse must not sit in `_resolve`, per finding 1).
7. **No `resultRef` targets `standard`.** Verified across all 25 in-scope templates: none has `resultRef` pointing at the `standard` group, so the `_extract_result` multi-row path change is harmless. **Correct.**
8. **Status model.** `TemplateStatus` has exactly `DRAFT/PENDING_APPROVAL/ACTIVE/INACTIVE`; no `Superseded`. `deactivate()`→Inactive, `approve()` sets Active + `approved_by=actor` + `approved_at`, `mark_superseded_by()` sets the back-link. **Correct.**
9. **Lifecycle on live rows.** TPL-A8-0001 v1(Inactive,→24,seed)/v2(Active,admin); TPL-A6A-0005 v1/v2(Inactive,→44)/v3(Active,admin); TPL-A4-0002 v1/v2 raw-string `Superseded`/v3 Active all `seed`; only 2 `Superseded`-string rows exist, both A4-0002. `approved_by` distribution: 47 seed / 5 admin / 2 null. **All correct.**
10. **Service supersede logic.** `TestTemplateService.approve` calls `_supersede_prior_versions`, which `deactivate()`s and `mark_superseded_by()`s each older version. **Correct.**
11. **Seeding precedent.** `scripts/update_a6a5_v3_definition.py` exists and does exactly new-version(idempotent reuse of an existing Draft) → PUT definition (server re-validates) → leaves Draft. **Correct**; the design's extension to also submit+approve as `admin` is a reasonable, explicitly-noted addition.
12. **NaCl A2-0006 / Franz A6D-0002.** A2-0006 is a single Active v1 row (`seed`) — consistent with the design's "in-place synced, not a version bump" characterization. A6D-0002 is out of scope (no `standard` group; `approved_by` null). **Correct.**
13. **`standard_group()` helper.** Returns `{"key": key, "kind": "singleton", ...}` at `_common.py` line 248. **Correct** (and the root of finding 2).
14. **A4-0004 `renderAsTable`.** A4-0004's standard carries `renderAsTable: True`; verified it is the only in-scope standard group with it. **Correct.**
15. **Frontend renderer reuse.** `WorksheetForm.tsx` `canAddRows = editable && group.kind !== 'singleton' && max > min` (line 1747); `renderAsTable` handled only inside the singleton branch on all three surfaces (`WorksheetForm` 1819, `PrintWorksheetPage` 438 under `isSingleton`, `WorksheetPreviewPage` 294 under `kind==='singleton'`). Types already allow `kind:'table'` + `rows` + `rowLabel`. **Correct** — the generic renderer is reused across all four surfaces with no per-template special-casing, and the one `renderAsTable` becomes dead data on conversion.

## Unverified / Wrong Assumptions

1. **WRONG — "aggregates bypass the collapse" with the collapse in `_resolve`.** (Finding 1.) The stated implementation site (`_resolve`) cannot distinguish a bare arithmetic reference from an aggregate argument; collapsing there breaks 816 verified live aggregate references. The rule is achievable, but only if the collapse is relocated to scalar coercion (`_as_number`) or to a `ColumnSeries` that collapses only under arithmetic.
2. **WRONG — "converting the shared helper only affects groups keyed `standard`."** (Finding 2.) The helper is also called with `key="standard_2"`; flipping its `kind` literal converts the out-of-scope `standard_2` in A4-0001 (module-backed) and diverges module from DB.
3. **WRONG (minor) — A4-0004 seed source is an "inline literal."** (Finding 3.) It is the shared `standard_group()` helper via `**`-spread plus `renderAsTable`.
4. **UNVERIFIED — parity-fixture coverage of `standard_2` and the DB-only six.** The design rests the safety of the six DB-only templates (A1-0002, A6A-0002/0003/0004, H1-0001/0002) entirely on the (f) layer-4 DB diff, and asserts the parity fixtures "already carry `standard` data." I did not execute the parity suite or inspect each fixture's input coverage, so whether every in-scope `standard.<field>` (and the untouched `standard_2`) is actually exercised by an oracle is unconfirmed. The layer-4 diff is correctly identified as mandatory; its sufficiency depends on fixture completeness that was not run here.
5. **UNVERIFIED — `--validate-only` and `npm run build` currently pass.** Stated as gates; not executed in this review (no code changes exist yet to validate).
