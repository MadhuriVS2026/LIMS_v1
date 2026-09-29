"""
SAP Integration Application Service.
Wraps SAP RFC calls (ZLIMS_read_batch_data1, ZLIMS_PROCESS_UD4, etc).
Currently simulated pending live pyrfc connection; every call is logged
via SAPIntegrationLog for full traceability regardless of transport.
"""
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import NotFoundException
from src.domain.entities.audit_log import AuditLog, SAPIntegrationLog, SAPReceivedLot
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import (
    IAuditLogRepository,
    ISAPIntegrationLogRepository,
    ISAPReceivedLotRepository,
)
from src.domain.repositories.sample_repository import ISampleRepository
from src.infrastructure.external.sap.sap_client import ISAPClient


class SAPIntegrationService:
    def __init__(
        self,
        sap_client: ISAPClient,
        sample_repo: ISampleRepository,
        sap_log_repo: ISAPIntegrationLogRepository,
        audit_repo: IAuditLogRepository,
        received_lot_repo: ISAPReceivedLotRepository,
    ) -> None:
        self._sap_client = sap_client
        self._sample_repo = sample_repo
        self._sap_log_repo = sap_log_repo
        self._audit_repo = audit_repo
        self._received_lot_repo = received_lot_repo

    async def post_usage_decision(
        self,
        sample_id: int,
        ud_code: str,
        ud_code_group: str | None,
        text_line: str | None,
        actor: User,
    ) -> dict:
        """Calls ZLIMS_PROCESS_UD4 (or simulation) to post the batch verdict to SAP QM."""
        sample = await self._sample_repo.get_by_id(sample_id)
        if sample is None:
            raise NotFoundException("Sample not found")
        if not sample.sap_inspection_lot:
            return {"success": False, "message": "No SAP inspection lot linked"}

        response = await self._sap_client.post_usage_decision(
            sample.sap_inspection_lot, ud_code, ud_code_group, text_line
        )

        await self._sap_log_repo.write(
            SAPIntegrationLog(
                transaction_type="USAGE_DECISION", direction="OUTBOUND",
                sample_id=sample.id, sap_inspection_lot=sample.sap_inspection_lot,
                request_payload={"lot": sample.sap_inspection_lot, "ud_code": ud_code},
                response_payload=response, status="Success",
                created_by=actor.username, completed_at=datetime.now(timezone.utc),
            )
        )

        sample.sap_ud_posted = True
        sample.sap_ud_code = ud_code
        sample.sap_ud_posted_at = datetime.now(timezone.utc)
        await self._sample_repo.update(sample)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="SAP_USAGE_DECISION",
                table_name="samples", record_id=sample.id,
                comments=f"UD Code: {ud_code} for lot {sample.sap_inspection_lot}",
            )
        )
        return {
            "success": True,
            "message": "Usage Decision posted successfully",
            "inspection_lot": sample.sap_inspection_lot,
        }

    async def list_logs(self, limit: int = 100) -> list:
        return await self._sap_log_repo.list_recent(limit)

    async def receive_inspection_lot(self, payload: dict) -> dict:
        """
        Stores an inspection lot pushed inbound from SAP CPI. Read-only: this
        never calls back out to SAP. Called by the unauthenticated (API-key
        protected) inbound endpoint, so there is no acting LIMS user — logs
        are attributed to "SAP-CPI".
        """
        header = payload.get("inspLotDat", {})
        characteristics = payload.get("inspCharData", []) or []
        inspection_lot = header.get("inspectionLotNum")

        lot = SAPReceivedLot(
            inspection_lot=inspection_lot,
            plant=header.get("inspectionLotPlant"),
            material_number=header.get("materialNum1") or header.get("materialNum"),
            material_desc=header.get("materialDesc"),
            batch_number=header.get("batchNumber"),
            storage_location=header.get("batchStorageLoc"),
            vendor_code=header.get("SupplierCode"),
            vendor_name=header.get("SupplierName"),
            vendor_batch=header.get("vendorBatchNum"),
            lot_quantity=header.get("inspectionLotQty"),
            lot_unit=header.get("inspectionLotUnit"),
            manufacturing_date=header.get("mfgDate2"),
            expiry_date=header.get("expDate"),
            characteristics=characteristics,
            raw_payload=payload,
        )
        saved = await self._received_lot_repo.upsert(lot)

        await self._sap_log_repo.write(
            SAPIntegrationLog(
                transaction_type="INSPECTION_LOT_RECEIVED", direction="INBOUND",
                sap_inspection_lot=inspection_lot,
                request_payload=payload, response_payload={"stored_id": saved.id},
                status="Success", created_by="SAP-CPI", completed_at=datetime.now(timezone.utc),
            )
        )
        await self._audit_repo.write(
            AuditLog(
                username="SAP-CPI", action="SAP_INSPECTION_LOT_RECEIVED",
                table_name="sap_received_lots", record_id=saved.id,
                comments=f"Received inspection lot {inspection_lot} from SAP CPI",
            )
        )
        return {
            "success": True,
            "message": f"Inspection lot {inspection_lot} received and stored",
            "inspection_lot": inspection_lot,
        }

    async def list_received_lots(self, limit: int = 100) -> list:
        return await self._received_lot_repo.list_recent(limit)

    async def pull_inspection_lot(self, inspection_lot: str, actor: User) -> dict:
        """
        Pulls an inspection lot from SAP CPI on demand (outbound call — the
        LIMS reaches out to SAP, nothing needs to be exposed to the internet
        for this to work) and stores it the same way as an inbound push, so
        it shows up identically in the received-lots list.
        """
        payload = await self._sap_client.read_inspection_lot(inspection_lot)

        await self._sap_log_repo.write(
            SAPIntegrationLog(
                transaction_type="INSPECTION_LOT_PULLED", direction="OUTBOUND",
                sap_inspection_lot=inspection_lot,
                request_payload={"inspection_lot": inspection_lot},
                response_payload=payload, status="Success",
                created_by=actor.username, completed_at=datetime.now(timezone.utc),
            )
        )
        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="SAP_INSPECTION_LOT_PULLED",
                table_name="sap_received_lots",
                comments=f"Pulled inspection lot {inspection_lot} from SAP CPI",
            )
        )

        header = payload.get("inspLotDat", {})
        characteristics = payload.get("inspCharData", []) or []
        lot = SAPReceivedLot(
            inspection_lot=header.get("inspectionLotNum") or inspection_lot,
            plant=header.get("inspectionLotPlant"),
            material_number=header.get("materialNum1") or header.get("materialNum"),
            material_desc=header.get("materialDesc"),
            batch_number=header.get("batchNumber"),
            storage_location=header.get("batchStorageLoc"),
            vendor_code=header.get("SupplierCode"),
            vendor_name=header.get("SupplierName"),
            vendor_batch=header.get("vendorBatchNum"),
            lot_quantity=header.get("inspectionLotQty"),
            lot_unit=header.get("inspectionLotUnit"),
            manufacturing_date=header.get("mfgDate2"),
            expiry_date=header.get("expDate"),
            characteristics=characteristics,
            raw_payload=payload,
        )
        saved = await self._received_lot_repo.upsert(lot)
        return {
            "success": True,
            "message": f"Inspection lot {saved.inspection_lot} pulled from SAP",
            "lot": saved,
        }
