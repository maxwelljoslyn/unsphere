"""Per-user workout analytics.

These helpers live in the ``workouts`` app — the owner of the underlying data —
rather than in the ``stats`` app, so anything can import them: the Stats page is
the biggest consumer today, but (for example) future streak-based achievements
can call :func:`current_streak` directly, the same way achievement definitions
lean on the gem helpers. Keep this module free of presentation concerns; it
returns plain numbers and JSON-ready dicts, never HTML.

Only *confirmed* workouts count (a draft being assembled exercise-by-exercise
must not move these numbers), matching how gems and achievements are gated.

Every workout stores its ``date`` as a UTC instant alongside the IANA
``timezone`` it was logged in; a workout's calendar day is therefore its instant
rendered in *that* zone, so a late-night session lands on the day the user
actually trained, regardless of where the server lives.
"""

import datetime as dt
from collections import defaultdict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone

from .models import CardioExercise, StrengthExercise, Workout


def _safe_zone(name: str) -> ZoneInfo:
    """The workout's zone, falling back to the project default if it's unknown."""
    try:
        return ZoneInfo(name or settings.TIME_ZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(settings.TIME_ZONE)


def _confirmed(user):
    return Workout.objects.filter(user=user, confirmed_at__isnull=False)


def _local_day(workout: Workout) -> dt.date:
    return workout.date.astimezone(_safe_zone(workout.timezone)).date()


def total_confirmed_workouts(user) -> int:
    """How many confirmed workouts the user has logged, all time."""
    return _confirmed(user).count()


def total_exercises_logged(user) -> int:
    """How many exercises the user has logged across confirmed workouts.

    Both cardio and strength exercises count, so a workout with two cardio and
    one strength movement contributes three. Drafts are excluded, matching every
    other figure on the dashboard.
    """
    confirmed = {"workout__user": user, "workout__confirmed_at__isnull": False}
    return (
        CardioExercise.objects.filter(**confirmed).count()
        + StrengthExercise.objects.filter(**confirmed).count()
    )


def local_workout_days(user) -> set[dt.date]:
    """The set of distinct local calendar days on which the user trained."""
    return {_local_day(w) for w in _confirmed(user).only("date", "timezone")}


def _today_for(user) -> dt.date:
    """ "Today" from the user's perspective.

    Anchored to the timezone of their most recent workout, so the streak doesn't
    spuriously break (or extend) just because the server clock is in a different
    zone than the user. Falls back to the project default zone when there are no
    workouts to read a zone from.
    """
    latest = _confirmed(user).order_by("-date").only("timezone").first()
    zone = _safe_zone(latest.timezone) if latest else ZoneInfo(settings.TIME_ZONE)
    return timezone.now().astimezone(zone).date()


def current_streak(user, today: dt.date | None = None) -> int:
    """Length of the user's current run of consecutive training days.

    A streak is "current" only if it reaches today or yesterday; if the most
    recent workout is older than that, the run has lapsed and the streak is 0.
    Counting back stops at the first gap. ``today`` is injectable for testing.
    """
    days = local_workout_days(user)
    if not days:
        return 0
    if today is None:
        today = _today_for(user)

    last = max(days)
    # A workout today, or yesterday (today not yet trained), keeps the streak
    # alive; anything older means it has already been broken.
    if last < today - dt.timedelta(days=1):
        return 0

    streak = 0
    day = last
    while day in days:
        streak += 1
        day -= dt.timedelta(days=1)
    return streak


def workout_day_percentage(user, today: dt.date | None = None) -> int:
    """Share of days the user has trained, from their first workout to today.

    Distinct training days as a percentage of the inclusive calendar span that
    starts on the user's first confirmed workout and ends today — a "how often do
    I actually show up" figure. 0 when there are no workouts. ``today`` is
    injectable for testing.
    """
    days = local_workout_days(user)
    if not days:
        return 0
    if today is None:
        today = _today_for(user)
    span = (today - min(days)).days + 1
    return round(len(days) / span * 100)


def cardio_cumulative_series(user) -> list[dict]:
    """Running cumulative cardio totals: lifetime miles and minutes over time.

    One point per local day on which the user did cardio, carrying the totals
    accumulated *through* that day. Plotted with a step interpolation this draws
    a staircase that rises on each training day and stays flat in between — a
    monotonically increasing "miles/minutes logged so far" line. Distance and
    duration are independent (a workout may record either or both), so both
    cumulative tracks advance from the same per-day points. Sorted by date.
    """
    daily_miles: dict[dt.date, float] = defaultdict(float)
    daily_minutes: dict[dt.date, float] = defaultdict(float)

    qs = _confirmed(user).prefetch_related("cardioexercises")
    for w in qs:
        day = _local_day(w)
        for ex in w.cardioexercises.all():
            if ex.distance is not None:
                daily_miles[day] += float(ex.distance.to("mile").magnitude)
            if ex.duration is not None:
                daily_minutes[day] += float(ex.duration.to("minute").magnitude)

    series = []
    cum_miles = cum_minutes = 0.0
    for day in sorted(set(daily_miles) | set(daily_minutes)):
        cum_miles += daily_miles[day]
        cum_minutes += daily_minutes[day]
        series.append(
            {
                "date": day.isoformat(),
                "miles": round(cum_miles, 2),
                "minutes": round(cum_minutes, 1),
            }
        )
    return series


def cardio_lifetime_totals(series: list[dict]) -> dict:
    """Lifetime cardio miles and hours, read off a cumulative series.

    Takes the output of :func:`cardio_cumulative_series` rather than hitting the
    database again: the final point already carries the running totals, so the
    headline tiles and the line charts are computed from exactly the same data
    in a single pass. Returns zeroes for a user with no cardio.
    """
    if not series:
        return {"miles": 0.0, "hours": 0.0}
    last = series[-1]
    return {"miles": last["miles"], "hours": round(last["minutes"] / 60, 1)}


def workout_day_counts(user) -> list[dict]:
    """Confirmed-workout count per local day, for a calendar heatmap."""
    counts: dict[dt.date, int] = defaultdict(int)
    for w in _confirmed(user).only("date", "timezone"):
        counts[_local_day(w)] += 1
    return [
        {"date": day.isoformat(), "count": count}
        for day, count in sorted(counts.items())
    ]
