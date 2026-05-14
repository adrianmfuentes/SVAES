from typing import List, Optional
from uuid import UUID
from application.ports.input.i_profile_service import IProfileService
from application.ports.output.i_profile_repository import IProfileRepository
from application.ports.output.i_verification_rule_repository import IVerificationRuleRepository
from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_rule import VerificationRule
from domain.enums import SeverityType
from domain.exceptions import EntityNotFoundError
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger

_log = get_logger(__name__)

"""
Este servicio maneja toda la lógica relacionada con los perfiles de verificación, incluyendo:
    - Creación, actualización, listado y eliminación de perfiles.
    - Gestión de reglas dentro de cada perfil (agregar, actualizar, eliminar, reordenar).
    - Validaciones necesarias para asegurar la integridad de los datos y el correcto funcionamiento del sistema.

Un perfil de verificación es un conjunto de reglas que se aplican durante el proceso de verificación de una release.
Cada regla define un chequeo específico que se ejecutará, su severidad, y opcionalmente un conector asociado para obtener datos externos.

Ejemplo de perfil:
    {
        "id": "uuid-del-perfil",
        "organization_id": "uuid-de-la-organización",
        "name": "Perfil de Verificación para Proyectos Web",
        "description": "Incluye reglas específicas para validar releases de proyectos web.",
        "is_default": false,
        "rules": [
            {
                "id": "uuid-de-la-regla",
                "profile_id": "uuid-del-perfil",
                "rule_template": "check_unit_tests",
                "severity": "HIGH",
                "params": {"min_coverage": 80},
                "connector_instance_id": null,
                "display_order": 0,
                "is_active": true
            },
            ...
        ]
    }
"""

class ProfileService(IProfileService):
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
        requested_by: Optional[UUID] = None,
    ) -> VerificationProfile:
        if is_default:
            existing_default = await self._profile_repo.get_default_for_organization(organization_id)
            if existing_default:
                existing_default.is_default = False
                await self._profile_repo.update(existing_default)

        profile = VerificationProfile(
            id=UUID(),
            organization_id=organization_id,
            name=name,
            description=description,
            is_default=is_default,
            rules=[],
        )
        created = await self._profile_repo.create(profile)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.PROFILE_CREATED,
            user_id=requested_by or UUID(),
            organization_id=organization_id,
            resource_type="profile",
            resource_id=created.id,
            details={"name": name, "is_default": is_default},
        ))
        _log.info("Profile created: by=%s org=%s name=%s is_default=%s", requested_by, organization_id, name, is_default)

        return created


    async def update_profile(
        self,
        profile_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_default: Optional[bool] = None,
        requested_by: Optional[UUID] = None,
    ) -> VerificationProfile:
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Perfil no encontrado: {profile_id}")

        if is_default and not profile.is_default:
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

        updated = await self._profile_repo.update(profile)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.PROFILE_UPDATED,
            user_id=UUID(),
            organization_id=profile.organization_id,
            resource_type="profile",
            resource_id=profile_id,
            details={"name": profile.name},
        ))
        _log.info("Profile updated: id=%s org=%s", profile_id, profile.organization_id)

        return updated


    async def list_profiles(
        self, organization_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[VerificationProfile]:
        return await self._profile_repo.list_by_organization(organization_id, skip=skip, limit=limit)


    async def get_profile(self, profile_id: UUID) -> Optional[VerificationProfile]:
        return await self._profile_repo.get_by_id(profile_id)


    async def duplicate_profile(
        self, profile_id: UUID, new_name: str, requested_by: Optional[UUID] = None
    ) -> VerificationProfile:
        original = await self._profile_repo.get_by_id(profile_id)
        if not original:
            raise EntityNotFoundError(f"Perfil no encontrado: {profile_id}")

        new_profile = VerificationProfile(
            id=UUID(),
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

        duplicated_profile = await self._profile_repo.get_by_id(created.id)
        if not duplicated_profile:
            raise EntityNotFoundError(f"Perfil no encontrado: {created.id}")
        return duplicated_profile


    async def delete_profile(self, profile_id: UUID, requested_by: UUID) -> None:
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Perfil no encontrado: {profile_id}")

        org_id = profile.organization_id
        await self._profile_repo.delete(profile_id)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.PROFILE_DELETED,
            user_id=UUID(),
            organization_id=org_id,
            resource_type="profile",
            resource_id=profile_id,
            details={"name": profile.name},
        ))
        _log.info("Profile deleted: id=%s org=%s", profile_id, org_id)

    async def add_rule(
        self,
        profile_id: UUID,
        rule_template: str,
        severity: SeverityType = SeverityType.HIGH,
        connector_instance_id: Optional[UUID] = None,
        params: Optional[dict] = None,
        display_order: int = 0,
        requested_by: Optional[UUID] = None,
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
        created = await self._rule_repo.create(rule)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.RULE_CREATED,
            user_id=UUID(),
            organization_id=profile.organization_id,
            resource_type="rule",
            resource_id=created.id,
            details={"template": rule_template, "severity": severity.value},
        ))
        _log.info("Rule added: profile=%s template=%s", profile_id, rule_template)

        return created


    async def update_rule(
        self,
        rule_id: UUID,
        severity: Optional[SeverityType] = None,
        connector_instance_id: Optional[UUID] = None,
        params: Optional[dict] = None,
        display_order: Optional[int] = None,
        is_active: Optional[bool] = None,
        requested_by: Optional[UUID] = None,
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

        updated = await self._rule_repo.update(rule)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.RULE_UPDATED,
            user_id=UUID(),
            organization_id=None,
            resource_type="rule",
            resource_id=rule_id,
            details={"template": rule.rule_template},
        ))
        _log.info("Rule updated: id=%s", rule_id)

        return updated


    async def delete_rule(self, rule_id: UUID, requested_by: UUID) -> None:
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