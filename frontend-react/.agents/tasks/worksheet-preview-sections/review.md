# Section-wise Excel-like rework of the read-only worksheet-preview page

The renderer `WorksheetPreviewPage.tsx` is reworked into a compact, bordered, Excel-sheet layout that is driven entirely by the template `definition` shape. It renders five section types — context key/value grid, singleton key/value blocks, numbered table/sequence tables (now including `headerContext` above and `footer` beneath), acceptance-criteria table with per-criterion severity, and a reportable-result block — all read-only with blank em-dash placeholder cells. The renderer stays generic (no per-archetype or per-template branching) and makes no backend call beyond the existing `useTemplateDetail` GET. The renderer file is clean on its own merits.

Watch for: the working tree changes **five** frontend files, not the one the task authorizes (confirmed) — the extra four are reachability wiring plus one unrelated TRF-dropdown change that does not belong to this task's scope. The renderer code itself meets every behavioral requirement.

**Verdict**: NEEDS_CHANGES

## High-level view

The renderer is correct and complete against the behavioral spec. It walks `definition.context`, `definition.groups`, `definition.criteria` and `definition.resultRef` with a single generic code path per section kind, guards every optional array (`?? []` / `.length > 0`), and never emits an editable input. `group.headerContext` and `group.footer` — previously ignored — are now rendered as a shaded summary strip above and a Mean/SD/%RSD-style `tfoot` strip below each table. Criterion severity is surfaced as a blocking/advisory Tag, defaulting to `blocking` when `severity` is absent, which is the safe default.

The gating problem is scope, not behavior. The task authorizes exactly one changed file (`WorksheetPreviewPage.tsx`) and checklist item 1 requires that no other frontend file is modified. The working tree modifies four additional tracked files: `AppRouter.tsx` (new `/test-templates/:id/worksheet` route), `test-templates/index.ts` (re-export), `TemplateListPage.tsx` (new Worksheet column), and `TRFDetailPage.tsx` (Add-Test-Line template dropdown). The verification note records a parent-session "decision B" relaxing the single-file rule to cover these, but the authoritative task text under review does not carry that relaxation, and checklist item 1 is written as a hard gate. No backend file was touched, so the most severe failure mode (backend edit) is avoided, but item 1 as written does not hold.

Build evidence exists and shows `npm run build` (`tsc -b && vite build`) passing with zero TypeScript errors; the only warning is the pre-existing chunk-size advisory. ESLint absence is a known, acceptable gap.

<details>
<summary>Issues (2)</summary>

1. **Scope exceeds the single authorized file** — the diff modifies five frontend files (`WorksheetPreviewPage.tsx` plus `AppRouter.tsx`, `test-templates/index.ts`, `TemplateListPage.tsx`, `TRFDetailPage.tsx`); checklist item 1 authorizes only `WorksheetPreviewPage.tsx`. Either narrow the working tree to the single file or obtain the scope relaxation in the authoritative task text (not only the verification note). (confirmed)
2. **Unrelated TRF change bundled in** — `TRFDetailPage.tsx` reworks the Add-Test-Line dropdown to list test templates; this is a separate earlier task, not part of the worksheet-preview rework, and should not ride in this diff. (confirmed)

</details>

<details>
<summary>Details</summary>

### Checklist item 1 — exactly one changed file

Does not hold (confirmed). `git status` shows four tracked modifications (`src/app/router/AppRouter.tsx`, `src/features/test-templates/index.ts`, `src/features/test-templates/pages/TemplateListPage.tsx`, `src/features/trf/pages/TRFDetailPage.tsx`) plus the untracked new renderer `src/features/test-templates/pages/WorksheetPreviewPage.tsx`. The task authorizes only the renderer. No file under `backend-v2` was touched, so there is no backend violation. The verification note cites a parent "decision B" relaxing the constraint, but that relaxation is not present in the authoritative task-under-review text, which states the renderer is "the ONLY file that may change." The route/export/list-column edits are plausible reachability wiring for the new page; the `TRFDetailPage.tsx` change is an unrelated test-template-dropdown task bundled into the same working tree.

### Checklist item 2 — build evidence

Holds (confirmed). `verification.md` records `npm run build` (`tsc -b && vite build`) passing with zero TypeScript errors (`✓ 325 modules transformed`, exit code 0). The sole warning is the pre-existing Vite chunk-size advisory. ESLint is not installed; per the task this absence is not a defect. Per instruction I did not re-run the build.

### Checklist item 3 — generic, definition-driven rendering

Holds (confirmed). Every section is derived from the `definition` shape with no archetype or template-name conditionals. Context fields chunk into a two-pair key/value grid; groups branch only on `group.kind === 'singleton'` versus the table/sequence path (a structural distinction from the schema, not a per-template branch); criteria and the reportable result read straight from `definition.criteria` and `definition.resultRef`. The `fieldHeader` helper adds the `calc` Tag purely from `field.kind === 'calculated'`, keeping the calculated-field marker generic.

### Checklist item 4 — headerContext and footer now rendered

Holds (confirmed). In the table/sequence branch, `const headerContext = group.headerContext ?? []` renders a shaded summary strip (chunked three-per-row) above the table, and `const footer = group.footer ?? []` renders a `tfoot` strip beneath it with each item's label, optional unit, and a blank placeholder. Both were previously ignored and both appear in the new file. Items are keyed by `item.ref`, consistent with `GroupHeaderContextItem.ref` and `GroupFooterItem.ref` in the schema.

### Checklist item 5 — criterion severity surfaced

Holds (confirmed). Each criterion row renders a Tag whose value and color come from `(c.severity ?? 'blocking') === 'advisory'` — advisory as a `warning` Tag, blocking as `danger`. Defaulting undefined severity to `blocking` is the conservative choice and matches the schema's `Severity` type.

### Checklist item 6 — read-only preserved

Holds (confirmed). There are no form controls that accept entry; `Placeholder` renders a static em-dash, numbered rows are generated from `rowCount(group)`, and the criteria Result column shows a static "Not assessed" Tag. The only data source is `useTemplateDetail(templateId)`, the existing GET — no mutation or additional fetch is introduced. The header block (code/name, version, status badge, archetype/test/result-unit line, read-only note) and the "Back to Templates" button are all present.

### Checklist item 7 — guards for undefined/empty definition parts

Holds (confirmed). `contextFields`, `groups`, `criteria`, `headerContext`, and `footer` all use `?? []` and render behind `.length > 0` guards; `visibleFields` guards `group.fields ?? []`; `rowCount` falls back through `rows.default ?? rows.min ?? 1`; and `resultRef`/`result_unit` fall back to literal strings. A template lacking footer, headerContext, or criteria renders cleanly with those sections simply omitted.

### Styling and schema

Matches the stated Excel-sheet target (`border-1 border-200`, `bg-gray-50` header/label cells, `p-1`, `text-sm`, right-aligned numeric cells), and no schema change was needed — as the task predicted. The one blocking matter is scope (item 1), not the renderer's behavior.

</details>

<details>
<summary>Files changed</summary>

- `src/features/test-templates/pages/WorksheetPreviewPage.tsx` (new) — generic, read-only, definition-driven Excel-like worksheet preview; renders all 5 sections including the newly-surfaced group headerContext and footer strips.
- `src/app/router/AppRouter.tsx` — adds `/test-templates/:id/worksheet` route (outside authorized scope).
- `src/features/test-templates/index.ts` — re-exports `WorksheetPreviewPage` (outside authorized scope).
- `src/features/test-templates/pages/TemplateListPage.tsx` — adds Worksheet column linking to the preview (outside authorized scope).
- `src/features/trf/pages/TRFDetailPage.tsx` — unrelated Add-Test-Line template dropdown rework (outside authorized scope).

Full diff: `git diff` plus the untracked `WorksheetPreviewPage.tsx` in the working tree.

</details>
