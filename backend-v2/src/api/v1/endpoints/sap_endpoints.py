"""SAP Integration API endpoints."""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_role
from src.api.v1.schemas.sap_schemas import (
    SAPInspectionLotPullRequest,
    SAPInspectionLotPushRequest,
    SAPUsageDecisionRequest,
    SAPUsageDecisionResponse,
)
from src.config.dependency_injection import Container
from src.config.settings import settings
from src.domain.entities.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sap", tags=["SAP Integration"])


def verify_sap_inbound_key(x_api_key: str | None = Header(default=None)) -> None:
    """
    Guards the inbound SAP push endpoint. SAP CPI authenticates with a shared
    x-api-key header (set as SAP_INBOUND_API_KEY), not a LIMS user JWT — CPI
    has no LIMS user account.
    """
    expected = settings.SAP_INBOUND_API_KEY
    if not expected:
        logger.warning(
            "SAP_INBOUND_API_KEY is not configured — /sap/inbound/inspection-lot "
            "is accepting unauthenticated calls. Set SAP_INBOUND_API_KEY before "
            "exposing this endpoint outside local development."
        )
        return
    if x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@router.post("/inbound/inspection-lot")
async def receive_inspection_lot(
    request: SAPInspectionLotPushRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(verify_sap_inbound_key),
) -> dict:
    """
    Inbound push target for SAP CPI. Point the CPI iFlow that currently posts
    to the "inspection_lot Download" (LotRequest) endpoint at this URL instead.
    Payload shape is unchanged (inspLotDat + inspCharData) so no CPI mapping
    changes are needed beyond the target URL and the x-api-key header value.

    This endpoint is read-only from SAP's perspective: it stores the lot data
    for the analyst to review; it never calls back out to SAP.
    """
    service = Container.get_sap_service(session)
    return await service.receive_inspection_lot(request.model_dump())


@router.get("/inbound/inspection-lot")
async def list_received_lots(
    current_user: User = Depends(require_role("Admin", "Analyst", "QA")),
    session: AsyncSession = Depends(get_session),
) -> list:
    """Lists inspection lots received from SAP, most recent first — for the LIMS UI."""
    service = Container.get_sap_service(session)
    return await service.list_received_lots()


@router.post("/inspection-lot/pull")
async def pull_inspection_lot(
    request: SAPInspectionLotPullRequest,
    current_user: User = Depends(require_role("Admin", "Analyst", "QA")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Pulls an inspection lot from SAP CPI on demand (outbound call to SAP's
    Post_lims_inspection_lot flow). No inbound exposure required — this LIMS
    reaches out to SAP and stores the response, same as the push endpoint.
    """
    service = Container.get_sap_service(session)
    return await service.pull_inspection_lot(request.inspection_lot, current_user)


@router.post("/usage-decision", response_model=SAPUsageDecisionResponse)
async def sap_usage_decision(
    request: SAPUsageDecisionRequest,
    current_user: User = Depends(require_role("QA")),
    session: AsyncSession = Depends(get_session),
):
    """Post the Usage Decision (Accept/Reject) to SAP QM (ZLIMS_PROCESS_UD4)."""
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_sap_service(session)
    result = await service.post_usage_decision(
        request.sample_id, request.ud_code, request.ud_code_group, request.text_line, current_user
    )
    return SAPUsageDecisionResponse(**result)


@router.get("/logs")
async def sap_logs(
    current_user: User = Depends(require_role("Admin", "QA")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_sap_service(session)
    return await service.list_logs()
