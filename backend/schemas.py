from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str
    full_name: str
    role: str
    email: Optional[str] = None
    department: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# Audit Log schemas
class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    username: str
    action: str
    table_name: str
    record_id: Optional[int] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    comments: Optional[str] = None
    class Config:
        from_attributes = True

# Test schemas
class TestBase(BaseModel):
    code: str
    name: str
    type: str
    unit: Optional[str] = None
    method_no: Optional[str] = None
    category: Optional[str] = None
    technique: Optional[str] = None

class TestCreate(TestBase):
    pass

class TestResponse(TestBase):
    id: int
    status: str
    class Config:
        from_attributes = True

# Product schemas
class ProductBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    material_type: Optional[str] = None
    retest_period_days: Optional[int] = None
    storage_condition: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Specification Test schemas
class SpecTestBase(BaseModel):
    test_id: int
    min_limit: Optional[float] = None
    max_limit: Optional[float] = None
    expected_result: Optional[str] = None
    display_in_coa: Optional[bool] = True

class SpecTestCreate(SpecTestBase):
    pass

class SpecTestResponse(SpecTestBase):
    id: int
    test: TestResponse
    class Config:
        from_attributes = True

# Specification schemas
class SpecBase(BaseModel):
    product_id: int
    version: int = 1

class SpecCreate(SpecBase):
    spec_type: Optional[str] = None
    document_no: Optional[str] = None
    tests: List[SpecTestCreate]

class SpecResponse(SpecBase):
    id: int
    spec_id_code: Optional[str] = None
    spec_type: Optional[str] = None
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    tests: List[SpecTestResponse]
    product: ProductResponse
    class Config:
        from_attributes = True

# E-Sign verification schema
class ESignRequest(BaseModel):
    password: str
    comments: Optional[str] = None

# Sample result schemas
class SampleResultBase(BaseModel):
    result_value: Optional[float] = None
    result_text: Optional[str] = None

class SampleResultSubmit(SampleResultBase):
    result_id: int
    password: str

class SampleResultResponse(BaseModel):
    id: int
    sample_id: int
    test_id: int
    min_limit: Optional[float] = None
    max_limit: Optional[float] = None
    expected_result: Optional[str] = None
    result_value: Optional[float] = None
    result_text: Optional[str] = None
    status: str
    is_oos: bool
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    test: TestResponse
    class Config:
        from_attributes = True

# Sample schemas
class SampleCreate(BaseModel):
    product_id: int
    batch_number: str
    quantity_received: float
    unit: str
    sample_type: Optional[str] = None
    priority: Optional[str] = "Normal"
    sap_inspection_lot: Optional[str] = None
    sap_material: Optional[str] = None
    sap_plant: Optional[str] = None
    sap_vendor: Optional[str] = None
    sap_vendor_batch: Optional[str] = None
    manufacturing_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

class SampleResponse(BaseModel):
    id: int
    sample_code: str
    product_id: int
    batch_number: str
    quantity_received: float
    unit: str
    sample_type: Optional[str] = None
    priority: Optional[str] = None
    status: str
    sap_inspection_lot: Optional[str] = None
    sap_ud_posted: Optional[bool] = False
    manufacturing_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    logged_by: Optional[str] = None
    logged_at: Optional[datetime] = None
    received_by: Optional[str] = None
    received_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    coa_released_by: Optional[str] = None
    coa_released_at: Optional[datetime] = None
    coa_data: Optional[dict] = None
    product: ProductResponse
    results: List[SampleResultResponse]
    class Config:
        from_attributes = True

# OOS Investigation schemas
class OOSCreate(BaseModel):
    sample_id: int
    test_id: int
    phase1_comments: str

class OOSSubmitDetails(BaseModel):
    root_cause: str
    corrective_action: str
    password: str

class OOSResponse(BaseModel):
    id: int
    sample_id: int
    test_id: int
    investigation_type: Optional[str] = "OOS"
    phase1_comments: str
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    status: str
    created_by: str
    created_at: datetime
    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    test: TestResponse
    class Config:
        from_attributes = True

# ==================== NEW MODULE SCHEMAS ====================

# Instrument schemas
class InstrumentBase(BaseModel):
    model_config = {"protected_namespaces": ()}
    code: str
    name: str
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None
    calibration_frequency_days: Optional[int] = None

class InstrumentCreate(InstrumentBase):
    pass

class InstrumentResponse(InstrumentBase):
    id: int
    status: str
    calibration_due_date: Optional[datetime] = None
    last_calibrated_at: Optional[datetime] = None
    last_calibrated_by: Optional[str] = None
    qualification_status: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class InstrumentCalibrationCreate(BaseModel):
    instrument_id: int
    calibration_date: datetime
    next_due_date: Optional[datetime] = None
    result: str
    certificate_no: Optional[str] = None
    comments: Optional[str] = None

class InstrumentCalibrationResponse(BaseModel):
    id: int
    instrument_id: int
    calibration_date: datetime
    next_due_date: Optional[datetime] = None
    performed_by: str
    result: str
    certificate_no: Optional[str] = None
    comments: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Stability schemas
class StabilityProtocolCreate(BaseModel):
    product_id: int
    condition: str
    duration_months: int
    study_type: Optional[str] = None
    testing_frequency: Optional[str] = None

class StabilityProtocolResponse(BaseModel):
    id: int
    protocol_code: str
    product_id: int
    condition: str
    duration_months: int
    study_type: Optional[str] = None
    testing_frequency: Optional[str] = None
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    product: ProductResponse
    class Config:
        from_attributes = True

class StabilitySampleCreate(BaseModel):
    protocol_id: int
    batch_number: str
    time_point_months: int
    scheduled_date: Optional[datetime] = None

class StabilitySampleResponse(BaseModel):
    id: int
    protocol_id: int
    batch_number: str
    time_point_months: int
    scheduled_date: Optional[datetime] = None
    pull_date: Optional[datetime] = None
    status: str
    sample_id: Optional[int] = None
    comments: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Column Management schemas
class ColumnCreate(BaseModel):
    code: str
    name: str
    type: Optional[str] = None
    manufacturer: Optional[str] = None
    dimensions: Optional[str] = None
    serial_number: Optional[str] = None
    instrument_id: Optional[int] = None
    max_injections: Optional[int] = None

class ColumnResponse(BaseModel):
    id: int
    code: str
    name: str
    type: Optional[str] = None
    manufacturer: Optional[str] = None
    dimensions: Optional[str] = None
    serial_number: Optional[str] = None
    instrument_id: Optional[int] = None
    max_injections: Optional[int] = None
    current_injections: int
    status: str
    received_date: Optional[datetime] = None
    retirement_date: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Reference Standard schemas
class ReferenceStandardCreate(BaseModel):
    code: str
    name: str
    lot_number: Optional[str] = None
    potency: Optional[float] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    storage_condition: Optional[str] = None
    quantity_received: Optional[float] = None
    unit: Optional[str] = None
    received_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

class ReferenceStandardResponse(BaseModel):
    id: int
    code: str
    name: str
    lot_number: Optional[str] = None
    potency: Optional[float] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    storage_condition: Optional[str] = None
    quantity_received: Optional[float] = None
    quantity_remaining: Optional[float] = None
    unit: Optional[str] = None
    received_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Chemical/Reagent schemas
class ChemicalReagentCreate(BaseModel):
    code: str
    name: str
    grade: Optional[str] = None
    manufacturer: Optional[str] = None
    lot_number: Optional[str] = None
    cas_number: Optional[str] = None
    quantity_received: Optional[float] = None
    unit: Optional[str] = None
    storage_condition: Optional[str] = None
    received_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

class ChemicalReagentResponse(BaseModel):
    id: int
    code: str
    name: str
    grade: Optional[str] = None
    manufacturer: Optional[str] = None
    lot_number: Optional[str] = None
    cas_number: Optional[str] = None
    quantity_received: Optional[float] = None
    quantity_remaining: Optional[float] = None
    unit: Optional[str] = None
    storage_condition: Optional[str] = None
    received_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    opened_date: Optional[datetime] = None
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Volumetric Solution schemas
class VolumetricSolutionCreate(BaseModel):
    code: str
    name: str
    concentration: Optional[str] = None
    prepared_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    standardization_factor: Optional[float] = None

class VolumetricSolutionResponse(BaseModel):
    id: int
    code: str
    name: str
    concentration: Optional[str] = None
    prepared_by: Optional[str] = None
    prepared_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    standardization_factor: Optional[float] = None
    standardized_by: Optional[str] = None
    standardized_date: Optional[datetime] = None
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# SAP Integration schemas
class SAPBatchDataRequest(BaseModel):
    inspection_lot: str

class SAPBatchDataResponse(BaseModel):
    inspection_lot: str
    material_number: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    vendor_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_batch: Optional[str] = None
    canceled: bool = False

class SAPUsageDecisionRequest(BaseModel):
    sample_id: int
    ud_code: str  # Accept/Reject code
    ud_code_group: Optional[str] = None
    text_line: Optional[str] = None
    password: str  # E-sign

class SAPUsageDecisionResponse(BaseModel):
    success: bool
    message: str
    inspection_lot: Optional[str] = None

class SAPIntegrationLogResponse(BaseModel):
    id: int
    transaction_type: str
    direction: str
    sample_id: Optional[int] = None
    sap_inspection_lot: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Dashboard schemas
class DashboardStats(BaseModel):
    total_samples: int
    pending_samples: int
    oos_open: int
    samples_today: int
    instruments_due_calibration: int
    pending_reviews: int
    approved_today: int
    rejected_today: int
