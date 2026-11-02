# DB-backed Project Master resource under Resource Manager

The change adds a new **Project Master** resource to the LIMS app, mirroring the existing Instruments / Reference Standards slices end to end: a `project_master` table with 16 stored columns plus audit fields, list + create REST endpoints under `/api/v1/projects`, and a `ProjectMasterPage` in the React SPA with an Admin-gated Add dialog. The implementation is woven into the shared resource files (model, entity, repo interface/impl, service, schemas, endpoints, DI) exactly as the sibling resources are, introduces no new architecture, and adds a non-destructive seed path alongside the full-reset seed. Every layer was read and cross-checked against the design, plan, and the Reference Standards analogue.

Watch for: nothing blocking. The CRITICAL RBAC menu grant (`projects` in `MENU_ACCESS`) is present (confirmed), so the nav item renders for an Admin. Seed row sample data diverges cosmetically from the design's illustrative values (confirmed), with no behavioral impact.

**Verdict**: APPROVED

## High-level view

The backend follows the layered resource pattern precisely. `ProjectMasterModel` is registered in `models/__init__.py` (the single point that makes `create_all` build the table), the `ProjectMaster` entity/repo/service/schemas carry all 16 stored fields plus the derived `id` ("Sr No"), and the two endpoints are added to the already-registered `resource_router` with no `router.py` change needed. The `project_repo` constructor parameter sits before `audit_repo` in both the `ResourceService` signature and the DI wiring, so arity matches.

Authorization mirrors the siblings exactly: `GET /projects` is gated by `get_current_user`, `POST /projects` by `require_role("Admin")`. Uniqueness of `project_id` is owned by the DB index and surfaces as an `IntegrityError` through the shared exception middleware, consistent with how `code` behaves on every other resource — no bespoke handling added.

The frontend slice is fully wired: type, api client, two hooks, page, barrel export, route, and nav entry. The Add dialog captures all 16 editable fields (Status as an Active/Inactive dropdown, dates via `Calendar` → ISO, Comments/Remarks as textareas), and the list renders a readable column subset plus a derived Sr No. The `ProjectResponse` schema returns all 16 fields (the sibling responses trim theirs); this is a superset, harmless to the frontend.

The nav-visibility gate — the most common failure mode — is handled: `projects` is in `MENU_ACCESS` granting the four base roles, and the `NAV_ITEMS` entry's `menuKey` matches, so `useMenuPermissions()` yields it for an Admin.

Table creation is non-destructive. The dev DB was seeded via a dedicated idempotent one-shot (`create_all` + guarded inserts) with a backup taken first; the destructive `seed_data.py` block was added for full-reset parity but not executed. Tests establish the first resource-manager suite (5 unit + 3 API) and the recorded evidence shows them green plus a clean frontend build and the list endpoint returning the 3 seeded rows.

<details>
<summary>Issues (1)</summary>

1. **Seed sample-data drift (non-blocking)** — `seed_data.py` / `seed_project_master.py` use group leads "Meera Nair"/"Arjun Rao" and other minor values that differ from the design's illustrative "Grace Leader"/"Tom Teamlead". Cosmetic only; no action required unless the design values are contractual.

</details>

<details>
<summary>Details</summary>

### Layered backend slice mirrors Reference Standards

The model, entity, repository interface, repository impl, service methods, schemas, and endpoints are all present and follow `ReferenceStandard` in shape. `ProjectMasterModel` defines `project_id` as `String(100), unique, indexed, non-null` (the `code` analogue), `product_name` non-null, the remaining optionals nullable, `status` defaulting to `"Active"`, and `start_date`/`end_date` as `DateTime` — matching the design's 17-field table (Sr No derived from `id`). Critically it is listed in the `resource_models` import block of `models/__init__.py`, which is what registers it with `Base.metadata`; omitting that is the one silent failure the design called out, and it is not omitted here (confirmed).

`ProjectRepositoryImpl.create` maps every one of the 16 entity fields plus `created_by`/`modified_by` into the model, and `_to_entity` maps all columns plus the four audit fields back — no field is dropped in either direction (confirmed by reading the impl).

### Service wiring and constructor arity

`ResourceService.__init__` gains `project_repo: IProjectRepository` positioned after `volumetric_repo` and before `audit_repo`, and `Container.get_resource_service` constructs `ProjectRepositoryImpl(session)` in the matching position before `AuditLogRepositoryImpl(session)` (confirmed). The arity lines up, so the container builds. `create_project` applies `status or "Active"` and writes an `AuditLog` with `table_name="project_master"`, `action="CREATE"`, `record_id=created.id` in the same session — identical to the sibling creates, preserving the GxP audit contract.

### API surface and authorization

Two routes are added to the existing `resource_router` (no prefix), resolving to `/api/v1/projects`, so `router.py` is correctly left untouched. `list_projects` requires a valid session via `get_current_user`; `create_project` requires `require_role("Admin")`. `CreateProjectRequest` makes `project_id`/`product_name` required and the rest optional; `ProjectResponse` carries `from_attributes=True`. Duplicate `project_id` raises `IntegrityError` at flush and propagates to the shared exception middleware, matching the siblings' deliberate no-pre-check behavior — the review confirms this is intentional parity, not a gap.

One divergence worth noting: `ProjectResponse` returns all 16 fields, whereas `ReferenceStandardResponse` and the others expose a trimmed subset. This is a superset relative to the frontend `ProjectMaster` type (which declares the same 16), so it is consistent and harmless (confirmed).

### Frontend wiring and the Add dialog

The `ProjectMaster` TS interface matches `ProjectResponse` (dates as strings, `status: string`, the rest optional-nullable). `projectApi.list/create` hit `/projects`, and `useProjects`/`useCreateProject` follow the TanStack Query pattern with `['projects']` invalidation on success. `ProjectMasterPage` is exported from the barrel, routed at `/projects` inside `MainLayout`, and present in `NAV_ITEMS` under Resource Manager.

The Add dialog is Admin-gated (`hasRole('Admin')`) and contains all 16 editable fields: `InputText` for the eleven text fields, `Calendar` for Start/End Date converting via `e.value ? (e.value as Date).toISOString() : undefined` (the TRFListPage form the design specified), `InputTextarea` for Comments and Remarks, and a `Dropdown` of `['Active','Inactive']` for Status defaulting to `Active`. `handleCreate` guards `project_id`/`product_name` with `toastService.warn` before submitting. The list renders a readable subset (Sr No derived from `rowIndex+1`, Project ID, Product Name, Product/Project Code, Group Lead, Location, Market, Start/End Date, License, Status via `StatusBadge`), with the omitted fields still captured and persisted by the dialog — matching StandardsPage's selective-column approach.

### RBAC nav grant (the critical check)

`usePermissions.ts` includes `projects: ['Admin', 'Analyst', 'Supervisor', 'QA']` in `MENU_ACCESS`. `useMenuPermissions()` derives `menuKeys` from `Object.keys(MENU_ACCESS)` filtered by the user's effective roles, and `MainLayout` keeps `NAV_ITEMS` whose `menuKey` is in `menuKeys`. The `NAV_ITEMS` entry uses `menuKey: 'projects'`, which matches the grant key exactly — so an Admin (and the other three base roles) sees **Resource Manager → Project Master** (confirmed by reading both files). Create stays Admin-only on both the page gate and the endpoint. This is the most common failure mode for this kind of change and it is correctly handled.

### Non-destructive table creation and seed

`seed_project_master.py` runs `Base.metadata.create_all` (creates only the missing `project_master` table, never drops) then inserts the 3 design rows behind an idempotent `project_id` select guard. The verification records a backup of `lims.db` taken first and the one-shot reporting `3 new row(s) inserted`, with the existing 17 users untouched — so the populated dev DB was not endangered. The destructive `seed_data.py` gained a parallel seed block (confirmed via grep: import + three `ProjectMasterModel(...)` adds) for full-reset parity but was correctly not executed.

The seed sample data drifts cosmetically from the design's illustrative values (group leads "Meera Nair"/"Arjun Rao" vs "Grace Leader"/"Tom Teamlead"; some product codes differ). These are example rows with no behavioral or schema impact; flagged as informational, not blocking.

### Test coverage

A new `tests/resource/` package establishes the first resource-manager tests. `test_project_master.py` builds `ResourceService` from the real repo impls against the in-memory `db_session` and covers: all fields persisted + `id` returned, a single `project_master` audit row with `action="CREATE"` and matching `record_id`, `list_projects` returning created rows, duplicate `project_id` raising `IntegrityError`, and `status` defaulting to `"Active"` when `None`. `test_project_api.py` drives the ASGI app with `get_session`/`get_current_user` overridden: empty-then-populated list with 200s, Admin `POST` → 200 / Analyst `POST` → 403, and missing `product_name` → 422.

Evidence (per `verification.md`, not re-run): `python -m pytest tests/resource -q` → `8 passed`; the dev-DB list endpoint returned the 3 seeded rows through the real DI service; `npm run build` exited 0 with zero TypeScript errors. The 5 failing tests in the full suite are pre-existing in `tests/calculation/` and confirmed unrelated by a `git stash` re-run on the base. Not tested: live browser login / UI render (documented as not performed, no dev server per instructions) — acceptable given the passing build and structural verification.

</details>

<details>
<summary>File map</summary>

Backend (modified):
- `src/infrastructure/database/models/resource_models.py` — `ProjectMasterModel`.
- `src/infrastructure/database/models/__init__.py` — register model with `Base.metadata`.
- `src/domain/entities/resource_items.py` — `ProjectMaster` dataclass.
- `src/domain/repositories/resource_repositories.py` — `IProjectRepository`.
- `src/infrastructure/database/repositories/resource_repositories_impl.py` — `ProjectRepositoryImpl`.
- `src/application/services/resource_service.py` — ctor param + `list_projects`/`create_project`.
- `src/config/dependency_injection.py` — wire `ProjectRepositoryImpl`.
- `src/api/v1/schemas/resource_schemas.py` — `CreateProjectRequest`/`ProjectResponse`.
- `src/api/v1/endpoints/resource_endpoints.py` — `GET`/`POST /projects`.
- `scripts/seed_data.py` — full-reset seed block (not executed).

Backend (new):
- `scripts/seed_project_master.py` — non-destructive create+seed one-shot.
- `tests/resource/__init__.py`, `tests/resource/test_project_master.py`, `tests/resource/test_project_api.py`.

Frontend (modified):
- `src/features/resource-management/models/resource.types.ts` — `ProjectMaster` type.
- `src/features/resource-management/api/resourceApi.ts` — `projectApi`.
- `src/features/resource-management/hooks/useResources.ts` — `useProjects`/`useCreateProject`.
- `src/features/resource-management/index.ts` — barrel export.
- `src/app/router/AppRouter.tsx` — `/projects` route.
- `src/app/layouts/MainLayout.tsx` — `NAV_ITEMS` entry.
- `src/core/rbac/usePermissions.ts` — `projects` in `MENU_ACCESS`.

Frontend (new):
- `src/features/resource-management/pages/ProjectMasterPage.tsx`.

Full diff: `git diff <base>` in `d:\RD-instance\GIT`.

</details>
