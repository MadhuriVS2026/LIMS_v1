# Implementation Plan — Worksheet column + read-only worksheet preview

Feature: on `/test-templates`, add a "Worksheet" column whose cell shows `CODE NAME`
(e.g. `TPL-A1-0001 Assay by HPLC`) as a clickable text-link Button. Clicking it opens a
read-only, viewable worksheet layout for that template, rendered from the template's
`definition`. Frontend-only; no backend changes.

## Design decisions (recorded)

- **Viewer approach: route + page (approach a), chosen over a Dialog.** This matches the
  existing navigation model exactly: the list already navigates to `/test-templates/:id`
  (TemplateDetailPage) via `useNavigate`, the full template with its `definition` is loaded
  by id through `useTemplateDetail(id)`, and a route is deep-linkable/bookmarkable. A Dialog
  would have to fetch the detail lazily on open and re-implement a header; the route reuses
  the established `useParams` + `useTemplateDetail` pattern (identical to TemplateDetailPage)
  with no new state plumbing on the list page. Route is `"/test-templates/:id/worksheet"` —
  the distinct `/worksheet` suffix means react-router matches it ahead of `/:id` with no
  conflict (a longer, more specific static-segment path wins), so the existing detail route
  is untouched.

- **Rendering source: the template `definition` only, NOT `computed`.** This is the one place
  the preview MUST diverge from `PrintWorksheetPage`. That page reads `detail.computed.rows`
  / `detail.computed.values`, which only exist for a real saved `Worksheet` instance
  (fetched via `useWorksheet`). For THIS feature no worksheet instance exists — we only have
  the `TestTemplate.definition` from `useTemplateDetail`. So the preview renders the *layout
  skeleton* from the definition: context fields, each group's fields as table headers/rows,
  calculated fields, acceptance criteria and reportable result — with empty/placeholder cells
  (an em dash) and no values. It reuses `PrintWorksheetPage`'s structural approach (singleton
  = 2-up field grid, table/sequence = columnar table, `header(field)`/`visibleFields` helpers,
  the `chunk` helper, the criteria + reportable-result footer) but drops every `computed`
  lookup. This keeps it purely display, no data entry, no save, no backend calls beyond the
  `useTemplateDetail` fetch already used by the detail page.

- **Why not reuse `WorksheetForm`:** it is an editable, stateful form driven by a
  `WorksheetDetail` (worksheet + computed) and the live `usePreview` recalculation hook, and
  it fires preview requests to the backend. That violates the "read-only, no backend calls"
  constraint and requires data we do not have. A dedicated lightweight read-only renderer is
  correct.

- **Row count for table/sequence groups in the preview:** render the group's declared default
  row count (`group.rows?.default ?? group.rows?.min ?? 1`, matching `WorksheetForm.rowCount`)
  as blank numbered rows, so the viewer shows the real shape of the worksheet (e.g. "6 rows")
  rather than an empty table. Mirrors how a freshly created worksheet seeds its rows.

## Project facts (verified during exploration)

- Build/verify command: `npm run build` (runs `tsc -b && vite build`) from
  `d:\RD-instance\GIT\frontend-react`. Also `npm run lint` (eslint). There is **no test
  framework** in this project (no vitest/jest, no `*.test.tsx`), so verification is the
  TypeScript build + lint + a manual click-through on the dev server (`npm run dev`).
- Path aliases (`@features/*`, `@shared/*`, `@app/*`) are configured in `tsconfig.json`;
  the barrel `@features/test-templates` is the import surface used by `AppRouter.tsx`.
- `TestTemplate` extends `TestTemplateSummary` and adds `definition: TemplateDefinition`.
  `TemplateDefinition` = `{ context?: FieldDef[]; groups?: GroupDef[]; criteria?: CriterionDef[];
  resultRef?: string | null }`. `GroupDef` has `kind` (`singleton` | `table` | `sequence`),
  `fields: FieldDef[]`, optional `rows`, `footer`, `headerContext`, `chart`. Summary rows on
  the list are `TestTemplateSummary` with `id, code, name, archetype, version, status,
  result_unit, approved_by, test_code, test_name`.
- `describeDefinition(definition)` returns counts + `resultRef`; `formatLimit(operator, limit)`
  renders a criterion limit — both reusable in the preview header/criteria section.

---

## Ordered implementation items

- [ ] 1. Create the read-only preview page `WorksheetPreviewPage`.
      Create a new page that reads `:id` from `useParams`, fetches the full template via
      `useTemplateDetail(Number(id))`, and renders a read-only worksheet layout from
      `template.definition` ONLY (no `computed`, no `usePreview`, no save). Handle loading
      (`<p>Loading…</p>`) and not-found (`<Message severity="warn" text="Template not found." />`)
      exactly like TemplateDetailPage. Include a "Back to Templates" text Button with
      `pi pi-arrow-left` (navigate to `/test-templates`) consistent with existing pages.
      Header block shows the worksheet name `CODE NAME` prominently plus archetype, bound test
      (`test_name (test_code)`), version (`v{version}`), status badge (`StatusBadge`), and
      result unit — reuse the header styling from TemplateDetailPage.
      Body renders, in order:
        - Context section: `definition.context` fields as read-only label/value pairs with em-dash
          placeholders (reuse the 2-up `chunk(fields, 2)` grid idea from PrintWorksheetPage).
        - Each `definition.groups` group: `singleton` → a 2-up field grid of `header(field)` with
          blank cells; `table`/`sequence` → a table with a `#` column plus one column per visible
          field (`visibleFields` = non-hidden), rendering `rows?.default ?? rows?.min ?? 1` blank
          numbered rows. Skip the `chart` group's plotting (no data to plot); render just its
          label and a short "Chart (no data in preview)" note, or omit — keep it simple and
          read-only. Use disabled PrimeReact inputs OR plain em-dash text cells; prefer plain
          text cells (lighter, unambiguously non-interactive).
        - Acceptance criteria: list `definition.criteria` with label + limit via
          `criterion.limitText || formatLimit(operator, Array.isArray(limit) ? limit : [limit])`
          and a "Not assessed" `Tag` (there are no observed values in a preview).
        - Reportable result: show `definition.resultRef ?? 'not set'` and the template
          `result_unit`.
      Use PrimeReact `Card`, `Column`/`DataTable` or plain tables (match PrintWorksheetPage's
      table styling or TemplateDetailPage's Card layout — pick Card + simple tables for an
      in-app view). Keep aria-labels on interactive elements and `role="img"`-style a11y where
      relevant. Add a top-of-file doc comment describing it as a definition-derived, read-only
      preview with no data entry/save/backend calls (matching the house doc-comment style).
      Files: `d:\RD-instance\GIT\frontend-react\src\features\test-templates\pages\WorksheetPreviewPage.tsx` (new)
      Verify: `npm run build` from `d:\RD-instance\GIT\frontend-react` compiles with no TS errors;
      `npm run lint` passes for the new file.

- [ ] 2. Export the new page from the feature barrel.
      Add `export { WorksheetPreviewPage } from './pages/WorksheetPreviewPage';` to the barrel,
      alongside the existing page exports (TemplateListPage, TemplateDetailPage,
      PrintWorksheetPage).
      Files: `d:\RD-instance\GIT\frontend-react\src\features\test-templates\index.ts`
      Verify: `npm run build` — the barrel re-export resolves with no TS errors.

- [ ] 3. Register the preview route in the router.
      Import `WorksheetPreviewPage` from `@features/test-templates` (add it to the existing
      `import { PrintWorksheetPage, TemplateDetailPage, TemplateListPage } from '@features/test-templates';`
      line, keeping alphabetical-ish order). Add inside the `<MainLayout>` block, immediately
      after the `<Route path="/test-templates/:id" element={<TemplateDetailPage />} />` line:
      `<Route path="/test-templates/:id/worksheet" element={<WorksheetPreviewPage />} />`.
      The `/worksheet` suffix is more specific than `/:id`, so it does not break the existing
      detail route. (Place it inside MainLayout — unlike PrintWorksheetPage, this is an in-app
      view that should keep the sidebar/topbar.)
      Files: `d:\RD-instance\GIT\frontend-react\src\app\router\AppRouter.tsx`
      Verify: `npm run build` compiles; `npm run dev` then navigate to
      `/test-templates/<someId>/worksheet` and confirm the preview page renders inside the
      app shell and the existing `/test-templates/<someId>` detail page still renders.

- [ ] 4. Add the "Worksheet" column to the list DataTable.
      In TemplateListPage, add a new `<Column header="Worksheet" ...>` to the `<DataTable>`,
      placed right after the existing `<Column field="name" header="Name" />`. Its `body`
      renders a text-style PrimeReact `Button` (`text`, `size="small"`, matching the existing
      "View" action button) with `label={` + "`${row.code} ${row.name}`" + `}`, an
      `aria-label` such as `` `View worksheet for ${row.code} ${row.name}` ``, and
      `onClick={() => navigate(`/test-templates/${row.id}/worksheet`)}`. Reuse the already-
      imported `Button` and `useNavigate`; no new imports needed. Leave the existing "View"
      Actions column unchanged.
      Files: `d:\RD-instance\GIT\frontend-react\src\features\test-templates\pages\TemplateListPage.tsx`
      Verify: `npm run build` compiles; `npm run dev`, open `/test-templates`, confirm the
      Worksheet column shows `CODE NAME` as a link per row, clicking it navigates to the
      preview, and the existing "View" button still opens the detail page.

- [ ] 5. Full verification pass.
      Run the production build and lint across the whole frontend to confirm nothing else broke.
      Files: none (verification only)
      Verify: from `d:\RD-instance\GIT\frontend-react`, `npm run build` completes successfully
      (tsc + vite) and `npm run lint` reports no new errors. Manual: on the dev server the
      Worksheet column renders, the preview is read-only (no editable inputs, no Save button,
      no network calls beyond the template GET), and both `/test-templates/:id` and
      `/test-templates/:id/worksheet` resolve correctly.

## Notes / assumptions

- No automated test framework exists, so items are verified by `npm run build` + `npm run lint`
  plus a manual click-through. If the implementer wants a regression guard, that is out of scope
  here (would require introducing vitest + RTL, which the project does not currently use).
- The preview intentionally shows blank/placeholder cells because a template has no entered
  data; this is the correct representation of "what a worksheet created from this template
  looks like" before any analyst input.
- Chart groups are shown as a labeled placeholder (no plotted data) since plotting requires
  computed rows that only a real worksheet has.
