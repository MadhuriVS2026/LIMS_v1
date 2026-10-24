"""
Non-destructive seed for the Project Master resource.

Unlike scripts/seed_data.py (which does drop_all + create_all + full reseed and
would wipe the populated dev lims.db), this one-shot:
  1. Runs Base.metadata.create_all — the same call init_models() uses, which
     creates ONLY missing tables (here: project_master) and never drops data.
  2. Inserts the 3 design seed rows, each guarded by an idempotent select so
     re-running does not duplicate rows.

Usage (from backend-v2/): python -m scripts.seed_project_master
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

import src.infrastructure.database.models  # noqa: F401  (registers all ORM models)
from src.infrastructure.database.models.base_model import Base
from src.infrastructure.database.models.resource_models import ProjectMasterModel
from src.infrastructure.database.session import async_session_factory, engine

SEED_ROWS = [
    dict(
        project_id="PID-2026-001", product_name="Doxorubicin Liposome",
        product_code="PRD-DOXO-01", project_code="PRJ-ONCO-01",
        project_code_academic="AR-ONCO-01", bd_code_sap="BD-100231",
        group_lead="Suresh Iyer", location="Ahmedabad", market="US",
        start_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        end_date=datetime(2026, 12, 31, tzinfo=timezone.utc), license="ANDA",
        comments="Liposomal oncology development program.", status="Active",
        requested_person="BD Team", remarks="Priority project.", created_by="System",
    ),
    dict(
        project_id="PID-2026-002", product_name="Propofol 1% Emulsion",
        product_code="PRD-PROP-01", project_code="PRJ-ANES-02",
        project_code_academic="AR-ANES-02", bd_code_sap="BD-100232",
        group_lead="Meera Nair", location="Hyderabad", market="EU",
        start_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 11, 30, tzinfo=timezone.utc), license="MAA",
        comments="Lipid emulsion anaesthetic.", status="Active",
        requested_person="BD Team", remarks="", created_by="System",
    ),
    dict(
        project_id="PID-2026-003", product_name="Bupivacaine Lipid Injection",
        product_code="PRD-BUPI-01", project_code="PRJ-ANES-03",
        project_code_academic="AR-ANES-03", bd_code_sap="BD-100233",
        group_lead="Arjun Rao", location="Bengaluru", market="IN",
        start_date=datetime(2025, 9, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 8, 31, tzinfo=timezone.utc), license="NDA",
        comments="Long-acting local anaesthetic.", status="Inactive",
        requested_person="BD Team", remarks="On hold pending review.", created_by="System",
    ),
]


async def main() -> None:
    # Non-destructive: creates only missing tables, leaves existing data intact.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    inserted = 0
    async with async_session_factory() as session:
        for row in SEED_ROWS:
            existing = await session.execute(
                select(ProjectMasterModel).where(
                    ProjectMasterModel.project_id == row["project_id"]
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            session.add(ProjectMasterModel(**row))
            inserted += 1
        await session.commit()

    print(f"project_master seed complete: {inserted} new row(s) inserted, "
          f"{len(SEED_ROWS) - inserted} already present.")


if __name__ == "__main__":
    asyncio.run(main())
