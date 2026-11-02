# Design — Universal Product Master + MRN Consumption

**Repo:** `D:\RNDLIMS-app` (the MRN/R&D-LIMS enterprise monorepo — NOT the LIMS templates repo `d:\RD-instance\GIT`)
**Target sub-app:** `mrn-frontend` (React 19 + TS, PrimeReact, Redux Toolkit, `useSyncExternalStore`), served on `http://localhost:5175`
**Scope:** Add a universal **Product Master** that mirrors the existing universal **Project Master** exactly (same storage, API shape, table conventions, routing/sidebar), and wire **product selection into the MRN flow** the same way projects are wired. Do NOT change Project Master behavior, the LIMS templates repo, or unrelated features.

---

## 1. Investigation findings (where the real Project Master lives)

The single most important finding: **the universal Project Master is NOT backed by a database or any backend service. It is an in-memory TypeScript store inside `mrn-frontend`, and that store is the real source of truth for the `/masters/projects` page AND for the "active projects" dropdown on the Raise MRN flow.** There is no alembic migration, no FastAPI endpoint, and no shared masters microservice behind it. `mrn-backend` contains no project/master code at all (only `scripts/seed_rbac.py`, which is RBAC-only; the only `alembic` present is the one bundled inside `mrn-backend/.venv`, i.e. the library, not a project migrations tree). A second, unrelated copy of a "Project Master" screen exists in `timesheet-ui` (`src/pages/admin/masters/ProjectMaster.jsx`) but that is the legacy portal and is out of scope; the app the user is viewing on :5175 is `mrn-frontend`.

Concrete locations and mechanisms:

### 1.1 Data model / schema + seed
- **File:** `mrn-frontend/src/features/material/data/materialStore.ts`
- **Type:** `ProjectMasterRow` interface (approx. lines 150–175): `id, projectId, projectDetails, productName, productCode, projectCode, academicResearchCode, bdCode, groupLead, location, market, startDate, endDate, license, comments, status ('Active'|'Inactive'), requestedPerson, remarks, costCenter, department`.
- **Seed:** `SEED_PROJECT_MASTER: ProjectMasterRow[]` (approx. lines 177–215) — 4 rows (`PM-0001`..`PM-0004`), e.g. `PID-2026-001 / Doxorubicin Liposome / PRD-DOXO-01 / PRJ-ONCO-01`.
- **State wiring:** `interface State { … projectMaster: ProjectMasterRow[] … }` and `const state: State = { … projectMaster: [...SEED_PROJECT_MASTER] … }`.
- **Reactivity:** module-level `state` + `listeners` set + `notify()` (bumps `snapshotVersion`) + `subscribe/getVersion`; components subscribe via `export function useMaterialStore(): State { useSyncExternalStore(subscribe, getVersion, getVersion); return state; }`.

### 1.2 "API" endpoints (there is no HTTP API — these are store functions)
The store exposes the project master through plain exported functions that every component calls directly (the file's own comment says "Every mutation maps 1:1 to a future apiClient call so pages don't change when a real backend lands"):
- **List:** read `store.projectMaster` (via `useMaterialStore()`).
- **Active filter:** `export const activeProjects = (): ProjectMasterRow[] => state.projectMaster.filter((p) => p.status === 'Active');`
- **Lookup:** `export const getProject = (code) => …` (by `projectCode`).
- **Create:** `export function addProjectMaster(input, actorId): MutationResult<ProjectMasterRow>` — validates `projectCode` required + unique, generates `id = PM-####`, appends, `logAudit('ADD_PROJECT', …)`, `notify()`.
- **Update/Delete:** the generic grid CRUD `updateRow(collection, id, patch, actor)` / `deleteRow(collection, id, actor)`, where `collection` is a member of the union `export type Collection = 'receipts' | … | 'projectMaster' | …`. Both log audit and `notify()`.
- **Legacy compat:** `projectList()` and the `PROJECT_MASTER` Proxy derive the old `Project` shape live from `projectMaster` so they never drift.

### 1.3 Frontend page + routing + sidebar
- **Page:** `mrn-frontend/src/features/material/pages/ProjectMasterPage.tsx`. Renders a header + note ("Authoritative project list. Active projects populate the Project dropdown on the Raise MRN page."), an admin-gated `Toolbar` with a **New Project** button opening a `Dialog` form, and a `MaterialDataTable<ProjectMasterRow>` with `collection='projectMaster'` (admin) or `undefined` (read-only). Admin signal = `useMenuPermission('roles').canAccess`.
- **Table wrapper:** `mrn-frontend/src/features/material/components/MaterialDataTable.tsx` — PrimeReact `DataTable` with global search box, `filterDisplay="row"` per-column filters, `editMode="row"` inline edit (when `collection` set) via `updateRow`, delete via `confirmDialog`+`deleteRow`, an always-present editable **Comments** column, `paginator rows={10} rowsPerPageOptions={[10,25,50]}`. Columns described by `MatColumn<T>[]` (`field, header, body?, editor?, sortable?, filter?, style?`).
- **Barrel:** `mrn-frontend/src/features/material/index.ts` re-exports every page, incl. `export { ProjectMasterPage } from './pages/ProjectMasterPage';`.
- **Route:** `mrn-frontend/src/app/router/AppRouter.tsx` — imported from `@features/material`, registered as `<Route path="masters/projects" element={<PrivateRoute menuKey="dashboard"><ProjectMasterPage /></PrivateRoute>} />` under the `MainLayout` protected tree. RBAC guard = `PrivateRoute` with `menuKey="dashboard"`.
- **Sidebar:** `mrn-frontend/src/app/layouts/MainLayout.tsx` — `navItems` entry `{ label: 'Project Master', icon: 'pi pi-folder', path: '/masters/projects', section: 'Masters', menuKey: 'dashboard' }`. Items are grouped by `section`; "Masters" is an existing section containing only Project Master today. Visibility filtered by `menuKeys.includes(item.menuKey)`.

### 1.4 How MRN consumes the Project Master (the pattern to mirror)
- **File:** `mrn-frontend/src/features/material/pages/RaiseMrnPage.tsx`.
- **Consumption level:** **LINE level.** Raise MRN renders a PrimeReact `DataTable` of the selected New-MRN lines; each line has its own **Project Code (BD-code)** column rendered as a filterable `Dropdown`. There is no header-level project pick.
- **Wiring:** `import { … activeProjects … } from '../data/materialStore'`; `const projects = activeProjects();` then the column body:
  ```tsx
  <Dropdown value={lineFor(r.id).projectCode}
    options={projects.map((p) => ({ label: `${p.projectCode} — ${p.productName || p.projectDetails}${p.bdCode ? ` (${p.bdCode})` : ''}`, value: p.projectCode }))}
    onChange={(e) => onProjectChange(r.id, e.value)} placeholder="Select project…" filter />
  ```
  `onProjectChange` looks the project up in `projects` and auto-fills `projectName`/`department` from the master. On submit, `raiseMrn(lines, actor)` validates each `projectCode` against `getProject()` and creates allocations.
- **Downstream:** `allocate`, `issueMaterial`, `allocateSto`, `issueSto` all validate `getProject(projectCode)` and copy `costCenter`/`department` from the master. The New-MRN type (`NewMrnRow`) stores `projectName` + `projectCode`.

**Decision resolved by investigation (no escalation needed):** storage = in-memory store (not DB); MRN consumption = line level. The Product Master will mirror both exactly.

### 1.5 Reconciliation with the LIMS Products list
The LIMS app (`lims-frontend` :5174, backend `lims-backend`) has its own **real DB-backed** Product entity — `lims-backend/src/domain/entities/product.py` and `src/api/v1/schemas/product_schemas.py`: `code, name, description, material_type (RM/PM/FG/IP), retest_period_days, storage_condition, status (Pending Approval/Active/Inactive), approved_by, approved_at`. The LIMS `ProductsPage.tsx` shows card tiles with name, code, description, status.
**This LIMS Product entity is a separate system and is explicitly out of scope to change.** We only borrow its *field vocabulary* (code/name/description/status) and its seed products (Propofol `PRD-PROP-10`, Pemetrexed `FRD-002`) to populate the new MRN-side Product Master. The new Product Master lives entirely in `mrn-frontend`'s in-memory store, exactly like the Project Master — it does not call `lims-backend`.

---

## 2. Technology stack (locked)

Mirrors the Project Master's stack. No new libraries.
- Store: in-memory TypeScript module state in `materialStore.ts`, reactive via `useSyncExternalStore`.
- UI: React 19 + PrimeReact (`DataTable`, `Dropdown`, `Dialog`, `InputText`, `Toolbar`, `Tag`, `Message`, `Toast`), the shared `MaterialDataTable` wrapper.
- Routing: `react-router-dom` with `PrivateRoute` (`menuKey="dashboard"`).
- State access: `useAppSelector` for the acting user, `useMenuPermission('roles')` for admin gating.

---

## 3. Product Master data model (final columns + types)

New interface `ProductMasterRow` in `materialStore.ts`. Columns mirror the Project Master structure where sensible and reconcile with LIMS Product fields. Final set:

| Field (TS) | UI header | Type | Notes |
|---|---|---|---|
| `id` | Sr No | `string` | Backing id, generated `PM-PRD-####` (distinct from Project Master's `PM-####`) |
| `productId` | Product ID | `string` | Human id, e.g. `PRD-2026-001` (mirrors `projectId`) |
| `productCode` | Product Code | `string` | **Natural key** (unique), e.g. `PRD-PROP-10` (mirrors `projectCode`'s role) |
| `productName` | Product Name | `string` | e.g. "Propofol 1% (10mg/mL) Injectable Emulsion" |
| `description` | Description / Details | `string` | Free text (mirrors `projectDetails`; aligns to LIMS `description`) |
| `genericName` | Generic Name | `string` | e.g. "Propofol" |
| `materialType` | Material Type | `string` | RM / PM / FG / IP (borrowed from LIMS `material_type`); free text/dropdown |
| `bdCode` | BD Code (SAP) | `string` | SAP material/BD code (mirrors Project `bdCode`) |
| `groupLead` | Owner / Group Lead | `string` | mirrors Project `groupLead` |
| `market` | Market | `string` | mirrors Project `market` |
| `status` | Status | `'Active' \| 'Inactive'` | drives the "active products" filter (mirrors Project `status`) |
| `remarks` | Remarks | `string` | mirrors Project `remarks` |
| `comments` | Comments | `string` | **required by `MaterialDataTable`** (the editable Comments column) |

Notes on reconciliation: LIMS `retest_period_days`, `storage_condition`, and the LIMS-specific "Pending Approval" status are intentionally **omitted** — the Project Master has no equivalent approval workflow and adding one would diverge from the pattern. Status is the two-value `Active`/`Inactive` union used by `activeProjects()`, so `activeProducts()` is a clean mirror.

---

## 4. Store changes (`materialStore.ts`) — the "API"

All additions live in `mrn-frontend/src/features/material/data/materialStore.ts`, mirroring the project functions 1:1.

1. **Type:** add `export interface ProductMasterRow { … }` (Section 3 fields).
2. **Seed:** add `const SEED_PRODUCT_MASTER: ProductMasterRow[]` with these rows (from LIMS + the products implied by the Project Master's Product Name/Code columns):

   | id | productId | productCode | productName | genericName | materialType | bdCode | status |
   |---|---|---|---|---|---|---|---|
   | PM-PRD-0001 | PRD-2026-001 | PRD-PROP-10 | Propofol 1% (10mg/mL) Injectable Emulsion | Propofol | FG | BD-100310 | Active |
   | PM-PRD-0002 | PRD-2026-002 | FRD-002 | Pemetrexed | Pemetrexed | FG | BD-100311 | Active |
   | PM-PRD-0003 | PRD-2026-003 | PRD-DOXO-01 | Doxorubicin Liposome | Doxorubicin | FG | BD-100231 | Active |
   | PM-PRD-0004 | PRD-2026-004 | PRD-AMPHO-02 | Amphotericin B | Amphotericin B | FG | BD-100240 | Active |
   | PM-PRD-0005 | PRD-2026-005 | PRD-PARA-03 | Paracetamol ER | Paracetamol | FG | BD-100255 | Active |
   | PM-PRD-0006 | PRD-2026-006 | PRD-MABX-04 | mAb-X | Monoclonal Antibody X | FG | BD-100261 | Inactive |

   (`PRD-MABX-04` seeded Inactive to exercise the active filter, mirroring the Project Master's inactive `PM-0004`.) Remaining string fields default to `''`; `groupLead`/`market` copied from the matching project rows where one exists.
3. **State:** extend `interface State` with `productMaster: ProductMasterRow[]` and initialize `state.productMaster = [...SEED_PRODUCT_MASTER]`.
4. **Collection union:** add `'productMaster'` to `export type Collection` so the generic `updateRow`/`deleteRow` work on it unchanged (this is what powers inline edit + delete in the table).
5. **Selectors:**
   - `export const activeProducts = (): ProductMasterRow[] => state.productMaster.filter((p) => p.status === 'Active');`
   - `export const getProduct = (code: string): ProductMasterRow | undefined => state.productMaster.find((p) => p.productCode === code);`
6. **Create mutation:** `export function addProductMaster(input: Partial<ProductMasterRow>, actorId = 'SYSTEM'): MutationResult<ProductMasterRow>` — an exact structural copy of `addProjectMaster`: trims `productCode`, rejects empty, rejects duplicate `productCode`, generates `id = PM-PRD-${(count+1).padStart(4,'0')}`, fills defaults, status defaults `Active`, `logAudit(actorId, 'ADD_PRODUCT', id, …)`, `notify()`, returns `{ ok: true, value: row }`.

No change to any existing project function; `updateRow`/`deleteRow` need only the one union member added.

---

## 5. Frontend page + routing + sidebar

1. **New page:** `mrn-frontend/src/features/material/pages/ProductMasterPage.tsx` — a structural copy of `ProjectMasterPage.tsx`:
   - Header "Product Master" + note: "Authoritative product list. Active products populate the Product dropdown on the Raise MRN page."
   - Admin gate `const { canAccess: isAdmin } = useMenuPermission('roles');`; non-admins see the read-only `Message` + editor-less columns (`roColumns`).
   - `columns: MatColumn<ProductMasterRow>[]` for the Section-3 fields; `status` rendered with a `Tag` (`success`/`danger`), `productCode` bold as the key column, `id` as the Sr-No primary span — all mirroring the project page's column bodies.
   - Admin `Toolbar` with **New Product** button → `Dialog` form (same 2-col `formgrid p-fluid` layout; a `Dropdown` for Status `['Active','Inactive']`), submit → `addProductMaster`, with success/error `Toast`. Add button disabled until `productCode` is non-empty.
   - `<MaterialDataTable<ProductMasterRow> collection={isAdmin ? 'productMaster' : undefined} columns={…} rows={store.productMaster} rowId={(r) => r.id} actorId={actor} emptyMessage="No products yet." />`
2. **Barrel:** add `export { ProductMasterPage } from './pages/ProductMasterPage';` to `mrn-frontend/src/features/material/index.ts`.
3. **Route:** in `mrn-frontend/src/app/router/AppRouter.tsx`, add `ProductMasterPage` to the `@features/material` import and register, directly after the projects route:
   `<Route path="masters/products" element={<PrivateRoute menuKey="dashboard"><ProductMasterPage /></PrivateRoute>} />`
4. **Sidebar:** in `mrn-frontend/src/app/layouts/MainLayout.tsx`, add one `navItems` entry in the existing "Masters" section, right after Project Master:
   `{ label: 'Product Master', icon: 'pi pi-box', path: '/masters/products', section: 'Masters', menuKey: 'dashboard' }`.

---

## 6. MRN consumption wiring (line level, mirroring Project)

Products are consumed at the **line level** on `RaiseMrnPage`, exactly parallel to the existing per-line Project Code dropdown. Decision: line level (not header) because the existing MRN flow already selects project per New-MRN line and each material line is independently tied to a product; a header-level pick would not match the established pattern and would lose per-line fidelity.

Changes to `mrn-frontend/src/features/material/pages/RaiseMrnPage.tsx`:
1. Import the product selector: `import { … activeProducts … } from '../data/materialStore';` and `const products = activeProducts();`.
2. Extend `LineForm` with `productCode: string;` and `productName: string;` and seed them blank in the per-row state initializer (alongside the existing `projectCode`/`projectName`).
3. Add a **Product** column (placed just before/after the Project Code column) rendering a filterable `Dropdown` that mirrors the project dropdown exactly:
   ```tsx
   <Column header="Product *" style={{ minWidth: '15rem' }}
     body={(r: NewMrnRow) => (
       <Dropdown value={lineFor(r.id).productCode}
         options={products.map((p) => ({ label: `${p.productCode} — ${p.productName}`, value: p.productCode }))}
         onChange={(e) => onProductChange(r.id, e.value)}
         placeholder="Select product…" className="w-full" filter />
     )} />
   ```
4. Add `onProductChange(id, code)` that sets `productCode` and auto-fills `productName` from `products.find(p => p.productCode === code)` (mirror of `onProjectChange`).
5. Make product selection part of `allValid` (require `l.productCode`), mirroring the project requirement, so Submit stays disabled until each line has a product.

Store/type ripple needed to persist the choice through submit:
6. Add `productCode: string;` and `productName: string;` to **`NewMrnRow`** in `materialStore.ts` (defaulting `''` in `addToNewMrn`, `updateNewMrnRow`, and cleared in `clearNewMrnRow`), so the selected product travels with the line.
7. Extend `RaiseMrnLine` with `productCode: string;` and carry it in the `payload` built in `submit()`.
8. In `raiseMrn(lines, actor)`: after the project validation loop, validate each line's product via `getProduct(line.productCode)` (reject with "Select a valid Product for {sapBatchNo}." when missing), and stamp `productCode`/`productName` onto the created `Allocation`. This requires adding `productCode?: string;` and `productName?: string;` to the **`Allocation`** interface (optional, so existing seed allocations remain valid) and populating them in the two `Allocation` constructions inside `raiseMrn` (and leaving the other allocate paths to default `undefined`).

No change to the Project dropdown or any project function — product selection is added alongside, not in place of, project selection.

---

## 7. Error handling (per operation)

| Operation | Failure condition | Recoverable? | Caller receives | Logged? |
|---|---|---|---|---|
| `addProductMaster` | empty `productCode` | yes (user re-enters) | `{ ok:false, error:'Product Code is required.' }` → error Toast | no (validation, pre-mutation) |
| `addProductMaster` | duplicate `productCode` | yes | `{ ok:false, error:'Product Code {code} already exists.' }` → error Toast | no |
| `addProductMaster` | success | — | `{ ok:true, value }` → success Toast, dialog closes | yes — `ADD_PRODUCT` audit entry |
| `updateRow('productMaster', …)` | row id not found | yes | `{ ok:false, error:'Row not found.' }` | only on success — `EDIT` audit entry |
| `deleteRow('productMaster', …)` | row id not found | yes | `{ ok:false, error:'Row not found.' }` | on success — `DELETE` audit entry; delete confirmed via `confirmDialog` first |
| `raiseMrn` product validation | `getProduct(code)` undefined for a line | yes (user picks a valid product) | `{ ok:false, error:'Select a valid Product for {sapBatchNo}.' }` → error Toast; **whole submit aborts before any mutation** (validate-all-then-apply, matching the existing project validation) | no (pre-mutation) |
| Product Dropdown render | `activeProducts()` empty | n/a — fatal to selection only | Dropdown shows placeholder with no options; `allValid` stays false so Submit is disabled | no |

All errors are **recoverable** and surface as inline UI messaging — there are no fatal/unrecoverable paths because the store is in-memory and synchronous (mirrors the Project Master, which has no network or persistence failure modes). Logging level: single append-only audit log via `logAudit` (the module's existing mechanism); no console logging is added, matching the project functions.

---

## 8. Input validation (each external input)

| Input | Required? | Type | Limits / rules | On failure |
|---|---|---|---|---|
| New Product → Product Code | **required** | string | trimmed non-empty; unique across `productMaster` | Add button disabled while empty; duplicate rejected by `addProductMaster` with error Toast |
| New Product → Product Name, Description, Generic Name, Material Type, BD Code, Owner, Market, Remarks | optional | string | free text; empty → `''` | none (accepted as blank) |
| New Product → Status | required (defaulted) | `'Active' \| 'Inactive'` | dropdown-constrained; default `Active` | n/a (constrained input) |
| Inline grid edit (any editable cell) | n/a | string | written back verbatim via `updateRow` | row-not-found guarded |
| Raise MRN → Product (per line) | **required** | string (`productCode`) | must resolve via `getProduct`; dropdown-constrained to active products | `allValid` false → Submit disabled; server-side re-check in `raiseMrn` aborts submit |

The natural-key uniqueness invariant on `productCode` is owned by the **store layer** (`addProductMaster`), not the UI — because the store is the single source of truth and inline create/other callers must honor it too; the UI's disabled-button check is a convenience, not the enforcement point. This mirrors how `addProjectMaster` owns `projectCode` uniqueness.

---

## 9. Edge cases

- **No active products:** Raise MRN product dropdown is empty; Submit stays disabled (good — prevents raising against an empty master). Product Master page still renders with an empty-but-seeded grid.
- **All products Inactive:** same as above; `activeProducts()` returns `[]`. The master table still lists them (it reads `productMaster`, not the active filter).
- **Duplicate seed product codes:** seed data is authored unique; `addProductMaster` guards runtime dupes only. Seed is trusted input.
- **Deleting a product referenced by an existing allocation:** allocations store a copy of `productCode`/`productName` (denormalized at raise time), so deleting the master row does not corrupt historical allocations — mirrors how deleting a project row doesn't rewrite past allocations. No cascade.
- **Non-admin user:** Product Master is read-only (no Toolbar, editor-less columns, info `Message`) — identical gating to Project Master.
- **Product vs Project both required on a line:** both dropdowns are independent and both feed `allValid`; a line needs product AND project AND quantity to submit.
- **`timesheet-ui` legacy Project Master:** untouched; out of scope.

---

## 10. Testability

- **Unit-testable (pure store functions, no React):** `activeProducts()` filters only `Active`; `getProduct()` returns by code / `undefined`; `addProductMaster()` happy path returns `PM-PRD-0001`-style id and appends; rejects empty and duplicate codes; `updateRow('productMaster', …)`/`deleteRow('productMaster', …)` mutate and audit; `raiseMrn` rejects a line with an unknown `productCode` and stamps product onto created allocations on success. These are the highest-value tests and need no DOM — the store is a plain module with injectable `actorId`. If a test runner is not yet configured in `mrn-frontend`, add Vitest (the Vite-native standard for this stack) with a single `materialStore.productMaster.test.ts`.
- **Integration/component-testable:** `ProductMasterPage` renders seeded rows, admin sees New Product + inline edit, non-admin sees read-only message; `RaiseMrnPage` product dropdown lists only active products and Submit is disabled until a product is chosen. Testable with React Testing Library if/when the frontend adopts it.
- **Manual/E2E:** the `tsc -b` + Vite build must stay clean (the repo's existing bar), and the `/masters/products` page must render in the Emcure shell with the Masters sidebar entry — the same verification used when the Project Master shipped.
- **Design testability note:** because the Product Master is a 1:1 structural mirror of the Project Master with no new infrastructure, it inherits the Project Master's (already-shipping) testability profile; nothing here is hard to test, which is a good signal the design fits the existing seams.

---

## 11. Files to add / change (complete list)

**Add:**
- `mrn-frontend/src/features/material/pages/ProductMasterPage.tsx` — new master page (mirror of `ProjectMasterPage.tsx`).
- *(optional, if adding tests)* `mrn-frontend/src/features/material/data/materialStore.productMaster.test.ts`.

**Change:**
- `mrn-frontend/src/features/material/data/materialStore.ts` — add `ProductMasterRow`, `SEED_PRODUCT_MASTER`, `State.productMaster`, `'productMaster'` in `Collection`, `activeProducts`, `getProduct`, `addProductMaster`; extend `NewMrnRow` (+`productCode`,`productName`), `RaiseMrnLine` (+`productCode`), `Allocation` (+ optional `productCode`,`productName`); set product defaults in `addToNewMrn`/`updateNewMrnRow`/`clearNewMrnRow`; product validation + stamping in `raiseMrn`.
- `mrn-frontend/src/features/material/index.ts` — export `ProductMasterPage`.
- `mrn-frontend/src/app/router/AppRouter.tsx` — import + `masters/products` route.
- `mrn-frontend/src/app/layouts/MainLayout.tsx` — "Product Master" nav item in the Masters section.
- `mrn-frontend/src/features/material/pages/RaiseMrnPage.tsx` — product dropdown column, `onProductChange`, `LineForm` fields, `allValid` + submit payload.

**Explicitly NOT changed:** `ProjectMasterPage.tsx`, any project store function, `mrn-backend`, `lims-backend`/`lims-frontend` products, `timesheet-ui`, and the LIMS templates repo `d:\RD-instance\GIT`.
