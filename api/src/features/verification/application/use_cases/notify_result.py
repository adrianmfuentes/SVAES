import logging
import uuid
from collections.abc import Set

from features.notifications.application.ports.i_notification_repository import INotificationRepository
from features.notifications.application.ports.i_notification_sender import INotificationSender
from features.identity.application.ports.i_user_repository import IUserRepository
from features.projects_releases.domain.release import Release
from features.verification.domain.verification_result import VerificationResult
from shared.domain.enums import ReleaseStatus, VerdictType
from shared.application.i_mailer import IMailer


_wlog = logging.getLogger(__name__)


def _is_drift(release: Release, saved_result: VerificationResult, triggered_by: str) -> bool:
    """Una release re-verificada automáticamente (scheduler) que pasa de un
    veredicto positivo a NO_VALIDA sin que nadie haya tocado su configuración:
    el estado externo cambió por su cuenta entre verificaciones. Solo aplica a
    disparos `triggered_by="scheduled"`; una re-verificación manual del mismo
    tipo no es "drift", es simplemente el usuario comprobando de nuevo.
    """
    if triggered_by != "scheduled":
        return False
    if saved_result.verdict != VerdictType.INVALID:
        return False
    return release.previous_status in (ReleaseStatus.VALIDA, ReleaseStatus.CON_ADVERTENCIAS)


class NotifyResult:
    def __init__(
        self, *, users: IUserRepository, notifications: INotificationRepository,
        send: INotificationSender, mailer: IMailer, outbound_channels: Set[str], app_base_url: str,
    ) -> None:
        self._users = users
        self._notifications = notifications
        self._send = send
        self._mailer = mailer
        self._outbound_channels = outbound_channels
        self._app_base_url = app_base_url

    async def _dispatch_org_channels(self, release: Release, event_type: str, verdict_value: str, release_id: uuid.UUID) -> None:
        """Empuja `event_type` a los canales salientes (Slack/MS Teams/genérico) de la
        organización, reutilizando el patrón declarativo de GenericHttpConnector pero
        en dirección de salida. Independiente de las preferencias por-usuario: es un
        aviso de equipo, no de una persona concreta.
        """
        organization_id = getattr(release, "organization_id", None)
        if not organization_id:
            return

        try:
            channels = await self._notifications.list_channels(organization_id)
        except Exception:
            _wlog.exception("Failed to list notification channels for org %s", organization_id)
            return

        ctx = {
            "release_name": release.name,
            "version": release.version,
            "verdict": verdict_value,
            "project_name": getattr(release, "project_name", None),
            "release_url": f"{self._app_base_url}/app/releases/{release_id}",
        }
        for channel in channels:
            if not channel.enabled or channel.channel_type not in self._outbound_channels:
                continue
            await self._send(channel, event_type, ctx)


    async def execute(
        self, release_id: uuid.UUID, release: Release, saved_result: VerificationResult, triggered_by: str,
    ) -> None:
        verdict_value = saved_result.verdict.value
        drift = _is_drift(release, saved_result, triggered_by)
        if drift:
            event_type = "DRIFT_DETECTED"
        elif verdict_value in ("VALID", "VALID_WITH_WARNINGS"):
            event_type = "RELEASE_VALIDATED"
        else:
            event_type = "RELEASE_INVALIDATED"

        await self._dispatch_org_channels(release, event_type, verdict_value, release_id)

        user = await self._users.get_by_id(release.created_by)
        if not user:
            _wlog.warning("Cannot notify: user not found for release %s (created_by=%s)", release_id, release.created_by)
            return

        # DRIFT_DETECTED no tiene preferencia propia (ver PREFERENCE_EVENT_MAP en
        # notification_service.py): para el email al propietario se trata como una
        # invalidación normal, la distinción "drift" queda en el mensaje a los canales de equipo.
        subscription_event = "RELEASE_INVALIDATED" if drift else event_type
        subscription = await self._notifications.get_subscription(user.id, subscription_event)
        if subscription is not None and not subscription.enabled:
            _wlog.info("Skipping notification for release %s: user %s has disabled %s", release_id, user.id, subscription_event)
            return

        try:
            await self._mailer.send_verification_result_email(
                to_email=user.email,
                to_name=user.display_name or user.email,
                release_name=release.name,
                verdict=verdict_value,
                release_id=str(release_id),
            )
        except Exception:
            _wlog.exception("Failed to send verification email for release %s to %s", release_id, user.email)
