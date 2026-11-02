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
def test_workout_created_as_draft(auth_client, user):
    auth_client.post(
        reverse("workout-create"),
        {"date": "2026-02-02T18:30", "timezone": "UTC", "notes": "draft day"},
    )
    workout = Workout.objects.get(user=user, notes="draft day")
    assert workout.is_draft


@pytest.mark.django_db
def test_workout_confirm_sets_timestamp_and_is_idempotent(auth_client, workout):
    assert workout.is_draft
    resp = auth_client.post(reverse("workout-confirm", args=[workout.pk]))
    assert resp.status_code == 302
    workout.refresh_from_db()
    assert workout.confirmed_at is not None
    first = workout.confirmed_at

    # Re-confirming leaves the original timestamp untouched.
    auth_client.post(reverse("workout-confirm", args=[workout.pk]))
    workout.refresh_from_db()
    assert workout.confirmed_at == first


@pytest.mark.django_db
def test_workout_confirm_htmx_returns_saved_status(auth_client, workout):
    resp = auth_client.post(
        reverse("workout-confirm", args=[workout.pk]), HTTP_HX_REQUEST="true"
    )
    assert resp.status_code == 200
    assert b"Saved" in resp.content


@pytest.mark.django_db
def test_workout_confirm_rejects_get(auth_client, workout):
    resp = auth_client.get(reverse("workout-confirm", args=[workout.pk]))
    assert resp.status_code == 405


@pytest.mark.django_db
def test_workout_confirm_scoped_to_owner(client, django_user_model, workout):
    other = django_user_model.objects.create_user(username="mallory", password="pw")
    client.force_login(other)
    resp = client.post(reverse("workout-confirm", args=[workout.pk]))
    assert resp.status_code == 404


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
def test_workout_detail_draft_scoped_to_owner(client, django_user_model, workout):
    # `workout` is a draft; other users may not view it.
    other = django_user_model.objects.create_user(username="bob", password="pw")
    client.force_login(other)
    resp = client.get(reverse("workout-detail", args=[workout.pk]))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_workout_detail_confirmed_viewable_by_non_owner(
    client, django_user_model, user
):
    w = Workout.objects.create(
        user=user,
        date=dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc),
        confirmed_at=dt.datetime(2026, 1, 1, 9, 0, tzinfo=dt.timezone.utc),
    )
    other = django_user_model.objects.create_user(username="bob", password="pw")
    client.force_login(other)
    content = client.get(reverse("workout-detail", args=[w.pk])).content.decode()
    # Owner-only controls are hidden; the logger's name is shown instead.
    assert "Logged by" in content
    assert "alice" in content
    assert reverse("workout-edit", args=[w.pk]) not in content
    assert reverse("workout-delete", args=[w.pk]) not in content


# --- Workout list visibility ------------------------------------------------


@pytest.mark.django_db
def test_workout_list_shows_others_confirmed_and_hides_others_drafts(
    auth_client, django_user_model
):
    other = django_user_model.objects.create_user(username="bob", password="pw")
    confirmed = Workout.objects.create(
        user=other,
        date=dt.datetime(2026, 1, 2, 8, 0, tzinfo=dt.timezone.utc),
        notes="bob confirmed",
        confirmed_at=dt.datetime(2026, 1, 2, 9, 0, tzinfo=dt.timezone.utc),
    )
    draft = Workout.objects.create(
        user=other,
        date=dt.datetime(2026, 1, 3, 8, 0, tzinfo=dt.timezone.utc),
        notes="bob draft",
    )
    content = auth_client.get(reverse("workout-list")).content.decode()
    assert "bob confirmed" in content
    assert "bob" in content  # username surfaced
    assert reverse("workout-detail", args=[confirmed.pk]) in content
    assert "bob draft" not in content
    assert reverse("workout-detail", args=[draft.pk]) not in content


@pytest.mark.django_db
def test_workout_list_shows_own_drafts(auth_client, workout):
    content = auth_client.get(reverse("workout-list")).content.decode()
    assert reverse("workout-detail", args=[workout.pk]) in content


# --- Cardio exercise add (HTMX) ---------------------------------------------


@pytest.mark.django_db
def test_cardio_add_happy_path(auth_client, workout, cardio_movement):
    resp = auth_client.post(
        reverse("cardio-exercise-add", args=[workout.pk]),
        {
            "movement": cardio_movement.pk,
            "distance_0": "5",
            "distance_1": "mile",
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
            "weight_1": "pound",
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
            "distance_1": "mile",
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


# --- Feedback ---------------------------------------------------------------


def test_feedback_form_disables_submit_after_click(auth_client):
    # Guards against double-submitting (and filing duplicate GitHub issues).
    resp = auth_client.get(reverse("feedback"))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'id="feedback-form"' in html
    assert "button.disabled = true" in html


# --- Alphabetized <option> lists --------------------------------------------


def _option_labels(field):
    return [str(label) for _value, label in field.field.widget.choices if _value]


@pytest.mark.django_db
def test_movement_options_are_alphabetized():
    from workouts.forms import CardioExerciseForm, StrengthExerciseForm

    Movement.objects.create(name="zumba", kind=Movement.CARDIO)
    Movement.objects.create(name="Aqua jogging", kind=Movement.CARDIO)
    Movement.objects.create(name="Zercher squat", kind=Movement.STRENGTH)
    Movement.objects.create(name="arnold press", kind=Movement.STRENGTH)

    for form in (CardioExerciseForm(), StrengthExerciseForm()):
        labels = _option_labels(form["movement"])
        assert labels == sorted(labels, key=str.lower)
        assert len(labels) >= 2


@pytest.mark.django_db
def test_unit_options_are_alphabetized():
    from workouts.forms import CardioExerciseForm, StrengthExerciseForm

    for bound in (CardioExerciseForm()["distance"], StrengthExerciseForm()["weight"]):
        unit_select = bound.field.widget.widgets[1]
        labels = [label for value, label in unit_select.choices if value]
        assert labels == sorted(labels, key=str.lower)


# --- Duplication ------------------------------------------------------------


def test_workout_duplicate_copies_exercises_into_new_draft(
    auth_client, user, workout, cardio_movement, strength_movement
):
    from unsphere.units import u

    workout.notes = "leg day"
    workout.timezone = "America/Los_Angeles"
    workout.confirmed_at = dt.datetime(2026, 1, 1, 9, 0, tzinfo=dt.timezone.utc)
    workout.save()
    CardioExercise.objects.create(
        workout=workout, movement=cardio_movement, distance=u("3 mile")
    )
    StrengthExercise.objects.create(
        workout=workout, movement=strength_movement, sets=3, reps=5, weight=u("100 pound")
    )

    resp = auth_client.post(reverse("workout-duplicate", args=[workout.pk]))
    copy = Workout.objects.exclude(pk=workout.pk).get()
    assert resp.status_code == 302
    assert resp.url == reverse("workout-detail", args=[copy.pk])
    assert copy.user == user
    assert copy.is_draft
    assert copy.notes == "leg day"
    assert copy.timezone == "America/Los_Angeles"
    assert copy.date > workout.date
    (c,) = copy.cardioexercises.all()
    assert c.movement == cardio_movement and c.distance == u("3 mile")
    (s,) = copy.strengthexercises.all()
    assert (s.sets, s.reps, s.weight) == (3, 5, u("100 pound"))
    # The original is untouched.
    assert workout.cardioexercises.count() == 1
    assert workout.strengthexercises.count() == 1


def test_workout_duplicate_rejects_get(auth_client, workout):
    resp = auth_client.get(reverse("workout-duplicate", args=[workout.pk]))
    assert resp.status_code == 405


def test_workout_duplicate_of_others_workout(client, django_user_model, workout):
    bob = django_user_model.objects.create_user(username="bob", password="pw")
    client.force_login(bob)
    # Another user's draft is private.
    resp = client.post(reverse("workout-duplicate", args=[workout.pk]))
    assert resp.status_code == 404
    # A confirmed workout can be copied, and the copy belongs to the requester.
    workout.confirmed_at = workout.date
    workout.save()
    resp = client.post(reverse("workout-duplicate", args=[workout.pk]))
    assert resp.status_code == 302
    assert Workout.objects.get(user=bob).is_draft


def test_cardio_duplicate(auth_client, workout, cardio_movement):
    from unsphere.units import u

    ex = CardioExercise.objects.create(
        workout=workout, movement=cardio_movement, duration=u("20 min"), notes="easy"
    )
    resp = auth_client.post(reverse("cardio-exercise-duplicate", args=[ex.pk]))
    assert resp.status_code == 200
    copy = workout.cardioexercises.exclude(pk=ex.pk).get()
    assert copy.duration == u("20 min") and copy.notes == "easy"
    assert f'id="cardio-exercise-{copy.pk}"' in resp.content.decode()


def test_strength_duplicate(auth_client, workout, strength_movement):
    ex = StrengthExercise.objects.create(
        workout=workout, movement=strength_movement, sets=3, reps=10
    )
    resp = auth_client.post(reverse("strength-exercise-duplicate", args=[ex.pk]))
    assert resp.status_code == 200
    copy = workout.strengthexercises.exclude(pk=ex.pk).get()
    assert (copy.sets, copy.reps) == (3, 10)
    assert f'id="strength-exercise-{copy.pk}"' in resp.content.decode()


def test_exercise_duplicate_scoped_to_owner(
    client, django_user_model, workout, strength_movement
):
    ex = StrengthExercise.objects.create(
        workout=workout, movement=strength_movement, sets=3, reps=10
    )
    bob = django_user_model.objects.create_user(username="bob", password="pw")
    client.force_login(bob)
    resp = client.post(reverse("strength-exercise-duplicate", args=[ex.pk]))
    assert resp.status_code == 404
    assert workout.strengthexercises.count() == 1


def test_feedback_issue_assigned_to_repo_owner(auth_client, settings, monkeypatch):
    import json

    from workouts import views

    settings.GITHUB_FEEDBACK_REPO = "maxwelljoslyn/unsphere"
    settings.GITHUB_FEEDBACK_TOKEN = "t"
    sent = []
    monkeypatch.setattr(views, "urlopen", lambda req: sent.append(req))

    resp = auth_client.post(
        reverse("feedback"), {"title": "Bug", "description": "It broke"}
    )
    assert resp.status_code == 302
    (req,) = sent
    payload = json.loads(req.data)
    assert payload["assignees"] == ["maxwelljoslyn"]
    assert payload["labels"] == ["user-feedback"]
