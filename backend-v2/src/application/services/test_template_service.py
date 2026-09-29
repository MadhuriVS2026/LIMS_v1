"""
Test Template Application Service.

Owns the lifecycle of the versioned analytical calculation templates that
replace the lab's standalone Excel workbooks: creation, definition editing,
submit/approve/reject, versioning and deactivation.

E-signature verification for `approve` is performed by the caller (endpoint
layer) via `AuthService.verify_esignature` before the method runs, mirroring
`MRNService`/`TRFService`/`StabilityService`. Every state change writes exactly
one `AuditLog` entry (Property 17).

Three things here are load-bearing:

* **A definition is validated twice on the way in** — structurally through
  `TemplateDefinition.parse`, then semantically by running the evaluator once
  against empty values. The second pass is what catches circular references and
  unparseable expressions, which the parser alone cannot see, because those only
  surface once the dependency graph is built (Property 9).
* **Editing an Active template is never in-place.** `new_version` branches a
  fresh Draft with a deep-copied definition, so worksheets already executed
  against the approved version stay reproducible (Property 10).
* **Supersession happens at approval, not at branch time.** Until a new version
  is approved there is no guarantee it will ever be the one in force, so the
  previous Active version stays selectable until the replacement is signed off.
"""
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.test_template import TemplateStatus, TestTemplate
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.test_repository import ITestRepository
from src.domain.repositories.test_template_repository import ITestTemplateRepository
from src.domain.services.calculation.evaluator import EvaluationError, WorksheetEvaluator
from src.domain.services.calculation.template_schema import (
    TemplateDefinition,
    TemplateSchemaError,
)
from src.domain.services.template_code_generator import TemplateCodeGenerator

#  Statuses a template can sit in without being the one in force. At most one
#  such version may exist per code, so an analyst is never asked to choose.
_UNAPPROVED = (TemplateStatus.DRAFT.value, TemplateStatus.PENDING_APPROVAL.value)


class TestTemplateService:
    def __init__(
        self,
        template_repo: ITestTemplateRepository,
        test_repo: ITestRepository,
        audit_repo: IAuditLogRepository,
    ) -> None:
        self._repo = template_repo
        self._test_repo = test_repo
        self._audit_repo = audit_repo

    # ── List / Get ───────────────────────────────────────────────────

    async def list_templates(
        self, test_id: int | None = None, status: str | None = None
    ) -> list[TestTemplate]:
        """Requirement 1.1: any authenticated role may read the template catalogue."""
        return await self._repo.list_all(test_id=test_id, status=status)

    async def get_template(self, template_id: int) -> TestTemplate:
        template = await self._repo.get_by_id(template_id)
        if template is None:
            raise NotFoundException("Test template not found")
        return template

    async def templates_for_test(self, test_id: int) -> list[TestTemplate]:
        """Requirement 1.5: only Active templates are selectable on a TRF test line."""
        return await self._repo.list_active_for_test(test_id)

    async def list_versions(self, code: str) -> list[TestTemplate]:
        return await self._repo.list_versions_of(code)

    # ── Definition validation ────────────────────────────────────────

    @staticmethod
    def validate_definition(definition: dict) -> TemplateDefinition:
        """
        Parse and dry-run a definition, raising `ValidationException` if either
        step fails.

        The dry run matters: `TemplateDefinition.parse` validates structure but
        will happily accept `a = b + 1` alongside `b = a + 1`. Running the
        evaluator once against empty values exercises the topological sort and
        every expression, so a template that cannot compute is rejected at
        authoring time rather than at result entry (Property 9).
        """
        try:
            parsed = TemplateDefinition.parse(definition)
        except TemplateSchemaError as exc:
            raise ValidationException(f"Invalid template definition: {exc}") from exc

        try:
            WorksheetEvaluator(parsed).evaluate({}, {})
        except EvaluationError as exc:
            raise ValidationException(f"Template definition cannot be evaluated: {exc}") from exc
        except (ValueError, TypeError, ZeroDivisionError) as exc:
            #  A definition whose expressions blow up on blank inputs is not
            #  usable — an analyst would hit the same failure on a fresh sheet.
            raise ValidationException(f"Template definition cannot be evaluated: {exc}") from exc

        return parsed

    # ── Creation & editing ───────────────────────────────────────────

    async def create_template(
        self,
        name: str,
        archetype: str,
        test_id: int,
        definition: dict,
        result_unit: str | None,
        actor: User,
    ) -> TestTemplate:
        """Requirement 1.1, 1.2, 9.1: Admin creates a Draft template with a generated code."""
        self._assert_admin(actor, "create a test template")
        self.validate_definition(definition)

        test = await self._test_repo.get_by_id(test_id)
        if test is None:
            raise NotFoundException("Test not found in the Test Master")

        prefix = TemplateCodeGenerator.archetype_prefix(archetype)
        existing = await self._repo.count_by_code_prefix(prefix)
        code = TemplateCodeGenerator.generate(archetype, existing)

        template = TestTemplate(
            code=code,
            name=name,
            archetype=archetype,
            test_id=test_id,
            version=1,
            status=TemplateStatus.DRAFT.value,
            result_unit=result_unit,
            definition=definition,
            created_by=actor.username,
            modified_by=actor.username,
        )
        saved = await self._repo.create(template)

        await self._audit(
            actor,
            "TEMPLATE_CREATED",
            saved.id,
            new_values={
                "code": saved.code,
                "name": saved.name,
                "archetype": saved.archetype,
                "test_id": saved.test_id,
                "version": saved.version,
                "status": saved.status,
            },
        )
        return saved

    async def update_definition(
        self, template_id: int, definition: dict, actor: User
    ) -> TestTemplate:
        """Requirement 1.2, 1.4: the definition is only editable while Draft."""
        self._assert_admin(actor, "edit a template definition")
        template = await self.get_template(template_id)
        self.validate_definition(definition)

        if not template.can_edit_definition():
            raise ValidationException(
                f"A template's definition can only be edited while Draft. Branch a new "
                f"version instead (current status: {template.status})"
            )

        old_definition = template.definition
        template.update_definition(definition, actor.username)
        saved = await self._repo.update(template)

        await self._audit(
            actor,
            "TEMPLATE_DEFINITION_UPDATED",
            saved.id,
            #  The full definition would swamp the audit trail; the top-level
            #  shape is enough to see *that* it changed, and the definition
            #  itself is versioned data anyone can diff.
            old_values={"definition_keys": sorted(old_definition or {})},
            new_values={"definition_keys": sorted(definition or {})},
        )
        return saved

    async def update_header(
        self,
        template_id: int,
        actor: User,
        name: str | None = None,
        result_unit: str | None = None,
    ) -> TestTemplate:
        """Rename or re-unit a Draft template without touching its definition."""
        self._assert_admin(actor, "edit a test template")
        template = await self.get_template(template_id)
        if not template.can_edit_definition():
            raise ValidationException(
                f"A template can only be edited while Draft (current status: {template.status})"
            )

        old = {"name": template.name, "result_unit": template.result_unit}
        if name is not None:
            template.name = name
        if result_unit is not None:
            template.result_unit = result_unit
        template.mark_modified(actor.username)
        saved = await self._repo.update(template)

        await self._audit(
            actor,
            "TEMPLATE_UPDATED",
            saved.id,
            old_values=old,
            new_values={"name": saved.name, "result_unit": saved.result_unit},
        )
        return saved

    # ── Lifecycle ────────────────────────────────────────────────────

    async def submit_for_approval(self, template_id: int, actor: User) -> TestTemplate:
        """Requirement 1.3: Draft -> PendingApproval."""
        self._assert_admin(actor, "submit a template for approval")
        template = await self.get_template(template_id)
        if not template.can_submit():
            raise ValidationException(
                f"A template must be Draft with a definition to submit "
                f"(current status: {template.status})"
            )
        #  Re-validate on the way out of Draft: a definition may have been
        #  seeded or migrated rather than written through `update_definition`.
        self.validate_definition(template.definition)

        template.submit_for_approval(actor.username)
        saved = await self._repo.update(template)

        await self._audit(
            actor,
            "TEMPLATE_SUBMITTED",
            saved.id,
            old_values={"status": TemplateStatus.DRAFT.value},
            new_values={"status": saved.status},
        )
        return saved

    async def approve(
        self, template_id: int, actor: User, comments: str | None = None
    ) -> TestTemplate:
        """
        Requirement 1.3, 9.2: PendingApproval -> Active, e-signed by the caller.

        Any earlier Active version of the same code is deactivated and
        back-linked here, so exactly one version of a template is ever
        selectable and the history stays walkable.
        """
        self._assert_reviewer(actor, "approve")
        template = await self.get_template(template_id)
        if not template.can_approve():
            raise ValidationException(
                f"Approval requires PendingApproval status (current status: {template.status})"
            )

        template.approve(actor.username, datetime.now(timezone.utc))
        saved = await self._repo.update(template)

        superseded = await self._supersede_prior_versions(saved, actor)

        await self._audit(
            actor,
            "TEMPLATE_APPROVED",
            saved.id,
            old_values={"status": TemplateStatus.PENDING_APPROVAL.value},
            new_values={
                "status": saved.status,
                "approved_by": saved.approved_by,
                "version": saved.version,
                "superseded_template_ids": superseded,
                **({"comments": comments} if comments else {}),
            },
        )
        return saved

    async def _supersede_prior_versions(
        self, approved: TestTemplate, actor: User
    ) -> list[int]:
        """
        Deactivate and back-link any older version sharing this code.

        No separate audit entry per superseded version — the ids are recorded on
        the approval entry, which is the single event that caused them all.
        """
        superseded: list[int] = []
        for other in await self._repo.list_versions_of(approved.code):
            if other.id == approved.id or other.version >= approved.version:
                continue
            changed = False
            if other.status == TemplateStatus.ACTIVE.value:
                other.deactivate(actor.username)
                changed = True
            if other.superseded_by_id != approved.id:
                other.mark_superseded_by(approved.id, actor.username)
                changed = True
            if changed:
                await self._repo.update(other)
                superseded.append(other.id)
        return superseded

    async def reject(self, template_id: int, actor: User, reason: str) -> TestTemplate:
        """PendingApproval -> Draft, so the author can revise it."""
        self._assert_reviewer(actor, "reject")
        if not (reason or "").strip():
            raise ValidationException("A rejection reason is required")

        template = await self.get_template(template_id)
        if not template.can_reject():
            raise ValidationException(
                f"Rejection requires PendingApproval status (current status: {template.status})"
            )

        template.reject(actor.username)
        saved = await self._repo.update(template)

        await self._audit(
            actor,
            "TEMPLATE_REJECTED",
            saved.id,
            old_values={"status": TemplateStatus.PENDING_APPROVAL.value},
            new_values={"status": saved.status, "reason": reason},
        )
        return saved

    async def new_version(self, template_id: int, actor: User) -> TestTemplate:
        """
        Requirement 1.4: branch an approved template into a new Draft.

        The source is left completely untouched — including its `definition`,
        which `TestTemplate.new_version` deep-copies — so every worksheet already
        executed against it resolves against exactly what it ran on (Property 10).

        Only one unapproved version may exist per code at a time. Allowing two
        concurrent drafts would mean whichever was approved second silently
        discarded the other's work.
        """
        self._assert_admin(actor, "create a new template version")
        source = await self.get_template(template_id)
        if not source.can_version():
            raise ValidationException(
                f"A new version can only be branched from an approved template "
                f"(current status: {source.status})"
            )

        versions = await self._repo.list_versions_of(source.code)
        in_flight = next((v for v in versions if v.status in _UNAPPROVED), None)
        if in_flight is not None:
            raise ValidationException(
                f"{source.code} already has an unapproved version "
                f"(v{in_flight.version}, {in_flight.status}) — finish or reject it first"
            )

        #  Branch from the highest version of this code, not necessarily the one
        #  the caller happened to open, so version numbers never collide.
        latest_version = max((v.version for v in versions), default=source.version)
        draft = source.new_version(actor.username)
        draft.version = latest_version + 1
        saved = await self._repo.create(draft)

        await self._audit(
            actor,
            "TEMPLATE_VERSIONED",
            saved.id,
            old_values={"source_template_id": source.id, "source_version": source.version},
            new_values={"code": saved.code, "version": saved.version, "status": saved.status},
        )
        return saved

    async def deactivate(
        self, template_id: int, actor: User, reason: str | None = None
    ) -> TestTemplate:
        """
        Requirement 1.5: an Inactive template stops being selectable on new test
        lines but keeps resolving for worksheets already bound to it.
        """
        self._assert_admin(actor, "deactivate a test template")
        template = await self.get_template(template_id)
        if not template.can_deactivate():
            raise ValidationException(
                f"Only an Active template can be deactivated (current status: {template.status})"
            )

        template.deactivate(actor.username)
        saved = await self._repo.update(template)

        await self._audit(
            actor,
            "TEMPLATE_DEACTIVATED",
            saved.id,
            old_values={"status": TemplateStatus.ACTIVE.value},
            new_values={"status": saved.status, **({"reason": reason} if reason else {})},
        )
        return saved

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _assert_admin(actor: User, action: str) -> None:
        if not actor.has_role("Admin"):
            raise ForbiddenException(f"Only an Admin may {action}")

    @staticmethod
    def _assert_reviewer(actor: User, action: str) -> None:
        if not actor.has_role("Admin", "Supervisor", "QA"):
            raise ForbiddenException(
                f"Only Admin, Supervisor or QA may {action} a test template"
            )

    async def _audit(
        self,
        actor: User,
        action: str,
        record_id: int | None,
        old_values: dict | None = None,
        new_values: dict | None = None,
    ) -> None:
        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action=action,
                table_name="test_templates",
                record_id=record_id,
                old_values=old_values,
                new_values=new_values,
            )
        )
