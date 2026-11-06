# Design — Convert singleton "Standard Details" to an expandable one-row table across all test templates

## Overview

The R&D LIMS test-template engine models each worksheet as a `definition` JSON stored on the `test_templates` row. Each section is a *group* with a `kind` of `singleton`, `table`, or `sequence`. A number of templates carry the standard-prep section (`key == "standard"`) as a `singleton` — one implicit row holding weight, dilution chain, potency, MW correction and the derived concentration. This design converts every such singleton `standard` section into an expandable one-row `table` (`{min:1, max:10, default:1}`), so analysts can add STD-2, STD-3, … up to ten, while every currently-computed result stays bit-for-bit identical.

> **Row spec is authoritative, not chosen.** The user fixed the row spec explicitly: `rows: {min: 1, max: 10, default: 1}`. Every converted table uses `max: 10` (an earlier draft used `max: 6` by analogy to the sibling replicate-injection tables; that is superseded — the user's stated `max: 10` governs). No per-template inspection of the ceiling is required or permitted.

The work splits into four concerns, each locked below:

1. **Classification** — which templates are in scope, decided from the `kind` flag of the `standard` group.
2. **Formula preservation** — a single general rule in the calculation engine so a bare dotted reference to *any* now-multi-row group resolves to its first row *at the point of scalar numeric consumption* (`_as_number`), while aggregates and explicit indexing keep seeing the full column series. The change is engine-wide, not `standard`-specific, and the collapse site is `_as_number`, **not** the resolver `_resolve` (see (c)).
3. **Versioning + seeding** — a new version per template through the service's real lifecycle (branch Draft → write definition → submit → approve), producing a new `Active` row, the prior row `Inactive`, `superseded_by_id` linked, and a real approver e-signature. The declarative seed modules (where they exist) are kept in sync, converting the `standard` group **without** touching the out-of-scope `standard_2` group that shares the same helper.
4. **Frontend** — confirmation that the generic table renderer already handles the converted section on all four surfaces with no per-template special-casing (one dead UI hint on A4-0004 to retire).

The investigation below is against the real worktree code (`…\.worktrees\std-details-tabular\backend-v2\src\domain\services\calculation\`, `…\frontend-react\src\features\test-templates\`), the seed modules (`…\backend-v2\scripts\template_definitions\`), and the live catalogue in the **main-repo** `d:\RD-instance\GIT\backend-v2\lims.db` (54 rows: 48 Active, 1 Draft, 3 Inactive, 2 raw-string `Superseded`). The worktree has **no** `lims.db` of its own (see (d)).

**Technology stack (locked):** Python 3.13 backend (SQLAlchemy models + SQLite `lims.db`), the in-house expression engine in `backend-v2/src/domain/services/calculation/`, declarative seed modules in `backend-v2/scripts/template_definitions/`, the `TestTemplateService` lifecycle (`src/application/services/test_template_service.py`) and its FastAPI endpoints, and a React + TypeScript frontend (`tsc -b && vite build`, PrimeReact). No new libraries, no schema changes.

---

## (a) The singleton-vs-table classification flag and procedure

### The exact flag

The distinguishing field is the group-level **`kind`** key in the definition JSON, parsed into `GroupKind` by `backend-v2/src/domain/services/calculation/template_schema.py` (`GroupKind.SINGLETON = "singleton"`, `TABLE = "table"`, `SEQUENCE = "sequence"`). `GroupDef.is_multi_row` is `True` for `table` and `sequence`. The section's **label is NOT used** for classification — labels like "Standard Details", "Standard detail", "STD Prep.", "Nitrosamine Standard", "Standard Preparation", "Reference Standard Details" all denote the same singleton standard section, and A11's table standard is also labelled "Standard Dose Levels".

### The exact procedure

For every template row where `status == 'Active'`:

1. Parse `definition` JSON.
2. Find the group with `key == "standard"` (the canonical key for the Standard Details section; distinct from `std_areas`, `std_injections`, `std_preps`, `std_stock`, `standards`, `standard_2`, `corel_*`, `bkt_*`, `stats`, which are separate sections and out of scope).
3. If no `standard` group exists → **skip**.
4. If `standard.kind == "singleton"` → **IN SCOPE** (convert).
5. If `standard.kind` is `"table"` or `"sequence"` → **OUT OF SCOPE** (already tabular; leave untouched).

This procedure was run against `lims.db` during design (the classification script is reproduced conceptually in (g)) and produced exactly the roster in (g): 25 singleton, 4 table, 19 with no `standard` group, reconciling to 48 Active.

Note on the "already a table" exclusions the user named: A11 "Standard Dose Levels" uses `key="standard"` with `kind="table"` (caught by step 5). The A6d Franz "Standard Tapinarof for Linearity" and A14 linearity replicate tables do **not** use `key="standard"` at all, so they are caught by step 3. Both exclusion paths are exercised by real data.

---

## (b) Target table shape and how N is chosen

Each converted `standard` group changes **only** its `kind` (`singleton` → `table`) and gains a `rows` spec:

```json
{ "key": "standard", "kind": "table", "label": "<unchanged>",
  "rows": { "min": 1, "max": 10, "default": 1 },
  "fields": [ /* unchanged */ ] }
```

- `min: 1` — a standard is always required; the section can never be emptied.
- `default: 1` — a fresh worksheet opens with exactly one standard row, so the on-screen and print layout and every result are visually and numerically identical to today's singleton until an analyst explicitly adds a row.
- `max: 10` — the add-row ceiling, fixed by the user.

### N is fixed at `max: 10` for all 25 (user-specified, not chosen)

`RowSpec.parse` (`template_schema.py`) requires `min <= default <= max`; with `min=1, default=1` the value `max=10` is valid. The user set the row spec explicitly to `rows: {min: 1, max: 10, default: 1}`, so **`max: 10` is applied uniformly to all 25 in-scope templates**. There is no per-template decision and no analysis of sibling tables; an earlier draft's `max: 6` (derived by analogy to the `std_areas` replicate tables, whose helper default is `max_rows=6`) is superseded by the user's stated ceiling. The implementer applies `{min:1, max:10, default:1}` verbatim.

### Rendering controls

A `table` group with `max > min` automatically renders add-row and delete-row controls in the worksheet form (see (e)) — the same path `std_areas` and the other injection tables already use, so no extra flags are required; with `max:10` the analyst can add rows until ten standard preparations are present. Optionally a `rowLabel: { format: "STD - {n}" }` captions rows STD-1, STD-2 rather than a bare ordinal; this is UI-only and is applied uniformly as a cosmetic enhancement, not a per-template decision.

> **`rowLabel` is a frontend-only presentation hint.** It is stored in the raw definition JSON and consumed by the React renderer (`RowLabelConfig.format` with `{n}` as the 1-based row number, verified in `frontend-react/.../testTemplate.types.ts`), but the backend schema parser (`RowSpec.parse`/`GroupDef.parse` in `template_schema.py`) reads only `rows` (`min`/`max`/`default`/`labelFrom`/`seed`) and ignores unknown group keys. So `rowLabel` passes server validation (dropped on parse, not rejected); it neither validates against the schema nor affects evaluation. Do not expect it to round-trip through the parsed backend model.

---

## (c) Calculation-engine name-resolution change for formula preservation

### The exact module, function, and code path

- Module: `backend-v2/src/domain/services/calculation/evaluator.py`, class `WorksheetEvaluator`.
- Functions: **`_build_scope`** (line 314 — scope for row-scoped field evaluation) and **`_sheet_scope`** (line 390 — scope for criteria and reportable-result extraction). These are the two places that project each group into the expression scope.
- Resolver: `backend-v2/src/domain/services/calculation/expression.py`, **`_Evaluator._resolve`** (line 407), which walks a dotted `_Ref` through dict/list/attr access.

Today both scope functions expose a group like this (verified, lines 322–327 and 394–399):

```python
if other.is_multi_row:
    scope[other.key] = { f.key: [r.get(f.key, EMPTY) for r in other_rows] for f in other.fields }  # column series (list per field)
else:
    scope[other.key] = dict(other_rows[0]) if other_rows else {}                                    # scalar per field
```

So for a **singleton** `standard`, `standard.weight_mg` resolves via `_resolve` (dict → `current["weight_mg"]`, a scalar). The moment `standard` becomes `table`, the same reference resolves to a **list** (the column series), and every `standard.<field>` arithmetic term would break — division/multiplication against a list yields `EMPTY`, blanking the whole result chain. This is the core risk the conversion must neutralise.

### The general rule (chosen approach) — collapse at scalar coercion, NOT in the resolver

Introduce a **column-series value object** that is simultaneously (i) a list — preserving `mean(group.field)`, `group.field[0]`, `pool(...)`, `slope/intercept/correl`, `where(...)` and all aggregate/indexing semantics for every multi-row group — and (ii) collapsible to its first element **only when the engine coerces it to a scalar number**, which is exactly where a bare arithmetic `group.field` is consumed and nowhere else.

Two pieces, both in `expression.py`:

1. **`ColumnSeries(list)` wrapper (new).** Add a tiny `class ColumnSeries(list): pass` subclass. Change `_build_scope` (evaluator.py line 314) and `_sheet_scope` (evaluator.py line 390) to wrap each multi-row field's per-row list in it, so multi-row groups expose `{field: ColumnSeries([...])}` instead of a bare `[...]`. Because `ColumnSeries` *is* a `list`, `_flatten` (expression.py line 368, `isinstance(values, (list, tuple))`), `_numeric` (which calls `_flatten`), explicit indexing in `_resolve` (the `isinstance(current, (list, tuple))` branch), and every aggregate function see it as the full series — **unchanged**. `_resolve` returns it verbatim; the resolver is NOT modified to collapse.

2. **First-element collapse in `_as_number` (the single collapse site).** `_as_number(value, ctx)` (expression.py, used by `_binary`, `_unary`, and the rounding/`trunc`/`abs`/`sqrt`/… operand coercions) is the function the engine calls the instant it needs a *scalar number* from a value. Add, at the top of `_as_number`, before the existing blank check: *if `value` is a non-empty `ColumnSeries`, set `value = value[0]`; if it is an empty `ColumnSeries`, return `EMPTY`.* Then the existing logic runs on the scalar. This makes a bare `standard.weight_mg` in `a / standard.weight_mg` resolve to row 0, because `_binary` coerces each operand through `_as_number`.

Why this site and not `_resolve`: `_resolve` is the **single code path that produces the value an aggregate argument evaluates to** — in `_call`, `args = [self.eval(a) for a in node.args]`, and `self.eval` on a `_Ref` calls `_resolve`. If `_resolve` collapsed a `ColumnSeries` to `series[0]` at end-of-walk, then `mean(std_areas.area)` would receive a single scalar and return the mean of one value. The design review verified this empirically: **816** bare, non-indexed `group.field` references to multi-row groups are passed directly into aggregates (`mean`/`sd`/`rsd`/`pool`/`slope`/…) across all 48 Active templates; a resolver-level collapse corrupts every one. `_as_number` is never called by the aggregate functions (they go through `_numeric`→`_flatten`, which iterate the list), so collapsing there leaves aggregates untouched while catching exactly the arithmetic-operand case we need. Indexing (`group.field[1]`) is also unaffected: the index is consumed mid-walk in `_resolve`, yielding a scalar long before any coercion.

This is a **single general rule — "a bare dotted reference to a multi-row group's field collapses to its first row at the moment it is coerced to a scalar number"** — applied in one place (`_as_number`) that every arithmetic/comparison/rounding operand already flows through, so it covers `_build_scope`, `_sheet_scope`, criteria targets and `resultRef` uniformly. No formula strings change.

**Equality operands (`=`, `==`, `<>`, `!=`) use a second coercion path — collapse there too.** `_binary` routes `=`/`<>` through `_loose_equal`, not `_as_number`. For full engine-wide correctness the same first-element collapse must be applied to a `ColumnSeries` operand inside `_loose_equal` (or, equivalently, `_loose_equal` must first unwrap a `ColumnSeries` to its `[0]`), so a bare `group.field` compared for equality also sees row 0. Verified there is currently **no** template with a bare `standard.<field>` (or any bare multi-row field) in an `=`/`<>` comparison — a catalogue grep returns zero hits — so this path is latent today, but the collapse is added to `_loose_equal` as well to keep the engine-wide rule complete and future-proof. A fifth unit test covers `group.field = <scalar>` collapsing to row 0.

> **Rejected alternative:** collapsing in `_resolve` at end-of-walk (the prior draft's approach). Rejected because `_resolve` cannot distinguish a bare arithmetic reference from an aggregate argument — both arrive as a 2-part `_Ref` with no trailing index — so it would feed scalars into the 816 live aggregate references and break the catalogue. A second viable option is to make `ColumnSeries` override the arithmetic dunders (`__truediv__`, `__mul__`, …) to collapse to `self[0]`; this works but spreads the rule across many dunder methods and still would not cover `_as_number`-based rounding operands cleanly. The `_as_number` single-site collapse is chosen as the lowest-risk, smallest-surface option.

### The decision this surfaces is ENGINE-WIDE, not `standard`-specific

The row-0 collapse changes resolution for **every** `table`/`sequence` group, not just `standard`. The real invariant the implementer is signing up for is: *any* bare (non-aggregated, non-indexed) `group.field` reference to *any* multi-row group now takes row 0 instead of yielding a list.

This was verified safe against the **entire current catalogue** (all 48 Active templates), not just the 25 in scope:

- A catalogue-wide scan of every expression, criterion `target`, and `resultRef` found **zero** bare (non-aggregated, non-indexed) references to any multi-row group's field. Every multi-row field reference today is either inside an aggregate (`mean`, `sd`, `rsd`, `sum`, `pool`, `where`, `slope`, …) or explicitly indexed (`weights.weight[7 - 1]` etc.).
- For the 25 in-scope templates specifically, every `standard.<field>` reference is the scalar form (`standard.weight_mg`, `standard.potency`, `standard.conc_ppm`, the A2-0002/0003 `standard.pc_*`/`standard.pg_*` pairs, NITRO's `standard.ml_stock_*`, A6a/A6b's `standard.dilution_1`/`volume_1`). Zero aggregates over `standard.*`, zero indexed `standard.field[...]`, zero bare whole-group `standard`.

Therefore **no existing result changes**, and there is **no live formula that must be rewritten**. This is the user decision point the task asked to surface, and the answer today is "no formula is affected" — but it is an engine-wide decision, so it is stated as such.

#### Residual risk and the guard

The only way the rule could ever change a value is a *future* formula that deliberately relies on a bare `group.field` yielding a list to feed something list-consuming (e.g. a future `mean(standard.area)` across multiple standard rows written as a bare reference). None exists today. Two guards pin the boundary:

1. **Unit tests** (new, `backend-v2/tests/calculation/`), each built on a minimal two-row multi-row group fed through `WorksheetEvaluator`/`evaluate`:
   (a) a two-row `standard` table resolves a bare `standard.weight_mg` used in arithmetic to **row 0** (`a / standard.weight_mg` uses the first row's weight);
   (b) **the distinguishing test** — `mean(group.field)` over a two-row group returns the **mean of both rows**, and `sd(group.field)` sees both rows, proving the collapse is in `_as_number` and does NOT reach aggregates (this test *fails* under the rejected `_resolve` collapse, so it pins the correct implementation);
   (c) explicit `group.field[1]` still returns the **second** row;
   (d) an empty `ColumnSeries` coerces to `EMPTY` in arithmetic (blank-propagation preserved);
   (e) a bare `group.field = <scalar>` equality comparison collapses to row 0 (covers the `_loose_equal` path).
2. **Static guard**: the apply step (see (f)) re-runs the catalogue-wide scan for bare multi-row `group.field` references across *all* groups (not just `standard`) and fails if any new one appears, so a future list-consuming bare reference that relies on the pre-change list behaviour is caught rather than silently collapsed.

**No formula string is rewritten in this task.**

#### Value migration: `result.values["standard.*"]` → `result.rows["standard"][0]`

Converting `standard` to a table has a second, benign effect the parity harness must account for. In `evaluate` (evaluator.py lines 164–168) the flat scalar mirror `result.values["group.field"]` is populated **only for non-multi-row groups**:

```python
for group in self._def.groups:
    if not group.is_multi_row and result.rows.get(group.key):
        for key, value in result.rows[group.key][0].items():
            result.values[f"{group.key}.{key}"] = value
```

After conversion `standard` is multi-row, so `result.values["standard.conc_ppm"]` and its siblings are **no longer emitted**; those numbers live in `result.rows["standard"][0]`. This is verified behaviorally safe — nothing consumes the removed keys: no `resultRef` points at `standard` (all 25 checked), no `mirrorFrom`/`mirrorTarget` references `standard.`, and the frontend print/preview pages read `computed.rows[groupKey][index][fieldKey]` for every group, never `computed.values["standard.*"]`. The parity diff (see (f)) must compare `values` and `rows` by **logical `(group, field)` identity** so `values["standard.x"]` (old) equals `rows["standard"][0]["x"]` (new); a naive `values`-equality diff would false-positive on this expected migration.

### Testability

- **Unit (engine):** the five tests above are pure and fast; they do not touch the DB. Test (b) is the one that distinguishes the chosen `_as_number` collapse from the rejected `_resolve` collapse.
- **Parity (templates):** the existing `tests/calculation/test_seeded_template_parity.py` and per-template parity tests evaluate each seeded definition against hand-derived oracle values. After converting the seed modules, these must still pass unchanged — the regression guard that every converted template reproduces its workbook.

---

## (d) Version-bump lifecycle and seeding mechanism

### The real lifecycle (verified from the live rows)

The authoritative lifecycle is the one the domain enforces, **not** the raw-string artifact on the oldest rows. Verified in code and DB:

- `TemplateStatus` (`src/domain/entities/test_template.py`) has exactly four members: **`Draft`, `PendingApproval`, `Active`, `Inactive`**. There is **no `Superseded` status.**
- `TestTemplate.deactivate()` sets `status = "Inactive"`. `approve()` sets `status = "Active"`, `approved_by = <actor username>`, `approved_at = <now>`.
- `TestTemplateService._supersede_prior_versions` (called inside `approve`) does two things to each older version: `other.deactivate(actor.username)` (→ `Inactive`) **and** `other.mark_superseded_by(approved.id, …)` (sets `superseded_by_id`). "Supersede" names the **back-link column**, not a status.

The live rows confirm which convention is real:

| Code | Versions (id, version, status, superseded_by_id, approved_by) |
|------|----------------------------------------------------------------|
| **TPL-A8-0001** | v1 (9, 1, `Inactive`, →24, `seed`); **v2 (24, 2, `Active`, —, `admin`)** |
| **TPL-A6A-0005** | v1 (40, 1, `Inactive`, →44, `seed`); v2 (41, 2, `Inactive`, →44, `admin`); **v3 (44, 3, `Active`, —, `admin`)** |
| TPL-A4-0002 | v1/v2 `Superseded` (raw string), v3 `Active`, all `approved_by='seed'` |

A8-0001 v2 and A6A-0005 v3 are the **real, service-driven version bumps**: prior versions are `Inactive` (not `Superseded`), `superseded_by_id` points at the new Active id, and the new version carries a human approver (`admin`). A4-0002's `Superseded` string is a **pre-domain-model artifact** written by an older hand script that bypassed the entity; only two such rows exist in the whole catalogue. **This task follows the A8-0001 / A6A-0005 convention and never writes the string `Superseded`.**

### The lifecycle this task produces, per template

For each in-scope code, the end state after the bump must be:

1. **New row:** same `code`, `name`, `archetype`, `test_id`, `result_unit`; `version = current_max_version + 1`; `status = "Active"`; `definition = <converted JSON>` (deep copy with only the `standard` group's `kind`/`rows` changed, plus optional `rowLabel`, and A4-0004's dead `renderAsTable` dropped — see (e)); `superseded_by_id = NULL`; `approved_by = <approving actor, e.g. 'admin'>`; `approved_at = now`; `created_by`/`modified_by = <actor>`.
2. **Prior Active row:** `status = "Inactive"` (via the entity's `deactivate`), `superseded_by_id = <new row id>`, `modified_by/modified_date` touched.

`code`, `name`, `archetype`, `test_id`, `result_unit` are preserved and asserted unchanged between old and new row.

### The seeding mechanism (chosen): drive the service lifecycle through the API

Three mechanisms exist; the task requires the one the newest version bump actually used.

- `scripts/seed_test_templates.py` — **additive/idempotent**, skips existing `code`, always inserts `version=1`. Cannot bump a version. Used only as the `--validate-only` gate. **Rejected for the write.**
- The `backend-v2/_apply_*.py` ORM scripts and the called-out `_apply_a6d_linearity.py` — verified to be an **in-place edit of a `Draft` row** (asserts status Draft and keeps it Draft); it bumps **no** version. The NaCl `scripts/update_a2_0006_definition.py` is likewise an **in-place sync** of a single Active row (`modified_by='a2-0006-…'`), not a version bump. These are precedents for *in-place definition edits*, **not** for inserting a new Active version. **Rejected as the version-bump pattern.**
- `scripts/update_a6a5_v3_definition.py` — the **actual, audited version-bump precedent**. Its docstring states an Active template is immutable, so a new version must be branched to a Draft first. It drives the API: `POST /test-templates/{id}/new-version` (→ Draft v+1), `PUT /test-templates/{draft_id}/definition` (re-validated server-side), and **deliberately leaves the new version as a Draft** for a human to approve. This is exactly the service contract: `update_definition` rejects edits unless `status == Draft` ("Branch a new version instead"); `submit_for_approval` re-validates; `approve` requires `PendingApproval`, e-signs with the actor's username, and runs `_supersede_prior_versions`.

**Chosen:** follow `update_a6a5_v3_definition.py` — drive the service through its HTTP API, for every in-scope code, with an explicit authenticated actor (e.g. `admin`). The flow per code:

1. `GET` the current Active row by code/id; assert `status == Active`; capture its `definition`.
2. `POST …/new-version` → a Draft at `version = max+1` (idempotent: reuse an existing unapproved Draft of this code if one is already present, exactly as the A6A-0005 script does).
3. Build the converted definition in memory (`deepcopy` the Active definition; flip **only the `key=="standard"`** group `kind`→`table`, add `rows:{min:1,max:10,default:1}`, add optional `rowLabel`, drop `renderAsTable` if present; leave `standard_2` and every other group untouched). `PUT …/{draft_id}/definition` — the server re-validates (`TemplateDefinition.parse` + empty-input evaluator dry run).
4. `POST …/{draft_id}/submit` → `PendingApproval` (re-validates again).
5. `POST …/{draft_id}/approve` as the approving actor → `Active`; the service automatically deactivates the prior Active version (→ `Inactive`) and sets `superseded_by_id`. The e-signature records the real approver.

This produces the identical end-state to A8-0001 v2 / A6A-0005 v3: new `Active`, prior `Inactive`, `superseded_by_id` linked, `approved_by=<actor>`. It is the GxP-correct route: every bump is re-validated on submit and e-signed on approve, which a direct `status='Active'` insert would skip.

A single driver script at the backend-v2 root — e.g. `_apply_standard_tabular.py` — orchestrates the 25 codes (holding the in-scope list, re-verifying each `standard` group is still `singleton` at runtime so an already-converted template is skipped, keeping the run idempotent and re-runnable). It must be run against a backend pointed at the authoritative DB (below). It performs the before/after parity diff (see (f)) per code and refuses to proceed past step 4 for a code whose diff is not clean. A `--validate-only` mode runs steps 1–3 against a throwaway Draft (or purely in memory) without approving.

> If running the live API in the worktree is impractical, the fallback is a script that replicates the service's **exact** end-state directly via the ORM — new row `Active`, prior `Inactive`, `superseded_by_id` set, `approved_by=<actor username>` (never `seed`), `approved_at=now` — and that explicitly documents it is reproducing `_supersede_prior_versions`. It must still pass the two-pass validate gate. The direct-Active-insert-with-`approved_by='seed'`-and-`status='Superseded'` approach from the prior draft is **not** acceptable: it writes a non-existent status, skips re-validation, and falsely asserts no human signed the bump.

### approver / audit convention

`approved_by = 'seed'` appears **only** on original seeded v1 rows. Genuine version bumps carry the approver's username (`admin` on A8-0001 v2 and A6A-0005 v3), because `approve()` sets `approved_by = actor.username`. This task's bumps therefore set `approved_by = <the actor the run is performed as>` (e.g. `admin`) — not `seed`. An unsigned automated bump would contradict both recent precedents and the e-signature the lifecycle is built to capture, so it is not used.

### Keeping the declarative seed modules in sync — the complete file inventory

The parity suite reads the seed **modules**, not the DB, so every in-scope template whose standard group is produced by a module must be converted **at source** too, or the module diverges from the DB and the parity guard evaluates an unconverted definition. The prior draft's claim that `_common.standard_group` + three modules covers everything is **wrong**: standard groups are emitted two ways, and six in-scope templates have no module at all.

Verified source map for the 25 in-scope codes:

**(i) Via the shared `standard_group()` helper in `scripts/template_definitions/_common.py`** (today returns `{"key": key, "kind":"singleton",…}` and takes a `key` parameter). The helper is called with **two different keys**: `key="standard"` (in scope) and `key="standard_2"` (the second reference-standard singleton in `a4_a5_related_substances.py` line 77, which is OUT of scope). A naive "flip the `kind` literal in the helper" edit would convert **both**, because the helper has no knowledge of which key it is emitting — this was the prior draft's error (finding 2). The helper emits a shared `kind` literal across every caller, so flipping it unconditionally would turn `standard_2` into a table in A4-0001's seed module, diverging it from the DB (whose driver only flips `key=="standard"`), and violating the stated scope.

**Chosen helper strategy — make the conversion key-aware via a parameter.** Add a parameter to `standard_group()`:

```python
def standard_group(*, key="standard", label="Standard Details", with_mw=True,
                   conc_label="Concentration", as_table: bool = False) -> dict:
    ...
    group = {"key": key, "kind": "table" if as_table else "singleton",
             "label": label, "fields": fields}
    if as_table:
        group["rows"] = {"min": 1, "max": 10, "default": 1}
    return group
```

Then pass `as_table=True` **only at the in-scope `key="standard"` call sites**, and leave the `key="standard_2"` call (and every out-of-scope caller) unchanged so it keeps emitting a singleton. This is strictly safer than a module-local literal because every converted site reuses the parity-tested helper body (fields unchanged); the only per-site edit is adding `as_table=True`.

In-scope helper callers that get `as_table=True`:
- `a1_assay.py` (A1-0001), `a2_a3_content.py` (A2-0001, A3-0001), `a4_a5_related_substances.py` **the `key="standard"` call only** (A4-0001 — leave the `key="standard_2"` call as singleton), `a6_dissolution.py` `_standard_groups()` (A6A-0001, A6B-0001, A6C-0001), `a8_content_uniformity.py` (A8-0001), `a8_cu_tablets_30units.py` (A8-0004 — verified it calls the shared helper, not an inline literal), `a9_a10_a13_classical.py` (A13-0001), `a12_derived_rollups.py` (A12-0001 — verified it calls the shared helper), and **`a4_rs_against_standard_rrf_division.py`** (A4-0004 — see below, helper via `**`-spread).

Out-of-scope helper callers left untouched (NO `as_table`): the `key="standard_2"` call in `a4_a5_related_substances.py`; `a11_microbial_bioassay.py` `_api_standard_group()` (A11 standard is already a table via a different construction); `a4_lenacapavir_related_substances.py` (its `standard_details` is a context field, not this group). A gate assertion (see (f)) confirms `standard_2` stays `kind:"singleton"` in A4-0001/H1-0001/H1-0002 after conversion.

**A4-0004 is a helper caller via `**`-spread, not an inline literal (finding 3).** `a4_rs_against_standard_rrf_division.py` line 249 emits `{**standard_group(label=..., conc_label=...), "renderAsTable": True}` — it spreads the shared helper (default `key="standard"`) and adds the `renderAsTable` hint. So A4-0004 converts the **same way as every other helper caller**: pass `as_table=True` into the spread, and additionally **drop the `"renderAsTable": True"` key** (dead once the group is a real table — see (e)). Do NOT hand-rebuild A4-0004's standard block as an inline literal; that would duplicate and drift from the parity-tested helper output. The module's own inline comment confirms the intent: it chose `renderAsTable` on a singleton precisely to "preserve the singleton's scalar evaluator scope ... while presenting ... as a table" and warned that `kind:"table"` "would turn those scalar formula references into column lists" — which is exactly the breakage the engine collapse rule (c) now prevents, making the real `kind:"table"` conversion safe.

Re-run the full parity suite after the helper edit: converting the helper is safe only because the collapse rule (c) is engine-wide, and the key-aware parameter keeps `standard_2` untouched.

**(ii) Via module-local helpers / inline literals** (hand-built `"key":"standard"` blocks that do NOT call the shared helper — each must be edited individually to set `kind:"table"` + `rows:{min:1,max:10,default:1}`):
- `a1_assay_fp_mgml.py` — A1-0003 (inline literal).
- `a2_lyso_content.py` — A2-0002 (inline literal).
- `a2_lyso_content_mgvial.py` — A2-0003 (inline literal).
- `a2_sodium_chloride_ic_mgvial.py` — **A2-0006** (the called-out NaCl template; inline literal).
- `a6a_leuprolide_microsphere.py` — A6A-0005 (module-local `_standard_group()`, line 102).
- `a6b_octreotide_ph10.py` — A6B-0002 (module-local `_a6b_standard_group()` in `a6_dissolution.py` line 412 / `_standard_group()` in `a6b_octreotide_ph10.py` line 85 — convert whichever emits A6B-0002's `standard`).
- `nitrosamine_routine.py` — NITRO-0001 (module-local `_standard_group()`, line 89).

> **A8-0004 and A12-0001 are NOT inline** (corrected from the prior draft): both call the shared `standard_group()` helper (`a8_cu_tablets_30units.py` line 214, `a12_derived_rollups.py` line 317), so they are covered by the (i) helper strategy — add `as_table=True` at those two call sites. They are listed under (i), not here.

> `a2_ampho_lipid_content.py`, `a2_bupivacaine_lipid_ratio.py`, `a6_dissolution.py`'s extra inline block, and the `a11` inline blocks also contain `"key":"standard"` literals but map to OUT-OF-SCOPE codes (A2-0005, A2-0004, A11) whose standard is already a table or whose inline block is a different section — do **not** convert those. The runtime guard (only flip a group with `key=="standard"` and `kind=="singleton"`) protects against touching them.

**(iii) DB-only templates with NO seed module** (verified: no `code=` definition and no hand-built block anywhere in `scripts/` or the `_apply_*` scripts): **A1-0002, A6A-0002, A6A-0003, A6A-0004, H1-0001, H1-0002.** These six exist only as DB rows (created via API/one-off scripts; e.g. A6A-0002 is explicitly documented as "a DB-only seeded row (no module)"). There is **nothing to edit in source** for them — the DB definition *is* their source of truth. The version-bump driver (which reads the live Active definition and converts it) is what converts them; the parity suite cannot cover them because there is no module, so their safety rests entirely on the before/after parity diff in (f) layer 4. This is called out as the reason the DB-diff layer is mandatory, not optional.

For each edited inline/module-local site, the exact mutation is: locate the dict it emits for the `key=="standard"` group and change `"kind": "singleton"` → `"kind": "table"`, add `"rows": {"min":1,"max":10,"default":1}`, optionally add `"rowLabel"`; leave `fields` untouched. For helper callers, pass `as_table=True` instead (see (i)). Never touch a `key=="standard_2"` block.

### The authoritative DB and the mandatory backup

The worktree `…\.worktrees\std-details-tabular\backend-v2\` has **no `lims.db`** (verified). The authoritative database is the **main-repo `d:\RD-instance\GIT\backend-v2\lims.db`** (54 rows, the live catalogue). Before any write:

1. Take a timestamped backup `lims.db.bak-stdtab-<UTC timestamp>` beside it (the established worklog convention).
2. **Pin the backend process to the authoritative file explicitly** (finding 5). The API-driven lifecycle writes to whatever DB the running backend is configured for, so the target is not left as an either/or: before launching the backend for the driver run, set its `DATABASE_URL` (via `backend-v2/.env`, the `.env.example` the workspace already carries) to the absolute authoritative path — `DATABASE_URL=sqlite:///d:/RD-instance/GIT/backend-v2/lims.db` — so the main-repo DB is the single target. (Running the backend from the main-repo checkout, which already defaults to that file, is the simplest way to guarantee this; copying the DB into the worktree is explicitly NOT done, to remove any copy-back step that could target the wrong file.)
3. **Fingerprint the catalogue before any write.** `_apply_standard_tabular.py` first calls `GET /test-templates` and asserts the expected catalogue shape — **54 total rows, 48 Active** (and, defensively, that the 25 in-scope codes each resolve to an Active `standard` group of `kind:"singleton"`). On any mismatch it aborts before the first `new-version`, so a backend accidentally pointed at a throwaway or wrong DB cannot be mutated.

The code and seed-module changes are committed in the worktree; the DB mutation targets the pinned main-repo `lims.db`. The version bump is hard to reverse, so the backup is mandatory, the `DATABASE_URL` is pinned, and the fingerprint gate guards the target — none of this is left to the implementer.

### Validation gate

`python -m scripts.seed_test_templates --validate-only` (run from `backend-v2`) parses and dry-runs every seed definition; it must pass after the module edits — the backend's own pre-write validation and the first acceptance check.

---

## (e) The four frontend surfaces + types

The generic table renderer already exists and is driven by `group.kind`, not by any template-specific key. Verified by reading each surface:

- **`components/WorksheetForm.tsx`** (data entry): the table branch computes `canAddRows = editable && group.kind !== 'singleton' && max > min` and renders Add-row / Delete-row using `group.rows.min`/`max`. Converting `standard` to `kind:'table', rows:{min:1,max:10,default:1}` moves it onto this path automatically (add/delete with ceiling 10, floor 1). **No code change required.** (`renderAsTable` is handled at line 1819 for singletons only; once the group is a table that branch no longer applies — see below.)
- **`pages/PrintWorksheetPage.tsx`** (print): branches on `group.kind === 'singleton'` vs the generic table printer (the `renderAsTable` special-case is at line 438, guarded by `isSingleton && group.renderAsTable`). A converted one-row `standard` prints as a one-row table, widening only if rows are added. **No code change required.**
- **`pages/WorksheetPreviewPage.tsx`** (preview): same split; the `renderAsTable` branch at line 294 is guarded by `group.kind === 'singleton' && group.renderAsTable`. A converted `standard` takes the generic table path. **No code change required.**
- **`models/testTemplate.types.ts`** (types): `GroupKind` is already `'singleton' | 'table' | 'sequence'`; `GroupDef.rows?: RowSpec` (`min`/`max`/`default`) and `rowLabel?` are already optional and typed; `renderAsTable?: boolean` is also present (line 244). A `standard` group typed `kind:'table'` with a `rows` spec is **already valid**. **No type change required.**

### The one hint to retire: A4-0004's `renderAsTable`

Of the 25 in-scope standard groups, exactly **one** carries a UI hint: **TPL-A4-0004**'s singleton `standard` has `renderAsTable: true` (verified; no other in-scope standard group has it). All three render surfaces special-case `renderAsTable` **only inside the `isSingleton`/`kind==='singleton'` branch**. Once A4-0004's `standard` becomes `kind:'table'`, that branch no longer runs, so `renderAsTable` becomes dead data. The conversion therefore **drops `renderAsTable` from A4-0004's `standard` group** (it is redundant once the group is a real table). During implementation, confirm the one-row generic table render for A4-0004 matches the prior `renderAsTable` layout (it should — `renderAsTable` was precisely a singleton-rendered-as-a-table hint, and the group is now an actual one-row table).

### Gaps

The generic renderer is reused **as-is**; no per-template special-casing is introduced on any surface, and no TypeScript or type change is required. The only edits are data (seed JSON: `kind`/`rows`, drop A4-0004 `renderAsTable`, optional `rowLabel`). The sole cosmetic consideration is the ordinal `#` column vs a `STD - {n}` caption, resolved uniformly by the optional `rowLabel`.

> **`rowLabel` is frontend-only (finding 4).** The React `RowLabelConfig.format` (`testTemplate.types.ts`) consumes it with `{n}` as the 1-based row number, but the backend schema parser (`RowSpec.parse`/`GroupDef.parse`) reads only `rows`/`labelFrom`/`seed` and ignores it — it passes server validation but is dropped on parse, so it neither validates against the backend schema nor affects evaluation. It is purely presentational.

### Frontend build gate

`npm run build` (`tsc -b && vite build`) must pass. Since no frontend source changes are required, it should pass unchanged; any `rowLabel`/hint change is data, not TypeScript, so no build impact.

---

## (f) Before/after value-parity verification

Parity is the GxP-critical acceptance criterion: every currently-computed result must be unchanged. The layers:

1. **Engine unit tests** (new): row-0 resolution for a bare arithmetic multi-row `group.field` (collapse in `_as_number`), `mean`/`sd` over a two-row series still aggregates both rows (collapse NOT reached — the test that fails under a `_resolve` collapse), explicit indexing still works, empty series coerces to `EMPTY`. Pins the general rule's boundaries and its collapse site.
2. **Static reference audit** (re-run by the driver before any write): assert that across **all** Active templates there is no bare (non-aggregated, non-indexed) `group.field` reference to any multi-row group — the condition under which the row-0 rule cannot change a value. If a counterexample is found, the driver refuses to proceed and surfaces it as the explicit engine-wide decision point from (c).
3. **Seeded-template parity suite**: `pytest backend-v2/tests/calculation/test_seeded_template_parity.py` (and per-template parity tests) must pass unchanged after the module edits — the strongest proof, since the oracle values predate the change. Note this covers only the 19 module-backed in-scope templates; the six DB-only templates (A1-0002, A6A-0002/0003/0004, H1-0001/0002) are covered solely by layer 4.
4. **Direct before/after DB diff** (mandatory, especially for the six DB-only templates): for each in-scope code, evaluate a representative worksheet input through `WorksheetEvaluator` against the **old** (singleton) and **new** (table, one row) definition and assert equality by **logical `(group, field)` identity** across the union of `result.values` and every `result.rows[*]`, plus `result.criteria` observed values and `result.reportable_result`. The diff must treat `values["standard.x"]` (old) and `rows["standard"][0]["x"]` (new) as the same cell, because converting `standard` to a table legitimately migrates those scalars from `values` to `rows` (see (c)). Any other divergence blocks the bump for that code. Representative inputs come from the existing parity-test fixtures (they already carry `standard` data for A1/A2/A3/A4/A6a/A6b/…); for the DB-only six, construct a minimal input exercising every `standard.<field>` they reference.
5. **Scope-preservation assertions** (new gate, driven by the driver and by the parity suite): after conversion of each code, assert (a) the `standard` group is now `kind:"table"` with `rows == {min:1,max:10,default:1}`; (b) for A4-0001/H1-0001/H1-0002, the `standard_2` group remains `kind:"singleton"` (finding 2 guard — catches a blanket helper flip); (c) for A4-0004, `renderAsTable` is absent from the converted group and the one-row generic table render matches the prior `renderAsTable` layout; (d) every other group's `kind`/`rows`/`fields` is byte-identical to the pre-conversion definition. For the module-backed templates this is also asserted directly against the helper output (e.g. a unit test that `standard_group(key="standard_2")` returns `kind:"singleton"` and `standard_group(as_table=True)` returns `kind:"table"` + `rows{...,max:10}`).
6. **Validation gates**: `python -m scripts.seed_test_templates --validate-only` passes; **frontend** `npm run build` passes.

A template is only version-bumped once layers 1–5 are green for it.

---

## (g) Affected vs skipped templates

Classified by the (a) procedure against the 48 Active rows in the main-repo `lims.db`.

### IN SCOPE — convert (25 templates; `standard` group is `kind:singleton`)

| Code | Archetype | Standard label | Seed source |
|------|-----------|----------------|-------------|
| TPL-A1-0001 | A1 | Standard Details | `a1_assay.py` → `standard_group()` helper |
| TPL-A1-0002 | A1 | Standard Details | **DB-only (no module)** |
| TPL-A1-0003 | A1 | Standard Details | `a1_assay_fp_mgml.py` (inline) |
| TPL-A2-0001 | A2 | Standard Details | `a2_a3_content.py` → helper |
| TPL-A2-0002 | A2 | Standard Details | `a2_lyso_content.py` (inline) |
| TPL-A2-0003 | A2 | Standard Details | `a2_lyso_content_mgvial.py` (inline) |
| TPL-A2-0006 | A2 | Standard Details | `a2_sodium_chloride_ic_mgvial.py` (inline) |
| TPL-A3-0001 | A3 | Standard Details | `a2_a3_content.py` → helper |
| TPL-A4-0001 | A4 | Reference Standard Details | `a4_a5_related_substances.py` → helper `key="standard"` call only (leave `standard_2`) |
| TPL-A4-0004 | A4 | Standard Details | `a4_rs_against_standard_rrf_division.py` → helper via `**`-spread; pass `as_table=True` + drop `renderAsTable` |
| TPL-A6A-0001 | A6a | Standard details for dissolution | `a6_dissolution.py` → helper |
| TPL-A6A-0002 | A6a | Standard details for dissolution | **DB-only (no module)** |
| TPL-A6A-0003 | A6a | Standard details for dissolution | **DB-only (no module)** |
| TPL-A6A-0004 | A6a | Standard details for dissolution | **DB-only (no module)** |
| TPL-A6A-0005 | A6a | Standard detail | `a6a_leuprolide_microsphere.py` → `_standard_group()` |
| TPL-A6B-0001 | A6b | Standard Preparation | `a6_dissolution.py` → helper |
| TPL-A6B-0002 | A6b | Standard detail | `a6b_octreotide_ph10.py` → `_a6b_standard_group()` |
| TPL-A6C-0001 | A6c | Standard Details | `a6_dissolution.py` → helper |
| TPL-A8-0001 | A8 | STD Prep. | `a8_content_uniformity.py` → helper |
| TPL-A8-0004 | A8 | Standard Details | `a8_cu_tablets_30units.py` → helper (line 214); pass `as_table=True` |
| TPL-A12-0001 | A12 | Standard Details | `a12_derived_rollups.py` → helper (line 317); pass `as_table=True` |
| TPL-A13-0001 | A13 | Nitrosamine Standard | `a9_a10_a13_classical.py` → helper |
| TPL-H1-0001 | A4 | Reference Standard Details | **DB-only (no module)** |
| TPL-H1-0002 | A4 | Reference Standard Details | **DB-only (no module)** |
| TPL-NITRO-0001 | A2 | Standard Preparation | `nitrosamine_routine.py` (inline/`_standard_group()`) |

All 25 take **`rows:{min:1,max:10,default:1}`** (user-specified).

Per-template notes:
- **A2-0002 / A2-0003** carry a two-analyte singleton standard (`pc_*` and `pg_*` field pairs in one row). Converting to a one-row table is correct — fields unchanged, all `standard.pc_*`/`standard.pg_*` references collapse to row 0.
- **A4-0001 / H1-0001 / H1-0002** also have a separate `standard_2` singleton (Reference Standard 2) — a different section (`key="standard_2"`), out of scope. Only `key="standard"` is converted. Critically, in `a4_a5_related_substances.py` the `standard_2` block is produced by the **same** shared `standard_group()` helper (called with `key="standard_2"`), so the helper must be made key-aware (add `as_table` param, passed `True` only at the `key="standard"` call) — a blanket helper flip would wrongly convert `standard_2`. A gate assertion confirms `standard_2` stays `kind:"singleton"` post-conversion (see (f)).
- **A6A-0005 / A6B-0002** use a dilution-style standard (`dilution_1`/`volume_1`/`dilution_2`); the conversion is identical (only `kind`/`rows` change).
- **NITRO-0001** has a stock-dilution standard (`stock_i..iv`, `ml_stock_*`); same mechanical conversion.
- **A1-0002, A6A-0002/0003/0004, H1-0001/0002** are DB-only (no seed module): converted by the version-bump driver reading the live definition; parity rests on (f) layer 4.

### OUT OF SCOPE — standard section already tabular (4 templates; `standard.kind == table`)

| Code | Archetype | Label | Reason |
|------|-----------|-------|--------|
| TPL-A2-0004 | A2 | Standard Details | `standard` already `kind:table` (multi-standard) |
| TPL-A2-0005 | A2 | Standard Details | `standard` already `kind:table` |
| TPL-A11-0001 | A11 | Standard Dose Levels | `standard` already `kind:table` (bioassay dose levels) |
| TPL-A11-0002 | A11 | Standard Dose Levels | `standard` already `kind:table` |

### OUT OF SCOPE — no `standard` group (19 Active templates)

TPL-A4-0002, TPL-A4-0003, TPL-A5-0001, TPL-A5-0002, TPL-A5-0003, TPL-A5-0004, TPL-A6D-0001, TPL-A6D-0002, TPL-A7-0001, TPL-A7-0002, TPL-A8-0002, TPL-A9-0001, TPL-A9-0002, TPL-A10-0001, TPL-A10-0002, TPL-A11-0003, TPL-A12-0002, TPL-A12-0003, TPL-A14-0001.

These either use differently-keyed standard sections (`standards`, `std_preps`, `std_stock`, `calibration`, `linearity`, `std`) already tables/sequences, or have no weighed-standard section (titration, LOD, area-normalisation, profile comparison, derived roll-ups). The A6d Franz and A14 linearity tables the user named fall here (their standard-type sections are not keyed `standard`). None are touched.

> **Draft, excluded:** TPL-A8-0003 is the catalogue's one `Draft` row and is excluded by the Active-only filter; it is not part of any list above.
>
> Scope reconciles: **48 Active = 25 in-scope + 4 standard-already-table + 19 no-`standard`-group.**

---

## Summary of changes (implementation checklist)

1. **Engine** (`expression.py`): add a `ColumnSeries(list)` wrapper; wrap each multi-row field's per-row list in it inside `evaluator.py` `_build_scope`/`_sheet_scope`; add the first-element collapse **in `_as_number`** (NOT `_resolve`) so a bare `group.field` collapses to row 0 only when coerced to a scalar number, while `_numeric`/`_flatten`-based aggregates and explicit indexing see the full series. Plus the four engine unit tests (crucially the `mean(group.field)`-over-two-rows test that fails under a `_resolve` collapse). Engine-wide change; verified no existing result changes across all 48 templates (the 816 live aggregate references stay intact because the collapse never reaches them).
2. **Seed source** — convert only the `key=="standard"` group at every emitting site. **Helper callers** (shared `_common.standard_group()` made key-aware with a new `as_table` param): `a1_assay.py`, `a2_a3_content.py`, the `key="standard"` call in `a4_a5_related_substances.py` (leave the `key="standard_2"` call singleton), `a6_dissolution.py` `_standard_groups()`, `a8_content_uniformity.py`, `a8_cu_tablets_30units.py`, `a9_a10_a13_classical.py`, `a12_derived_rollups.py`, and `a4_rs_against_standard_rrf_division.py` (A4-0004, via `**`-spread — pass `as_table=True` and drop `renderAsTable`). **Inline/module-local sites** edited directly (`kind:"table"` + `rows`): `a1_assay_fp_mgml.py`, `a2_lyso_content.py`, `a2_lyso_content_mgvial.py`, `a2_sodium_chloride_ic_mgvial.py`, `a6a_leuprolide_microsphere.py`, `a6b_octreotide_ph10.py`/`a6_dissolution.py` `_a6b_standard_group`, `nitrosamine_routine.py`. Each converted group: `kind:"table"`, `rows:{min:1,max:10,default:1}`, optional `rowLabel`. The six DB-only templates have no source to edit.
3. **DB version bump** — drive the service lifecycle (`new-version` → `PUT definition` → `submit` → `approve` as `admin`) for all 25 codes via a `_apply_standard_tabular.py` driver at backend-v2 root, idempotent, re-verifying `standard.kind=='singleton'` per code and flipping **only** `key=="standard"`. End state per code: new `Active` version, prior `Inactive`, `superseded_by_id` linked, `approved_by=admin`, identity fields preserved, `standard_2` untouched. Pin the backend's `DATABASE_URL` to the authoritative main-repo `d:/RD-instance/GIT/backend-v2/lims.db`; fingerprint the catalogue (54 rows / 48 Active) and abort on mismatch; take the mandatory timestamped `lims.db.bak-stdtab-*` backup first. Never write `status='Superseded'` or `approved_by='seed'`.
4. **Frontend**: no source or type change; drop the dead `renderAsTable` from A4-0004's converted group. The generic table renderer and `GroupKind` type already cover the converted section on all four surfaces.
5. **Gates**: engine + parity pytest green; before/after DB parity diff (logical `(group,field)` identity, values↔rows migration expected) equal for all 25 — the sole guard for the six DB-only templates; `scripts.seed_test_templates --validate-only` green; `npm run build` green.

---

## Responses to design-review findings (latest review — `design-review.json`, CHANGES_REQUESTED: 1 HIGH, 2 MEDIUM, 2 NIT)

- **1 (HIGH — row-0 collapse cannot live in `_resolve`; breaks 816 live aggregate refs).** Addressed. Confirmed in code that `_resolve` is the single path feeding aggregate arguments (`_call` does `args=[self.eval(a) …]`, `eval(_Ref)` → `_resolve`), so collapsing there would corrupt every `mean(std_areas.area)` etc. Section (c) is rewritten: the collapse now lives in **`_as_number`** (expression.py) — the one function the engine calls to coerce a value to a scalar number, used by `_binary`/`_unary`/rounding operands — while `_resolve` returns the full `ColumnSeries` untouched and aggregates (via `_numeric`→`_flatten`) see the whole series. The rejected `_resolve` approach is documented as such. Unit test (b) (`mean(group.field)` over two rows returns the mean of both) is added precisely because it fails under the rejected implementation and passes under the chosen one. The checklist and (f) layer 1 are updated to name `_as_number` as the collapse site.

- **2 (MEDIUM — shared helper also converts out-of-scope `standard_2`).** Addressed. Confirmed `standard_group(key="standard_2", …)` is called at `a4_a5_related_substances.py` line 77 and that a blanket `kind` flip in the helper would convert it. Section (d)(i), (g) and the checklist now specify a **key-aware helper**: add an `as_table: bool = False` parameter, emit `kind:"table"` + `rows:{min:1,max:10,default:1}` only when `as_table=True`, and pass `as_table=True` solely at the `key="standard"` call sites — leaving the `key="standard_2"` call (and all out-of-scope callers) singleton. (f) layer 5 adds an explicit gate asserting `standard_2` stays `kind:"singleton"` in A4-0001/H1-0001/H1-0002 after conversion, plus a helper-level unit test.

- **3 (MEDIUM — A4-0004 seed source mis-attributed as inline).** Addressed. Confirmed `a4_rs_against_standard_rrf_division.py` line 249 emits A4-0004's standard as `{**standard_group(…), "renderAsTable": True}` — the shared helper via `**`-spread, not an inline literal. (g) roster, (d)(i) and the checklist now reclassify it as a helper caller: pass `as_table=True` into the spread and drop the `renderAsTable` key; no hand-rebuilt literal. The module's own comment (preserve scalar scope while rendering as a table; `kind:"table"` would list-ify the refs) is cited to confirm the engine collapse rule makes the real `kind:"table"` conversion safe.

- **4 (NIT — `rowLabel` is frontend-only, unstated).** Addressed. Confirmed `RowSpec.parse`/`GroupDef.parse` (`template_schema.py`) parse only `rows`/`labelFrom`/`seed` and ignore `rowLabel`. Sections (b) and (e) now state explicitly that `rowLabel` is a frontend-only presentation hint stored in the raw JSON: it passes server validation (dropped on parse) but does not round-trip through the parsed backend model and does not affect evaluation.

- **5 (NIT — backend DB path not pinned for the API-driven write).** Addressed. Section (d)'s "authoritative DB" subsection now pins `DATABASE_URL=sqlite:///d:/RD-instance/GIT/backend-v2/lims.db` for the backend process (recommending the main-repo backend, and explicitly dropping the copy-DB-into-worktree option to remove copy-back risk), and requires `_apply_standard_tabular.py` to **fingerprint the catalogue (54 rows / 48 Active)** before any write and abort on mismatch. The checklist item 3 reflects this.

### Correction carried into this revision beyond the review

- **Row ceiling corrected to the user's spec.** The prior draft used `rows:{min:1,max:6,default:1}` throughout; the authoritative user requirement is **`rows:{min:1,max:10,default:1}`**. All occurrences (overview, (b), (d), (e), (g), checklist) are updated to `max:10`. The `max:6` sibling-table analogy is retained only as a dismissed rationale.

### Prior review (earlier 10-finding round) — remains resolved

The earlier review's findings (Superseded is not a real status; direct-Active-insert bypassing the lifecycle; incomplete seed-module inventory incl. the six DB-only templates; `approved_by='seed'`; row-0 rule is engine-wide; `values→rows` migration; A8-0003 Draft reconciliation; A4-0004 `renderAsTable`; DB authoritativeness/backup) remain addressed in sections (c)–(g): the service-driven `new-version → PUT → submit → approve` lifecycle with `status=Inactive`/`superseded_by_id`/`approved_by=admin`, the complete source map plus the six DB-only templates, and the engine-wide framing with the catalogue-wide zero-bare-ref evidence and the `values`↔`rows` logical-identity parity diff.
