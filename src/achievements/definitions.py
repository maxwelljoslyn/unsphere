"""Achievement definitions.

Importing this module registers every AchievementDef into the global registry.
It is imported from AchievementsConfig.ready() so registration happens at startup.

Each threshold is a callable taking the user and returning a bool. Thresholds are
evaluated on every request by the middleware, so keep them cheap (a single
.exists()/.count() query each).
"""

from __future__ import annotations

from .achievements import AchievementDef


def _workout_count(user) -> int:
    from workouts.models import Workout

    return Workout.objects.filter(user=user, confirmed_at__isnull=False).count()


def _achievement_count(user) -> int:
    from achievements.models import Achievement

    return Achievement.objects.filter(user=user).count()


def _has_cardio(user) -> bool:
    from workouts.models import CardioExercise

    return CardioExercise.objects.filter(
        workout__user=user, workout__confirmed_at__isnull=False
    ).exists()


def _has_strength(user) -> bool:
    from workouts.models import StrengthExercise

    return StrengthExercise.objects.filter(
        workout__user=user, workout__confirmed_at__isnull=False
    ).exists()


def _has_gems(user) -> bool:
    from gems.middleware import lifetime_gems

    # Lifetime, not spendable balance: once earned, the achievement stays earned
    # even if the user later spends all their gems.
    return lifetime_gems(user) >= 1


AchievementDef(
    key="one_workout",
    name="Getting Started",
    description="You logged your first workout.",
    threshold=lambda user: _workout_count(user) >= 1,
)

AchievementDef(
    key="three_workouts",
    name="Warming Up",
    description="You've logged 3 workouts.",
    threshold=lambda user: _workout_count(user) >= 3,
)

AchievementDef(
    key="six_workouts",
    name="Hooked",
    description="You've logged 6 workouts.",
    threshold=lambda user: _workout_count(user) >= 6,
)

AchievementDef(
    key="ten_workouts",
    name="Commitment",
    description="You've logged 10 workouts.",
    threshold=lambda user: _workout_count(user) >= 10,
)

AchievementDef(
    key="fifteen_workouts",
    name="Greasing That Groove",
    description="You've logged 15 workouts.",
    threshold=lambda user: _workout_count(user) >= 15,
)

AchievementDef(
    key="twenty_workouts",
    name="Dedication",
    description="You've logged 20 workouts.",
    threshold=lambda user: _workout_count(user) >= 20,
)

AchievementDef(
    key="twenty_five_workouts",
    name="Quarter-Hundo",
    description="You've logged 25 workouts!",
    threshold=lambda user: _workout_count(user) >= 25,
)

AchievementDef(
    key="fifty_workouts",
    name="Committed",
    description="You've logged 50 workouts!",
    threshold=lambda user: _workout_count(user) >= 50,
)

AchievementDef(
    key="first_cardio",
    name="On the Move",
    description="You recorded your first cardio exercise.",
    threshold=_has_cardio,
)

AchievementDef(
    key="first_strength",
    name="Lifting Off",
    description="You recorded your first strength exercise.",
    threshold=_has_strength,
)

AchievementDef(
    key="metachievement",
    name="Metachievement",
    description="You earned an achievement. That's worth an achievement.",
    threshold=lambda user: _achievement_count(user) >= 1,
)

AchievementDef(
    key="pentachievement",
    name="Pentachievement",
    description="You've earned five achievements.",
    threshold=lambda user: _achievement_count(user) >= 5,
)

AchievementDef(
    key="megachievement",
    name="Megachievement",
    description="You've earned ten achievements!",
    threshold=lambda user: _achievement_count(user) >= 10,
)

AchievementDef(
    key="first_gem",
    name="Stats, Gems, and Webs",
    description="You earned your first gem.",
    threshold=lambda user: _has_gems(user),
)
