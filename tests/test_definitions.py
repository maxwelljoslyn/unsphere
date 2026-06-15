import datetime as dt

import pytest

from achievements.achievements import registry
from achievements.middleware import check_achievements
from gems.models import GemTransaction
from workouts.models import CardioExercise, Movement, Workout

EXPECTED_KEYS = {
    "one_workout",
    "ten_workouts",
    "fifty_workouts",
    "first_cardio",
    "first_strength",
    "first_gem",
}


def test_definitions_registered_in_global_registry():
    assert EXPECTED_KEYS <= set(registry)


@pytest.mark.django_db
def test_one_workout_threshold(django_user_model):
    user = django_user_model.objects.create_user(username="thresh", password="pw")
    adef = registry["one_workout"]
    assert adef.threshold(user) is False
    # A draft workout doesn't count.
    workout = Workout.objects.create(
        user=user, date=dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc)
    )
    assert adef.threshold(user) is False
    # Confirming it makes it count.
    workout.confirmed_at = dt.datetime(2026, 1, 1, 9, 0, tzinfo=dt.timezone.utc)
    workout.save(update_fields=["confirmed_at"])
    assert adef.threshold(user) is True


@pytest.mark.django_db
def test_first_cardio_awarded_via_checker(django_user_model):
    user = django_user_model.objects.create_user(username="cardio", password="pw")
    movement = Movement.objects.create(name="elliptical", kind=Movement.CARDIO)
    workout = Workout.objects.create(
        user=user,
        date=dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc),
        confirmed_at=dt.datetime(2026, 1, 1, 9, 0, tzinfo=dt.timezone.utc),
    )
    from unsphere.units import u

    CardioExercise.objects.create(
        workout=workout, movement=movement, distance=u("2 miles")
    )

    earned = {a.key for a in check_achievements(user)}
    assert "one_workout" in earned
    assert "first_cardio" in earned
    assert "first_strength" not in earned


@pytest.mark.django_db
def test_first_gem_threshold(django_user_model):
    user = django_user_model.objects.create_user(username="gemmer", password="pw")
    adef = registry["first_gem"]

    # No gems yet.
    assert adef.threshold(user) is False

    # A single credited gem clears the threshold.
    GemTransaction.objects.create(user=user, amount=1, rule_key="cardio_distance")
    assert adef.threshold(user) is True


@pytest.mark.django_db
def test_first_gem_threshold_tracks_lifetime_not_spendable_balance(django_user_model):
    """_has_gems counts gems ever earned, so spending them away keeps it met."""
    user = django_user_model.objects.create_user(username="spender", password="pw")
    adef = registry["first_gem"]

    GemTransaction.objects.create(user=user, amount=3, rule_key="active_days")
    assert adef.threshold(user) is True

    # Spend the whole balance: lifetime earnings are unchanged, so it stays met.
    GemTransaction.objects.create(user=user, amount=-3)
    assert adef.threshold(user) is True


@pytest.mark.django_db
def test_first_gem_awarded_via_checker(django_user_model):
    user = django_user_model.objects.create_user(username="gemcheck", password="pw")

    assert "first_gem" not in {a.key for a in check_achievements(user)}

    GemTransaction.objects.create(user=user, amount=2, rule_key="cardio_duration")
    assert "first_gem" in {a.key for a in check_achievements(user)}
