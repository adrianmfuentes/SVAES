from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.template import Template


class ITemplateRepository(ABC):
    @abstractmethod
    async def create(self, template: Template) -> Template:
        pass

    @abstractmethod
    async def get_by_id(self, template_id: UUID) -> Optional[Template]:
        pass

    @abstractmethod
    async def list_by_organization(self, organization_id: UUID, skip: int = 0, limit: int = 50, include_archived: bool = False) -> List[Template]:
        pass

    @abstractmethod
    async def update(self, template: Template) -> Template:
        pass

    @abstractmethod
    async def delete(self, template_id: UUID) -> None:
        pass
