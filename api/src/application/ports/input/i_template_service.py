from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.template import Template

class ITemplateService(ABC):
    @abstractmethod
    async def create_template(
        self,
        name: str,
        description: str,
        profile_id: UUID,
        created_by: UUID,
        organization_id: UUID,
        project_name_template: Optional[str] = None,
    ) -> Template:
        pass

    @abstractmethod
    async def list_templates(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
    ) -> List[Template]:
        pass

    @abstractmethod
    async def get_template(self, template_id: UUID) -> Optional[Template]:
        pass

    @abstractmethod
    async def update_template(
        self,
        template_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_archived: Optional[bool] = None,
    ) -> Template:
        pass

    @abstractmethod
    async def archive_template(self, template_id: UUID) -> None:
        pass

    @abstractmethod
    async def clone_template(
        self,
        template_id: UUID,
        new_name: str,
        target_organization_id: UUID,
        requested_by: UUID,
    ) -> Template:
        pass