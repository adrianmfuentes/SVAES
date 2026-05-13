from uuid import UUID
from application.ports.output.i_release_repository import IReleaseRepository
from application.ports.output.i_task_queue import ITaskQueue
from domain.enums import ReleaseStatus
from domain.exceptions import ValidationError


class LaunchVerificationUseCase:
    def __init__(
        self,
        release_repository: IReleaseRepository,
        task_queue: ITaskQueue,
    ) -> None:
        self._release_repo = release_repository
        self._task_queue = task_queue

    async def execute(self, release_id: UUID) -> str:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError("Release no encontrada")

        valid_statuses = (
            ReleaseStatus.PENDIENTE,
            ReleaseStatus.VALIDA,
            ReleaseStatus.NO_VALIDA,
            ReleaseStatus.CON_ADVERTENCIAS,
        )

        if release.status not in valid_statuses:
            raise ValidationError(
                f"No se puede iniciar verificación desde estado {release.status.value}. "
                "Debe estar en PENDIENTE o tener un resultado previo."
            )

        if not release.artifacts:
            raise ValidationError("No se puede verificar una release sin artefactos asociados.")

        await self._release_repo.update_status(release_id, ReleaseStatus.EN_VERIFICACION)
        task_id = await self._task_queue.enqueue_verification_task(release_id)
        return task_id