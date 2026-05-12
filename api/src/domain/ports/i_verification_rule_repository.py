from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities.verification_rule import VerificationRule


class IVerificationRuleRepository(ABC):
    @abstractmethod
    async def create(self, rule: VerificationRule) -> VerificationRule:
        pass

    @abstractmethod
    async def get_by_id(self, rule_id: UUID) -> Optional[VerificationRule]:
        pass

    @abstractmethod
    async def list_by_profile(self, profile_id: UUID) -> List[VerificationRule]:
        pass

    @abstractmethod
    async def update(self, rule: VerificationRule) -> VerificationRule:
        pass

    @abstractmethod
    async def delete(self, rule_id: UUID) -> None:
        pass
