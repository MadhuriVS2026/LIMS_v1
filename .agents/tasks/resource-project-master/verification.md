# Verification — Project Master (Resource Manager)

First iteration (no `review.json` present). Implemented per the approved
`design.md` and `plan.md`, mirroring the Instruments / Reference Standards
resource convention. All 17 fields present: Sr No (UI row index), Project ID,
Product Name, Product Code, Project Code, Project Code (Academic Research),
BD Code (SAP), Group Lead, Location, Market, Start Date, End Date, License,
Comments, Project Status (Active/Inactive), Requested person/Remark, Remarks.

## 1. Backend import / wiring + route registration

Command (run in `backend-v2`):

```
python -c "import src.infrastructure.database.models; from src.infrastructure.database.models.base_model import Base; assert 'project_master' in Base.metadata.tables; from src.config.dependency_injection import Container; from src.main import app; routes=[r.path for r in app.routes]; assert '/api/v1/projects' in routes, routes; print('all ok')"
```

Result: `all ok` (exit 0). Confirms the model is registered with `Base.metadata`,
the DI container constructs with the new `ProjectRepositoryImpl` in the new
constructor position, and `GET/POST /api/v1/projects` are registered on the app.

Seed script parse check: `python -c "import ast; ast.parse(open('scripts/seed_data.py').read()); print('parses')"` -> `parses`.

## 2. Table create + non-destructive seed in dev lims.db

- Backed up the dev DB first: `Copy-Item lims.db lims.db.bak-projectmaster-20261024211934`.
- Ran `python -m scripts.seed_project_master` (one-shot: `Base.metadata.create_all`
  — same call `init_models()` uses, creates only the missing `project_master`
  table, never drops — then idempotent insert of the 3 design rows).
- Output: `project_master seed complete: 3 new row(s) inserted, 0 already present.`

Data integrity spot-check:

```
python -c "import sqlite3; c=sqlite3.connect('lims.db'); print('projects:', c.execute('select count(*) from project_master').fetchone()[0]); print('users:', c.execute('select count(*) from users').fetchone()[0]); print([r[0] for r in c.execute('select project_id from project_master').fetchall()])"
```

Result:
```
projects: 3
users: 17
['PID-2026-001', 'PID-2026-002', 'PID-2026-003']
```

Existing data intact (17 users unchanged); 3 project rows present. The lead seed
row matches the design exactly: PID-2026-001 / Doxorubicin Liposome / PRD-DOXO-01 /
PRJ-ONCO-01 / AR-ONCO-01 / BD-100231 / Suresh Iyer / Ahmedabad / US /
2026-01-15..2026-12-31 / ANDA / Active, plus PID-2026-002 (EU/MAA/Active) and
PID-2026-003 (IN/NDA/Inactive).

## 3. List endpoint returns the seeded projects (dev DB)

One-shot through the real DI service against `lims.db`:

```
python -c "import asyncio; from src.infrastructure.database.session import async_session_factory; from src.config.dependency_injection import Container; ..."
```

Result:
```
count 3
PID-2026-001 | Doxorubicin Liposome | Active
PID-2026-002 | Propofol 1% Emulsion | Active
PID-2026-003 | Bupivacaine Lipid Injection | Inactive
```

`ResourceService.list_projects()` (what `GET /api/v1/projects` calls) returns all
3 seeded rows.

## 4. Backend test suite

Repo has pytest (`asyncio_mode=auto`, `testpaths=["tests"]`). Added a new test
package `tests/resource/` with unit + API tests.

Command: `python -m pytest tests/resource -q`

Result: `8 passed in 3.95s`.

Full suite: `python -m pytest -q` reports `5 failed, 838 passed`. The 5 failures
are **pre-existing and unrelated** to this change — all in `tests/calculation/`
(`test_seeded_template_parity.py::TestA6BDissolutionWithReplacement` x3 and two
`test_worksheet_service.py` cases about worksheet edit-locking/analyst
assignment). Confirmed by `git stash`-ing the Project Master changes and
re-running only those 5: they still fail on the base (`5 failed, 1 passed`), so
they are not caused by this work. None touch any file edited here.

- `test_project_master.py` (unit, real repos against in-memory `db_session`):
  persists all fields; writes a `project_master` CREATE audit row; `list_projects`
  returns created rows; duplicate `project_id` raises `IntegrityError`; `status`
  defaults to `"Active"` when `None`.
- `test_project_api.py` (ASGI integration via `httpx.AsyncClient` +
  `ASGITransport`, overriding `get_session`/`get_current_user`): `GET /projects`
  empty then populated + 200; `POST /projects` as Admin -> 200, as Analyst -> 403;
  `POST` missing required `product_name` -> 422.

## 5. Frontend build (one-shot)

Command (run in `frontend-react`): `npm run build` (= `tsc -b && vite build`).

Result: exit 0, `336 modules transformed`, `built in 4.19s`, **zero TypeScript
errors**. (The chunk-size warning is pre-existing and unrelated.)

## 6. Nav renders for Admin + page lists seeded rows with 17 columns + Add dialog (reasoning)

- RBAC: `projects` was added to `MENU_ACCESS` in `usePermissions.ts` granting
  `['Admin','Analyst','Supervisor','QA']`. `useMenuPermissions()` iterates
  `Object.keys(MENU_ACCESS)`, so `projects` is now yielded for an Admin —
  this is the usual failure mode and is covered.
- Nav: `MainLayout.tsx` has a `NAV_ITEMS` entry
  `{ label: 'Project Master', path: '/projects', section: 'Resource Manager', menuKey: 'projects' }`.
  `visibleItems` keeps items whose `menuKey` is in `menuKeys`; with the grant
  above, an Admin sees **Resource Manager -> Project Master**.
- Route: `AppRouter.tsx` maps `/projects` to `<ProjectMasterPage />` inside
  `MainLayout`, so clicking the nav item renders the page.
- Page: `ProjectMasterPage.tsx` uses `useProjects()` (calls `GET /projects`) and
  renders a `DataTable` with Sr No + Project ID + Product Name + Product Code +
  Project Code + Group Lead + Location + Market + Start/End Date + License +
  Status columns; with the 3 seeded rows the list shows them. The Admin-gated
  `Add Project` button (`hasRole('Admin')`) opens a 640px dialog with all 16
  editable fields — Project Status as an Active/Inactive `Dropdown`, Start/End
  Date as `Calendar` date inputs, Comments/Remarks as `InputTextarea`. Create is
  Admin-only on both the page (gate) and the endpoint (`require_role("Admin")`).

Manual UI login was not performed (no dev server started per instructions); the
above is verified structurally via the passing build and the endpoint/data checks.

## Shared-file edits (precise)

Backend:
- `src/infrastructure/database/models/resource_models.py` — added `ProjectMasterModel`.
- `src/infrastructure/database/models/__init__.py` — added `ProjectMasterModel` to the resource-models import.
- `src/domain/entities/resource_items.py` — added `ProjectMaster` dataclass.
- `src/domain/repositories/resource_repositories.py` — added `IProjectRepository` + entity import.
- `src/infrastructure/database/repositories/resource_repositories_impl.py` — added `ProjectRepositoryImpl` + imports.
- `src/application/services/resource_service.py` — added ctor param `project_repo`, `list_projects`/`create_project`, imports.
- `src/config/dependency_injection.py` — wired `ProjectRepositoryImpl` into `get_resource_service` + import.
- `src/api/v1/schemas/resource_schemas.py` — added `CreateProjectRequest`/`ProjectResponse`.
- `src/api/v1/endpoints/resource_endpoints.py` — added `GET /projects` + `POST /projects` + schema imports.
- `scripts/seed_data.py` — added `ProjectMasterModel` import + 3-row seed block (full-reset path only; NOT run here).
- `src/api/v1/router.py` — NOT edited (resource_router already registered, no sub-prefix).

Backend new files:
- `scripts/seed_project_master.py` (non-destructive create+seed one-shot).
- `tests/resource/__init__.py`, `tests/resource/test_project_master.py`, `tests/resource/test_project_api.py`.
- DB backup: `backend-v2/lims.db.bak-projectmaster-20261024211934`.

Frontend:
- `src/features/resource-management/models/resource.types.ts` — added `ProjectMaster` type.
- `src/features/resource-management/api/resourceApi.ts` — added `projectApi` + import.
- `src/features/resource-management/hooks/useResources.ts` — added `useProjects`/`useCreateProject` + import.
- `src/features/resource-management/index.ts` — added `ProjectMasterPage` barrel export.
- `src/app/router/AppRouter.tsx` — added import + `/projects` route.
- `src/app/layouts/MainLayout.tsx` — added `NAV_ITEMS` 'Project Master' entry.
- `src/core/rbac/usePermissions.ts` — added `projects` to `MENU_ACCESS`.

Frontend new files:
- `src/features/resource-management/pages/ProjectMasterPage.tsx`.

## Scope

No existing resources, calculation templates, or unrelated features were
modified. `scripts/seed_data.py` gained a seed block for full-reset consistency
but was not executed (it is destructive); the dev DB was seeded via the
non-destructive one-shot. Per instructions, no commit was made in this step and
no branch was pushed.
