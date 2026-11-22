import logging
from types import EllipsisType
from typing import List, Optional
from uuid import UUID, uuid4
from collections.abc import Callable
from features.verification.application.ports.i_profile_service import IProfileService
from features.verification.application.ports.i_profile_repository import IProfileRepository
from features.verification.application.ports.i_verification_rule_repository import IVerificationRuleRepository
from features.verification.application.use_cases.manage_profile import ManageProfileUseCase
from features.verification.domain.verification_profile import VerificationProfile
from features.verification.domain.verification_rule import VerificationRule
from shared.domain.enums import SeverityType
from shared.domain.exceptions import EntityNotFoundError, ValidationError
from shared.application.i_audit_logger import IAuditLogger
from shared.domain.audit import AuditEntry, AuditEvent
from features.verification.domain.rule_names import CUSTOM_FIELD_CHECK_OPERATORS

_log = logging.getLogger(__name__)


def _validate_schedule(schedule: Optional[str], is_valid: Callable[[str], bool]) -> None:
    """`schedule` es una expresión cron de 5 campos (minuto hora dia mes dia_semana)
    que dispara re-verificaciones automáticas (ver scheduler_worker.py). `None`/""
    desactiva el cronograma, así que solo se valida cuando trae contenido.
    """
    if not schedule:
        return
    if not is_valid(schedule):
        raise ValidationError(f"Expresión cron inválida: '{schedule}'")


def _validate_rule_params(rule_template: str, params: dict) -> None:
    """Valida la forma de `params` para plantillas de regla que lo requieren.

    `rule_template`/`params` son texto libre a propósito (ver core/rule_names.py)
    para no acoplar el catálogo de reglas del motor Rust al backend, pero
    `custom_field_check` sí tiene una forma de params conocida y merece
    validarse aquí para no descubrir un error de tipeo solo tras lanzar
    la verificación y ver "NO_EVALUADA" en el motor.
    """
    if rule_template != "custom_field_check":
        return
    field = params.get("field")
    if not isinstance(field, str) or not field.strip():
        raise ValidationError("La regla personalizada requiere un 'field' no vacío.")
    artifact_type = params.get("artifact_type")
    if not isinstance(artifact_type, str) or not artifact_type.strip():
        raise ValidationError("La regla personalizada requiere un 'artifact_type' no vacío.")
    operator = params.get("operator", "non_empty")
    if operator not in CUSTOM_FIELD_CHECK_OPERATORS:
        raise ValidationError(
            f"Operador de regla personalizada no soportado: '{operator}'. "
            f"Valores permitidos: {', '.join(sorted(CUSTOM_FIELD_CHECK_OPERATORS))}."
        )
    if operator != "non_empty" and "value" not in params:
        raise ValidationError(f"El operador '{operator}' requiere un 'value' de comparación.")


class ProfileService(ManageProfileUseCase, IProfileService):
    def __init__(
        self,
        profile_repository: IProfileRepository,
        rule_repository: IVerificationRuleRepository,
        *,
        audit_logger: IAuditLogger,
        schedule_is_valid: Callable[[str], bool],
    ) -> None:
        super().__init__(profile_repository, rule_repository)
        self._audit_logger = audit_logger
        self._schedule_is_valid = schedule_is_valid

    async def create_profile(
        self,
        organization_id: UUID,
        name: str,
        description: str = "",
        is_default: bool = False,
        requested_by: Optional[UUID] = None,
    ) -> VerificationProfile:
        created = await super().create_profile(organization_id, name, description, is_default)
        self._audit_logger.log(AuditEntry(
            event=AuditEvent.PROFILE_CREATED,
            user_id=requested_by or uuid4(),
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
        schedule: Optional[str] | EllipsisType = ...,
        requested_by: Optional[UUID] = None,
    ) -> VerificationProfile:
        if schedule is not ...:
            _validate_schedule(schedule, self._schedule_is_valid)
        updated = await super().update_profile(profile_id, name, description, is_default, schedule)
        self._audit_logger.log(AuditEntry(
            event=AuditEvent.PROFILE_UPDATED,
            user_id=uuid4(),
            organization_id=updated.organization_id,
            resource_type="profile",
            resource_id=profile_id,
            details={"name": updated.name, "schedule": updated.schedule},
        ))
        _log.info("Profile updated: id=%s org=%s", profile_id, updated.organization_id)
        return updated

    async def duplicate_profile(
        self, profile_id: UUID, new_name: str, requested_by: Optional[UUID] = None
    ) -> VerificationProfile:
        return await super().duplicate_profile(profile_id, new_name)

    async def delete_profile(self, profile_id: UUID, requested_by: UUID) -> None:
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Perfil no encontrado: {profile_id}")
        if profile.is_system:
            raise ValidationError("El perfil del sistema no puede ser eliminado.")
        org_id = profile.organization_id
        await self._profile_repo.delete(profile_id)
        self._audit_logger.log(AuditEntry(
            event=AuditEvent.PROFILE_DELETED,
            user_id=uuid4(),
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
        if profile.is_default:
            raise ValidationError("No se pueden agregar reglas al perfil por defecto.")
        _validate_rule_params(rule_template, params or {})

        rule = VerificationRule(
            profile_id=profile_id,
            rule_template=rule_template,
            severity=severity,
            params=params or {},
            connector_instance_id=connector_instance_id,
            display_order=display_order,
        )
        created = await self._rule_repo.create(rule)
        self._audit_logger.log(AuditEntry(
            event=AuditEvent.RULE_CREATED,
            user_id=uuid4(),
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
        profile = await self._profile_repo.get_by_id(rule.profile_id)
        if profile and profile.is_default:
            raise ValidationError("No se pueden modificar reglas del perfil por defecto.")
        if params is not None:
            _validate_rule_params(rule.rule_template, params)
        updated = await super().update_rule(rule_id, severity, connector_instance_id, params, display_order, is_active)
        self._audit_logger.log(AuditEntry(
            event=AuditEvent.RULE_UPDATED,
            user_id=uuid4(),
            organization_id=None,
            resource_type="rule",
            resource_id=rule_id,
            details={"template": updated.rule_template},
        ))
        _log.info("Rule updated: id=%s", rule_id)
        return updated

    async def delete_rule(self, rule_id: UUID, requested_by: UUID) -> None:
        rule = await self._rule_repo.get_by_id(rule_id)
        if not rule:
            raise EntityNotFoundError(f"Regla no encontrada: {rule_id}")
        profile = await self._profile_repo.get_by_id(rule.profile_id)
        if profile and profile.is_default:
            raise ValidationError("No se pueden eliminar reglas del perfil por defecto.")
        await super().delete_rule(rule_id, requested_by)
