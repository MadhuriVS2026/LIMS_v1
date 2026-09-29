from sqlalchemy.orm import Session
from datetime import datetime
import json
from . import models, schemas, auth


def object_as_dict(obj):
    if obj is None:
        return None
    d = {}
    for c in obj.__table__.columns:
        val = getattr(obj, c.name)
        if isinstance(val, datetime):
            d[c.name] = val.isoformat()
        else:
            d[c.name] = val
    return d


def write_audit_log(db: Session, username: str, user_id: int, action: str, table_name: str, record_id: int, old_values=None, new_values=None, comments=None):
    log_entry = models.AuditLog(
        user_id=user_id, username=username, action=action,
        table_name=table_name, record_id=record_id,
        old_values=old_values, new_values=new_values, comments=comments
    )
    db.add(log_entry)
    db.commit()

# ==================== USER OPERATIONS ====================
def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user_in: schemas.UserCreate, creator_name: str, creator_id: int):
    hashed_pwd = auth.get_password_hash(user_in.password)
    db_user = models.User(
        username=user_in.username, hashed_password=hashed_pwd,
        full_name=user_in.full_name, role=user_in.role,
        email=user_in.email, department=user_in.department, is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    write_audit_log(db, creator_name, creator_id, "CREATE", "users", db_user.id,
                    new_values={"username": db_user.username, "role": db_user.role})
    return db_user

# ==================== TEST OPERATIONS ====================
def create_test(db: Session, test_in: schemas.TestCreate, creator_name: str, creator_id: int):
    db_test = models.Test(
        code=test_in.code, name=test_in.name, type=test_in.type,
        unit=test_in.unit, method_no=test_in.method_no,
        category=test_in.category, technique=test_in.technique, status="Active"
    )
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    write_audit_log(db, creator_name, creator_id, "CREATE", "tests", db_test.id, new_values=object_as_dict(db_test))
    return db_test

# ==================== PRODUCT OPERATIONS ====================
def create_product(db: Session, prod_in: schemas.ProductCreate, creator_name: str, creator_id: int):
    db_prod = models.Product(
        code=prod_in.code, name=prod_in.name, description=prod_in.description,
        material_type=prod_in.material_type, retest_period_days=prod_in.retest_period_days,
        storage_condition=prod_in.storage_condition,
        status="Pending Approval", created_by=creator_name
    )
    db.add(db_prod)
    db.commit()
    db.refresh(db_prod)
    write_audit_log(db, creator_name, creator_id, "CREATE", "products", db_prod.id, new_values=object_as_dict(db_prod))
    return db_prod

def approve_product(db: Session, product_id: int, approver_name: str, approver_id: int, comments: str = None):
    prod = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not prod:
        return None
    old_state = object_as_dict(prod)
    prod.status = "Active"
    prod.approved_by = approver_name
    prod.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(prod)
    write_audit_log(db, approver_name, approver_id, "APPROVE", "products", prod.id,
                    old_values=old_state, new_values=object_as_dict(prod), comments=comments)
    return prod

# ==================== SPECIFICATION OPERATIONS ====================
def create_specification(db: Session, spec_in: schemas.SpecCreate, creator_name: str, creator_id: int):
    existing_specs = db.query(models.Specification).filter(models.Specification.product_id == spec_in.product_id).all()
    version = len(existing_specs) + 1
    db_spec = models.Specification(
        product_id=spec_in.product_id, version=version,
        spec_type=spec_in.spec_type, document_no=spec_in.document_no,
        status="Pending Approval", created_by=creator_name
    )
    db.add(db_spec)
    db.commit()
    db.refresh(db_spec)
    for test_item in spec_in.tests:
        db_spec_test = models.SpecificationTest(
            specification_id=db_spec.id, test_id=test_item.test_id,
            min_limit=test_item.min_limit, max_limit=test_item.max_limit,
            expected_result=test_item.expected_result,
            display_in_coa=test_item.display_in_coa if test_item.display_in_coa is not None else True
        )
        db.add(db_spec_test)
    db.commit()
    db.refresh(db_spec)
    write_audit_log(db, creator_name, creator_id, "CREATE", "specifications", db_spec.id,
                    new_values={"product_id": db_spec.product_id, "version": db_spec.version})
    return db_spec

def approve_specification(db: Session, spec_id: int, approver_name: str, approver_id: int, comments: str = None):
    spec = db.query(models.Specification).filter(models.Specification.id == spec_id).first()
    if not spec:
        return None
    old_state = object_as_dict(spec)
    db.query(models.Specification).filter(
        models.Specification.product_id == spec.product_id,
        models.Specification.status == "Active"
    ).update({"status": "Inactive"})
    spec.status = "Active"
    spec.approved_by = approver_name
    spec.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(spec)
    write_audit_log(db, approver_name, approver_id, "APPROVE", "specifications", spec.id,
                    old_values=old_state, new_values=object_as_dict(spec), comments=comments)
    return spec

# ==================== SAMPLE OPERATIONS ====================
def create_sample(db: Session, sample_in: schemas.SampleCreate, creator_name: str, creator_id: int):
    spec = db.query(models.Specification).filter(
        models.Specification.product_id == sample_in.product_id,
        models.Specification.status == "Active"
    ).first()
    if not spec:
        raise ValueError("No active specification found for this product.")
    date_str = datetime.utcnow().strftime("%Y%m%d")
    todays_samples = db.query(models.Sample).filter(models.Sample.sample_code.like(f"SMP-{date_str}-%")).count()
    sample_code = f"SMP-{date_str}-{todays_samples + 1:04d}"
    db_sample = models.Sample(
        sample_code=sample_code, product_id=sample_in.product_id,
        batch_number=sample_in.batch_number, quantity_received=sample_in.quantity_received,
        unit=sample_in.unit, sample_type=sample_in.sample_type, priority=sample_in.priority or "Normal",
        sap_inspection_lot=sample_in.sap_inspection_lot, sap_material=sample_in.sap_material,
        sap_plant=sample_in.sap_plant, sap_vendor=sample_in.sap_vendor,
        sap_vendor_batch=sample_in.sap_vendor_batch,
        manufacturing_date=sample_in.manufacturing_date, expiry_date=sample_in.expiry_date,
        status="Logged", logged_by=creator_name, logged_at=datetime.utcnow()
    )
    db.add(db_sample)
    db.commit()
    db.refresh(db_sample)
    for spec_test in spec.tests:
        db_res = models.SampleResult(
            sample_id=db_sample.id, test_id=spec_test.test_id,
            min_limit=spec_test.min_limit, max_limit=spec_test.max_limit,
            expected_result=spec_test.expected_result, status="Pending", is_oos=False
        )
        db.add(db_res)
    db.commit()
    db.refresh(db_sample)
    write_audit_log(db, creator_name, creator_id, "CREATE", "samples", db_sample.id, new_values=object_as_dict(db_sample))
    return db_sample

def receive_sample(db: Session, sample_id: int, username: str, user_id: int):
    sample = db.query(models.Sample).filter(models.Sample.id == sample_id).first()
    if not sample:
        return None
    old_state = object_as_dict(sample)
    sample.status = "Received"
    sample.received_by = username
    sample.received_at = datetime.utcnow()
    db.commit()
    db.refresh(sample)
    write_audit_log(db, username, user_id, "RECEIVE", "samples", sample.id, old_values=old_state, new_values=object_as_dict(sample))
    return sample

# ==================== RESULT OPERATIONS ====================
def submit_sample_result(db: Session, result_id: int, result_in: schemas.SampleResultBase, analyst_name: str, analyst_id: int, comments: str = None):
    res = db.query(models.SampleResult).filter(models.SampleResult.id == result_id).first()
    if not res:
        return None
    old_state = object_as_dict(res)
    res.result_value = result_in.result_value
    res.result_text = result_in.result_text
    res.status = "Submitted"
    res.analyst_id = analyst_id
    res.submitted_at = datetime.utcnow()
    is_oos = False
    if res.test.type == "Quantitative":
        if res.result_value is not None:
            if res.min_limit is not None and res.result_value < res.min_limit:
                is_oos = True
            if res.max_limit is not None and res.result_value > res.max_limit:
                is_oos = True
    else:
        if res.expected_result and res.result_text:
            if res.result_text.strip().lower() != res.expected_result.strip().lower():
                is_oos = True
    res.is_oos = is_oos
    db.commit()
    db.refresh(res)
    write_audit_log(db, analyst_name, analyst_id, "SUBMIT_RESULT", "sample_results", res.id,
                    old_values=old_state, new_values=object_as_dict(res), comments=f"E-Signed by {analyst_name}")
    sample = res.sample
    if is_oos:
        sample.status = "OOS Investigation"
        db.commit()
        existing_oos = db.query(models.OOSInvestigation).filter(
            models.OOSInvestigation.sample_id == sample.id,
            models.OOSInvestigation.test_id == res.test_id
        ).first()
        if not existing_oos:
            oos = models.OOSInvestigation(
                sample_id=sample.id, test_id=res.test_id,
                phase1_comments=f"Auto-generated: value '{res.result_value or res.result_text}' out of specification.",
                status="Open", created_by="System"
            )
            db.add(oos)
            db.commit()
            db.refresh(oos)
            res.oos_investigation_id = oos.id
            db.commit()
            write_audit_log(db, "System", 0, "CREATE", "oos_investigations", oos.id, comments="Auto-triggered OOS")
    else:
        all_results = db.query(models.SampleResult).filter(models.SampleResult.sample_id == sample.id).all()
        if all(r.status in ["Submitted", "Approved"] for r in all_results):
            sample.status = "OOS Investigation" if any(r.is_oos for r in all_results) else "Under Review"
            db.commit()
    return res

def review_sample_result(db: Session, result_id: int, supervisor_name: str, supervisor_id: int, comments: str = None):
    res = db.query(models.SampleResult).filter(models.SampleResult.id == result_id).first()
    if not res:
        return None
    old_state = object_as_dict(res)
    res.status = "Approved"
    res.supervisor_id = supervisor_id
    res.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(res)
    write_audit_log(db, supervisor_name, supervisor_id, "REVIEW_RESULT", "sample_results", res.id,
                    old_values=old_state, new_values=object_as_dict(res), comments=comments)
    return res

# ==================== OOS OPERATIONS ====================
def update_oos_investigation(db: Session, oos_id: int, oos_in: schemas.OOSSubmitDetails, username: str, user_id: int):
    oos = db.query(models.OOSInvestigation).filter(models.OOSInvestigation.id == oos_id).first()
    if not oos:
        return None
    old_state = object_as_dict(oos)
    oos.root_cause = oos_in.root_cause
    oos.corrective_action = oos_in.corrective_action
    oos.status = "Closed"
    oos.closed_by = username
    oos.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(oos)
    write_audit_log(db, username, user_id, "CLOSE_OOS", "oos_investigations", oos.id,
                    old_values=old_state, new_values=object_as_dict(oos))
    open_oos = db.query(models.OOSInvestigation).filter(
        models.OOSInvestigation.sample_id == oos.sample_id,
        models.OOSInvestigation.status == "Open"
    ).all()
    if not open_oos:
        sample = db.query(models.Sample).filter(models.Sample.id == oos.sample_id).first()
        sample.status = "Under Review"
        db.commit()
    return oos

# ==================== BATCH RELEASE ====================
def release_sample(db: Session, sample_id: int, verdict: str, qa_name: str, qa_id: int, comments: str = None):
    sample = db.query(models.Sample).filter(models.Sample.id == sample_id).first()
    if not sample:
        return None
    if verdict not in ["Approved", "Rejected"]:
        raise ValueError("Verdict must be Approved or Rejected")
    old_state = object_as_dict(sample)
    sample.status = verdict
    sample.approved_by = qa_name
    sample.approved_at = datetime.utcnow()
    sample.coa_released_by = qa_name
    sample.coa_released_at = datetime.utcnow()
    results_snapshot = []
    for r in sample.results:
        results_snapshot.append({
            "test_code": r.test.code, "test_name": r.test.name,
            "min_limit": r.min_limit, "max_limit": r.max_limit,
            "expected_result": r.expected_result,
            "result_value": r.result_value, "result_text": r.result_text,
            "is_oos": r.is_oos
        })
    sample.coa_data = {
        "sample_code": sample.sample_code, "product_name": sample.product.name,
        "product_code": sample.product.code, "batch_number": sample.batch_number,
        "quantity_received": sample.quantity_received, "unit": sample.unit,
        "released_by": qa_name, "released_at": sample.coa_released_at.isoformat(),
        "verdict": verdict, "results": results_snapshot, "comments": comments
    }
    db.commit()
    db.refresh(sample)
    write_audit_log(db, qa_name, qa_id, "RELEASE_COA", "samples", sample.id,
                    old_values=old_state, new_values=object_as_dict(sample),
                    comments=f"Verdict: {verdict}. {comments or ''}")
    return sample

# ==================== INSTRUMENT OPERATIONS ====================
def create_instrument(db: Session, instr_in: schemas.InstrumentCreate, creator_name: str, creator_id: int):
    db_instr = models.Instrument(
        code=instr_in.code, name=instr_in.name, category=instr_in.category,
        manufacturer=instr_in.manufacturer, model_number=instr_in.model_number,
        serial_number=instr_in.serial_number, location=instr_in.location,
        calibration_frequency_days=instr_in.calibration_frequency_days,
        status="Active", created_by=creator_name
    )
    db.add(db_instr)
    db.commit()
    db.refresh(db_instr)
    write_audit_log(db, creator_name, creator_id, "CREATE", "instruments", db_instr.id, new_values=object_as_dict(db_instr))
    return db_instr

def record_calibration(db: Session, instrument_id: int, cal_in: schemas.InstrumentCalibrationCreate, username: str, user_id: int):
    instr = db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()
    if not instr:
        return None
    cal = models.InstrumentCalibration(
        instrument_id=instrument_id, calibration_date=cal_in.calibration_date,
        next_due_date=cal_in.next_due_date, performed_by=username,
        result=cal_in.result, certificate_no=cal_in.certificate_no, comments=cal_in.comments
    )
    db.add(cal)
    instr.last_calibrated_at = cal_in.calibration_date
    instr.last_calibrated_by = username
    instr.calibration_due_date = cal_in.next_due_date
    if cal_in.result == "Pass":
        instr.status = "Active"
        instr.qualification_status = "Qualified"
    db.commit()
    db.refresh(cal)
    write_audit_log(db, username, user_id, "CALIBRATE", "instruments", instr.id, comments=f"Result: {cal_in.result}")
    return cal

# ==================== STABILITY OPERATIONS ====================
def create_stability_protocol(db: Session, proto_in: schemas.StabilityProtocolCreate, creator_name: str, creator_id: int):
    count = db.query(models.StabilityProtocol).count()
    protocol_code = f"STAB-{count + 1:04d}"
    db_proto = models.StabilityProtocol(
        protocol_code=protocol_code, product_id=proto_in.product_id,
        condition=proto_in.condition, duration_months=proto_in.duration_months,
        study_type=proto_in.study_type, testing_frequency=proto_in.testing_frequency,
        status="Draft", created_by=creator_name
    )
    db.add(db_proto)
    db.commit()
    db.refresh(db_proto)
    write_audit_log(db, creator_name, creator_id, "CREATE", "stability_protocols", db_proto.id)
    return db_proto

def create_stability_sample(db: Session, ss_in: schemas.StabilitySampleCreate, creator_name: str, creator_id: int):
    db_ss = models.StabilitySample(
        protocol_id=ss_in.protocol_id, batch_number=ss_in.batch_number,
        time_point_months=ss_in.time_point_months, scheduled_date=ss_in.scheduled_date,
        status="Scheduled"
    )
    db.add(db_ss)
    db.commit()
    db.refresh(db_ss)
    write_audit_log(db, creator_name, creator_id, "CREATE", "stability_samples", db_ss.id)
    return db_ss

# ==================== RESOURCE MANAGER OPERATIONS ====================
def create_column(db: Session, col_in: schemas.ColumnCreate, creator_name: str, creator_id: int):
    db_col = models.ColumnMaster(
        code=col_in.code, name=col_in.name, type=col_in.type,
        manufacturer=col_in.manufacturer, dimensions=col_in.dimensions,
        serial_number=col_in.serial_number, instrument_id=col_in.instrument_id,
        max_injections=col_in.max_injections, status="Active", created_by=creator_name
    )
    db.add(db_col)
    db.commit()
    db.refresh(db_col)
    write_audit_log(db, creator_name, creator_id, "CREATE", "columns", db_col.id)
    return db_col

def create_reference_standard(db: Session, rs_in: schemas.ReferenceStandardCreate, creator_name: str, creator_id: int):
    db_rs = models.ReferenceStandard(
        code=rs_in.code, name=rs_in.name, lot_number=rs_in.lot_number,
        potency=rs_in.potency, manufacturer=rs_in.manufacturer,
        category=rs_in.category, storage_condition=rs_in.storage_condition,
        quantity_received=rs_in.quantity_received, quantity_remaining=rs_in.quantity_received,
        unit=rs_in.unit, received_date=rs_in.received_date, expiry_date=rs_in.expiry_date,
        status="Active", created_by=creator_name
    )
    db.add(db_rs)
    db.commit()
    db.refresh(db_rs)
    write_audit_log(db, creator_name, creator_id, "CREATE", "reference_standards", db_rs.id)
    return db_rs

def create_chemical(db: Session, chem_in: schemas.ChemicalReagentCreate, creator_name: str, creator_id: int):
    db_chem = models.ChemicalReagent(
        code=chem_in.code, name=chem_in.name, grade=chem_in.grade,
        manufacturer=chem_in.manufacturer, lot_number=chem_in.lot_number,
        cas_number=chem_in.cas_number, quantity_received=chem_in.quantity_received,
        quantity_remaining=chem_in.quantity_received, unit=chem_in.unit,
        storage_condition=chem_in.storage_condition,
        received_date=chem_in.received_date, expiry_date=chem_in.expiry_date,
        status="Active", created_by=creator_name
    )
    db.add(db_chem)
    db.commit()
    db.refresh(db_chem)
    write_audit_log(db, creator_name, creator_id, "CREATE", "chemicals_reagents", db_chem.id)
    return db_chem

def create_volumetric_solution(db: Session, vs_in: schemas.VolumetricSolutionCreate, creator_name: str, creator_id: int):
    db_vs = models.VolumetricSolution(
        code=vs_in.code, name=vs_in.name, concentration=vs_in.concentration,
        prepared_by=creator_name, prepared_date=vs_in.prepared_date,
        expiry_date=vs_in.expiry_date, standardization_factor=vs_in.standardization_factor,
        status="Active", created_by=creator_name
    )
    db.add(db_vs)
    db.commit()
    db.refresh(db_vs)
    write_audit_log(db, creator_name, creator_id, "CREATE", "volumetric_solutions", db_vs.id)
    return db_vs

# ==================== SAP INTEGRATION ====================
def sap_read_batch_data(db: Session, inspection_lot: str, username: str, user_id: int):
    """
    In production: calls SAP RFC ZLIMS_read_batch_data1 via pyrfc.
    For now: simulates the response and logs the transaction.
    """
    log = models.SAPIntegrationLog(
        transaction_type="BATCH_READ", direction="INBOUND",
        sap_inspection_lot=inspection_lot,
        request_payload={"inspection_lot": inspection_lot},
        status="Success", created_by=username, completed_at=datetime.utcnow()
    )
    # Simulated response (in production, this comes from SAP RFC)
    response = {
        "inspection_lot": inspection_lot,
        "material_number": f"MAT-{inspection_lot[-4:]}",
        "batch_number": f"B{inspection_lot[-6:]}",
        "manufacturing_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "expiry_date": "2027-12-31",
        "vendor_number": "V001",
        "vendor_name": "Simulated Vendor",
        "vendor_batch": f"VB-{inspection_lot[-4:]}",
        "canceled": False
    }
    log.response_payload = response
    db.add(log)
    db.commit()
    write_audit_log(db, username, user_id, "SAP_BATCH_READ", "sap_integration_logs", log.id,
                    comments=f"Read batch data for lot {inspection_lot}")
    return schemas.SAPBatchDataResponse(**response)

def sap_post_usage_decision(db: Session, req: schemas.SAPUsageDecisionRequest, username: str, user_id: int):
    """
    In production: calls SAP RFC ZLIMS_PROCESS_UD4 to post usage decision.
    Maps LIMS verdict to SAP UD codes and posts via BDC to QA11.
    """
    sample = db.query(models.Sample).filter(models.Sample.id == req.sample_id).first()
    if not sample:
        return schemas.SAPUsageDecisionResponse(success=False, message="Sample not found")
    if not sample.sap_inspection_lot:
        return schemas.SAPUsageDecisionResponse(success=False, message="No SAP inspection lot linked")
    log = models.SAPIntegrationLog(
        transaction_type="USAGE_DECISION", direction="OUTBOUND",
        sample_id=sample.id, sap_inspection_lot=sample.sap_inspection_lot,
        request_payload={
            "lot": sample.sap_inspection_lot, "ud_code": req.ud_code,
            "ud_code_group": req.ud_code_group, "text_line": req.text_line
        },
        status="Success", created_by=username, completed_at=datetime.utcnow()
    )
    # In production: call pyrfc connection to SAP
    # conn.call('ZLIMS_PROCESS_UD4', I_LOT=..., I_UD_CODE=..., ...)
    log.response_payload = {"message": "Usage Decision posted successfully (simulated)"}
    db.add(log)
    sample.sap_ud_posted = True
    sample.sap_ud_code = req.ud_code
    sample.sap_ud_posted_at = datetime.utcnow()
    db.commit()
    write_audit_log(db, username, user_id, "SAP_USAGE_DECISION", "samples", sample.id,
                    comments=f"UD Code: {req.ud_code} for lot {sample.sap_inspection_lot}")
    return schemas.SAPUsageDecisionResponse(
        success=True, message="Usage Decision posted successfully",
        inspection_lot=sample.sap_inspection_lot
    )
