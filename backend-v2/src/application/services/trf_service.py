"""
TRF — Test Request Form Application Service.

Orchestrates the full request/approval/testing/release lifecycle: creation
and test-line management, submission, the FDGL and ADGL gates, Analyst
result entry, ADGL review/correction/release, Refer-Back resubmission, and
ATR retrieval. E-signature verification for the four gated actions (FDGL
Approve, ADGL Accept, Submit Results, Release) is performed by the caller
(endpoint layer) via AuthService.verify_esignature before these methods run,
mirroring MRNService/StabilityService. Every state change writes an
AuditLog entry.
"""
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import (
    NotFoundException,
    ValidationException,
)
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.trf import TestRequestForm, TRFTestLine
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.trf_repository import ITRFRepository
from src.domain.services.ar_number_generator import ARNumberGenerator
from src.domain.services.trf_number_generator import TRFNumberGenerator


class TRFService:
    def __init__(
        self,
        trf_repo: ITRFRepository,
        audit_repo: IAuditLogRepository,
    ) -> None:
        self._repo = trf_repo
        self._audit_repo = audit_repo

    # ── List / Get ───────────────────────────────────────────────────

    async def list_trfs(self, actor: User) -> list[TestRequestForm]:
        """The TRF list is role-consistent: every authenticated user sees the
        full list, so two users of the same role never see different lists. The
        "Initiated By" column still shows ownership, and the per-action guards
        (accept/submit/edit/approve) continue to enforce who may act on each TRF.
        `actor` is accepted for interface stability and future scoping."""
        _ = actor
        return await self._repo.list_all()

    async def get_trf(self, trf_id: int) -> TestRequestForm:
        trf = await self._repo.get_by_id(trf_id)
        if trf is None:
            raise NotFoundException("Test Request Form not found")
        return trf

    async def get_test_line(self, line_id: int) -> TRFTestLine:
        """Used by the API layer to determine which status a PUT .../result call falls under
        (Analyst result entry vs. ADGL correction) before delegating to the matching method."""
        line = await self._repo.get_test_line_by_id(line_id)
        if line is None:
            raise NotFoundException("Test line not found")
        return line

    # ── Creation & test-line management ─────────────────────────────

    async def create_trf(self, header_fields: dict, actor: User) -> TestRequestForm:
        """Requirement 1.1, 11.1: new Draft TRF with a generated trf_number."""
        prefix = TRFNumberGenerator.date_prefix()
        count_today = await self._repo.count_by_number_prefix(prefix)
        trf_number = TRFNumberGenerator.generate(count_today)

        trf = TestRequestForm(
            trf_number=trf_number,
            status="Draft",
            created_by=actor.username,
            modified_by=actor.username,
            **header_fields,
        )
        saved = await self._repo.create(trf)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="TRF_CREATED",
                table_name="test_request_forms", record_id=saved.id,
                new_values={"trf_number": saved.trf_number, "status": saved.status},
            )
        )
        return saved

    def _assert_can_mutate_lines(self, trf: TestRequestForm, actor: User) -> None:
        """Requirement 1.4: Draft/ReferredBack (Initiator or Admin), or PendingFDGLApproval (FDGL/Admin)."""
        actor_is_fdgl = actor.has_role("Supervisor", "Admin")
        if not trf.can_mutate_lines(actor_is_fdgl=actor_is_fdgl):
            raise ValidationException(
                f"Test lines can only be mutated while Draft/ReferredBack, or PendingFDGLApproval "
                f"for FDGL (current status: {trf.status})"
            )
        #  Any Analyst/Admin (per the endpoint role guard) may modify the TRF —
        #  editing is not restricted to the initiating user. The audit trail
        #  records who made each change.

    async def add_test_line(
        self, trf_id: int, test_id: int, specification: str | None,
        raw_data_reference: str | None, remark: str | None, actor: User,
    ) -> TRFTestLine:
        """Requirement 1.2, 1.4, 9.1: validated test line addition."""
        trf = await self.get_trf(trf_id)
        self._assert_can_mutate_lines(trf, actor)

        line = TRFTestLine(
            trf_id=trf_id,
            line_no=len(trf.test_lines) + 1,
            test_id=test_id,
            specification=specification,
            raw_data_reference=raw_data_reference,
            remark=remark,
            created_by=actor.username,
            modified_by=actor.username,
        )
        saved = await self._repo.add_test_line(trf_id, line)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="TRF_TEST_LINE_ADDED",
                table_name="trf_test_lines", record_id=saved.id,
                new_values={"test_id": test_id, "specification": specification},
            )
        )
        return saved

    async def remove_test_line(self, trf_id: int, line_id: int, actor: User) -> None:
        """Requirement 1.3, 1.4: remove a test line without affecting the header or other lines."""
        trf = await self.get_trf(trf_id)
        self._assert_can_mutate_lines(trf, actor)

        line = await self._repo.get_test_line_by_id(line_id)
        if line is None or line.trf_id != trf_id:
            raise NotFoundException("Test line not found on this TRF")

        await self._repo.remove_test_line(trf_id, line_id)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="TRF_TEST_LINE_REMOVED",
                table_name="trf_test_lines", record_id=line_id,
                old_values={"test_id": line.test_id},
            )
        )

    # ── Submission ───────────────────────────────────────────────────

    async def submit_trf(self, trf_id: int, actor: User) -> TestRequestForm:
        """Requirement 2.1, 2.2, 2.3: Draft/ReferredBack -> PendingFDGLApproval, requires >= 1 test line."""
        trf = await self.get_trf(trf_id)
        #  Any Analyst/Admin may submit — not only the initiating user.
        if not trf.can_submit():
            raise ValidationException(
                "TRF must be in Draft or ReferredBack status with at least one test line to submit"
            )

        old_status = trf.status
        when = datetime.now(timezone.utc)
        trf.submit(actor.username, when)
        updated = await self._repo.update(trf)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="TRF_SUBMITTED",
                table_name="test_request_forms", record_id=trf.id,
                old_values={"status": old_status}, new_values={"status": trf.status},
            )
        )
        return updated

    # ── FDGL gate ────────────────────────────────────────────────────

    async def fdgl_approve(self, trf_id: int, actor: User) -> TestRequestForm:
        """Requirement 3.1, 3.2, 3.5: PendingFDGLApproval -> PendingADGLAcceptance. E-sign verified by caller."""
        return await self._apply_transition(
            trf_id, actor, "TRF_FDGL_APPROVED",
            lambda trf, when: trf.fdgl_approve(actor.username, when),
        )

    async def fdgl_refer_back(self, trf_id: int, actor: User, comments: str) -> TestRequestForm:
        return await self._apply_transition(
            trf_id, actor, "TRF_FDGL_REFERRED_BACK",
            lambda trf, when: trf.fdgl_refer_back(actor.username, comments, when),
        )

    async def fdgl_reject(self, trf_id: int, actor: User, comments: str) -> TestRequestForm:
        return await self._apply_transition(
            trf_id, actor, "TRF_FDGL_REJECTED",
            lambda trf, when: trf.fdgl_reject(actor.username, comments, when),
        )

    # ── ADGL acceptance gate ─────────────────────────────────────────

    async def adgl_accept(self, trf_id: int, actor: User) -> TestRequestForm:
        """Requirement 4.1, 4.2, 4.4, 4.6: PendingADGLAcceptance -> PendingAnalystAcceptance,
        assigns ar_number exactly once. E-sign verified by caller."""
        trf = await self.get_trf(trf_id)
        if not trf.can_adgl_accept_act():
            raise ValidationException(
                f"ADGL acceptance requires PendingADGLAcceptance status (current status: {trf.status})"
            )

        prefix = ARNumberGenerator.date_prefix()
        count_today = await self._repo.count_ar_by_number_prefix(prefix)
        ar_number = ARNumberGenerator.generate(count_today)

        old_status = trf.status
        when = datetime.now(timezone.utc)
        trf.adgl_accept(actor.username, ar_number, when)
        updated = await self._repo.update(trf)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="TRF_ADGL_ACCEPTED",
                table_name="test_request_forms", record_id=trf.id,
                old_values={"status": old_status}, new_values={"status": trf.status, "ar_number": ar_number},
            )
        )
        return updated

    async def adgl_refer_back(self, trf_id: int, actor: User, comments: str) -> TestRequestForm:
        return await self._apply_transition(
            trf_id, actor, "TRF_ADGL_REFERRED_BACK",
            lambda trf, when: trf.adgl_refer_back(actor.username, comments, when),
        )

    async def adgl_reject(self, trf_id: int, actor: User, comments: str) -> TestRequestForm:
        return await self._apply_transition(
            trf_id, actor, "TRF_ADGL_REJECTED",
            lambda trf, when: trf.adgl_reject(actor.username, comments, when),
        )

    # ── Analyst gate ─────────────────────────────────────────────────

    async def analyst_accept(self, trf_id: int, actor: User) -> TestRequestForm:
        """Requirement 5.1: PendingAnalystAcceptance -> InProgress. Not e-signed."""
        return await self._apply_transition(
            trf_id, actor, "TRF_ANALYST_ACCEPTED",
            lambda trf, when: trf.analyst_accept(actor.username, when),
        )

    async def analyst_refer_back(self, trf_id: int, actor: User, comments: str) -> TestRequestForm:
        return await self._apply_transition(
            trf_id, actor, "TRF_ANALYST_REFERRED_BACK",
            lambda trf, when: trf.analyst_refer_back(actor.username, comments, when),
        )

    async def analyst_reject(self, trf_id: int, actor: User, comments: str) -> TestRequestForm:
        return await self._apply_transition(
            trf_id, actor, "TRF_ANALYST_REJECTED",
            lambda trf, when: trf.analyst_reject(actor.username, comments, when),
        )

    # ── Result entry ─────────────────────────────────────────────────

    async def submit_test_result(
        self, line_id: int, result: str | None, remark: str | None, actor: User
    ) -> TRFTestLine:
        """Requirement 5.3: analyst sets/updates a line's result while the parent TRF is InProgress."""
        line = await self._repo.get_test_line_by_id(line_id)
        if line is None:
            raise NotFoundException("Test line not found")
        trf = await self.get_trf(line.trf_id)
        if not trf.can_enter_results():
            raise ValidationException(
                f"Results can only be entered while the TRF is InProgress (current status: {trf.status})"
            )

        line.set_result(result, remark)
        updated = await self._repo.update_test_line(line)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="TRF_TEST_RESULT_SUBMITTED",
                table_name="trf_test_lines", record_id=line.id,
                new_values={"result": result, "remark": remark},
            )
        )
        return updated

    async def submit_results(self, trf_id: int, actor: User) -> TestRequestForm:
        """Requirement 5.4, 5.5: InProgress -> PendingADGLRelease, requires every line resulted.
        E-sign verified by caller."""
        trf = await self.get_trf(trf_id)
        if not trf.can_enter_results():
            raise ValidationException(f"Submit Results requires InProgress status (current status: {trf.status})")
        if not trf.all_lines_resulted():
            unresulted = [line.line_no for line in trf.test_lines if not line.has_result()]
            raise ValidationException(f"Every test line must have a result before submitting (missing line(s): {unresulted})")

        old_status = trf.status
        when = datetime.now(timezone.utc)
        trf.submit_results(actor.username, when)
        updated = await self._repo.update(trf)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="TRF_RESULTS_SUBMITTED",
                table_name="test_request_forms", record_id=trf.id,
                old_values={"status": old_status}, new_values={"status": trf.status},
            )
        )
        return updated

    # ── ADGL review, correction, release ──────────────────────────────

    async def correct_test_result(
        self, line_id: int, result: str | None, remark: str | None, actor: User
    ) -> TRFTestLine:
        """Requirement 6.1, 6.2: ADGL-only correction while PendingADGLRelease."""
        line = await self._repo.get_test_line_by_id(line_id)
        if line is None:
            raise NotFoundException("Test line not found")
        trf = await self.get_trf(line.trf_id)
        if not trf.can_correct_result():
            raise ValidationException(
                f"Result correction requires PendingADGLRelease status (current status: {trf.status})"
            )

        old_result = line.result
        line.set_result(result, remark)
        updated = await self._repo.update_test_line(line)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="TRF_TEST_RESULT_CORRECTED",
                table_name="trf_test_lines", record_id=line.id,
                old_values={"result": old_result}, new_values={"result": result, "remark": remark},
            )
        )
        return updated

    async def release_results(self, trf_id: int, actor: User) -> TestRequestForm:
        """Requirement 6.3, 6.5, 8.4: PendingADGLRelease -> Released, captures immutable ATR
        snapshot. E-sign verified by caller."""
        trf = await self.get_trf(trf_id)
        if not trf.can_release():
            raise ValidationException(f"Release requires PendingADGLRelease status (current status: {trf.status})")

        when = datetime.now(timezone.utc)
        atr_snapshot = self._build_atr_snapshot(trf, actor.username, when)
        trf.release(actor.username, when, atr_snapshot)
        updated = await self._repo.update(trf)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="TRF_RELEASED",
                table_name="test_request_forms", record_id=trf.id,
                new_values={"status": trf.status, "ar_number": trf.ar_number},
            )
        )
        return updated

    @staticmethod
    def _build_atr_snapshot(trf: TestRequestForm, releasing_actor: str, released_at: datetime) -> dict:
        """Requirement 8.1: immutable snapshot of header, test lines, and full signature chain."""
        return {
            "trf_number": trf.trf_number,
            "ar_number": trf.ar_number,
            "product_id": trf.product_id,
            "batch_number": trf.batch_number,
            "label_claim": trf.label_claim,
            "stage_of_sample": trf.stage_of_sample,
            "storage_condition": trf.storage_condition,
            "storage_period": trf.storage_period,
            "pack_details": trf.pack_details,
            "manufactured_by": trf.manufactured_by,
            "mfg_date": trf.mfg_date.isoformat() if trf.mfg_date else None,
            "expiry_or_retest_date": trf.expiry_or_retest_date.isoformat() if trf.expiry_or_retest_date else None,
            "remark": trf.remark,
            "test_lines": [
                {
                    "line_no": line.line_no,
                    "test_id": line.test_id,
                    "test_code": line.test_code,
                    "test_name": line.test_name,
                    "specification": line.specification,
                    "raw_data_reference": line.raw_data_reference,
                    "result": line.result,
                    "remark": line.remark,
                }
                for line in trf.test_lines
            ],
            "signatures": {
                "initiated_by": trf.initiated_by,
                "initiated_at": trf.initiated_at.isoformat() if trf.initiated_at else None,
                "approved_by": trf.fdgl_approved_by,
                "approved_at": trf.fdgl_approved_at.isoformat() if trf.fdgl_approved_at else None,
                "accepted_by": trf.adgl_accepted_by,
                "accepted_at": trf.adgl_accepted_at.isoformat() if trf.adgl_accepted_at else None,
                "analysed_by": trf.analyst_accepted_by,
                "analysed_at": trf.results_submitted_at.isoformat() if trf.results_submitted_at else None,
                "released_by": releasing_actor,
                "released_at": released_at.isoformat(),
            },
        }

    # ── Refer-Back resubmission ───────────────────────────────────────

    async def resubmit_trf(self, trf_id: int, actor: User) -> TestRequestForm:
        """Requirement 7.1, 7.2, 7.3: ReferredBack -> PendingFDGLApproval, always re-enters at FDGL."""
        trf = await self.get_trf(trf_id)
        #  Any Analyst/Admin may resubmit — not only the initiating user.
        if not trf.can_resubmit():
            raise ValidationException(f"Resubmit requires ReferredBack status (current status: {trf.status})")

        when = datetime.now(timezone.utc)
        trf.resubmit(actor.username, when)
        updated = await self._repo.update(trf)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="TRF_RESUBMITTED",
                table_name="test_request_forms", record_id=trf.id,
                new_values={"status": trf.status},
            )
        )
        return updated

    # ── ATR ────────────────────────────────────────────────────────────

    async def get_atr(self, trf_id: int) -> dict:
        """Requirement 8.1, 8.2: available only once Released."""
        trf = await self.get_trf(trf_id)
        if not trf.can_view_atr() or trf.atr_snapshot is None:
            raise ValidationException(f"ATR is only available once the TRF is Released (current status: {trf.status})")
        return trf.atr_snapshot

    # ── Shared helper ────────────────────────────────────────────────

    async def _apply_transition(
        self, trf_id: int, actor: User, audit_action: str, transition_fn
    ) -> TestRequestForm:
        """
        Shared plumbing for the simple gate transitions (approve/refer-back/
        reject/accept) that don't need bespoke pre/post logic beyond
        recording old/new status and writing one AuditLog entry.
        """
        trf = await self.get_trf(trf_id)
        old_status = trf.status
        when = datetime.now(timezone.utc)
        try:
            transition_fn(trf, when)
        except ValueError as exc:
            raise ValidationException(str(exc)) from exc
        updated = await self._repo.update(trf)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action=audit_action,
                table_name="test_request_forms", record_id=trf.id,
                old_values={"status": old_status}, new_values={"status": trf.status},
                comments=trf.referred_back_comments if trf.status == "ReferredBack" else (
                    trf.rejected_comments if trf.status == "Rejected" else None
                ),
            )
        )
        return updated
