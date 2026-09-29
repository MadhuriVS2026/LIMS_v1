from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # Admin, Analyst, Supervisor, QA
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    email = Column(String, nullable=True)
    department = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    material_type = Column(String, nullable=True)  # RM, PM, FG, IP
    retest_period_days = Column(Integer, nullable=True)
    storage_condition = Column(String, nullable=True)
    status = Column(String, default="Pending Approval")  # Active, Inactive, Pending Approval
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    specifications = relationship("Specification", back_populates="product")


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # Quantitative, Qualitative, Statistical-1, Statistical-2, Multi-Qualitative, Multi-Quantitative
    unit = Column(String, nullable=True)
    method_no = Column(String, nullable=True)
    category = Column(String, nullable=True)  # Physical, Chemical, Microbiological, etc.
    technique = Column(String, nullable=True)  # HPLC, GC, UV, IR, etc.
    status = Column(String, default="Active")  # Active, Inactive


class Specification(Base):
    __tablename__ = "specifications"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    version = Column(Integer, default=1)
    spec_id_code = Column(String, nullable=True)  # User-friendly spec ID
    spec_type = Column(String, nullable=True)  # Regulatory, Release, Tentative
    effective_from = Column(DateTime, nullable=True)
    review_date = Column(DateTime, nullable=True)
    document_no = Column(String, nullable=True)
    status = Column(String, default="Pending Approval")
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="specifications")
    tests = relationship("SpecificationTest", back_populates="specification")


class SpecificationTest(Base):
    __tablename__ = "specification_tests"

    id = Column(Integer, primary_key=True, index=True)
    specification_id = Column(Integer, ForeignKey("specifications.id"), nullable=False)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    min_limit = Column(Float, nullable=True)
    max_limit = Column(Float, nullable=True)
    expected_result = Column(String, nullable=True)
    display_in_coa = Column(Boolean, default=True)

    specification = relationship("Specification", back_populates="tests")
    test = relationship("Test")


class Sample(Base):
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, index=True)
    sample_code = Column(String, unique=True, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number = Column(String, nullable=False)
    quantity_received = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    sample_type = Column(String, nullable=True)  # Raw Material, Finished Product, In-Process, Stability
    priority = Column(String, default="Normal")  # Normal, Urgent
    status = Column(String, default="Logged")
    
    # SAP Integration fields
    sap_inspection_lot = Column(String, nullable=True)  # SAP Inspection Lot (PRUEFLOS)
    sap_material = Column(String, nullable=True)
    sap_plant = Column(String, nullable=True)
    sap_vendor = Column(String, nullable=True)
    sap_vendor_batch = Column(String, nullable=True)
    manufacturing_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)

    logged_by = Column(String, nullable=True)
    logged_at = Column(DateTime, default=datetime.datetime.utcnow)
    received_by = Column(String, nullable=True)
    received_at = Column(DateTime, nullable=True)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    coa_released_by = Column(String, nullable=True)
    coa_released_at = Column(DateTime, nullable=True)
    coa_data = Column(JSON, nullable=True)

    # SAP Usage Decision posted
    sap_ud_posted = Column(Boolean, default=False)
    sap_ud_code = Column(String, nullable=True)
    sap_ud_posted_at = Column(DateTime, nullable=True)

    product = relationship("Product")
    results = relationship("SampleResult", back_populates="sample")


class SampleResult(Base):
    __tablename__ = "sample_results"

    id = Column(Integer, primary_key=True, index=True)
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    min_limit = Column(Float, nullable=True)
    max_limit = Column(Float, nullable=True)
    expected_result = Column(String, nullable=True)
    result_value = Column(Float, nullable=True)
    result_text = Column(String, nullable=True)
    status = Column(String, default="Pending")  # Pending, Submitted, Approved
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    is_oos = Column(Boolean, default=False)
    oos_investigation_id = Column(Integer, ForeignKey("oos_investigations.id"), nullable=True)

    sample = relationship("Sample", back_populates="results")
    test = relationship("Test")


class OOSInvestigation(Base):
    __tablename__ = "oos_investigations"

    id = Column(Integer, primary_key=True, index=True)
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    investigation_type = Column(String, default="OOS")  # OOS, OOT
    phase1_comments = Column(String, nullable=False)
    root_cause = Column(String, nullable=True)
    corrective_action = Column(String, nullable=True)
    status = Column(String, default="Open")  # Open, Phase1, Phase2, Closed
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    closed_by = Column(String, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    sample = relationship("Sample")
    test = relationship("Test")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String, nullable=False)
    action = Column(String, nullable=False)
    table_name = Column(String, nullable=False)
    record_id = Column(Integer, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    comments = Column(String, nullable=True)


# ==================== NEW MODULES ====================

class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)  # HPLC, GC, UV-Vis, Balance, pH Meter, etc.
    manufacturer = Column(String, nullable=True)
    model_number = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    location = Column(String, nullable=True)
    status = Column(String, default="Active")  # Active, Under Calibration, Under Maintenance, Inactive
    calibration_due_date = Column(DateTime, nullable=True)
    calibration_frequency_days = Column(Integer, nullable=True)
    last_calibrated_at = Column(DateTime, nullable=True)
    last_calibrated_by = Column(String, nullable=True)
    qualification_status = Column(String, nullable=True)  # Qualified, Pending, Expired
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class InstrumentCalibration(Base):
    __tablename__ = "instrument_calibrations"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    calibration_date = Column(DateTime, nullable=False)
    next_due_date = Column(DateTime, nullable=True)
    performed_by = Column(String, nullable=False)
    result = Column(String, nullable=True)  # Pass, Fail
    certificate_no = Column(String, nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    instrument = relationship("Instrument")


class StabilityProtocol(Base):
    __tablename__ = "stability_protocols"

    id = Column(Integer, primary_key=True, index=True)
    protocol_code = Column(String, unique=True, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    condition = Column(String, nullable=False)  # 25°C/60%RH, 30°C/65%RH, 40°C/75%RH
    duration_months = Column(Integer, nullable=False)
    study_type = Column(String, nullable=True)  # Long Term, Accelerated, Intermediate
    testing_frequency = Column(String, nullable=True)  # e.g., "0,3,6,9,12,18,24"
    status = Column(String, default="Draft")  # Draft, Active, Completed, Cancelled
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    product = relationship("Product")
    samples = relationship("StabilitySample", back_populates="protocol")


class StabilitySample(Base):
    __tablename__ = "stability_samples"

    id = Column(Integer, primary_key=True, index=True)
    protocol_id = Column(Integer, ForeignKey("stability_protocols.id"), nullable=False)
    batch_number = Column(String, nullable=False)
    time_point_months = Column(Integer, nullable=False)
    scheduled_date = Column(DateTime, nullable=True)
    pull_date = Column(DateTime, nullable=True)
    status = Column(String, default="Scheduled")  # Scheduled, Pulled, Testing, Completed
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=True)  # Links to main sample
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    protocol = relationship("StabilityProtocol", back_populates="samples")


class ColumnMaster(Base):
    """Chromatography column management"""
    __tablename__ = "columns"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)  # C18, C8, HILIC, etc.
    manufacturer = Column(String, nullable=True)
    dimensions = Column(String, nullable=True)  # 250x4.6mm, 5um
    serial_number = Column(String, nullable=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=True)
    max_injections = Column(Integer, nullable=True)
    current_injections = Column(Integer, default=0)
    status = Column(String, default="Active")  # Active, Retired, Under Test
    received_date = Column(DateTime, nullable=True)
    retirement_date = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ReferenceStandard(Base):
    __tablename__ = "reference_standards"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    lot_number = Column(String, nullable=True)
    potency = Column(Float, nullable=True)
    manufacturer = Column(String, nullable=True)
    category = Column(String, nullable=True)  # Primary, Secondary, Working
    storage_condition = Column(String, nullable=True)
    quantity_received = Column(Float, nullable=True)
    quantity_remaining = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    received_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    status = Column(String, default="Active")  # Active, Expired, Exhausted
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ChemicalReagent(Base):
    __tablename__ = "chemicals_reagents"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    grade = Column(String, nullable=True)  # AR, LR, HPLC, etc.
    manufacturer = Column(String, nullable=True)
    lot_number = Column(String, nullable=True)
    cas_number = Column(String, nullable=True)
    quantity_received = Column(Float, nullable=True)
    quantity_remaining = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    storage_condition = Column(String, nullable=True)
    received_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    opened_date = Column(DateTime, nullable=True)
    status = Column(String, default="Active")  # Active, Expired, Exhausted
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class VolumetricSolution(Base):
    __tablename__ = "volumetric_solutions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    concentration = Column(String, nullable=True)  # 0.1N, 0.5M, etc.
    prepared_by = Column(String, nullable=True)
    prepared_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    standardization_factor = Column(Float, nullable=True)
    standardized_by = Column(String, nullable=True)
    standardized_date = Column(DateTime, nullable=True)
    status = Column(String, default="Active")  # Active, Expired
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SAPIntegrationLog(Base):
    """Tracks all SAP integration transactions"""
    __tablename__ = "sap_integration_logs"

    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String, nullable=False)  # BATCH_READ, USAGE_DECISION, STATUS_CHANGE, QTY_POST, CERT_STATUS
    direction = Column(String, nullable=False)  # INBOUND, OUTBOUND
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=True)
    sap_inspection_lot = Column(String, nullable=True)
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    status = Column(String, default="Pending")  # Pending, Success, Failed
    error_message = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
