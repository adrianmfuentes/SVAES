import logging
from datetime import datetime
from typing import Any

from croniter import croniter


_slog = logging.getLogger(__name__)


def _is_due(profile: Any, now: datetime) -> bool:
    if not profile.schedule:
        return False
    reference = profile.schedule_last_run_at or profile.created_at
    try:
        cron = croniter(profile.schedule, reference)
    except (ValueError, KeyError):
        _slog.warning("Profile %s has an invalid schedule '%s', skipping", profile.id, profile.schedule)
        return False
    next_fire = cron.get_next(datetime)
    return next_fire <= now
