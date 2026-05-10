import uuid
from dataclasses import dataclass
from typing import List

from domain.entities.verification_profile import VerificationProfile
from domain.exceptions import EntityNotFoundError
from domain.ports.i_profile_repository import IProfileRepository


@dataclass
class CreateProfileCommand:
    organization_id: uuid.UUID
    name: str


@dataclass
class UpdateProfileCommand:
    profile_id: uuid.UUID
    name: str | None = None


class ManageProfileUseCase:
    def __init__(self, profile_repo: IProfileRepository):
        self.profile_repo = profile_repo

    async def create_profile(self, command: CreateProfileCommand) -> VerificationProfile:
        profile = VerificationProfile(
            id=uuid.uuid4(),
            organization_id=command.organization_id,
            name=command.name,
        )
        return await self.profile_repo.create(profile)

    async def get_profile(self, profile_id: uuid.UUID) -> VerificationProfile:
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Profile {profile_id} not found")
        return profile

    async def list_profiles(self, organization_id: uuid.UUID) -> List[VerificationProfile]:
        return await self.profile_repo.list_by_organization(organization_id)

    async def update_profile(self, command: UpdateProfileCommand) -> VerificationProfile:
        profile = await self.profile_repo.get_by_id(command.profile_id)
        if not profile:
            raise EntityNotFoundError(f"Profile {command.profile_id} not found")

        if command.name is not None:
            profile.name = command.name

        return await self.profile_repo.update(profile)

    async def delete_profile(self, profile_id: uuid.UUID) -> None:
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Profile {profile_id} not found")
        await self.profile_repo.delete(profile_id)
