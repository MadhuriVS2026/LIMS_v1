"""Audit Trail & Dashboard API endpoints."""
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user, get_session
from src.api.v1.schemas.audit_schemas import AuditLogResponse, DashboardStatsResponse
from src.config.dependency_injection import Container
from src.domain.entities.user import User
from src.infrastructure.database.models.instrument_model import InstrumentModel
from src.infrastructure.database.models.sample_model import SampleModel, SampleResultModel
from src.infrastructure.database.models.oos_model import OOSInvestigationModel

router = APIRouter(tags=["Audit & Dashboard"])


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    skip: int = Query(default=0),
    limit: int = Query(default=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = Container.get_audit_repo(session)
    return await repo.list_recent(skip, limit)


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardStatsResponse:
    """Aggregate KPIs for the LIMS home dashboard."""
    # SQLite does not persist tzinfo, so all comparisons here use naive UTC datetimes.
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    today_start = datetime.combine(now_naive.date(), time.min)

    total_samples = (await session.execute(select(SampleModel))).scalars().all()
    total_count = len(total_samples)
    pending_count = len([s for s in total_samples if s.status in ("Logged", "Received", "Under Review")])
    samples_today = len([s for s in total_samples if s.logged_at and s.logged_at >= today_start])
    approved_today = len(
        [s for s in total_samples if s.status == "Approved" and s.approved_at and s.approved_at >= today_start]
    )
    rejected_today = len(
        [s for s in total_samples if s.status == "Rejected" and s.approved_at and s.approved_at >= today_start]
    )

    oos_rows = (await session.execute(select(OOSInvestigationModel).where(OOSInvestigationModel.status == "Open"))).scalars().all()
    pending_review_rows = (await session.execute(select(SampleResultModel).where(SampleResultModel.status == "Submitted"))).scalars().all()

    threshold = now_naive + timedelta(days=7)
    instruments = (await session.execute(select(InstrumentModel))).scalars().all()
    instruments_due = len([i for i in instruments if i.calibration_due_date and i.calibration_due_date <= threshold])

    return DashboardStatsResponse(
        total_samples=total_count,
        pending_samples=pending_count,
        oos_open=len(oos_rows),
        samples_today=samples_today,
        instruments_due_calibration=instruments_due,
        pending_reviews=len(pending_review_rows),
        approved_today=approved_today,
        rejected_today=rejected_today,
    )
