"""
Sample Application Service.
Orchestrates the full Sample Manager workflow:
Login -> Receive -> Submit Results (OOS detection) -> Review -> Release (COA).
"""
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import (
    NotFoundException,
    ValidationException,
)
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.oos_investigation import OOSInvestigation
from src.domain.entities.sample import Sample, SampleResult
from src.domain.entities.user import User
from src.domain.exceptions.domain_exceptions import NoActiveSpecificationError
from src.domain.repositories.audit_repository import IAuditLogRepository, ISAPReceivedLotRepository
from src.domain.repositories.oos_repository import IOOSRepository
from src.domain.repositories.product_repository import IProductRepository
from src.domain.repositories.sample_repository import ISampleRepository
from src.domain.repositories.specification_repository import ISpecificationRepository
from src.domain.repositories.test_repository import ITestRepository
from src.domain.services.sample_code_generator import SampleCodeGenerator


class SampleService:
    """Coordinates the Sample lifecycle across repositories."""

    def __init__(
        self,
        sample_repo: ISampleRepository,
        spec_repo: ISpecificationRepository,
        product_repo: IProductRepository,
        test_repo: ITestRepository,
        oos_repo: IOOSRepository,
        audit_repo: IAuditLogRepository,
        received_lot_repo: ISAPReceivedLotRepository | None = None,
    ) -> None:
        self._sample_repo = sample_repo
        self._spec_repo = spec_repo
        self._product_repo = product_repo
        self._test_repo = test_repo
        self._oos_repo = oos_repo
        self._audit_repo = audit_repo
        self._received_lot_repo = received_lot_repo

    async def list_samples(self, status: str | None = None) -> list[Sample]:
        return await self._sample_repo.list_all(status)

    async def get_sample(self, sample_id: int) -> Sample:
        sample = await self._sample_repo.get_by_id(sample_id)
        if sample is None:
            raise NotFoundException("Sample not found")
        return sample

    async def log_sample(
        self,
        product_id: int,
        batch_number: str,
        quantity_received: float,
        unit: str,
        sample_type: str | None,
        priority: str,
        sap_inspection_lot: str | None,
        sap_material: str | None,
        sap_plant: str | None,
        sap_vendor: str | None,
        sap_vendor_batch: str | None,
        manufacturing_date: datetime | None,
        expiry_date: datetime | None,
        actor: User,
    ) -> Sample:
        """
        Sample Login Registration.
        Requires an Active Specification for the Product; auto-generates the
        A.R. Number (SMP-YYYYMMDD-XXXX) and seeds pending SampleResults from
        the specification's test limits.
        """
        spec = await self._spec_repo.get_active_for_product(product_id)
        if spec is None:
            raise NoActiveSpecificationError(
                "No active specification found for this product. Please approve a specification first."
            )

        if sap_inspection_lot and self._received_lot_repo:
            existing_lot = await self._received_lot_repo.get_by_inspection_lot(sap_inspection_lot)
            if existing_lot and existing_lot.consumed_by_sample_id:
                existing_sample = await self._sample_repo.get_by_id(existing_lot.consumed_by_sample_id)
                sample_ref = existing_sample.sample_code if existing_sample else f"#{existing_lot.consumed_by_sample_id}"
                raise ValidationException(
                    f"SAP inspection lot {sap_inspection_lot} has already been used to log sample "
                    f"{sample_ref}. Each inspection lot can only be sampled once."
                )

        now = datetime.now(timezone.utc)
        prefix = SampleCodeGenerator.date_prefix(now)
        count_today = await self._sample_repo.count_by_code_prefix(prefix)
        sample_code = SampleCodeGenerator.generate(count_today, now)

        results = [
            SampleResult(
                test_id=st.test_id,
                min_limit=st.min_limit,
                max_limit=st.max_limit,
                expected_result=st.expected_result,
                status="Pending",
                is_oos=False,
            )
            for st in spec.tests
        ]

        sample = Sample(
            sample_code=sample_code,
            product_id=product_id,
            batch_number=batch_number,
            quantity_received=quantity_received,
            unit=unit,
            sample_type=sample_type,
            priority=priority or "Normal",
            status="Logged",
            sap_inspection_lot=sap_inspection_lot,
            sap_material=sap_material,
            sap_plant=sap_plant,
            sap_vendor=sap_vendor,
            sap_vendor_batch=sap_vendor_batch,
            manufacturing_date=manufacturing_date,
            expiry_date=expiry_date,
            logged_by=actor.username,
            logged_at=now,
            results=results,
            created_by=actor.username,
            modified_by=actor.username,
        )
        created = await self._sample_repo.create(sample)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="CREATE",
                table_name="samples", record_id=created.id,
                new_values={"sample_code": created.sample_code, "status": created.status},
            )
        )

        if sap_inspection_lot and self._received_lot_repo:
            await self._received_lot_repo.mark_consumed(sap_inspection_lot, created.id)
            await self._audit_repo.write(
                AuditLog(
                    user_id=actor.id, username=actor.username, action="SAP_LOT_CONSUMED",
                    table_name="sap_received_lots", record_id=created.id,
                    comments=f"SAP inspection lot {sap_inspection_lot} consumed by sample {created.sample_code}",
                )
            )

        return created

    async def receive_sample(self, sample_id: int, actor: User) -> Sample:
        sample = await self.get_sample(sample_id)
        old_status = sample.status
        sample.receive(actor.username, datetime.now(timezone.utc))
        updated = await self._sample_repo.update(sample)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="RECEIVE",
                table_name="samples", record_id=updated.id,
                old_values={"status": old_status}, new_values={"status": updated.status},
            )
        )
        return updated

    async def update_sample(
        self,
        sample_id: int,
        actor: User,
        *,
        batch_number: str | None = None,
        quantity_received: float | None = None,
        unit: str | None = None,
        sample_type: str | None = None,
        priority: str | None = None,
        sap_inspection_lot: str | None = None,
        sap_material: str | None = None,
        sap_plant: str | None = None,
        sap_vendor: str | None = None,
        sap_vendor_batch: str | None = None,
        manufacturing_date: datetime | None = None,
        expiry_date: datetime | None = None,
    ) -> Sample:
        """Edit sample registration details. Only allowed before testing begins
        (Logged/Received)."""
        sample = await self.get_sample(sample_id)
        if not sample.can_edit():
            raise ValidationException(
                f"Sample cannot be edited in status '{sample.status}'. "
                f"Editing is only permitted while Logged or Received."
            )

        before = {
            "batch_number": sample.batch_number,
            "quantity_received": sample.quantity_received, "unit": sample.unit,
            "sample_type": sample.sample_type, "priority": sample.priority,
        }
        sample.update_details(
            actor.username,
            batch_number=batch_number, quantity_received=quantity_received, unit=unit,
            sample_type=sample_type, priority=priority,
            sap_inspection_lot=sap_inspection_lot, sap_material=sap_material,
            sap_plant=sap_plant, sap_vendor=sap_vendor, sap_vendor_batch=sap_vendor_batch,
            manufacturing_date=manufacturing_date, expiry_date=expiry_date,
        )
        updated = await self._sample_repo.update(sample)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="UPDATE",
                table_name="samples", record_id=updated.id,
                old_values=before,
                new_values={
                    "batch_number": updated.batch_number,
                    "quantity_received": updated.quantity_received, "unit": updated.unit,
                    "sample_type": updated.sample_type, "priority": updated.priority,
                },
                comments="Sample registration details edited.",
            )
        )
        return updated

    async def soft_delete_sample(
        self, sample_id: int, actor: User, comments: str | None
    ) -> Sample:
        """Soft-delete (deactivate) a sample. Blocked once released
        (Approved/Rejected). Writes an audit entry flagged for GL/TL/Supervisor/
        Admin review."""
        sample = await self.get_sample(sample_id)
        if sample.status == "Inactive":
            raise ValidationException("Sample is already deactivated")
        if not sample.can_soft_delete():
            raise ValidationException(
                f"Sample cannot be deleted in status '{sample.status}'. "
                f"A released sample owns an immutable certificate and must be retained."
            )

        old_status = sample.status
        sample.deactivate(actor.username)
        updated = await self._sample_repo.update(sample)

        note = (
            f"[REVIEW: GL/TL/Supervisor/Admin] Sample '{updated.sample_code}' "
            f"deactivated by {actor.username} ({actor.role})."
        )
        if comments:
            note += f" Reason: {comments}"
        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="DELETE",
                table_name="samples", record_id=updated.id,
                old_values={"status": old_status}, new_values={"status": updated.status},
                comments=note,
            )
        )
        return updated

    async def submit_result(
        self,
        result_id: int,
        result_value: float | None,
        result_text: str | None,
        actor: User,
        comments: str | None,
    ) -> SampleResult:
        """
        Analyst submits a test result (E-Signed).
        Domain rule evaluates OOS; if OOS, auto-creates an OOSInvestigation and
        moves the parent Sample to 'OOS Investigation'. Otherwise, once all
        results are finalized, the Sample moves to 'Under Review'.
        """
        result = await self._sample_repo.get_result_by_id(result_id)
        if result is None:
            raise NotFoundException("Sample result record not found")

        result.result_value = result_value
        result.result_text = result_text
        result.status = "Submitted"
        result.analyst_id = actor.id
        result.submitted_at = datetime.now(timezone.utc)
        result.is_oos = result.evaluate_oos()

        updated_result = await self._sample_repo.update_result(result)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="SUBMIT_RESULT",
                table_name="sample_results", record_id=updated_result.id,
                new_values={"result_value": result_value, "result_text": result_text, "is_oos": updated_result.is_oos},
                comments=f"E-Signed by {actor.username}. {comments or ''}",
            )
        )

        sample = await self.get_sample(result.sample_id)

        if updated_result.is_oos:
            sample.status = "OOS Investigation"
            await self._sample_repo.update(sample)

            existing_oos = await self._oos_repo.find_existing(sample.id, result.test_id)
            if existing_oos is None:
                oos = OOSInvestigation(
                    sample_id=sample.id,
                    test_id=result.test_id,
                    phase1_comments=(
                        f"Auto-generated OOS report: test value "
                        f"'{result_value if result_value is not None else result_text}' out of specification."
                    ),
                    status="Open",
                    created_by="System",
                    modified_by="System",
                )
                created_oos = await self._oos_repo.create(oos)

                updated_result.oos_investigation_id = created_oos.id
                await self._sample_repo.update_result(updated_result)

                await self._audit_repo.write(
                    AuditLog(
                        user_id=0, username="System", action="CREATE",
                        table_name="oos_investigations", record_id=created_oos.id,
                        comments="Auto-triggered OOS investigation",
                    )
                )
        else:
            fresh_sample = await self.get_sample(sample.id)
            fresh_sample.refresh_status_after_result_submission()
            await self._sample_repo.update(fresh_sample)

        return updated_result

    async def review_result(self, result_id: int, actor: User, comments: str | None) -> SampleResult:
        """Supervisor reviews & approves a submitted result (E-Signed)."""
        result = await self._sample_repo.get_result_by_id(result_id)
        if result is None:
            raise NotFoundException("Sample result record not found")

        result.status = "Approved"
        result.supervisor_id = actor.id
        result.reviewed_at = datetime.now(timezone.utc)
        updated = await self._sample_repo.update_result(result)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="REVIEW_RESULT",
                table_name="sample_results", record_id=updated.id, comments=comments,
            )
        )
        return updated

    async def release_sample(
        self, sample_id: int, verdict: str, actor: User, comments: str | None
    ) -> Sample:
        """
        QA releases the batch (Approved/Rejected) with E-Signature.
        Generates an immutable COA data snapshot of all results at release time.
        """
        if verdict not in ("Approved", "Rejected"):
            raise ValidationException("Verdict must be Approved or Rejected")

        sample = await self.get_sample(sample_id)
        product = await self._product_repo.get_by_id(sample.product_id)

        snapshot = {
            "sample_code": sample.sample_code,
            "product_code": product.code if product else None,
            "product_name": product.name if product else None,
            "batch_number": sample.batch_number,
            "quantity_received": sample.quantity_received,
            "unit": sample.unit,
            "released_by": actor.username,
            "released_at": datetime.now(timezone.utc).isoformat(),
            "verdict": verdict,
            "comments": comments,
            "results": [
                {
                    "test_id": r.test_id,
                    "min_limit": r.min_limit,
                    "max_limit": r.max_limit,
                    "expected_result": r.expected_result,
                    "result_value": r.result_value,
                    "result_text": r.result_text,
                    "is_oos": r.is_oos,
                }
                for r in sample.results
            ],
        }

        sample.release(verdict, actor.username, datetime.now(timezone.utc), comments, snapshot)
        updated = await self._sample_repo.update(sample)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="RELEASE_COA",
                table_name="samples", record_id=updated.id,
                new_values={"status": updated.status},
                comments=f"Verdict: {verdict}. {comments or ''}",
            )
        )
        return updated
