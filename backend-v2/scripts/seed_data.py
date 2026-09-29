"""
Seed script for Anti Gravity LIMS (Enterprise Architecture).
Creates baseline users, tests, product, specification, and Resource Manager data.

Usage: python -m scripts.seed_data   (run from backend-v2/)
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from src.infrastructure.database.models.base_model import Base
from src.infrastructure.database.session import engine, async_session_factory
from src.infrastructure.database.models.user_model import UserModel
from src.infrastructure.database.models.test_model import TestModel
from src.infrastructure.database.models.product_model import ProductModel
from src.infrastructure.database.models.specification_model import (
    SpecificationModel,
    SpecificationTestModel,
)
from src.infrastructure.database.models.instrument_model import InstrumentModel
from src.infrastructure.database.models.resource_models import (
    ChemicalReagentModel,
    ColumnMasterModel,
    ReferenceStandardModel,
    VolumetricSolutionModel,
)
from src.infrastructure.database.models.stability_model import StabilityProtocolModel
from src.infrastructure.database.models.audit_log_model import AuditLogModel
from src.infrastructure.security.password_encoder import hash_password


async def seed() -> None:
    print("Resetting database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        print("Seeding users...")
        users_data = [
            ("admin", "admin123", "System Administrator", "Admin", "IT"),
            ("analyst", "analyst123", "John Analyst", "Analyst", "QC"),
            ("supervisor", "super123", "Jane Supervisor", "Supervisor", "QC"),
            ("qa", "qa123", "Alice QualityAssurance", "QA", "QA"),
            ("analyst2", "analyst123", "Bob Chemist", "Analyst", "QC"),
        ]
        for username, password, full_name, role, department in users_data:
            session.add(UserModel(
                username=username, password_hash=hash_password(password),
                full_name=full_name, role=role, department=department, is_active=True,
            ))
        await session.commit()

        print("Seeding test parameters...")
        tests_data = [
            ("TST-01", "Description", "Qualitative", "", "Physical", "Visual"),
            ("TST-02", "Identification by HPLC", "Qualitative", "", "Chemical", "HPLC"),
            ("TST-03", "Assay (Propofol)", "Quantitative", "mg/mL", "Chemical", "HPLC"),
            ("TST-04", "pH", "Quantitative", "", "Physical", "pH Meter"),
            ("TST-05", "Average Droplet Size", "Quantitative", "nm", "Physical", "DLS"),
            ("TST-06", "Sterility", "Qualitative", "", "Microbiological", "Membrane Filtration"),
        ]
        test_ids = []
        for code, name, type_, unit, category, technique in tests_data:
            t = TestModel(code=code, name=name, type=type_, unit=unit, category=category,
                           technique=technique, status="Active")
            session.add(t)
            await session.flush()
            test_ids.append(t.id)
        await session.commit()

        print("Seeding product...")
        product = ProductModel(
            code="PRD-PROP-10", name="Propofol 1% (10mg/mL) Injectable Emulsion",
            description="Intravenous general anesthetic and sedation emulsion.",
            material_type="FG", retest_period_days=730,
            storage_condition="Store below 25°C. Do not freeze.",
            status="Active", created_by="System", approved_by="System",
            approved_at=datetime.now(timezone.utc),
        )
        session.add(product)
        await session.flush()
        await session.commit()

        print("Seeding specification...")
        spec = SpecificationModel(
            product_id=product.id, version=1, spec_type="Release", status="Active",
            created_by="System", approved_by="System", approved_at=datetime.now(timezone.utc),
        )
        session.add(spec)
        await session.flush()

        spec_tests = [
            (test_ids[0], None, None, "Homogeneous white emulsion"),
            (test_ids[1], None, None, "Complies"),
            (test_ids[2], 9.0, 11.0, None),
            (test_ids[3], 6.0, 8.5, None),
            (test_ids[4], 0.0, 500.0, None),
            (test_ids[5], None, None, "Complies"),
        ]
        for test_id, min_l, max_l, expected in spec_tests:
            session.add(SpecificationTestModel(
                specification_id=spec.id, test_id=test_id, min_limit=min_l,
                max_limit=max_l, expected_result=expected, display_in_coa=True,
            ))
        await session.commit()

        print("Seeding instruments...")
        instruments_data = [
            ("HPLC-001", "Agilent 1260 Infinity II", "HPLC", "Agilent", "1260", "Lab A - Room 101", 365),
            ("BAL-001", "Mettler Toledo XPR205", "Balance", "Mettler Toledo", "XPR205", "Lab A - Room 102", 180),
            ("PH-001", "Metrohm 827 pH Lab", "pH Meter", "Metrohm", "827", "Lab A - Room 101", 30),
            ("UV-001", "Shimadzu UV-1900i", "UV-Vis", "Shimadzu", "UV-1900i", "Lab B - Room 201", 365),
            ("DLS-001", "Malvern Zetasizer Nano ZS", "DLS", "Malvern", "Nano ZS", "Lab B - Room 202", 365),
        ]
        for code, name, category, mfr, model, location, freq in instruments_data:
            session.add(InstrumentModel(
                code=code, name=name, category=category, manufacturer=mfr, model_number=model,
                location=location, calibration_frequency_days=freq, status="Active",
                qualification_status="Qualified",
                calibration_due_date=datetime.now(timezone.utc) + timedelta(days=freq),
                last_calibrated_at=datetime.now(timezone.utc) - timedelta(days=30),
                created_by="System",
            ))
        await session.commit()

        print("Seeding columns, reference standards, chemicals, volumetric solutions...")
        session.add(ColumnMasterModel(code="COL-001", name="Hypersil BDS C18", type="C18",
                    manufacturer="Thermo Fisher", dimensions="250x4.6mm, 5µm", max_injections=2000,
                    status="Active", created_by="System"))
        session.add(ColumnMasterModel(code="COL-002", name="XBridge C8", type="C8",
                    manufacturer="Waters", dimensions="150x4.6mm, 3.5µm", max_injections=1500,
                    status="Active", created_by="System"))

        session.add(ReferenceStandardModel(code="RS-001", name="Propofol Reference Standard",
                    lot_number="LOT-2024-A1", potency=99.8, manufacturer="USP", category="Primary",
                    quantity_received=100.0, quantity_remaining=100.0, unit="mg",
                    expiry_date=datetime(2027, 12, 31, tzinfo=timezone.utc), status="Active", created_by="System"))
        session.add(ReferenceStandardModel(code="RS-002", name="Propofol Related Compound A",
                    lot_number="LOT-2024-B2", potency=99.5, manufacturer="USP", category="Primary",
                    quantity_received=50.0, quantity_remaining=50.0, unit="mg",
                    expiry_date=datetime(2027, 6, 30, tzinfo=timezone.utc), status="Active", created_by="System"))

        session.add(ChemicalReagentModel(code="CHM-001", name="Acetonitrile", grade="HPLC",
                    manufacturer="Merck", cas_number="75-05-8", quantity_received=2500.0,
                    quantity_remaining=2500.0, unit="mL", status="Active",
                    expiry_date=datetime(2027, 12, 31, tzinfo=timezone.utc), created_by="System"))
        session.add(ChemicalReagentModel(code="CHM-002", name="Methanol", grade="HPLC",
                    manufacturer="Merck", cas_number="67-56-1", quantity_received=2500.0,
                    quantity_remaining=2500.0, unit="mL", status="Active",
                    expiry_date=datetime(2027, 12, 31, tzinfo=timezone.utc), created_by="System"))
        session.add(ChemicalReagentModel(code="CHM-003", name="Phosphoric Acid", grade="AR",
                    manufacturer="Rankem", cas_number="7664-38-2", quantity_received=500.0,
                    quantity_remaining=500.0, unit="mL", status="Active",
                    expiry_date=datetime(2027, 12, 31, tzinfo=timezone.utc), created_by="System"))

        now = datetime.now(timezone.utc)
        session.add(VolumetricSolutionModel(code="VS-001", name="0.1N Sodium Hydroxide",
                    concentration="0.1N", prepared_by="System", prepared_date=now,
                    expiry_date=now + timedelta(days=30), standardization_factor=1.002,
                    standardized_by="System", standardized_date=now, status="Active", created_by="System"))
        session.add(VolumetricSolutionModel(code="VS-002", name="0.1N Hydrochloric Acid",
                    concentration="0.1N", prepared_by="System", prepared_date=now,
                    expiry_date=now + timedelta(days=30), standardization_factor=0.998,
                    standardized_by="System", standardized_date=now, status="Active", created_by="System"))

        session.add(StabilityProtocolModel(protocol_code="STAB-0001", product_id=product.id,
                    condition="25°C/60%RH", duration_months=24, study_type="Long Term",
                    testing_frequency="0,3,6,9,12,18,24", status="Active",
                    created_by="System", approved_by="System", approved_at=now))
        await session.commit()

        session.add(AuditLogModel(user_id=0, username="System", action="SEED",
                    table_name="database", record_id=0,
                    comments="Database successfully initialized (Enterprise Architecture)."))
        await session.commit()

    print("\n*** Seeding completed successfully! ***")
    print("Users: admin/admin123, analyst/analyst123, supervisor/super123, qa/qa123")


if __name__ == "__main__":
    asyncio.run(seed())
