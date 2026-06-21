import datetime as dt

import pytest
from django.urls import reverse

from workouts import analytics
from workouts.models import CardioExercise, Movement, Workout
from unsphere.units import u

UTC = dt.timezone.utc


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="alice", password="pw")


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def cardio_movement(db):
    # "running" is seeded by a data migration, so reuse it rather than colliding
    # with the unique-name constraint.
    movement, _ = Movement.objects.get_or_create(
        name="running", defaults={"kind": Movement.CARDIO}
    )
    return movement


def make_workout(user, when, *, confirmed=True, timezone="UTC"):
    return Workout.objects.create(
        user=user,
        date=when,
        timezone=timezone,
        confirmed_at=(when if confirmed else None),
    )


def add_cardio(workout, movement, *, distance=None, duration=None):
    return CardioExercise.objects.create(
        workout=workout,
        movement=movement,
        distance=u(distance) if distance else None,
        duration=u(duration) if duration else None,
    )


# --- view -------------------------------------------------------------------


def test_stats_requires_login(client):
    resp = client.get(reverse("stats"))
    assert resp.status_code == 302
    assert "/login" in resp.url or "/accounts/login" in resp.url


def test_stats_renders_for_authenticated_user(auth_client):
    resp = auth_client.get(reverse("stats"))
    assert resp.status_code == 200
    assert resp.context["total_workouts"] == 0
    assert resp.context["current_streak"] == 0
    assert resp.context["cardio_series"] == []
    assert resp.context["day_counts"] == []


def test_stats_nav_link_present(auth_client):
    resp = auth_client.get(reverse("stats"))
    assert reverse("stats").encode() in resp.content


# --- total_confirmed_workouts ----------------------------------------------


def test_total_counts_only_confirmed(user):
    make_workout(user, dt.datetime(2026, 1, 1, 12, tzinfo=UTC))
    make_workout(user, dt.datetime(2026, 1, 2, 12, tzinfo=UTC))
    make_workout(user, dt.datetime(2026, 1, 3, 12, tzinfo=UTC), confirmed=False)
    assert analytics.total_confirmed_workouts(user) == 2


# --- current_streak ---------------------------------------------------------


def test_streak_counts_consecutive_days_ending_today(user):
    for day in (18, 19, 20):
        make_workout(user, dt.datetime(2026, 6, day, 9, tzinfo=UTC))
    today = dt.date(2026, 6, 20)
    assert analytics.current_streak(user, today=today) == 3


def test_streak_allows_today_untrained_if_yesterday_done(user):
    make_workout(user, dt.datetime(2026, 6, 19, 9, tzinfo=UTC))
    assert analytics.current_streak(user, today=dt.date(2026, 6, 20)) == 1


def test_streak_lapses_when_gap_exceeds_one_day(user):
    make_workout(user, dt.datetime(2026, 6, 17, 9, tzinfo=UTC))
    assert analytics.current_streak(user, today=dt.date(2026, 6, 20)) == 0


def test_streak_stops_at_first_gap(user):
    # Trained the 20th and 19th, skipped the 18th, trained the 17th.
    for day in (17, 19, 20):
        make_workout(user, dt.datetime(2026, 6, day, 9, tzinfo=UTC))
    assert analytics.current_streak(user, today=dt.date(2026, 6, 20)) == 2


def test_streak_dedupes_multiple_workouts_same_day(user):
    make_workout(user, dt.datetime(2026, 6, 20, 7, tzinfo=UTC))
    make_workout(user, dt.datetime(2026, 6, 20, 18, tzinfo=UTC))
    assert analytics.current_streak(user, today=dt.date(2026, 6, 20)) == 1


def test_streak_uses_local_day(user):
    # 03:00 UTC on the 20th is still the 19th in Los Angeles; the workout should
    # land on the 19th, keeping a streak with an LA-local workout on the 20th.
    la = "America/Los_Angeles"
    make_workout(user, dt.datetime(2026, 6, 20, 3, tzinfo=UTC), timezone=la)
    make_workout(user, dt.datetime(2026, 6, 20, 20, tzinfo=UTC), timezone=la)
    assert analytics.current_streak(user, today=dt.date(2026, 6, 20)) == 2


# --- cardio_cumulative_series ----------------------------------------------


def test_cardio_cumulative_accumulates(user, cardio_movement):
    w1 = make_workout(user, dt.datetime(2026, 6, 1, 9, tzinfo=UTC))
    add_cardio(w1, cardio_movement, distance="3 mile", duration="30 min")
    w2 = make_workout(user, dt.datetime(2026, 6, 5, 9, tzinfo=UTC))
    add_cardio(w2, cardio_movement, distance="2 mile", duration="20 min")

    series = analytics.cardio_cumulative_series(user)
    assert series == [
        {"date": "2026-06-01", "miles": 3.0, "minutes": 30.0},
        {"date": "2026-06-05", "miles": 5.0, "minutes": 50.0},
    ]


def test_cardio_cumulative_converts_units(user, cardio_movement):
    w = make_workout(user, dt.datetime(2026, 6, 1, 9, tzinfo=UTC))
    add_cardio(w, cardio_movement, distance="5 kilometer", duration="90 second")
    series = analytics.cardio_cumulative_series(user)
    assert series[0]["miles"] == pytest.approx(3.11, abs=0.01)
    assert series[0]["minutes"] == pytest.approx(1.5, abs=0.01)


def test_cardio_cumulative_sums_same_day(user, cardio_movement):
    w1 = make_workout(user, dt.datetime(2026, 6, 1, 7, tzinfo=UTC))
    add_cardio(w1, cardio_movement, distance="3 mile")
    w2 = make_workout(user, dt.datetime(2026, 6, 1, 18, tzinfo=UTC))
    add_cardio(w2, cardio_movement, distance="2 mile")
    series = analytics.cardio_cumulative_series(user)
    assert series == [{"date": "2026-06-01", "miles": 5.0, "minutes": 0.0}]


# --- workout_day_counts -----------------------------------------------------


def test_day_counts(user):
    make_workout(user, dt.datetime(2026, 6, 1, 7, tzinfo=UTC))
    make_workout(user, dt.datetime(2026, 6, 1, 18, tzinfo=UTC))
    make_workout(user, dt.datetime(2026, 6, 3, 9, tzinfo=UTC))
    make_workout(user, dt.datetime(2026, 6, 4, 9, tzinfo=UTC), confirmed=False)
    assert analytics.workout_day_counts(user) == [
        {"date": "2026-06-01", "count": 2},
        {"date": "2026-06-03", "count": 1},
    ]
