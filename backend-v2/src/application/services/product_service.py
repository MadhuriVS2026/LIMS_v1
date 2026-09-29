"""Product Application Service — registration & approval workflow."""
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import (
    ConflictException,
    NotFoundException,
)
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.product import Product
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.product_repository import IProductRepository


class ProductService:
    def __init__(self, product_repo: IProductRepository, audit_repo: IAuditLogRepository) -> None:
        self._product_repo = product_repo
        self._audit_repo = audit_repo

    async def list_products(self) -> list[Product]:
        return await self._product_repo.list_all()

    async def get_product(self, product_id: int) -> Product:
        product = await self._product_repo.get_by_id(product_id)
        if product is None:
            raise NotFoundException("Product not found")
        return product

    async def create_product(
        self,
        code: str,
        name: str,
        description: str | None,
        material_type: str | None,
        retest_period_days: int | None,
        storage_condition: str | None,
        actor: User,
    ) -> Product:
        if await self._product_repo.exists_by_code(code):
            raise ConflictException(f"Product code '{code}' already exists")

        product = Product(
            code=code,
            name=name,
            description=description,
            material_type=material_type,
            retest_period_days=retest_period_days,
            storage_condition=storage_condition,
            status="Pending Approval",
            created_by=actor.username,
            modified_by=actor.username,
        )
        created = await self._product_repo.create(product)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="CREATE",
                table_name="products", record_id=created.id,
                new_values={"code": created.code, "name": created.name},
            )
        )
        return created

    async def approve_product(self, product_id: int, approver: User, comments: str | None) -> Product:
        product = await self.get_product(product_id)
        old_status = product.status
        product.approve(approver.username, datetime.now(timezone.utc))
        updated = await self._product_repo.update(product)

        await self._audit_repo.write(
            AuditLog(
                user_id=approver.id, username=approver.username, action="APPROVE",
                table_name="products", record_id=updated.id,
                old_values={"status": old_status}, new_values={"status": updated.status},
                comments=comments,
            )
        )
        return updated
