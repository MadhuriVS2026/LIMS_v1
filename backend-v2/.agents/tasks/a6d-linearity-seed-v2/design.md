# TPL-A6D-0002 — pre-filled "Standard Tapinarof for Linearity" table (OPTION ii) + eleven baked-in Additional-Info defaults

Technical design for two additions to the EXISTING Draft template **TPL-A6D-0002**
(id=43, version 1, archetype `A6d`, test_id=25 / `TST-IVRT`, status `Draft`,
result_unit `µg/cm²/√h`, resultRef `flux.mean_flux`). TPL-A6D-0001 (id=26, Active)
is **not** touched. `lims.db` is the source of truth; the live definition was read
firsthand for this design (see Evidence).

This design **supersedes** the earlier `a6d-linearity-addlinfo/design.md` on two
points:

1. **Addition 1 is now OPTION (ii): the nine linearity rows pre-fill.** The earlier
   design chose option (i) "nine blank rows, analyst-entered" and explicitly proved
   there was no per-row seed mechanism. The user has since chosen OPTION (ii): the
   nine fixed **Calibration curve** labels and their **Concentration (%)** values
   MUST be present when a worksheet opens. This design introduces the least-invasive
   engine capability that actually delivers that, grounded in firsthand code.
2. **Addition 2 grew from ten to eleven fields** (Date of Analysis added) and the
   user chose option (a): **bake all eleven in as fixed field defaults that override
   any TRF auto-fetch**, not auto-fetch. The acceptance criterion is **rendering**:
   all eleven must be visible and pre-filled on a worksheet, exactly like the
   existing left-column values render.

---

## Summary

- **Addition 1 (engine + schema + frontend, source code — committable but do not
  commit unless asked).** Add one `sequence` group `linearity` ("Standard Tapinarof
  for Linearity", 8 columns, add-row), and give it a **per-row seed** so it opens
  pre-filled with nine rows whose `calibration_curve` label and `concentration_pct`
  are seeded; the other six columns open blank. Because no existing mechanism
  pre-populates distinct per-row content (verified — see Decision A), a new,
  additive `rows.seed` capability is introduced: parsed by `template_schema.py`
  (`RowSpec`), stored in the TPL-A6D-0002 definition JSON in `lims.db`, consumed by
  `WorksheetService.create_worksheet` to seed `group_values["linearity"]`, returned
  verbatim in the worksheet API response, and rendered by the existing
  `WorksheetForm.tsx` row builder with **no frontend change required** (the form
  already seeds rows from stored `group_values` before falling back to
  `field.default`).

- **Addition 2 (definition only, no engine change).** Make all eleven Additional-Info
  values fixed `FieldDef.default`s on the template's `context[]`. Six map to context
  keys that already exist (`date_of_analysis`, `potency`, `temperature_c`,
  `donor_area`, `batch_no`, plus the data point behind an existing key); five are new
  context fields. For every one of the eleven, the stored value is a fixed `default`
  and — critically — any `source` that would otherwise override the default at seed
  time is **removed**, so the baked default is what seeds and renders. This needs no
  code change: `FieldDef.default` is a single value per field, `_seed_context` already
  copies defaults into `context_values` at creation, and `WorksheetForm.tsx` already
  renders every context field's value the same way the current left-column values
  render.

Both additions are purely additive to existing groups/fields; `resultRef` stays
`flux.mean_flux`; no existing expression references either addition.

---

## Evidence (read firsthand for this design)

### Live TPL-A6D-0002 (id=43), read from `lims.db`

```
META (43, 'TPL-A6D-0002', 1, 'Draft', 'A6d', 25, 'µg/cm²/√h', 'In-Vitro Release (Franz Diffusion Cell) — with Sampling Details')
TOPKEYS ['resultRef', 'context', 'groups', 'criteria']
RESULTREF flux.mean_flux
GROUPS ['calibration', 'curve', 'qc', 'cells', 'sampling_details', 'timepoints', 'flux']
CONTEXT COUNT 17
```

Context fields (key | source | default | overridable | type | unit | label):

| key | source | default | overridable | type | unit | label |
|---|---|---|---|---|---|---|
| `generic_name` | `product.name` | — | — | text | — | Generic Name |
| `batch_no` | `trf.batch_number` | — | — | text | — | Batch No. |
| `label_claim` | `trf.label_claim_numeric` | — | yes | number | — | Label Claim |
| `potency` | — | 100 | yes | — | % | Standard Potency |
| `membrane` | — | — | yes | text | — | Membrane Type / Make |
| `membrane_lot` | — | — | yes | text | — | Membrane B. No. |
| `receptor_media` | — | — | yes | text | — | Receptor Media |
| `receptor_volume` | — | 7 | yes | — | mL | Total Receptor Volume |
| `replacement_volume` | — | 1 | yes | — | mL | Media Replacement Volume |
| `sample_pip` | — | 1 | yes | — | mL | Withdrawn Aliquot |
| `sample_vol` | — | 1 | yes | — | mL | Diluted to |
| `donor_area` | — | 1.76 | yes | — | cm² | Donor Chamber Area |
| `temperature_c` | — | 32 | yes | — | °C | Temperature |
| `method_no` | — | — | yes | text | — | Method No. |
| `instrument_id` | — | — | yes | text | — | Instrument ID |
| `analysed_by` | `session.analyst` | — | — | text | — | Analysed By |
| `date_of_analysis` | `session.date` | — | — | date | — | Date of Analysis |

Rows-spec precedents (read firsthand):

```
calibration table    {'min': 2, 'max': 10, 'default': 6,  'labelFrom': 'level'}
qc          table    {'min': 0, 'max': 24, 'default': 6,  'labelFrom': 'level'}
timepoints  sequence {'min': 2, 'max': 12, 'default': 6,  'labelFrom': 'time_min'}
```

There is **no `additional_info` group**; the "Additional Info" header renders from
the flat `context[]` list (confirmed — top-level keys are exactly
`resultRef, context, groups, criteria`).

### `template_schema.py` — `RowSpec` and `FieldDef` (quoted)

`RowSpec` currently carries only counts and a label source:

```python
@dataclass(frozen=True)
class RowSpec:
    min: int = 1
    max: int = 1
    default: int = 1
    #  Rows may be labelled from one of their own fields (e.g. analyte name).
    label_from: str | None = None

    @classmethod
    def parse(cls, raw: dict | None, where: str) -> "RowSpec":
        if not raw:
            return cls()
        min_ = raw.get("min", 1)
        max_ = raw.get("max", min_)
        default = raw.get("default", min_)
        ...
        return cls(min=min_, max=max_, default=default, label_from=raw.get("labelFrom"))
```

`FieldDef.default` is a single scalar applied uniformly:

```python
default=raw.get("default"),
```

`GroupDef.parse` rejects duplicate field keys and validates `labelFrom ∈ fields`
(so `ml_a`/`ml_b`, `diluted_to_ml_1`/`diluted_to_ml_2` must be distinct keys).

### `evaluator.py` — `_seed_rows` (quoted): proves `FieldDef.default` is uniform-per-row

```python
for i in range(count):
    source = stored[i] if i < len(stored) else {}
    row: dict[str, Any] = {}
    for f in group.fields:
        if f.kind is FieldKind.CALCULATED:
            row[f.key] = EMPTY
            continue
        if f.key in source and source[f.key] is not None:
            row[f.key] = source[f.key]
        elif f.default is not None:
            row[f.key] = f.default           # same default for every row i
        else:
            row[f.key] = EMPTY
    rows.append(row)
```

A6D sibling seed modules state the same limitation in prose, e.g.
`scripts/template_definitions/a2_ampho_lipid_content.py`:

> "the per-row values are entered on the worksheet … a single field-level `default`
> cannot differ per row"

### `worksheet_service.py` — `create_worksheet` and `_seed_context` (quoted)

`create_worksheet` seeds context from the TRF but leaves group rows empty:

```python
definition = self._parse(template)
product = await self._product_repo.get_by_id(trf.product_id)
context_values = self._seed_context(definition, trf, line, product, actor)

worksheet = TestWorksheet(
    ...
    context_values=context_values,
    group_values={},                 # <-- no per-row group content at creation
    ...
)
```

`_seed_context` (default applies when source is absent or unresolved):

```python
seeded: dict[str, Any] = {}
for cf in definition.context:
    value = available.get(cf.source) if cf.source else None
    if value is None:
        value = cf.default
    if value is not None:
        seeded[cf.key] = value
return seeded
```

The two facts that drive Addition 2's "remove the source" rule:
`session.date` / `trf.batch_number` / `trf.label_claim_numeric` always resolve to a
**non-None** live value, so `value is None` is false and `cf.default` is **never**
reached for a source-backed field. A baked default therefore only takes effect if
the competing `source` is removed from that field.

Also confirmed present verbatim in the `available` map: `trf.trf_number`,
`trf.ar_number`, `trf.batch_number`, `session.date` — and **absent**:
`trf.expiry_or_retest_date`, any "working standard" or "potency" key. (This is why
Addition 2 uses fixed defaults, not sources — the user's chosen option (a) and the
only way to pin exact values like 99.67 / 06 April 2026 regardless of the TRF.)

### `worksheet_endpoints.py` + `test_template_schemas.py` — API returns stored rows verbatim

`WorksheetResponse` serializes the worksheet's stored dicts directly:

```python
context_values: dict[str, Any] = {}
group_values: dict[str, list[dict[str, Any]]] = {}
```

and `WorksheetDetailResponse` carries `worksheet` + `template` (with `definition`) +
`computed`. So whatever `create_worksheet` writes into `group_values["linearity"]`
is returned to the frontend as-is.

### `WorksheetForm.tsx` — row builder prefers stored rows, then `field.default`

```typescript
function rowCount(group: GroupDef, stored: WorksheetRow[] | undefined): number {
  if (group.kind === 'singleton') return 1;
  if (stored && stored.length) return stored.length;          // stored rows win
  return group.rows?.default ?? group.rows?.min ?? 1;
}

function seedValues(detail: WorksheetDetail): Values {
  ...
  const stored = detail.worksheet.group_values?.[group.key];
  const count = rowCount(group, stored);
  out[group.key] = Array.from({ length: count }, (_, i) => {
    const source = stored?.[i] ?? {};
    ...
    row[field.key] =
      source[field.key] !== undefined && source[field.key] !== null
        ? source[field.key]                                   // stored cell wins
        : (field.default ?? null);                            // else uniform default
  });
  ...
}
```

And every **context** field renders its value through one path (the "Additional Info"
header is this grid — there is no separate left/right column code; the user's
"right column" is simply fields that currently resolve to blank):

```typescript
const stored = detail.worksheet.context_values?.[field.key];
const current = contextValues[field.key] ?? stored;
...
<span className="text-sm font-medium">
  {current === null || current === undefined || current === '' ? '—' : String(current)}
</span>
```

**This is the render path the task asks Addition 2 to match.** The existing
left-column values (Total media volume `7`, Donor area `1.76`, Temperature `32`, …)
are visible **because** they carry a `default` (or a resolvable `source`) that
`_seed_context` copies into `context_values`, which this `<span>` then prints. A
field that renders `—` does so only because `context_values[key]` is empty. Giving
each of the eleven a fixed `default` (and removing any competing source) makes
`current` non-empty for all eleven, so all eleven render identically to the left
column. No frontend change for Addition 2.

---

## Decision A — the per-row seeding mechanism (Addition 1, OPTION ii)

### Is there an existing precedent? No.

I searched the engine, seed modules, and frontend for any per-row seed
(`seed`, `seedRows`, `rowSeed`, `rows.seed`, `prefill`). The only hits are
`evaluator._seed_rows` (uniform `field.default`), `seed_project_master.py`
(unrelated DB seeding of the product master), and the a2 module comment that
explicitly says per-row values are analyst-entered because a field default cannot
differ per row. **No existing template or mechanism pre-populates specific sequence
rows with distinct content.** A new capability is therefore required; I introduce
the candidate from the task (`rows.seed`) because nothing to follow exists.

### Why the seed must live on the backend creation path (not frontend-only, not `field.default`)

- `field.default` is rejected: it is one value for all rows (quoted `_seed_rows`
  and `seedValues`), so it cannot carry nine distinct labels/concentrations.
- A frontend-only prefill is rejected: the row builder's stored-rows branch wins
  (`if (stored && stored.length) return stored.length`), and once the analyst saves,
  `save_values` persists exactly the rows the form holds. If the nine rows existed
  only as a frontend constant and were never in stored `group_values`, the first
  save would be fine, but a freshly created worksheet's `group_values["linearity"]`
  would be `[]` until the form re-seeded — fragile, template-specific branching in a
  deliberately generic component, and invisible to the API/evaluator. Rejected.
- Seeding real rows into `group_values["linearity"]` **at `create_worksheet`** is the
  least-invasive choice that actually works end to end: it reuses the exact same
  persistence slot that `context_values` already uses, the rows are then stored,
  returned by the API, rendered by the **unchanged** frontend (stored-rows branch),
  survive save/preview/evaluate, and appear in audit/COA like any analyst data.

### The mechanism: `rows.seed` — an additive, generic per-row seed list

Add an **optional** `seed` to the rows spec: a list of row objects, each a
`{fieldKey: value}` map, applied to the first N opening rows (N = len(seed)).
It is generic (any template, any sequence/table group), additive (absent `seed`
behaves exactly as today), and changes three source files.

Definition JSON shape (stored in `lims.db` on TPL-A6D-0002):

```json
"rows": {
  "min": 9, "max": 15, "default": 9, "labelFrom": "calibration_curve",
  "seed": [
    { "calibration_curve": "Calibration standard-1", "concentration_pct": 1 },
    { "calibration_curve": "Calibration standard-2", "concentration_pct": 5 },
    { "calibration_curve": "Calibration standard-3", "concentration_pct": 15 },
    { "calibration_curve": "Calibration standard-4", "concentration_pct": 30 },
    { "calibration_curve": "Calibration standard-5", "concentration_pct": 40 },
    { "calibration_curve": "Calibration standard-6", "concentration_pct": 60 },
    { "calibration_curve": "LQC", "concentration_pct": 1 },
    { "calibration_curve": "MQC", "concentration_pct": 15 },
    { "calibration_curve": "HQC", "concentration_pct": 30 }
  ]
}
```

Only `calibration_curve` and `concentration_pct` are seeded per row; the other six
columns are omitted from each seed map and therefore open blank.

#### Code change 1 — `template_schema.py` `RowSpec` (parse + carry the seed)

Add a `seed` field to `RowSpec` and parse+validate it. Exact change:

```python
@dataclass(frozen=True)
class RowSpec:
    min: int = 1
    max: int = 1
    default: int = 1
    label_from: str | None = None
    seed: tuple[dict[str, Any], ...] = ()      # NEW: per-row opening values

    @classmethod
    def parse(cls, raw: dict | None, where: str) -> "RowSpec":
        if not raw:
            return cls()
        min_ = raw.get("min", 1)
        max_ = raw.get("max", min_)
        default = raw.get("default", min_)
        # ... existing int + ordering validation unchanged ...
        raw_seed = raw.get("seed") or []
        if not isinstance(raw_seed, list):
            raise TemplateSchemaError(f"{where}.rows.seed must be a list")
        for i, r in enumerate(raw_seed):
            if not isinstance(r, dict):
                raise TemplateSchemaError(f"{where}.rows.seed[{i}] must be an object")
        if len(raw_seed) > max_:
            raise TemplateSchemaError(
                f"{where}.rows.seed has {len(raw_seed)} rows, exceeding max ({max_})"
            )
        seed = tuple(dict(r) for r in raw_seed)
        return cls(min=min_, max=max_, default=default,
                   label_from=raw.get("labelFrom"), seed=seed)
```

`GroupDef.parse` must additionally validate that every key used in any seed row is a
real field of the group (fail loudly, matching the schema's "malformed definition
fails at load time" contract). Add, right after the existing `labelFrom ∈ fields`
check in `GroupDef.parse`:

```python
field_keys = seen  # already the set of this group's field keys
for i, seed_row in enumerate(rows.seed):
    bad = set(seed_row) - field_keys
    if bad:
        raise TemplateSchemaError(
            f"{where}: group {key!r} rows.seed[{i}] names unknown field(s) {sorted(bad)}"
        )
```

`RowSpec` is frozen and `seed` holds plain dicts; because it is a dataclass default
of `()`, every existing template parses unchanged. **Invariant ownership:** the
schema layer owns structural validity of `seed` (list of objects, within `max`, keys
exist) — the one place a malformed definition can be rejected before any worksheet is
created.

#### Code change 2 — `worksheet_service.py` `create_worksheet` (seed the stored rows)

After `context_values = self._seed_context(...)`, build `group_values` from any group
whose rows spec carries a seed, then pass it instead of `{}`. New helper mirrors the
style of `_seed_context`:

```python
context_values = self._seed_context(definition, trf, line, product, actor)
group_values = self._seed_group_rows(definition)       # NEW

worksheet = TestWorksheet(
    ...
    context_values=context_values,
    group_values=group_values,          # was {}
    ...
)
```

```python
@staticmethod
def _seed_group_rows(definition: TemplateDefinition) -> dict[str, list[dict[str, Any]]]:
    """Pre-populate the opening rows of any group whose rows spec declares a
    `seed`. Each seed entry is one row's starting values; unseeded columns are
    left out (the frontend row builder and evaluator fill them blank). Groups
    without a seed are omitted entirely, preserving today's empty-rows behavior."""
    seeded: dict[str, list[dict[str, Any]]] = {}
    for group in definition.groups:
        if group.rows.seed:
            seeded[group.key] = [dict(r) for r in group.rows.seed]
    return seeded
```

This is the single functional seam. `group_values={}` → seeded dict. Everything
downstream (`save_values`, `preview`, `_evaluate`, `_filter_groups`, audit) already
handles a populated `group_values`, because that is the normal post-entry state.

**Draft-template caveat (unchanged):** `create_worksheet` still rejects non-Active
templates (`if not template.is_selectable: raise …`; `is_selectable == status ==
ACTIVE`). TPL-A6D-0002 is Draft, so the live proof of nine seeded rows runs only
after the template is promoted to Active (see Proof plan). The pure seeding logic is
independently unit-testable without creating a worksheet (see Testability).

**Edit-level invariant ownership.** The seed defines *opening* values only; once the
analyst edits and saves, the stored rows are authoritative and the seed is never
re-applied (seeding happens exactly once, at creation). `save_values`/`_filter_groups`
own the entered rows thereafter. This matches how `context_values` defaults behave.

#### Code change 3 — frontend: none required (verify only)

The row builder already prefers stored rows (`rowCount` → `if (stored && stored.length)`;
`seedValues` → `source[field.key] ?? field.default`). Because `create_worksheet` now
stores nine rows under `group_values["linearity"]`, the form renders nine rows with
the seeded `calibration_curve`/`concentration_pct` cells filled and the rest blank,
with the add/remove-row control bounded by `min:9`/`max:15`. No `WorksheetForm.tsx`
edit is needed; this is a **verify-the-render** step, not a code change. (If a later
review finds the generic builder does not surface a seeded cell, the fix stays in the
generic path — never a `template_code ===` special case.)

### End-to-end trace (Addition 1)

1. **Definition JSON** — TPL-A6D-0002 `groups[]` gains the `linearity` group with
   `rows.seed` (nine maps). Written to `lims.db` row id=43 by a one-off author script
   following `_apply_a6d_sampling_details.py` (read-live → deepcopy → two-pass
   validate → write id=43 → byte-equal re-read).
2. **Parse** — `TemplateDefinition.parse` → `GroupDef.parse` → `RowSpec.parse` reads
   `seed` into `RowSpec.seed`; `GroupDef.parse` validates the seed keys exist.
3. **DB** — the `seed` list persists inside the stored `definition` JSON on id=43.
4. **create_worksheet seeding** — `_seed_group_rows(definition)` emits
   `{"linearity": [ {calibration_curve, concentration_pct}, ×9 ]}` into
   `worksheet.group_values` (runs once the template is Active).
5. **API response** — `WorksheetResponse.group_values` serializes those nine rows
   verbatim in `WorksheetDetailResponse.worksheet`.
6. **Frontend render** — `seedValues`/`rowCount` take the stored-rows branch: nine
   rows render, `calibration_curve` and `concentration_pct` pre-filled, other six
   columns blank, add/remove bounded by `{min:9, max:15}`.

### Specific functions/lines that must change (Addition 1)

- `src/domain/services/calculation/template_schema.py`: `RowSpec` dataclass
  (add `seed` field) and `RowSpec.parse` (parse+validate `seed`); `GroupDef.parse`
  (validate seed keys ∈ group fields).
- `src/application/services/worksheet_service.py`: `create_worksheet`
  (`group_values={}` → `group_values = self._seed_group_rows(definition)`) and a new
  static `_seed_group_rows`.
- `frontend-react/.../WorksheetForm.tsx`: **no change** (verify render only).
- `lims.db` row id=43 `definition`: add the `linearity` group with `rows.seed`
  (data edit, gitignored; applied by the author script).

> **Assumption (stated per instructions):** the `TestWorksheet` entity / its
> persistence accepts a non-empty `group_values` at construction exactly as it
> accepts it from `save_values` (the normal post-entry state). This is consistent
> with `save_values` storing arbitrary `group_values`, but the implementer must
> confirm `TestWorksheet.__init__`/the repo mapper persists a creation-time
> `group_values` round-trip (it already persists `context_values` at creation). If
> for any reason construction-time `group_values` are dropped, the fallback is to
> call the same seeding right after `create` via `set_values`, or to seed in the
> repository's create mapper — same data, same trace, one layer lower.

---

## Addition 1 — exact linearity group definition JSON

Insert into `definition["groups"]` **immediately after `qc` and before `cells`**
(companion to `calibration`/`qc`; presentation-only — no expression references it,
so placement does not affect calculation).

```json
{
  "key": "linearity",
  "kind": "sequence",
  "label": "Standard Tapinarof for Linearity",
  "rows": {
    "min": 9,
    "max": 15,
    "default": 9,
    "labelFrom": "calibration_curve",
    "seed": [
      { "calibration_curve": "Calibration standard-1", "concentration_pct": 1 },
      { "calibration_curve": "Calibration standard-2", "concentration_pct": 5 },
      { "calibration_curve": "Calibration standard-3", "concentration_pct": 15 },
      { "calibration_curve": "Calibration standard-4", "concentration_pct": 30 },
      { "calibration_curve": "Calibration standard-5", "concentration_pct": 40 },
      { "calibration_curve": "Calibration standard-6", "concentration_pct": 60 },
      { "calibration_curve": "LQC", "concentration_pct": 1 },
      { "calibration_curve": "MQC", "concentration_pct": 15 },
      { "calibration_curve": "HQC", "concentration_pct": 30 }
    ]
  },
  "fields": [
    { "key": "calibration_curve", "kind": "input", "type": "text",   "label": "Calibration curve" },
    { "key": "concentration_pct", "kind": "input", "type": "number", "label": "Concentration", "unit": "%" },
    { "key": "std_weight_mg",     "kind": "input", "type": "number", "label": "Standard Weight", "unit": "mg" },
    { "key": "diluted_to_ml_1",   "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL" },
    { "key": "ml_a",              "kind": "input", "type": "number", "label": "mL", "unit": "mL" },
    { "key": "ml_b",              "kind": "input", "type": "number", "label": "mL", "unit": "mL" },
    { "key": "ml_taken",          "kind": "input", "type": "number", "label": "mL taken", "unit": "mL" },
    { "key": "diluted_to_ml_2",   "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL" }
  ]
}
```

Column → field mapping (user's 8-column order preserved):

| # | User column header | field key | type | unit | opens |
|---|---|---|---|---|---|
| 1 | Calibration curve | `calibration_curve` | text | — | **seeded** per row (nine labels); `labelFrom` target |
| 2 | Concentration (%) | `concentration_pct` | number | % | **seeded** per row (1,5,15,30,40,60,1,15,30) |
| 3 | Standard Weight in mg | `std_weight_mg` | number | mg | blank; entered once per block (Decision C) |
| 4 | Diluted to (mL) | `diluted_to_ml_1` | number | mL | blank; entered once per block (Decision C) |
| 5 | mL | `ml_a` | number | mL | blank reusable input |
| 6 | mL | `ml_b` | number | mL | blank reusable input |
| 7 | mL taken | `ml_taken` | number | mL | blank reusable input |
| 8 | Diluted to (mL) | `diluted_to_ml_2` | number | mL | blank reusable input |

Two columns headed "mL" (5,6) and two "Diluted to (mL)" (4,8) are disambiguated as
`ml_a`/`ml_b` and `diluted_to_ml_1`/`diluted_to_ml_2` (both pairs keep the display
label but need unique keys — `GroupDef.parse` rejects duplicates).

**Rows spec rationale** (follows the `timepoints` sequence precedent):
`default:9` so the sheet opens with exactly the nine seeded rows; `min:9` so the nine
mandated standards/QCs cannot be deleted below the fixed set; `max:15` gives six
rows of headroom, matching the bounded style of `timepoints` (12) / `calibration`
(10); `labelFrom:"calibration_curve"` names column 1, as `calibration` uses `level`
and `timepoints` uses `time_min`. `kind:sequence` matches the named precedent the
task cites and leaves room for a future linearity regression (not in scope).

### Decision C — the two "entered once per block" columns

Columns 3 (`std_weight_mg`) and the first 4 (`diluted_to_ml_1`) are entered once per
block (calibration-standards block; QC block). The schema has **no merge / rowspan /
colspan primitive** — confirmed: `FieldDef` has no span attribute and `RowSpec` is
only `min/max/default/label_from/seed`. So these two columns stay ordinary blank
per-row inputs; by convention the analyst fills them only on the first row of each
block and leaves them blank beneath. They are deliberately **not** in the `seed`
maps (seeding them would pre-fill every block row, the opposite of "once per block").
Blank = "shared from the first row of this block, by convention." A true visual
rowspan would be a frontend-only follow-up and must not drive a schema invention.

The example weight/volume figures the user pasted (89.73, 50.0, 5.0, 50, 1.0, 15.0,
3.0, 4.0, 6.0, …) are **examples only** and appear nowhere in the stored definition
(`seed` carries labels + concentrations only).

---

## Addition 2 — exact Additional-Info field mapping (eleven baked-in defaults)

All eleven become fixed `FieldDef.default` values on `context[]`. Rule derived from
`_seed_context` (quoted): a baked default only seeds/renders if no competing `source`
resolves first, so for every field that currently has (or would have) a resolvable
source, the **source is removed** and replaced by the fixed default. This realises
the user's option (a): fixed defaults that override TRF auto-fetch.

Mapping of the eleven user values to context keys:

| # | User label | Value to bake | Context key | Pre-existing? | Action |
|---|---|---|---|---|---|
| 1 | Date of Analysis | `06 April 2026` | `date_of_analysis` | yes (source `session.date`, no default) | **Drop `source`**, set `default:"06 April 2026"`, `type:text`*, `overridable:true` |
| 2 | Working/reference standard number | `WS/25/079` | `working_std_no` | no | **Add** context text, `default:"WS/25/079"`, `overridable:true` |
| 3 | Use before date | `26-May` | `use_before_date` | no | **Add** context text, `default:"26-May"`, `overridable:true` |
| 4 | Potency(%) | `99.67` | `potency` | yes (default 100) | **Change default 100 → 99.67** (keep unit %, overridable) |
| 5 | Temperature (°C) | `32` | `temperature_c` | yes (default 32) | **Keep default 32** (already correct; unit °C, overridable) |
| 6 | Time points (Min) | `40, 80, 120, 160, 200, 240` | `time_points_min` | no | **Add** context text, `default:"40, 80, 120, 160, 200, 240"`, `overridable:true` |
| 7 | Average weight (mg) | `100` | `avg_weight_mg` | no | **Add** context number, unit mg, `default:100`, `overridable:true` |
| 8 | Batch No.: | `LE6001` | `batch_no` | yes (source `trf.batch_number`, no default) | **Drop `source`**, set `default:"LE6001"`, `overridable:true` |
| 9 | TRF number | `TRF-021-26-053` | `trf_number` | no | **Add** context text, `default:"TRF-021-26-053"`, `overridable:true` (no source — fixed) |
| 10 | A R No. | `AD/048/26/0121` | `ar_number` | no | **Add** context text, `default:"AD/048/26/0121"`, `overridable:true` (no source — fixed) |
| 11 | Surface Area of Donor chamber (cm²) | `1.76` | `donor_area` | yes (default 1.76) | **Keep default 1.76** (already correct; unit cm², overridable) |

\* **Date of Analysis as text, not `date`.** The user's literal value is
"06 April 2026", not an ISO date. The frontend renders a context value with bare
`String(current)`, and the editable input for `type:'date'` is a plain `InputText`
(no date coercion), so storing the human string `"06 April 2026"` as `type:text`
renders exactly as written. Keeping `type:date` with a non-ISO default would still
render the string but is semantically misleading; `type:text` is chosen so the baked
default displays verbatim. (Dropping the `session.date` source is mandatory either
way — otherwise today's date always wins over the default.)

**Net changes to `context[]`:**

- **Modify 4 existing fields:** `date_of_analysis` (drop source, add default, set
  text, overridable), `batch_no` (drop source, add default, overridable), `potency`
  (default 100 → 99.67), `donor_area` (unchanged value — already 1.76; listed for
  completeness, no edit needed but assert it equals 1.76). `temperature_c` likewise
  already 32 — assert, no edit needed.
- **Add 5 new fields:** `working_std_no`, `use_before_date`, `time_points_min`,
  `avg_weight_mg`, `trf_number`, `ar_number` — that is **six** new keys. (Five of the
  eleven map to existing keys: `date_of_analysis`, `potency`, `temperature_c`,
  `donor_area`, `batch_no`; the remaining six are new: the four manual + `trf_number`
  + `ar_number`.)

Exact new/changed field JSON (append the six new ones after `date_of_analysis`;
modify the existing ones in place):

```json
// modified in place
{ "key": "date_of_analysis", "kind": "context", "type": "text", "label": "Date of Analysis", "default": "06 April 2026", "overridable": true }
{ "key": "batch_no", "kind": "context", "type": "text", "label": "Batch No.", "default": "LE6001", "overridable": true }
{ "key": "potency", "kind": "context", "unit": "%", "label": "Standard Potency", "default": 99.67, "overridable": true }
// (temperature_c default stays 32; donor_area default stays 1.76 — no edit, assert only)

// new
{ "key": "working_std_no",  "kind": "context", "type": "text",   "label": "Working / Reference Standard No.", "default": "WS/25/079",             "overridable": true },
{ "key": "use_before_date", "kind": "context", "type": "text",   "label": "Use Before Date",                  "default": "26-May",                "overridable": true },
{ "key": "time_points_min", "kind": "context", "type": "text",   "label": "Time Points (Min)",                "default": "40, 80, 120, 160, 200, 240", "overridable": true },
{ "key": "avg_weight_mg",   "kind": "context", "type": "number", "unit": "mg", "label": "Average Weight",      "default": 100,                     "overridable": true },
{ "key": "trf_number",      "kind": "context", "type": "text",   "label": "TRF Number",                       "default": "TRF-021-26-053",        "overridable": true },
{ "key": "ar_number",       "kind": "context", "type": "text",   "label": "A.R. No.",                         "default": "AD/048/26/0121",        "overridable": true }
```

The canonical six new keys are `working_std_no`, `use_before_date`, `time_points_min`,
`avg_weight_mg`, `trf_number`, `ar_number`. Time Points is a free-text list, so
`type:text` with the unit folded into the label ("Time Points (Min)") — per the prior
review's NIT #3 that a `unit` on a free-text field renders oddly.

All six new fields are `overridable:true` — required by the documented `_common.py`
invariant ("a context field with neither a resolvable source nor a default renders as
a permanently-blank read-only box"); here they also all carry a default, so they
render pre-filled **and** stay editable, matching the existing overridable
left-column fields (potency, temperature, etc.).

### Why this makes all eleven VISIBLE (the actual acceptance criterion)

The user reported the values "still not viewing on the UI" because nothing was
written yet — the right-column fields either did not exist or had no default/source,
so the render `<span>` printed `—`. With this change, `_seed_context` copies each
field's `default` into `context_values` at `create_worksheet` (defaults are reached
because the competing sources on `date_of_analysis`/`batch_no` are removed), the API
returns `context_values`, and the **same** context render path that already displays
`7` / `1.76` / `32` for the left column now displays all eleven values. No frontend
change; Addition 2 is a definition-only edit.

### Addition 2 render trace

1. Definition JSON: six new/modified `context[]` fields with fixed `default`s and no
   overriding `source`. Written to id=43 by the author script.
2. Parse: `FieldDef.parse` reads each `default` (and `overridable`).
3. DB: stored in id=43 `definition`.
4. `create_worksheet` → `_seed_context`: `value = available.get(cf.source)` is
   `None` for every one of the eleven (no source, or source removed), so
   `value = cf.default`; each is copied into `context_values`.
5. API: `WorksheetResponse.context_values` carries all eleven.
6. Frontend: the Context grid renders each field's `current` value through the
   existing `<span>`/`InputText`/`InputNumber`, identical to the left-column fields.

---

## How Addition 2 reuses the prior analysis

Reused verbatim from `a6d-linearity-addlinfo/design.md` (re-verified firsthand here):

- The "Additional Info" header is the flat `context[]` list, not an `additional_info`
  group (A6D has none). Confirmed.
- The five already-present keys and their live defaults/sources
  (`date_of_analysis` src `session.date`; `potency` default 100; `temperature_c`
  default 32; `donor_area` default 1.76; `batch_no` src `trf.batch_number`) — reused;
  this design does **not** duplicate those keys, it edits them in place.
- The `_common.py` "source-or-overridable-or-blank-box" invariant — reused to justify
  `overridable:true` on the new fields.
- NIT #3 (unit on a free-text list field renders oddly) — adopted: Time Points is
  `type:text` with the unit in the label, no `unit` attribute.

Superseded from the prior analysis:

- The prior design mapped `trf_number`/`ar_number` to live **sources**
  (`trf.trf_number`/`trf.ar_number`) and `date_of_analysis` to `session.date`. The
  user's option (a) requires **fixed values that override auto-fetch**, so this design
  drops those sources and bakes literals instead. The verified fact that those source
  keys exist is now moot for these fields (we deliberately do not use them).
- The prior count was ten fields; this design handles eleven (Date of Analysis added).

---

## Runtime proof plan

Addition 1 (the nine seeded rows) cannot be proven by `create_worksheet` while
TPL-A6D-0002 is Draft (the Active-only guard). Proof is therefore split:

1. **Schema unit test (no DB, no worksheet).** Parse the edited definition with
   `TemplateDefinition.parse`; assert `linearity` group exists after `qc`/before
   `cells`, `rows == {min:9,max:15,default:9,labelFrom:"calibration_curve"}` and
   `RowSpec.seed` has nine entries with the exact nine label/concentration pairs; run
   `WorksheetEvaluator(parsed).evaluate({}, {})` → `has_blocking_failure is False`,
   `resultRef` still `flux.mean_flux`.

2. **Seeding unit test (no worksheet needed).** Call the new
   `WorksheetService._seed_group_rows(definition)` directly and assert it returns
   `{"linearity": [ … 9 rows … ]}` with row 0 `{"calibration_curve":"Calibration
   standard-1","concentration_pct":1}` … row 8 `{"calibration_curve":"HQC",
   "concentration_pct":30}`, and that the six unseeded columns are absent from each
   seed row. Assert a group without `rows.seed` yields no entry (today's behavior
   preserved).

3. **End-to-end render proof (requires an Active template).** Because the live app
   rejects `create_worksheet` on a Draft template, promote a copy to Active in a
   throwaway/dev DB (or temporarily set id=43 Active in a disposable DB copy — never
   the shipped Draft), create a worksheet for a `TST-IVRT` line, and assert the API
   `WorksheetDetailResponse.worksheet.group_values["linearity"]` contains the nine
   seeded rows and `context_values` contains all eleven baked values. Then load the
   worksheet in the UI (`start-lims.bat`, backend 127.0.0.1:8443, frontend 5174) and
   visually confirm: the "Standard Tapinarof for Linearity" table opens with nine
   rows, column 1 showing Calibration standard-1..6 / LQC / MQC / HQC and column 2
   showing 1/5/15/30/40/60/1/15/30, the other six columns blank, add/remove bounded
   9–15; and the Additional-Info header shows all eleven values pre-filled exactly as
   the left-column values render.

4. **Parity regression.** Run `tests/calculation/test_seeded_template_parity.py`; the
   result must match the recorded baseline (the three pre-existing `A6B` failures only)
   with no new failures — the `rows.seed` addition is additive and must not change any
   other template's evaluation.

The author script that writes id=43 validates with the two-pass gate
(`TemplateDefinition.parse` + `evaluate({}, {})`) and asserts a byte-equal re-read
before finishing, and makes a timestamped `lims.db` backup first (setup already
created `lims.db.bak-a6dlinearity2-20261027-122834`). These engine/schema edits are
source code and committable, but the implementation must **not** commit unless the
user later asks.

---

## Acceptance criteria

1. `template_schema.py` `RowSpec` gains a `seed: tuple[dict, ...]` field;
   `RowSpec.parse` parses `seed` (list of objects, length ≤ `max`) and `GroupDef.parse`
   rejects a seed row naming a non-field key. Absent `seed` parses exactly as before
   (every existing template unaffected).
2. `WorksheetService.create_worksheet` passes
   `group_values=self._seed_group_rows(definition)` instead of `{}`;
   `_seed_group_rows` returns one entry per group that declares `rows.seed`, each a
   list of that group's seed rows, and omits groups without a seed.
3. TPL-A6D-0002 (id=43) `definition.groups` contains a `sequence` group
   `key="linearity"`, label "Standard Tapinarof for Linearity", positioned after `qc`
   and before `cells`, with the eight fields in order and
   `rows={min:9,max:15,default:9,labelFrom:"calibration_curve",seed:[…9…]}`.
4. The nine seed rows carry exactly: `calibration_curve` ∈ {Calibration standard-1..6,
   LQC, MQC, HQC} and `concentration_pct` ∈ {1,5,15,30,40,60,1,15,30} respectively, and
   **no** other column (the six input columns are absent from every seed row and carry
   no `field.default`).
5. None of the example weight/volume figures (89.73, 50.0, 5.0, 50, 1.0, 15.0, 3.0,
   4.0, 6.0) appear anywhere in the stored definition.
6. `definition.context` has all eleven Additional-Info values as fixed defaults:
   `date_of_analysis`="06 April 2026" (no source, text), `working_std_no`="WS/25/079",
   `use_before_date`="26-May", `potency`=99.67, `temperature_c`=32,
   `time_points_min`="40, 80, 120, 160, 200, 240", `avg_weight_mg`=100,
   `batch_no`="LE6001" (no source), `trf_number`="TRF-021-26-053",
   `ar_number`="AD/048/26/0121", `donor_area`=1.76 — each present exactly once, all
   `overridable:true`, no competing `source` on any of the eleven.
7. No duplicate context keys; the five pre-existing keys are edited in place, not
   re-added; six new keys are added (`working_std_no`, `use_before_date`,
   `time_points_min`, `avg_weight_mg`, `trf_number`, `ar_number`).
8. `TemplateDefinition.parse(definition)` succeeds and
   `WorksheetEvaluator(parsed).evaluate({}, {})` → `has_blocking_failure == False`,
   `resultRef` still `flux.mean_flux`.
9. `_seed_group_rows(parsed)` returns `{"linearity": [9 rows]}` with the exact seeded
   labels/concentrations; `_seed_context(parsed, …)` returns a dict containing all
   eleven Additional-Info keys with the exact baked values.
10. On a worksheet created from an Active copy of the template: the API response's
    `group_values["linearity"]` has nine rows with the seeded cells filled, and
    `context_values` has all eleven values; the UI renders the nine linearity rows
    (col 1/2 pre-filled, other six blank) and all eleven Additional-Info values
    pre-filled, rendered the same way the existing left-column values render.
11. Row id=26 (TPL-A6D-0001) is byte-unchanged and still Active; id=43 keeps
    code/name/version/status(Draft)/test_id/archetype/result_unit; only `definition`
    changes. A `lims.db` backup exists before any write.
12. Parity suite matches baseline (only the pre-existing A6B failures; no new failure).

## Out of scope

- Any calculation on the linearity table (regression slope/intercept/r). No expression
  references `linearity`; `sequence` leaves room for a later regression if wanted.
- A true visual cell-merge/rowspan for columns 3–4 (frontend-only follow-up; the
  blank-non-first-row convention stands).
- Auto-fetch of any Additional-Info value from the TRF — explicitly rejected by the
  user's option (a); all eleven are fixed defaults.
- Committing any of the engine/schema/frontend edits or the `lims.db` change (do not
  commit unless the user later asks).

## Stated assumptions

- `TestWorksheet` construction persists a non-empty creation-time `group_values`
  round-trip (as it already does for `context_values`); if not, seed via `set_values`
  immediately after create or in the repository create mapper — same data/trace (see
  Decision A assumption note).
- The frontend generic row builder surfaces seeded cells without a per-template branch
  (it reads stored `group_values` first); confirmed by code inspection, to be
  re-verified in the live render proof.
- "06 April 2026" and "26-May" are stored as the literal strings the user supplied
  (`type:text`), rendered verbatim; no date normalization is applied.
