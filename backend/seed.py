from datetime import datetime, timedelta
from .database import engine, Base, SessionLocal
from . import models, auth, crud


def seed_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Seeding Anti Gravity LIMS database...")

        # 1. Create Users
        users_data = [
            {"username": "admin", "password": "admin123", "full_name": "System Administrator", "role": "Admin", "department": "IT"},
            {"username": "analyst", "password": "analyst123", "full_name": "John Analyst", "role": "Analyst", "department": "QC"},
            {"username": "supervisor", "password": "super123", "full_name": "Jane Supervisor", "role": "Supervisor", "department": "QC"},
            {"username": "qa", "password": "qa123", "full_name": "Alice QualityAssurance", "role": "QA", "department": "QA"},
            {"username": "analyst2", "password": "analyst123", "full_name": "Bob Chemist", "role": "Analyst", "department": "QC"},
        ]
        for u in users_data:
            user = models.User(
                username=u["username"], hashed_password=auth.get_password_hash(u["password"]),
                full_name=u["full_name"], role=u["role"], department=u["department"], is_active=True
            )
            db.add(user)
        db.commit()
        print("  [OK] Users seeded")

        # 2. Create Tests
        tests_data = [
            {"code": "TST-01", "name": "Description", "type": "Qualitative", "unit": "", "category": "Physical", "technique": "Visual"},
            {"code": "TST-02", "name": "Identification by HPLC", "type": "Qualitative", "unit": "", "category": "Chemical", "technique": "HPLC"},
            {"code": "TST-03", "name": "Assay (Propofol)", "type": "Quantitative", "unit": "mg/mL", "category": "Chemical", "technique": "HPLC"},
            {"code": "TST-04", "name": "pH", "type": "Quantitative", "unit": "", "category": "Physical", "technique": "pH Meter"},
            {"code": "TST-05", "name": "Average Droplet Size", "type": "Quantitative", "unit": "nm", "category": "Physical", "technique": "DLS"},
            {"code": "TST-06", "name": "Sterility", "type": "Qualitative", "unit": "", "category": "Microbiological", "technique": "Membrane Filtration"},
        ]
        db_tests = []
        for t in tests_data:
            test = models.Test(code=t["code"], name=t["name"], type=t["type"], unit=t["unit"], category=t["category"], technique=t["technique"], status="Active")
            db.add(test)
            db_tests.append(test)
        db.commit()
        print("  [OK] Tests seeded")

        # 3. Create Product
        prod = models.Product(
            code="PRD-PROP-10", name="Propofol 1% (10mg/mL) Injectable Emulsion",
            description="Intravenous general anesthetic and sedation emulsion.",
            material_type="FG", retest_period_days=730,
            storage_condition="Store below 25°C. Do not freeze.",
            status="Active", created_by="System", approved_by="System", approved_at=datetime.utcnow()
        )
        db.add(prod)
        db.commit()
        print("  [OK] Product seeded")

        # 4. Create Specification
        spec = models.Specification(
            product_id=prod.id, version=1, spec_type="Release",
            status="Active", created_by="System", approved_by="System", approved_at=datetime.utcnow()
        )
        db.add(spec)
        db.commit()
        spec_tests_data = [
            {"test_id": db_tests[0].id, "expected_result": "Homogeneous white emulsion"},
            {"test_id": db_tests[1].id, "expected_result": "Complies"},
            {"test_id": db_tests[2].id, "min_limit": 9.0, "max_limit": 11.0},
            {"test_id": db_tests[3].id, "min_limit": 6.0, "max_limit": 8.5},
            {"test_id": db_tests[4].id, "min_limit": 0.0, "max_limit": 500.0},
            {"test_id": db_tests[5].id, "expected_result": "Complies"},
        ]
        for st in spec_tests_data:
            db.add(models.SpecificationTest(
                specification_id=spec.id, test_id=st["test_id"],
                min_limit=st.get("min_limit"), max_limit=st.get("max_limit"),
                expected_result=st.get("expected_result"), display_in_coa=True
            ))
        db.commit()
        print("  [OK] Specification seeded")

        # 5. Instruments
        instruments_data = [
            {"code": "HPLC-001", "name": "Agilent 1260 Infinity II", "category": "HPLC", "manufacturer": "Agilent", "model_number": "1260", "location": "Lab A - Room 101", "calibration_frequency_days": 365},
            {"code": "BAL-001", "name": "Mettler Toledo XPR205", "category": "Balance", "manufacturer": "Mettler Toledo", "model_number": "XPR205", "location": "Lab A - Room 102", "calibration_frequency_days": 180},
            {"code": "PH-001", "name": "Metrohm 827 pH Lab", "category": "pH Meter", "manufacturer": "Metrohm", "model_number": "827", "location": "Lab A - Room 101", "calibration_frequency_days": 30},
            {"code": "UV-001", "name": "Shimadzu UV-1900i", "category": "UV-Vis", "manufacturer": "Shimadzu", "model_number": "UV-1900i", "location": "Lab B - Room 201", "calibration_frequency_days": 365},
            {"code": "DLS-001", "name": "Malvern Zetasizer Nano ZS", "category": "DLS", "manufacturer": "Malvern", "model_number": "Nano ZS", "location": "Lab B - Room 202", "calibration_frequency_days": 365},
        ]
        for i in instruments_data:
            db.add(models.Instrument(
                code=i["code"], name=i["name"], category=i["category"],
                manufacturer=i["manufacturer"], model_number=i["model_number"],
                location=i["location"], calibration_frequency_days=i["calibration_frequency_days"],
                status="Active", qualification_status="Qualified",
                calibration_due_date=datetime.utcnow() + timedelta(days=i["calibration_frequency_days"]),
                last_calibrated_at=datetime.utcnow() - timedelta(days=30),
                created_by="System"
            ))
        db.commit()
        print("  [OK] Instruments seeded")

        # 6. Columns
        columns_data = [
            {"code": "COL-001", "name": "Hypersil BDS C18", "type": "C18", "manufacturer": "Thermo Fisher", "dimensions": "250x4.6mm, 5µm", "max_injections": 2000},
            {"code": "COL-002", "name": "XBridge C8", "type": "C8", "manufacturer": "Waters", "dimensions": "150x4.6mm, 3.5µm", "max_injections": 1500},
        ]
        for c in columns_data:
            db.add(models.ColumnMaster(code=c["code"], name=c["name"], type=c["type"], manufacturer=c["manufacturer"], dimensions=c["dimensions"], max_injections=c["max_injections"], status="Active", created_by="System"))
        db.commit()
        print("  [OK] Columns seeded")

        # 7. Reference Standards
        ref_stds = [
            {"code": "RS-001", "name": "Propofol Reference Standard", "lot_number": "LOT-2024-A1", "potency": 99.8, "manufacturer": "USP", "category": "Primary", "quantity_received": 100.0, "unit": "mg", "expiry_date": datetime(2027, 12, 31)},
            {"code": "RS-002", "name": "Propofol Related Compound A", "lot_number": "LOT-2024-B2", "potency": 99.5, "manufacturer": "USP", "category": "Primary", "quantity_received": 50.0, "unit": "mg", "expiry_date": datetime(2027, 6, 30)},
        ]
        for rs in ref_stds:
            db.add(models.ReferenceStandard(code=rs["code"], name=rs["name"], lot_number=rs["lot_number"], potency=rs["potency"], manufacturer=rs["manufacturer"], category=rs["category"], quantity_received=rs["quantity_received"], quantity_remaining=rs["quantity_received"], unit=rs["unit"], expiry_date=rs["expiry_date"], status="Active", created_by="System"))
        db.commit()
        print("  [OK] Reference Standards seeded")

        # 8. Chemicals
        chemicals = [
            {"code": "CHM-001", "name": "Acetonitrile", "grade": "HPLC", "manufacturer": "Merck", "cas_number": "75-05-8", "quantity_received": 2500.0, "unit": "mL"},
            {"code": "CHM-002", "name": "Methanol", "grade": "HPLC", "manufacturer": "Merck", "cas_number": "67-56-1", "quantity_received": 2500.0, "unit": "mL"},
            {"code": "CHM-003", "name": "Phosphoric Acid", "grade": "AR", "manufacturer": "Rankem", "cas_number": "7664-38-2", "quantity_received": 500.0, "unit": "mL"},
        ]
        for ch in chemicals:
            db.add(models.ChemicalReagent(code=ch["code"], name=ch["name"], grade=ch["grade"], manufacturer=ch["manufacturer"], cas_number=ch["cas_number"], quantity_received=ch["quantity_received"], quantity_remaining=ch["quantity_received"], unit=ch["unit"], status="Active", expiry_date=datetime(2027, 12, 31), created_by="System"))
        db.commit()
        print("  [OK] Chemicals seeded")

        # 9. Volumetric Solutions
        db.add(models.VolumetricSolution(code="VS-001", name="0.1N Sodium Hydroxide", concentration="0.1N", prepared_by="System", prepared_date=datetime.utcnow(), expiry_date=datetime.utcnow() + timedelta(days=30), standardization_factor=1.002, standardized_by="System", standardized_date=datetime.utcnow(), status="Active", created_by="System"))
        db.add(models.VolumetricSolution(code="VS-002", name="0.1N Hydrochloric Acid", concentration="0.1N", prepared_by="System", prepared_date=datetime.utcnow(), expiry_date=datetime.utcnow() + timedelta(days=30), standardization_factor=0.998, standardized_by="System", standardized_date=datetime.utcnow(), status="Active", created_by="System"))
        db.commit()
        print("  [OK] Volumetric Solutions seeded")

        # 10. Stability Protocol
        proto = models.StabilityProtocol(protocol_code="STAB-0001", product_id=prod.id, condition="25°C/60%RH", duration_months=24, study_type="Long Term", testing_frequency="0,3,6,9,12,18,24", status="Active", created_by="System", approved_by="System", approved_at=datetime.utcnow())
        db.add(proto)
        db.commit()
        print("  [OK] Stability Protocol seeded")

        # 11. Audit log
        crud.write_audit_log(db, "System", 0, "SEED", "database", 0, comments="Database seeded with complete LIMS data.")
        print("\n  *** Seeding completed successfully! ***")
        print("  Users: admin/admin123, analyst/analyst123, supervisor/super123, qa/qa123")

    finally:
        db.close()


if __name__ == "__main__":
    seed_db()
