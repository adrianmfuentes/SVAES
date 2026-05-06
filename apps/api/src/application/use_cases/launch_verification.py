import uuid
from dataclasses import dataclass
from typing import Tuple
from domain.entities.release import Release
from domain.entities.enums import ReleaseStatus
from domain.ports.i_release_repository import IReleaseRepository
from domain.ports.i_task_queue import ITaskQueue
from domain.exceptions import EntityNotFoundError, ReleaseInvalidStateError

@dataclass
class LaunchVerificationCommand:
    release_id: uuid.UUID
    user_id: uuid.UUID

class LaunchVerificationUseCase:
    def __init__(
        self,
        release_repo: IReleaseRepository,
        task_queue: ITaskQueue,
    ):
        self.release_repo = release_repo
        self.task_queue = task_queue

    async def execute(self, command: LaunchVerificationCommand) -> Tuple[Release, str]:
        release = await self.release_repo.get_by_id(command.release_id)
        if not release:
            raise EntityNotFoundError(f"No se encontró la release {command.release_id}")

        if release.status != ReleaseStatus.PENDIENTE:
            raise ReleaseInvalidStateError(
                release_id=release.id,
                current_status=release.status,
                expected_status=ReleaseStatus.PENDIENTE,
            )

        release.status = ReleaseStatus.EN_VERIFICACION
        updated_release = await self.release_repo.update(release)

        task_id = await self.task_queue.enqueue_verification_task(release.id)
        return updated_release, task_id
