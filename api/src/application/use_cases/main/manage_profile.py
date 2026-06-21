from typing import List, Optional
from uuid import UUID, uuid4
from application.ports.output.i_profile_repository import IProfileRepository
from application.ports.output.i_verification_rule_repository import IVerificationRuleRepository
from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_rule import VerificationRule
from domain.enums import SeverityType
from domain.exceptions import EntityNotFoundError, ValidationError

"""
Este módulo define el caso de uso para gestionar los perfiles de verificación, que es responsable de crear, actualizar, obtener, listar, duplicar y 
eliminar perfiles de verificación, así como agregar, actualizar, eliminar y reordenar las reglas dentro de un perfil.
"""
class ManageProfileUseCase:
    def __init__(
        self,
        profile_repository: IProfileRepository,
        rule_repository: IVerificationRuleRepository,
    ) -> None:
        self._profile_repo = profile_repository
        self._rule_repo = rule_repository


    async def create_profile(
        self,
        organization_id: UUID,
        name: str,
        description: str = "",
        is_default: bool = False,
    ) -> VerificationProfile:
        if is_default:
            existing_default = await self._profile_repo.get_default_for_organization(organization_id)
            if existing_default:
                existing_default.is_default = False
                await self._profile_repo.update(existing_default)

        profile = VerificationProfile(
            id=uuid4(),
            organization_id=organization_id,
            name=name,
            description=description,
            is_default=is_default,
            rules=[],
        )
        return await self._profile_repo.create(profile)


    async def update_profile(
        self,
        profile_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_default: Optional[bool] = None,
    ) -> VerificationProfile:
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Perfil no encontrado: {profile_id}")

        if is_default and not profile.is_default:
            if profile.organization_id is None:
                raise ValidationError("El perfil no pertenece a ninguna organización")
            existing_default = await self._profile_repo.get_default_for_organization(profile.organization_id)
            if existing_default:
                existing_default.is_default = False
                await self._profile_repo.update(existing_default)

        if name is not None:
            profile.name = name
        if description is not None:
            profile.description = description
        if is_default is not None:
            profile.is_default = is_default

        return await self._profile_repo.update(profile)


    async def get_profile(self, profile_id: UUID) -> Optional[VerificationProfile]:
        return await self._profile_repo.get_by_id(profile_id)


    async def list_profiles(
        self, organization_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[VerificationProfile]:
        return await self._profile_repo.list_by_organization(organization_id, skip=skip, limit=limit)

    async def duplicate_profile(self, profile_id: UUID, new_name: str) -> VerificationProfile:
        original = await self._profile_repo.get_by_id(profile_id)
        if not original:
            raise EntityNotFoundError(f"Perfil no encontrado: {profile_id}")

        new_profile = VerificationProfile(
            id=uuid4(),
            organization_id=original.organization_id,
            name=new_name,
            description=original.description,
            is_default=False,
            rules=[],
        )
        created = await self._profile_repo.create(new_profile)

        for rule in original.rules:
            new_rule = VerificationRule(
                profile_id=created.id,
                rule_template=rule.rule_template,
                severity=rule.severity,
                params=rule.params,
                connector_instance_id=rule.connector_instance_id,
                display_order=rule.display_order,
                is_active=rule.is_active,
            )
            await self._rule_repo.create(new_rule)

        duplicated = await self._profile_repo.get_by_id(created.id)
        if not duplicated:
            raise EntityNotFoundError(f"Perfil no encontrado: {created.id}")
        return duplicated


    async def delete_profile(self, profile_id: UUID, _requested_by: UUID) -> None:
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Perfil no encontrado: {profile_id}")
        if profile.is_system:
            raise ValidationError("El perfil del sistema no puede ser eliminado.")
        if profile.is_default:
            raise ValidationError("El perfil por defecto no puede ser eliminado.")
        await self._profile_repo.delete(profile_id)


    async def get_system_profile(self) -> Optional[VerificationProfile]:
        return await self._profile_repo.get_system_profile()


    async def add_rule(
        self,
        profile_id: UUID,
        rule_template: str,
        severity: SeverityType = SeverityType.HIGH,
        connector_instance_id: Optional[UUID] = None,
        params: Optional[dict] = None,
        display_order: int = 0,
    ) -> VerificationRule:
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Perfil no encontrado: {profile_id}")

        rule = VerificationRule(
            profile_id=profile_id,
            rule_template=rule_template,
            severity=severity,
            params=params or {},
            connector_instance_id=connector_instance_id,
            display_order=display_order,
        )
        return await self._rule_repo.create(rule)


    async def update_rule(
        self,
        rule_id: UUID,
        severity: Optional[SeverityType] = None,
        connector_instance_id: Optional[UUID] = None,
        params: Optional[dict] = None,
        display_order: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> VerificationRule:
        rule = await self._rule_repo.get_by_id(rule_id)
        if not rule:
            raise EntityNotFoundError(f"Regla no encontrada: {rule_id}")

        if severity is not None:
            rule.severity = severity
        if connector_instance_id is not None:
            rule.connector_instance_id = connector_instance_id
        if params is not None:
            rule.params = params
        if display_order is not None:
            rule.display_order = display_order
        if is_active is not None:
            rule.is_active = is_active

        return await self._rule_repo.update(rule)


    async def delete_rule(self, rule_id: UUID, _requested_by: UUID) -> None:
        rule = await self._rule_repo.get_by_id(rule_id)
        if not rule:
            raise EntityNotFoundError(f"Regla no encontrada: {rule_id}")
        await self._rule_repo.delete(rule_id)


    async def reorder_rules(self, profile_id: UUID, rule_ids: List[UUID]) -> List[VerificationRule]:
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Perfil no encontrado: {profile_id}")

        rules = []
        for idx, rule_id in enumerate(rule_ids):
            rule = await self._rule_repo.get_by_id(rule_id)
            if rule and rule.profile_id == profile_id:
                rule.display_order = idx
                rules.append(await self._rule_repo.update(rule))

        return rules