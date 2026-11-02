# Design — Merge the calibration/linearity tables of LIMS template id=43 (TPL-A6D-0002)

> **Revision 2 (design-review loop).** A `design-review.json` (verdict `CHANGES_REQUESTED`, 3 HIGH / 3 MEDIUM / 2 NIT) exists and has been read in full together with its `reviewDoc`. My responses to every finding are in **§8**. The headline disagreement is Finding 1/2: the review asks me to split the calibration maths into **two** tables. I have **not** adopted that, because it contradicts the authoritative original user request and the verbatim task for this step, both of which mandate **one single table**. The reasoning, and the downstream consequence (the regression-scoping engine capability the review wanted removed is in fact required under the one-table layout the user asked for), are set out in §8 Finding 1 and §2. All other findings (3–8) are valid independent of structure and are addressed.

## Status of inputs (evidence)
- **Live DB was read** (`lims.db`, this environment). `test_templates` rows 26 and 43 queried directly:
  - id=43 → `code=TPL-A6D-0002`, `name="In-Vitro Release (Franz Diffusion Cell) — with Sampling Details"`, `test_id=25`, `version=1`, **`status=Draft`**, `result_unit=µg/cm²/√h`, `resultRef=flux.mean_flux`.
  - id=26 → `code=TPL-A6D-0001`, `status=Active`. **Out of scope**; read only to confirm it is untouched. The author script must target **id=43 only**.
  - The full id=43 `definition` JSON was dumped and read verbatim; the raw dump is saved alongside this design at `.agents/tasks/a6d-calib-merge/_id43_dump.json` so the reference trace in §1 is checkable against the exact stored bytes (addresses review Finding 3's "unverifiable" objection). Stored group order: `['calibration','curve','qc','linearity','cells','sampling_details','timepoints','flux']`. Top-level keys present: `resultRef, context, groups, criteria` — **there is no `footer`, no `charts`, no `flags` block**, so those reference classes do not exist to trace.
- **Status note (review Finding 4):** the task calls id=43 "Active" but the stored row is `Draft`. This design does **not** silently assume it away; §6 specifies that the author script's single `UPDATE` must **set `status='Active'`** (and preserve `approved_by`/`approved_at`) on id=43, and never write `Draft` back and never touch id=26.
- **"Migrated from calibration" framing corrected (review Finding 3):** the old `calibration` group computes `theoretical_ppm` from a *different* 3-stage chain (`weight_mg / c_vol_1 * c_pip_1 / c_vol_2 * c_pip_2 / c_vol_3 * potency/100*1000`, keys `c_vol_*`/`c_pip_*`). The merged table does **not** carry those columns and does **not** reuse that formula. The old `calibration` and `qc` groups are **deleted outright**; the merged table computes `theoretical_ppm` with a **new** per-row dilution formula (§3) verified against the user's targets (§7). This is a replacement, not a move.

## Overview
Today A6D-0002 carries the calibration maths in two disconnected places. The `calibration` table (kind=table) holds its own `weight_mg`/`c_vol_*`/`c_pip_*` inputs and computes `theoretical_ppm`, `observed_ppm`, `recovery_pct`; the `curve` singleton fits the regression over `calibration.*`; and `linearity` (kind=sequence, 9 seeded rows) is a **separate** table holding the dilution columns the analyst actually fills in but with **no calculated outputs**. Because the dilution columns the user edits live in `linearity` while the theoretical concentration is computed in `calibration`, the reported theoretical concentration never responds to the dilutions entered — the bug the user reported ("Theoretical conc not matching as per the Calibration standards").

The fix, exactly as the user and this step's task describe it, is to make `linearity` the **one single table**: extend it to the twelve columns the user listed so Theoretical / Observed / %Recovery are computed from the same row's dilution inputs, re-point the `curve` regression at `linearity`, delete the now-redundant `calibration` group, and fold the three bracketing QC rows (already seeded inside `linearity` as rows 7–9) so the standalone `qc` group is removed and its two advisory criteria re-pointed at the QC rows living in `linearity`. A small free-text **title singleton** is inserted immediately before `linearity`, following the repo's existing `sri1_header` precedent. The downstream IVRT flux chain (`timepoints.conc_* → amount → carry → cumulative → per_area → flux.* → flux.mean_flux`) is untouched in formula and keeps reading `curve.curve_slope`/`curve.curve_intercept`, which keep their meaning because the merged curve feeds them.

Because standards and QC now share one table, the regression must be fit over the **six calibration-standard rows only**, excluding LQC/MQC/HQC — otherwise an entered QC area skews the curve. The current engine has no row-restricted aggregate. The design adds one small, backward-compatible masking built-in (`where`) plus two hidden mask columns. This is proven necessary and proven correct numerically in §2, run against the real engine.

## Technology stack (locked)
- **Storage/shape:** template-definition JSON in `test_templates.definition` (SQLite `lims.db`), parsed by `src/domain/services/calculation/template_schema.py` into `TemplateDefinition`/`GroupDef`/`FieldDef`. No DB schema/table change.
- **Calculation:** the existing in-house evaluator (`expression.py` + `evaluator.py`). No new third-party dependency, no `eval`, no numpy. One additive built-in (`where`) — see §2.
- **Author script:** a Python script under `backend-v2/scripts/` using the existing `update_*`/`_apply_a6d_*` pattern (stdlib `sqlite3`, `json`; one `UPDATE test_templates SET definition=?, status='Active', modified_* WHERE id=43`), preceded by one file backup of `lims.db`. One backup, one coherent write.
- **Language/runtime:** Python 3.13 (matches the `cpython-313` pycache artifacts in the engine dir).

---

## 1. Complete reference trace of `calibration.*`, `curve.*`, `qc.*`
Reconstructed from the **verbatim id=43 dump** (`_id43_dump.json`). Dotted references resolve through `evaluator.py::_build_scope`/`_sheet_scope`: a multi-row group exposes each field as a **column series** `group.field` (a list down the rows); a singleton exposes `group.field` scalars.

### 1a. References to `calibration.*`
| Site | Expression (verbatim) | Disposition |
|---|---|---|
| `curve.curve_slope` | `slope(calibration.area, calibration.theoretical_ppm)` | **Re-point** to the masked `linearity` series (§2/§3). |
| `curve.curve_intercept` | `intercept(calibration.area, calibration.theoretical_ppm)` | **Re-point** to `linearity`. |
| `curve.correlation` | `correl(calibration.area, calibration.theoretical_ppm)` | **Re-point** to `linearity`. |

No criterion, and no `footer`/`chart`/`resultRef` (none exist) references `calibration.*`. After re-pointing `curve`, `calibration` has **zero** inbound references → safe to delete (§5). A repo-wide grep (`src/**/*.py`) found **no** source outside the definition that hard-codes the `calibration` group key.

### 1b. References to `curve.*` (the regression — must keep feeding downstream)
| Site | Expression (verbatim) | Disposition |
|---|---|---|
| `calibration.observed_ppm` | `(area - curve.curve_intercept) / curve.curve_slope` | Reproduced per-row as `linearity.observed_ppm`, same formula (§3). |
| `qc.observed_ppm` | `(area - curve.curve_intercept) / curve.curve_slope` | QC rows now live in `linearity`; same per-row formula there (§3). |
| `timepoints.conc_1 … conc_6` | `(area_k - curve.curve_intercept) / curve.curve_slope` | **Unchanged.** `curve.*` keeps its key and meaning. |
| criterion `calibration_correlation` | target `curve.correlation`, `gte 0.99`, **blocking** | **Unchanged** — still reads `curve.correlation`, now fit over the 6 standards. |

Full reportable chain (verbatim from the dump): `timepoints.conc_k = (area_k − curve.curve_intercept)/curve.curve_slope` → `amount_k = conc_k * sample_vol / sample_pip * receptor_volume` → `carry_k = sum(prior.amount_k) * replacement_volume / receptor_volume` → `cumulative_k = amount_k + carry_k` → `per_area_k = cumulative_k / donor_area` → `flux.flux_k = slope(timepoints.per_area_k, timepoints.sqrt_hours)` → `flux.mean_flux = mean([flux_1..6])` → **`resultRef = flux.mean_flux`**. The only leaves touching `curve.*` are `conc_1..6`'s reads of `curve.curve_slope`/`curve.curve_intercept`, both preserved by key. **The reportable result and flux chain are structurally unchanged** (§6).

### 1c. References to `qc.*`
| Site | Expression (verbatim) | Disposition |
|---|---|---|
| criterion `qc_recovery_low` | `min(qc.recovery_pct)`, `gte 85`, **advisory** | **Re-point** to QC rows in `linearity`: target becomes `min(where(linearity.recovery_pct, linearity.is_qc))`. |
| criterion `qc_recovery_high` | `max(qc.recovery_pct)`, `lte 115`, **advisory** | **Re-point** to `max(where(linearity.recovery_pct, linearity.is_qc))`. |
| `qc.observed_ppm`, `qc.recovery_pct` | internal to the `qc` group | Removed with the group; equivalent per-row values computed inside `linearity`. |

No `resultRef`/`footer`/`chart` references `qc.*` (none exist). After re-pointing the two criteria, `qc` has zero inbound references → safe to delete (§5).

**Trace conclusion.** The surviving external consumers are (a) `curve.correlation`/`curve_slope`/`curve_intercept`, which remain in `curve` and are re-sourced from `linearity`; (b) the two QC-recovery criteria, re-pointed to the QC rows inside `linearity`. Nothing in the flux chain reads `calibration.*` or `qc.*`.

---

## 2. Calculation-engine aggregate row-selection: current capability and the minimal, *necessary* addition

### 2a. What `slope`/`intercept`/`correl` do today (verified by reading `expression.py`)
All three call `_xy_pairs(args)`: it `_flatten`s the two argument series, **zips them positionally**, and **drops any pair where either side is blank** (`_is_blank`). `slope(ys, xs)` is the least-squares slope of y on x; `intercept = mean(y) − slope·mean(x)`; `correl` is Pearson r. Argument order is Excel's: **first arg = y, second = x**. A reference like `linearity.area` resolves (via `_build_scope`) to the **entire** column down all rows; **there is no mechanism to restrict an aggregate to a subset of rows** — no predicate, no `where`, no row-tag selection. The only incidental exclusion is blank-pair dropping inside `_xy_pairs`. The codebase idiom for "aggregate over a subset" is to keep subsets in **separate groups** and union with `pool(...)`; `pool` cannot *exclude* a subset that lives in the same group. (Confirmed: a grep for `where` in `expression.py` finds only docstring prose — the function does not exist.)

### 2b. Why the engine change IS required here (and why the review's "no engine change" does not apply)
The review argued the `where` built-in is unnecessary — but that conclusion was entirely contingent on its **two-table** restructure (Finding 1/2), where QC lives in a different group so is excluded by construction. Under the **one-table** layout the user and this step's task actually mandate, QC rows share the `linearity` group with the standards, so a naive `slope(linearity.area, linearity.theoretical_ppm)` pulls QC into the fit **the moment an analyst enters QC dilutions and areas** — which bracketing QC exists to do. This was measured, not assumed, against the real engine (`_proto_check.py`, run in this environment):

| Scenario | slope | intercept |
|---|---|---|
| 6 standards only (target) | **53797.61198599985** | **28844.8684743559** |
| naive all-9-row fit, QC areas filled, QC theoretical still blank | 53797.61… | 28844.87… (QC pairs dropped as blank — *accidentally* correct) |
| naive all-9-row fit, QC dilutions **and** areas entered | 53373.61412647779 | **124336.6993399798** ← **skewed, wrong** |
| `where`-masked fit over the 6 standards (QC dilutions+areas entered) | **53797.61198599985** | **28844.8684743559** |

Relying on QC emptiness is unacceptable for a GxP curve: it silently produces the right answer only until the QC row is filled, then silently corrupts every downstream `observed_ppm` and the whole flux chain. The regression must exclude QC **by construction**. Since one-table is the requirement, the engine needs row-restricted aggregation.

### 2c. Decision — add one minimal, backward-compatible `where()` built-in
**API shape** (one function, registered in `_FUNCTIONS` in `expression.py`):
```
where(series, mask) -> list
```
- `series`: a value series (e.g. `linearity.area`); `mask`: a parallel series (e.g. `linearity.is_standard`), interpreted truthily.
- Semantics: `_flatten` both, zip positionally, keep `series[i]` where `mask[i]` is truthy-and-not-blank; return the kept values as a list. Blanks that survive the mask are left as-is for the downstream aggregate's own blank-dropping, so `slope(where(area,m), where(theo,m))` keeps today's blank semantics — just over the masked subset.
- Pure, stateless, returns a list; composes with the existing aggregates.

**Reference implementation** (≈8 lines, mirroring `_f_pool`):
```python
def _f_where(args: list[Any]) -> Any:
    if len(args) < 2:
        return []
    series = _flatten(args[0])
    mask = _flatten(args[1])
    out: list[Any] = []
    for value, flag in zip(series, mask):
        if not _is_blank(flag) and bool(flag):
            out.append(value)
    return out
```
Register with `"where": _f_where` in `_FUNCTIONS`.

**Where it plugs in / backward compatibility:** purely additive — no parser, tokenizer, scope, or schema change; no existing function signature changes; no existing template references `where` (grep-confirmed). `referenced_paths` already walks function arguments generically, so `where(linearity.area, linearity.is_standard)` correctly registers a dependency on the calculated `is_standard` column, and `_evaluation_order` orders `is_standard` before `curve.*`.

**The mask columns.** Add two hidden calculated boolean columns to `linearity`. The engine has no substring/prefix primitive, but `_loose_equal` does case-insensitive string equality and `or` works, so bind to the six seeded standard labels explicitly:
```
is_standard = (calibration_curve = "Calibration standard-1") or (calibration_curve = "Calibration standard-2")
            or (calibration_curve = "Calibration standard-3") or (calibration_curve = "Calibration standard-4")
            or (calibration_curve = "Calibration standard-5") or (calibration_curve = "Calibration standard-6")
is_qc       = not is_standard
```
(Alternative considered: a dedicated hidden "point type" input column, or a new `startswith` primitive — both rejected as more surface area than six self-documenting equalities that bind to the already-seeded labels. The behavioural consequence of a row being relabelled is documented under Edge cases.)

**Numeric proof the masked fit is correct even with QC present** (from `_proto_check.py`, real engine): masked `n=6` → slope `53797.61198599985`, intercept `28844.8684743559`, correl `0.9998994755732439` → rounded **53797.61 / 28844.87 / 0.9999**, identical to the standards-only fit and invariant to QC values. `observed_ppm = (area − 28844.87…)/53797.61…` reproduces all six §7 targets (std-1 `3.195479` vs target `3.195478386`, … std-6 `213.362298` vs `213.3623055`).

> Engine edit footprint: `expression.py` gains `_f_where` + one `_FUNCTIONS` entry. This is committable backend source but **must not be committed unless the user asks**. A `where()` unit test goes in `tests/calculation/test_expression.py` (§6).

---

## 3. The merged 12-column `linearity` group spec

`linearity` stays `kind=sequence` (keeps the existing `rows.seed` and `prev`/`prior` scope; the new formulas use neither). The twelve user-visible columns in the exact required order, plus two **hidden** mask helpers appended after them (they carry no unit and are never rendered as inputs, so the visible order is unchanged):

| # | key | kind | type | unit | label | expression |
|---|---|---|---|---|---|---|
| 1 | `calibration_curve` | input | text | — | Calibration curve | — (existing) |
| 2 | `concentration_pct` | input | number | % | Concentration | — (existing) — **display/label-only, see note** |
| 3 | `std_weight_mg` | input | number | mg | Standard Weight | — (existing) |
| 4 | `diluted_to_ml_1` | input | number | mL | Diluted to | — (existing) |
| 5 | `ml_a` | input | number | mL | mL | — (existing) |
| 6 | `ml_b` | input | number | mL | mL | — (existing) |
| 7 | `ml_taken` | input | number | mL | mL taken | — (existing) |
| 8 | `diluted_to_ml_2` | input | number | mL | Diluted to | — (existing) |
| 9 | `theoretical_ppm` | calculated | number | ppm | Theoretical concentration | formula below |
| 10 | `area` | area | number | µV·s | Area Response | — (analyst / Waters CDS entry) |
| 11 | `observed_ppm` | calculated | number | ppm | Observed concentration | formula below |
| 12 | `recovery_pct` | calculated | number | % | % Recovery | formula below (round 2) |
| hidden | `is_standard` | calculated | boolean | — | — | six-way `or`, §2c |
| hidden | `is_qc` | calculated | boolean | — | — | `not is_standard`, §2c |

> **`concentration_pct` is display/label-only (review Finding 5).** It is the nominal level (1/5/15/30/40/60 %). It feeds **no** formula — `theoretical_ppm` is driven by `std_weight_mg` and the dilution columns (`ml_taken` in particular), **not** by `concentration_pct`. Verified: the §7 targets reproduce without it. An implementer must **not** wire it into the theoretical formula.

The three mandated formulas, written out exactly:

- **theoretical_ppm** (per row, from that row's own dilution inputs; `potency` is the context field — see note):
  ```
  std_weight_mg / diluted_to_ml_1 * ml_a / ml_b * ml_taken / diluted_to_ml_2 * potency / 100 * 1000
  ```
- **observed_ppm** (per row, against the fitted curve):
  ```
  (area - curve.curve_intercept) / curve.curve_slope
  ```
- **recovery_pct** (per row), `rounding {"mode":"round","digits":2}` (matches the old `calibration.recovery_pct`):
  ```
  observed_ppm / theoretical_ppm * 100
  ```

> **`potency` is overridable context, not a bare default (review Finding 6).** In the live id=43 `context`, `potency` is `kind=context, unit=%, default=99.67, overridable=true`. (The generic base builder default is 100; id=43's stored default is 99.67.) The §7 targets reproduce **only** with `potency=99.67`; the §6 self-check must seed `potency=99.67` explicitly rather than assume a builder default.

**Re-pointed `curve` group** (same keys, new source = masked `linearity` series; keep existing roundings — slope/intercept round 2, correlation round 4):
```
curve_slope     = slope(where(linearity.area, linearity.is_standard), where(linearity.theoretical_ppm, linearity.is_standard))
curve_intercept = intercept(where(linearity.area, linearity.is_standard), where(linearity.theoretical_ppm, linearity.is_standard))
correlation     = correl(where(linearity.area, linearity.is_standard), where(linearity.theoretical_ppm, linearity.is_standard))
```

**Dependency-ordering (no cycle).** `curve.*` depends on `linearity.theoretical_ppm` (calculated), `linearity.area` (area — no ordering edge), and `linearity.is_standard` (calculated). `linearity.observed_ppm`/`recovery_pct` depend on `curve.*`. Per `_evaluation_order`, a qualified `group.field` edge is created only when the referenced field is calculated, so the sort is `theoretical_ppm, is_standard → curve.* → observed_ppm → recovery_pct`. No cycle — this mirrors the old `calibration.theoretical_ppm → curve.* → calibration.observed_ppm` that already worked.

**Seed data.** Extend the existing 9-row seed (which currently names only `calibration_curve` + `concentration_pct`) so the six standard rows carry their dilution inputs and reproduce the verified theoretical values out of the box. QC rows keep label + concentration only (no dilution values in the user's data set):

| row | calibration_curve | concentration_pct | std_weight_mg | diluted_to_ml_1 | ml_a | ml_b | ml_taken | diluted_to_ml_2 |
|---|---|---|---|---|---|---|---|---|
| 1 | Calibration standard-1 | 1 | 89.73 | 50 | 5 | 50 | 1 | 50 |
| 2 | Calibration standard-2 | 5 | 89.73 | 50 | 5 | 50 | 5 | 50 |
| 3 | Calibration standard-3 | 15 | 89.73 | 50 | 5 | 50 | 15 | 50 |
| 4 | Calibration standard-4 | 30 | 89.73 | 50 | 1 | 1 | 3 | 50 |
| 5 | Calibration standard-5 | 40 | 89.73 | 50 | 1 | 1 | 4 | 50 |
| 6 | Calibration standard-6 | 60 | 89.73 | 50 | 1 | 1 | 6 | 50 |
| 7 | LQC | 1 | (blank) | | | | | |
| 8 | MQC | 15 | (blank) | | | | | |
| 9 | HQC | 30 | (blank) | | | | | |

`rows` stays `{min:9, max:15, default:9, labelFrom:"calibration_curve", seed:[…]}`.

> **QC theoretical.** In the merged table QC `theoretical_ppm` is computed by the **same** per-row dilution formula (not a manual input as in the old `qc.theoretical_ppm`), per the task's explicit instruction. With QC dilution columns blank, `theoretical_ppm` → EMPTY (divide-by-blank → EMPTY) and `recovery_pct` → EMPTY until the analyst enters QC dilutions; QC `observed_ppm` still computes against the standards-only curve. **Open confirmation for the user** (non-blocking): whether QC `theoretical_ppm` should instead be a manual input. Absent that, the design follows the task's "keep QC theoretical computed by the same formula".

---

## 4. Title singleton group + field JSON, immediately before `linearity`

Following the **`sri1_header` precedent** in `scripts/template_definitions/a4_a5_related_substances.py` **verbatim** — a singleton whose single `{"key":"title","kind":"input","type":"text","label":"Title"}` field renders as a heading above the table — plus a `default` (the review's Finding 7 confirmed, and `template_schema.py` confirms, that `overridable` is a **no-op on an input field**; it only affects `kind=context`. So I follow `sri1_header` exactly and add only `default`, dropping `overridable`):

```json
{
  "key": "linearity_title",
  "kind": "singleton",
  "label": "Calibration Standards",
  "fields": [
    { "key": "title", "kind": "input", "type": "text", "label": "Title", "default": "Calibration Standards" }
  ]
}
```

**Placement.** Insert `linearity_title` **immediately before** `linearity`. With `calibration` and `qc` removed, the final group order is:
```
curve, linearity_title, linearity, cells, sampling_details, timepoints, flux
```
so `[linearity_title]` sits directly in front of `[merged 12-column linearity]` and renders as its heading. (`curve` may stay where it is; the only ordering requirement is `linearity_title` immediately precedes `linearity`.)

**Referenced by nothing (verified).** `linearity_title.title` appears in no `expression`, no `where(...)` mask, no criterion `target`, no `limit`; there is no `footer`/`chart`/second `resultRef` in this definition. It is an `input`/`text` field (not `area`, so the Waters import ignores it per `area_field_refs`), carries no unit, and the evaluator treats singleton input fields as plain stored values — it cannot enter any numeric computation and cannot affect the regression scoping or the theoretical/observed/recovery formulas. It is editable and persisted because `kind=input` (`FieldDef.is_editable`), and `default` seeds its opening value (`_seed_rows`).

> **Schema safety.** `title` as a field key is fine — `GroupDef.parse` enforces field-key uniqueness only *within* a group, and group scoping means `linearity_title.title` never collides with anything in `linearity`. The group key `linearity_title` is unique among groups.

---

## 5. Removing `calibration` and handling `qc`
**Remove `calibration` (kind=table).** Per §1a, after re-pointing the three `curve` aggregates to the masked `linearity` series, `calibration.*` has zero inbound references (no expression, criterion, and no footer/chart/resultRef exist). Deleting it yields the single calibration table the user asked for. Its per-row logic is reproduced inside `linearity` (§3) via a new formula (not a move — review Finding 3).

**Remove `qc` (kind=table).** Per §1c, the three QC rows already exist as seeded rows 7–9 inside `linearity`, and the only external references to `qc.*` are the two advisory criteria, which are **re-pointed** to the QC rows inside `linearity`:
```
qc_recovery_low  : target  min(where(linearity.recovery_pct, linearity.is_qc))   operator gte  limit 85   severity advisory
qc_recovery_high : target  max(where(linearity.recovery_pct, linearity.is_qc))   operator lte  limit 115  severity advisory
```
`min`/`max` ignore blanks, so until QC theoretical/area are entered these criteria are "not yet assessable" (`passed=None`) — same behaviour as today. With `qc.*` otherwise unreferenced, the group is deleted.

**Net group set after the edit:** `curve, linearity_title, linearity, cells, sampling_details, timepoints, flux` (7 groups; was 8). `calibration` and `qc` removed; `linearity_title` added. The `calibration_correlation` criterion is unchanged (still blocks on `curve.correlation`).

---

## 6. Confirmation strategy: flux reportable result, IVRT chain, and Active status stay intact
1. **Static.** `resultRef` stays `flux.mean_flux`; the `flux` and `timepoints` groups are not edited. The only cross-group reads from that chain are `timepoints.conc_k`'s `curve.curve_slope`/`curve.curve_intercept`, both preserved by key and now sourced from the merged curve. `TemplateDefinition.parse` re-validates `resultRef` resolves (it does) and the author script must assert no surviving expression/criterion references a deleted group (`calibration.*`/`qc.*` all re-pointed or removed).
2. **Runtime parity (author-script self-check, before the write).** Load the proposed definition through `TemplateDefinition.parse`, then `WorksheetEvaluator.evaluate` with the six seeded standard rows + the user's six areas, with `potency=99.67` seeded explicitly, asserting **exact post-rounding** values (review Finding 8):
   - `curve.curve_slope == 53797.61`, `curve.curve_intercept == 28844.87` (round 2), `curve.correlation == 0.9999` (round 4) — fit over the six standards only, re-asserted with dummy QC areas populated to prove the mask excludes them;
   - each `linearity.theoretical_ppm` / `observed_ppm` matches §7 to full precision (`≈` tolerance only for these unrounded per-row values); each `recovery_pct` matches §7 at round 2;
   - feeding representative `timepoints` areas yields finite `conc_k`/`per_area_k`/`flux_k`/`mean_flux` and **no circular-reference error** (proves the chain still resolves through the re-pointed curve; specific flux numbers are not pinned).
3. **Status/approval.** The single `UPDATE` sets `status='Active'` and preserves `approved_by`/`approved_at` on id=43; it never writes `Draft` and never touches id=26 (review Finding 4).
4. **Test suite.**
   - Add a `where()` unit test to `tests/calculation/test_expression.py` (mask drops unmasked positions; blanks handled; composes with `slope`).
   - **Update `tests/calculation/test_a6d_linearity_seed.py`:** it currently pins the 8-column input-only `linearity` (`set(row) == {"calibration_curve","concentration_pct"}`, `UNSEEDED_COLUMNS` all blank, no calculated fields). After the merge, `linearity` has 12 user columns + 2 hidden masks and a richer 6-row dilution seed, so that assertion must be updated to the new column/seed set and a regression assertion added (fit over the six standards reproduces §7). This is **expected churn**, flagged so the failing assertion is not mistaken for a regression.
   - Run the full `tests/calculation` suite to confirm the additive `where` built-in regresses no other template.

---

## 7. Numeric acceptance targets (restated; `potency = 99.67`)
**theoretical_ppm** (six standards must reproduce exactly — all verified in `_proto_check.py`):
| row | theoretical_ppm |
|---|---|
| std-1 | 3.57735564 |
| std-2 | 17.8867782 |
| std-3 | 53.6603346 |
| std-4 | 107.3206692 |
| std-5 | 143.0942256 |
| std-6 | 214.6413384 |

**Regression over the six standards only** (mask excludes LQC/MQC/HQC): slope **53797.61** (round 2), intercept **28844.87** (round 2), correlation **0.9999** (round 4). Verified reproducible with `slope(where(area,is_standard), where(theoretical_ppm,is_standard))` even when QC dilutions+areas are populated.

**observed_ppm** = `(area − intercept)/slope`:
| row | area | observed_ppm |
|---|---|---|
| std-1 | 200754 | 3.195478386 |
| std-2 | 974514 | 17.57827346 |
| std-3 | 2922207 | 53.7823539 |
| std-4 | 5786622 | 107.0266337 |
| std-5 | 7842177 | 145.2356731 |
| std-6 | 11507227 | 213.3623055 |

**recovery_pct** = `observed_ppm/theoretical_ppm*100` (round 2):
| row | recovery_pct |
|---|---|
| std-1 | 89.32515266 |
| std-2 | 98.27523583 |
| std-3 | 100.227392 |
| std-4 | 99.72602157 |
| std-5 | 101.4965296 |
| std-6 | 99.40410691 |

Tolerance: `theoretical_ppm`/`observed_ppm` carry no rounding (full precision in the chain); `recovery_pct` and the three `curve.*` fields assert exact post-rounding values.

---

## Edge cases & validation rules
- **Blank dilution inputs** → `theoretical_ppm` EMPTY (divide-by-blank/zero → EMPTY); `observed_ppm`/`recovery_pct` cascade to EMPTY. No exception — correct "not yet entered" behaviour.
- **Slope == 0 or < 2 valid standard pairs** → `_xy_pairs` returns None → `curve.*` EMPTY → every `observed_ppm` and the flux chain EMPTY; `calibration_correlation` is `passed=None`. Non-fatal; matches current behaviour.
- **Analyst renames a standard row** so its label no longer equals one of the six seeded strings → that row drops out of `is_standard` and the regression. This is the explicit contract of the label-equality mask, documented here as known/intended rather than a silent surprise. (Rename-tolerance alternative — a dedicated hidden point-type column — noted and not chosen, to avoid a user-facing column beyond the mandated twelve.)
- **QC rows with areas but no dilutions** → excluded from the fit by `is_qc`; `observed_ppm` computes against the curve; `recovery_pct` EMPTY until QC theoretical present; QC criteria remain not-assessable (advisory, non-blocking).
- **`where` length mismatch** (defensive) → `zip` truncates to the shorter series; both mask inputs come from the same group, so lengths match row-for-row.
- **Rows beyond the seed** (analyst adds up to max 15) → new rows are neither standard nor QC unless labelled to match; they do not enter the fit — the safe default.

## Testability summary
- **Unit-testable (pure engine):** `where()` masking; `slope`/`intercept`/`correl` over masked series reproducing §7; the `theoretical_ppm` per-row formula.
- **Integration-testable (`WorksheetEvaluator` over the full definition):** parse round-trip, dependency ordering with no cycle, §7 end-to-end, and the flux chain resolving to a non-blank `mean_flux`. The updated `test_a6d_linearity_seed.py` plus a new A6D calibration-merge parity test cover this.

## Deliverables of the implementing step (not performed here)
1. Add `_f_where` + `"where"` registration to `expression.py` (+ a `where()` unit test). Do **not** commit engine source unless the user asks.
2. One author script under `scripts/` that: backs up `lims.db` once; builds the new id=43 definition (remove `calibration` & `qc`, insert `linearity_title`, extend `linearity` to 12 cols + 2 hidden masks + 6-row dilution seed, re-point `curve`, re-point the two QC criteria); runs the parse+evaluate self-check against §7 with `potency=99.67`; then performs a single `UPDATE … SET definition=?, status='Active', modified_* WHERE id=43`, preserving `approved_by`/`approved_at` and never touching id=26.
3. Update `tests/calculation/test_a6d_linearity_seed.py` to the merged shape.

---

## 8. Responses to the design-review findings
**Finding 1 (HIGH) — "Wrong structure: build TWO titled tables, not one."** **Not adopted; justified against requirements.** The authoritative original user request says, verbatim, *"…is a single table"* (message 10) and then lists all twelve columns of **one** table (messages 11–12). This step's task is titled *"MERGED INTO ONE SINGLE TABLE"* and repeats *"ONE merged table (the `linearity` group) with these TWELVE columns"*, *"ONE SINGLE TABLE"*, and *"so there is ONE calibration table as the user asked."* The review's two-table layout (with an invented second title "Calibration Standards table 2") appears in neither the user's words nor this step's task. Per the authoring rules, my choices must align with the original requirements, and the original user text wins over any conflicting instruction. I therefore keep the single merged `linearity` table. I did seriously weigh the review's point — a two-table split is a legitimate engineering shape and would remove the engine change — but it changes *what the user asked for*, so adopting it would be a silent deviation from the requirement. Flagged here explicitly rather than actioned.

**Finding 2 (HIGH) — "`where()`/`is_standard` engine change is unnecessary; re-point curve directly at the standards table."** **Not adopted, because it is contingent on Finding 1.** Its own text says the mask is unnecessary *"under the two-table layout"* — true, but only there. Under the one-table layout the user mandates, QC shares the group, and I measured the skew on the real engine: entering QC dilutions+areas moves the intercept from 28844.87 to 124336.70 (§2b table). This step's task explicitly anticipates exactly this and instructs me to *"INVESTIGATE how the calculation engine's slope/intercept/correl aggregates select rows … If the engine has no row-filtering for aggregates, DESIGN the least-invasive capability."* I confirmed the engine has none and designed the least-invasive capability (`where`, §2c), proving the masked fit reproduces the targets invariant to QC values. So the engine change is retained, with the obstacle stated explicitly as the review asked ("if the revise pass finds a genuine reason an engine change is still required, it must be flagged explicitly").

**Finding 3 (HIGH) — provenance + "migrated from calibration" framing.** **Addressed.** The live id=43 definition was read from `lims.db` in this environment and the raw dump saved at `.agents/tasks/a6d-calib-merge/_id43_dump.json` for checkability; §1 is reconstructed from that verbatim dump. The design now states plainly that old `calibration` (3-stage `c_vol`/`c_pip` chain) and old `qc` are **deleted outright**, not migrated, and that the merged table uses a **new** per-row dilution formula verified against §7. Dispositions match the review: `curve` re-pointed to the (masked) merged series; `calibration_correlation` unchanged/blocking; `qc_recovery_low/high` re-pointed; timepoints/flux chain and `resultRef=flux.mean_flux` preserved. (The one divergence from the review's wording — re-pointing to `cal_standards.*` vs the masked `linearity` series — follows from Finding 1/2.)

**Finding 4 (MEDIUM) — Active-status preservation.** **Addressed.** §Status-of-inputs and §6 now require the single `UPDATE` to set `status='Active'`, preserve `approved_by`/`approved_at`, never write `Draft`, and never touch id=26.

**Finding 5 (MEDIUM) — `concentration_pct` display-only.** **Addressed.** §3 declares `concentration_pct` display/label-only, feeding no formula; `theoretical_ppm` is driven by `ml_taken`/the dilution columns, not by it.

**Finding 6 (MEDIUM) — `potency` is overridable context, not a bare default.** **Addressed.** §3 states `potency` is `kind=context, overridable=true`, stored default 99.67 on id=43 (base builder default 100), and §6 seeds `potency=99.67` explicitly in the self-check.

**Finding 7 (NIT) — title field shape.** **Addressed.** The title singleton follows `sri1_header` exactly (singleton `input`/`text` `title`) plus a `default`; `overridable` is **dropped** as a confirmed no-op on input fields. Confirmed referenced by nothing (§4). Only one title singleton is specified, consistent with the single-table decision in Finding 1.

**Finding 8 (NIT) — assert exact post-rounding values.** **Addressed.** §6 asserts `curve_slope==53797.61`, `curve_intercept==28844.87` (round 2), `correlation==0.9999` (round 4), reserving `≈` for the unrounded per-row `theoretical_ppm`/`observed_ppm`.
