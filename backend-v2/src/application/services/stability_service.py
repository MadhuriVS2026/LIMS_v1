"""
Stability Management Application Service.

Orchestrates the full Stability workflow: protocol header + Loading Matrix
creation, the two-step (Formulation/Analytical) approval, time-point schedule
generation, pulling a time point (which reuses SampleService.log_sample()
directly rather than duplicating sample-creation logic), and Stability Report
generation/sign-off. Every state change writes an AuditLog entry, mirroring
MRNService's/SampleService's pattern.
"""
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import (
    NotFoundException,
    ValidationException,
)
from src.application.services.sample_service import SampleService
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.stability import (
    StabilityMatrixCell,
    StabilityProtocol,
    StabilityReport,
    StabilitySample,
    time_point_month_label,
)
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.stability_repository import IStabilityRepository
from src.domain.services.stability_code_generator import StabilityCodeGenerator
from src.domain.services.stability_report_number_generator import StabilityReportNumberGenerator

# Sample Manager statuses considered "results in progress" (neither freshly
# pulled nor finalized) for the purposes of assembling a report's results row.
_FINALIZED_SAMPLE_RESULT_STATUSES = {"Submitted", "Approved"}


class StabilityService:
    def __init__(
        self,
        stability_repo: IStabilityRepository,
        sample_service: SampleService,
        audit_repo: IAuditLogRepository,
    ) -> None:
        self._repo = stability_repo
        self._sample_service = sample_service
        self._audit_repo = audit_repo

    # ── Protocol ──────────────────────────────────────────────────────

    async def list_protocols(self) -> list[StabilityProtocol]:
        return await self._repo.list_protocols()

    async def get_protocol(self, protocol_id: int) -> StabilityProtocol:
        protocol = await self._repo.get_protocol_by_id(protocol_id)
        if protocol is None:
            raise NotFoundException("Stability protocol not found")
        return protocol

    async def create_protocol(self, header_fields: dict, actor: User) -> StabilityProtocol:
        """Requirement 2.1, 10.1: new Draft protocol with a generated protocol_code."""
        prefix = StabilityCodeGenerator.date_prefix()
        count_today = await self._repo.count_protocols()
        protocol_code = StabilityCodeGenerator.generate(count_today)

        protocol = StabilityProtocol(
            protocol_code=protocol_code,
            status="Draft",
            created_by=actor.username,
            modified_by=actor.username,
            **header_fields,
        )
        created = await self._repo.create_protocol(protocol)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_PROTOCOL_CREATED",
                table_name="stability_protocols", record_id=created.id,
                new_values={"protocol_code": created.protocol_code, "status": created.status},
            )
        )
        return created

    async def update_protocol_header(
        self, protocol_id: int, header_fields: dict, actor: User
    ) -> StabilityProtocol:
        """Header fields can only be edited while the protocol is Draft."""
        protocol = await self.get_protocol(protocol_id)
        if not protocol.can_edit_header():
            raise ValidationException(
                f"Protocol header can only be edited while Draft (current status: {protocol.status})"
            )
        old_values = {
            k: getattr(protocol, k) for k in header_fields if hasattr(protocol, k)
        }
        for key, value in header_fields.items():
            if hasattr(protocol, key):
                setattr(protocol, key, value)
        protocol.mark_modified(actor.username)
        updated = await self._repo.update_protocol(protocol)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_PROTOCOL_HEADER_UPDATED",
                table_name="stability_protocols", record_id=protocol.id,
                old_values=self._jsonable(old_values), new_values=self._jsonable(header_fields),
            )
        )
        return updated

    @staticmethod
    def _jsonable(values: dict) -> dict:
        """AuditLog old/new_values must be JSON-serializable; datetimes aren't."""
        result = {}
        for key, value in values.items():
            result[key] = value.isoformat() if isinstance(value, datetime) else value
        return result

    async def complete_protocol(self, protocol_id: int, actor: User) -> StabilityProtocol:
        """Manual close-out of an Active study."""
        protocol = await self.get_protocol(protocol_id)
        if not protocol.can_complete():
            raise ValidationException(
                f"Complete requires an Active protocol (current status: {protocol.status})"
            )
        old_status = protocol.status
        protocol.complete(actor.username, datetime.now(timezone.utc))
        updated = await self._repo.update_protocol(protocol)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_PROTOCOL_COMPLETED",
                table_name="stability_protocols", record_id=protocol.id,
                old_values={"status": old_status}, new_values={"status": protocol.status},
            )
        )
        return updated

    async def cancel_protocol(self, protocol_id: int, actor: User, reason: str | None) -> StabilityProtocol:
        """Cancels a protocol from any non-terminal state."""
        protocol = await self.get_protocol(protocol_id)
        if not protocol.can_cancel():
            raise ValidationException(
                f"Protocol is already {protocol.status} and cannot be cancelled"
            )
        old_status = protocol.status
        protocol.cancel(actor.username, datetime.now(timezone.utc))
        updated = await self._repo.update_protocol(protocol)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_PROTOCOL_CANCELLED",
                table_name="stability_protocols", record_id=protocol.id,
                old_values={"status": old_status}, new_values={"status": protocol.status},
                comments=reason,
            )
        )
        return updated

    # ── Loading Matrix ───────────────────────────────────────────────

    async def list_matrix_cells(self, protocol_id: int) -> list[StabilityMatrixCell]:
        return await self._repo.list_matrix_cells(protocol_id)

    async def set_matrix_cells(
        self, protocol_id: int, cells: list[dict], actor: User
    ) -> list[StabilityMatrixCell]:
        """
        Requirement 1.2, 1.3, 1.4, 1.5: upsert Loading Matrix cells by natural
        key (protocol_id, condition, time_point_days, is_reserve), only while
        the protocol is Draft. Derives time_point_month_label per cell.
        """
        protocol = await self.get_protocol(protocol_id)
        if not protocol.can_edit_matrix():
            raise ValidationException(
                f"Loading Matrix can only be edited while the protocol is Draft (current status: {protocol.status})"
            )

        saved: list[StabilityMatrixCell] = []
        for raw in cells:
            time_point_days = raw.get("time_point_days")
            is_reserve = bool(raw.get("is_reserve", False))
            cell = StabilityMatrixCell(
                id=raw.get("id", 0),
                protocol_id=protocol_id,
                condition=raw["condition"],
                is_reserve=is_reserve,
                time_point_days=time_point_days,
                time_point_month_label=time_point_month_label(time_point_days),
                is_scheduled=bool(raw.get("is_scheduled", False)),
                notes=raw.get("notes"),
                created_by=actor.username,
                modified_by=actor.username,
            )
            saved.append(await self._repo.upsert_matrix_cell(cell))

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_MATRIX_UPDATED",
                table_name="stability_matrix_cells", record_id=protocol_id,
                comments=f"Upserted {len(saved)} Loading Matrix cell(s) for protocol {protocol.protocol_code}",
            )
        )
        return saved

    # ── Two-step approval ────────────────────────────────────────────

    async def check_formulation(self, protocol_id: int, actor: User) -> StabilityProtocol:
        """Requirement 3.1, 3.3: Draft -> FormulationChecked (Supervisor e-sign)."""
        protocol = await self.get_protocol(protocol_id)
        if not protocol.can_check_formulation():
            raise ValidationException(
                f"Formulation Check requires Draft status (current status: {protocol.status})"
            )
        cells = await self._repo.list_matrix_cells(protocol_id)
        if not any(c.is_scheduled for c in cells):
            raise ValidationException(
                "At least one Loading Matrix cell must be scheduled before Formulation Check"
            )
        old_status = protocol.status
        protocol.check_formulation(actor.username, datetime.now(timezone.utc))
        updated = await self._repo.update_protocol(protocol)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_FORMULATION_CHECKED",
                table_name="stability_protocols", record_id=protocol.id,
                old_values={"status": old_status}, new_values={"status": protocol.status},
            )
        )
        return updated

    async def check_analytical(self, protocol_id: int, actor: User) -> StabilityProtocol:
        """Requirement 3.4, 3.5: FormulationChecked -> Active (Supervisor e-sign)."""
        protocol = await self.get_protocol(protocol_id)
        if not protocol.can_check_analytical():
            raise ValidationException(
                f"Analytical Check requires FormulationChecked status (current status: {protocol.status})"
            )
        old_status = protocol.status
        protocol.check_analytical(actor.username, datetime.now(timezone.utc))
        updated = await self._repo.update_protocol(protocol)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_ANALYTICAL_CHECKED",
                table_name="stability_protocols", record_id=protocol.id,
                old_values={"status": old_status}, new_values={"status": protocol.status},
            )
        )
        return updated

    # ── Schedule generation & pull ───────────────────────────────────

    async def generate_schedule(
        self, protocol_id: int, batch_numbers: list[str], actor: User
    ) -> list[StabilitySample]:
        """
        Requirement 4.1-4.5: for an Active protocol, create exactly one
        StabilitySample per (batch_number, matrix_cell) pair for every cell
        where is_scheduled and not is_reserve, skipping combinations that
        already exist (idempotent re-trigger).
        """
        protocol = await self.get_protocol(protocol_id)
        if not protocol.can_generate_schedule():
            raise ValidationException(
                f"Generate Schedule requires an Active protocol (current status: {protocol.status})"
            )

        cells = await self._repo.list_matrix_cells(protocol_id)
        eligible_cells = [c for c in cells if c.is_scheduled and not c.is_reserve]

        created: list[StabilitySample] = []
        for batch_number in batch_numbers:
            for cell in eligible_cells:
                already_exists = await self._repo.exists_sample_for_cell(
                    protocol_id, batch_number, cell.id
                )
                if already_exists:
                    continue

                scheduled_date = StabilitySample.compute_scheduled_date(
                    protocol.stability_initiation_date, cell.time_point_days
                )
                sample = StabilitySample(
                    protocol_id=protocol_id,
                    matrix_cell_id=cell.id,
                    condition=cell.condition,
                    time_point_days=cell.time_point_days,
                    time_point_months=round((cell.time_point_days or 0) / 30),
                    batch_number=batch_number,
                    scheduled_date=scheduled_date,
                    created_by=actor.username,
                    modified_by=actor.username,
                )
                created_sample = await self._repo.create_sample(sample)
                created.append(created_sample)

                await self._audit_repo.write(
                    AuditLog(
                        user_id=actor.id, username=actor.username, action="STABILITY_SAMPLE_SCHEDULED",
                        table_name="stability_samples", record_id=created_sample.id,
                        comments=(
                            f"Scheduled {batch_number} @ {cell.condition}/"
                            f"{cell.time_point_days}d for protocol {protocol.protocol_code}"
                        ),
                    )
                )
        return created

    async def list_samples(self, protocol_id: int) -> list[StabilitySample]:
        """Requirement 5.4: derived status recomputed against the linked Sample on every read."""
        return await self._repo.list_samples(protocol_id)

    async def create_reserve_sample(
        self, protocol_id: int, matrix_cell_id: int, batch_number: str, comments: str | None, actor: User
    ) -> StabilitySample:
        """
        Raises a Scheduled time-point entry from a Reserve matrix cell on
        demand (e.g. to pull a retain sample for an OOS retest), independent
        of the regular Generate Schedule flow which only ever schedules
        non-reserve cells. The resulting entry is pulled the same way as any
        other scheduled time point, via pull_sample().
        """
        protocol = await self.get_protocol(protocol_id)
        if not protocol.can_generate_schedule():
            raise ValidationException(
                f"Reserve pulls require an Active protocol (current status: {protocol.status})"
            )
        cell = await self._repo.get_matrix_cell_by_id(matrix_cell_id)
        if cell is None or cell.protocol_id != protocol_id:
            raise NotFoundException("Loading Matrix cell not found on this protocol")
        if not cell.is_reserve:
            raise ValidationException("This matrix cell is not a Reserve cell")

        if not batch_number or not batch_number.strip():
            raise ValidationException("Batch number is required")

        sample = StabilitySample(
            protocol_id=protocol_id,
            matrix_cell_id=cell.id,
            condition=cell.condition,
            time_point_days=None,
            time_point_months=0,
            batch_number=batch_number.strip(),
            scheduled_date=None,
            comments=comments,
            created_by=actor.username,
            modified_by=actor.username,
        )
        created = await self._repo.create_sample(sample)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_RESERVE_SAMPLE_CREATED",
                table_name="stability_samples", record_id=created.id,
                comments=f"Reserve pull raised for {batch_number} @ {cell.condition} on protocol {protocol.protocol_code}",
            )
        )
        return created

    async def get_sample(self, stability_sample_id: int) -> StabilitySample:
        sample = await self._repo.get_sample_by_id(stability_sample_id)
        if sample is None:
            raise NotFoundException("Stability time-point sample not found")
        return sample

    async def pull_sample(self, stability_sample_id: int, actor: User) -> StabilitySample:
        """
        Requirement 5.1, 5.2, 5.3: pull requires derived status Scheduled;
        calls SampleService.log_sample() exactly once, links the result, and
        sets pull_date only after Sample creation succeeds (no partial state
        on failure).
        """
        stability_sample = await self.get_sample(stability_sample_id)
        if not stability_sample.can_pull():
            raise ValidationException(
                f"Pull requires Scheduled status (current status: {stability_sample.status})"
            )
        protocol = await self.get_protocol(stability_sample.protocol_id)

        # May raise (e.g. NoActiveSpecificationError) — propagates untouched,
        # leaving the StabilitySample completely unchanged (Requirement 5.3).
        created_sample = await self._sample_service.log_sample(
            product_id=protocol.product_id,
            batch_number=stability_sample.batch_number,
            quantity_received=0.0,
            unit="",
            sample_type="Stability",
            priority="Normal",
            sap_inspection_lot=None,
            sap_material=None,
            sap_plant=None,
            sap_vendor=None,
            sap_vendor_batch=None,
            manufacturing_date=protocol.mfg_date,
            expiry_date=None,
            actor=actor,
        )

        when = datetime.now(timezone.utc)
        stability_sample.sample_id = created_sample.id
        stability_sample.pull_date = when
        stability_sample.modified_by = actor.username
        updated = await self._repo.update_sample(stability_sample)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_SAMPLE_PULLED",
                table_name="stability_samples", record_id=stability_sample.id,
                new_values={"sample_id": created_sample.id, "pull_date": when.isoformat()},
            )
        )
        return updated

    # ── Stability Report ─────────────────────────────────────────────

    async def generate_report(self, protocol_id: int, actor: User) -> StabilityReport:
        """
        Requirement 6.1-6.4: assemble results_data from Completed time points
        only. If no Prepared/Approved report exists, overwrite the latest
        Draft (or create one); otherwise always create a new Draft, leaving
        the signed report untouched (Requirement 6.3).
        """
        protocol = await self.get_protocol(protocol_id)
        samples = await self._repo.list_samples(protocol_id)
        completed_samples = [s for s in samples if s.status == "Completed"]

        results_data = await self._assemble_results_data(completed_samples)

        when = datetime.now(timezone.utc)
        header_fields = dict(
            protocol_id=protocol_id,
            product_name=protocol.label_claim,
            composition_label=protocol.label_claim,
            manufactured_at=protocol.api_source,
            stability_study_type=protocol.study_type,
            batch_no=protocol.batch_number,
            stability_condition=protocol.condition,
            batch_size=protocol.batch_size,
            date_of_commencement=protocol.stability_initiation_date,
            manufacturing_date=protocol.mfg_date,
            stability_protocol_no=protocol.protocol_code,
            api_source=protocol.api_source,
            api_batch_number=protocol.api_batch_no,
            packing=protocol.primary_pack,
            results_data=results_data,
            generated_by=actor.username,
            generated_at=when,
            modified_by=actor.username,
        )

        signed_report = await self._repo.get_latest_signed_report(protocol_id)
        if signed_report is not None:
            prefix = StabilityReportNumberGenerator.date_prefix()
            count_today = await self._repo.count_reports()
            report = StabilityReport(
                report_number=StabilityReportNumberGenerator.generate(count_today),
                status="Draft",
                created_by=actor.username,
                **header_fields,
            )
            saved = await self._repo.create_report(report)
        else:
            draft_report = await self._repo.get_latest_draft_report(protocol_id)
            if draft_report is not None:
                for key, value in header_fields.items():
                    setattr(draft_report, key, value)
                saved = await self._repo.update_report(draft_report)
            else:
                prefix = StabilityReportNumberGenerator.date_prefix()
                count_today = await self._repo.count_reports()
                report = StabilityReport(
                    report_number=StabilityReportNumberGenerator.generate(count_today),
                    status="Draft",
                    created_by=actor.username,
                    **header_fields,
                )
                saved = await self._repo.create_report(report)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_REPORT_GENERATED",
                table_name="stability_reports", record_id=saved.id,
                comments=f"Generated report {saved.report_number} for protocol {protocol.protocol_code}",
            )
        )
        return saved

    async def _assemble_results_data(self, completed_samples: list[StabilitySample]) -> list[dict]:
        """
        Requirement 6.1: one row per test, one column per Completed time
        point, sourced from each pulled time point's linked Sample results.
        """
        # Group by test, collecting each time point's result under a label.
        rows: dict[int, dict] = {}
        for stability_sample in completed_samples:
            if not stability_sample.sample_id:
                continue
            sample = await self._sample_service.get_sample(stability_sample.sample_id)
            label = (
                stability_sample.time_point_days is not None
                and f"{stability_sample.time_point_days} Days"
                or "Initial"
            )
            for result in sample.results:
                row = rows.setdefault(
                    result.test_id,
                    {
                        "test_id": result.test_id,
                        "test_name": result.test_name or "",
                        "specification": (
                            f"{result.min_limit}-{result.max_limit}"
                            if result.min_limit is not None or result.max_limit is not None
                            else (result.expected_result or "")
                        ),
                        "results": {},
                    },
                )
                row["results"][label] = (
                    result.result_value if result.result_value is not None else result.result_text
                )
        return list(rows.values())

    async def get_report(self, report_id: int) -> StabilityReport:
        report = await self._repo.get_report_by_id(report_id)
        if report is None:
            raise NotFoundException("Stability report not found")
        return report

    async def list_reports(self, protocol_id: int) -> list[StabilityReport]:
        return await self._repo.list_reports(protocol_id)

    async def set_report_signature_names(
        self, report_id: int, checked_by_name: str | None, reviewed_by_name: str | None, actor: User
    ) -> StabilityReport:
        """
        Requirement 6 / real Report Format's 4-signature block: 'Checked By'
        and 'Reviewed By' are free-text, print-only names (unlike Prepared/
        Approved, which are system-enforced e-sign gates) — only settable
        while the report is still Draft.
        """
        report = await self.get_report(report_id)
        if report.is_signed():
            raise ValidationException("Cannot edit signature names on a Prepared/Approved report")
        report.checked_by_name = checked_by_name
        report.reviewed_by_name = reviewed_by_name
        report.mark_modified(actor.username)
        updated = await self._repo.update_report(report)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_REPORT_SIGNATURE_NAMES_SET",
                table_name="stability_reports", record_id=report.id,
                new_values={"checked_by_name": checked_by_name, "reviewed_by_name": reviewed_by_name},
            )
        )
        return updated

    async def prepare_report(self, report_id: int, actor: User) -> StabilityReport:
        """Requirement 7.1, 7.2: Draft -> Prepared (Analyst e-sign)."""
        report = await self.get_report(report_id)
        if not report.can_prepare():
            raise ValidationException(f"Prepare requires Draft status (current status: {report.status})")
        old_status = report.status
        report.prepare(actor.username, datetime.now(timezone.utc))
        updated = await self._repo.update_report(report)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_REPORT_PREPARED",
                table_name="stability_reports", record_id=report.id,
                old_values={"status": old_status}, new_values={"status": report.status},
            )
        )
        return updated

    async def approve_report(self, report_id: int, actor: User) -> StabilityReport:
        """Requirement 7.3, 7.4: Prepared -> Approved (QA e-sign)."""
        report = await self.get_report(report_id)
        if not report.can_approve():
            raise ValidationException(f"Approve requires Prepared status (current status: {report.status})")
        old_status = report.status
        report.approve(actor.username, datetime.now(timezone.utc))
        updated = await self._repo.update_report(report)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="STABILITY_REPORT_APPROVED",
                table_name="stability_reports", record_id=report.id,
                old_values={"status": old_status}, new_values={"status": report.status},
            )
        )
        return updated
