# Design Review — Project Master (Resource Manager)

Reviewed: `d:\RD-instance\GIT\.agents\tasks\resource-project-master\design.md`
Scope: DB-backed Project Master resource mirroring the Instruments / Reference Standards Resource Manager pattern, end to end.
Method: Every structural claim in the design was checked against the actual source in `backend-v2` and `frontend-react`. This is revision iteration 1; the design already carries a "Review responses" section addressing 5 prior findings — I re-verified those resolutions independently rather than trusting the prose.

## Verdict

APPROVED — zero HIGH and zero MEDIUM findings. All findings below are NITs and do not block implementation.

The design faithfully mirrors the existing resource-slice pattern, covers all 17 fields, identifies the correct table-creation mechanism (`Base.metadata.create_all` + seed, no Alembic), names every file to add/change concretely, and gets the single most dangerous detail — the RBAC `MENU_ACCESS` grant that makes the nav item render — correct and explicit.

---

## Findings

1. NIT — Seed block omits `created_by`/`requested_person`/`remarks` from the tuple but hard-codes them in the `.add(...)`.
   Where: `scripts/seed_data.py` seed block (design file #10). The `projects_data` tuples carry 13 positional values and the `ProjectMasterModel(...)` call appends `requested_person="System"`, `remarks="Seeded project."`, `created_by="System"` as constants for all three rows.
   Why minor: Functionally correct and consistent with how other seeds mix tuple data + constants; purely a readability nit.
   Concrete fix (optional): leave as-is, or drop a one-line comment above the loop noting that `requested_person`/`remarks`/`created_by` are intentionally constant across seed rows. No code change required to proceed.

2. NIT — `index.ts` export is appended at the end rather than grouped with the other page exports.
   Where: `src/features/resource-management/index.ts` (design file #15). The existing file lists Instruments, Chemicals, Standards, Columns, Volumetric; the design adds `ProjectMasterPage` without specifying position.
   Why minor: Order is irrelevant to module resolution.
   Concrete fix: add `export { ProjectMasterPage } from './pages/ProjectMasterPage';` anywhere in the barrel; grouping it with the Resource Manager pages keeps it tidy.

3. NIT — API integration-test override uses root-conftest `make_admin_user()` whereas the copied template (`tests/calculation/test_coa_api.py`) pulls its `user()`/`seed_test` helpers from the calculation-scoped conftest.
   Where: Testability → Integration-testable (API). The design correctly says to establish a new `tests/resource/` package on the root conftest and to override `get_current_user` with a `User`. The template it copies happens to import role helpers from `tests.calculation.conftest`, which must NOT be reused from the new package.
   Why minor: The design already calls out not placing tests under `tests/calculation/` and names `make_admin_user()` (a root-conftest export) as the override value, so the guidance is internally correct — this note just flags the one import in the template that the implementer must swap for the root-conftest factory rather than copy verbatim.
   Concrete fix: in `tests/resource/test_project_api.py`, build the override user with `from tests.conftest import make_admin_user` (and a non-Admin via `make_analyst_user()`), not `from tests.calculation.conftest import user`.

---

## Verified Assumptions

Each item below was confirmed against the cited source file.

- Backend layered pattern exists exactly as described. `resource_items.py` (entities), `resource_repositories.py` (interfaces), `resource_repositories_impl.py` (impls with `list_all`/`create`/`_to_entity`), `resource_service.py` (`ResourceService` with per-resource list/create + `_audit_repo.write`), `resource_schemas.py` (Create*/‌*Response Pydantic v2), `resource_endpoints.py` (prefix-less `router`), `dependency_injection.py` (`Container.get_resource_service`). The design's additions slot into each verbatim.
- `ResourceService.__init__` order is `instrument_repo, column_repo, standard_repo, chemical_repo, volumetric_repo, audit_repo`. The design inserts `project_repo` after `volumetric_repo` and before `audit_repo` — valid and keeps audit last. Confirmed.
- `create_reference_standard` is a faithful template for `create_project`: it builds the entity with `created_by=actor.username, modified_by=actor.username`, calls the repo, then writes an `AuditLog(user_id=actor.id, username=actor.username, action="CREATE", table_name=..., record_id=created.id)`. The `AuditLog` dataclass (audit_log.py) accepts exactly those kwargs. Confirmed.
- DI: `Container.get_resource_service` constructs `InstrumentRepositoryImpl(session), ColumnRepositoryImpl(session), ReferenceStandardRepositoryImpl(session), ChemicalRepositoryImpl(session), VolumetricSolutionRepositoryImpl(session), AuditLogRepositoryImpl(session)`. Adding `ProjectRepositoryImpl(session)` before `AuditLogRepositoryImpl(session)` matches the new ctor position. Confirmed.
- Endpoints: `list` gated by `Depends(get_current_user)`, `create` gated by `Depends(require_role("Admin"))`, both using `Container.get_resource_service(session)`. This matches the reference-standards pair exactly (Standards create is Admin-only). Confirmed.
- Router: `resource_router` is already registered in `router.py` on `api_v1_router = APIRouter(prefix="/api/v1")`, and `resource_endpoints.router = APIRouter(tags=[...])` carries no prefix. So new `/projects` routes resolve to `/api/v1/projects` with no edit to `router.py`. Confirmed — the design's claim is correct.
- Model registration: `src/infrastructure/database/models/__init__.py` imports the resource models from `resource_models` so they register with `Base.metadata`; `session.py` imports the `models` package and `init_models()` runs `Base.metadata.create_all`. Adding `ProjectMasterModel` to the `resource_models` import block is indeed the single wiring point. Confirmed.
- Table-creation mechanism: No Alembic. `init_models()` (startup) and `scripts/seed_data.py` (`drop_all` + `create_all` + seed) both use `Base.metadata.create_all`. The design correctly identifies this and correctly notes an existing dev DB must be re-seeded/recreated. Confirmed.
- Model imports: `resource_models.py` already imports `DateTime` and `String` from sqlalchemy (and `datetime`); the `ProjectMasterModel` snippet uses only those plus `BaseModel`. No new imports needed beyond what's present. Confirmed.
- `BaseModel` supplies `id` + `created_by/created_date/modified_by/modified_date`; `BaseEntity` supplies the same as dataclass fields with defaults. The `ProjectMaster` dataclass gives every field a default, satisfying dataclass inheritance rules (no non-default field after a default). Confirmed.
- Seed script imports `from datetime import datetime, timedelta, timezone` and imports resource models explicitly — the design's seed block (`datetime(...)`, `timezone.utc`, `ProjectMasterModel(...)`) compiles against that. Confirmed.
- All 17 fields are accounted for. Sr No = derived display ordinal (not stored); 16 stored columns: `project_id` (unique business key / `code` analogue), `product_name` (required), `product_code`, `project_code`, `project_code_academic`, `bd_code_sap`, `group_lead`, `location`, `market`, `start_date`, `end_date`, `license`, `comments`, `status` (default "Active"), `requested_person`, `remarks`. Entity, model, schema (request+response), and TS interface all list the same 16. Confirmed consistent across all four definitions.
- **RBAC — the critical path.** `MainLayout.tsx` filters `NAV_ITEMS` by `menuKeys.includes(item.menuKey)`; `useMenuPermissions()` derives `menuKeys` as `Object.keys(MENU_ACCESS).filter(key => MENU_ACCESS[key].some(r => held.has(r)))`. A `menuKey` absent from `MENU_ACCESS` therefore yields no `menuKeys` entry and the item never renders — exactly the failure mode the design calls out. Adding `projects: ['Admin', 'Analyst', 'Supervisor', 'QA']` to `MENU_ACCESS` and a `NAV_ITEMS` entry with `menuKey: 'projects'` makes the item render for an Admin (and the other base roles). There is no backend menu-grant table. The design's "CRITICAL" step is accurate and sufficient. Confirmed.
- Frontend API/hook pattern: `apiClient` baseURL is `/api/v1`, so `'/projects'` → `/api/v1/projects`. `resourceApi.ts` uses per-resource `{list, create}` objects; `useResources.ts` uses `useQuery({queryKey, queryFn})` + `useMutation({mutationFn, onSuccess: invalidateQueries})`. The design's `projectApi` / `useProjects` / `useCreateProject` match verbatim. Confirmed.
- Route: `/projects` is unused in `AppRouter.tsx` (Sample Manager uses `/products`, distinct). Resource pages are named-imported from `@features/resource-management`. The design's route + import additions are correct. Confirmed.
- Page template: `StandardsPage.tsx` uses `useReferenceStandards()`/`useCreateReferenceStandard()`, `usePermissions().hasRole`, an Admin-gated Add button, a `DataTable` with selective columns, `StatusBadge`, a `Dialog`, a Code+Name required-field guard via `toastService.warn`, and `Dropdown options={CATEGORIES}` (string array). The `ProjectMasterPage` design mirrors each of these. `StatusBadge` exists at `src/shared/components/StatusBadge.tsx`. Confirmed.
- Testability: root `tests/conftest.py` provides the `db_session` fixture (in-memory SQLite, runs `Base.metadata.create_all`, drops after) and `make_admin_user`/`admin_user` (plus analyst/supervisor/qa). `tests/calculation/test_coa_api.py` drives the app via `AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1")` and overrides `get_session`/`get_current_user` through `app.dependency_overrides`. `tests/resource/` does not yet exist, so it is genuinely new. All design claims here are accurate.
- `require_role("Admin")` + role inheritance: `dependencies.py` defines `require_role`, `get_current_user`, `get_session`, and `effective_roles`. Admin satisfies the gate directly. Confirmed.

## Unverified / Wrong Assumptions

None. Every verifiable claim in the design was checked against source and found accurate. No claim in the design was contradicted by the code.

(Note: the three NITs above are not wrong assumptions — they are cosmetic/clarity observations. They do not affect correctness of the plan.)
