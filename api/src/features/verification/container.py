from __future__ import annotations

from features.notifications.infrastructure.gateways.outbound_webhook_sender import OUTBOUND_CHANNEL_TYPES, send_outbound_notification
from features.verification.application.use_cases.notify_result import NotifyResult
from features.verification.application.use_cases.run_verification import RunVerification
from features.verification.infrastructure.gateways.http_rule_engine_client import HttpRuleEngineClient
from shared.infrastructure.config import get_settings
from shared.infrastructure.smtp_mailer import email_service
from shared.infrastructure.system_clock import SystemClock
from bootstrap.repositories import get_notification_repository, get_user_repository, get_connector_registry, get_connector_repository

from bootstrap.repositories import get_profile_repository, get_release_repository, get_rule_repository, get_task_queue, get_template_repository
from croniter import croniter
from fastapi import Depends
from features.connectors.infrastructure.gateways import create_registered_connector_registry
from features.connectors.infrastructure.persistence.connector_repository import SqlConnectorRepository
from features.projects_releases.infrastructure.persistence.release_repository import SqlReleaseRepository
from features.verification.application.ports.i_profile_service import IProfileService
from features.verification.application.ports.i_task_service import ITaskService
from features.verification.application.ports.i_template_service import ITemplateService
from features.verification.application.ports.i_verification_service import IVerificationService
from features.verification.application.use_cases.profile_service import ProfileService
from features.verification.application.use_cases.task_service import TaskService
from features.verification.application.use_cases.template_service import TemplateService
from features.verification.application.use_cases.verification_service import VerificationService
from features.verification.infrastructure.persistence.verification_outcome_store import SqlVerificationOutcomeStore
from features.verification.infrastructure.persistence.profile_repository import SqlProfileRepository
from features.verification.infrastructure.persistence.rule_repository import SqlVerificationRuleRepository
from features.verification.infrastructure.persistence.verification_result_repository import SqlVerificationResultRepository
from shared.infrastructure.queue.celery_task_queue import CeleryTaskQueue
from shared.infrastructure.audit_db import get_audit_logger
from shared.infrastructure.fernet_encryptor import create_credential_encryptor


def get_verification_service(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
) -> IVerificationService:
    verification_repo = SqlVerificationResultRepository()
    task_queue = CeleryTaskQueue()
    connector_registry = create_registered_connector_registry()
    connector_repo = SqlConnectorRepository()
    return VerificationService(
        release_repository=release_repo,
        verification_repository=verification_repo,
        task_queue=task_queue,
        connector_registry=connector_registry,
        connector_repository=connector_repo,
        credential_encryptor=create_credential_encryptor(),
        audit_logger=get_audit_logger(),
    )


def get_profile_service(
    profile_repo: SqlProfileRepository = Depends(get_profile_repository),
    rule_repo: SqlVerificationRuleRepository = Depends(get_rule_repository),
) -> IProfileService:
    return ProfileService(
        profile_repository=profile_repo,
        rule_repository=rule_repo,
        audit_logger=get_audit_logger(),
        schedule_is_valid=croniter.is_valid,
    )


def get_task_service(
    task_queue: CeleryTaskQueue = Depends(get_task_queue),
) -> ITaskService:
    return TaskService(
        task_queue=task_queue,
    )


def get_template_service() -> ITemplateService:
    template_repo = get_template_repository()
    profile_repo = get_profile_repository()
    return TemplateService(
        template_repository=template_repo,
        profile_repository=profile_repo,
        audit_logger=get_audit_logger(),
    )


def get_run_verification() -> RunVerification:
    settings = get_settings()
    notify = NotifyResult(
        users=get_user_repository(),
        notifications=get_notification_repository(),
        send=send_outbound_notification,
        mailer=email_service,
        outbound_channels=OUTBOUND_CHANNEL_TYPES,
        app_base_url=settings.app_base_url,
    )
    return RunVerification(
        releases=get_release_repository(),
        outcomes=SqlVerificationOutcomeStore(SqlReleaseRepository),
        profiles=get_profile_repository(),
        connectors=get_connector_repository(),
        registry=get_connector_registry(),
        encryptor=create_credential_encryptor(),
        engine=HttpRuleEngineClient(settings.engine_url, settings.engine_api_key),
        clock=SystemClock(),
        notify=notify.execute,
    )
