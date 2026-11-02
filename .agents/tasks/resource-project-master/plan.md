# Implementation Plan — Project Master (Resource Manager)

Derived from the APPROVED design at `.agents/tasks/resource-project-master/design.md`. All file-level claims in the design were verified against the codebase before writing this plan (see "Verified facts" below). Order is strictly by dependency: each item leaves the repo buildable. Backend first (items 1–11), then frontend (items 12–19), then verification (item 20).

## Verified facts (confirmed by reading the code)

- Backend resources are woven into shared files (`resource_models.py`, `resource_items.py`, `resource_repositories.py`, `resource_repositories_impl.py`, `resource_service.py`, `resource_schemas.py`, `resource_endpoints.py`), exactly as the design states. `ReferenceStandard` is the closest analogue to copy.
- `src/api/v1/router.py` registers `resource_router` with **no** sub-prefix; `api_v1_router` has prefix `/api/v1`. New routes added to `resource_router` resolve to `/api/v1/projects`. **No change to `router.py` is required.**
- Model registration point is `src/infrastructure/database/models/__init__.py` (imports from `resource_models`). A model omitted here is never created by `create_all`.
- `src/infrastructure/database/session.py::init_models()` runs `Base.metadata.create_all` at app startup — this **creates missing tables without dropping** existing ones. `scripts/seed_data.py` does `drop_all` + `create_all` + reseed (destructive full reset).
- Dev DB is `backend-v2/lims.db` (`DATABASE_URL=sqlite+aiosqlite:///./lims.db`). **It already contains extensive real data and dozens of `.bak-*` backups — the destructive full seed must NOT be run against it. See item 11 for the non-destructive path.**
- `src/api/v1/dependencies.py` provides `get_current_user`, `require_role(*roles)`, and `get_session`. Reference-standards uses `get_current_user` for list and `require_role("Admin")` for create.
- Tests: `backend-v2/pyproject.toml` sets `testpaths=["tests"]`, `asyncio_mode="auto"`. Root `tests/conftest.py` provides the `db_session` fixture (runs `Base.metadata.create_all`, in-memory SQLite, StaticPool) plus `make_admin_user()`/`make_user()` factories and `admin_user` fixture. Only existing test packages are `tests/calculation/*` and `tests/mrn/`. The integration template to copy is `tests/calculation/test_coa_api.py` (ASGITransport + `app.dependency_overrides` for `get_session`/`get_current_user`). `tests/resource/` does not exist yet.
- Frontend: resource slices live in `resource.types.ts`, `resourceApi.ts`, `useResources.ts`, `index.ts`. `StandardsPage.tsx` is the page template (DataTable + `hasRole('Admin')` gate + `StatusBadge` + `toastService`). `Calendar`, `InputTextarea`, `Dropdown`, `InputText`, `StatusBadge`, `toastService` are all already used in the codebase.
- Nav visibility is driven by `useMenuPermissions()` in `src/core/rbac/usePermissions.ts`, which iterates `Object.keys(MENU_ACCESS)`. A `menuKey` absent from `MENU_ACCESS` is **never** granted, so `MainLayout` would hide the item even for Admin. The `projects` key MUST be added to `MENU_ACCESS` (item 18).
- `/projects` is unused in `AppRouter.tsx`; `/products` belongs to Sample Manager and is distinct.
- Frontend build command is `npm run build` = `tsc -b && vite build`. No AGENTS.md / `.kiro/steering` exists in the repo.

---

# Implementation Plan

- [ ] 1. Add the `ProjectMasterModel` SQLAlchemy model mirroring `ReferenceStandardModel`: table `project_master`, columns per the design's 17-field table (`project_id` String(100) unique+indexed non-null; `product_name` String(500) non-null; `product_code`/`project_code`/`project_code_academic`/`bd_code_sap` String(100) nullable; `group_lead`/`location` String(255) nullable; `market` String(100) nullable; `start_date`/`end_date` DateTime nullable; `license` String(255) nullable; `comments`/`remarks` String(2000) nullable; `status` String(50) default `"Active"`; `requested_person` String(500) nullable). `BaseModel` supplies `id` + audit columns. `DateTime` and `String` are already imported in the file.
      Files: `backend-v2/src/infrastructure/database/models/resource_models.py`
      Verify: `cd backend-v2; python -c "from src.infrastructure.database.models.resource_models import ProjectMasterModel; print(ProjectMasterModel.__tablename__)"` prints `project_master`.

- [ ] 2. Register the new model so `create_all` builds the table: add `ProjectMasterModel` to the existing `from src.infrastructure.database.models.resource_models import (...)` block (alongside `ChemicalReagentModel`, `ColumnMasterModel`, `ReferenceStandardModel`, `VolumetricSolutionModel`).
      Files: `backend-v2/src/infrastructure/database/models/__init__.py`
      Verify: `cd backend-v2; python -c "import src.infrastructure.database.models; from src.infrastructure.database.models.base_model import Base; assert 'project_master' in Base.metadata.tables; print('registered')"` prints `registered`.

- [ ] 3. Add the `ProjectMaster` domain dataclass to the entities module, mirroring `ReferenceStandard`: fields matching the model (string defaults `""` for required `project_id`/`product_name`, `None` for optionals, `status` default `"Active"`). `datetime` and `BaseEntity` are already imported.
      Files: `backend-v2/src/domain/entities/resource_items.py`
      Verify: `cd backend-v2; python -c "from src.domain.entities.resource_items import ProjectMaster; p=ProjectMaster(project_id='x', product_name='y'); print(p.status)"` prints `Active`.

- [ ] 4. Add the `IProjectRepository` abstract interface (methods `list_all() -> list[ProjectMaster]` and `create(project: ProjectMaster) -> ProjectMaster`), mirroring `IReferenceStandardRepository`. Add `ProjectMaster` to the `from src.domain.entities.resource_items import (...)` import.
      Files: `backend-v2/src/domain/repositories/resource_repositories.py`
      Verify: `cd backend-v2; python -c "from src.domain.repositories.resource_repositories import IProjectRepository; print(IProjectRepository.__name__)"` prints `IProjectRepository`.

- [ ] 5. Add `ProjectRepositoryImpl(IProjectRepository)` mirroring `ReferenceStandardRepositoryImpl`: `__init__(session)`, `list_all` (`select(ProjectMasterModel)` → `_to_entity`), `create` (build `ProjectMasterModel` from every entity field including `created_by`/`modified_by`, `session.add`, `await flush`, return `_to_entity`), and a static `_to_entity` mapping all columns + audit fields back to `ProjectMaster`. Add `ProjectMaster` to the entities import, `IProjectRepository` to the repositories import, and `ProjectMasterModel` to the models import block.
      Files: `backend-v2/src/infrastructure/database/repositories/resource_repositories_impl.py`
      Verify: `cd backend-v2; python -c "from src.infrastructure.database.repositories.resource_repositories_impl import ProjectRepositoryImpl; print('ok')"` prints `ok`.

- [ ] 6. Extend `ResourceService` with the Project Master slice: add a `project_repo: IProjectRepository` constructor parameter stored as `self._project_repo` (positioned after `volumetric_repo`, before `audit_repo` so audit stays last), and add `list_projects()` and `create_project(...)` methods mirroring `list_reference_standards`/`create_reference_standard`. `create_project` builds a `ProjectMaster` from all 16 request fields (`status or "Active"`, `created_by`/`modified_by = actor.username`), calls `self._project_repo.create`, writes an `AuditLog` (`action="CREATE"`, `table_name="project_master"`, `record_id=created.id`), and returns the created entity. Add `ProjectMaster` to the `resource_items` import and `IProjectRepository` to the `resource_repositories` import.
      Files: `backend-v2/src/application/services/resource_service.py`
      Verify: `cd backend-v2; python -c "from src.application.services.resource_service import ResourceService; assert hasattr(ResourceService,'create_project') and hasattr(ResourceService,'list_projects'); print('ok')"` prints `ok`. (Full constructor wiring is exercised in item 20.)

- [ ] 7. Wire the repository into DI: in `Container.get_resource_service`, construct `ProjectRepositoryImpl(session)` and pass it to `ResourceService(...)` in the new parameter position (after `VolumetricSolutionRepositoryImpl(session)`, before `AuditLogRepositoryImpl(session)`). Add `ProjectRepositoryImpl` to the existing `resource_repositories_impl` import block.
      Files: `backend-v2/src/config/dependency_injection.py`
      Verify: `cd backend-v2; python -c "from src.config.dependency_injection import Container; print('ok')"` prints `ok` (import succeeds with the new constructor arity).

- [ ] 8. Add the Pydantic v2 schemas `CreateProjectRequest` (all 16 editable fields; `project_id` and `product_name` required strings, the rest optional with `None` defaults; `start_date`/`end_date` as `datetime | None`; `status: str | None = None`) and `ProjectResponse` (adds `id: int`, `status: str`, `model_config = ConfigDict(from_attributes=True)`), mirroring the reference-standard schemas. `datetime`, `BaseModel`, `ConfigDict` are already imported.
      Files: `backend-v2/src/api/v1/schemas/resource_schemas.py`
      Verify: `cd backend-v2; python -c "from src.api.v1.schemas.resource_schemas import CreateProjectRequest, ProjectResponse; print(CreateProjectRequest(project_id='p', product_name='n').status)"` prints `None`.

- [ ] 9. Add the two endpoints to the existing `resource_router`, mirroring the reference-standards pair: `GET /projects` (`response_model=list[ProjectResponse]`, `Depends(get_current_user)`) returning `Container.get_resource_service(session).list_projects()`; and `POST /projects` (`response_model=ProjectResponse`, `Depends(require_role("Admin"))`) calling `service.create_project(...)` with every `request.*` field plus `current_user`. Add `CreateProjectRequest` and `ProjectResponse` to the `resource_schemas` import block. **No change to `router.py`.**
      Files: `backend-v2/src/api/v1/endpoints/resource_endpoints.py`
      Verify: `cd backend-v2; python -c "from src.main import app; routes=[r.path for r in app.routes]; assert '/api/v1/projects' in routes, routes; print('route ok')"` prints `route ok`.

- [ ] 10. Add a Project Master seed block to the full-reset seed script, placed with the other resource seeds (before the final audit-log commit): add `ProjectMasterModel` to the `resource_models` import, define the 3 seed rows from the design (PID-2026-001 Doxorubicin Liposome / PRD-DOXO-01 / PRJ-ONCO-01 / AR-ONCO-01 / BD-100231 / Suresh Iyer / Ahmedabad / US / 2026-01-15..2026-12-31 / ANDA / Active; PID-2026-002 Propofol 1% Emulsion / EU / MAA / Active; PID-2026-003 Bupivacaine Lipid Injection / IN / NDA / Inactive), and `session.add(ProjectMasterModel(...))` each with `requested_person`/`remarks`/`created_by="System"`, then rely on the existing `await session.commit()`. `datetime`/`timezone` are already imported. This path runs only on a full DB reset.
      Files: `backend-v2/scripts/seed_data.py`
      Verify: `cd backend-v2; python -c "import ast; ast.parse(open('scripts/seed_data.py').read()); print('parses')"` prints `parses`. (Not executed here — see item 11; do NOT run `python -m scripts.seed_data` against the dev DB.)

- [ ] 11. Create the `project_master` table in the real dev `lims.db` and seed it **non-destructively**, because `lims.db` holds extensive real data. First back it up (`Copy-Item backend-v2/lims.db backend-v2/lims.db.bak-projectmaster-<timestamp>`, matching the repo's `.bak-*` convention). Then add a small one-shot script `backend-v2/scripts/seed_project_master.py` that opens the app's engine/session (import `engine`, `async_session_factory` from `src.infrastructure.database.session` and `src.infrastructure.database.models` to register models), runs `Base.metadata.create_all` (creates only the missing `project_master` table — non-destructive, same call `init_models` uses), then inserts the 3 design seed rows **only if** `project_master` has no row with that `project_id` (idempotent `select` guard), and commits. Run it: `cd backend-v2; python -m scripts.seed_project_master`.
      Files: `backend-v2/scripts/seed_project_master.py` (new); backup copy of `backend-v2/lims.db`
      Verify: `cd backend-v2; python -m scripts.seed_project_master` prints a success line; then `python -c "import sqlite3; c=sqlite3.connect('lims.db'); print(c.execute('select count(*) from project_master').fetchone()[0])"` prints `3`. Existing tables/rows remain intact (spot-check: the same sqlite3 connection's `select count(*) from users` is unchanged / non-zero).

- [ ] 12. Add the `ProjectMaster` TypeScript interface to the resource types, fields matching `ProjectResponse`: `id: number`, `project_id: string`, `product_name: string`, `status: string`, and the remaining 13 optional `?: string | null` fields (dates as string). Mirrors the `ReferenceStandard` interface shape.
      Files: `frontend-react/src/features/resource-management/models/resource.types.ts`
      Verify: part of the item 20 `npm run build` (tsc) check; no standalone command.

- [ ] 13. Add `projectApi` to the resource API client with `list(): Promise<ProjectMaster[]>` (`apiClient.get('/projects')`) and `create(payload: Partial<ProjectMaster>): Promise<ProjectMaster>` (`apiClient.post('/projects', payload)`), mirroring `referenceStandardApi`. Add `ProjectMaster` to the `../models/resource.types` type import.
      Files: `frontend-react/src/features/resource-management/api/resourceApi.ts`
      Verify: part of item 20 `npm run build`.

- [ ] 14. Add the `useProjects()` query hook (`queryKey: ['projects']`, `queryFn: projectApi.list`) and `useCreateProject()` mutation hook (`mutationFn: projectApi.create`, `onSuccess` invalidates `['projects']`), mirroring the reference-standard hooks. Add `projectApi` to the `../api/resourceApi` import.
      Files: `frontend-react/src/features/resource-management/hooks/useResources.ts`
      Verify: part of item 20 `npm run build`.

- [ ] 15. Create `ProjectMasterPage.tsx` modeled on `StandardsPage.tsx`: `useProjects()` + `useCreateProject()` + `usePermissions()`; header showing `{projects.length} projects` with an `Add Project` button gated by `hasRole('Admin')`; a `DataTable` (`paginator rows={10} size="small"`) with a readable column subset — Sr No (`body={(_r,{rowIndex})=>rowIndex+1}`), Project ID, Product Name, Product Code, Project Code, Group Lead, Location, Market, Start/End Date (`new Date(...).toLocaleDateString()` with `-` fallback), License, Status (`<StatusBadge status={row.status} />`); and a 640px `Dialog` "Add Project" with **all 16 editable fields** laid out in PrimeFlex grid rows — `InputText` for Project ID, Product Name, Product Code, Project Code, Project Code (Academic Research), BD Code (SAP), Group Lead, Location, Market (free-text, not a dropdown), License, Requested person/Remark; `Calendar` for Start Date and End Date converting with `e.value ? (e.value as Date).toISOString() : undefined` (the TRFListPage form — do not change it); `InputTextarea` for Comments and Remarks; `Dropdown` with `options={['Active','Inactive']}` for Project Status defaulting to `Active`; and a submit `Button` (`loading={createProject.isPending}`). `handleCreate` requires `project_id` and `product_name` via `toastService.warn`, and on success calls `toastService.success`, closes the dialog, and resets the form.
      Files: `frontend-react/src/features/resource-management/pages/ProjectMasterPage.tsx` (new)
      Verify: part of item 20 `npm run build`.

- [ ] 16. Export the new page from the feature barrel: add `export { ProjectMasterPage } from './pages/ProjectMasterPage';`.
      Files: `frontend-react/src/features/resource-management/index.ts`
      Verify: part of item 20 `npm run build`.

- [ ] 17. Register the route: add `ProjectMasterPage` to the `@features/resource-management` import and add `<Route path="/projects" element={<ProjectMasterPage />} />` inside `MainLayout`, alongside the other Resource Manager routes.
      Files: `frontend-react/src/app/router/AppRouter.tsx`
      Verify: part of item 20 `npm run build`.

- [ ] 18. Add the nav entry: a `NAV_ITEMS` object `{ label: 'Project Master', icon: 'pi pi-briefcase', path: '/projects', section: 'Resource Manager', menuKey: 'projects' }`, placed among the other Resource Manager items.
      Files: `frontend-react/src/app/layouts/MainLayout.tsx`
      Verify: part of item 20 `npm run build`.

- [ ] 19. **CRITICAL (nav invisible otherwise):** add a `projects` key to the `MENU_ACCESS` map in `usePermissions.ts` granting `['Admin', 'Analyst', 'Supervisor', 'QA']`, mirroring the `instruments`/`standards` grants. Without this, `useMenuPermissions()` never yields `projects` and `MainLayout` hides the item even for an Admin. (Create stays Admin-only via `hasRole('Admin')` on the page and `require_role("Admin")` on the endpoint.)
      Files: `frontend-react/src/core/rbac/usePermissions.ts`
      Verify: part of item 20 `npm run build` + the login check in item 20.

- [ ] 20. Add and run tests, then run the full build. Create the new test package `backend-v2/tests/resource/` (`__init__.py` + `test_project_master.py`) using the root `tests/conftest.py` `db_session` fixture and `make_admin_user()`. Cover the design's cases: (a) `ResourceService.create_project` persists all fields and returns an `id`; (b) a `project_master` `AuditLog` row is written; (c) `list_projects` returns created rows; (d) duplicate `project_id` raises `IntegrityError` on flush; (e) `status` defaults to `"Active"` when `None`. Add an API test `tests/resource/test_project_api.py` copying the `tests/calculation/test_coa_api.py` harness (`httpx.AsyncClient` + `ASGITransport(app=app)`, `base_url="http://test/api/v1"`, `app.dependency_overrides` for `get_session`→`db_session` and `get_current_user`→role user): `GET /projects` → 200 + list; `POST /projects` as Admin → 200 + body; `POST` as non-Admin → 403; `POST` missing a required field → 422. Build a `ResourceService` for unit tests either via the DI container against `db_session` or by constructing it with the real repo impls (pass `ProjectRepositoryImpl(db_session)` in the new position and `AuditLogRepositoryImpl(db_session)`).
      Files: `backend-v2/tests/resource/__init__.py` (new), `backend-v2/tests/resource/test_project_master.py` (new), `backend-v2/tests/resource/test_project_api.py` (new)
      Verify (run all):
      - Backend tests: `cd backend-v2; python -m pytest tests/resource -q` → all pass.
      - Backend list endpoint against dev DB (table + seed from item 11): `cd backend-v2; python -m pytest tests/resource/test_project_api.py -q` covers the endpoint; additionally the item 11 sqlite count confirms 3 seeded rows are returned by `list_projects`.
      - Frontend build: `cd frontend-react; npm run build` → exits 0 with zero TypeScript errors.
      - Manual (optional, documented): start the app, log in as `admin/admin123`, confirm **Project Master** appears under Resource Manager, lists the 3 seeded rows, and the Admin-gated Add Project dialog creates a row.

---

## Shared-file edits (precise list)

These existing files are edited (not created); every other new artifact is additive:

- `backend-v2/src/infrastructure/database/models/resource_models.py` — add `ProjectMasterModel` (item 1).
- `backend-v2/src/infrastructure/database/models/__init__.py` — add `ProjectMasterModel` to the resource-models import (item 2).
- `backend-v2/src/domain/entities/resource_items.py` — add `ProjectMaster` dataclass (item 3).
- `backend-v2/src/domain/repositories/resource_repositories.py` — add `IProjectRepository` + entity import (item 4).
- `backend-v2/src/infrastructure/database/repositories/resource_repositories_impl.py` — add `ProjectRepositoryImpl` + imports (item 5).
- `backend-v2/src/application/services/resource_service.py` — add ctor param + `list_projects`/`create_project` + imports (item 6).
- `backend-v2/src/config/dependency_injection.py` — wire `ProjectRepositoryImpl` into `get_resource_service` + import (item 7).
- `backend-v2/src/api/v1/schemas/resource_schemas.py` — add `CreateProjectRequest`/`ProjectResponse` (item 8).
- `backend-v2/src/api/v1/endpoints/resource_endpoints.py` — add 2 routes + schema imports (item 9).
- `backend-v2/scripts/seed_data.py` — add seed block + import (item 10).
- `frontend-react/src/features/resource-management/models/resource.types.ts` — add `ProjectMaster` type (item 12).
- `frontend-react/src/features/resource-management/api/resourceApi.ts` — add `projectApi` + import (item 13).
- `frontend-react/src/features/resource-management/hooks/useResources.ts` — add 2 hooks + import (item 14).
- `frontend-react/src/features/resource-management/index.ts` — add barrel export (item 16).
- `frontend-react/src/app/router/AppRouter.tsx` — add import + `/projects` route (item 17).
- `frontend-react/src/app/layouts/MainLayout.tsx` — add `NAV_ITEMS` entry (item 18).
- `frontend-react/src/core/rbac/usePermissions.ts` — add `projects` to `MENU_ACCESS` (item 19).

`backend-v2/src/api/v1/router.py` is intentionally NOT edited (resource_router already registered, no sub-prefix).

## Scope guard

Confine changes to the new Project Master resource and its wiring. Do NOT modify existing resources (Instruments, Columns, Reference Standards, Chemicals, Volumetric, Stability), calculation templates, or unrelated features. The only edits to shared files are the additive insertions listed above.

## Risk notes / assumptions

- **Destructive seed avoided.** `scripts/seed_data.py` does `drop_all` and would wipe the populated dev `lims.db`. The plan uses a non-destructive one-shot (`create_all` + idempotent insert, item 11) and takes a backup first. The seed block is still added to `seed_data.py` (item 10) for consistency on a full reset, but that script is NOT run here.
- **Test framework exists** (pytest, `asyncio_mode=auto`); a minimal unit + API test is added per item 20. The root `tests/conftest.py` auto-creates the new table for tests once the model is registered (item 2).
- `datetime` import in `resource_endpoints.py` is not required (dates flow through the Pydantic schema); only the two schema symbols are imported there.
