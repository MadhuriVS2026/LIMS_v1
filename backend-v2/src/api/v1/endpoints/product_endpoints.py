"""Product/Material Master Data API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user, get_session, require_role
from src.api.v1.schemas.auth_schemas import ESignRequest
from src.api.v1.schemas.product_schemas import (
    CreateProductRequest,
    ProductResponse,
    UpdateProductRequest,
)
from src.application.services.auth_service import AuthService
from src.config.dependency_injection import Container
from src.domain.entities.user import User

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=list[ProductResponse])
async def list_products(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_product_service(session)
    return await service.list_products()


@router.post("", response_model=ProductResponse)
async def create_product(
    request: CreateProductRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    service = Container.get_product_service(session)
    return await service.create_product(
        request.code, request.name, request.description, request.material_type,
        request.retest_period_days, request.storage_condition, current_user,
    )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    request: UpdateProductRequest,
    current_user: User = Depends(require_role("Admin")),
    session: AsyncSession = Depends(get_session),
):
    """Edit product master data. Editing an approved product returns it to
    Pending Approval and requires re-approval."""
    service = Container.get_product_service(session)
    return await service.update_product(
        product_id, current_user,
        name=request.name, description=request.description,
        material_type=request.material_type,
        retest_period_days=request.retest_period_days,
        storage_condition=request.storage_condition,
    )


@router.delete("/{product_id}", response_model=ProductResponse)
async def delete_product(
    product_id: int,
    esign: ESignRequest,
    current_user: User = Depends(require_role("Admin", "Supervisor")),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete (deactivate) a product. E-signed; retains the record and
    writes an audit entry flagged for GL/TL/Supervisor/Admin review."""
    auth_service: AuthService = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, esign.password)

    service = Container.get_product_service(session)
    return await service.soft_delete_product(product_id, current_user, esign.comments)


@router.post("/{product_id}/approve", response_model=ProductResponse)
async def approve_product(
    product_id: int,
    esign: ESignRequest,
    current_user: User = Depends(require_role("Supervisor", "QA")),
    session: AsyncSession = Depends(get_session),
):
    auth_service: AuthService = Container.get_auth_service(session)
    await auth_service.verify_esignature(current_user, esign.password)

    service = Container.get_product_service(session)
    return await service.approve_product(product_id, current_user, esign.comments)
