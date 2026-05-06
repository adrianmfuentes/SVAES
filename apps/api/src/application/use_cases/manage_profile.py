import uuid
from dataclasses import dataclass
from domain.entities.verification_profile import VerificationProfile
from domain.ports.i_profile_repository import IProfileRepository

@dataclass
class CreateProfileCommand:
    organization_id: uuid.UUID
    name: str

class ManageProfileUseCase:
    """Application service for managing verification profiles within an organization."""

    def __init__(self, profile_repo: IProfileRepository):
        self.profile_repo = profile_repo

    async def create_profile(self, command: CreateProfileCommand) -> VerificationProfile:
        profile = VerificationProfile(
            id=uuid.uuid4(),
            organization_id=command.organization_id,
            name=command.name,
        )
        return await self.profile_repo.create(profile)
