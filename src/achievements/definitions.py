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

    return Workout.objects.filter(user=user).count()


def _achievement_count(user) -> int:
    from achievements.models import Achievement

    return Achievement.objects.filter(user=user).count()


def _has_cardio(user) -> bool:
    from workouts.models import CardioExercise

    return CardioExercise.objects.filter(workout__user=user).exists()


def _has_strength(user) -> bool:
    from workouts.models import StrengthExercise

    return StrengthExercise.objects.filter(workout__user=user).exists()


AchievementDef(
    key="one_workout",
    name="Getting Started",
    description="You logged your first workout.",
    threshold=lambda user: _workout_count(user) >= 1,
)

AchievementDef(
    key="ten_workouts",
    name="Regular",
    description="You've logged 10 workouts.",
    threshold=lambda user: _workout_count(user) >= 10,
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
