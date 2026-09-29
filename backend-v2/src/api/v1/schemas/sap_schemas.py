"""Pydantic schemas for SAP Integration endpoints."""
from pydantic import BaseModel, ConfigDict


class SAPInspectionLotHeader(BaseModel):
    """
    Mirrors the "inspLotDat" object from the LIMS QAS Postman collection's
    "inspection_lot Download" request body. Only the fields the LIMS actually
    uses are declared; extra fields SAP sends are ignored (not rejected).
    """

    model_config = ConfigDict(extra="ignore")

    inspectionLotNum: str
    inspectionLotPlant: str | None = None
    materialNum1: str | None = None
    materialNum: str | None = None
    materialDesc: str | None = None
    batchNumber: str | None = None
    batchStorageLoc: str | None = None
    SupplierCode: str | None = None
    SupplierName: str | None = None
    vendorBatchNum: str | None = None
    inspectionLotQty: str | None = None
    inspectionLotUnit: str | None = None
    mfgDate2: str | None = None
    expDate: str | None = None
    certNo: str | None = None
    certStatus: str | None = None


class SAPInspectionCharacteristic(BaseModel):
    """Mirrors one entry of the "inspCharData" array from the same request."""

    model_config = ConfigDict(extra="ignore")

    InspectionLot: str | None = None
    characteristicNum: str | None = None
    testName: str | None = None
    uom: str | None = None
    targetValue: str | None = None
    upperTolLimit: str | None = None
    lowerTolLimit: str | None = None


class SAPInspectionLotPushRequest(BaseModel):
    """
    Inbound payload SAP CPI pushes to this LIMS for a new/updated inspection lot.
    Shape matches the Postman collection's "inspection_lot Download" body so the
    existing CPI iFlow can be repointed here with no payload changes.
    """

    model_config = ConfigDict(extra="ignore")

    inspLotDat: SAPInspectionLotHeader
    inspCharData: list[SAPInspectionCharacteristic] = []


class SAPInspectionLotPullRequest(BaseModel):
    """Request to pull an inspection lot from SAP CPI on demand (outbound call)."""

    inspection_lot: str


class SAPUsageDecisionRequest(BaseModel):
    sample_id: int
    ud_code: str
    ud_code_group: str | None = None
    text_line: str | None = None
    password: str


class SAPUsageDecisionResponse(BaseModel):
    success: bool
    message: str
    inspection_lot: str | None = None
