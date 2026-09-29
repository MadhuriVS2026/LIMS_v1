"""OOS Investigation Application Service."""
from datetime import datetime, timezone

from src.application.exceptions.application_exceptions import NotFoundException
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.oos_investigation import OOSInvestigation
from src.domain.entities.user import User
from src.domain.repositories.audit_repository import IAuditLogRepository
from src.domain.repositories.oos_repository import IOOSRepository
from src.domain.repositories.sample_repository import ISampleRepository


class OOSService:
    def __init__(
        self,
        oos_repo: IOOSRepository,
        sample_repo: ISampleRepository,
        audit_repo: IAuditLogRepository,
    ) -> None:
        self._oos_repo = oos_repo
        self._sample_repo = sample_repo
        self._audit_repo = audit_repo

    async def list_oos(self) -> list[OOSInvestigation]:
        return await self._oos_repo.list_all()

    async def close_oos(
        self,
        oos_id: int,
        root_cause: str,
        corrective_action: str,
        actor: User,
    ) -> OOSInvestigation:
        """
        Close an OOS investigation with root cause + CAPA (E-Signed).
        If this was the last Open OOS on the Sample, the Sample returns to
        'Under Review' so QA can make the final batch disposition.
        """
        oos = await self._oos_repo.get_by_id(oos_id)
        if oos is None:
            raise NotFoundException("OOS Record not found")

        old_status = oos.status
        oos.close(actor.username, datetime.now(timezone.utc), root_cause, corrective_action)
        updated = await self._oos_repo.update(oos)

        await self._audit_repo.write(
            AuditLog(
                user_id=actor.id, username=actor.username, action="CLOSE_OOS",
                table_name="oos_investigations", record_id=updated.id,
                old_values={"status": old_status}, new_values={"status": updated.status},
                comments="OOS investigation closed with findings",
            )
        )

        remaining_open = await self._oos_repo.list_open_for_sample(oos.sample_id)
        if not remaining_open:
            sample = await self._sample_repo.get_by_id(oos.sample_id)
            if sample:
                sample.status = "Under Review"
                await self._sample_repo.update(sample)

        return updated
