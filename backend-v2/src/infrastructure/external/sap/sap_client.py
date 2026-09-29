"""
SAP Client abstraction (Port + Adapters).

Two transport styles are supported for the CaliberLIMS-SAP interface:

1. SAP Integration Suite / CPI HTTP flows (LIMS QAS Postman collection) —
   implemented by SAPIntegrationSuiteClient. This is the currently wired
   default (see Container.get_sap_client()). All calls target the SAP
   Integration Suite (CPI) tenant only — no other host is ever called.
   Endpoints:
     - Get/all_data_values         -> post_result_recording()   (Q64/Q65 result records)
     - Post/INSP_Point2            -> post_inspection_point()    (sampling/inspection point data)
     - Get/update_quantity         -> get_stock_quantity()        (material/plant/batch stock qty)
     - Get/WMS_PlantData           -> get_plant_data()
     - Post/Process_UD             -> post_usage_decision()       (batch Accept/Reject)
     - Post/Process_Stock          -> post_stock_quantities()     (5 storage-location postings)
     - Post/Result_Confirm         -> confirm_results()           (close out inspection lot)
     - Post_lims_inspection_lot    -> read_inspection_lot()       (pull full lot + characteristics)

   read_inspection_lot() is an outbound-only pull: the LIMS calls out to
   CPI and gets the lot data back in the response. Nothing needs to be
   reachable from the internet for this to work, unlike an inbound push.

   Note: the "inspection_lot Download" (LotRequest) call in the Postman
   collection targets a different host (the customer's own LIMS web API,
   not SAP CPI) and is intentionally NOT implemented here — this client
   only ever talks to the SAP CPI tenant.

2. Direct ABAP RFC via pyrfc (PyRFCSAPClient) — kept as a fallback for
   environments where CPI is not available and a direct NetWeaver RFC
   connection is preferred. Requires SAP NWRFC SDK on the host.

`SimulatedSAPClient` returns realistic mock data so the LIMS is fully
functional end-to-end without any live SAP connection — useful for local
dev/demo and automated tests.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone


class ISAPClient(ABC):
    """Port: abstraction over the SAP transport (CPI HTTP or direct RFC)."""

    @abstractmethod
    async def post_usage_decision(
        self, inspection_lot: str, ud_code: str, ud_code_group: str | None, text_line: str | None
    ) -> dict: ...

    @abstractmethod
    async def post_result_recording(self, records: list[dict]) -> dict: ...

    @abstractmethod
    async def post_inspection_point(self, points: list[dict], subsystem: str = "00002") -> dict: ...

    @abstractmethod
    async def get_stock_quantity(self, material: str, plant: str, storage_loc: str, batch: str) -> dict: ...

    @abstractmethod
    async def get_plant_data(self) -> dict: ...

    @abstractmethod
    async def post_stock_quantities(self, inspection_lot: str, quantities: dict[str, float]) -> dict: ...

    @abstractmethod
    async def confirm_results(self, inspection_lot: str, plant: str) -> dict: ...

    @abstractmethod
    async def read_inspection_lot(self, inspection_lot: str) -> dict: ...

    @abstractmethod
    async def read_grn_completed_materials(self, plant: str) -> list[dict]: ...

    @abstractmethod
    async def post_material_consumption(
        self,
        material_code: str,
        batch_number: str,
        plant: str,
        quantity: float,
        idempotency_key: str,
    ) -> dict: ...


class SimulatedSAPClient(ISAPClient):
    """Adapter: simulates SAP responses. Default until CPI/RFC credentials are configured."""

    async def post_usage_decision(
        self, inspection_lot: str, ud_code: str, ud_code_group: str | None, text_line: str | None
    ) -> dict:
        return {"message": "Usage Decision posted successfully (simulated)"}

    async def post_result_recording(self, records: list[dict]) -> dict:
        return {"message": f"Recorded {len(records)} result(s) (simulated)"}

    async def post_inspection_point(self, points: list[dict], subsystem: str = "00002") -> dict:
        return {"message": f"Posted {len(points)} inspection point(s) (simulated)"}

    async def get_stock_quantity(self, material: str, plant: str, storage_loc: str, batch: str) -> dict:
        return {"material": material, "plant": plant, "storage_loc": storage_loc, "batch": batch, "quantity": 0.0}

    async def get_plant_data(self) -> dict:
        return {"plant": "EP22", "flag": "X"}

    async def post_stock_quantities(self, inspection_lot: str, quantities: dict[str, float]) -> dict:
        return {"message": f"Posted stock quantities for lot {inspection_lot} (simulated)"}

    async def confirm_results(self, inspection_lot: str, plant: str) -> dict:
        return {"message": f"Results confirmed for lot {inspection_lot} (simulated)"}

    async def read_inspection_lot(self, inspection_lot: str) -> dict:
        return {
            "inspLotDat": {
                "inspectionLotNum": inspection_lot,
                "inspectionLotPlant": "EP22",
                "materialNum1": f"MAT-{inspection_lot[-4:]}",
                "materialDesc": "Simulated Material",
                "batchNumber": f"B{inspection_lot[-6:]}",
                "SupplierName": "Simulated Vendor",
                "mfgDate2": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "expDate": "2027-12-31",
            },
            "inspCharData": [],
        }

    async def read_grn_completed_materials(self, plant: str) -> list[dict]:
        """
        Requirement 1.7: realistic mock GRN-complete material lots so the MRN
        module is fully functional end-to-end without live SAP credentials.
        Field names here mirror the (unconfirmed) natural key/shape assumed
        by MRNService — see SAPIntegrationSuiteClient's mapping helpers below
        for where this gets reconciled against the real CPI payload later.
        """
        now = datetime.now(timezone.utc)
        return [
            {
                "grn_document_no": "5000001234",
                "grn_item_no": "0010",
                "material_code": "RM-NITROGEN-USP",
                "material_description": "Nitrogen USP (Simulated)",
                "batch_number": "B24GRN01",
                "plant": plant,
                "unit": "KG",
                "quantity": 50.0,
                "grn_date": now.strftime("%Y-%m-%d"),
            },
            {
                "grn_document_no": "5000001235",
                "grn_item_no": "0010",
                "material_code": "RM-PROPYLENE-GLYCOL",
                "material_description": "Propylene Glycol (Simulated)",
                "batch_number": "B24GRN02",
                "plant": plant,
                "unit": "KG",
                "quantity": 25.5,
                "grn_date": now.strftime("%Y-%m-%d"),
            },
        ]

    async def post_material_consumption(
        self,
        material_code: str,
        batch_number: str,
        plant: str,
        quantity: float,
        idempotency_key: str,
    ) -> dict:
        """Requirement 3.10: realistic mock SAP document number."""
        return {
            "sap_doc_no": f"CONS-{idempotency_key}",
            "message": (
                f"Consumption of {quantity} posted for material {material_code} "
                f"batch {batch_number} at plant {plant} (simulated)"
            ),
        }


class SAPIntegrationSuiteClient(ISAPClient):
    """
    Adapter: connects to SAP Integration Suite (CPI) HTTP integration flows,
    matching the "LIMS QAS" Postman collection endpoints exactly. This is the
    default live client — see Container.get_sap_client().

    Auth: Basic Auth (username/password from Settings.SAP_CPI_USERNAME/PASSWORD)
    for all CPI endpoints. This client never calls any host other than
    SAP_CPI_BASE_URL.
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout_seconds: int = 30,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._timeout = timeout_seconds

    def _client(self, base_url: str | None = None) -> "httpx.AsyncClient":  # type: ignore[name-defined]
        import httpx

        return httpx.AsyncClient(
            base_url=base_url or self._base_url,
            auth=(self._username, self._password),
            timeout=self._timeout,
        )

    @staticmethod
    def _raise_on_error(response) -> None:  # type: ignore[no-untyped-def]
        if response.status_code >= 400:
            raise RuntimeError(
                f"SAP CPI call failed ({response.status_code}): {response.text[:500]}"
            )

    # ─── UD -> Post/Process_UD ───
    async def post_usage_decision(
        self, inspection_lot: str, ud_code: str, ud_code_group: str | None, text_line: str | None
    ) -> dict:
        payload = {
            "root": {
                "I_LOT": inspection_lot,
                "I_UD_CODE": ud_code,
                "I_UD_CODEGROUP": ud_code_group or "",
                "I_TEXT_LINE": text_line or "",
                "I_PROCESS_MODE": "N",
            }
        }
        async with self._client() as client:
            response = await client.post("/http/QAS/Post/Process_UD", json=payload)
        self._raise_on_error(response)
        return {"message": "Usage Decision posted successfully", "raw": response.json() if response.text else {}}

    # ─── Result recording -> Get/all_data_values ───
    async def post_result_recording(self, records: list[dict]) -> dict:
        payload = {
            "root": {
                "I_IND_EVALUATION_TRANSFER": "X",
                "I_IND_CLOSE_PROCESSING": "X",
                "I_IND_PROC_COMMIT_WORK": "X",
                "I_IND_POSTING_KZ": "X",
                "I_SEND_PROTOCOL_MAIL": "",
                "LT_QAIMRTAB": {"item": records},
            }
        }
        async with self._client() as client:
            response = await client.post("/http/QAS/Get/all_data_values", json=payload)
        self._raise_on_error(response)
        return {"message": f"Recorded {len(records)} result(s)", "raw": response.json() if response.text else {}}

    # ─── INSP Point2 -> Post/INSP_Point2 ───
    async def post_inspection_point(self, points: list[dict], subsystem: str = "00002") -> dict:
        payload = {"root": {"I_SUBSYS": subsystem, "GT_QAIPP": {"item": points}}}
        async with self._client() as client:
            response = await client.post("/http/QAS/Post/INSP_Point2", json=payload)
        self._raise_on_error(response)
        return {"message": f"Posted {len(points)} inspection point(s)", "raw": response.json() if response.text else {}}

    # ─── Update quantity -> Get/update_quantity ───
    async def get_stock_quantity(self, material: str, plant: str, storage_loc: str, batch: str) -> dict:
        params = {"I_MATNR": material, "I_WERKS": plant, "I_LGORT": storage_loc, "I_CHARG": batch}
        async with self._client() as client:
            response = await client.get("/http/Dev/Get/update_quantity", params=params)
        self._raise_on_error(response)
        return response.json() if response.text else {}

    # ─── WMS plant -> Get/WMS_PlantData ───
    async def get_plant_data(self) -> dict:
        async with self._client() as client:
            response = await client.get("/http/Dev/Get/WMS_PlantData")
        self._raise_on_error(response)
        return response.json() if response.text else {}

    # ─── Stock Post -> Post/Process_Stock ───
    async def post_stock_quantities(self, inspection_lot: str, quantities: dict[str, float]) -> dict:
        root = {"I_LOT": inspection_lot, "I_PROCESS_MODE": "N"}
        for i in range(1, 6):
            key = f"storage_{i}"
            value = quantities.get(key, 0)
            root[f"I_QLGO_VM{i:02d}"] = str(value)
            root[f"I_VMENGE{i:02d}"] = str(value)
        async with self._client() as client:
            response = await client.post("/http/QAS/Post/Process_Stock", json={"root": root})
        self._raise_on_error(response)
        return {"message": f"Posted stock quantities for lot {inspection_lot}", "raw": response.json() if response.text else {}}

    # ─── Result Confirm -> Post/Result_Confirm ───
    async def confirm_results(self, inspection_lot: str, plant: str) -> dict:
        payload = {"root": {"I_LOT": inspection_lot, "I_PLANT": plant}}
        async with self._client() as client:
            response = await client.post("/http/QAS/Post/Result_Confirm", json=payload)
        self._raise_on_error(response)
        return {"message": f"Results confirmed for lot {inspection_lot}", "raw": response.json() if response.text else {}}

    # ─── Pull inspection lot -> Post_lims_inspection_lot ───
    async def read_inspection_lot(self, inspection_lot: str) -> dict:
        """
        Pulls the full inspection lot (header + characteristics + catalog data)
        from SAP CPI on demand. Outbound-only: the LIMS calls CPI and reads the
        response — CPI never needs to reach the LIMS for this operation.
        """
        payload = {"inspLotDat": {"inspectionLotNum": inspection_lot}}
        async with self._client() as client:
            response = await client.post("/http/QAS/Post_lims_inspection_lot", json=payload)
        self._raise_on_error(response)
        return response.json() if response.text else {}

    # ─── GRN-complete materials (MRN module) ───
    #
    # NOTE (MRN Requirement — Dependencies and Assumptions): the exact SAP CPI
    # iFlow path and payload field names for the GRN-complete material feed
    # and the consumption-posting request/response contract are NOT YET
    # CONFIRMED with SAP CoE. `(grn_document_no, grn_item_no)` is a best-guess
    # natural key. Everything CPI-shape-specific is isolated in these two
    # small private helpers + the two constants below, so it can be revised
    # in one place without touching MRNService or the domain layer.
    _GRN_PULL_PATH = "/http/QAS/Post_lims_grn_material"
    _MATERIAL_CONSUMPTION_PATH = "/http/QAS/Post_lims_material_consumption"

    @staticmethod
    def _map_grn_response_to_lots(raw: dict) -> list[dict]:
        """Best-guess mapping from the (unconfirmed) CPI GRN-feed response shape."""
        items = raw.get("grnMaterialData") or raw.get("items") or []
        lots = []
        for item in items:
            lots.append(
                {
                    "grn_document_no": item.get("grnDocumentNo") or item.get("GRN_DOC_NO"),
                    "grn_item_no": item.get("grnItemNo") or item.get("GRN_ITEM_NO"),
                    "material_code": item.get("materialCode") or item.get("MATERIAL"),
                    "material_description": item.get("materialDesc") or item.get("MATERIAL_DESC"),
                    "batch_number": item.get("batchNumber") or item.get("BATCH"),
                    "plant": item.get("plant") or item.get("PLANT"),
                    "unit": item.get("unit") or item.get("UOM"),
                    "quantity": item.get("quantity") or item.get("QUANTITY") or 0.0,
                    "grn_date": item.get("grnDate") or item.get("GRN_DATE"),
                }
            )
        return lots

    async def read_grn_completed_materials(self, plant: str) -> list[dict]:
        """
        Requirement 1.2: outbound pull of GRN-complete materials at `plant`
        from SAP CPI. See `_map_grn_response_to_lots` for the isolated,
        easily-revisable field mapping.
        """
        payload = {"root": {"I_PLANT": plant}}
        async with self._client() as client:
            response = await client.post(self._GRN_PULL_PATH, json=payload)
        self._raise_on_error(response)
        raw = response.json() if response.text else {}
        return self._map_grn_response_to_lots(raw)

    async def post_material_consumption(
        self,
        material_code: str,
        batch_number: str,
        plant: str,
        quantity: float,
        idempotency_key: str,
    ) -> dict:
        """
        Requirement 3.3: outbound consumption posting for a single MRN line
        item, deducting quantity against an internal order in SAP. The
        idempotency_key is sent through so a retried call can be recognized
        as a duplicate by SAP/CPI if it supports that; the LIMS side also
        never re-sends a call for an already-Success line (see MRNService).
        """
        payload = {
            "root": {
                "I_MATERIAL": material_code,
                "I_BATCH": batch_number,
                "I_PLANT": plant,
                "I_QUANTITY": str(quantity),
                "I_IDEMPOTENCY_KEY": idempotency_key,
            }
        }
        async with self._client() as client:
            response = await client.post(self._MATERIAL_CONSUMPTION_PATH, json=payload)
        self._raise_on_error(response)
        raw = response.json() if response.text else {}
        sap_doc_no = raw.get("sapDocNo") or raw.get("SAP_DOC_NO") or raw.get("materialDocument")
        return {
            "sap_doc_no": sap_doc_no,
            "message": f"Consumption posted for material {material_code} batch {batch_number}",
            "raw": raw,
        }


class PyRFCSAPClient(ISAPClient):
    """
    Adapter: connects to a live SAP system via pyrfc (direct ABAP RFC, bypassing CPI).
    Requires: pip install pyrfc + SAP NWRFC SDK installed on the host.
    Not activated by default — see Container.get_sap_client() to enable.
    Only the two originally-scoped RFC modules are implemented; the newer
    CPI-only operations raise NotImplementedError here.
    """

    def __init__(self, connection_params: dict) -> None:
        self._connection_params = connection_params

    def _connect(self):
        from pyrfc import Connection  # type: ignore[import-not-found]
        return Connection(**self._connection_params)

    async def post_usage_decision(
        self, inspection_lot: str, ud_code: str, ud_code_group: str | None, text_line: str | None
    ) -> dict:
        conn = self._connect()
        try:
            result = conn.call(
                "ZLIMS_PROCESS_UD4",
                I_LOT=inspection_lot,
                I_UD_CODE=ud_code,
                I_UD_CODEGROUP=ud_code_group or "",
                I_TEXT_LINE=text_line or "",
                I_PROCESS_MODE="N",
            )
            error = result.get("ERROR")
            if error:
                raise RuntimeError(f"SAP Usage Decision failed: {error}")
            return {"message": "Usage Decision posted successfully"}
        finally:
            conn.close()

    async def post_result_recording(self, records: list[dict]) -> dict:
        raise NotImplementedError("Result recording is only available via the CPI client (SAPIntegrationSuiteClient).")

    async def post_inspection_point(self, points: list[dict], subsystem: str = "00002") -> dict:
        raise NotImplementedError("Inspection point posting is only available via the CPI client.")

    async def get_stock_quantity(self, material: str, plant: str, storage_loc: str, batch: str) -> dict:
        raise NotImplementedError("Stock quantity lookup is only available via the CPI client.")

    async def get_plant_data(self) -> dict:
        raise NotImplementedError("Plant data lookup is only available via the CPI client.")

    async def post_stock_quantities(self, inspection_lot: str, quantities: dict[str, float]) -> dict:
        raise NotImplementedError("Stock quantity posting is only available via the CPI client.")

    async def confirm_results(self, inspection_lot: str, plant: str) -> dict:
        raise NotImplementedError("Result confirmation is only available via the CPI client.")

    async def read_inspection_lot(self, inspection_lot: str) -> dict:
        raise NotImplementedError("Inspection lot pull is only available via the CPI client.")

    async def read_grn_completed_materials(self, plant: str) -> list[dict]:
        raise NotImplementedError("GRN-complete material pull is only available via the CPI client.")

    async def post_material_consumption(
        self,
        material_code: str,
        batch_number: str,
        plant: str,
        quantity: float,
        idempotency_key: str,
    ) -> dict:
        raise NotImplementedError("Material consumption posting is only available via the CPI client.")
