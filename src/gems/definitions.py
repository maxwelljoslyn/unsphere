"""Gem rule definitions.

Importing this module registers every GemRuleDef into the global registry. It is
imported from GemsConfig.ready() so registration happens at startup.

Each rule's `entitled(user)` returns the cumulative number of gems the user
should have earned from that rule. Unlike achievement thresholds these are not a
single cheap query: the cardio rules load the user's cardio exercises and sum
their pint quantities in Python, because distances/durations are stored as
strings (PintField is a CharField) and the database can't SUM them. That's fine
at per-user scale but heavier than an .exists(), so keep the rule set small.
"""

from __future__ import annotations

import math
from zoneinfo import ZoneInfo

from .gems import GemRuleDef


def _total_cardio_miles(user) -> float:
    from workouts.models import CardioExercise

    total_mi = 0.0
    for ex in CardioExercise.objects.filter(
        workout__user=user, workout__confirmed_at__isnull=False
    ):
        if ex.distance is None:
            continue
        try:
            total_mi += float(ex.distance.to("mile").magnitude)
        except Exception:
            # Distance recorded in a non-length unit; it can't count toward
            # mileage, so skip it rather than blow up the whole grant.
            continue
    return total_mi


def _total_cardio_minutes(user) -> float:
    from workouts.models import CardioExercise

    total_min = 0.0
    for ex in CardioExercise.objects.filter(
        workout__user=user, workout__confirmed_at__isnull=False
    ):
        if ex.duration is None:
            continue
        try:
            total_min += float(ex.duration.to("minute").magnitude)
        except Exception:
            continue
    return total_min


def _active_days(user) -> int:
    from workouts.models import Workout

    days = set()
    for w in Workout.objects.filter(user=user, confirmed_at__isnull=False):
        try:
            tz = ZoneInfo(w.timezone or "UTC")
        except Exception:
            tz = ZoneInfo("UTC")
        # `date` is a UTC instant; the gem counts the *local* calendar day the
        # workout was logged in, so two workouts on the same local day are one.
        days.add(w.date.astimezone(tz).date())
    return len(days)


GemRuleDef(
    key="cardio_distance",
    name="+1 gem per cumulative mile of cardio",
    category="cardio",
    entitled=lambda user: int(math.floor(_total_cardio_miles(user))),
)

GemRuleDef(
    key="cardio_duration",
    name="+1 gem per cumulative 10 minutes of cardio",
    category="cardio",
    entitled=lambda user: int(_total_cardio_minutes(user) // 10),
)

GemRuleDef(
    key="active_days",
    name="+1 gem per day where you worked out at least once",
    category="consistency",
    # 1 gem per distinct local calendar day with a workout.
    entitled=_active_days,
)
