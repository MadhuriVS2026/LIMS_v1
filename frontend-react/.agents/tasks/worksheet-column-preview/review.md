# Worksheet column + read-only worksheet preview for test templates

Adds a clickable "Worksheet" column to the Test Templates list that renders `CODE NAME` and navigates to a new read-only preview page. `WorksheetPreviewPage` is reached at `/test-templates/:id/worksheet`, reuses `useTemplateDetail`, and renders the worksheet layout skeleton from `template.definition` — context fields, group tables, acceptance criteria, reportable result — with em-dash placeholder cells, no inputs, no save, and no new backend calls. This is a later review pass: the working tree is exactly four frontend files (three modified, one new), and the one blocker carried from pass 2 — missing build/lint evidence — is now resolved by a `verification.md` recording a passing `npm run build`.

**Watch for:** `npm run lint` could not run because eslint is not an installed dependency of this project; the authoritative type-check (`tsc -b` via `npm run build`) passed and I independently confirmed eslint's absence (confirmed).

**Verdict**: APPROVED

## High-level view

The list page gains one `<Column header="Worksheet">` whose cell is a `text` `Button` labelled `` `${row.code} ${row.name}` `` with a matching `aria-label`, wired to the already-imported `navigate` and `Button`; the existing "View" action column is untouched (AC1). The route `/test-templates/:id/worksheet` is registered after `/test-templates/:id`, so the longer static suffix wins the match and the detail route still resolves; the page is barrel-exported and imported in `AppRouter` from `@features/test-templates` (AC4).

The preview is read-only by construction. It renders from `definition` only — never `computed`, which belongs to a saved worksheet instance — so the sole network call is the template GET that `useTemplateDetail` already performs, and every cell is plain text with no editable or disabled control (AC2, AC5). The header shows `CODE NAME`, version, status, archetype, bound test, and result unit (AC3). Calculated columns carry a `calc` `Tag`, which closed the pass-1 AC2 observation.

Scope is clean: the diff is four frontend files, no backend file is modified, and the chart feature that previously inflated the diff is gone. The remaining pass-2 blocker — no recorded verification — is now resolved: `verification.md` records `npm run build` (`tsc -b && vite build`) passing with zero TypeScript errors, and documents that `npm run lint` cannot run because eslint is not installed in this project. I confirmed that condition against `package.json` and the repo: it is pre-existing and unrelated to this change, not a regression, so the passing build is the authoritative verification for a TypeScript project with no test framework.

<details>
<summary>Issues (0)</summary>

No blocking findings. The lint-not-runnable condition is a pre-existing project state (no eslint dependency, no eslint config at the repo root), documented in `verification.md` and independently confirmed; it is noted for awareness, not as an action item for this change.

</details>

<details>
<summary>Details</summary>

### Route registration

```
/test-templates              → TemplateListPage
/test-templates/:id          → TemplateDetailPage   (unchanged)
/test-templates/:id/worksheet→ WorksheetPreviewPage (new)
```

The route is added after `/:id` inside `MainLayout`, so react-router matches the more specific `/:id/worksheet` ahead of `/:id` and the detail route is unaffected — the one place a route addition could regress the existing detail page.

### Read-only preview rendering

The one divergence from `PrintWorksheetPage` worth noting: that page reads `computed.rows` / `computed.values`, which only exist for a saved worksheet instance, whereas the preview reads only `template.definition`. That is what keeps the page valid for a template with no worksheet, and it is why read-only is structural (plain `<td>{EMPTY}</td>` cells) rather than disabled inputs that could be re-enabled. All imports (`useTemplateDetail`, `formatLimit`, `StatusBadge`, `FieldDef`/`GroupDef`) resolve against the current module shapes.

### Verification evidence

`verification.md` records the build run from `d:\RD-instance\GIT\frontend-react`:

```
> anti-gravity-lims-frontend@2.0.0 build
> tsc -b && vite build
✓ 325 modules transformed.
✓ built in 3.51s
```

`npm run build` passed with exit code 0 and zero TypeScript errors; `tsc -b` precedes `vite build` and gates on type-check success, so this covers all four changed/added frontend files. The only notice is Vite's generic chunk-size warning, which is pre-existing and unrelated.

`npm run lint` could not run: eslint is not installed. I verified this directly — `package.json` `devDependencies` lists only `@types/react`, `@types/react-dom`, `@vitejs/plugin-react`, `typescript`, and `vite` (no eslint), and there is no eslint config at the repo root (the only `.eslintrc` hits are inside unrelated transitive `node_modules` packages). Installing eslint and authoring a config would add tooling the project does not use, which is out of scope. For a TypeScript project with no test framework, the passing `tsc -b` build is the authoritative verification, so the evidence requirement is met.

### Resolved since prior passes

The two scope blockers from the earlier passes are gone from the working tree. The backend `evaluator.py` change no longer appears — the diff is frontend-only, satisfying AC5. The chart feature (`renderChart` / `chartSeries` in `WorksheetForm`, `PrintChart` in `PrintWorksheetPage`, `ChartConfig`/`ChartSeries` types) is also absent, so the diff is now the four files the task scopes it to. The pass-2 blocker — missing build/lint evidence — is resolved by `verification.md`.

</details>

<details>
<summary>File map</summary>

- `frontend-react/src/features/test-templates/pages/WorksheetPreviewPage.tsx` (new) — read-only, definition-derived worksheet preview.
- `frontend-react/src/features/test-templates/pages/TemplateListPage.tsx` — adds the "Worksheet" column.
- `frontend-react/src/app/router/AppRouter.tsx` — registers `/test-templates/:id/worksheet`.
- `frontend-react/src/features/test-templates/index.ts` — exports `WorksheetPreviewPage`.

Full diff: `git diff` plus the untracked `WorksheetPreviewPage.tsx`, from `d:\RD-instance\GIT\frontend-react`.

</details>
