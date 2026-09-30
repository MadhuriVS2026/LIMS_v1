"""
MRN — Material Requisition & Consumption Application Service.

Orchestrates the full lifecycle: pulling GRN-complete material lots from
SAP, raising/editing/submitting a Material Requisition, and the Supervisor's
approve-and-post action that posts consumption back to SAP per line item
(with independent per-line failure handling, idempotent retries, and derived
header/lot status). Every state change and SAP call writes an AuditLog and/or
SAPIntegrationLog entry, mirroring SAPIntegrationService's pattern.
"""
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.domain.entities.audit_log import AuditLog, SAPIntegrationLog
from src.domain.entities.mrn import (
    ConsumptionPosting,
    MaterialRequisition,
    MRNLineItem,
    MRNMaterialLot,
)
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import (
    IAuditLogRepository,
    ISAPIntegrationLogRepository,
)
from src.domain.repositories.mrn_repository import (
    IConsumptionPostingRepository,
    IMaterialRequisitionRepository,
    IMRNMaterialLotRepository,
)
from src.domain.services.mrn_number_generator import MRNNumberGenerator
from src.infrastructure.external.sap.sap_client import ISAPClient


class MRNService:
    def __init__(
        self,
        lot_repo: IMRNMaterialLotRepository,
        mrn_repo: IMaterialRequisitionRepository,
        posting_repo: IConsumptionPostingRepository,
        sap_client: ISAPClient,
        sap_log_repo: ISAPIntegrationLogRepository,
        audit_repo: IAuditLogRepository,
        mrn_sap_plant_code: str,
    ) -> None:
        self._lot_repo = lot_repo
        self._mrn_repo = mrn_repo
        self._posting_repo = posting_repo
        self._sap_client = sap_client
        self._sap_log_repo = sap_log_repo
        self._audit_repo = audit_repo
        self._plant_code = mrn_sap_plant_code

    # ── Material Queue ──────────────────────────────────────────────

    async def list_material_queue(self) -> list[MRNMaterialLot]:
        """Requirement 1.1: lots with available_quantity > 0, most-recently-pulled first."""
        return await self._lot_repo.list_available()

    async def pull_grn_materials(self, actor: User) -> dict:
        """
        Requirement 1.2-1.5: pull GRN-complete materials from SAP and upsert
        by natural key. On failure, leaves existing MRNMaterialLot rows
        untouched and still writes one SAPIntegrationLog + one AuditLog entry.
        """
        request_payload = {"plant": self._plant_code}
        try:
            raw_lots = await self._sap_client.read_grn_completed_materials(self._plant_code)
        except Exception as exc:  # noqa: BLE001 - SAP transport errors are opaque here
            await self._sap_log_repo.write(
                SAPIntegrationLog(
                    transaction_type="MRN_GRN_PULL",
                    direction="OUTBOUND",
                    request_payload=request_payload,
                    response_payload=None,
                    status="Failed",
                    error_message=str(exc),
                    created_by=actor.username,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await self._audit_repo.write(
                AuditLog(
                    user_id=actor.id,
                    username=actor.username,
                    action="MRN_GRN_PULL_FAILED",
                    table_name="mrn_material_lots",
                    comments=f"GRN pull failed: {exc}",
                )
            )
            raise ValidationException(f"SAP GRN material pull failed: {exc}") from exc

        pulled_at = datetime.now(timezone.utc)
        upserted: list[MRNMaterialLot] = []
        for raw in raw_lots:
            lot = MRNMaterialLot(
                grn_document_no=str(raw.get("grn_document_no") or ""),
                grn_item_no=str(raw.get("grn_item_no") or ""),
                material_code=raw.get("material_code") or "",
                material_description=raw.get("material_description"),
                batch_number=raw.get("batch_number"),
                plant=raw.get("plant") or self._plant_code,
                unit=raw.get("unit") or "",
                original_quantity=float(raw.get("quantity") or 0.0),
                grn_date=self._parse_date(raw.get("grn_date")),
                pulled_at=pulled_at,
                created_by=actor.username,
                modified_by=actor.username,
            )
            upserted.append(await self._lot_repo.upsert(lot))

        await self._sap_log_repo.write(
            SAPIntegrationLog(
                transaction_type="MRN_GRN_PULL",
                direction="OUTBOUND",
                request_payload=request_payload,
                response_payload={"count": len(upserted)},
                status="Success",
                created_by=actor.username,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="MRN_GRN_PULL",
                table_name="mrn_material_lots",
                comments=f"Pulled {len(upserted)} GRN-complete lot(s) from SAP",
            )
        )
        return {"pulled": len(upserted), "lots": upserted}

    @staticmethod
    def _parse_date(value) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return None

    # ── MRN creation & editing (Draft) ──────────────────────────────

    async def list_mrns(self, actor: User) -> list[MaterialRequisition]:
        """Role-consistent list: every authenticated user sees all MRNs, so two
        users of the same role never see different lists. The "Created By" column
        shows ownership, and the per-action guards still enforce who may edit or
        submit each MRN. `actor` is accepted for interface stability."""
        _ = actor
        return await self._mrn_repo.list_all()

    async def get_mrn(self, mrn_id: int) -> MaterialRequisition:
        mrn = await self._mrn_repo.get_by_id(mrn_id)
        if mrn is None:
            raise NotFoundException("Material Requisition not found")
        return mrn

    async def create_mrn(self, actor: User) -> MaterialRequisition:
        """Requirement 2.1, 2.8: new Draft MRN with a generated MRN number."""
        prefix = MRNNumberGenerator.date_prefix()
        count_today = await self._mrn_repo.count_by_number_prefix(prefix)
        mrn_number = MRNNumberGenerator.generate(count_today)

        mrn = MaterialRequisition(
            mrn_number=mrn_number,
            status="Draft",
            created_by=actor.username,
            modified_by=actor.username,
        )
        saved = await self._mrn_repo.create(mrn)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="MRN_CREATED",
                table_name="material_requisitions",
                record_id=saved.id,
                new_values={"mrn_number": saved.mrn_number, "status": saved.status},
            )
        )
        return saved

    def _assert_can_edit(self, mrn: MaterialRequisition, actor: User) -> None:
        """Requirement 2.7: only the creating user or an Admin may edit/submit a Draft MRN."""
        if mrn.created_by != actor.username and not actor.has_role("Admin"):
            raise ForbiddenException("Only the creating user or an Admin may modify this MRN")
        if not mrn.can_mutate_line_items():
            raise ValidationException("Line items can only be added or removed while the MRN is in Draft status")

    async def add_line_item(
        self, mrn_id: int, lot_id: int, quantity: float, project_code: str, actor: User
    ) -> MRNLineItem:
        """Requirement 2.2, 2.3, 2.4, 2.7, 4.3: validated line item addition."""
        mrn = await self.get_mrn(mrn_id)
        self._assert_can_edit(mrn, actor)

        if not project_code or not project_code.strip():
            raise ValidationException("Project code is required and cannot be blank")

        lot = await self._lot_repo.get_by_id(lot_id)
        if lot is None:
            raise NotFoundException("Material lot not found")
        if not lot.can_fulfill(quantity):
            raise ValidationException(
                f"Requested quantity {quantity} exceeds available quantity {lot.available_quantity} "
                f"for lot {lot.grn_document_no}/{lot.grn_item_no}"
            )

        item = MRNLineItem(
            mrn_id=mrn_id,
            line_no=len(mrn.line_items) + 1,
            lot_id=lot_id,
            requested_quantity=quantity,
            project_code=project_code.strip(),
            status="Draft",
            created_by=actor.username,
            modified_by=actor.username,
        )
        saved = await self._mrn_repo.add_line_item(mrn_id, item)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="MRN_LINE_ITEM_ADDED",
                table_name="mrn_line_items",
                record_id=saved.id,
                new_values={
                    "lot_id": lot_id,
                    "requested_quantity": quantity,
                    "project_code": saved.project_code,
                },
            )
        )
        return saved

    async def remove_line_item(self, mrn_id: int, line_item_id: int, actor: User) -> None:
        """Requirement 2.4: remove a line item without affecting the header or other lines."""
        mrn = await self.get_mrn(mrn_id)
        self._assert_can_edit(mrn, actor)

        item = await self._mrn_repo.get_line_item_by_id(line_item_id)
        if item is None or item.mrn_id != mrn_id:
            raise NotFoundException("Line item not found on this MRN")

        await self._mrn_repo.remove_line_item(mrn_id, line_item_id)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="MRN_LINE_ITEM_REMOVED",
                table_name="mrn_line_items",
                record_id=line_item_id,
                old_values={"lot_id": item.lot_id, "requested_quantity": item.requested_quantity},
            )
        )

    async def submit_mrn(self, mrn_id: int, actor: User) -> MaterialRequisition:
        """Requirement 2.5, 2.6, 2.7: Draft -> Submitted, requires >= 1 line item."""
        mrn = await self.get_mrn(mrn_id)
        if mrn.created_by != actor.username and not actor.has_role("Admin"):
            raise ForbiddenException("Only the creating user or an Admin may submit this MRN")
        if not mrn.can_submit():
            raise ValidationException("MRN must be in Draft status with at least one line item to submit")

        old_status = mrn.status
        when = datetime.now(timezone.utc)
        mrn.submit(actor.username, when)

        updated = await self._mrn_repo.update(mrn)
        for item in mrn.line_items:
            await self._mrn_repo.update_line_item(item)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="MRN_SUBMITTED",
                table_name="material_requisitions",
                record_id=mrn.id,
                old_values={"status": old_status},
                new_values={"status": mrn.status},
            )
        )
        return updated

    # ── Approval, posting, reprocessing ─────────────────────────────

    async def approve_and_post(self, mrn_id: int, actor: User) -> MaterialRequisition:
        """
        Requirement 3.1-3.9: transitions Submitted -> PostingInProgress, then
        attempts every line item independently, deriving the header status
        from the combined outcome. E-signature verification is performed by
        the caller (endpoint layer) before this method runs.
        """
        mrn = await self.get_mrn(mrn_id)
        if not mrn.can_approve_and_post():
            raise ValidationException("MRN must be in Submitted status to approve and post")

        mrn.begin_posting()
        await self._mrn_repo.update(mrn)

        for item in mrn.line_items:
            await self._post_single_line_item(mrn, item, actor, existing_posting=None)

        when = datetime.now(timezone.utc)
        mrn.recompute_status_after_posting(actor.username, when)
        updated = await self._mrn_repo.update(mrn)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="MRN_APPROVED_AND_POSTED",
                table_name="material_requisitions",
                record_id=mrn.id,
                new_values={"status": mrn.status},
            )
        )
        return updated

    async def reprocess_failed(self, mrn_id: int, actor: User) -> MaterialRequisition:
        """
        Requirement 3.7: retries only PostingFailed line items, reusing each
        one's existing ConsumptionPosting record (by idempotency_key) rather
        than creating a new one.
        """
        mrn = await self.get_mrn(mrn_id)
        if not mrn.can_reprocess():
            raise ValidationException("MRN must be PartiallyPosted or PostingFailed to reprocess")

        for item in mrn.line_items:
            if item.status != "PostingFailed":
                continue
            existing_posting = None
            if item.consumption_posting_id:
                existing_posting = await self._posting_repo.get_by_id(item.consumption_posting_id)
            await self._post_single_line_item(mrn, item, actor, existing_posting=existing_posting)

        when = datetime.now(timezone.utc)
        mrn.recompute_status_after_posting(actor.username, when)
        updated = await self._mrn_repo.update(mrn)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="MRN_REPROCESSED",
                table_name="material_requisitions",
                record_id=mrn.id,
                new_values={"status": mrn.status},
            )
        )
        return updated

    async def _post_single_line_item(
        self,
        mrn: MaterialRequisition,
        item: MRNLineItem,
        actor: User,
        existing_posting: ConsumptionPosting | None,
    ) -> None:
        """
        Shared per-line posting logic used by both approve_and_post (fresh
        attempt) and reprocess_failed (retry). Property 18: a line item with
        an existing Success posting is never re-submitted to SAP.
        """
        if existing_posting is not None and existing_posting.status == "Success":
            return

        idempotency_key = existing_posting.idempotency_key if existing_posting else f"{mrn.mrn_number}-{item.line_no}"

        lot = await self._lot_repo.get_by_id(item.lot_id)
        when = datetime.now(timezone.utc)

        # Property 22: posting cannot over-consume a lot — never call SAP in that case.
        if lot is None or not lot.can_fulfill(item.requested_quantity):
            error_message = (
                f"Cannot post: requested quantity {item.requested_quantity} would exceed "
                f"lot availability (over-consumption guard)"
            )
            posting = await self._save_posting_outcome(
                existing_posting, item, idempotency_key, success=False,
                sap_doc_no=None, error_message=error_message, when=when,
            )
            item.mark_posting_failed(posting.id)
            await self._mrn_repo.update_line_item(item)
            await self._write_posting_logs(mrn, item, lot, actor, success=False, error_message=error_message)
            return

        request_payload = {
            "material_code": lot.material_code,
            "batch_number": lot.batch_number,
            "plant": lot.plant,
            "quantity": item.requested_quantity,
            "idempotency_key": idempotency_key,
        }
        try:
            response = await self._sap_client.post_material_consumption(
                lot.material_code, lot.batch_number or "", lot.plant, item.requested_quantity, idempotency_key
            )
        except Exception as exc:  # noqa: BLE001 - SAP transport errors are opaque here
            posting = await self._save_posting_outcome(
                existing_posting, item, idempotency_key, success=False,
                sap_doc_no=None, error_message=str(exc), when=when,
            )
            item.mark_posting_failed(posting.id)
            await self._mrn_repo.update_line_item(item)
            await self._write_posting_logs(
                mrn, item, lot, actor, success=False, error_message=str(exc),
                request_payload=request_payload,
            )
            return

        sap_doc_no = response.get("sap_doc_no")
        posting = await self._save_posting_outcome(
            existing_posting, item, idempotency_key, success=True,
            sap_doc_no=sap_doc_no, error_message=None, when=when,
        )
        item.mark_posted(posting.id)
        await self._mrn_repo.update_line_item(item)

        lot.apply_consumption(item.requested_quantity)
        lot.mark_modified(actor.username)
        await self._lot_repo.update(lot)

        await self._write_posting_logs(
            mrn, item, lot, actor, success=True, response_payload=response, request_payload=request_payload,
        )

    async def _save_posting_outcome(
        self,
        existing_posting: ConsumptionPosting | None,
        item: MRNLineItem,
        idempotency_key: str,
        success: bool,
        sap_doc_no: str | None,
        error_message: str | None,
        when: datetime,
    ) -> ConsumptionPosting:
        if existing_posting is not None:
            if success:
                existing_posting.mark_success(sap_doc_no or "", when)
            else:
                existing_posting.mark_failed(error_message or "Unknown error", when)
            return await self._posting_repo.update(existing_posting)

        posting = ConsumptionPosting(line_item_id=item.id, idempotency_key=idempotency_key)
        if success:
            posting.mark_success(sap_doc_no or "", when)
        else:
            posting.mark_failed(error_message or "Unknown error", when)
        return await self._posting_repo.create(posting)

    async def _write_posting_logs(
        self,
        mrn: MaterialRequisition,
        item: MRNLineItem,
        lot: MRNMaterialLot | None,
        actor: User,
        success: bool,
        response_payload: dict | None = None,
        request_payload: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        """Requirement 3.8, 5.1: one SAPIntegrationLog + one AuditLog per line attempt."""
        await self._sap_log_repo.write(
            SAPIntegrationLog(
                transaction_type="MRN_MATERIAL_CONSUMPTION",
                direction="OUTBOUND",
                request_payload=request_payload,
                response_payload=response_payload,
                status="Success" if success else "Failed",
                error_message=error_message,
                created_by=actor.username,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id,
                username=actor.username,
                action="MRN_CONSUMPTION_POSTED" if success else "MRN_CONSUMPTION_POSTING_FAILED",
                table_name="mrn_line_items",
                record_id=item.id,
                new_values={"status": item.status},
                comments=(
                    f"MRN {mrn.mrn_number} line {item.line_no}: "
                    f"{'posted' if success else 'failed'}"
                    + (f" ({error_message})" if error_message else "")
                ),
            )
        )
