import logging
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from features.verification.application.ports.i_verification_service import IVerificationService
from features.verification.application.ports.i_profile_repository import IProfileRepository
from features.projects_releases.application.ports.i_release_repository import IReleaseRepository
from features.verification.domain.verification_profile import VerificationProfile
from shared.domain.enums import ReleaseStatus
from shared.domain.exceptions import ValidationError
from shared.application.i_clock import IClock


_slog = logging.getLogger(__name__)

_RE_VERIFIABLE_STATUSES = [ReleaseStatus.VALIDA, ReleaseStatus.CON_ADVERTENCIAS, ReleaseStatus.NO_VALIDA]
_SYSTEM_ACTOR = UUID(int=0)


class CheckScheduledVerifications:
    def __init__(
        self, *, profiles: IProfileRepository, releases: IReleaseRepository,
        verifications: IVerificationService, clock: IClock,
        is_due: Callable[[VerificationProfile, datetime], bool],
    ) -> None:
        self._profiles = profiles
        self._releases = releases
        self._verifications = verifications
        self._clock = clock
        self._is_due = is_due

    async def execute(self) -> dict[str, int]:
        now = self._clock.now()
        profiles = await self._profiles.list_scheduled()

        triggered = 0
        skipped = 0
        errors = 0

        for profile in profiles:
            if not self._is_due(profile, now):
                continue

            await self._profiles.update_schedule_last_run(profile.id, now)

            releases = await self._releases.list_by_profile(profile.id, statuses=_RE_VERIFIABLE_STATUSES)
            for release in releases:
                try:
                    await self._verifications.launch_verification(
                        release.id, requested_by=_SYSTEM_ACTOR, triggered_by="scheduled"
                    )
                    triggered += 1
                except ValidationError:
                    # p.ej. la release ya no tiene artefactos o cambió de estado entre
                    # la consulta y el lanzamiento: no es un fallo del scheduler.
                    skipped += 1
                except Exception:
                    errors += 1
                    _slog.exception(
                        "Scheduled verification failed to launch: release=%s profile=%s", release.id, profile.id
                    )

        result = {"profiles_checked": len(profiles), "triggered": triggered, "skipped": skipped, "errors": errors}
        _slog.info("Scheduled verification sweep: %s", result)
        return result
