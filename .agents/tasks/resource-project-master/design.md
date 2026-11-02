# Design — Project Master (Resource Manager)

## Overview

Add a new DB-backed **Project Master** resource under the **Resource Manager** section, mirroring the existing Instruments / Reference Standards resources end to end. The feature stores an organization's project catalog (17 confirmed fields) in a new `project_master` SQLite table, exposes list + create REST endpoints under `/api/v1/projects`, and surfaces a `ProjectMasterPage` in the React SPA with a list view and an Admin-gated "Add Project" dialog. It reuses every established pattern — the layered backend (domain entity → repository interface → SQLAlchemy model → repository impl → application service method → Pydantic schemas → FastAPI endpoint → DI container → v1 router), the `Base.metadata.create_all` table-creation mechanism with a seed block in `scripts/seed_data.py`, and the frontend TanStack Query hook + axios API client + nav entry + route + RBAC menu-grant wiring. No new architectural concepts are introduced; the implementer adds a parallel "project" slice alongside the existing resource slices.

The technology stack is **locked** to what the codebase already uses: **Backend** — Python 3.13, FastAPI, SQLAlchemy 2.x async ORM (`Mapped`/`mapped_column`), aiosqlite/SQLite, Pydantic v2. **Frontend** — React + TypeScript, Vite, PrimeReact + PrimeFlex, TanStack Query (`@tanstack/react-query`), axios (`apiClient`), React Router. The Project Master is added to the **existing** `ResourceService` and the **existing** `resource_endpoints.py` / `resourceApi.ts` / `useResources.ts` / `resource.types.ts` files, matching how Columns, Standards, Chemicals, and Volumetric all share those files, rather than creating a new feature module.

## Field model (the 17 confirmed fields)

The task's "Sr No" is a display ordinal, not stored data — it mirrors the way existing list pages present rows. We back it with the table's autoincrement `id` (same as every other resource) and render the row index (or `id`) as "Sr No" in the UI. The remaining 16 fields are stored columns. `Project ID` is the unique business key (the analogue of `code` on other resources). Dates are stored as `DateTime` (matching `expiry_date`/`received_date` on the other resources) and exchanged as ISO strings. `Project Status` is a constrained string defaulting to `"Active"` (same convention as `status` elsewhere), surfaced in the UI as an Active/Inactive dropdown.

| # | Field (UI label) | Column / entity attr | Type | Null | Notes |
|---|---|---|---|---|---|
| 1 | Sr No | *(derived)* `id` | int | — | display ordinal; not a request field |
| 2 | Project ID | `project_id` | String(100), unique, indexed | NO | business key (the `code` analogue) |
| 3 | Product Name | `product_name` | String(500) | NO | required |
| 4 | Product Code | `product_code` | String(100) | YES | |
| 5 | Project Code | `project_code` | String(100) | YES | |
| 6 | Project Code (Academic Research) | `project_code_academic` | String(100) | YES | |
| 7 | BD Code (SAP) | `bd_code_sap` | String(100) | YES | |
| 8 | Group Lead | `group_lead` | String(255) | YES | |
| 9 | Location | `location` | String(255) | YES | |
| 10 | Market | `market` | String(100) | YES | **free text** (not an enum); US / EU / IN are illustrative only |
| 11 | Start Date | `start_date` | DateTime | YES | |
| 12 | End Date | `end_date` | DateTime | YES | |
| 13 | License | `license` | String(255) | YES | e.g. ANDA |
| 14 | Comments | `comments` | String(2000) | YES | |
| 15 | Project Status | `status` | String(50), default `"Active"` | NO | `"Active"` \| `"Inactive"` |
| 16 | Requested person / Remark | `requested_person` | String(500) | YES | |
| 17 | Remarks | `remarks` | String(2000) | YES | |

Plus the inherited audit columns from `BaseModel` / `BaseEntity` (`created_by`, `created_date`, `modified_by`, `modified_date`). `status` reuses the attribute name `status` so `StatusBadge` on the frontend renders it exactly as it does for other resources.

---

## Backend design (`d:\RD-instance\GIT\backend-v2`)

### Files to ADD
None as new files are strictly necessary — the Project Master is woven into the existing resource files, exactly as Columns/Standards/Chemicals/Volumetric are. The implementer edits the files below. (The one new artifact is the model class and entity class, which live inside the existing `resource_models.py` and `resource_items.py`.)

### Files to MODIFY

**1. `src/infrastructure/database/models/resource_models.py`** — add the ORM model:

```python
class ProjectMasterModel(BaseModel):
    __tablename__ = "project_master"

    project_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project_code_academic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bd_code_sap: Mapped[str | None] = mapped_column(String(100), nullable=True)
    group_lead: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comments: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active")
    requested_person: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remarks: Mapped[str | None] = mapped_column(String(2000), nullable=True)
```

**2. `src/infrastructure/database/models/__init__.py`** — add `ProjectMasterModel` to the existing `from ...resource_models import (...)` block so it registers with `Base.metadata`. This is the single wiring point that makes `create_all` produce the table; omitting it is the one failure that silently drops the table. (This mirrors how `ChemicalReagentModel` etc. are listed there.)

**3. `src/domain/entities/resource_items.py`** — add the domain entity:

```python
@dataclass
class ProjectMaster(BaseEntity):
    """Project catalog master (Resource Manager)."""
    project_id: str = field(default="")
    product_name: str = field(default="")
    product_code: str | None = field(default=None)
    project_code: str | None = field(default=None)
    project_code_academic: str | None = field(default=None)
    bd_code_sap: str | None = field(default=None)
    group_lead: str | None = field(default=None)
    location: str | None = field(default=None)
    market: str | None = field(default=None)
    start_date: datetime | None = field(default=None)
    end_date: datetime | None = field(default=None)
    license: str | None = field(default=None)
    comments: str | None = field(default=None)
    status: str = field(default="Active")
    requested_person: str | None = field(default=None)
    remarks: str | None = field(default=None)
```

**4. `src/domain/repositories/resource_repositories.py`** — add the interface:

```python
class IProjectRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[ProjectMaster]: ...

    @abstractmethod
    async def create(self, project: ProjectMaster) -> ProjectMaster: ...
```
(and add `ProjectMaster` to the `from src.domain.entities.resource_items import (...)` import.)

**5. `src/infrastructure/database/repositories/resource_repositories_impl.py`** — add `ProjectRepositoryImpl(IProjectRepository)` following `ReferenceStandardRepositoryImpl` verbatim in shape: a `list_all` (`select(ProjectMasterModel)` → `_to_entity`), a `create` (build `ProjectMasterModel` from the entity's fields, `session.add`, `await flush`, return `_to_entity`), and a static `_to_entity` mapping every column back to the dataclass including the audit fields. Add `ProjectMaster` and `ProjectMasterModel` and `IProjectRepository` to the existing imports.

**6. `src/application/services/resource_service.py`** — extend `ResourceService`:
- Constructor gains a `project_repo: IProjectRepository` parameter stored as `self._project_repo` (added after `volumetric_repo`, before `audit_repo` to keep audit last).
- Add methods mirroring `create_reference_standard`:

```python
# ─── Project Master ───
async def list_projects(self) -> list[ProjectMaster]:
    return await self._project_repo.list_all()

async def create_project(
    self, project_id: str, product_name: str, product_code: str | None,
    project_code: str | None, project_code_academic: str | None, bd_code_sap: str | None,
    group_lead: str | None, location: str | None, market: str | None,
    start_date: datetime | None, end_date: datetime | None, license: str | None,
    comments: str | None, status: str | None, requested_person: str | None,
    remarks: str | None, actor: User,
) -> ProjectMaster:
    project = ProjectMaster(
        project_id=project_id, product_name=product_name, product_code=product_code,
        project_code=project_code, project_code_academic=project_code_academic,
        bd_code_sap=bd_code_sap, group_lead=group_lead, location=location, market=market,
        start_date=start_date, end_date=end_date, license=license, comments=comments,
        status=status or "Active", requested_person=requested_person, remarks=remarks,
        created_by=actor.username, modified_by=actor.username,
    )
    created = await self._project_repo.create(project)
    await self._audit_repo.write(
        AuditLog(user_id=actor.id, username=actor.username, action="CREATE",
                 table_name="project_master", record_id=created.id)
    )
    return created
```
Add `ProjectMaster` to the `resource_items` import and `IProjectRepository` to the `resource_repositories` import.

**7. `src/config/dependency_injection.py`** — in `get_resource_service`, construct and pass `ProjectRepositoryImpl(session)` into `ResourceService(...)` (positioned to match the new constructor parameter order, before `AuditLogRepositoryImpl(session)`). Add `ProjectRepositoryImpl` to the existing `resource_repositories_impl` import block.

**8. `src/api/v1/schemas/resource_schemas.py`** — add the request/response schemas (Pydantic v2, `from_attributes=True` on the response, as the others do):

```python
class CreateProjectRequest(BaseModel):
    project_id: str
    product_name: str
    product_code: str | None = None
    project_code: str | None = None
    project_code_academic: str | None = None
    bd_code_sap: str | None = None
    group_lead: str | None = None
    location: str | None = None
    market: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    license: str | None = None
    comments: str | None = None
    status: str | None = None
    requested_person: str | None = None
    remarks: str | None = None


class ProjectResponse(BaseModel):
    id: int
    project_id: str
    product_name: str
    product_code: str | None = None
    project_code: str | None = None
    project_code_academic: str | None = None
    bd_code_sap: str | None = None
    group_lead: str | None = None
    location: str | None = None
    market: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    license: str | None = None
    comments: str | None = None
    status: str
    requested_person: str | None = None
    remarks: str | None = None

    model_config = ConfigDict(from_attributes=True)
```

**9. `src/api/v1/endpoints/resource_endpoints.py`** — add the endpoints (mirroring the reference-standards pair: `list` gated by `get_current_user`, `create` gated by `require_role("Admin")`):

```python
# ─── Project Master ───
@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await Container.get_resource_service(session).list_projects()


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_resource_service(session)
    return await service.create_project(
        request.project_id, request.product_name, request.product_code, request.project_code,
        request.project_code_academic, request.bd_code_sap, request.group_lead, request.location,
        request.market, request.start_date, request.end_date, request.license, request.comments,
        request.status, request.requested_person, request.remarks, current_user,
    )
```
Add `CreateProjectRequest` and `ProjectResponse` to the `resource_schemas` import block. No change to `router.py` is needed because these routes are added to the already-registered `resource_router` (the router has no prefix, so paths resolve to `/api/v1/projects`).

**10. `scripts/seed_data.py`** — add `ProjectMasterModel` to the `resource_models` import, and add a seed block (placed with the other resource seeds, before the final audit-log commit):

```python
print("Seeding project master...")
projects_data = [
    # project_id, product_name, product_code, project_code, academic, bd_sap, group_lead, location, market, start, end, license, status
    ("PID-2026-001", "Doxorubicin Liposome", "PRD-DOXO-01", "PRJ-ONCO-01", "AR-ONCO-01", "BD-100231",
     "Suresh Iyer", "Ahmedabad", "US", datetime(2026, 1, 15, tzinfo=timezone.utc),
     datetime(2026, 12, 31, tzinfo=timezone.utc), "ANDA", "Active"),
    ("PID-2026-002", "Propofol 1% Emulsion", "PRD-PROP-10", "PRJ-ANES-02", "AR-ANES-02", "BD-100244",
     "Grace Leader", "Hyderabad", "EU", datetime(2026, 2, 1, tzinfo=timezone.utc),
     datetime(2027, 1, 31, tzinfo=timezone.utc), "MAA", "Active"),
    ("PID-2026-003", "Bupivacaine Lipid Injection", "PRD-BUPI-05", "PRJ-PAIN-03", "AR-PAIN-03", "BD-100258",
     "Tom Teamlead", "Bengaluru", "IN", datetime(2026, 3, 10, tzinfo=timezone.utc),
     datetime(2026, 9, 30, tzinfo=timezone.utc), "NDA", "Inactive"),
]
for (pid, pname, pcode, prjcode, acad, bdsap, lead, loc, market, start, end, lic, status) in projects_data:
    session.add(ProjectMasterModel(
        project_id=pid, product_name=pname, product_code=pcode, project_code=prjcode,
        project_code_academic=acad, bd_code_sap=bdsap, group_lead=lead, location=loc, market=market,
        start_date=start, end_date=end, license=lic, status=status,
        requested_person="System", remarks="Seeded project.", created_by="System",
    ))
await session.commit()
```

### Backend table creation / migration mechanism (MIRRORED)

The project uses **no Alembic**. Tables are created by `Base.metadata.create_all` in two places: `src/infrastructure/database/session.py::init_models()` (runs at app startup for SQLite dev) and `scripts/seed_data.py` (drops + recreates + seeds). A model participates **only if it is imported** in `src/infrastructure/database/models/__init__.py`. Therefore the Project Master table is created exactly like every other resource: define `ProjectMasterModel`, register it in `models/__init__.py`, and it appears on next startup / seed run. **No migration file is written.** After implementation, the database must be re-seeded (`python -m scripts.seed_data` from `backend-v2/`) or otherwise recreated for the new table to exist in an existing dev DB — note this in the implementation handoff.

---

## Frontend design (`d:\RD-instance\GIT\frontend-react`)

### Files to ADD

**11. `src/features/resource-management/pages/ProjectMasterPage.tsx`** — new page. Modeled on `StandardsPage.tsx` (DataTable list) with the Instruments/Standards Admin gate. Behavior:
- `const { data: projects = [], isLoading } = useProjects();`
- `const createProject = useCreateProject();`
- `const { hasRole } = usePermissions();`
- Header row: `{projects.length} projects` + an `Add Project` button rendered only when `hasRole('Admin')` (same gate as `StandardsPage`).
- A PrimeReact `DataTable` (`paginator rows={10} size="small"`) with columns: Sr No (`body={(_row, { rowIndex }) => rowIndex + 1}`), Project ID, Product Name, Product Code, Project Code, Group Lead, Location, Market, Start Date / End Date (`new Date(row.start_date).toLocaleDateString()` with a `-` fallback), License, and Status rendered via `<StatusBadge status={row.status} />`. (Comments / Academic code / BD code / Requested person / Remarks are captured in the dialog and available on the row; they need not all appear as table columns — keep the table readable, matching StandardsPage's selective columns.)
- A `Dialog` "Add Project" (`style={{ width: '640px' }}` — wider than the 440px resource dialogs because of the field count) containing the 16 editable fields laid out in PrimeFlex `grid`/`col-*` rows:
  - `InputText` for Project ID, Product Name, Product Code, Project Code, Project Code (Academic Research), BD Code (SAP), Group Lead, Location, Market, License, Requested person/Remark. **Market is a free-text `InputText`** — not a dropdown/enum; any illustrative "US / EU / IN" values elsewhere in this doc are examples, not an enforced set.
  - PrimeReact `Calendar` (date mode) for Start Date and End Date; convert to ISO on change (`e.value ? (e.value as Date).toISOString() : undefined`). This ISO-conversion form is chosen deliberately to match `TRFListPage.tsx` (the codebase has two forms — `TRFListPage` uses `e.value ? (e.value as Date).toISOString() : undefined` and `ProtocolsPage` uses `(e.value as Date)?.toISOString()`); implementers should keep the TRFListPage form here and not "correct" it to the other. `Calendar` is the established date input in this codebase (used in other feature dialogs); the task's "date inputs" requirement is satisfied by `Calendar`.
  - `InputTextarea` for Comments and Remarks.
  - PrimeReact `Dropdown` for Project Status with `options={['Active', 'Inactive']}`, defaulting to `Active`.
  - A submit `Button` ("Add Project", `loading={createProject.isPending}`).
  - All 16 stored fields are inputs in the Add Project dialog and are submitted on create; the DataTable above shows only a readable subset (the omitted columns — Project Code (Academic Research), BD Code (SAP), Comments, Requested person/Remark, Remarks — are still captured by the dialog and persisted, they are simply not rendered as table columns, matching StandardsPage's selective columns).
- `handleCreate`: require `project_id` and `product_name` (mirrors the Code+Name guard on other pages) via `toastService.warn`; on success call `toastService.success`, close the dialog, and reset the form.

### Files to MODIFY

**12. `src/features/resource-management/models/resource.types.ts`** — add the `ProjectMaster` TS interface, fields matching `ProjectResponse` (string dates, `status: string`, optional nullable fields):

```typescript
export interface ProjectMaster {
  id: number;
  project_id: string;
  product_name: string;
  product_code?: string | null;
  project_code?: string | null;
  project_code_academic?: string | null;
  bd_code_sap?: string | null;
  group_lead?: string | null;
  location?: string | null;
  market?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  license?: string | null;
  comments?: string | null;
  status: string;
  requested_person?: string | null;
  remarks?: string | null;
}
```

**13. `src/features/resource-management/api/resourceApi.ts`** — add `projectApi` (base client is `apiClient` with `baseURL '/api/v1'`, so `'/projects'` hits `/api/v1/projects`):

```typescript
export const projectApi = {
  async list(): Promise<ProjectMaster[]> {
    return (await apiClient.get<ProjectMaster[]>('/projects')).data;
  },
  async create(payload: Partial<ProjectMaster>): Promise<ProjectMaster> {
    return (await apiClient.post<ProjectMaster>('/projects', payload)).data;
  },
};
```
Add `ProjectMaster` to the `../models/resource.types` type import.

**14. `src/features/resource-management/hooks/useResources.ts`** — add the hooks and import `projectApi`:

```typescript
export function useProjects() {
  return useQuery({ queryKey: ['projects'], queryFn: projectApi.list });
}
export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: projectApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });
}
```

**15. `src/features/resource-management/index.ts`** — add `export { ProjectMasterPage } from './pages/ProjectMasterPage';`.

**16. `src/app/router/AppRouter.tsx`** — add `ProjectMasterPage` to the `@features/resource-management` import and add the route inside `MainLayout`, alongside the other Resource Manager routes:
`<Route path="/projects" element={<ProjectMasterPage />} />`. Path chosen: `/projects` (short, consistent with `/instruments`, `/standards`, `/columns`). Note the Sample Manager already uses `/products` — `/projects` is distinct and unused (verified against the current route table).

**17. `src/app/layouts/MainLayout.tsx`** — add a `NAV_ITEMS` entry in the `Resource Manager` section:
`{ label: 'Project Master', icon: 'pi pi-briefcase', path: '/projects', section: 'Resource Manager', menuKey: 'projects' },`
placed among the other Resource Manager items.

**18. `src/core/rbac/usePermissions.ts`** — **CRITICAL** nav visibility step. The sidebar filters `NAV_ITEMS` by `menuKeys.includes(item.menuKey)`, and `useMenuPermissions()` derives `menuKeys` from the `MENU_ACCESS` map. An item whose `menuKey` is absent from `MENU_ACCESS` is **never granted** (the derivation iterates `Object.keys(MENU_ACCESS)`), so the nav item would not appear even for an Admin. Therefore add a `projects` key to `MENU_ACCESS`:
`projects: ['Admin', 'Analyst', 'Supervisor', 'QA'],`
This mirrors how `instruments` / `standards` are granted — entirely frontend-side; there is no backend menu-grant table. Granting all four base roles for the list view matches the other resources; create remains Admin-only via `hasRole('Admin')` on the page and `require_role("Admin")` on the endpoint.

---

## Error handling (per operation)

**`POST /api/v1/projects` — validation.** The Pydantic `CreateProjectRequest` enforces types and required fields (`project_id`, `product_name` non-null strings). A malformed body (missing required field, wrong type, unparseable date) yields FastAPI's automatic **422 Unprocessable Entity** with field-level detail — recoverable by the caller; not logged as an application error (it never reaches the service). Optional fields accept `null`/omitted. `status`, if omitted or null, defaults to `"Active"` in the service.

**`POST /api/v1/projects` — authorization.** `require_role("Admin")` raises **403 Forbidden** for non-Admins (recoverable: the user lacks rights; the frontend additionally hides the button). Missing/invalid JWT raises **401** via `get_current_user`. Neither is logged as an application error.

**`POST /api/v1/projects` — duplicate `project_id`.** `project_id` is `unique=True`. Inserting a duplicate causes the `flush()` to raise a SQLAlchemy `IntegrityError` at commit time. This matches the existing resources' behavior exactly (they do not pre-check uniqueness on `code`), so we **mirror it**: the error propagates to the global exception handler middleware (`src/api/middleware/exception_handler.py`), which maps it to a 4xx/5xx response. We do not add bespoke duplicate handling that the other resources lack — consistency with Instruments/Standards is the governing requirement here. If product owners later want a friendly "Project ID already exists" 409, that is a follow-up applied uniformly across all resources, not a Project-Master-only deviation (**backlogged**, noted below).

**`POST /api/v1/projects` — audit write.** After a successful create, an `AuditLog` row (`action="CREATE"`, `table_name="project_master"`, `record_id`) is written within the same session/transaction, identical to every other resource create. If the audit write fails, the whole transaction rolls back (fatal to the request, surfaced as 5xx) — the create and its audit record are atomic, which is the existing contract.

**`GET /api/v1/projects`.** Requires a valid session (401 otherwise). Returns `[]` when the table is empty — never an error. A DB/connection failure surfaces as 5xx via the exception middleware and is logged there (the established path); the endpoint adds no special handling.

**Frontend.** `useProjects` surfaces loading via `isLoading` (DataTable `loading` prop) and leaves list errors to the shared axios response interceptor in `apiClient` (401 → redirect/refresh handling already present). `useCreateProject` failures are not swallowed: the component's `onSuccess` only closes/toasts on success; a rejected mutation leaves the dialog open and the global axios error handling/toast applies, matching StandardsPage. Client-side required-field validation (`project_id`, `product_name`) short-circuits with `toastService.warn` before any request.

## External-input validation rules (create request)

- `project_id` — **required**, string, max 100 chars (DB), unique. Failure: 422 (missing/empty) or IntegrityError (duplicate).
- `product_name` — **required**, string, max 500. Failure: 422.
- `product_code`, `project_code`, `project_code_academic`, `bd_code_sap`, `market`, `license` — optional, string, max 100–255 per the column. `market` is unconstrained **free text** (no enum/allowed-value check); the "US / EU / IN" references are examples only. Over-length is truncated/errored at the DB layer as with existing resources (no explicit length guard beyond the column, matching the codebase).
- `group_lead`, `requested_person` — optional, string, max 255/500.
- `location` — optional, string, max 255.
- `start_date`, `end_date` — optional, ISO-8601 datetime; Pydantic parses to `datetime`. Unparseable → 422. No cross-field rule enforcing `end_date >= start_date` is added, because the existing resources enforce no analogous date-order invariant; adding one here would be an inconsistent, unrequested constraint (**backlogged**).
- `comments`, `remarks` — optional, string, max 2000.
- `status` — optional string; service coerces null/empty to `"Active"`. The UI constrains it to `Active`/`Inactive` via the dropdown; the API does not hard-reject other strings (same leniency as `status` on other resources).

## Invariant ownership

- **Uniqueness of `project_id`** — owned by the **database** (`unique=True` index), consistent with `code` on all other resource tables. The service/API do not duplicate the check, matching the existing pattern and keeping a single source of truth.
- **`status` default of `"Active"`** — owned jointly by the **ORM model** (`default="Active"`) and the **service** (`status or "Active"`), so a create with status omitted is well-defined at both layers exactly as `ReferenceStandard` does.
- **Audit-trail completeness** — owned by the **application service** (`ResourceService.create_project` writes the `AuditLog`), the same layer that owns it for every other resource, so the GxP audit contract is uniform.
- **Menu visibility** — owned by the **frontend RBAC map** (`MENU_ACCESS` in `usePermissions.ts`); there is no backend menu authority, so this is the sole enforcement point and must be edited (the critical step above).

## Testability

**Unit-testable (backend).** `ProjectRepositoryImpl.list_all`/`create` and `ResourceService.create_project`/`list_projects` are testable against an in-memory SQLite session. There are **no existing Resource Manager tests** in the repo today (the only test packages are `tests/calculation/*`, the calculation-engine suite with its own `conftest.py`, and `tests/mrn/test_repository_smoke.py`), so this establishes the **first** resource-manager test — it is newly written, not mirrored from a prior resource test. It must live in a **new package** `backend-v2/tests/resource/` (`__init__.py` + `test_project_master.py`), **not** under `tests/calculation/` (that package's `conftest.py` is scoped to template/TRF fixtures). The new module relies on the **root `tests/conftest.py`** — verified to provide the `db_session` fixture that runs `Base.metadata.create_all` (so the new table is created automatically once `ProjectMasterModel` is registered in `models/__init__.py`), plus the `make_admin_user()` / `admin_user` factory for the service's `actor`. The five cases to cover:
- (a) `create_project` persists all 17 fields and returns the entity with an `id`;
- (b) the create writes an `AuditLog` row with `table_name="project_master"` (query the `AuditLog`/`audit_logs` table on the same session);
- (c) `list_projects` returns previously-created rows;
- (d) duplicate `project_id` raises an `IntegrityError` on flush;
- (e) `status` defaults to `"Active"` when the create is called with `status=None`.

**Integration-testable (API).** No resource endpoint has an existing test, so there is no resource-endpoint harness to inherit. The real, working template to **copy** is `tests/calculation/test_coa_api.py` (and `test_template_api.py`): drive the real ASGI app via `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1")`, and override `get_session` (yield the test `db_session`) and `get_current_user` (return a `User` of the desired role) through `app.dependency_overrides` — exactly the `client` fixture shape shown there. There is no JWT minted; role gating is exercised by swapping the overridden current user rather than a real token, so reuse that override pattern (set the current user to a `make_admin_user()` for Admin paths, a non-Admin `User` for the 403 path). Cases: `GET /api/v1/projects` returns 200 + list; `POST` as Admin returns 200 and the created body; `POST` as a non-Admin returns 403; `POST` with a missing required field returns 422. Place this alongside the unit tests in the new `tests/resource/` package (e.g. `tests/resource/test_project_api.py`).

**Frontend.** The page is thin and declarative (hooks + PrimeReact), so coverage is best at the integration level (render `ProjectMasterPage` with a mocked `apiClient`, assert the table renders rows and that the Add button is gated by role). No complex client logic needs isolated unit tests beyond the required-field guard. The design is deliberately kept parallel to `StandardsPage`, which is the easiest-to-test shape already in the codebase; nothing here is hard to test, so no rethink is warranted.

## Out of scope / backlog

- **Update & delete endpoints.** Instruments exposes a domain-specific `calibrate`, but Columns/Standards/Chemicals expose **only list + create** — no generic update or delete. To mirror Standards exactly, Project Master ships **list + create only**. Edit/delete is **backlogged** (would be added uniformly across resources, not just here).
- **Friendly 409 on duplicate `project_id`** — backlogged (consistency with existing resources takes precedence; any change should be applied to all resource creates).
- **`end_date >= start_date` cross-field validation** — backlogged (no analogous invariant exists on other resources; adding it unilaterally would be inconsistent).
- **Linking Project Master to Products/Samples/TRF** — not requested; the user explicitly set aside the earlier "universal project master / MRN / product master" direction ("forget that MRN things"). This design delivers a standalone Resource Manager master only.

## Implementation checklist (file-by-file, ordered)

Backend: (1) `resource_models.py` add model → (2) `models/__init__.py` register → (3) `resource_items.py` entity → (4) `resource_repositories.py` interface → (5) `resource_repositories_impl.py` impl → (6) `resource_service.py` methods + ctor → (7) `dependency_injection.py` wire repo → (8) `resource_schemas.py` schemas → (9) `resource_endpoints.py` routes → (10) `scripts/seed_data.py` seed → re-seed DB.
Frontend: (12) `resource.types.ts` → (13) `resourceApi.ts` → (14) `useResources.ts` → (11) `ProjectMasterPage.tsx` → (15) `index.ts` → (16) `AppRouter.tsx` → (17) `MainLayout.tsx` → (18) `usePermissions.ts` MENU_ACCESS (**do not skip — nav invisible otherwise**).
Verify: `python -m scripts.seed_data` then backend tests (run the new `tests/resource/` package: `pytest tests/resource/` from `backend-v2/`); frontend `tsc`/build; log in as `admin/admin123` and confirm **Project Master** appears under Resource Manager, lists seeded rows, and the Admin-gated Add Project dialog creates a row.

---

## Review responses (revision iteration 1)

Responding to `design-review.json` (verdict: CHANGES_REQUESTED). All HIGH/MEDIUM findings addressed; NITs addressed.

- **Finding 1 (MEDIUM) — "existing resource tests" referenced don't exist.** *Addressed.* Verified the repo has only `tests/calculation/*` (with its own package-scoped `conftest.py`), `tests/mrn/test_repository_smoke.py`, and the root `tests/conftest.py`. Rewrote the backend Testability paragraph to: (1) state this is the **first** resource-manager test, newly established and not mirrored; (2) put it in a **new** `backend-v2/tests/resource/` package (`__init__.py` + `test_project_master.py`), explicitly **not** under `tests/calculation/`; (3) rely on the **root `tests/conftest.py`** (confirmed it provides the `db_session` fixture running `Base.metadata.create_all`, plus `make_admin_user`/`admin_user`). Kept the five cases (17-field persist, `project_master` AuditLog write, list returns rows, duplicate `project_id` raises on flush, `status` defaults to `"Active"`).
- **Finding 2 (MEDIUM) — unsupported "matches how resource endpoints are exercised today" claim.** *Addressed.* Removed that wording and pointed at the real template to copy: `tests/calculation/test_coa_api.py` / `test_template_api.py`. Documented their actual shape — `httpx.AsyncClient` + `ASGITransport(app=app)`, `base_url="http://test/api/v1"`, and `app.dependency_overrides` for `get_session`/`get_current_user`. Noted there is no minted JWT; role gating is tested by swapping the overridden current user (`make_admin_user()` vs a non-Admin `User`). Placed the API test in the new `tests/resource/` package.
- **Finding 3 (NIT) — 16 dialog fields vs shorter table list.** *Addressed.* Added explicit prose that all 16 stored fields are dialog inputs and are submitted on create, while the DataTable shows only a readable subset (named the omitted columns), matching StandardsPage's selective columns.
- **Finding 4 (NIT) — market free-text vs "US/EU/IN" hint.** *Addressed.* Stated in the field table, the dialog description, and the validation rules that Market is free-text `InputText` (not an enum/dropdown) and that US/EU/IN are illustrative only.
- **Finding 5 (NIT) — ISO date conversion helper has two forms.** *Addressed (note added).* Documented that the chosen form (`e.value ? (e.value as Date).toISOString() : undefined`) deliberately matches `TRFListPage.tsx` and should not be "corrected" to the `ProtocolsPage` form.
