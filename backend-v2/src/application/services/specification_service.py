"""Specification Application Service — versioned test limits & approval workflow."""
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import NotFoundException
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.specification import Specification, SpecificationTest
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.specification_repository import ISpecificationRepository


class SpecificationService:
    def __init__(
        self,
        spec_repo: ISpecificationRepository,
        audit_repo: IAuditLogRepository,
    ) -> None:
        self._spec_repo = spec_repo
        self._audit_repo = audit_repo

    async def list_specifications(self) -> list[Specification]:
        return await self._spec_repo.list_all()

    async def get_specification(self, spec_id: int) -> Specification:
        spec = await self._spec_repo.get_by_id(spec_id)
        if spec is None:
            raise NotFoundException("Specification not found")
        return spec

    async def create_specification(
        self,
        product_id: int,
        spec_type: str | None,
        document_no: str | None,
        tests: list[dict],
        actor: User,
    ) -> Specification:
        existing = await self._spec_repo.list_by_product(product_id)
        version = len(existing) + 1

        spec = Specification(
            product_id=product_id,
            version=version,
            spec_type=spec_type,
            document_no=document_no,
            status="Pending Approval",
            tests=[
                SpecificationTest(
                    test_id=t["test_id"],
                    min_limit=t.get("min_limit"),
                    max_limit=t.get("max_limit"),
                    expected_result=t.get("expected_result"),
                    display_in_coa=t.get("display_in_coa", True),
                )
                for t in tests
            ],
            created_by=actor.username,
            modified_by=actor.username,
        )
        created = await self._spec_repo.create(spec)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="CREATE",
                table_name="specifications", record_id=created.id,
                new_values={"product_id": created.product_id, "version": created.version},
            )
        )
        return created

    async def approve_specification(
        self, spec_id: int, approver: User, comments: str | None
    ) -> Specification:
        spec = await self.get_specification(spec_id)
        old_status = spec.status

        # Deactivate any previously Active spec for this product (domain rule:
        # only one Active specification per product at a time).
        await self._spec_repo.deactivate_active_for_product(spec.product_id)

        spec.approve(approver.username, datetime.now(timezone.utc))
        updated = await self._spec_repo.update(spec)

        await self._audit_repo.write(
            AuditLog(
                user_id=approver.id, username=approver.username, action="APPROVE",
                table_name="specifications", record_id=updated.id,
                old_values={"status": old_status}, new_values={"status": updated.status},
                comments=comments,
            )
        )
        return updated
