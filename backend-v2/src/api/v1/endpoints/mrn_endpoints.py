"""MRN — Material Requisition & Consumption API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_role
from src.api.v1.schemas.mrn_schemas import (
    ApproveAndPostRequest,
    CreateLineItemRequest,
    MaterialQueuePullResponse,
    MaterialRequisitionResponse,
    MRNLineItemResponse,
    MRNMaterialLotResponse,
)
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/mrn", tags=["MRN — Material Requisition & Consumption"])


@router.get("/material-queue", response_model=list[MRNMaterialLotResponse])
async def get_material_queue(
    current_user: User = Depends(require_role("Admin", "Analyst", "Supervisor", "QA")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.1, 6.4: available material lots, any authenticated role may view."""
    service = Container.get_mrn_service(session)
    return await service.list_material_queue()


@router.post("/material-queue/pull", response_model=MaterialQueuePullResponse)
async def pull_material_queue(
    current_user: User = Depends(require_role("Admin", "Analyst", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 1.2, 6.3: manual pull of GRN-complete materials from SAP."""
    service = Container.get_mrn_service(session)
    return await service.pull_grn_materials(current_user)


@router.post("", response_model=MaterialRequisitionResponse)
async def create_mrn(
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 2.1, 6.1: raise a new Draft MRN."""
    service = Container.get_mrn_service(session)
    return await service.create_mrn(current_user)


@router.get("", response_model=list[MaterialRequisitionResponse])
async def list_mrns(
    current_user: User = Depends(require_role("Admin", "Analyst", "Supervisor", "QA")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 6.4: Admin/Supervisor see all MRNs; others see only their own."""
    service = Container.get_mrn_service(session)
    return await service.list_mrns(current_user)


@router.get("/{mrn_id}", response_model=MaterialRequisitionResponse)
async def get_mrn(
    mrn_id: int,
    current_user: User = Depends(require_role("Admin", "Analyst", "Supervisor", "QA")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 6.4: detail view with line items, any authenticated role may view."""
    service = Container.get_mrn_service(session)
    return await service.get_mrn(mrn_id)


@router.post("/{mrn_id}/line-items", response_model=MRNLineItemResponse)
async def add_line_item(
    mrn_id: int,
    request: CreateLineItemRequest,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 2.2, 2.3, 2.7, 6.1: add a line item to a Draft MRN."""
    service = Container.get_mrn_service(session)
    return await service.add_line_item(
        mrn_id, request.lot_id, request.requested_quantity, request.project_code, current_user
    )


@router.delete("/{mrn_id}/line-items/{line_id}")
async def remove_line_item(
    mrn_id: int,
    line_id: int,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Requirement 2.4, 6.1: remove a line item from a Draft MRN."""
    service = Container.get_mrn_service(session)
    await service.remove_line_item(mrn_id, line_id, current_user)
    return {"success": True, "message": "Line item removed"}


@router.post("/{mrn_id}/submit", response_model=MaterialRequisitionResponse)
async def submit_mrn(
    mrn_id: int,
    current_user: User = Depends(require_role("Admin", "Analyst")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 2.5, 2.6, 2.7, 6.1: submit a Draft MRN, locking its line items."""
    service = Container.get_mrn_service(session)
    return await service.submit_mrn(mrn_id, current_user)


@router.post("/{mrn_id}/approve-post", response_model=MaterialRequisitionResponse)
async def approve_and_post(
    mrn_id: int,
    request: ApproveAndPostRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """
    Requirement 3.1-3.9, 6.2: e-sign-gated approval that triggers consumption
    posting to SAP for every line item of a Submitted MRN.
    """
    auth_service = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, request.password)

    service = Container.get_mrn_service(session)
    return await service.approve_and_post(mrn_id, current_user)


@router.post("/{mrn_id}/reprocess", response_model=MaterialRequisitionResponse)
async def reprocess_failed(
    mrn_id: int,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Requirement 3.7, 6.2: retry only PostingFailed line items."""
    service = Container.get_mrn_service(session)
    return await service.reprocess_failed(mrn_id, current_user)
