"""
Worksheet Application Service.

A worksheet is one filled-in test template bound to a single TRF test line. This
service owns creation, live preview, value entry/correction, and confirmation of
the reportable result back onto the test line.

Design points that carry weight:

* **Who may edit is a function of the parent TRF's status, not the worksheet's.**
  `TestWorksheet.edit_mode_for` maps `InProgress -> Entry` (Analyst/Admin) and
  `PendingADGLRelease -> Correction` (QA/Admin). Anything else is refused. Both
  the status and the role must agree, and a rejected mutation leaves the stored
  values byte-for-byte unchanged (Property 12).
* **`preview` never persists.** The UI recalculates on every keystroke, so
  writing to the database or the audit trail there would flood both and turn a
  read into a write. Preview takes the caller's candidate values, evaluates, and
  returns — nothing is saved.
* **Computed values are not stored while in progress.** They are derived on
  demand so a template fix is picked up immediately. At confirmation the full
  computed state is snapshotted, and that snapshot is never rewritten
  (Requirement 2.7 / Property 16).
* **A worksheet is bound to a template *version*** at creation and never
  re-pointed, so it stays reproducible after the template moves on.
"""
from datetime import datetime, timezone
from typing import Any

from src.application.exceptions.application_exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.product import Product
from src.domain.entities.specification import units_comparable
from src.domain.entities.test_template import (
    WORKSHEET_REVIEWER_ROLES,
    TestTemplate,
    TestWorksheet,
    WorksheetEditMode,
)
from src.domain.entities.trf import TestRequestForm, TRFTestLine
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.product_repository import IProductRepository
from src.domain.repositories.specification_repository import ISpecificationRepository
from src.domain.repositories.test_template_repository import (
    ITestTemplateRepository,
    ITestWorksheetRepository,
)
from src.domain.repositories.trf_repository import ITRFRepository
from src.domain.services.calculation.evaluator import (
    CriterionResult,
    EvaluationError,
    WorksheetEvaluator,
    WorksheetResult,
)
from src.domain.services.calculation.expression import EMPTY
from src.domain.services.calculation.template_schema import (
    TemplateDefinition,
    TemplateSchemaError,
)

#  Roles permitted per edit mode. Kept here rather than in the domain because
#  this is the layer that holds the `User`.
_ROLES_BY_MODE: dict[WorksheetEditMode, tuple[str, ...]] = {
    WorksheetEditMode.ENTRY: ("Analyst", "Admin"),
    WorksheetEditMode.CORRECTION: ("QA", "Admin"),
}

#  The refusal message goes to a lab user, so it names what they were trying to
#  do rather than echoing an enum member at them.
_VERB_BY_MODE: dict[WorksheetEditMode, str] = {
    WorksheetEditMode.ENTRY: "enter",
    WorksheetEditMode.CORRECTION: "correct",
}


class WorksheetService:
    def __init__(
        self,
        worksheet_repo: ITestWorksheetRepository,
        template_repo: ITestTemplateRepository,
        trf_repo: ITRFRepository,
        product_repo: IProductRepository,
        audit_repo: IAuditLogRepository,
        #  Optional so existing callers and tests keep working; when absent the
        #  unit check is simply skipped rather than the service refusing to build.
        spec_repo: ISpecificationRepository | None = None,
    ) -> None:
        self._repo = worksheet_repo
        self._template_repo = template_repo
        self._trf_repo = trf_repo
        self._product_repo = product_repo
        self._audit_repo = audit_repo
        self._spec_repo = spec_repo

    # ── Get ──────────────────────────────────────────────────────────

    async def get_worksheet(self, worksheet_id: int) -> TestWorksheet:
        worksheet = await self._repo.get_by_id(worksheet_id)
        if worksheet is None:
            raise NotFoundException("Worksheet not found")
        return worksheet

    async def get_worksheet_for_line(self, line_id: int) -> TestWorksheet | None:
        """`None` rather than 404 — a test line legitimately may not have one."""
        return await self._repo.get_by_test_line(line_id)

    async def list_for_trf(self, trf_id: int) -> list[TestWorksheet]:
        return await self._repo.list_by_trf(trf_id)

    # ── Creation ─────────────────────────────────────────────────────

    async def create_worksheet(
        self, line_id: int, template_id: int, actor: User
    ) -> TestWorksheet:
        """
        Requirement 5.1, 5.2: attach an Active template to a test line.

        Context fields are pre-populated from the parent TRF header at this
        moment, not resolved lazily at render time. A worksheet reporting the
        batch it was actually run against is the point; if the TRF header were
        later edited, a lazily-resolved context would silently rewrite history.
        """
        line, trf = await self._load_line_and_trf(line_id)
        self._assert_can_edit(trf, actor)

        existing = await self._repo.get_by_test_line(line_id)
        if existing is not None:
            raise ValidationException(
                f"This test line already has a worksheet (id {existing.id})"
            )

        template = await self._template_repo.get_by_id(template_id)
        if template is None:
            raise NotFoundException("Test template not found")
        if not template.is_selectable:
            raise ValidationException(
                f"Only an Active template can be attached to a test line "
                f"(template {template.code} is {template.status})"
            )
        if template.test_id != line.test_id:
            raise ValidationException(
                f"Template {template.code} is defined for a different test than this line"
            )

        await self._assert_units_comparable(trf, line, template)

        definition = self._parse(template)
        product = await self._product_repo.get_by_id(trf.product_id)
        context_values = self._seed_context(definition, trf, line, product, actor)

        worksheet = TestWorksheet(
            trf_test_line_id=line_id,
            template_id=template.id,
            template_version=template.version,
            context_values=context_values,
            group_values={},
            created_by=actor.username,
            modified_by=actor.username,
            template_code=template.code,
            template_name=template.name,
        )
        saved = await self._repo.create(worksheet)

        await self._audit(
            actor,
            "WORKSHEET_CREATED",
            saved.id,
            new_values={
                "trf_test_line_id": line_id,
                "template_id": template.id,
                "template_code": template.code,
                "template_version": template.version,
            },
        )
        return saved

    # ── Preview ──────────────────────────────────────────────────────

    async def preview(
        self,
        worksheet_id: int,
        context_values: dict[str, Any] | None = None,
        group_values: dict[str, list[dict[str, Any]]] | None = None,
    ) -> tuple[TestWorksheet, TestTemplate, WorksheetResult]:
        """
        Requirement 2.1, 2.5: compute without persisting.

        Candidate values from the caller are evaluated on top of what is stored,
        so the UI can recalculate live. Nothing is written — no row, no audit
        entry.

        Deliberately not role-gated beyond authentication: it exposes no more
        than a GET of the worksheet plus arithmetic, and gating it on the *edit*
        roles would stop a reviewer from seeing the numbers they are reviewing.
        """
        worksheet = await self.get_worksheet(worksheet_id)
        template = await self._load_bound_template(worksheet)
        definition = self._parse(template)

        merged_context = {
            **(worksheet.context_values or {}),
            **(context_values or {}),
        }
        merged_groups = (
            {k: [dict(r) for r in v] for k, v in group_values.items()}
            if group_values is not None
            else {k: [dict(r) for r in v] for k, v in (worksheet.group_values or {}).items()}
        )

        result = self._evaluate(definition, merged_context, merged_groups)
        return worksheet, template, result

    # ── Value entry & correction ─────────────────────────────────────

    async def save_values(
        self,
        worksheet_id: int,
        actor: User,
        context_values: dict[str, Any] | None = None,
        group_values: dict[str, list[dict[str, Any]]] | None = None,
        reason: str | None = None,
    ) -> tuple[TestWorksheet, TestTemplate, WorksheetResult]:
        """
        Requirement 4.2, 5.3, 5.6, 9.3, 9.4: persist entered values.

        The permitted mode comes from the parent TRF's status; the role must
        match it. In `Correction` mode a reason is mandatory, since that path
        rewrites a result an analyst already submitted.

        Nothing is mutated until every check has passed, so a rejected call
        leaves the worksheet exactly as it was (Property 12).
        """
        worksheet = await self.get_worksheet(worksheet_id)
        _line, trf = await self._load_line_and_trf(worksheet.trf_test_line_id)
        mode = self._assert_can_edit(trf, actor)

        #  A worksheet submitted for review is frozen until a reviewer acts —
        #  the TRF-status check above cannot see this worksheet-level lock.
        if not worksheet.is_worksheet_editable:
            raise ValidationException(
                f"This worksheet is {worksheet.status} and cannot be edited until a "
                f"reviewer approves or refers it back."
            )

        if mode is WorksheetEditMode.CORRECTION and not (reason or "").strip():
            raise ValidationException("A reason is required when correcting worksheet values")

        template = await self._load_bound_template(worksheet)
        definition = self._parse(template)

        clean_context = self._filter_context(definition, context_values)
        clean_groups = self._filter_groups(definition, group_values)

        #  Evaluate before writing: a payload that cannot compute is rejected
        #  rather than stored, so a worksheet is never left unevaluable.
        merged_context = {**(worksheet.context_values or {}), **clean_context}
        merged_groups = (
            clean_groups
            if group_values is not None
            else {k: [dict(r) for r in v] for k, v in (worksheet.group_values or {}).items()}
        )
        result = self._evaluate(definition, merged_context, merged_groups)

        changes = self._diff(worksheet, merged_context, merged_groups)

        if worksheet.is_confirmed:
            #  Re-opening keeps the prior snapshot until the next confirmation
            #  replaces it, so a released TRF never has an unsupported result.
            worksheet.reopen(actor.username)

        worksheet.set_values(merged_context, merged_groups, actor.username)
        saved = await self._repo.update(worksheet)

        await self._audit(
            actor,
            "WORKSHEET_VALUES_CORRECTED"
            if mode is WorksheetEditMode.CORRECTION
            else "WORKSHEET_VALUES_SAVED",
            saved.id,
            old_values=changes["old"] or None,
            new_values={
                **(changes["new"] or {}),
                "area_sources": self._area_sources(definition, merged_groups),
                **({"reason": reason} if reason else {}),
            },
        )
        return saved, template, result

    # ── Confirmation ─────────────────────────────────────────────────

    async def confirm_result(
        self, worksheet_id: int, actor: User
    ) -> tuple[TestWorksheet, TRFTestLine, WorksheetResult]:
        """
        Requirement 2.7, 5.4, 5.5, 6.3, 10.3: freeze and publish the result.

        Refuses while any *blocking* acceptance criterion fails — an out-of-spec
        system suitability must be resolved, not reported. Advisory criteria are
        recorded in the snapshot but do not gate.
        """
        worksheet = await self.get_worksheet(worksheet_id)
        line, trf = await self._load_line_and_trf(worksheet.trf_test_line_id)
        mode = self._assert_can_edit(trf, actor)
        if mode is not WorksheetEditMode.ENTRY:
            raise ValidationException(
                f"A result can only be confirmed while the TRF is InProgress "
                f"(current status: {trf.status})"
            )
        if not worksheet.is_worksheet_editable:
            raise ValidationException(
                f"This worksheet is {worksheet.status}; it must be approved through "
                f"review rather than confirmed directly."
            )

        template = await self._load_bound_template(worksheet)
        definition = self._parse(template)
        result = self._evaluate(
            definition, worksheet.context_values or {}, worksheet.group_values or {}
        )

        if result.has_blocking_failure:
            failed = "; ".join(
                f"{c.label} (observed {self._plain(c.observed)}, requires {c.limit_text or c.operator.value})"
                for c in result.blocking_failures
            )
            raise ValidationException(
                f"Cannot confirm the result while a blocking acceptance criterion fails: {failed}"
            )

        reportable = self._plain(result.reportable_result)
        if reportable is None or reportable == "":
            raise ValidationException(
                "The template's reportable result is blank — complete the required "
                "entries before confirming"
            )

        reportable_text = self._format_result(reportable, template.result_unit)
        snapshot = self._snapshot(worksheet, template, result, actor)

        worksheet.confirm(actor.username, datetime.now(timezone.utc), snapshot, reportable_text)
        saved = await self._repo.update(worksheet)

        old_result = line.result
        line.set_result(reportable_text, line.remark)
        line.mark_modified(actor.username)
        saved_line = await self._trf_repo.update_test_line(line)

        await self._audit(
            actor,
            "WORKSHEET_RESULT_CONFIRMED",
            saved.id,
            old_values={"test_line_result": old_result},
            new_values={
                "test_line_id": line.id,
                "test_line_result": reportable_text,
                "template_code": template.code,
                "template_version": worksheet.template_version,
            },
        )
        return saved, saved_line, result

    # ── Review cycle ─────────────────────────────────────────────────

    async def submit_for_review(
        self, worksheet_id: int, actor: User, comments: str | None
    ) -> tuple[TestWorksheet, TestTemplate, WorksheetResult]:
        """
        Analyst submits the worksheet to a supervisor. Only while the parent TRF
        permits entry and the worksheet is in an editable state; locks editing
        until a reviewer approves or refers it back.
        """
        worksheet = await self.get_worksheet(worksheet_id)
        _line, trf = await self._load_line_and_trf(worksheet.trf_test_line_id)
        mode = self._assert_can_edit(trf, actor)
        if mode is not WorksheetEditMode.ENTRY:
            raise ValidationException(
                f"A worksheet can only be submitted for review while the TRF is "
                f"InProgress (current status: {trf.status})"
            )

        template = await self._load_bound_template(worksheet)
        definition = self._parse(template)
        #  Evaluate so a submission that cannot compute is caught up front.
        result = self._evaluate(
            definition, worksheet.context_values or {}, worksheet.group_values or {}
        )

        worksheet.submit_for_review(actor.username, datetime.now(timezone.utc), comments)
        saved = await self._repo.update(worksheet)

        await self._audit(
            actor,
            "WORKSHEET_SUBMITTED_FOR_REVIEW",
            saved.id,
            new_values={"status": saved.status, "comments": comments},
        )
        return saved, template, result

    async def refer_back_review(
        self, worksheet_id: int, actor: User, comments: str | None
    ) -> tuple[TestWorksheet, TestTemplate, WorksheetResult]:
        """Reviewer returns a submitted worksheet to the analyst for changes."""
        worksheet = await self.get_worksheet(worksheet_id)
        self._assert_can_review(worksheet, actor)
        if not (comments or "").strip():
            raise ValidationException("A comment is required when referring a worksheet back")

        template = await self._load_bound_template(worksheet)
        definition = self._parse(template)
        result = self._evaluate(
            definition, worksheet.context_values or {}, worksheet.group_values or {}
        )

        worksheet.refer_back(actor.username, datetime.now(timezone.utc), comments)
        saved = await self._repo.update(worksheet)

        await self._audit(
            actor,
            "WORKSHEET_REFERRED_BACK",
            saved.id,
            new_values={"status": saved.status, "comments": comments},
        )
        return saved, template, result

    async def approve_review(
        self, worksheet_id: int, actor: User, comments: str | None
    ) -> tuple[TestWorksheet, TRFTestLine, WorksheetResult]:
        """
        Reviewer accepts a submitted worksheet: records the review outcome and
        confirms the result (snapshot + publish to the test line), refusing while
        any blocking acceptance criterion fails.
        """
        worksheet = await self.get_worksheet(worksheet_id)
        line, trf = await self._load_line_and_trf(worksheet.trf_test_line_id)
        self._assert_can_review(worksheet, actor)

        template = await self._load_bound_template(worksheet)
        definition = self._parse(template)
        result = self._evaluate(
            definition, worksheet.context_values or {}, worksheet.group_values or {}
        )

        if result.has_blocking_failure:
            failed = "; ".join(
                f"{c.label} (observed {self._plain(c.observed)}, requires {c.limit_text or c.operator.value})"
                for c in result.blocking_failures
            )
            raise ValidationException(
                f"Cannot approve the worksheet while a blocking acceptance criterion fails: {failed}"
            )

        reportable = self._plain(result.reportable_result)
        if reportable is None or reportable == "":
            raise ValidationException(
                "The reportable result is blank — the worksheet cannot be approved"
            )

        reportable_text = self._format_result(reportable, template.result_unit)
        snapshot = self._snapshot(worksheet, template, result, actor)

        now = datetime.now(timezone.utc)
        worksheet.approve_review(actor.username, now, comments)
        worksheet.confirm(actor.username, now, snapshot, reportable_text)
        saved = await self._repo.update(worksheet)

        old_result = line.result
        line.set_result(reportable_text, line.remark)
        line.mark_modified(actor.username)
        saved_line = await self._trf_repo.update_test_line(line)

        await self._audit(
            actor,
            "WORKSHEET_REVIEW_APPROVED",
            saved.id,
            old_values={"test_line_result": old_result},
            new_values={
                "test_line_id": line.id,
                "test_line_result": reportable_text,
                "comments": comments,
                "template_code": template.code,
                "template_version": worksheet.template_version,
            },
        )
        return saved, saved_line, result

    def _assert_can_review(self, worksheet: TestWorksheet, actor: User) -> None:
        """A worksheet under review may be actioned only by a reviewer role."""
        if not worksheet.is_pending_review:
            raise ValidationException(
                f"Only a worksheet pending review can be reviewed "
                f"(current status: {worksheet.status})"
            )
        if not actor.has_role(*WORKSHEET_REVIEWER_ROLES):
            raise ForbiddenException(
                f"Only {' / '.join(WORKSHEET_REVIEWER_ROLES)} may review a worksheet"
            )

    # ── Loading helpers ──────────────────────────────────────────────

    async def _load_line_and_trf(self, line_id: int) -> tuple[TRFTestLine, TestRequestForm]:
        line = await self._trf_repo.get_test_line_by_id(line_id)
        if line is None:
            raise NotFoundException("Test line not found")
        trf = await self._trf_repo.get_by_id(line.trf_id)
        if trf is None:
            raise NotFoundException("Test Request Form not found")
        return line, trf

    async def _assert_units_comparable(
        self, trf: TestRequestForm, line: TRFTestLine, template: TestTemplate
    ) -> None:
        """
        Refuse a template whose result unit disagrees with the specification limits.

        Caught here rather than at certificate time on purpose. A mismatch found
        now costs the analyst one dialog; found at COA generation it has already
        produced a released result that cannot be compared to anything, and the
        certificate has to report `NotEvaluated` for a test that was performed
        correctly.

        Only a *definite* disagreement blocks — a specification with no unit is
        permitted, since most existing ones have none.
        """
        if self._spec_repo is None:
            return
        spec = await self._spec_repo.get_active_for_product(trf.product_id)
        if spec is None:
            return
        spec_test = next((t for t in spec.tests if t.test_id == line.test_id), None)
        if spec_test is None or spec_test.unit is None:
            return
        if units_comparable(template.result_unit, spec_test.unit):
            return

        raise ValidationException(
            f"Template {template.code} reports its result in "
            f"{template.result_unit!r}, but the active specification for this test "
            f"sets limits in {spec_test.unit!r}. Results from this template could not "
            f"be judged against those limits, so the certificate would have to report "
            f"them as not evaluated. Correct the specification unit or choose a "
            f"different template."
        )

    async def _load_bound_template(self, worksheet: TestWorksheet) -> TestTemplate:
        """
        Resolve the template *version* the worksheet was created against.

        Deliberately by id, not by `(code, latest version)`: a worksheet must
        keep computing against what it ran on even after the template is
        re-versioned or deactivated (Requirement 2.7 / Property 10).
        """
        template = await self._template_repo.get_by_id(worksheet.template_id)
        if template is None:
            raise NotFoundException(
                "The template this worksheet was created against no longer exists"
            )
        return template

    @staticmethod
    def _parse(template: TestTemplate) -> TemplateDefinition:
        try:
            return TemplateDefinition.parse(template.definition)
        except TemplateSchemaError as exc:
            raise ValidationException(
                f"Template {template.code} v{template.version} has an invalid definition: {exc}"
            ) from exc

    @staticmethod
    def _evaluate(
        definition: TemplateDefinition,
        context_values: dict[str, Any],
        group_values: dict[str, list[dict[str, Any]]],
    ) -> WorksheetResult:
        try:
            return WorksheetEvaluator(definition).evaluate(context_values, group_values)
        except EvaluationError as exc:
            raise ValidationException(f"Worksheet cannot be evaluated: {exc}") from exc
        except ZeroDivisionError as exc:
            raise ValidationException(
                f"Worksheet calculation divided by zero — check the entered values: {exc}"
            ) from exc

    # ── Authorisation ────────────────────────────────────────────────

    @staticmethod
    def _assert_can_edit(trf: TestRequestForm, actor: User) -> WorksheetEditMode:
        """
        Requirements 5.3, 5.6, 9.3, 9.4: status decides the mode, role must match.

        Raises before anything is mutated, which is what makes a rejected
        mutation a genuine no-op.
        """
        mode = TestWorksheet.edit_mode_for(trf.status)
        if mode is None:
            raise ValidationException(
                f"Worksheet values can only be entered while the TRF is InProgress, or "
                f"corrected while PendingADGLRelease (current status: {trf.status})"
            )
        allowed = _ROLES_BY_MODE[mode]
        if not actor.has_role(*allowed):
            raise ForbiddenException(
                f"Only {' or '.join(allowed)} may {_VERB_BY_MODE[mode]} worksheet values "
                f"while the TRF is {trf.status}"
            )
        #  Any analyst (not only the one who accepted the TRF) may enter results.
        #  Access is governed by role; individual ownership is not required. The
        #  audit trail still records exactly who made each change.
        return mode

    # ── Value shaping ────────────────────────────────────────────────

    @staticmethod
    def _seed_context(
        definition: TemplateDefinition,
        trf: TestRequestForm,
        line: TRFTestLine,
        product: Product | None,
        actor: User,
    ) -> dict[str, Any]:
        """
        Resolve each context field's declared `source` against the TRF header,
        product, test line and session. An unresolvable source yields the field's
        default (or nothing), leaving it for the analyst rather than failing
        creation — templates outlive any one header shape.
        """
        available: dict[str, Any] = {
            "product.code": product.code if product else None,
            "product.name": product.name if product else None,
            "product.material_type": product.material_type if product else None,
            "product.storage_condition": product.storage_condition if product else None,
            "trf.trf_number": trf.trf_number,
            "trf.ar_number": trf.ar_number,
            "trf.batch_number": trf.batch_number,
            "trf.label_claim": trf.label_claim,
            #  Label Claim is free text on the TRF ("50 mg/vial", "LC-0072e76").
            #  Only auto-fill the numeric worksheet field when the TRF value is a
            #  clean number; otherwise leave it blank for manual entry, since the
            #  assay formula divides by it.
            "trf.label_claim_numeric": WorksheetService._as_number(trf.label_claim),
            "trf.stage_of_sample": trf.stage_of_sample,
            "trf.group_name": trf.group_name,
            "trf.quantity": trf.quantity,
            "trf.storage_condition": trf.storage_condition,
            "trf.storage_period": trf.storage_period,
            "trf.pack_details": trf.pack_details,
            "trf.manufactured_by": trf.manufactured_by,
            "trf.product_id": trf.product_id,
            "trf.remark": trf.remark,
            "line.test_code": line.test_code,
            "line.test_name": line.test_name,
            "line.specification": line.specification,
            "line.line_no": line.line_no,
            "line.raw_data_reference": line.raw_data_reference,
            "session.username": actor.username,
            "session.analyst": actor.username,
            "session.date": datetime.now(timezone.utc).date().isoformat(),
        }
        seeded: dict[str, Any] = {}
        for cf in definition.context:
            value = available.get(cf.source) if cf.source else None
            if value is None:
                value = cf.default
            if value is not None:
                seeded[cf.key] = value
        return seeded

    @staticmethod
    def _as_number(value: Any) -> float | None:
        """Return the value as a float if it is a clean number (int/float, or a
        string that is purely numeric), else None. Used so a free-text TRF Label
        Claim is only auto-filled when it is actually a usable number."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            s = value.strip()
            try:
                return float(s)
            except ValueError:
                return None
        return None

    @staticmethod
    def _filter_context(
        definition: TemplateDefinition, context_values: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Accept only context keys the template declares as overridable."""
        if not context_values:
            return {}
        out: dict[str, Any] = {}
        for key, value in context_values.items():
            cf = definition.context_field(key)
            if cf is None:
                raise ValidationException(f"Unknown context field {key!r}")
            if not cf.overridable:
                raise ValidationException(
                    f"Context field {cf.label!r} is derived from the TRF and cannot be overridden"
                )
            out[key] = value
        return out

    @staticmethod
    def _filter_groups(
        definition: TemplateDefinition,
        group_values: dict[str, list[dict[str, Any]]] | None,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Keep only editable fields, and enforce each group's row bounds.

        Calculated fields are dropped rather than rejected: the UI round-trips
        the whole worksheet including the values it just displayed, and silently
        ignoring them is friendlier than a 400 while still guaranteeing a client
        can never overwrite a computed number.
        """
        if not group_values:
            return {}
        out: dict[str, list[dict[str, Any]]] = {}
        for group_key, rows in group_values.items():
            group = definition.group(group_key)
            if group is None:
                raise ValidationException(f"Unknown group {group_key!r}")
            if not isinstance(rows, list):
                raise ValidationException(f"Group {group_key!r} values must be a list of rows")

            if group.is_multi_row:
                if len(rows) > group.rows.max:
                    raise ValidationException(
                        f"Group {group.label!r} accepts at most {group.rows.max} rows "
                        f"({len(rows)} supplied)"
                    )
            elif len(rows) > 1:
                raise ValidationException(f"Group {group.label!r} accepts a single row")

            editable = {f.key for f in group.fields if f.is_editable}
            out[group_key] = [
                {k: v for k, v in (row or {}).items() if k in editable} for row in rows
            ]
        return out

    @staticmethod
    def _area_sources(
        definition: TemplateDefinition, group_values: dict[str, list[dict[str, Any]]]
    ) -> dict[str, str]:
        """
        Requirement 4.2, 4.5 / Property 14: record where every populated area
        came from. Until the Waters CDS integration lands this is `ManualEntry`
        from the template's `areaSource`, but recording it now means the
        provenance of historical results is never ambiguous afterwards.
        """
        sources: dict[str, str] = {}
        for group_key, field_key in definition.area_field_refs:
            rows = group_values.get(group_key) or []
            if not any(
                (row or {}).get(field_key) not in (None, "") for row in rows
            ):
                continue
            group = definition.group(group_key)
            field_def = group.field(field_key) if group else None
            sources[f"{group_key}.{field_key}"] = (
                field_def.area_source if field_def else "ManualEntry"
            )
        return sources

    @staticmethod
    def _diff(
        worksheet: TestWorksheet,
        new_context: dict[str, Any],
        new_groups: dict[str, list[dict[str, Any]]],
    ) -> dict[str, dict[str, Any]]:
        """
        Old/new pairs for only the fields that actually changed.

        Logging the whole payload on every keystroke-driven save would make the
        audit trail unreadable, which defeats its purpose.
        """
        old: dict[str, Any] = {}
        new: dict[str, Any] = {}

        prev_context = worksheet.context_values or {}
        for key in sorted(set(prev_context) | set(new_context)):
            if prev_context.get(key) != new_context.get(key):
                old[key] = prev_context.get(key)
                new[key] = new_context.get(key)

        prev_groups = worksheet.group_values or {}
        for group_key in sorted(set(prev_groups) | set(new_groups)):
            prev_rows = prev_groups.get(group_key) or []
            next_rows = new_groups.get(group_key) or []
            for index in range(max(len(prev_rows), len(next_rows))):
                prev_row = prev_rows[index] if index < len(prev_rows) else {}
                next_row = next_rows[index] if index < len(next_rows) else {}
                for field_key in sorted(set(prev_row) | set(next_row)):
                    if prev_row.get(field_key) != next_row.get(field_key):
                        ref = f"{group_key}[{index + 1}].{field_key}"
                        old[ref] = prev_row.get(field_key)
                        new[ref] = next_row.get(field_key)
        return {"old": old, "new": new}

    # ── Snapshot & formatting ────────────────────────────────────────

    def _snapshot(
        self,
        worksheet: TestWorksheet,
        template: TestTemplate,
        result: WorksheetResult,
        actor: User,
    ) -> dict:
        """
        The immutable record of how a reported number was arrived at: the
        template identity, the inputs, every computed value, and every criterion
        assessment. This is what makes a released result reproducible without
        the live template (Requirement 2.7).
        """
        return {
            "template": {
                "id": template.id,
                "code": template.code,
                "name": template.name,
                "archetype": template.archetype,
                "version": worksheet.template_version,
                "result_unit": template.result_unit,
            },
            "inputs": {
                "context": dict(worksheet.context_values or {}),
                "groups": {
                    k: [dict(r) for r in v] for k, v in (worksheet.group_values or {}).items()
                },
            },
            "computed": {
                "values": {k: self._plain(v) for k, v in result.values.items()},
                "rows": {
                    group_key: [
                        {k: self._plain(v) for k, v in row.items()} for row in rows
                    ]
                    for group_key, rows in result.rows.items()
                },
            },
            "criteria": [self._criterion_dict(c) for c in result.criteria],
            "reportable_result": self._plain(result.reportable_result),
            "confirmed_by": actor.username,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _criterion_dict(self, criterion: CriterionResult) -> dict:
        return {
            "key": criterion.key,
            "label": criterion.label,
            "observed": self._plain(criterion.observed),
            "operator": criterion.operator.value,
            "limit": list(criterion.limit),
            "limit_text": criterion.limit_text,
            "severity": criterion.severity.value,
            "passed": criterion.passed,
        }

    @staticmethod
    def _plain(value: Any) -> Any:
        """`EMPTY` is an engine sentinel; JSON gets `None`."""
        return None if value is EMPTY else value

    @staticmethod
    def _format_result(value: Any, unit: str | None) -> str:
        """
        Render the reportable result for `TRFTestLine.result`, which is free
        text shared with the non-templated entry path.

        The rounding a template declares on its result field has already been
        applied by the engine, so this must not re-round — it only trims the
        float repr artefacts (`108.83799999999999`) that would otherwise leak
        into a GxP record.
        """
        if isinstance(value, float):
            text = f"{value:.10f}".rstrip("0").rstrip(".")
            if text in ("", "-"):
                text = "0"
        else:
            text = str(value)
        return f"{text} {unit}".strip() if unit else text

    # ── Audit ────────────────────────────────────────────────────────

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
                table_name="test_worksheets",
                record_id=record_id,
                old_values=old_values,
                new_values=new_values,
            )
        )
