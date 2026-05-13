from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.release import Release
from domain.enums import ReleaseStatus

class IReleaseRepository(ABC):
    @abstractmethod
    async def create(self, release: Release) -> None:
        pass

    @abstractmethod
    async def get_by_id(self, release_id: uuid.UUID) -> Optional[Release]:
        pass

    @abstractmethod
    async def list_by_project(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> List[Release]:
        pass

    @abstractmethod
    async def list_by_organization(
        self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> List[Release]:
        pass

    @abstractmethod
    async def update(self, release: Release) -> Release:
        pass

    @abstractmethod
    async def update_status(
        self, release_id: uuid.UUID, status: ReleaseStatus
    ) -> Optional[Release]:
        pass

    @abstractmethod
    async def delete(self, release_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    async def get_artifact_by_id(self, artifact_id: uuid.UUID) -> Optional[
        dict
    ]:
        pass

    @abstractmethod
    async def delete_artifact(self, artifact_id: uuid.UUID) -> None:
        pass
