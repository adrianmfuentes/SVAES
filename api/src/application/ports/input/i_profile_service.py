from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_rule import VerificationRule
from domain.enums import SeverityType


class IProfileService(ABC):
    @abstractmethod
    async def create_profile(
        self,
        organization_id: UUID,
        name: str,
        description: str = "",
        is_default: bool = False,
    ) -> VerificationProfile:
        pass

    @abstractmethod
    async def update_profile(
        self,
        profile_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_default: Optional[bool] = None,
    ) -> VerificationProfile:
        pass

    @abstractmethod
    async def list_profiles(
        self, organization_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[VerificationProfile]:
        pass

    @abstractmethod
    async def get_profile(self, profile_id: UUID) -> Optional[VerificationProfile]:
        pass

    @abstractmethod
    async def duplicate_profile(
        self, profile_id: UUID, new_name: str
    ) -> VerificationProfile:
        pass

    @abstractmethod
    async def delete_profile(self, profile_id: UUID) -> None:
        pass

    @abstractmethod
    async def add_rule(
        self,
        profile_id: UUID,
        rule_template: str,
        severity: SeverityType = SeverityType.HIGH,
        connector_instance_id: Optional[UUID] = None,
        params: Optional[dict] = None,
        display_order: int = 0,
    ) -> VerificationRule:
        pass

    @abstractmethod
    async def update_rule(
        self,
        rule_id: UUID,
        severity: Optional[SeverityType] = None,
        connector_instance_id: Optional[UUID] = None,
        params: Optional[dict] = None,
        display_order: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> VerificationRule:
        pass

    @abstractmethod
    async def delete_rule(self, rule_id: UUID) -> None:
        pass

    @abstractmethod
    async def reorder_rules(self, profile_id: UUID, rule_ids: List[UUID]) -> List[VerificationRule]:
        pass