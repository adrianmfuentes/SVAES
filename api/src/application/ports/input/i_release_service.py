from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities.release import Release
from domain.entities.artifact import Artifact
from domain.enums import ReleaseStatus


class IReleaseService(ABC):
    @abstractmethod
    async def create_release(
        self,
        name: str,
        version: str,
        project_id: UUID,
        user_id: UUID,
        description: str = "",
        profile_id: Optional[UUID] = None,
    ) -> Release:
        pass

    @abstractmethod
    async def get_release(self, release_id: UUID) -> Optional[Release]:
        pass

    @abstractmethod
    async def list_releases(
        self, project_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[Release]:
        pass

    @abstractmethod
    async def update_release(
        self,
        release_id: UUID,
        name: str,
        version: str,
        description: str = "",
    ) -> Release:
        pass

    @abstractmethod
    async def update_status(
        self, release_id: UUID, status: ReleaseStatus
    ) -> Release:
        pass

    @abstractmethod
    async def add_artifact(
        self,
        release_id: UUID,
        connector_instance_id: UUID,
        connector_implementation: str,
        artifact_type: str,
        external_ref: str,
        metadata: Optional[dict] = None,
    ) -> Artifact:
        pass

    @abstractmethod
    async def remove_artifact(self, artifact_id: UUID) -> None:
        pass

    @abstractmethod
    async def list_artifacts(
        self, release_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Artifact]:
        pass

    @abstractmethod
    async def delete_release(self, release_id: UUID) -> None:
        pass

    @abstractmethod
    async def restore_release(self, release_id: UUID) -> None:
        pass

    @abstractmethod
    async def list_org_releases(
        self, organization_id: Optional[UUID] = None
    ) -> List[Release]:
        pass