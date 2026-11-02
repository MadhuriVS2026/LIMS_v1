# Dissolution "% Release vs Time" line chart in the worksheet form

The worksheet form now renders a line chart for dissolution timepoints instead of a field grid, driven entirely by an optional `chart` config carried on a `singleton` group (the `release_chart` group that already exists on template TPL-A6A-0002 in the DB). X is `time_hr`, Y is `% Release`, the Mean series is on by default, and `unit_1..unit_6` are toggleable via chips above the canvas. The chart reads the same server-computed state the rest of the form uses (`computed.rows["timepoints_release"]`), so it repaints when a timepoint is edited. The branch is gated purely on the presence of `group.chart`, so every other template and singleton renders exactly as before.

Watch for: nothing blocking. The change is additive, frontend-only, and matches the plan. The only observations are minor and non-blocking: the chart title ("% Release vs Time") is not rendered anywhere (the group label is the only header), and lint could not run because no eslint toolchain exists in the project (pre-existing, out of scope).

**Verdict**: APPROVED

## High-level view

Rendering stays template-driven. The chart is not keyed to a hard-coded group name; it fires whenever a `singleton` group carries a `chart` property, mirroring how `footer`/`headerContext` are already modeled on `GroupDef`. That keeps the branch additive — a group without `chart` takes the unchanged field-grid path — so there is no regression surface for non-chart templates.

The data path reuses existing computed state. `WorksheetChart` reads `computed.rows[chart.sourceGroup]`, the same read footers use, and rebuilds its Chart.js `data`/`options` via `useMemo` keyed on the rows and the visible-series set. That reference churn is deliberate: PrimeReact's `Chart` is reference-memoised, so fresh objects are what make it repaint on edits. Blank/non-numeric rows are dropped by a blank-tolerant `toNum`, so a half-filled worksheet still draws a clean, X-sorted line.

The dependency is correct and minimal. `chart.js ^4.4.0` was added and resolves to `4.5.1` as a single clean entry; PrimeReact 10's `Chart` pulls `chart.js/auto` which self-registers controllers and scales, so no manual registration is needed. No backend, `.py`, or DB-definition file is touched — the config already lives on the DB template.

Verification rests on the TypeScript build (`tsc -b`) and `vite build`, both exit 0, plus a standalone point-mapping sanity check of `buildPoints`. No automated UI test runs (no test framework configured); a manual click-through of a TPL-A6A-0002 worksheet remains the only unexecuted check.

<details>
<summary>Issues (2)</summary>

1. **Chart title not rendered** (confirmed) — `ChartConfig.title` ("% Release vs Time") is defined and documented but never displayed; only the group label renders as the header. Non-blocking: decide whether the title should appear above the canvas or drop the field.
2. **Lint not executed** (confirmed) — `npm run lint` could not run because no eslint toolchain/config exists in the project. Pre-existing environment gap, not a regression; the TypeScript build is the authoritative static check and passes.

</details>

<details>
<summary>Details</summary>

### Template-driven gating on `group.chart`

The render branch sits inside the existing `if (group.kind === 'singleton')` block in `WorksheetForm.tsx` and returns early only when `group.chart` is present. Keying on the property, not the group name, keeps it template-driven and leaves every other singleton on the untouched field-grid path. It reuses the same `<Card>` + `<h3 className="m-0 text-base">{group.label ?? group.key}</h3>` header, so "Graphical data" (the group label) stays the section header, and omits the group toolbar since the chart group has no editable fields. `computed` and `preview.stale` are both in scope at that point.

`ChartConfig` is modeled as an optional member on `GroupDef`, documented as a UI-only hint the calc engine ignores — the same pattern as `footer`/`headerContext`. The shape matches the brief exactly (`title?`, `sourceGroup`, `xField`, `xLabel?`, `yLabel?`, `series: {key,label}[]`, `defaultSeries?`), and `WorksheetRow`/`WorksheetComputed` are imported from the same models module with the expected `rows: Record<string, WorksheetRow[]>` shape.

### Repaint correctness and the memo keys

PrimeReact's `Chart` is reference-memoised, so `WorksheetChart` builds `data`/`options` with `useMemo` to produce fresh references on change. The `data` memo is keyed on `rows`, `visible`, `chart.series`, `chart.xField`, and `seriesKeys`, so editing a timepoint (which changes the `computed.rows` reference) or toggling a chip forces a repaint. The `options` memo is keyed only on `chart.xLabel`/`chart.yLabel` — the only values in it that can change. Note that `rows` is derived as `computed.rows?.[chart.sourceGroup] ?? []` each render, so the memo only churns when the underlying `computed` reference actually changes.

### Data mapping and blank tolerance

`buildPoints` coerces X and Y through `toNum` (treats `null`/`undefined`/`''`/non-finite as missing) and skips the row if either axis is missing, so a partially entered worksheet still draws a clean line. Points are sorted by X, so an out-of-order timepoint entry still renders a monotonic line. The x-axis is `type: 'linear'`, so numeric hours are spaced proportionally rather than as categories. The standalone node check recorded in the plan confirms blank-X and blank-Y rows are dropped and partially-filled series still plot.

Series seeding is defensive: `defaultSeries` is intersected with the declared series keys so a stale default can't enable a key the chart doesn't define, and it falls back to the first series if nothing matches. The toggle chips use PrimeReact/primeflex utility classes consistent with the file and carry `aria-pressed`.

### Dependency and scope

`chart.js ^4.4.0` is the only `package.json` change; the lockfile resolves it to `4.5.1` as a single node with no peer/unmet errors. PrimeReact 10's `Chart` dynamically imports `chart.js/auto` (self-registers controllers/scales), so no manual `Chart.register` is needed and `primereact/chart` is used directly rather than an inline-SVG fallback. The commit touches only `package.json`, `package-lock.json`, two component files, the types file, and the plan doc — no `backend-v2`, no `.py`, no DB template-definition file. The `chart` config lives on the DB template already, consistent with the scope guardrail.

### Test coverage

Not tested: no automated UI or component test exists (no test framework configured; the brief says not to add one). Static verification is `tsc -b` (exit 0) and `vite build` (exit 0, bundle includes `dist/assets/auto-*.js` confirming `chart.js/auto` was pulled), plus a standalone node check of `buildPoints`. The one unexecuted check is a manual click-through of a live TPL-A6A-0002 worksheet — Mean line draws, unit chips toggle, axis labels read "Time Interval (Hours)"/"% Release", non-chart template unchanged. That gap is inherent to the authenticated-HTTPS backend.

</details>

<details>
<summary>File map</summary>

- `src/features/test-templates/models/testTemplate.types.ts` — added `ChartSeries` + `ChartConfig` interfaces and optional `chart?: ChartConfig` on `GroupDef`.
- `src/features/test-templates/components/WorksheetChart.tsx` — new line-chart component (PrimeReact `Chart`, memoized data/options, blank-tolerant point mapping, series toggle chips).
- `src/features/test-templates/components/WorksheetForm.tsx` — early `if (group.chart)` branch in the singleton render path renders `WorksheetChart` inside the usual `<Card>`.
- `package.json` / `package-lock.json` — added `chart.js ^4.4.0` (resolves 4.5.1).
- `.agents/tasks/plan.md` — implementation plan and verification notes.

Full diff: `git show 185850f`.

</details>
