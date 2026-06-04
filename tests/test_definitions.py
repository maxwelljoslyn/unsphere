import datetime as dt

import pytest

from achievements.achievements import registry
from achievements.middleware import check_achievements
from workouts.models import CardioExercise, Movement, Workout

EXPECTED_KEYS = {
    "one_workout",
    "ten_workouts",
    "fifty_workouts",
    "first_cardio",
    "first_strength",
}


def test_definitions_registered_in_global_registry():
    assert EXPECTED_KEYS <= set(registry)


@pytest.mark.django_db
def test_one_workout_threshold(django_user_model):
    user = django_user_model.objects.create_user(username="thresh", password="pw")
    adef = registry["one_workout"]
    assert adef.threshold(user) is False
    Workout.objects.create(
        user=user, date=dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc)
    )
    assert adef.threshold(user) is True


@pytest.mark.django_db
def test_first_cardio_awarded_via_checker(django_user_model):
    user = django_user_model.objects.create_user(username="cardio", password="pw")
    movement = Movement.objects.create(name="elliptical", kind=Movement.CARDIO)
    workout = Workout.objects.create(
        user=user, date=dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc)
    )
    from unsphere.units import u

    CardioExercise.objects.create(
        workout=workout, movement=movement, distance=u("2 miles")
    )

    earned = {a.key for a in check_achievements(user)}
    assert "one_workout" in earned
    assert "first_cardio" in earned
    assert "first_strength" not in earned
