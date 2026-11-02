# Design + Implementation Plan — TPL-A7-0003 "Dissolution F1-F2-calculations"

Task: build a FRESH LIMS test-calculation template with FOUR data-entry sections, following the
exact mechanism the earlier TPL-A7-0002 mirrored template used (a seed module + registration in
`__init__.py`, plus a scoped frontend render in `WorksheetForm.tsx`):

1. Section 1 "Test Product" — header block, six fields.
2. Section 2 "Reference Product" — the same six fields.
   → Sections 1 and 2 render SIDE BY SIDE (two responsive columns, stack on narrow screens).
3. Section 3 "Timepoints for Test Product" — a repeating timepoints table.
4. Section 4 "Timepoints for Reference Product" — a repeating timepoints table.

Plus a RECOMMENDED fifth f1/f2 comparison section (see §7 — open to the user's confirmation).

IMPORTANT distinction from TPL-A7-0001 / TPL-A7-0002: those use a SINGLE shared-row timepoints model
(one row carries both products' means). This template is DIFFERENT — each product has its OWN header
block AND its OWN timepoints table. The four sections are FOUR distinct groups. Do NOT reuse A7's
single-shared-row `timepoints` group or its per-row `abs(ref_mean - test_mean)` arithmetic.

All edits happen in the worktree: `d:\RD-instance\GIT\.worktrees\f1f2-calculations`.
Do NOT modify or overwrite `TPL-A7-0001` (`a7_profile_comparison.py`) or any other existing template.

Exploration grounding (what was actually read in the worktree):
- `backend-v2\src\domain\services\calculation\template_schema.py` — group kinds `singleton` /
  `table` / `sequence`; field kinds `context` / `input` / `area` / `calculated` / `flag`; value types
  `number` / `text` / `date` / `boolean`. Group keys and field keys must be valid Python identifiers
  and unique within scope. `resultRef` must be `"group.field"` and resolve to a real field.
- `backend-v2\scripts\template_definitions\_common.py` — `SeedTemplate` dataclass (fields: `code`,
  `name`, `archetype`, `result_unit`, `test_code`, `test_name`, `test_type`, `definition`) and
  `context_header(...)`.
- `backend-v2\scripts\template_definitions\a7_profile_comparison.py` — the f1/f2 arithmetic (one
  expression per step), the `comparison` singleton, and the five criteria. REFERENCE for formulas and
  style only; its data model is NOT reused here.
- `backend-v2\scripts\template_definitions\a6_dissolution.py` — per-product timepoints table /
  sequence shape (reference for the repeating-table style).
- `backend-v2\scripts\template_definitions\__init__.py` — import + splice into `SEED_TEMPLATES`.
  NOTE: the worktree `__init__.py` does NOT import the A7 mirrored module (that module does not exist
  in this worktree — the worktree is at an earlier state than `MadhuriWorktree`/main). Add the new
  module import alongside the existing `a7_profile_comparison` import.
- `backend-v2\scripts\seed_test_templates.py` — additive, idempotent seeder; validates + dry-runs
  every definition (`--validate-only`), creates the Test Master entry if absent.
- `frontend-react\src\features\test-templates\components\WorksheetForm.tsx` — the generic renderer and
  the two existing scoped flags `allowClearColumn === 'TPL-A6A-0004'` and
  `allowCumulativeVertical === 'TPL-A6A-0005'`; the `groups.map(...)` dispatch; the singleton
  field-grid render path.
- `frontend-react\src\features\test-templates\models\testTemplate.types.ts` — `FieldDef`, `GroupDef`,
  `GroupKind` already model everything used here; no type changes required.

---

## 1. Uniqueness confirmation (done)

Grepped the entire `template_definitions` tree (worktree, main repo, and other worktrees):
- Existing A7 codes: `TPL-A7-0001` / `TST-F1F2` (worktree + main), `TPL-A7-0002` / `TST-F1F2M`
  (main repo only — the mirrored module; absent from this worktree).
- `TPL-A7-0003` and `TST-F1F2CALC` do **not** appear anywhere. Both are UNIQUE. Safe to use.

`test_seeded_template_parity.py::test_template_codes_are_unique` will enforce this at test time.

---

## 2. Identifiers (confirmed)

| Field          | Value                                 |
|----------------|---------------------------------------|
| `code`         | `TPL-A7-0003`                         |
| `name`         | `Dissolution F1-F2-calculations`      |
| `archetype`    | `A7`                                  |
| `result_unit`  | `None` (f2 is dimensionless)          |
| `test_code`    | `TST-F1F2CALC`                        |
| `test_name`    | `Dissolution F1-F2-calculations`      |
| `test_type`    | `Quantitative`                        |
| `resultRef`    | `comparison.f2` (if §7 wired) — else see §7 fallback |

Archetype `A7` is already in the seeded-archetype set, so
`test_every_archetype_in_scope_is_seeded` (which asserts the SET of archetypes) is UNAFFECTED by
adding another `A7` entry. No edit to that test is required.

---

## 3. Group design — the four (or five) distinct groups

New module: `a7_f1f2_calculations.py` (see §4 for the full file structure). The definition's
`groups` list, in order:

### Section 1 — `test_product` (singleton header block)

```
{
  "key": "test_product",
  "kind": "singleton",
  "label": "Test Product",
  "fields": [
    {"key": "product_name", "kind": "input", "type": "text",   "label": "Product Name"},
    {"key": "batch_no",     "kind": "input", "type": "text",   "label": "Batch No."},
    {"key": "date_of_analysis", "kind": "input", "type": "date", "label": "Date of Analysis"},
    {"key": "media",        "kind": "input", "type": "text",   "label": "Media"},
    {"key": "rpm",          "kind": "input", "type": "number", "label": "RPM"},
    {"key": "volume",       "kind": "input", "type": "number", "label": "Volume", "unit": "mL"},
  ],
}
```

### Section 2 — `reference_product` (singleton header block)

Same SIX fields, same kinds/types/units, same keys (keys only need to be unique WITHIN a group, and
these live in a different group):

```
{
  "key": "reference_product",
  "kind": "singleton",
  "label": "Reference Product",
  "fields": [ <identical six field dicts as test_product> ],
}
```

Rationale for INPUT (not context) fields: there are two independent product blocks that cannot both
auto-source from the same single TRF context, so each of the twelve fields is an independently
editable `input`. This matches the user's screenshot (a plain vertical field list per section) and
avoids the "one shared context value feeding two blocks" problem. Field-type choices per the brief:
Date of Analysis = `date`; Media = `text`; RPM = `number`; Volume = `number` (mL); Product Name /
Batch No. = `text`. A helper `_product_header_fields()` returns the shared six-field list so Sections
1 and 2 are defined once and reused (one change pattern, two call sites).

### Section 3 — `test_timepoints` (repeating table)

Each row is one time point of the TEST product's dissolution profile.

```
{
  "key": "test_timepoints",
  "kind": "table",
  "label": "Timepoints for Test Product",
  "rows": {"min": 1, "max": 20, "default": 6, "labelFrom": "time"},
  "fields": [
    {"key": "time",  "kind": "input", "type": "text",   "label": "Time Point", "required": True},
    {"key": "unit",  "kind": "input", "type": "text",   "label": "Unit", "default": "Hr"},
    {"key": "mean",  "kind": "input", "type": "number", "label": "Mean % Dissolved", "unit": "%"},
    {"key": "rsd",   "kind": "input", "type": "number", "label": "%RSD", "unit": "%"},
  ],
}
```

### Section 4 — `reference_timepoints` (repeating table)

Identical shape to Section 3, for the REFERENCE product. A helper `_timepoint_fields()` returns the
four-field list so both tables are defined once.

```
{
  "key": "reference_timepoints",
  "kind": "table",
  "label": "Timepoints for Reference Product",
  "rows": {"min": 1, "max": 20, "default": 6, "labelFrom": "time"},
  "fields": [ <identical four field dicts as test_timepoints> ],
}
```

Design decisions and rationale (one or two sentences each — this is a greenfield template, so these
are mine to make):

- **`kind: "table"` (not `sequence`) for Sections 3 and 4.** A7 uses `sequence` only because its
  `prior.`-based %RSD-limit rule reads earlier rows; this template has no cross-row arithmetic in the
  timepoint tables (each row is a self-contained mean/%RSD entry), so a plain `table` is the simpler
  correct kind. If §7's f1/f2 is wired, the row-INDEX alignment it needs (see §7) does not require a
  sequence either.
- **Row cap `max: 20`, `default: 6`.** Mirrors A7's `_MAX_TIMEPOINTS = 20` so a long profile needs no
  new template; `default: 6` is a reasonable starting row count for a dissolution profile.
- **Per-row `time` + `unit`.** `time` is the free-text label ("1", "24") used as the row label via
  `labelFrom`; `unit` ("Hr") is per-row display metadata. The two tables are INDEPENDENT (no mirroring
  between them) — this is the explicit distinction from TPL-A7-0002.
- **`mean` / `rsd` as `input` numbers.** Each profile's mean % dissolved and %RSD per timepoint are
  transcribed (as in A7, both profiles are already-released results), so they are inputs, not
  area-derived calculations.

### Section 5 — `comparison` (singleton; RECOMMENDED, see §7)

Only added if the f1/f2 recommendation in §7 is accepted. Holds the f1/f2 arithmetic computed from
the two timepoint tables by row index. See §7 for the exact field list and expressions.

---

## 4. Backend module structure — `a7_f1f2_calculations.py`

New file:
`d:\RD-instance\GIT\.worktrees\f1f2-calculations\backend-v2\scripts\template_definitions\a7_f1f2_calculations.py`

Structure (plain JSON-shaped dicts, same convention as every sibling module):

```python
"""
A7 (f1/f2 calculations) — TPL-A7-0003.

Four independent data-entry sections: a Test Product header, a Reference Product
header (both singletons, six identical input fields each), and a SEPARATE
repeating timepoints table per product. Unlike TPL-A7-0001/-0002 there is no
single shared row carrying both products' means — each product owns its header
and its timepoint table, so the four sections are four distinct groups.

<...note the f1/f2 recommendation from the plan here, and that it is wired as the
fifth `comparison` group pointing resultRef at f2; see plan §7...>
"""
from scripts.template_definitions._common import SeedTemplate

_MAX_TIMEPOINTS = 20


def _product_header_fields() -> list[dict]:
    return [ ...the six input fields from §3... ]


def _timepoint_fields() -> list[dict]:
    return [ ...the four input fields from §3... ]


_TEST_PRODUCT_GROUP = {"key": "test_product", "kind": "singleton",
                       "label": "Test Product", "fields": _product_header_fields()}
_REFERENCE_PRODUCT_GROUP = {"key": "reference_product", "kind": "singleton",
                            "label": "Reference Product", "fields": _product_header_fields()}
_TEST_TIMEPOINTS_GROUP = {"key": "test_timepoints", "kind": "table",
                          "label": "Timepoints for Test Product",
                          "rows": {"min": 1, "max": _MAX_TIMEPOINTS, "default": 6,
                                   "labelFrom": "time"},
                          "fields": _timepoint_fields()}
_REFERENCE_TIMEPOINTS_GROUP = {"key": "reference_timepoints", "kind": "table",
                               "label": "Timepoints for Reference Product",
                               "rows": {"min": 1, "max": _MAX_TIMEPOINTS, "default": 6,
                                        "labelFrom": "time"},
                               "fields": _timepoint_fields()}

_COMPARISON_GROUP = { ... see §7 ... }   # only if f1/f2 is wired

A7C_DEFINITION = {
    "resultRef": "comparison.f2",          # see §7 for the no-f1/f2 fallback
    "context": [],                          # see §5 — context handling
    "groups": [
        _TEST_PRODUCT_GROUP,
        _REFERENCE_PRODUCT_GROUP,
        _TEST_TIMEPOINTS_GROUP,
        _REFERENCE_TIMEPOINTS_GROUP,
        _COMPARISON_GROUP,                  # only if f1/f2 is wired
    ],
    "criteria": [ ... see §7: f2 NLT 50 advisory, f1 NMT 15 advisory, if wired ... ],
}

A7C = SeedTemplate(
    code="TPL-A7-0003",
    name="Dissolution F1-F2-calculations",
    archetype="A7",
    result_unit=None,
    test_code="TST-F1F2CALC",
    test_name="Dissolution F1-F2-calculations",
    test_type="Quantitative",
    definition=A7C_DEFINITION,
)

TEMPLATES = [A7C]
```

---

## 5. Context handling

The twelve header values live in the two singleton groups (§3), NOT in `definition.context`, because
the brief requires two independently editable blocks. So `definition["context"]` can be an EMPTY
list. This is allowed by the schema (`context` defaults to `()`).

Caution — `test_no_context_field_is_unfillable`: that invariant only applies to `context` fields. By
putting the header fields in `input` groups (not context) the invariant is trivially satisfied (no
context fields to be unfillable). Do NOT add placeholder context fields without a `source`,
`overridable`, or `default` — they would fail that test.

---

## 6. Registration — `__init__.py`

In `d:\RD-instance\GIT\.worktrees\f1f2-calculations\backend-v2\scripts\template_definitions\__init__.py`:

- Add an import next to the existing A7 import (`from scripts.template_definitions.a7_profile_comparison import TEMPLATES as _A7`):
  ```python
  from scripts.template_definitions.a7_f1f2_calculations import TEMPLATES as _A7C
  ```
- Splice `*_A7C,` into the `SEED_TEMPLATES` list immediately after `*_A7,`.

---

## 7. THE f1/f2 RECOMMENDATION (surface to the user — do not silently decide)

**The genuine ambiguity:** should the f1/f2 comparison math be wired now, or does this first cut only
need the four data-entry sections? The user's PRIMARY explicit requirement is the FOUR SECTIONS with
the listed fields and the side-by-side layout. f1/f2 is IMPLIED by the test name
("F1-F2-calculations") but was not spelled out in the verbatim request.

**Recommendation (wire it):** add a fifth `comparison` singleton group that computes f1/f2 from the
two timepoint tables' per-row means, reusing A7's proven formulas, and point `resultRef` at
`comparison.f2`. The test is literally named for the f1/f2 result, so a template that only captures
data without producing the number it is named after would be incomplete. This recommendation is OPEN
to the user's confirmation — the orchestrator should relay it.

**How f1/f2 is derived here (differs from A7's in-row subtraction because the means now live in two
SEPARATE tables, aligned by row index):**

```
f1 = Σ |R(t) − T(t)| / Σ R(t) × 100          (R = reference mean, T = test mean)
f2 = 50 · log10( 100 / sqrt(1 + (1/n) Σ (R(t) − T(t))²) )
```

Row-index alignment: `reference_timepoints.mean[i]` pairs with `test_timepoints.mean[i]`. The engine
exposes other groups as whole columns and supports indexed access (`group.field[i]`, seen in
`a6b` / A6A-0005 modules), so the `comparison` singleton can build the per-point difference series by
indexing both tables at the same row. The implementer MUST confirm the exact aggregate/indexing
expression support in `src\domain\services\calculation\expression.py` and
`evaluator.py` before finalizing the expressions, and model them on A7's one-step-per-cell style.

Suggested `comparison` field list (final expressions to be confirmed against the evaluator's
supported functions — `count`, `sum`, `abs`, `sqrt`, `log10`, indexed refs):

```
{
  "key": "comparison", "kind": "singleton", "label": "f1 / f2 Comparison",
  "fields": [
    {"key": "n_points", "kind": "calculated", "label": "n (time points compared)",
     "expression": "min([count(test_timepoints.mean), count(reference_timepoints.mean)])"},
    {"key": "sum_abs_diff", "kind": "calculated", "label": "Σ | R(t) − T(t) |", "unit": "%",
     "expression": "<Σ over i of abs(reference_timepoints.mean[i] - test_timepoints.mean[i])>"},
    {"key": "sum_ref", "kind": "calculated", "label": "Σ R(t)", "unit": "%",
     "expression": "sum(reference_timepoints.mean)"},
    {"key": "sum_sq_diff", "kind": "calculated", "label": "Σ [ R(t) − T(t) ]²",
     "expression": "<Σ over i of (reference_timepoints.mean[i] - test_timepoints.mean[i])^2>"},
    {"key": "mean_sq_diff", "kind": "calculated", "label": "Σ[...]²/n",
     "expression": "sum_sq_diff / n_points"},
    {"key": "f1", "kind": "calculated", "label": "f1 — difference factor",
     "expression": "sum_abs_diff / sum_ref * 100", "rounding": {"mode": "round", "digits": 1}},
    {"key": "f2", "kind": "calculated", "label": "f2 — similarity factor",
     "expression": "50 * log10(100 / sqrt(1 + mean_sq_diff))",
     "rounding": {"mode": "round", "digits": 1}},
  ],
}
```

Criteria (reuse A7's advisory thresholds; "not similar" is a valid reportable outcome, so both are
advisory, not blocking):

```
{"key": "f2_similarity", "label": "f2 — similarity factor", "target": "comparison.f2",
 "operator": "gte", "limit": 50.0, "severity": "advisory", "limitText": "NLT 50 for similar profiles"},
{"key": "f1_difference", "label": "f1 — difference factor", "target": "comparison.f1",
 "operator": "lte", "limit": 15.0, "severity": "advisory", "limitText": "NMT 15 for similar profiles"},
```

If the expression engine turns out NOT to support the row-indexed cross-table difference series
cleanly, fall back to building the per-point `abs_diff` / `sq_diff` as CALCULATED columns ON the
`test_timepoints` table that read `reference_timepoints.mean[rowno - 1]` (the A6B pattern:
`...[rowno - 1]`), then `sum(test_timepoints.abs_diff)` / `sum(test_timepoints.sq_diff)` in the
`comparison` singleton. This keeps the two tables as the data model while still producing f1/f2.

**If the user DECLINES f1/f2 (four sections only):** drop the `comparison` group and the two
criteria, and set `resultRef` to a stable existing field so the template still parses and can publish
— recommended `resultRef: "test_timepoints.mean"` (the first populated test-product mean). The
`test_every_template_has_a_resolvable_reportable_result` invariant requires a resolvable `resultRef`,
so it cannot be omitted.

---

## 8. Frontend — scoped side-by-side render for Sections 1 & 2

File: `d:\RD-instance\GIT\.worktrees\f1f2-calculations\frontend-react\src\features\test-templates\components\WorksheetForm.tsx`

Goal: Sections 1 (`test_product`) and 2 (`reference_product`) — both `singleton` groups — must render
SIDE BY SIDE in one responsive flex row, reusing the existing singleton field-grid rendering.
Sections 3 and 4 (the two `table` groups) and the `comparison` singleton fall through to the GENERIC
renderer UNCHANGED, stacked. The generic path must not change for any other template.

### 8a. Add the scoped flag (next to the existing flags, ~line 205)

Where `allowClearColumn` and `allowCumulativeVertical` are declared:
```ts
const allowSideBySideHeaders = detail.worksheet.template_code === 'TPL-A7-0003';
```

### 8b. Extract the singleton field-grid into a reusable renderer

Today the singleton render path is INLINE inside the `groups.map(...)` dispatch (the
`if (group.kind === 'singleton') { ...field grid... }` branch, excluding the `group.chart` sub-case).
Extract the field-grid body (the `<div className="grid">` with `editableFields.map` + `calculatedFields.map`)
into a small local helper, e.g.:
```ts
const renderSingletonFieldGrid = (group: GroupDef) => { /* the existing grid JSX */ };
```
and have the existing inline singleton branch call it, so behaviour for every other template is
byte-identical. This is the "reuse the existing singleton field-grid rendering" requirement.

### 8c. Side-by-side branch in the `groups.map(...)` dispatch

At the TOP of the `groups.map((group) => { ... })` callback — in the same place the
`allowCumulativeVertical && group.key === 'timepoints_release'` early-return lives — add, BEFORE the
generic logic:

```ts
// TPL-A7-0003 only: render the Test Product + Reference Product singleton
// headers SIDE BY SIDE in one responsive row. Reached once (on test_product);
// reference_product is folded in here and skipped when the map reaches it.
if (allowSideBySideHeaders && group.key === 'test_product') {
  const refGroup = groups.find((g) => g.key === 'reference_product');
  return (
    <div className="flex flex-wrap gap-3" key="test_reference_headers">
      <div style={{ flex: '1 1 22rem', minWidth: 'min(22rem, 100%)' }}>
        <Card>
          {/* section header + toolbar, then renderSingletonFieldGrid(group) */}
        </Card>
      </div>
      {refGroup && (
        <div style={{ flex: '1 1 22rem', minWidth: 'min(22rem, 100%)' }}>
          <Card>
            {/* section header + toolbar, then renderSingletonFieldGrid(refGroup) */}
          </Card>
        </div>
      )}
    </div>
  );
}
if (allowSideBySideHeaders && group.key === 'reference_product') {
  return null; // already rendered beside test_product above
}
```

Notes:
- Each child uses `style={{ flex: '1 1 22rem', minWidth: 'min(22rem, 100%)' }}` inside a
  `className="flex flex-wrap gap-3"` wrapper — the exact responsive pattern the brief specifies
  (share width on wide screens; `flex-wrap` + `minWidth: min(22rem,100%)` stacks them vertically on
  narrow screens with no overlap/clipping).
- Reuse the existing `<Card>`, the section-header `<h3>` + `renderGroupToolbar(group)` block, and
  `renderSingletonFieldGrid(...)` so per-section Edit/Save/Delete and field inputs work exactly as the
  generic singleton. Do NOT re-implement input widgets.
- Returning `null` for `reference_product` is safe: React renders nothing for a `null` array element.
  (Confirm no sibling code assumes every group yields a non-null node; the `groups.map` output is
  rendered directly in the fragment, so `null` entries are fine.)
- Keep `allowCumulativeVertical`'s existing early-return intact; add these branches alongside it.

### 8d. Models/types

`GroupDef`, `FieldDef`, `GroupKind` in `testTemplate.types.ts` already cover `singleton` + `input`
fields of types `text` / `number` / `date`. No type changes needed. Use only PrimeFlex classes +
inline styles already used in this file — no new UI libraries.

---

## 9. Tests to add

Add `d:\RD-instance\GIT\.worktrees\f1f2-calculations\backend-v2\tests\calculation\test_a7_0003_f1f2_calculations.py`,
modelled on `test_a8_0004_cu30_parity.py` / `test_a6a_0005_leuprolide_parity.py`:

- Import `A7C_DEFINITION` (or load via `SEED_TEMPLATES` by code `TPL-A7-0003`), build a
  `WorksheetEvaluator`, and assert:
  - The four groups exist with the expected keys/kinds (`test_product`/`reference_product` singleton,
    `test_timepoints`/`reference_timepoints` table).
  - All twelve header fields are editable `input` fields with the expected types.
  - Empty evaluation runs without a blocking failure (parity with the catalogue invariant).
- **If §7 f1/f2 is wired:** feed a known pair of profiles and assert the exact f1/f2 the engine
  returns, DERIVED by hand from the formulas (do not copy a run). Use the A7 docstring's example
  profiles for a cross-check: reference means 9,23,41,58,89; test means 7,21,39,56,84 →
  f1 ≈ 5.9, f2 computed from the same inputs. Assert `comparison.f1` / `comparison.f2`.

The catalogue-wide invariants in `test_seeded_template_parity.py` (codes unique, parses/runs empty,
resolvable reportable result, no unfillable context, area fields discoverable) automatically cover
`TPL-A7-0003`; they are the primary regression gate.

---

## 10. Implementation items (ordered, each independently verifiable)

- [ ] 1. Create the seed module `a7_f1f2_calculations.py` with the four groups (Sections 1–4) and,
      per the §7 recommendation, the fifth `comparison` group + f1/f2 criteria; define the
      `A7C` SeedTemplate and `TEMPLATES = [A7C]`.
      Files: `backend-v2\scripts\template_definitions\a7_f1f2_calculations.py`
      Verify: from `backend-v2`, run `python -m scripts.seed_test_templates --validate-only` — expect
      a line `ok   TPL-A7-0003 [A7] ...` and "All definitions valid." (exit 0, nothing written).

- [ ] 2. Register the module in `__init__.py` (import `_A7C`, splice `*_A7C,` after `*_A7,`).
      Files: `backend-v2\scripts\template_definitions\__init__.py`
      Verify: re-run `python -m scripts.seed_test_templates --validate-only` — `TPL-A7-0003` now
      appears in the validated list; exit 0.

- [ ] 3. Add the backend parity/structure test for TPL-A7-0003 (§9).
      Files: `backend-v2\tests\calculation\test_a7_0003_f1f2_calculations.py`
      Verify: from `backend-v2`, `python -m pytest tests/calculation/test_a7_0003_f1f2_calculations.py tests/calculation/test_seeded_template_parity.py -q`
      — all pass (new test + catalogue invariants now covering TPL-A7-0003).

- [ ] 4. Back up `lims.db` (if present) then seed additively (idempotent).
      Files: none (DB only; `lims.db` is gitignored).
      Verify: from `backend-v2`, back up first:
      `Copy-Item lims.db "lims.db.bak-f1f2calc-$(Get-Date -Format 'yyyyMMdd-HHmmss')"` (only if
      `lims.db` exists), then `python -m scripts.seed_test_templates` — expect
      `add  TPL-A7-0003 [A7] Dissolution F1-F2-calculations -> TST-F1F2CALC` and
      `+ Test Master: TST-F1F2CALC — ...`; all others `skip`. Re-run once: expect
      `skip TPL-A7-0003 — already present` (idempotency).

- [ ] 5. Frontend: add the `allowSideBySideHeaders` flag, extract `renderSingletonFieldGrid`, and add
      the side-by-side branch (render both headers on `test_product`, return `null` for
      `reference_product`) per §8. Leave the generic path and the two timepoint tables unchanged.
      Files: `frontend-react\src\features\test-templates\components\WorksheetForm.tsx`
      Verify: from `frontend-react`, `npm run build` (`tsc -b && vite build`) — no TS errors, build
      succeeds; then `npm run lint` — no new eslint errors in `WorksheetForm.tsx`.

- [ ] 6. Runtime browser check (MANDATORY — layout cannot be verified from code alone).
      Files: none.
      Verify: start the stack (repo `start-lims.bat`, or `uvicorn` + `vite dev` per dev setup). Open
      or create a worksheet on a TRF test line bound to `TST-F1F2CALC` (template `TPL-A7-0003`) and
      confirm: (a) "Test Product" and "Reference Product" render SIDE BY SIDE and share the window
      width on a wide screen; (b) each block shows all six fields (Product Name, Batch No., Date of
      Analysis, Media, RPM, Volume) and each is independently editable; (c) resizing wide→narrow
      auto-fits then stacks the two blocks vertically with NO overlap/clipping; (d) Sections 3 and 4
      render as two stacked repeating timepoint tables; (e) if f1/f2 is wired, the comparison section
      shows f1/f2. Capture a screenshot of the resized layout as evidence.

---

## 11. lims.db backup convention

Before ANY seeding write to the database, make a timestamped copy in `backend-v2\`:
`lims.db.bak-f1f2calc-<yyyymmdd-HHMMSS>` (PowerShell: `Copy-Item lims.db "lims.db.bak-f1f2calc-$(Get-Date -Format 'yyyyMMdd-HHmmss')"`).
This matches the repo convention (`lims.db.bak-*`) and the worklog note. `lims.db` and its backups are
gitignored — never commit them; commit only source (new seed module, the `__init__.py` line, the
frontend render, the new test).

---

## 12. Gaps / assumptions

- **f1/f2 wiring is a RECOMMENDATION, not a settled decision** (§7). The plan wires it as the fifth
  `comparison` group with `resultRef → comparison.f2`, but the orchestrator must relay the
  recommendation to the user. If declined, drop the `comparison` group + its two criteria and set
  `resultRef: "test_timepoints.mean"` (§7 fallback). This is the ONE item genuinely open to the user.
- **Exact f1/f2 expression syntax** (indexed cross-table refs vs. the A6B `[rowno - 1]` calculated-
  column fallback) must be confirmed against `expression.py` / `evaluator.py` during implementation
  (§7). Both approaches are viable; the implementer picks whichever the engine supports most cleanly,
  preferring the calculated-column-on-`test_timepoints` fallback if indexed aggregates are awkward.
- **Row alignment for f1/f2** assumes the analyst enters the SAME time points, in the same order, in
  both tables (the two tables are independent, unlike TPL-A7-0002 which guaranteed this structurally).
  `n_points` uses the MIN of the two row counts so a mismatch cannot index past the shorter table.
  If the lab needs a "same time points" validity check, that is a follow-up criterion — out of scope
  for this first cut.
- **Header fields are `input`, not `context`** (§5), deliberately, so the two product blocks are
  independently editable. No TRF auto-sourcing of these six fields.
- **Runtime check environment** assumes the standard dev stack starts cleanly and a `TST-F1F2CALC`
  TRF line can be created (the template seeds Active and is immediately selectable).

---

## 13. Why no workflow-tail restructuring (FEAT decomposition)

This task is a single coherent unit of work: one new seed module, one `__init__.py` line, one scoped
frontend render, and one test file — all bound together by the single template code `TPL-A7-0003`.
The backend and frontend changes are not independently shippable (the frontend render is meaningless
without the seeded template, and vice versa), so splitting into separate FEATs would create artificial
seams rather than genuinely separable features. Per the decomposition guidance (prefer fewer/larger
units; only decompose when the work genuinely separates), this stays a single `plan.md` and the
workflow's existing implement-and-review loop runs it — matching how the sibling TPL-A7-0002 task was
structured.
