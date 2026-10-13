# Implementation Plan — Dissolution "% Release vs Time" chart (frontend only)

Goal: render a line chart ("% Release vs Time") for the dissolution template
TPL-A6A-0002 v1 inside the generic worksheet form. X = `time_hr`, Y = `% Release`,
default series = `mean`, with per-unit series (`unit_1..unit_6`) toggleable via the
chart legend. Data comes from the same server-computed state the rest of the form
already reads: `computed.rows["timepoints_release"]`.

Scope guardrails (do NOT violate):
- Frontend only. Do NOT touch `backend-v2`, any `.py` file, or the template
  definition stored in the DB. The `chart` config already exists on the
  `release_chart` group in the DB.
- Templates with no chart config must render EXACTLY as before. The chart branch
  must be additive and gated on the presence of a `chart` property.

## Design decisions (made here, grounded in the code I read)

- Rendering is driven generically from `TemplateDefinition.groups` in
  `WorksheetForm.tsx`. The chart group `release_chart` is `kind: "singleton"` and
  carries a non-standard `chart` property. Decision: model `chart` as an optional
  field on `GroupDef` (mirroring how `footer`/`headerContext` are already modeled)
  and, in the singleton branch of the render loop, render the chart when
  `group.chart` is present instead of the normal field grid. Gating on
  `group.chart` (not on the group key) keeps it template-driven and leaves every
  non-chart group untouched.
- Charting: use `primereact/chart` (already shipped with PrimeReact 10.8). Its
  Chart component dynamically imports `chart.js/auto` (confirmed by reading
  `node_modules/primereact/chart/chart.esm.js`), which self-registers all
  controllers/scales — so no manual `Chart.register(...)` is needed, but `chart.js`
  MUST be installed as a dependency (it is not currently installed). Decision: add
  `chart.js` `^4.4.0` (the current v4 line PrimeReact 10 loads via `chart.js/auto`).
- Reactivity: PrimeReact's `Chart` is wrapped in `React.memo` whose comparator uses
  REFERENCE equality on `data` and `options`. Decision: build the `data` and
  `options` objects with `useMemo` keyed on `computed.rows["timepoints_release"]`
  and the visible-series state, so a new object reference is produced whenever the
  computed rows or the toggles change — otherwise the chart would not repaint on
  edits.
- Series visibility: keep it simple. Local component state holding the set of
  visible series keys, seeded from `chart.defaultSeries` (falls back to `["mean"]`).
  Render the legend as small toggle chips/buttons above the canvas (matches the
  existing PrimeReact + primeflex button patterns in the file). The Mean line is
  on by default.
- Data mapping: a pure helper converts `computed.rows[sourceGroup]` to Chart.js
  datasets. For each visible series it emits `{x,y}` points using the row's
  `time_hr` as x and the series key as y, SKIPPING any row where x or y is
  blank/non-numeric (so a partially filled worksheet still draws a clean line).
  Use a `linear` x-axis so numeric hours are spaced correctly.

## Plan

- [ ] 1. Add the `chart.js` dependency and install it.
      Add `"chart.js": "^4.4.0"` to `dependencies` in
      `frontend-react/package.json` (place it alphabetically / near `axios`), then
      run `npm install` in `frontend-react`. PrimeReact's Chart loads
      `chart.js/auto`, so no other charting package is needed.
      Files: `frontend-react/package.json` (and resulting `package-lock.json`).
      Verify: run `npm ls chart.js` in `frontend-react` and confirm a single
      `chart.js@4.x` entry resolves with no peer/unmet errors.

- [ ] 2. Model the chart config on the template types.
      In `testTemplate.types.ts` add a `ChartConfig` interface and an optional
      `chart?: ChartConfig` on `GroupDef`, placed and documented like the existing
      `footer?`/`headerContext?` members. Shape:
      ```ts
      export interface ChartSeries { key: string; label: string; }
      export interface ChartConfig {
        title?: string;
        sourceGroup: string;      // e.g. "timepoints_release"
        xField: string;           // e.g. "time_hr"
        xLabel?: string;
        yLabel?: string;
        series: ChartSeries[];
        defaultSeries?: string[]; // keys on by default; falls back to ["mean"] in UI
      }
      ```
      Add `chart?: ChartConfig;` to `GroupDef` with a one-line doc comment noting it
      is a non-standard, UI-only rendering hint (the calc engine ignores it).
      Files: `frontend-react/src/features/test-templates/models/testTemplate.types.ts`
      Verify: run `npx tsc -b` in `frontend-react` — type-checks with no errors.

- [ ] 3. Create the `WorksheetChart` component.
      New file `frontend-react/src/features/test-templates/components/WorksheetChart.tsx`
      exporting `WorksheetChart`. Props:
      `{ chart: ChartConfig; computed: WorksheetComputed; stale?: boolean }`.
      Behaviour:
      - Import `Chart` from `primereact/chart`, `Button`/`Tag` for the legend, and
        types from `../models/testTemplate.types` using the existing relative-import
        style in this folder (the folder uses relative `../models/...` imports, e.g.
        in `WorksheetForm.tsx`; match that rather than inventing an alias).
      - `useState<Set<string>>` for visible series keys, seeded from
        `chart.defaultSeries` or `["mean"]`, intersected with
        `chart.series.map(s => s.key)` so a stale default can't enable a missing
        series.
      - A pure helper (module-scope) `buildPoints(rows, xField, yKey)` returning
        `{x:number;y:number}[]`: for each row read `xField` and `yKey`, coerce with
        a `toNum` that treats `null`/`''`/`undefined`/`NaN` as missing, and skip the
        row if either x or y is missing. (Mirror the blank/non-numeric handling the
        form already uses, e.g. the `notEmpty` checks in `WorksheetForm.tsx`.)
      - `useMemo` the Chart.js `data` object (one dataset per visible series, each
        from `buildPoints(computed.rows[chart.sourceGroup] ?? [], chart.xField,
        key)`, with distinct `borderColor`s and `tension: 0`) keyed on
        `computed.rows[chart.sourceGroup]` and the visible-series Set — so the memo
        yields a NEW reference when rows or toggles change (required for repaint).
      - `useMemo` the `options` object: `maintainAspectRatio:false`,
        `scales.x` of `type:'linear'` with `title.text = chart.xLabel ?? 'Time'`,
        `scales.y` with `title.text = chart.yLabel ?? '% Release'` and
        `beginAtZero:true`, legend hidden (we provide our own toggles).
      - Render: section title from `chart.title` is already covered by the group
        header in step 4, so render only the toggle row + a fixed-height
        (`~320px`) wrapper div holding `<Chart type="line" data={data}
        options={options} />`. Toggle buttons: one per `chart.series` entry,
        highlighted when active, flipping membership in the visible Set.
      - When `stale` is true, dim the wrapper (reuse the `text-400`/opacity
        convention used for stale computed cells) so it reads as "recalculating".
      Files: `frontend-react/src/features/test-templates/components/WorksheetChart.tsx`
      Verify: run `npx tsc -b` in `frontend-react` — compiles with no errors.

- [ ] 4. Wire the chart into the WorksheetForm singleton render branch.
      In `WorksheetForm.tsx`, import `WorksheetChart`. Inside the
      `groups.map((group) => {...})` loop, in the `if (group.kind === 'singleton')`
      block, add an early branch BEFORE the normal field-grid return:
      `if (group.chart) { return (<Card key={group.key}> ...header... <WorksheetChart
      chart={group.chart} computed={computed} stale={preview.stale} /></Card>); }`.
      Keep the existing `<Card>` + `<h3 className="m-0 text-base">{group.label ??
      group.key}</h3>` header (so "Graphical data" stays the section header) and
      match the surrounding card/spacing exactly; do NOT render the group toolbar
      (there are no editable fields on the chart group). Leave every other code
      path in the loop unchanged so non-chart singletons/tables render identically.
      Files: `frontend-react/src/features/test-templates/components/WorksheetForm.tsx`
      Verify: run `npx tsc -b` in `frontend-react` — compiles with no errors.

- [ ] 5. Build and manually verify the feature end to end.
      Run `npm run build` in `frontend-react` (this runs `tsc -b && vite build`) and
      confirm it succeeds with no type or build errors. Then, with the dev stack
      running (`start-lims.bat`; frontend http://localhost:5174, backend
      http://127.0.0.1:8443), open a worksheet for template TPL-A6A-0002 v1 and
      confirm: the "Graphical data" section shows a line chart titled "% Release vs
      Time"; the Mean line renders by default; X-axis is labelled
      "Time Interval (Hours)" and Y-axis "% Release"; toggling unit chips shows/hides
      unit_1..unit_6 lines; editing a timepoint value updates the chart; a template
      WITHOUT a chart config renders exactly as before (no chart, no regression).
      Files: none (verification only).
      Verify: `npm run build` succeeds; manual checks above all pass.

## Verification (iteration 1)

What was implemented (frontend only; no `.py`, backend, or DB touched):
- `package.json`: added `"chart.js": "^4.4.0"`; `npm install` resolved
  `chart.js@4.5.1` with a single clean entry (`npm ls chart.js` → one node, no
  peer/unmet errors).
- `testTemplate.types.ts`: added `ChartSeries` + `ChartConfig` interfaces and an
  optional `chart?: ChartConfig` on `GroupDef`, documented like `footer`/
  `headerContext` as a UI-only hint the calc engine ignores.
- New `WorksheetChart.tsx`: PrimeReact `Chart type="line"`. X = `chart.xField`,
  Y = selected series; `useMemo` on rows+visible-set yields fresh `data`/`options`
  references so it repaints on edits (PrimeReact Chart is reference-memoised).
  `buildPoints` coerces with a blank-tolerant `toNum` and skips rows missing X or
  Y; series seeded from `defaultSeries` → `["mean"]`, toggled by chips.
- `WorksheetForm.tsx`: in the `singleton` branch, an early `if (group.chart)`
  renders the chart inside the usual `<Card>` with the group label as header; no
  toolbar, no field grid. Every other code path is untouched, so templates
  without `chart` render identically.

Commands run:
- `npm install` (frontend-react) → exit 0, added chart.js.
- `npm ls chart.js` → `chart.js@4.5.1`, no conflicts.
- `npm run build` (`tsc -b && vite build`) → exit 0, PASS. No TypeScript errors.
  Bundle includes `dist/assets/auto-*.js` (208 kB), confirming PrimeReact pulled
  in `chart.js/auto` which self-registers controllers/scales.
- `npm run lint` → FAILED to run: `eslint` is not installed in this project
  (`npm ls eslint` → empty) and there is no eslint config file. This is a
  pre-existing environment gap, NOT a regression from this change; no lint
  toolchain was added (out of scope). The TypeScript build is the authoritative
  static check and it passes.
- Point-mapping sanity check (node, standalone): verified `buildPoints` skips a
  blank-X row and a blank-Y row, sorts by X, and still plots partially-filled
  rows for series that have values. Mean and unit_1 produced the expected
  `{x,y}` sequences.

UI check: the dev stack is up (5174/8443 both listening) but the backend API is
behind authenticated HTTPS, so a scripted end-to-end click-through wasn't
performed here. The chart renders purely from `computed.rows[chart.sourceGroup]`
(the same read path footers use) and the config lives on the DB template, so the
compiled component + verified mapping cover the data path; a manual click-through
of a TPL-A6A-0002 worksheet remains the final visual confirmation.

## Notes / assumptions
- `chart.js@^4.4.0` is pinned because PrimeReact 10's Chart loads `chart.js/auto`
  (v4 API). If `npm install` surfaces a peer conflict with PrimeReact, fall back to
  the exact v4 version PrimeReact resolves, but a conflict is not expected since
  PrimeReact declares chart.js as optional/undeclared.
- The chart group is detected by the presence of `group.chart`, NOT by key, so the
  branch is fully template-driven and safe for all other templates.
- No automated test framework is configured in `frontend-react` (no test script or
  runner in `package.json`), so verification is the TypeScript build (`tsc -b`),
  the production build (`vite build`), and the manual UI checks above. Do not add a
  test framework for this task.
