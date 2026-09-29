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

    async def update_product(
        self,
        product_id: int,
        actor: User,
        *,
        name: str | None = None,
        description: str | None = None,
        material_type: str | None = None,
        retest_period_days: int | None = None,
        storage_condition: str | None = None,
    ) -> Product:
        """Edit product master data. An edit to an Active product returns it to
        Pending Approval (re-approval required)."""
        product = await self.get_product(product_id)
        if product.status == "Inactive":
            raise ConflictException("Cannot edit a deactivated product")

        before = {
            "name": product.name, "description": product.description,
            "material_type": product.material_type,
            "retest_period_days": product.retest_period_days,
            "storage_condition": product.storage_condition, "status": product.status,
        }
        product.update_details(
            actor.username, name=name, description=description,
            material_type=material_type, retest_period_days=retest_period_days,
            storage_condition=storage_condition,
        )
        updated = await self._product_repo.update(product)

        after = {
            "name": updated.name, "description": updated.description,
            "material_type": updated.material_type,
            "retest_period_days": updated.retest_period_days,
            "storage_condition": updated.storage_condition, "status": updated.status,
        }
        requires_reapproval = before["status"] == "Active"
        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="UPDATE",
                table_name="products", record_id=updated.id,
                old_values=before, new_values=after,
                comments=(
                    "Edited — returned to Pending Approval; re-approval required."
                    if requires_reapproval else "Edited (pending approval)."
                ),
            )
        )
        return updated

    async def soft_delete_product(
        self, product_id: int, actor: User, comments: str | None
    ) -> Product:
        """Soft-delete (deactivate). The record is retained; a flagged audit
        entry notifies GL/TL/Supervisor/Admin for review."""
        product = await self.get_product(product_id)
        if product.status == "Inactive":
            raise ConflictException("Product is already deactivated")

        old_status = product.status
        product.deactivate(actor.username)
        updated = await self._product_repo.update(product)

        note = (
            f"[REVIEW: GL/TL/Supervisor/Admin] Product '{updated.code}' "
            f"deactivated by {actor.username} ({actor.role})."
        )
        if comments:
            note += f" Reason: {comments}"
        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="DELETE",
                table_name="products", record_id=updated.id,
                old_values={"status": old_status}, new_values={"status": updated.status},
                comments=note,
            )
        )
        return updated
