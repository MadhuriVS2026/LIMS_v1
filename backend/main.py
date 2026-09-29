from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from starlette.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
import os
from .database import engine, get_db, Base
from . import models, schemas, auth, crud

app = FastAPI(title="Anti Gravity LIMS", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

def check_esign(user: models.User, password: str):
    if not auth.verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Electronic signature verification failed: Invalid password."
        )

# ==================== AUTH ENDPOINTS ====================
@app.post("/api/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if user.locked_until and user.locked_until > datetime.datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked. Try again later.")
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.datetime.utcnow()
    db.commit()
    access_token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    crud.write_audit_log(db, user.username, user.id, "LOGIN", "users", user.id, comments="User logged in")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

# ==================== USER MANAGEMENT ====================
@app.get("/api/users", response_model=List[schemas.UserResponse])
def list_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin"]))):
    return db.query(models.User).all()

@app.post("/api/users", response_model=schemas.UserResponse)
def create_user(user_in: schemas.UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin"]))):
    existing = crud.get_user_by_username(db, user_in.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    return crud.create_user(db, user_in, current_user.username, current_user.id)

@app.put("/api/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin"]))):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_update.full_name is not None: user.full_name = user_update.full_name
    if user_update.role is not None: user.role = user_update.role
    if user_update.email is not None: user.email = user_update.email
    if user_update.department is not None: user.department = user_update.department
    if user_update.is_active is not None: user.is_active = user_update.is_active
    db.commit()
    db.refresh(user)
    crud.write_audit_log(db, current_user.username, current_user.id, "UPDATE", "users", user.id)
    return user

@app.post("/api/auth/change-password")
def change_password(pwd: schemas.PasswordChange, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not auth.verify_password(pwd.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = auth.get_password_hash(pwd.new_password)
    current_user.password_changed_at = datetime.datetime.utcnow()
    db.commit()
    return {"message": "Password changed successfully"}

# ==================== DASHBOARD ====================
@app.get("/api/dashboard", response_model=schemas.DashboardStats)
def get_dashboard(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    today = datetime.datetime.utcnow().date()
    total_samples = db.query(models.Sample).count()
    pending = db.query(models.Sample).filter(models.Sample.status.in_(["Logged", "Received", "Under Review"])).count()
    oos_open = db.query(models.OOSInvestigation).filter(models.OOSInvestigation.status == "Open").count()
    samples_today = db.query(models.Sample).filter(models.Sample.logged_at >= datetime.datetime.combine(today, datetime.time.min)).count()
    instruments_due = db.query(models.Instrument).filter(
        models.Instrument.calibration_due_date <= datetime.datetime.utcnow() + datetime.timedelta(days=7)
    ).count()
    pending_reviews = db.query(models.SampleResult).filter(models.SampleResult.status == "Submitted").count()
    approved_today = db.query(models.Sample).filter(
        models.Sample.status == "Approved",
        models.Sample.approved_at >= datetime.datetime.combine(today, datetime.time.min)
    ).count()
    rejected_today = db.query(models.Sample).filter(
        models.Sample.status == "Rejected",
        models.Sample.approved_at >= datetime.datetime.combine(today, datetime.time.min)
    ).count()
    return schemas.DashboardStats(
        total_samples=total_samples, pending_samples=pending, oos_open=oos_open,
        samples_today=samples_today, instruments_due_calibration=instruments_due,
        pending_reviews=pending_reviews, approved_today=approved_today, rejected_today=rejected_today
    )

# ==================== AUDIT LOGS ====================
@app.get("/api/audit-logs", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

# ==================== TESTS ====================
@app.get("/api/tests", response_model=List[schemas.TestResponse])
def read_tests(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Test).all()

@app.post("/api/tests", response_model=schemas.TestResponse)
def create_test(test_in: schemas.TestCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin"]))):
    return crud.create_test(db, test_in, current_user.username, current_user.id)

# ==================== PRODUCTS ====================
@app.get("/api/products", response_model=List[schemas.ProductResponse])
def read_products(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Product).all()

@app.post("/api/products", response_model=schemas.ProductResponse)
def create_product(prod_in: schemas.ProductCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin"]))):
    return crud.create_product(db, prod_in, current_user.username, current_user.id)

@app.post("/api/products/{id}/approve", response_model=schemas.ProductResponse)
def approve_product(id: int, esign: schemas.ESignRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Supervisor", "QA"]))):
    check_esign(current_user, esign.password)
    prod = crud.approve_product(db, id, current_user.username, current_user.id, esign.comments)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return prod

# ==================== SPECIFICATIONS ====================
@app.get("/api/specifications", response_model=List[schemas.SpecResponse])
def read_specifications(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Specification).all()

@app.post("/api/specifications", response_model=schemas.SpecResponse)
def create_specification(spec_in: schemas.SpecCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin"]))):
    return crud.create_specification(db, spec_in, current_user.username, current_user.id)

@app.post("/api/specifications/{id}/approve", response_model=schemas.SpecResponse)
def approve_specification(id: int, esign: schemas.ESignRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Supervisor", "QA"]))):
    check_esign(current_user, esign.password)
    spec = crud.approve_specification(db, id, current_user.username, current_user.id, esign.comments)
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")
    return spec

# ==================== SAMPLES ====================
@app.get("/api/samples", response_model=List[schemas.SampleResponse])
def read_samples(status: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    q = db.query(models.Sample)
    if status:
        q = q.filter(models.Sample.status == status)
    return q.order_by(models.Sample.logged_at.desc()).all()

@app.post("/api/samples", response_model=schemas.SampleResponse)
def create_sample(sample_in: schemas.SampleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin", "Analyst"]))):
    try:
        return crud.create_sample(db, sample_in, current_user.username, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/samples/{id}/receive", response_model=schemas.SampleResponse)
def receive_sample(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Analyst", "Supervisor"]))):
    sample = crud.receive_sample(db, id, current_user.username, current_user.id)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    return sample

# ==================== RESULTS ====================
@app.post("/api/results/{id}/submit", response_model=schemas.SampleResultResponse)
def submit_result(id: int, result_submit: schemas.SampleResultSubmit, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Analyst"]))):
    check_esign(current_user, result_submit.password)
    result_in = schemas.SampleResultBase(result_value=result_submit.result_value, result_text=result_submit.result_text)
    res = crud.submit_sample_result(db, id, result_in, current_user.username, current_user.id, result_submit.password)
    if not res:
        raise HTTPException(status_code=404, detail="Sample result record not found")
    return res

@app.post("/api/results/{id}/review", response_model=schemas.SampleResultResponse)
def review_result(id: int, esign: schemas.ESignRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Supervisor"]))):
    check_esign(current_user, esign.password)
    res = crud.review_sample_result(db, id, current_user.username, current_user.id, esign.comments)
    if not res:
        raise HTTPException(status_code=404, detail="Sample result record not found")
    return res

# ==================== OOS ====================
@app.get("/api/oos", response_model=List[schemas.OOSResponse])
def read_oos(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.OOSInvestigation).order_by(models.OOSInvestigation.created_at.desc()).all()

@app.post("/api/oos/{id}/close", response_model=schemas.OOSResponse)
def close_oos(id: int, oos_details: schemas.OOSSubmitDetails, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Supervisor", "QA"]))):
    check_esign(current_user, oos_details.password)
    oos = crud.update_oos_investigation(db, id, oos_details, current_user.username, current_user.id)
    if not oos:
        raise HTTPException(status_code=404, detail="OOS Record not found")
    return oos

# ==================== BATCH RELEASE ====================
@app.post("/api/samples/{id}/release", response_model=schemas.SampleResponse)
def release_batch(id: int, verdict: str = Query(...), esign: Optional[schemas.ESignRequest] = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["QA"]))):
    if esign and esign.password:
        check_esign(current_user, esign.password)
    try:
        sample = crud.release_sample(db, id, verdict, current_user.username, current_user.id, esign.comments if esign else None)
        if not sample:
            raise HTTPException(status_code=404, detail="Sample not found")
        return sample
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== INSTRUMENTS ====================
@app.get("/api/instruments", response_model=List[schemas.InstrumentResponse])
def read_instruments(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Instrument).all()

@app.post("/api/instruments", response_model=schemas.InstrumentResponse)
def create_instrument(instr_in: schemas.InstrumentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin"]))):
    return crud.create_instrument(db, instr_in, current_user.username, current_user.id)

@app.post("/api/instruments/{id}/calibrate", response_model=schemas.InstrumentCalibrationResponse)
def calibrate_instrument(id: int, cal_in: schemas.InstrumentCalibrationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin", "Analyst"]))):
    return crud.record_calibration(db, id, cal_in, current_user.username, current_user.id)

# ==================== STABILITY ====================
@app.get("/api/stability/protocols", response_model=List[schemas.StabilityProtocolResponse])
def read_stability_protocols(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.StabilityProtocol).all()

@app.post("/api/stability/protocols", response_model=schemas.StabilityProtocolResponse)
def create_stability_protocol(proto_in: schemas.StabilityProtocolCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin", "Supervisor"]))):
    return crud.create_stability_protocol(db, proto_in, current_user.username, current_user.id)

@app.get("/api/stability/samples", response_model=List[schemas.StabilitySampleResponse])
def read_stability_samples(protocol_id: Optional[int] = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    q = db.query(models.StabilitySample)
    if protocol_id:
        q = q.filter(models.StabilitySample.protocol_id == protocol_id)
    return q.all()

@app.post("/api/stability/samples", response_model=schemas.StabilitySampleResponse)
def create_stability_sample(ss_in: schemas.StabilitySampleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin", "Analyst"]))):
    return crud.create_stability_sample(db, ss_in, current_user.username, current_user.id)

# ==================== COLUMNS ====================
@app.get("/api/columns", response_model=List[schemas.ColumnResponse])
def read_columns(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.ColumnMaster).all()

@app.post("/api/columns", response_model=schemas.ColumnResponse)
def create_column(col_in: schemas.ColumnCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin"]))):
    return crud.create_column(db, col_in, current_user.username, current_user.id)

# ==================== REFERENCE STANDARDS ====================
@app.get("/api/reference-standards", response_model=List[schemas.ReferenceStandardResponse])
def read_reference_standards(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.ReferenceStandard).all()

@app.post("/api/reference-standards", response_model=schemas.ReferenceStandardResponse)
def create_reference_standard(rs_in: schemas.ReferenceStandardCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin"]))):
    return crud.create_reference_standard(db, rs_in, current_user.username, current_user.id)

# ==================== CHEMICALS/REAGENTS ====================
@app.get("/api/chemicals", response_model=List[schemas.ChemicalReagentResponse])
def read_chemicals(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.ChemicalReagent).all()

@app.post("/api/chemicals", response_model=schemas.ChemicalReagentResponse)
def create_chemical(chem_in: schemas.ChemicalReagentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin"]))):
    return crud.create_chemical(db, chem_in, current_user.username, current_user.id)

# ==================== VOLUMETRIC SOLUTIONS ====================
@app.get("/api/volumetric-solutions", response_model=List[schemas.VolumetricSolutionResponse])
def read_volumetric_solutions(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.VolumetricSolution).all()

@app.post("/api/volumetric-solutions", response_model=schemas.VolumetricSolutionResponse)
def create_volumetric_solution(vs_in: schemas.VolumetricSolutionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin", "Analyst"]))):
    return crud.create_volumetric_solution(db, vs_in, current_user.username, current_user.id)

# ==================== SAP INTEGRATION ====================
@app.post("/api/sap/read-batch", response_model=schemas.SAPBatchDataResponse)
def sap_read_batch(req: schemas.SAPBatchDataRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin", "Analyst"]))):
    """Simulate reading batch data from SAP (in production, calls RFC)"""
    result = crud.sap_read_batch_data(db, req.inspection_lot, current_user.username, current_user.id)
    return result

@app.post("/api/sap/usage-decision", response_model=schemas.SAPUsageDecisionResponse)
def sap_usage_decision(req: schemas.SAPUsageDecisionRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["QA"]))):
    """Post usage decision to SAP QM (in production, calls RFC ZLIMS_PROCESS_UD4)"""
    check_esign(current_user, req.password)
    result = crud.sap_post_usage_decision(db, req, current_user.username, current_user.id)
    return result

@app.get("/api/sap/logs", response_model=List[schemas.SAPIntegrationLogResponse])
def sap_integration_logs(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role(["Admin", "QA"]))):
    return db.query(models.SAPIntegrationLog).order_by(models.SAPIntegrationLog.created_at.desc()).limit(100).all()

# ==================== COA PDF ====================
@app.get("/api/samples/{id}/coa")
def get_coa(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Generate COA data for a released sample"""
    sample = db.query(models.Sample).filter(models.Sample.id == id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    if sample.status not in ["Approved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Sample not yet released")
    if not sample.coa_data:
        raise HTTPException(status_code=400, detail="COA data not available")
    return sample.coa_data

# Mount Frontend - MUST be last
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(os.path.join(frontend_path, "index.html")):
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))
    
    @app.get("/app.js")
    async def serve_js():
        return FileResponse(os.path.join(frontend_path, "app.js"))
