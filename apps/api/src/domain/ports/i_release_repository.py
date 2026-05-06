from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.release import Release

class IReleaseRepository(ABC):
    """Puerto para la persistencia de Releases."""

    @abstractmethod
    async def create(self, release: Release) -> Release:
        pass

    @abstractmethod
    async def get_by_id(self, release_id: uuid.UUID) -> Optional[Release]:
        pass

    @abstractmethod
    async def list_by_project(self, project_id: uuid.UUID) -> List[Release]:
        pass

    @abstractmethod
    async def update(self, release: Release) -> Release:
        """Actualiza el estado u otros campos de la release."""
        pass