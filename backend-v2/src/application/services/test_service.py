"""Test Parameter Application Service."""
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.test_parameter import TestParameter
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.test_repository import ITestRepository


class TestService:
    def __init__(self, test_repo: ITestRepository, audit_repo: IAuditLogRepository) -> None:
        self._test_repo = test_repo
        self._audit_repo = audit_repo

    async def list_tests(self) -> list[TestParameter]:
        return await self._test_repo.list_all()

    async def create_test(
        self,
        code: str,
        name: str,
        type_: str,
        unit: str | None,
        method_no: str | None,
        category: str | None,
        technique: str | None,
        actor: User,
    ) -> TestParameter:
        test = TestParameter(
            code=code, name=name, type=type_, unit=unit, method_no=method_no,
            category=category, technique=technique, status="Active",
            created_by=actor.username, modified_by=actor.username,
        )
        created = await self._test_repo.create(test)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="CREATE",
                table_name="tests", record_id=created.id,
                new_values={"code": created.code, "name": created.name},
            )
        )
        return created
