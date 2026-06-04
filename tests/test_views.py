import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse

from workouts.models import CardioExercise, Movement, StrengthExercise, Workout


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="alice", password="pw")


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def workout(user):
    return Workout.objects.create(
        user=user, date=dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc)
    )


@pytest.fixture
def cardio_movement(db):
    return Movement.objects.create(name="cycling", kind=Movement.CARDIO)


@pytest.fixture
def strength_movement(db):
    return Movement.objects.create(name="squat", kind=Movement.STRENGTH)


# --- Workout CRUD -----------------------------------------------------------


@pytest.mark.django_db
def test_workout_create(auth_client, user):
    resp = auth_client.post(
        reverse("workout-create"),
        {
            "date": "2026-02-02T18:30",
            "timezone": "America/Los_Angeles",
            "notes": "leg day",
        },
    )
    assert resp.status_code == 302
    workout = Workout.objects.get(user=user, notes="leg day")
    assert workout.timezone == "America/Los_Angeles"
    # The wall-clock 18:30 is interpreted in the submitted zone, then stored as
    # a UTC instant. Converting back to that zone yields exactly what was typed.
    local = workout.date.astimezone(ZoneInfo("America/Los_Angeles"))
    assert (local.year, local.month, local.day, local.hour, local.minute) == (
        2026,
        2,
        2,
        18,
        30,
    )


@pytest.mark.django_db
def test_workout_edit(auth_client, workout):
    resp = auth_client.post(
        reverse("workout-edit", args=[workout.pk]),
        {
            "date": "2026-03-03T07:15",
            "timezone": "America/New_York",
            "notes": "updated",
        },
    )
    assert resp.status_code == 302
    workout.refresh_from_db()
    assert workout.notes == "updated"
    assert workout.timezone == "America/New_York"
    local = workout.date.astimezone(ZoneInfo("America/New_York"))
    assert (local.year, local.month, local.day, local.hour, local.minute) == (
        2026,
        3,
        3,
        7,
        15,
    )


@pytest.mark.django_db
def test_workout_delete(auth_client, workout):
    resp = auth_client.post(reverse("workout-delete", args=[workout.pk]))
    assert resp.status_code == 302
    assert not Workout.objects.filter(pk=workout.pk).exists()


@pytest.mark.django_db
def test_workout_detail_shows_time_in_origin_zone_with_label(auth_client, user):
    w = Workout.objects.create(
        user=user,
        date=dt.datetime(2026, 2, 2, 18, 30, tzinfo=ZoneInfo("America/Los_Angeles")),
        timezone="America/Los_Angeles",
    )
    content = auth_client.get(reverse("workout-detail", args=[w.pk])).content.decode()
    assert "Feb 2, 2026, 18:30" in content
    assert "PST" in content  # February -> Pacific Standard Time, regardless of viewer


@pytest.mark.django_db
def test_workout_detail_scoped_to_owner(client, django_user_model, workout):
    other = django_user_model.objects.create_user(username="bob", password="pw")
    client.force_login(other)
    resp = client.get(reverse("workout-detail", args=[workout.pk]))
    assert resp.status_code == 404


# --- Cardio exercise add (HTMX) ---------------------------------------------


@pytest.mark.django_db
def test_cardio_add_happy_path(auth_client, workout, cardio_movement):
    resp = auth_client.post(
        reverse("cardio-exercise-add", args=[workout.pk]),
        {
            "movement": cardio_movement.pk,
            "distance_0": "5",
            "distance_1": "miles",
            "duration_0": "",
            "duration_1": "",
            "notes": "",
        },
    )
    assert resp.status_code == 200
    assert workout.cardioexercises.count() == 1
    # success partial restores the add buttons
    assert b"add-exercise-area" in resp.content


@pytest.mark.django_db
def test_cardio_add_validation_failure(auth_client, workout, cardio_movement):
    resp = auth_client.post(
        reverse("cardio-exercise-add", args=[workout.pk]),
        {
            "movement": cardio_movement.pk,
            "distance_0": "",
            "distance_1": "",
            "duration_0": "",
            "duration_1": "",
            "notes": "",
        },
    )
    assert resp.status_code == 200
    assert workout.cardioexercises.count() == 0
    assert b"at least one" in resp.content.lower()


# --- Strength exercise add (HTMX) -------------------------------------------


@pytest.mark.django_db
def test_strength_add_happy_path(auth_client, workout, strength_movement):
    resp = auth_client.post(
        reverse("strength-exercise-add", args=[workout.pk]),
        {
            "movement": strength_movement.pk,
            "sets": "3",
            "reps": "10",
            "weight_0": "135",
            "weight_1": "lbs",
            "notes": "",
        },
    )
    assert resp.status_code == 200
    assert workout.strengthexercises.count() == 1


# --- Exercise edit / delete (HTMX) ------------------------------------------


@pytest.mark.django_db
def test_cardio_edit(auth_client, workout, cardio_movement):
    from unsphere.units import u

    ex = CardioExercise.objects.create(
        workout=workout, movement=cardio_movement, distance=u("3 miles")
    )
    resp = auth_client.post(
        reverse("cardio-exercise-edit", args=[ex.pk]),
        {
            "movement": cardio_movement.pk,
            "distance_0": "6",
            "distance_1": "miles",
            "duration_0": "",
            "duration_1": "",
            "notes": "longer",
        },
    )
    assert resp.status_code == 200
    ex.refresh_from_db()
    assert ex.distance == u("6 miles")
    assert ex.notes == "longer"


@pytest.mark.django_db
def test_cardio_delete(auth_client, workout, cardio_movement):
    from unsphere.units import u

    ex = CardioExercise.objects.create(
        workout=workout, movement=cardio_movement, distance=u("3 miles")
    )
    resp = auth_client.delete(reverse("cardio-exercise-delete", args=[ex.pk]))
    assert resp.status_code == 200
    assert not CardioExercise.objects.filter(pk=ex.pk).exists()


@pytest.mark.django_db
def test_strength_delete(auth_client, workout, strength_movement):
    ex = StrengthExercise.objects.create(
        workout=workout, movement=strength_movement, sets=3, reps=10
    )
    resp = auth_client.delete(reverse("strength-exercise-delete", args=[ex.pk]))
    assert resp.status_code == 200
    assert not StrengthExercise.objects.filter(pk=ex.pk).exists()


# --- Login required ---------------------------------------------------------


@pytest.mark.django_db
def test_workout_list_requires_login(client):
    resp = client.get(reverse("workout-list"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.url
